# services/ai_service.py
# 统一 AI 能力入口 —— V1.1 Step 1：只做路由，不发起真实请求
#
# 业务侧未来只调用这一个类：
#     AIService.chat() / vision() / image() / asr() / tts()
# 不要直接 import 具体 provider。
#
# 第一版行为：一律返回 {"status": "not_implemented", ...}
#   （provider_manager 选不到 provider 时返回 {"status": "error", ...}）

from . import provider_manager as _pm
from .providers.base import (
    CAPABILITY_CHAT,
    CAPABILITY_VISION,
    CAPABILITY_IMAGE,
    CAPABILITY_ASR,
    CAPABILITY_TTS,
    error_result,
    not_implemented,
)


class AIService:
    """多供应商 / 多模型 / 多能力的统一服务入口。

    用法（未来真实接入后不变）：
        svc = AIService()
        svc.chat(messages=[...])
        svc.vision(image=..., prompt=...)
        svc.image(prompt=...)
        svc.asr(audio=...)
        svc.tts(text=...)

    可选参数：
        provider —— 指定供应商（不传则按能力自动选型）
        model    —— 指定模型（不传则用 provider_manager 里登记的模型）
    """

    def __init__(self, manager=None):
        # 允许注入 manager（便于测试 / 后续接设置页）
        self._manager = manager or _pm.get_manager()

    # ---------- 内部：统一选型 + 分发 ----------
    def _dispatch(self, capability, prefer_provider="", model="", kwargs=None):
        """按能力选型并把请求交给对应 provider。

        返回统一结构；provider 选不到时返回 error，而不是抛异常，
        这样业务侧可以安全地「先接上、后实现」。
        """
        kwargs = dict(kwargs or {})
        prefer = [prefer_provider] if prefer_provider else None

        pkey, reg_model = self._manager.resolve(capability, prefer=prefer)
        if not pkey:
            return error_result(
                provider=prefer_provider or "",
                capability=capability,
                message=f"没有可用于 {capability} 的供应商（provider_manager 未登记）",
            )

        provider = self._manager.get_provider(pkey)
        if provider is None:
            return error_result(
                provider=pkey,
                capability=capability,
                message=f"未知供应商: {pkey}",
            )

        # 显式传入的 model 优先于登记表里的 model
        use_model = model or reg_model

        # 第一版：所有 provider 的五个能力位都返回 not_implemented。
        # 这里仍走真实分发，保证后续 provider 实现后无需改业务代码。
        handler = {
            CAPABILITY_CHAT: provider.chat,
            CAPABILITY_VISION: provider.vision,
            CAPABILITY_IMAGE: provider.image,
            CAPABILITY_ASR: provider.asr,
            CAPABILITY_TTS: provider.tts,
        }.get(capability)

        if handler is None:
            return error_result(
                provider=pkey,
                capability=capability,
                message=f"未知能力位: {capability}",
            )

        try:
            result = handler(model=use_model, **kwargs)
        except Exception as e:
            # 第一版 provider 不该抛错；这里兜住，避免影响调用方
            return error_result(provider=pkey, capability=capability, message=f"provider 调用异常: {e}")

        # 补齐选型信息，方便调用方排查
        if isinstance(result, dict):
            result.setdefault("provider", pkey)
            result.setdefault("capability", capability)
            if use_model:
                result.setdefault("model", use_model)
            return result

        # provider 返回了非 dict（异常情况）→ 归一化
        return not_implemented(pkey, capability)

    # ---------- 五个能力位 ----------
    def chat(self, messages=None, provider="", model="", **kwargs):
        """对话。messages 为 OpenAI 风格的消息数组。"""
        return self._dispatch(
            CAPABILITY_CHAT,
            prefer_provider=provider,
            model=model,
            kwargs={"messages": messages or [], **kwargs},
        )

    def vision(self, image=None, prompt="", provider="", model="", **kwargs):
        """识图：给一张图（路径/URL/base64）+ 提示词，返回理解结果。"""
        return self._dispatch(
            CAPABILITY_VISION,
            prefer_provider=provider,
            model=model,
            kwargs={"image": image, "prompt": prompt, **kwargs},
        )

    def image(self, prompt="", provider="", model="", **kwargs):
        """生图：给提示词，返回图片（第一版未实现）。"""
        return self._dispatch(
            CAPABILITY_IMAGE,
            prefer_provider=provider,
            model=model,
            kwargs={"prompt": prompt, **kwargs},
        )

    def asr(self, audio=None, provider="", model="", **kwargs):
        """语音识别：音频 → 文本。"""
        return self._dispatch(
            CAPABILITY_ASR,
            prefer_provider=provider,
            model=model,
            kwargs={"audio": audio, **kwargs},
        )

    def tts(self, text="", provider="", model="", **kwargs):
        """语音合成：文本 → 音频。"""
        return self._dispatch(
            CAPABILITY_TTS,
            prefer_provider=provider,
            model=model,
            kwargs={"text": text, **kwargs},
        )

    # ---------- 只读查询（供 UI / 调试） ----------
    @property
    def manager(self):
        return self._manager

    def capabilities(self):
        """返回各能力位的可用供应商（不发起网络请求）。"""
        out = {}
        for cap in (CAPABILITY_CHAT, CAPABILITY_VISION, CAPABILITY_IMAGE, CAPABILITY_ASR, CAPABILITY_TTS):
            selected, _model = self._manager.resolve(cap)
            available = []
            for k in self._manager.list_providers():
                p = self._manager.get_provider(k)
                if p is not None and p.supports(cap):
                    available.append(k)
            out[cap] = {"selected": selected, "available": available}
        return out

    def describe(self):
        return self._manager.describe()
