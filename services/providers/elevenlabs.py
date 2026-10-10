# services/providers/elevenlabs.py
# ElevenLabs provider —— V1.1 Step 6B
#
# 能力位现状（implemented_capabilities 才是唯一选型依据）：
#   tts   ❌ 真实协议尚未接入（6A-2 待做）
#   asr   ❌ 未接
# 克隆能力：
#   supports_clone = True      供应商业务上支持声音克隆（成熟）
#   clone_implemented = False  我们**尚未**接入其真实端点/参数
#
# 为什么不直接写 clone_voice 的真实实现：
#   ElevenLabs 的 TTS 与 Voice Clone 端点、鉴权头、multipart 字段名
#   我**无法在本地验证**（本项目环境 shell 不可用，也没有官方文档核对）。
#   把未核实的端点写进代码，就是"写了但从没跑通"的代码 ——
#   所以这里只声明能力、明确返回"协议待接入"，等核对后再补。

from .base import (
    BaseProvider,
    CAPABILITY_TTS,
    CAPABILITY_ASR,
    not_implemented,
)
from .voice_clone import VoiceCloneProvider


class ElevenLabsProvider(BaseProvider, VoiceCloneProvider):
    key = "elevenlabs"
    name = "ElevenLabs"

    # 与 ext_ai.py 的 PROVIDERS 命名习惯保持一致（供应商必须有自己的端点）
    default_base_url = "https://api.elevenlabs.io"

    # Step 5B：已真实实现的能力位 —— 目前为空（TTS 在 6A-2 接）
    implemented_capabilities = []
    planned_capabilities = [CAPABILITY_TTS, CAPABILITY_ASR]

    # ---- 克隆能力（Step 6B）----
    supports_clone = True          # 供应商业务上支持（克隆成熟、多语言好）
    clone_implemented = False      # 真实协议待接入
    clone_note = "待接入：需核对 Voice Clone 端点、鉴权头与 multipart 字段名"

    def tts(self, text="", model="", voice_id="", **kwargs):
        # TODO(6A-2): 接入真实语音合成请求（端点为 /v1/text-to-speech/{voice_id}）
        return not_implemented(self.key, CAPABILITY_TTS)

    def asr(self, audio=None, model="", **kwargs):
        # TODO: 接入真实语音识别请求
        return not_implemented(self.key, CAPABILITY_ASR)

    # clone_voice 未覆盖 —— 继承 VoiceCloneProvider 的版本，
    # 会因 supports_clone=True 自动返回"协议待接入"，而不是假装"不支持克隆"。
