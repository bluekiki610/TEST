# services/world_voice_manager.py
# ⚠️ 已废弃（Step 6C 修正版）
#
# ==================== 为什么废弃 ====================
# 6C 第一版把声音直接挂在角色名下（world_voice_profiles.json）：
#
#     World → AI Character → voice_profile
#
# 产品方向确认后修正为「角色模板 + 声音资产库」两层：
#
#     World Template
#          ↓
#     Character Template  ──voice_asset_id──→  Voice Library
#          ↓
#     Character Runtime（关系 / 记忆 / 对话）
#
# 好处：换供应商或换音色时**只改声音库一处**，所有角色与世界自动跟随；
#       角色模板里不复制 voice_id，世界复制时不会产生漂移。
#
# 因此功能迁移到：
#     services/character_manager.py       （角色模板，存 voice_asset_id）
#     services/voice_library_manager.py   （声音资产库，存 voice_id）
#
# AIService.tts() 现在走 character_manager → voice_library_manager，
# **不再引用本文件**。
#
# ==================== 本文件现在的状态 ====================
# 保留为兼容转发层：把旧类名指到新的 CharacterManager，
# 避免还有谁 import 旧名字时报错。它不再产生/读取自己的数据文件。
#
# 如需彻底清理：删掉本文件，以及旧的 data/world_voice_profiles.json。

from .character_manager import (  # noqa: F401
    CharacterManager,
    get_character_manager,
    set_character_manager,
    TYPE_TEMPLATE,
    TYPE_CUSTOM,
)

# 旧类名别名（历史遗留；请改用 CharacterManager）
WorldVoiceManager = CharacterManager

_DEPRECATED_MSG = ("[world_voice_manager] ⚠️ 已废弃：声音现在是可复用资产，"
                   "请改用 voice_library_manager + character_manager")


def get_world_voice_manager(path=None):
    """⚠️ 已废弃：请改用 character_manager.get_character_manager()。"""
    print(_DEPRECATED_MSG, flush=True)
    return get_character_manager(path=path)


def set_world_voice_manager(mgr):
    """⚠️ 已废弃：请改用 character_manager.set_character_manager()。"""
    print(_DEPRECATED_MSG, flush=True)
    return set_character_manager(mgr)
