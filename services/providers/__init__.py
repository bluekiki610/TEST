# services/providers/__init__.py
# 供应商 provider 集合 —— V1.1 Step 6B
#
# 每个 provider 都继承 services.providers.base.BaseProvider，
# 统一实现 chat / vision / image / asr / tts 五个能力位。
#
# 支持声音克隆的 provider 额外继承 voice_clone.VoiceCloneProvider（mixin），
# 通过 supports_clone / clone_implemented 两个标志位区分
# 「供应商能不能克隆」与「我们接没接真实协议」。

from .base import BaseProvider, CAPABILITIES  # noqa: F401
from .deepseek import DeepSeekProvider
from .minimax import MiniMaxProvider
from .qwen import QwenProvider
from .zhipu import ZhipuProvider
from .volcano import VolcanoProvider
from .elevenlabs import ElevenLabsProvider
from .siliconflow import SiliconFlowProvider
from .voicestudio import VoiceStudioProvider
from .voice_clone import (  # noqa: F401
    VoiceCloneProvider,
    build_voice_object,
    clone_ok,
    clone_fail,
    clone_not_supported,
    clone_pending,
    VOICE_TYPE_PRESET,
    VOICE_TYPE_CLONED,
)

# provider key -> 类。key 与 provider_manager 里的配置键一致。
PROVIDER_CLASSES = {
    "deepseek": DeepSeekProvider,
    "minimax": MiniMaxProvider,
    "qwen": QwenProvider,
    "zhipu": ZhipuProvider,
    "volcano": VolcanoProvider,
    "elevenlabs": ElevenLabsProvider,
    "siliconflow": SiliconFlowProvider,
    "voicestudio": VoiceStudioProvider,
}

__all__ = [
    "BaseProvider",
    "CAPABILITIES",
    "PROVIDER_CLASSES",
    "DeepSeekProvider",
    "MiniMaxProvider",
    "QwenProvider",
    "ZhipuProvider",
    "VolcanoProvider",
    "ElevenLabsProvider",
    "SiliconFlowProvider",
    "VoiceStudioProvider",
    "VoiceCloneProvider",
    "build_voice_object",
    "clone_ok",
    "clone_fail",
    "clone_not_supported",
    "clone_pending",
    "VOICE_TYPE_PRESET",
    "VOICE_TYPE_CLONED",
]
