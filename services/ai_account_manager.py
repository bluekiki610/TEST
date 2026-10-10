# services/ai_account_manager.py
# AI Accounts 存储层 —— V1.1 Step 3
#
# 目标：把「用户的 API Key / 多供应商 / 模型收藏 / 默认模型」存到独立文件，
#       与现有 data.json 完全解耦。
#
# 存储位置：data/ai_accounts.json
#   - 跟随 main.py 的 DATA_ROOT 规则（支持 DATA_DIR 环境变量）
#   - 该文件是 step 2 审核通过的设计落点
#
# ⚠️ 安全与边界（严格遵守 Step 3 要求）：
#   - 不修改 data.json
#   - 不读写 ai_keys（现有系统的那一份配置，本层完全不碰）
#   - 不修改 ext_ai / ext_* 任何插件
#   - 不发起任何真实 API 请求
#   - 本层是**存储层**，只负责读写与校验，不做选型请求
#
# 关于 API Key 明文：
#   与现有 ai_keys 同级别的明文存储（Step 2 已确认）。
#   但本文件独立于 data.json，因此：
#     · 不会进入 /api/backup 的默认输出
#     · 不会进入 agent 层 provider 的读取面
#   建议部署时把该文件设为仅服务账户可读（chmod 600），
#   并确认它不会被提交进公开仓库。结构里预留 encrypted 字段位。

import json
import os
import re
import shutil
import threading
from pathlib import Path

from .providers.base import CAPABILITIES

# 优先复用 provider 注册表的 key 做校验；拿不到时不阻断（保持本层可独立使用）
try:
    from .providers import PROVIDER_CLASSES as _KNOWN_PROVIDERS
except Exception:  # pragma: no cover
    _KNOWN_PROVIDERS = {}

SCHEMA_VERSION = 1
DEFAULT_FILENAME = "ai_accounts.json"

# 环境变量覆盖（便于测试与多世界部署）
ENV_FILE = "AI_ACCOUNTS_FILE"
ENV_DATA_DIR = "DATA_DIR"

# 用户名归一化用的 emoji / 变体选择符 / 零宽字符范围。
# 与 main.py 的 normalize_name / strip_emoji 保持同一套语义（此处不 import main，
# 避免与主程序形成循环依赖）。
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F000-\U0001F2FF"
    "\uFE00-\uFE0F"
    "\u200B-\u200D"
    "\u20E3"
    "\u2122\u2139\u2194-\u21AA\u231A-\u231B\u2328\u23CF\u23E9-\u23F3\u23F8-\u23FA"
    "\u24C2\u25AA-\u25AB\u25B6\u25C0\u25FB-\u25FE"
    "\u2600-\u27BF\u2934-\u2935\u2B05-\u2B07\u2B1B-\u2B1C\u2B50\u2B55"
    "\u3030\u303D\u3297\u3299"
    "]+",
    flags=re.UNICODE,
)


def _refine_name(name):
    """把用户名归一化成稳定 key。

    规则与 main.py 的 strip_emoji 一致：去掉 emoji / 变体选择符 / 零宽字符后 strip。
    注意：项目当前**没有真正的 user_id**，主键就是归一化后的用户名（Step 2 已确认）。
    """
    s = str(name or "")
    s = _EMOJI_RE.sub("", s)
    s = s.replace("\ufe0f", "").strip()
    return s or str(name or "").strip()


def _now():
    """时间戳字符串。优先用 main.now_str 的格式，避免强依赖。"""
    try:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def _default_data_root():
    """推断 data 目录：DATA_DIR 环境变量优先，否则 <repo>/data。

    与 main.py:29 `DATA_ROOT = DATA_DIR or BASE_DIR/"data"` 保持同一规则。
    """
    env_dir = (os.environ.get(ENV_DATA_DIR) or "").strip()
    if env_dir:
        return Path(env_dir)
    # services/ai_account_manager.py -> services/ -> <repo>/data
    return Path(__file__).resolve().parent.parent / "data"


def _default_file_path():
    env_file = (os.environ.get(ENV_FILE) or "").strip()
    if env_file:
        return Path(env_file)
    return _default_data_root() / DEFAULT_FILENAME


def empty_accounts():
    """初始文件结构。"""
    return {"version": SCHEMA_VERSION, "users": {}}


def empty_user(display_name=""):
    """单个用户的结构（Step 3 要求的四个字段 + 迁移锚点）。"""
    return {
        "display_name": display_name or "",
        "providers": {},
        "favorites": {},
        "defaults": {},
    }


