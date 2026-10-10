# services/providers/base.py
# 供应商统一接口 —— V1.1 Step 1：只定义契约，不实现真实请求
#
# 设计要点：
#   1. 五个能力位固定为 chat / vision / image / asr / tts。
#   2. 未实现的能力统一返回 STANDARD_NOT_IMPLEMENTED，不要抛异常，
#      这样上层 AIService 可以直接把结构返回给业务方，不需要写 try/except。
#   3. 真实接入时，子类只需覆写自己支持的方法，并在 capabilities() 里声明。

# 能力位常量（全项目统一，业务层不要自己拼字符串）
CAPABILITY_CHAT = "chat"
CAPABILITY_VISION = "vision"
CAPABILITY_IMAGE = "image"
CAPABILITY_ASR = "asr"
CAPABILITY_TTS = "tts"

CAPABILITIES = (
    CAPABILITY_CHAT,
    CAPABILITY_VISION,
    CAPABILITY_IMAGE,
    CAPABILITY_ASR,
    CAPABILITY_TTS,
)

# 统一返回结构：未实现
STATUS_NOT_IMPLEMENTED = "not_implemented"
STATUS_OK = "ok"
STATUS_ERROR = "error"


def not_implemented(provider="", capability=""):
    """统一的「未实现」返回结构。

    第一版所有 provider 都返回这个结构，不做真实 API 请求。
    """
    return {
        "status": STATUS_NOT_IMPLEMENTED,
        "provider": provider,
        "capability": capability,
        "message": "V1.1 Step 1：仅有架构骨架，尚未接入真实供应商请求",
        "data": None,
    }


def error_result(provider="", capability="", message=""):
    """统一的错误返回结构（供后续真实接入时复用）。"""
    return {
        "status": STATUS_ERROR,
        "provider": provider,
        "capability": capability,
        "message": message or "unknown error",
        "data": None,
    }


# ==================== Step 5A：真实调用使用的统一返回结构 ====================
# 约定字段：status / provider / model / error
#   status = ok                → 正常，结果在 content
#   status = error             → 出错，原因在 error
#   status = not_implemented   → 该能力位尚未接入
# 额外附带 usage（若上游返回）便于以后接经济系统计费；不保存对话内容。
def ok_result(provider="", model="", content="", usage=None, **extra):
    """成功返回。"""
    out = {
        "status": STATUS_OK,
        "provider": provider,
        "model": model,
        "error": "",
        "content": content,
        "usage": usage if isinstance(usage, dict) else {},
    }
    out.update(extra)
    return out


def fail_result(provider="", model="", error="", **extra):
    """失败返回（含未配置 key、上游报错、超时、解析失败等）。"""
    out = {
        "status": STATUS_ERROR,
        "provider": provider,
        "model": model,
        "error": error or "unknown error",
        "content": "",
    }
    out.update(extra)
    return out


def not_implemented_result(provider="", model="", capability=""):
    """该能力位尚未接入的返回（同样是统一字段，便于上层统一判断）。"""
    return {
        "status": STATUS_NOT_IMPLEMENTED,
        "provider": provider,
        "model": model,
        "error": f"capability '{capability}' not implemented yet" if capability else "not implemented yet",
        "content": "",
    }


class BaseProvider:
    """所有供应商 provider 的基类。

    子类约定：
        key         —— 供应商标识（与配置键一致），如 "deepseek"
        name        —— 展示名，如 "DeepSeek"
        capabilities() —— 返回本 provider 本期**计划支持**的能力位列表
    """

    key = ""
    name = ""
    # 供应商默认端点 / 默认模型（Step 5A 新增）：
    # 用户只填 api_key、不填 base_url 时用这里的兜底，避免调用方必须知道端点。
    # 【架构规则】禁止「provider A 的 key + provider B 的 url」组合：
    #   每个 provider 必须声明自己的 default_base_url；
    #   真实调用的 URL 只能由「本 provider 的 base_url 或 default_base_url」推出。
    default_base_url = ""
    default_model = ""

    # ==================== 能力声明（Step 5B） ====================
    # implemented_capabilities —— 本 provider **已经真实可用**的能力位。
    #   它是唯一的选型依据：ProviderManager 用 supports() 过滤候选，
    #   AIService 不再维护任何硬编码的 (provider, capability) 名单。
    #
    #   ⚠️ 语义必须严格：只写「真的实现了」的能力，不要写「计划支持」的。
    #      否则声明一个未实现的能力位，会绕过 not_implemented 保护，
    #      变成"看起来接上了其实没有"的假成功。
    #
    # planned_capabilities —— 仅供文档/前端展示的「计划支持」清单，
    #   **不参与任何选型判断**，避免把意图误当成能力。
    #
    #   注意：类属性刻意不叫 capabilities —— 那会与下面的 capabilities() 方法同名，
    #   实例属性查找会命中方法对象，class 属性被遮蔽，容易踩坑。
    implemented_capabilities = []
    planned_capabilities = []

    def __init__(self, config=None):
        # config 只保存「配置内容」，不负责持久化（持久化归 provider_manager）
        self.config = config or {}
        self.api_key = self.config.get("api_key", "")
        # 显式配置优先；没配则用类级默认
        self.base_url = self.config.get("base_url", "") or self.default_base_url
        self.models = self.config.get("models", {}) or {}

    # ---------- 能力声明 ----------
    def capabilities(self):
        """本 provider **已真实实现**的能力位（列表副本）。"""
        return list(type(self).implemented_capabilities or [])

    def planned_capabilities(self):
        """本 provider 计划支持的能力位（仅展示，不参与选型）。"""
        return list(type(self).planned_capabilities or [])

    def supports(self, capability):
        """是否已真实实现该能力位。Step 5B 起，这就是唯一的选型依据。"""
        return capability in self.capabilities()

    def get_model(self, capability):
        """取本 provider 针对某能力位配置的模型名（未配置则返回空串）。"""
        return (self.models or {}).get(capability, "")

    def is_configured(self):
        """是否已填好 api_key 等必要配置。"""
        return bool(self.api_key)

    # ---------- 五个能力位（基类统一未实现，子类按需覆盖） ----------
    def chat(self, messages=None, model="", **kwargs):
        return not_implemented(self.key, CAPABILITY_CHAT)

    def vision(self, image=None, prompt="", model="", **kwargs):
        return not_implemented(self.key, CAPABILITY_VISION)

    def image(self, prompt="", model="", **kwargs):
        return not_implemented(self.key, CAPABILITY_IMAGE)

    def asr(self, audio=None, model="", **kwargs):
        return not_implemented(self.key, CAPABILITY_ASR)

    def tts(self, text="", model="", **kwargs):
        return not_implemented(self.key, CAPABILITY_TTS)

    # ---------- 描述 ----------
    def describe(self):
        """给 provider_manager / 调试接口用的自描述。

        capabilities          —— 已真实实现（参与选型）
        planned_capabilities  —— 计划支持（仅展示）
        """
        return {
            "key": self.key,
            "name": self.name,
            "configured": self.is_configured(),
            "capabilities": list(self.capabilities()),
            "planned_capabilities": list(self.planned_capabilities()),
            "models": dict(self.models or {}),
        }

    def __repr__(self):
        return f"<{self.__class__.__name__} key={self.key!r} configured={self.is_configured()}>"
