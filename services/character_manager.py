# services/character_manager.py
# Character Template Manager —— V1.1 Step 6C 修正版
#
# ==================== 定位 ====================
# 角色模板定义「这个世界里有哪些人、他们是什么样」，属于**世界**，
# 不随用户变化。用户与角色的关系/记忆属于**运行时**（另一层）。
#
#     World Template
#           ↓
#     Character Template        ← 本模块（人格/外观/system_prompt/声音引用/行为）
#           ↓
#     Character Runtime         ← 未来：relationship / memory / conversation
#
# 声音**只引用资产 id（default_voice_id）**，不复制 voice_id：
#   这样换供应商或换音色时只改声音库一处，所有世界/角色自动跟随。
#
# 双层绑定（Step 6C 修正版）：
#   角色模板存 **默认声音**（default_voice_id，管理员设定，所有用户共享）
#   用户可在 user_character_preferences.json 里存**覆盖**（只影响自己）
#   解析优先级见 ai_service.resolve_voice()
#
# 存储：data/character_templates.json
#
# 结构：
#   {
#     "version": 1,
#     "characters": {
#       "nightchen": {
#         "character_id": "nightchen",
#         "name": "夜辰",
#         "character_type": "template",      // template（官方）| custom（用户创建）
#         "world_id": "otome_a",              // 属于哪个世界模板（空=全局可用）
#         "default_voice_id": "voice_001",    // ← 只存引用，不存 voice_id
#         "personality": "",
#         "appearance": "",
#         "system_prompt": "",
#         "behavior": {},
#         "owner": "",                        // custom 角色才有（创建者）
#         "locked": true,
#         "created_at": "...",
#         "updated_at": "..."
#       }
#     }
#   }

import json
import os
import re
import shutil
import threading
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_FILENAME = "character_templates.json"

ENV_FILE = "CHARACTER_TEMPLATES_FILE"
ENV_DATA_DIR = "DATA_DIR"

# 官方角色（世界模板定义）
TYPE_TEMPLATE = "template"
# 用户创建角色（当前测试环境允许，未来由世界决定是否开放）
TYPE_CUSTOM = "custom"

CHARACTER_TYPES = (TYPE_TEMPLATE, TYPE_CUSTOM)

_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{2,64}$")


def _now():
    try:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def _default_data_root():
    env_dir = (os.environ.get(ENV_DATA_DIR) or "").strip()
    if env_dir:
        return Path(env_dir)
    return Path(__file__).resolve().parent.parent / "data"


def _default_file_path():
    env_file = (os.environ.get(ENV_FILE) or "").strip()
    if env_file:
        return Path(env_file)
    return _default_data_root() / DEFAULT_FILENAME


def empty_characters():
    return {"version": SCHEMA_VERSION, "characters": {}}


