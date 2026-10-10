# services/providers/voicestudio.py
# VoiceStudio 本地 TTS provider —— V1.1 Step 6C 修正版
#
# ==================== 定位 ====================
# 本地声音引擎，用于**降低成本**：
#
#     免费/低成本层          VoiceStudio（本机 GPU）
#         适合：大量普通用户 / NPC / 无限聊天
#
#     高端层                 ElevenLabs / MiniMax
#         适合：VIP / 官方男主 / 高价值角色
#
# 这就是声音的分层策略：80% 走本地，20% 走云端精品，
# 成本模型才健康（否则每句话都调云端会爆）。
#
# ==================== 为什么现在只写接口 ====================
# 按审核意见：**先做好 Voice Asset + Binding + Override 层，再换引擎**。
# 只要 provider 抽象正确，接本地引擎只是换一个 Provider。
#
# 而且 VoiceStudio 的真实协议取决于你最终选哪个项目
# （GPT-SoVITS / CosyVoice 本地部署 / Fish Speech …），端点与参数各不相同。
# 在这里凭空写一个端点，就是"写了但从没跑通"的代码。
#
# 因此本文件**只做两件事**：
#   1. 把 VoiceStudio 注册进 Provider 体系（选型、describe、UI 都能看到它）
#   2. 明确声明"协议待接入"，绝不假装可用
#
# 接法（未来）：实现下面的 tts()，把 text + voice_id POST 给本地服务即可。
#
# 部署形态（你描述的）：
#     小世界服务器 → VoiceProvider → VoiceStudio GPU → 生成声音
#   base_url 指向本机/内网地址，例如 http://127.0.0.1:9880

from .base import (
    BaseProvider,
    CAPABILITY_TTS,
    not_implemented,
)

# 本地服务默认地址（未来按实际部署改 base_url 即可）
DEFAULT_BASE_URL = "http://127.0.0.1:9880"


class VoiceStudioProvider(BaseProvider):
    """本地 VoiceStudio 声音引擎。

    与其他 provider 完全并列 —— 上层 AIService / 声音库 / 角色绑定
    **不需要知道**某个角色用的是本地还是云端引擎。
    """

    key = "voicestudio"
    name = "VoiceStudio（本地）"

    default_base_url = DEFAULT_BASE_URL
    default_model = ""

    # Step 5B：implemented_capabilities 只写"真的实现了"的能力。
    #   本地引擎尚未接入真实协议 → 留空，避免绕过 not_implemented 保护。
    implemented_capabilities = []
    # 计划支持（仅展示，不参与选型）
    planned_capabilities = [CAPABILITY_TTS]

    # 本地引擎通常不需要 api_key（走内网），但接口保持一致
    def is_configured(self):
        return True

    def tts(self, text="", model="", voice_id="", timeout=60, **kwargs):
        """本地语音合成。

        TODO(VoiceStudio 接入时实现)：
            POST {base_url}/tts  (或你所选引擎的实际端点)
            body: {"text": ..., "voice_id": ..., "model": ...}
            → 音频字节 → ok_audio_result(...)

        参数约定与云端 provider 完全一致（text / model / voice_id），
        因此换上真实实现后，上层一行都不用改。
        """
        return not_implemented(self.key, CAPABILITY_TTS)
