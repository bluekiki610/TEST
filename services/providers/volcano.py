# services/providers/volcano.py
# 火山引擎（豆包 / 语音）provider —— V1.1 Step 1：仅骨架，不发起真实请求
#
# 说明：火山引擎同时提供对话、视觉、语音合成与语音识别能力，
# 因此这里五个能力位都声明，真实接入时按需覆写。

from .base import (
    BaseProvider,
    CAPABILITY_CHAT,
    CAPABILITY_VISION,
    CAPABILITY_IMAGE,
    CAPABILITY_ASR,
    CAPABILITY_TTS,
    not_implemented,
)


class VolcanoProvider(BaseProvider):
    key = "volcano"
    name = "火山引擎"

    # Step 5B：已真实实现的能力位 —— 目前为空（Step 6 才接真实调用）
    implemented_capabilities = []
    planned_capabilities = [
        CAPABILITY_CHAT,
        CAPABILITY_VISION,
        CAPABILITY_IMAGE,
        CAPABILITY_ASR,
        CAPABILITY_TTS,
    ]

    def chat(self, messages=None, model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实对话请求
        return not_implemented(self.key, CAPABILITY_CHAT)

    def vision(self, image=None, prompt="", model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实视觉理解请求
        return not_implemented(self.key, CAPABILITY_VISION)

    def image(self, prompt="", model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实文生图请求
        return not_implemented(self.key, CAPABILITY_IMAGE)

    def asr(self, audio=None, model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实语音识别请求
        return not_implemented(self.key, CAPABILITY_ASR)

    def tts(self, text="", model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实语音合成请求
        return not_implemented(self.key, CAPABILITY_TTS)
