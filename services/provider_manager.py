# services/provider_manager.py
# 供应商配置 / 模型 / 按能力选型 —— V1.1 Step 1：只做内存结构 + 可选简易 JSON
#
# 职责（严格限定）：
#   1. 保存供应商配置（api_key / base_url / models）
#   2. 获取模型（按 provider、按能力位）
#   3. 根据能力选择模型（返回 (provider_key, model_name) 供 AIService 调用）
#
# 明确不做：
#   - 不接数据库
#   - 不读写 main.data / data.json（那是现有系统的持久化，本层完全不碰）
#   - 不发起任何网络请求
#
# 配置结构（内存）：
#   providers = {
#       "deepseek": {"api_key": "...", "base_url": "...",
#                    "models": {"chat": "...", "vision": "..."}},
#       ...
#   }
# 「按能力选模型」还支持一层可选的能力→供应商偏好：
#   capability_prefs = {"tts": ["minimax", "volcano", "elevenlabs"], ...}

import json
import os
from pathlib import Path

from .providers import PROVIDER_CLASSES
from .providers.base import CAPABILITIES


class ProviderManager:
    """供应商与模型的登记中心（第一版：纯内存，可选用 JSON 文件存取）。"""

    def __init__(self, config=None, capability_prefs=None):
        # provider_key -> 配置 dict
        self._configs = dict(config or {})
        # capability -> [provider_key, ...] 偏好顺序
        self._prefs = dict(capability_prefs or {})
        # provider_key -> provider 实例（懒加载）
        self._instances = {}

    # ==================== 配置保存 ====================
    def set_config(self, provider_key, *, api_key=None, base_url=None, models=None):
        """登记（或更新）一个供应商的配置。返回更新后的配置副本。"""
        cfg = dict(self._configs.get(provider_key, {}))
        if api_key is not None:
            cfg["api_key"] = api_key
        if base_url is not None:
            cfg["base_url"] = base_url
        if models is not None:
            merged = dict(cfg.get("models", {}) or {})
            merged.update(models)
            cfg["models"] = merged
        self._configs[provider_key] = cfg
        # 配置变了，丢弃已缓存的实例，下次重建
        self._instances.pop(provider_key, None)
        return dict(cfg)

    def get_config(self, provider_key):
        """取某个供应商的配置（副本，避免外部误改内部状态）。"""
        return dict(self._configs.get(provider_key, {}))

    def remove_config(self, provider_key):
        self._configs.pop(provider_key, None)
        self._instances.pop(provider_key, None)

    def clear(self):
        self._configs.clear()
        self._instances.clear()

    # ==================== 能力偏好 ====================
    def set_capability_prefs(self, capability, provider_keys):
        """设定某能力位的供应商偏好顺序。"""
        self._prefs[capability] = list(provider_keys or [])

    def get_capability_prefs(self, capability):
        return list(self._prefs.get(capability, []))

    # ==================== provider 实例 ====================
    def list_providers(self):
        """所有已知供应商的 key（来自 provider 注册表，不依赖是否已配置）。"""
        return list(PROVIDER_CLASSES.keys())

    def get_provider(self, provider_key):
        """取 provider 实例（懒加载 + 缓存）。未知 key 返回 None。"""
        if provider_key in self._instances:
            return self._instances[provider_key]
        cls = PROVIDER_CLASSES.get(provider_key)
        if cls is None:
            return None
        inst = cls(self._configs.get(provider_key, {}))
        self._instances[provider_key] = inst
        return inst

    def configured_keys(self):
        """已登记配置的供应商 key。"""
        return [k for k in self._configs.keys()]

    # ==================== 模型获取 ====================
    def get_model(self, provider_key, capability):
        """取某供应商在某能力位上配置的模型名；没配返回空串。"""
        p = self.get_provider(provider_key)
        if p is None:
            return ""
        return p.get_model(capability)

    def list_models(self, provider_key=None):
        """列出模型配置。provider_key 为空则返回全部。"""
        if provider_key:
            return {provider_key: dict((self._configs.get(provider_key, {}) or {}).get("models", {}) or {})}
        return {k: dict((v or {}).get("models", {}) or {}) for k, v in self._configs.items()}

    # ==================== 按能力选型 ====================
    def _candidates(self, capability, prefer=None):
        """产出候选 provider 顺序：显式 prefer > 能力偏好 > 已配置 > 其余。"""
        order = []
        for k in (prefer or []):
            if k and k not in order:
                order.append(k)
        for k in self.get_capability_prefs(capability):
            if k not in order:
                order.append(k)
        for k in self.configured_keys():
            if k not in order:
                order.append(k)
        for k in PROVIDER_CLASSES.keys():
            if k not in order:
                order.append(k)
        return order

    def resolve(self, capability, prefer=None, require_configured=False):
        """根据能力位选择 (provider_key, model_name)。

        选择规则（第一版，简单确定、无网络）：
          1. 候选顺序：prefer → 能力偏好 → 已配置的 → 其余已知供应商
          2. 跳过不支持该能力的 provider
          3. require_configured=True 时，跳过未配置 api_key 的 provider
          4. 命中第一个候选即返回；全都不行返回 ("", "")

        注意：第一版不校验模型是否真实存在（那需要网络），只做登记表内的选择。
        """
        for k in self._candidates(capability, prefer=prefer):
            p = self.get_provider(k)
            if p is None:
                continue
            if not p.supports(capability):
                continue
            if require_configured and not p.is_configured():
                continue
            return k, p.get_model(capability)
        return "", ""

    def describe(self):
        """整体自描述，供调试/前端展示用。"""
        return {
            "providers": {
                k: (self.get_provider(k).describe() if self.get_provider(k) else None)
                for k in PROVIDER_CLASSES.keys()
            },
            "configured": self.configured_keys(),
            "capability_prefs": {c: self.get_capability_prefs(c) for c in CAPABILITIES},
        }

    # ==================== 可选：简易 JSON 存取（不接数据库） ====================
    def load_json(self, path):
        """从 JSON 文件读取配置。文件不存在则静默返回 False。"""
        try:
            p = Path(path)
            if not p.is_file():
                return False
            raw = json.loads(p.read_text(encoding="utf-8"))
            self._configs = dict((raw.get("providers") or {}))
            self._prefs = dict((raw.get("capability_prefs") or {}))
            self._instances.clear()
            return True
        except Exception as e:
            print(f"[provider_manager] load_json 失败: {e}", flush=True)
            return False

    def save_json(self, path):
        """把配置写入 JSON 文件。仅用于本地调试/备份，不参与现有系统持久化。"""
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            payload = {"providers": self._configs, "capability_prefs": self._prefs}
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception as e:
            print(f"[provider_manager] save_json 失败: {e}", flush=True)
            return False


# 默认配置来源：环境变量 SERVICES_CONFIG（可选），不设则纯内存空配置
DEFAULT_CONFIG_ENV = "SERVICES_CONFIG"


def build_default_manager():
    """构造一个默认 ProviderManager。

    - 若设置了环境变量 SERVICES_CONFIG 且文件存在 → 从中加载
    - 否则返回空配置的管理器（各 provider 均为「未配置」）
    不读取 main.data，不影响现有系统。
    """
    mgr = ProviderManager()
    path = os.environ.get(DEFAULT_CONFIG_ENV, "")
    if path:
        mgr.load_json(path)
    return mgr


# 模块级单例：业务侧通过 get_manager() 获取，避免到处 new
_default_manager = None


def get_manager():
    global _default_manager
    if _default_manager is None:
        _default_manager = build_default_manager()
    return _default_manager


def set_manager(mgr):
    """替换单例（测试或后续接入设置页时用）。"""
    global _default_manager
    _default_manager = mgr
    return _default_manager
