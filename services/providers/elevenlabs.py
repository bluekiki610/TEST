# services/providers/elevenlabs.py
# ElevenLabs provider —— V1.1 Step 1：仅骨架，不发起真实请求
#
# 说明：ElevenLabs 主打语音合成（TTS），可选语音识别（ASR），不做对话/视觉/生图。

from .base import (
    BaseProvider,
    CAPABILITY_TTS,
    CAPABILITY_ASR,
    not_implemented,
)


class ElevenLabsProvider(BaseProvider):
    key = "elevenlabs"
    name = "ElevenLabs"

    # Step 5B：已真实实现的能力位 —— 目前为空（Step 6 才接真实调用）
    implemented_capabilities = []
    planned_capabilities = [CAPABILITY_TTS, CAPABILITY_ASR]

    def tts(self, text="", model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实语音合成请求
        return not_implemented(self.key, CAPABILITY_TTS)

    def asr(self, audio=None, model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实语音识别请求
        return not_implemented(self.key, CAPABILITY_ASR)
