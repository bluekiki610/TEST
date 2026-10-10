# services/providers/minimax.py
# MiniMax provider —— V1.1 Step 1：仅骨架，不发起真实请求

from .base import (
    BaseProvider,
    CAPABILITY_CHAT,
    CAPABILITY_TTS,
    CAPABILITY_ASR,
    not_implemented,
)


class MiniMaxProvider(BaseProvider):
    key = "minimax"
    name = "MiniMax"

    # Step 5B：已真实实现的能力位 —— 目前为空（Step 6 才接真实调用）
    implemented_capabilities = []
    planned_capabilities = [CAPABILITY_CHAT, CAPABILITY_TTS, CAPABILITY_ASR]

    def chat(self, messages=None, model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实对话请求
        return not_implemented(self.key, CAPABILITY_CHAT)

    def tts(self, text="", model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实语音合成请求
        return not_implemented(self.key, CAPABILITY_TTS)

    def asr(self, audio=None, model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实语音识别请求
        return not_implemented(self.key, CAPABILITY_ASR)