class CharacterManager:
    """角色模板管理（世界级）。

    支持两种角色类型：
        template —— 官方角色，管理员定义，用户不可改
        custom   —— 用户创建角色（当前测试环境保留，未来由世界开关控制）
    """

    def __init__(self, path=None, autoload=True, create_file=True, write_guard=None):
        self.path = Path(path) if path else _default_file_path()
        self._lock = threading.RLock()
        self._data = empty_characters()
        self._stat = None
        self._loaded = False
        self._write_guard = write_guard
        if autoload:
            self.load()
        if create_file:
            self.ensure_file()

    # ==================== 写保护 ====================
    def set_write_guard(self, guard):
        self._write_guard = guard

    def _check_write(self):
        if self._write_guard is None:
            return True
        try:
            return bool(self._write_guard())
        except Exception as e:
            print(f"[characters] 写保护回调异常，拒绝写入: {e}", flush=True)
            return False

    # ==================== 文件 ====================
    def _stat_now(self):
        try:
            st = self.path.stat()
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def _changed_on_disk(self):
        return self._loaded and self._stat_now() != self._stat

    def load(self):
        with self._lock:
            try:
                if not self.path.is_file():
                    self._data = empty_characters()
                    self._stat = None
                    self._loaded = True
                    return False
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("根节点不是对象")
                chars = raw.get("characters")
                if not isinstance(chars, dict):
                    chars = {}
                ver = raw.get("version")
                self._data = {
                    "version": ver if isinstance(ver, int) else SCHEMA_VERSION,
                    "characters": chars,
                }
                self._stat = self._stat_now()
                self._loaded = True
                return True
            except Exception as e:
                print(f"[characters] 读取失败，使用空结构: {e}", flush=True)
                self._data = empty_characters()
                self._stat = None
                self._loaded = True
                return False

    def _reload_if_changed(self):
        if self._changed_on_disk():
            self.load()

    def ensure_file(self):
        with self._lock:
            self._reload_if_changed()
            if not self.path.is_file():
                return self._write(skip_guard=True)
            return True

    def _write(self, skip_guard=False):
        if not skip_guard and not self._check_write():
            print("[characters] 写入被拒绝（缺少管理员权限）", flush=True)
            return False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(self._data, ensure_ascii=False, indent=1)
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
            print(f"[characters] 写入失败: {e}", flush=True)
            return False

    def save(self):
        with self._lock:
            return self._write()

    # ==================== 查询 ====================
    def list_characters(self, world_id=None, character_type=None):
        """列出角色。可按 world_id / character_type 过滤。"""
        with self._lock:
            self._reload_if_changed()
            out = []
            for cid, c in (self._data.get("characters", {}) or {}).items():
                if not isinstance(c, dict):
                    continue
                if world_id and (c.get("world_id") or "") not in ("", world_id):
                    continue
                if character_type and (c.get("character_type") or TYPE_TEMPLATE) != character_type:
                    continue
                item = json.loads(json.dumps(c, ensure_ascii=False))
                item.setdefault("character_id", cid)
                out.append(item)
            out.sort(key=lambda x: x.get("character_id", ""))
            return out

    def get_character(self, character_id):
        """按 character_id 取角色模板（TTS 链路的第一跳）。"""
        cid = (character_id or "").strip()
        if not cid:
            return None
        with self._lock:
            self._reload_if_changed()
            c = (self._data.get("characters", {}) or {}).get(cid)
            if not isinstance(c, dict):
                return None
            out = json.loads(json.dumps(c, ensure_ascii=False))
            out.setdefault("character_id", cid)
            return out

    def find_by_name(self, name):
        """按显示名反查角色（兼容旧调用里传中文名的情况）。"""
        target = (name or "").strip()
        if not target:
            return None
        with self._lock:
            self._reload_if_changed()
            for cid, c in (self._data.get("characters", {}) or {}).items():
                if not isinstance(c, dict):
                    continue
                if (c.get("name") or "").strip() == target or cid == target:
                    out = json.loads(json.dumps(c, ensure_ascii=False))
                    out.setdefault("character_id", cid)
                    return out
        return None

    def resolve(self, character_id_or_name):
        """既接受 character_id 也接受显示名，返回角色模板或 None。"""
        c = self.get_character(character_id_or_name)
        if c is not None:
            return c
        return self.find_by_name(character_id_or_name)

    def get_voice_asset_id(self, character_id_or_name):
        """取该角色的**默认声音**资产 id（TTS 链路的第二跳）。

        Step 6C 修正版字段名为 default_voice_id；为兼容 6C 第一版
        写入的 voice_asset_id，读取时两者都认（新字段优先）。
        """
        c = self.resolve(character_id_or_name)
        if not c:
            return ""
        return (c.get("default_voice_id") or c.get("voice_asset_id") or "").strip()

    # 旧名别名（6C 第一版 API，保留以免旧调用报错）
    def get_default_voice_id(self, character_id_or_name):
        return self.get_voice_asset_id(character_id_or_name)

    def set_character(self, character_id, name="", character_type=TYPE_TEMPLATE,
                      voice_asset_id=None, world_id="", personality="",
                      appearance="", system_prompt="", behavior=None,
                      owner="", locked=None, default_voice_id=None, extra=None):
        """新增或更新角色模板。

        default_voice_id —— 角色**默认声音**资产 id。
            传 None 表示"保持原值不动"；传 "" 表示"清空声音引用"。
        voice_asset_id    —— 6C 第一版的旧参数名，仍然接受（会写入 default_voice_id），
                             仅为兼容旧调用，新代码请用 default_voice_id。
        locked            —— 不传则按类型默认：template=True，custom=False。
        """
        cid = (character_id or "").strip()
        if not cid:
            raise ValueError("character_id 不能为空")
        if not _ID_RE.match(cid):
            raise ValueError(f"character_id 只能包含字母/数字/下划线/中划线（2-64位），收到: {cid}")
        ctype = (character_type or TYPE_TEMPLATE)
        if ctype not in CHARACTER_TYPES:
            raise ValueError(f"character_type 必须是 {CHARACTER_TYPES} 之一")

        # 新旧参数统一：显式传的 default_voice_id 优先，其次旧的 voice_asset_id
        incoming = default_voice_id if default_voice_id is not None else voice_asset_id

        with self._lock:
            self._reload_if_changed()
            chars = self._data.setdefault("characters", {})
            old = chars.get(cid) if isinstance(chars.get(cid), dict) else {}

            if locked is None:
                locked = old.get("locked", ctype == TYPE_TEMPLATE)

            old_voice = (old.get("default_voice_id") or old.get("voice_asset_id") or "")
            item = {
                "character_id": cid,
                "name": (name or old.get("name") or cid).strip(),
                "character_type": ctype,
                "world_id": (world_id or old.get("world_id") or "").strip(),
                # ← 只存引用，绝不在角色里复制 voice_id
                "default_voice_id": old_voice if incoming is None else (incoming or "").strip(),
                "personality": personality if personality else old.get("personality", ""),
                "appearance": appearance if appearance else old.get("appearance", ""),
                "system_prompt": system_prompt if system_prompt else old.get("system_prompt", ""),
                "behavior": behavior if isinstance(behavior, dict) else old.get("behavior", {}),
                "owner": (owner or old.get("owner") or "").strip(),
                "locked": bool(locked),
                "created_at": old.get("created_at") or _now(),
                "updated_at": _now(),
            }
            item.pop("voice_asset_id", None)   # 迁移后不再保留旧字段
            if isinstance(extra, dict):
                for k, v in extra.items():
                    if k not in ("character_id", "created_at"):
                        item[k] = v
            chars[cid] = item
            ok = self._write()
            return ok, (json.loads(json.dumps(item, ensure_ascii=False)) if ok else None)

    def bind_voice_asset(self, character_id, voice_asset_id):
        """把某个声音资产绑定为角色的**默认声音**（只改引用）。

        会校验该声音资产是否存在，避免角色指向一个不存在的 id。
        """
        return self.bind_default_voice(character_id, voice_asset_id)

    def bind_default_voice(self, character_id, voice_asset_id):
        """设置角色默认声音（Step 6C 修正版正式名）。"""
        vid = (voice_asset_id or "").strip()
        if vid:
            try:
                from .voice_library_manager import get_voice_library_manager
                if not get_voice_library_manager().has_voice(vid):
                    return False, f"声音资产不存在: {vid}"
            except Exception as e:
                print(f"[characters] 校验声音资产失败（继续绑定）: {e}", flush=True)
        ok, item = self.set_character(character_id, default_voice_id=vid)
        return ok, item

    def clear_voice_asset(self, character_id):
        return self.set_character(character_id, default_voice_id="")

    def clear_default_voice(self, character_id):
        return self.set_character(character_id, default_voice_id="")

    def remove_character(self, character_id):
        with self._lock:
            self._reload_if_changed()
            chars = self._data.setdefault("characters", {})
            existed = chars.pop((character_id or "").strip(), None) is not None
            if existed:
                return self._write()
            return False

    def characters_using_voice(self, voice_asset_id):
        """反查哪些角色把这个资产当**默认声音**（删除资产前必须先查这个）。"""
        vid = (voice_asset_id or "").strip()
        if not vid:
            return []
        with self._lock:
            self._reload_if_changed()
            out = []
            for cid, c in (self._data.get("characters", {}) or {}).items():
                if not isinstance(c, dict):
                    continue
                used = (c.get("default_voice_id") or c.get("voice_asset_id") or "").strip()
                if used == vid:
                    out.append(cid)
            return sorted(out)

    def describe(self):
        with self._lock:
            self._reload_if_changed()
            chars = self._data.get("characters", {}) or {}
            return {
                "file": str(self.path),
                "version": self._data.get("version", SCHEMA_VERSION),
                "count": len(chars),
                "characters": json.loads(json.dumps(chars, ensure_ascii=False)),
                "write_protected": self._write_guard is not None,
            }


# ==================== 单例 ====================
_default_manager = None
_default_lock = threading.RLock()


def get_character_manager(path=None):
    global _default_manager
    with _default_lock:
        if _default_manager is None or path is not None:
            _default_manager = CharacterManager(path=path)
        return _default_manager


def set_character_manager(mgr):
    global _default_manager
    with _default_lock:
        _default_manager = mgr
    return _default_manager
