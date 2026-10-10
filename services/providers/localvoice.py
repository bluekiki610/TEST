# services/providers/localvoice.py
# 本地声音引擎 provider —— V1.1 Step 6D
#
# ==================== 为什么不叫 voicestudio ====================
# 本地引擎**不是**一个具体软件，而是一个类别：
#     GPT-SoVITS / CosyVoice / Fish Speech / VoiceStudio …
# 把 provider 绑死在 VoiceStudio 上，将来换引擎就要改上层。
#
# 因此：
#     provider = "localvoice"      ← 稳定标识（上层只认这个）
#     engine   = "voicestudio"     ← 具体引擎（可换，写在声音资产里）
#
# 声音资产例子：
#     {
#       "id": "voice_nightchen_v1",
#       "provider": "localvoice",
#       "engine": "gpt_sovits",       ← 换引擎只改这一处
#       "voice_id": "nightchen_zh"
#     }
#
# 统一接口与云端 provider 完全一致：
#     tts(text, voice_id, model)
#
# ==================== 为什么现在只写接口 ====================
# 每个本地引擎的端点/参数都不同（GPT-SoVITS 是 /tts 或 api_v2，
# CosyVoice 是 /inference_sft，Fish Speech 是 /v1/tts …），
# 在选型确定前写死任何一个都是"从没跑通的代码"。
#
# 本文件只做：
#   1. 注册进 Provider 体系（选型 / describe / UI 都能看到）
#   2. 支持按 engine 选择（引擎名进日志，便于将来分派）
#   3. 如实声明未接入

from .base import (
    BaseProvider,
    CAPABILITY_TTS,
    not_implemented,
)

# 本地服务默认地址（未来按实际部署改 base_url）
DEFAULT_BASE_URL = "http://127.0.0.1:9880"

# 未来要支持的本地引擎（仅登记，未接入任何协议）
SUPPORTED_ENGINES = (
    "voicestudio",
    "gpt_sovits",
    "cosyvoice",
    "fish_speech",
)


class LocalVoiceProvider(BaseProvider):
    """本地声音引擎（引擎无关）。

    与云端 provider 完全并列 —— 上层 AIService / 声音库 / 角色绑定
    **不需要知道**某个角色用的是本地还是云端。
    """

    key = "localvoice"
    name = "本地声音引擎"

    default_base_url = DEFAULT_BASE_URL
    default_model = ""

    # Step 5B：implemented_capabilities 只写"真的实现了"的能力。
    #   本地引擎尚未接入真实协议 → 留空，避免绕过 not_implemented 保护。
    implemented_capabilities = []
    planned_capabilities = [CAPABILITY_TTS]

    # 本地引擎通常不需要 api_key（走内网），接口保持一致即可
    def is_configured(self):
        return True

    def engine_of(self, engine=""):
        """解析本次要用哪个本地引擎。

        传入的 engine 优先；没有则退回本地服务默认引擎。
        仅用于日志与将来分派，不影响接口形状。
        """
        return (engine or "voicestudio").strip() or "voicestudio"

    def tts(self, text="", model="", voice_id="", engine="", timeout=60, **kwargs):
        """本地语音合成。

        TODO(本地引擎接入时实现)：按 self.engine_of(engine) 分派到具体引擎：

            gpt_sovits  → POST {base_url}/tts        {"text","ref_audio_path",...}
            cosyvoice   → POST {base_url}/inference_sft
            fish_speech → POST {base_url}/v1/tts
            voicestudio → POST {base_url}/tts

        参数约定与云端 provider 完全一致（text / model / voice_id / engine），
        因此换上真实实现后，上层一行都不用改。
        """
        return not_implemented(self.key, CAPABILITY_TTS)
