# services/providers/deepseek.py
# DeepSeek provider —— V1.1 Step 1：仅骨架，不发起真实请求

from .base import (
    BaseProvider,
    CAPABILITY_CHAT,
    CAPABILITY_VISION,
    not_implemented,
)


class DeepSeekProvider(BaseProvider):
    key = "deepseek"
    name = "DeepSeek"

    # 本期计划支持的能力（尚未接入真实请求）
    def capabilities(self):
        return [CAPABILITY_CHAT, CAPABILITY_VISION]

    def chat(self, messages=None, model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实 chat completions 请求
        return not_implemented(self.key, CAPABILITY_CHAT)

    def vision(self, image=None, prompt="", model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实视觉理解请求
        return not_implemented(self.key, CAPABILITY_VISION)
