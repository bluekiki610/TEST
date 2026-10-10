# services/providers/siliconflow.py
# 硅基流动 SiliconFlow provider —— V1.1 Step 1：仅骨架，不发起真实请求
#
# 说明：硅基流动同时提供对话、视觉、文生图、语音合成与语音识别能力，
# 因此五个能力位都声明，真实接入时按需覆写。
# 本项目现有代码里已经在用它（ext_ai.py 的 PROVIDERS 表、
# ext_mem.py 的 /api/tts 走 api.siliconflow.cn），本文件只是把它纳入统一服务层。

from .base import (
    BaseProvider,
    CAPABILITY_CHAT,
    CAPABILITY_VISION,
    CAPABILITY_IMAGE,
    CAPABILITY_ASR,
    CAPABILITY_TTS,
    not_implemented,
)


class SiliconFlowProvider(BaseProvider):
    key = "siliconflow"
    name = "硅基流动"

    def capabilities(self):
        return [
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
