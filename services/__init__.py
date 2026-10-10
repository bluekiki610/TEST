# services/__init__.py
# AI 能力服务层 —— V1.1 Step 1：仅建立架构骨架
#
# 本包**不参与**现有聊天链路：
#   main.py 的 load_extensions() 只扫描 ext/*.py（ext_loader.py 只扫描 ext/*.js），
#   不会自动导入 services/，因此新增本包对现有运行行为零影响。
#
# 约定：
#   业务代码只调用 AIService 的 chat/vision/image/asr/tts，
#   不要直接 import 具体供应商模块。

__all__ = ["ai_service", "provider_manager", "providers"]
