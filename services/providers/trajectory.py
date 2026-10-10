# services/providers/trajectory.py
# 轨迹（trajectory）provider —— V1.1 Step 1：仅骨架，不发起真实请求
#
# 说明：本项目已有「👣 AI 行动轨迹」概念（main.py 的 trails / ext_ai 的 add_trail）。
# 这里预留一个 provider 位，用于后续把「轨迹/事件摘要」类能力也纳入统一服务层。
# 它不属于常规大模型能力，因此五个标准能力位均未声明支持。

from .base import BaseProvider


class TrajectoryProvider(BaseProvider):
    key = "trajectory"
    name = "轨迹服务"

    def capabilities(self):
        # 非标准能力位，暂不声明 chat/vision/image/asr/tts 中的任何一个
        return []
