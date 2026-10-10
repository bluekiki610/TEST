# services/providers/qwen.py
# 通义千问 Qwen provider —— V1.1 Step 1：仅骨架，不发起真实请求

from .base import (
    BaseProvider,
    CAPABILITY_CHAT,
    CAPABILITY_VISION,
    CAPABILITY_IMAGE,
    not_implemented,
)


class QwenProvider(BaseProvider):
    key = "qwen"
    name = "通义千问 Qwen"

    # Step 5B：已真实实现的能力位 —— 目前为空（Step 6 才接真实调用）
    implemented_capabilities = []
    planned_capabilities = [CAPABILITY_CHAT, CAPABILITY_VISION, CAPABILITY_IMAGE]

    def chat(self, messages=None, model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实对话请求
        return not_implemented(self.key, CAPABILITY_CHAT)

    def vision(self, image=None, prompt="", model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实视觉理解请求
        return not_implemented(self.key, CAPABILITY_VISION)

    def image(self, prompt="", model="", **kwargs):
        # TODO(V1.1 Step 2+): 接入真实文生图请求
        return not_implemented(self.key, CAPABILITY_IMAGE)
