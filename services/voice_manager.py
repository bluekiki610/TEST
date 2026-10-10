# services/voice_manager.py
# ⚠️ 已废弃（V1.1 Step 6C 修正版）
#
# ==================== 这个模块曾经是什么 ====================
# 6A 时把声音当作**用户资产**存在 data/ai_voice_profiles.json：
#
#     user → ai_account → voice_profile          ❌ 方向错误
#
# 6C 第一版改成挂在角色名下（world_voice_profiles.json），仍然不够：
# 声音应该是**可复用的世界资产**，角色只引用它。
#
# ==================== 现在正确的层级 ====================
#     World Template            world_manager.py
#          ↓
#     Character Template        character_manager.py   ──voice_asset_id──┐
#          ↓                                                             │
#     Character Runtime         （未来：关系 / 记忆 / 对话）              │
#                                                                        │
#     Voice Library             voice_library_manager.py  ←──────────────┘
#
# AIService.tts() 走的是 character_manager → voice_library_manager，
# **不再引用本文件**。
#
# ==================== 本文件现在的状态 ====================
# 保留为兼容转发层，只做一件事：把旧的导入名字指向 CharacterManager，
# 避免还有谁 import 旧名字时报错。调用它会打印废弃警告。
#
# 它不产生也不读取任何自己的数据文件。旧文件可直接删除：
#     data/ai_voice_profiles.json
#     data/world_voice_profiles.json
#
# 如需彻底清理：删掉本文件（services/ 之外零引用）。

from .character_manager import (  # noqa: F401
    CharacterManager,
    get_character_manager,
    set_character_manager,
    TYPE_TEMPLATE,
    TYPE_CUSTOM,
)

# 旧类名别名（历史遗留；请改用 CharacterManager）
VoiceProfileManager = CharacterManager
WorldVoiceManager = CharacterManager

_DEPRECATED_MSG = ("[voice_manager] ⚠️ 已废弃：声音现在是可复用资产，"
                   "请改用 voice_library_manager（资产库）+ character_manager（角色引用）")


def get_voice_manager(path=None):
    """⚠️ 已废弃：请改用 character_manager / voice_library_manager。"""
    print(_DEPRECATED_MSG, flush=True)
    return get_character_manager(path=path)


def set_voice_manager(mgr):
    """⚠️ 已废弃：请改用 character_manager.set_character_manager()。"""
    print(_DEPRECATED_MSG, flush=True)
    return set_character_manager(mgr)