class AIAccountManager:
    """用户 AI 账号配置的存储层（多供应商 / 模型收藏 / 默认模型）。

    设计要点：
      1. 独立文件，不碰 data.json / ai_keys。
      2. 线程安全：所有公开方法持同一把可重入锁（现有系统大量使用后台线程）。
      3. 原子写：先写临时文件，再 os.replace 覆盖；覆盖前留一份 .bak。
      4. 宽容失败：读失败不抛异常，返回安全默认值，避免拖垮调用方。
      5. 支持多实例：每次读写前比对文件 mtime/size，外部改动会被重新加载。

    典型用法：
        mgr = AIAccountManager()
        mgr.save_provider("亦言❄️", "deepseek", "sk-xxx")
        mgr.add_favorite_model("亦言", "chat", "deepseek", "deepseek-chat", label="V3")
        mgr.set_default_model("亦言", "chat", "deepseek", "deepseek-chat")
        cfg = mgr.get_user("亦言")
    """

    def __init__(self, path=None, autoload=True, create_file=True):
        self.path = Path(path) if path else _default_file_path()
        self._lock = threading.RLock()
        self._data = empty_accounts()
        self._stat = None          # (mtime_ns, size) 用于外部改动检测
        self._loaded = False
        if autoload:
            self.load()
        if create_file:
            # Step 3 要求：初始化 ai_accounts.json（首次即落盘 {"version":1,"users":{}}）
            self.ensure_file()

    # ==================== 路径与文件 ====================
    @property
    def data_root(self):
        return self.path.parent

    def _stat_now(self):
        try:
            st = self.path.stat()
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def _changed_on_disk(self):
        return self._loaded and self._stat_now() != self._stat

    def load(self):
        """从磁盘读取。文件不存在 / 解析失败时回到空结构，不抛异常。"""
        with self._lock:
            try:
                if not self.path.is_file():
                    self._data = empty_accounts()
                    self._stat = None
                    self._loaded = True
                    return False
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("根节点不是对象")
                users = raw.get("users")
                if not isinstance(users, dict):
                    users = {}
                ver = raw.get("version")
                self._data = {
                    "version": ver if isinstance(ver, int) else SCHEMA_VERSION,
                    "users": users,
                }
                self._stat = self._stat_now()
                self._loaded = True
                return True
            except Exception as e:
                print(f"[ai_accounts] 读取失败，使用空结构: {e}", flush=True)
                self._data = empty_accounts()
                self._stat = None
                self._loaded = True
                return False

    def _reload_if_changed(self):
        """多实例/外部编辑场景：发现文件变了就重新加载。"""
        if self._changed_on_disk():
            self.load()

    def ensure_file(self):
        """确保文件存在且结构合法（不存在则写出初始结构）。"""
        with self._lock:
            self._reload_if_changed()
            if not self.path.is_file():
                return self._write()
            return True

    def _write(self):
        """原子写入。返回是否成功。调用方需已持锁。"""
        try:
            self.data_root.mkdir(parents=True, exist_ok=True)
            text = json.dumps(self._data, ensure_ascii=False, indent=1)
            # 覆盖前留备份，沿用 main.py:_do_save_async 的 .bak 习惯
            if self.path.is_file():
                try:
                    shutil.copyfile(self.path, str(self.path) + ".bak")
                except Exception:
                    pass
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, self.path)
            self._stat = self._stat_now()
            self._loaded = True
            return True
        except Exception as e:
            print(f"[ai_accounts] 写入失败: {e}", flush=True)
            return False

    def save(self):
        """显式落盘。"""
        with self._lock:
            return self._write()

    # ==================== 用户名归一化 ====================
    def _match_existing_key(self, name):
        """尽量复用已存在的键，避免出现「亦言」与「亦言❄️」两份配置。"""
        target = _refine_name(name)
        raw = str(name or "").strip()
        users = self._data.get("users", {}) or {}
        # 1) 精确命中已有键
        if raw in users:
            return raw
        if target in users:
            return target
        # 2) 归一化后相等 / display_name 相等
        for k, v in users.items():
            if _refine_name(k) == target:
                return k
            if isinstance(v, dict) and _refine_name(v.get("display_name")) == target and target:
                return k
        # 3) 都不匹配 → 用归一化名作为新键
        return target

    def user_key(self, user):
        """公开：把任意写法解析成实际存储键（不落盘、不创建）。"""
        with self._lock:
            self._reload_if_changed()
            return self._match_existing_key(user)

    # ==================== 用户读写 ====================
    def list_users(self):
        with self._lock:
            self._reload_if_changed()
            return sorted((self._data.get("users", {}) or {}).keys())

    def has_user(self, user):
        with self._lock:
            self._reload_if_changed()
            return self._match_existing_key(user) in (self._data.get("users", {}) or {})

    def get_user(self, user):
        """读取某个用户的配置。

        返回副本（深拷贝语义上的浅层结构），调用方改它不会污染内部状态。
        用户不存在时**不创建**，返回 None，便于调用方区分「没配置」与「配置为空」。
        """
        with self._lock:
            self._reload_if_changed()
            key = self._match_existing_key(user)
            u = (self._data.get("users", {}) or {}).get(key)
            if u is None:
                return None
            return json.loads(json.dumps(u, ensure_ascii=False))

    def ensure_user(self, user):
        """取用户配置；不存在则按初始结构创建并落盘。始终返回 dict。"""
        with self._lock:
            self._reload_if_changed()
            users = self._data.setdefault("users", {})
            key = self._match_existing_key(user)
            if key not in users or not isinstance(users[key], dict):
                users[key] = empty_user(display_name=str(user or "").strip())
                self._write()
                return json.loads(json.dumps(users[key], ensure_ascii=False))
            # 补齐可能缺失的子字段（兼容手工编辑过的文件）
            u = users[key]
            u.setdefault("display_name", str(user or "").strip())
            u.setdefault("providers", {})
            u.setdefault("favorites", {})
            u.setdefault("defaults", {})
            return json.loads(json.dumps(u, ensure_ascii=False))

    def delete_user(self, user):
        """删除整个用户配置。返回是否真的删了。"""
        with self._lock:
            self._reload_if_changed()
            key = self._match_existing_key(user)
            users = self._data.setdefault("users", {})
            if key in users:
                users.pop(key, None)
                self._write()
                return True
            return False

    # ==================== 供应商（API Key） ====================
    def save_provider(self, user, provider, api_key, base_url=None, enabled=True):
        """保存某用户的某供应商配置（api_key 等）。

        行为：已存在则合并更新（未传的字段保持原值）。
        provider 未知时仍允许保存（不锁死供应商集合），只打一行日志。
        """
        provider = (provider or "").strip()
        if not provider:
            raise ValueError("provider 不能为空")
        if _KNOWN_PROVIDERS and provider not in _KNOWN_PROVIDERS:
            print(f"[ai_accounts] 注意：provider '{provider}' 不在已知注册表中（仍保存）", flush=True)

        with self._lock:
            self._reload_if_changed()
            key = self._match_existing_key(user)
            users = self._data.setdefault("users", {})
            u = users.setdefault(key, empty_user(display_name=str(user or "").strip()))
            providers = u.setdefault("providers", {})
            cfg = dict(providers.get(provider, {}) or {})
            cfg["api_key"] = api_key if api_key is not None else cfg.get("api_key", "")
            if base_url is not None:
                cfg["base_url"] = base_url
            cfg["enabled"] = bool(enabled)
            cfg["set_at"] = _now()
            providers[provider] = cfg
            self._write()
            return json.loads(json.dumps(cfg, ensure_ascii=False))

    def get_provider(self, user, provider):
        """读取某用户的某供应商配置（无则 None）。"""
        with self._lock:
            u = self.get_user(user)
            if not u:
                return None
            cfg = (u.get("providers", {}) or {}).get((provider or "").strip())
            return cfg if isinstance(cfg, dict) else None

    def remove_provider(self, user, provider):
        with self._lock:
            self._reload_if_changed()
            key = self._match_existing_key(user)
            users = self._data.setdefault("users", {})
            u = users.get(key)
            if not isinstance(u, dict):
                return False
            changed = (u.get("providers", {}) or {}).pop((provider or "").strip(), None) is not None
            # 同时清掉指向该 provider 的默认模型（避免默认项悬空）
            defaults = u.get("defaults", {}) or {}
            for cap in list(defaults.keys()):
                d = defaults.get(cap)
                if isinstance(d, dict) and d.get("provider") == (provider or "").strip():
                    defaults.pop(cap, None)
                    changed = True
            if changed:
                self._write()
            return changed

    def list_providers(self, user):
        """列出该用户已配置的供应商 key。"""
        u = self.get_user(user)
        if not u:
            return []
        return sorted((u.get("providers", {}) or {}).keys())

    def has_api_key(self, user, provider):
        """该用户该供应商是否已填 key（只回答有无，不返回 key 本身）。"""
        cfg = self.get_provider(user, provider)
        return bool(cfg and (cfg.get("api_key") or "").strip())

    # ==================== 模型收藏 ====================
    def add_favorite_model(self, user, capability, provider, model, label="", extra=None):
        """往某能力位的收藏列表里加一个模型（同 provider+model 去重，重复则更新 label）。"""
        capability = (capability or "").strip()
        if capability not in CAPABILITIES:
            raise ValueError(f"未知能力位: {capability}（可用: {', '.join(CAPABILITIES)}）")
        provider = (provider or "").strip()
        model = (model or "").strip()
        if not provider or not model:
            raise ValueError("provider 与 model 都不能为空")

        with self._lock:
            self._reload_if_changed()
            key = self._match_existing_key(user)
            users = self._data.setdefault("users", {})
            u = users.setdefault(key, empty_user(display_name=str(user or "").strip()))
            favs = u.setdefault("favorites", {})
            lst = favs.setdefault(capability, [])
            if not isinstance(lst, list):
                lst = []
                favs[capability] = lst
            item = {"provider": provider, "model": model, "label": label or "", "added_at": _now()}
            if isinstance(extra, dict):
                for k, v in extra.items():
                    if k not in ("provider", "model", "added_at"):
                        item[k] = v
            # 去重：同 provider + 同 model 视为同一个收藏
            for i, old in enumerate(lst):
                if isinstance(old, dict) and old.get("provider") == provider and old.get("model") == model:
                    item["added_at"] = old.get("added_at") or item["added_at"]
                    lst[i] = item
                    self._write()
                    return json.loads(json.dumps(item, ensure_ascii=False))
            lst.append(item)
            self._write()
            return json.loads(json.dumps(item, ensure_ascii=False))

    def list_favorite_models(self, user, capability=None):
        """列出收藏。capability 为空则返回全部能力位。"""
        u = self.get_user(user)
        favs = (u or {}).get("favorites", {}) or {}
        if capability:
            lst = favs.get((capability or "").strip(), [])
            return list(lst) if isinstance(lst, list) else []
        return {k: (list(v) if isinstance(v, list) else []) for k, v in favs.items()}

    def remove_favorite_model(self, user, capability, provider, model):
        capability = (capability or "").strip()
        provider = (provider or "").strip()
        model = (model or "").strip()
        with self._lock:
            self._reload_if_changed()
            key = self._match_existing_key(user)
            users = self._data.setdefault("users", {})
            u = users.get(key)
            if not isinstance(u, dict):
                return False
            favs = u.get("favorites", {}) or {}
            lst = favs.get(capability)
            if not isinstance(lst, list):
                return False
            before = len(lst)
            favs[capability] = [
                x for x in lst
                if not (isinstance(x, dict) and x.get("provider") == provider and x.get("model") == model)
            ]
            changed = len(favs[capability]) != before
            # 若删掉的正是当前默认模型，同时清掉默认项，避免悬空
            d = (u.get("defaults", {}) or {}).get(capability)
            if changed and isinstance(d, dict) and d.get("provider") == provider and d.get("model") == model:
                (u.get("defaults", {}) or {}).pop(capability, None)
            # 收藏清空则移除该能力位的空列表
            if not favs[capability]:
                favs.pop(capability, None)
            if changed:
                self._write()
            return changed

    # ==================== 默认模型 ====================
    def set_default_model(self, user, capability, provider, model):
        """设定某能力位的默认模型。

        不强依赖收藏列表（允许先设默认再收藏），但会记录 provider/model 便于自检。
        """
        capability = (capability or "").strip()
        if capability not in CAPABILITIES:
            raise ValueError(f"未知能力位: {capability}（可用: {', '.join(CAPABILITIES)}）")
        provider = (provider or "").strip()
        model = (model or "").strip()
        if not provider or not model:
            raise ValueError("provider 与 model 都不能为空")

        with self._lock:
            self._reload_if_changed()
            key = self._match_existing_key(user)
            users = self._data.setdefault("users", {})
            u = users.setdefault(key, empty_user(display_name=str(user or "").strip()))
            defaults = u.setdefault("defaults", {})
            defaults[capability] = {"provider": provider, "model": model, "set_at": _now()}
            self._write()
            return json.loads(json.dumps(defaults[capability], ensure_ascii=False))

    def get_default_model(self, user, capability):
        """取某能力位的默认模型。返回 (provider, model)；未设置返回 ("", "")。"""
        u = self.get_user(user)
        d = ((u or {}).get("defaults", {}) or {}).get((capability or "").strip())
        if not isinstance(d, dict):
            return "", ""
        return d.get("provider", "") or "", d.get("model", "") or ""

    def clear_default_model(self, user, capability):
        with self._lock:
            self._reload_if_changed()
            key = self._match_existing_key(user)
            users = self._data.setdefault("users", {})
            u = users.get(key)
            if not isinstance(u, dict):
                return False
            defaults = u.get("defaults", {}) or {}
            changed = defaults.pop((capability or "").strip(), None) is not None
            if changed:
                self._write()
            return changed

    # ==================== 与 Step 1 ProviderManager 的衔接 ====================
    def to_manager_payload(self, user):
        """把某用户的配置转成 ProviderManager 能直接吃的结构（**不 import provider_manager**，
        避免两个模块互相依赖；Step 4 再接起来）。

        产出：
            {
              "config": {provider: {"api_key","base_url","models":{capability:model}}},
              "capability_prefs": {capability: [provider, ...]}
            }
        其中 models 由「该能力位的默认模型」与「收藏列表顺序」推导。
        """
        u = self.get_user(user) or empty_user()
        providers = u.get("providers", {}) or {}
        favorites = u.get("favorites", {}) or {}
        defaults = u.get("defaults", {}) or {}

        config = {}
        for pkey, pcfg in providers.items():
            if not isinstance(pcfg, dict):
                continue
            config[pkey] = {
                "api_key": pcfg.get("api_key", ""),
                "base_url": pcfg.get("base_url", ""),
                "models": {},
            }

        prefs = {}
        for cap in CAPABILITIES:
            order = []
            # 1) 默认模型所在 provider 排最前
            d = defaults.get(cap)
            if isinstance(d, dict) and d.get("provider"):
                order.append(d["provider"])
                config.setdefault(d["provider"], {"api_key": "", "base_url": "", "models": {}})
                config[d["provider"]].setdefault("models", {})[cap] = d.get("model", "")
            # 2) 其余按收藏顺序
            for item in (favorites.get(cap) or []):
                if not isinstance(item, dict):
                    continue
                p = item.get("provider")
                if not p:
                    continue
                if p not in order:
                    order.append(p)
                config.setdefault(p, {"api_key": "", "base_url": "", "models": {}})
                # 不覆盖默认模型已经写好的那一项
                config[p].setdefault("models", {}).setdefault(cap, item.get("model", ""))
            if order:
                prefs[cap] = order

        return {"config": config, "capability_prefs": prefs}

    # ==================== 只读自检 ====================
    def describe(self):
        """概览，用于调试/前端展示。**不返回 api_key 明文**，只回答有无。"""
        with self._lock:
            self._reload_if_changed()
            users = self._data.get("users", {}) or {}
            out = {}
            for k, u in users.items():
                if not isinstance(u, dict):
                    continue
                provs = u.get("providers", {}) or {}
                out[k] = {
                    "display_name": u.get("display_name", ""),
                    "providers": {
                        p: {"has_key": bool((c or {}).get("api_key")), "enabled": bool((c or {}).get("enabled", True))}
                        for p, c in provs.items()
                    },
                    "favorites": {cap: len(v) for cap, v in (u.get("favorites", {}) or {}).items() if isinstance(v, list)},
                    "defaults": {
                        cap: {"provider": (d or {}).get("provider", ""), "model": (d or {}).get("model", "")}
                        for cap, d in (u.get("defaults", {}) or {}).items() if isinstance(d, dict)
                    },
                }
            return {
                "file": str(self.path),
                "version": self._data.get("version", SCHEMA_VERSION),
                "user_count": len(out),
                "users": out,
            }


# ==================== 便捷单例 ====================
_default_manager = None
_default_lock = threading.RLock()


def get_account_manager(path=None):
    """获取默认 manager 单例（可按需传入自定义路径）。"""
    global _default_manager
    with _default_lock:
        if _default_manager is None or path is not None:
            _default_manager = AIAccountManager(path=path)
        return _default_manager


def set_account_manager(mgr):
    global _default_manager
    with _default_lock:
        _default_manager = mgr
    return _default_manager
