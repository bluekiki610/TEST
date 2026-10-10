# services/providers/__init__.py
# 供应商 provider 集合 —— V1.1 Step 1：仅空实现骨架，不发起任何真实请求
#
# 每个 provider 都继承 services.providers.base.BaseProvider，
# 统一实现 chat / vision / image / asr / tts 五个能力位。

from .base import BaseProvider, CAPABILITIES  # noqa: F401
from .deepseek import DeepSeekProvider
from .minimax import MiniMaxProvider
from .qwen import QwenProvider
from .zhipu import ZhipuProvider
from .volcano import VolcanoProvider
from .elevenlabs import ElevenLabsProvider
from .trajectory import TrajectoryProvider

# provider key -> 类。key 与 provider_manager 里的配置键一致。
PROVIDER_CLASSES = {
    "deepseek": DeepSeekProvider,
    "minimax": MiniMaxProvider,
    "qwen": QwenProvider,
    "zhipu": ZhipuProvider,
    "volcano": VolcanoProvider,
    "elevenlabs": ElevenLabsProvider,
    "trajectory": TrajectoryProvider,
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
    "TrajectoryProvider",
]
