# services/providers/minimax.py
# MiniMax provider —— V1.1 Step 6B
#
# 能力位现状（implemented_capabilities 才是唯一选型依据）：
#   chat  ❌ 未接
#   tts   ❌ 真实协议尚未接入（6A-2 待做）
#   asr   ❌ 未接
# 克隆能力：
#   supports_clone = True      供应商业务上支持声音克隆（中文自然）
#   clone_implemented = False  我们**尚未**接入其真实端点/参数
#
# 与 ElevenLabs 同理：未核实的端点不写进代码，只声明能力并明确返回"协议待接入"。

from .base import (
    BaseProvider,
    CAPABILITY_CHAT,
    CAPABILITY_TTS,
    CAPABILITY_ASR,
    not_implemented,
)
from .voice_clone import VoiceCloneProvider


class MiniMaxProvider(BaseProvider, VoiceCloneProvider):
    key = "minimax"
    name = "MiniMax"

    # 供应商必须有自己的端点（禁止跨供应商串用 URL）
    default_base_url = "https://api.minimax.chat"

    # Step 5B：已真实实现的能力位 —— 目前为空（TTS 在 6A-2 接）
    implemented_capabilities = []
    planned_capabilities = [CAPABILITY_CHAT, CAPABILITY_TTS, CAPABILITY_ASR]

    # ---- 克隆能力（Step 6B）----
    supports_clone = True          # 供应商业务上支持（中文表现好）
    clone_implemented = False      # 真实协议待接入
    clone_note = "待接入：需核对 Voice Clone 端点、GroupId 参数与文件上传字段"

    def chat(self, messages=None, model="", **kwargs):
        # TODO: 接入真实对话请求
        return not_implemented(self.key, CAPABILITY_CHAT)

    def tts(self, text="", model="", voice_id="", **kwargs):
        # TODO(6A-2): 接入真实语音合成请求
        return not_implemented(self.key, CAPABILITY_TTS)

    def asr(self, audio=None, model="", **kwargs):
        # TODO: 接入真实语音识别请求
        return not_implemented(self.key, CAPABILITY_ASR)

    # clone_voice 未覆盖 —— 继承 VoiceCloneProvider 的版本，
    # 会因 supports_clone=True 自动返回"协议待接入"。
