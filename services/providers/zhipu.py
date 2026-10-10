# services/providers/zhipu.py
# 智谱 GLM provider —— V1.1 Step 1：仅骨架，不发起真实请求

from .base import (
    BaseProvider,
    CAPABILITY_CHAT,
    CAPABILITY_VISION,
    not_implemented,
)


class ZhipuProvider(BaseProvider):
    key = "zhipu"
    name = "智谱 GLM"

    def capabilities(self):
        return [CAPABILITY_CHAT, CAPABILITY_VISION]

    def chat(self, messages=None, model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实对话请求
        return not_implemented(self.key, CAPABILITY_CHAT)

    def vision(self, image=None, prompt="", model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实视觉理解请求
        return not_implemented(self.key, CAPABILITY_VISION)
