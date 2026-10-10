# services/providers/voicestudio.py
# ⚠️ 已改名为 localvoice.py（V1.1 Step 6D）
#
# ==================== 为什么改名 ====================
# 本地引擎**不是**一个具体软件，而是一个类别：
#     GPT-SoVITS / CosyVoice / Fish Speech / VoiceStudio
#
# 把 provider 绑死在 VoiceStudio 上，将来换引擎就要改上层。
# 因此拆成两个概念：
#     provider = "localvoice"    ← 稳定标识，上层只认这个
#     engine   = "voicestudio"   ← 具体引擎，写在声音资产里，可换
#
# ==================== 本文件现在的状态 ====================
# 兼容转发层：把旧类名指到 LocalVoiceProvider，避免旧配置/旧 import 报错。
#
# 仍需注意：如果你的声音资产里写了 provider="voicestudio"，
# 请改成：
#     "provider": "localvoice",
#     "engine":   "voicestudio"
# 否则选型时找不到该 provider。
#
# 如需彻底清理：删掉本文件（services/ 之外零引用）。

from .localvoice import LocalVoiceProvider, SUPPORTED_ENGINES, DEFAULT_BASE_URL  # noqa: F401

# 旧类名别名（历史遗留；请改用 LocalVoiceProvider）
VoiceStudioProvider = LocalVoiceProvider
