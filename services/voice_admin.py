# services/voice_admin.py
# 管理员声音 / 角色配置接口 —— V1.1 Step 6C 修正版
#
# 这一层是给未来后台「AI Studio」用的**业务接口**，不注册任何 HTTP 路由
# （保持旁路，不碰 main.py / ext_*）。
#
# ==================== 它管理的是三层资产 ====================
#     World Template           world_manager
#          ↓
#     Character Template       character_manager  ──voice_asset_id──┐
#          ↓                                                        │
#     Voice Library            voice_library_manager  ←────────────┘
#
# 管理员典型流程（对应你最终目标）：
#     1. 建世界            set_world("otome_a", ...)
#     2. 做声音资产        create_voice_asset(...)  或  clone_voice_asset(...)
#     3. 建角色并绑声音    set_character(...) → bind_voice_asset(...)
#     4. 把角色登记进世界  add_character_to_world(...)
#     5. 试听             preview(...)
#
# 之后任何用户：
#     AIService().tts(text="晚上好", character_id="nightchen")   ← 无需 voice_id / 无需克隆

from .character_manager import get_character_manager, TYPE_TEMPLATE, TYPE_CUSTOM
from .voice_library_manager import get_voice_library_manager
from .voice_clone_manager import get_voice_clone_manager
from .world_manager import get_world_manager


class VoiceAdminService:
    """管理员侧的世界 / 角色 / 声音资产管理。"""

    def __init__(self, world_manager=None, character_manager=None,
                 voice_library=None, clone_manager=None):
        self._wm = world_manager
        self._cm = character_manager
        self._vl = voice_library
        self._cloner = clone_manager

    # ---------- 依赖 ----------
    @property
    def worlds(self):
        if self._wm is None:
            self._wm = get_world_manager()
        return self._wm

    @property
    def characters(self):
        if self._cm is None:
            self._cm = get_character_manager()
        return self._cm

    @property
    def library(self):
        if self._vl is None:
            self._vl = get_voice_library_manager()
        return self._vl

    @property
    def cloner(self):
        if self._cloner is None:
            self._cloner = get_voice_clone_manager()
        return self._cloner

    # ==================== 世界 ====================
    def create_world(self, world_id, name="", allow_custom_characters=True, **kwargs):
        """创建/更新世界模板。

        allow_custom_characters —— 你现在测试环境设 True（允许好友创建），
        未来官方世界设 False（只保留固定男主）。
        """
        ok, w = self.worlds.set_world(
            world_id, name=name, allow_custom_characters=allow_custom_characters, **kwargs
        )
        return {"status": "ok" if ok else "error", "world": w,
                "error": "" if ok else "写入失败（权限或磁盘问题）"}

    def list_worlds(self):
        return {"status": "ok", "worlds": self.worlds.list_worlds()}

    def add_character_to_world(self, world_id, character_id):
        ok = self.worlds.add_character_to_world(world_id, character_id)
        return {"status": "ok" if ok else "error", "error": "" if ok else "世界不存在或写入失败"}

    # ==================== 声音资产库 ====================
    def list_voice_assets(self):
        return {"status": "ok", "library": self.library.describe()}

    def create_voice_asset(self, name="", provider="", voice_id="",
                           voice_type="cloned", model="", locked=True):
        """手动登记一个已有 voice_id 的声音资产（例如在 ElevenLabs 网站上克隆好的）。"""
        if not provider:
            return {"status": "error", "error": "provider 不能为空"}
        try:
            ok, asset = self.library.add_voice(
                name=name, provider=provider, voice_id=voice_id,
                voice_type=voice_type, model=model, locked=locked,
            )
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        if not ok:
            return {"status": "error", "error": "写入失败（权限、磁盘或 id 冲突）"}
        return {"status": "ok", "voice_asset": asset}

    def clone_voice_asset(self, audio_file, name="", provider="elevenlabs",
                          user="", model="", retain=False, duration=0,
                          account_manager=None):
        """上传样本 → 克隆 → **只建声音资产**（不绑定角色）。

        适合"先备好一批声音，再分配给角色"的工作流。
        """
        result = self.cloner.clone_voice(
            user=user, ai_name=name, audio_file=audio_file, provider=provider,
            model=model, label=name, retain=retain, duration=duration,
            account_manager=account_manager,
        )
        if result.get("status") != "ok":
            return result
        obj = result.get("voice_object") or {}
        try:
            ok, asset = self.library.add_voice(
                name=name or obj.get("label", ""), provider=obj.get("provider", ""),
                voice_id=obj.get("voice_id", ""), voice_type=obj.get("voice_type", "cloned"),
                model=obj.get("model", ""),
                extra={"source_audio": obj.get("source_audio")} if obj.get("source_audio") else None,
            )
        except ValueError as e:
            return {"status": "error", "error": str(e), "clone": result}
        if not ok:
            return {"status": "error", "error": "声音资产写入失败", "clone": result}
        return {"status": "ok", "voice_asset": asset, "clone": result}

    def delete_voice_asset(self, voice_asset_id, force=False):
        """删除声音资产。默认会先检查是否有角色在引用。"""
        users = self.characters.characters_using_voice(voice_asset_id)
        if users and not force:
            return {"status": "error",
                    "error": f"仍有角色引用该声音资产，无法删除：{', '.join(users)}",
                    "used_by": users}
        ok = self.library.remove_voice(voice_asset_id)
        return {"status": "ok" if ok else "error", "used_by": users,
                "error": "" if ok else "资产不存在或写入失败"}

    # ==================== 角色 + 绑定 ====================
    def list_characters(self, world_id=None, character_type=None):
        return {"status": "ok",
                "characters": self.characters.list_characters(world_id=world_id,
                                                              character_type=character_type)}

    def create_character(self, character_id, name="", character_type=TYPE_TEMPLATE,
                         voice_asset_id="", world_id="", personality="",
                         appearance="", system_prompt="", owner="", **kwargs):
        """创建角色模板。可选直接指定 voice_asset_id（只存引用）。"""
        try:
            ok, c = self.characters.set_character(
                character_id, name=name, character_type=character_type,
                voice_asset_id=voice_asset_id, world_id=world_id,
                personality=personality, appearance=appearance,
                system_prompt=system_prompt, owner=owner, **kwargs
            )
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        if not ok:
            return {"status": "error", "error": "写入失败（权限或磁盘问题）"}
        return {"status": "ok", "character": c}

    def bind_character_voice(self, character_id, voice_asset_id):
        """把声音资产绑定到角色（角色只存 voice_asset_id，不复制 voice_id）。"""
        ok, res = self.characters.bind_voice_asset(character_id, voice_asset_id)
        if not ok:
            return {"status": "error", "error": res if isinstance(res, str) else "绑定失败"}
        return {"status": "ok", "character": res}

    def unbind_character_voice(self, character_id):
        ok, c = self.characters.clear_voice_asset(character_id)
        return {"status": "ok" if ok else "error", "character": c}

    def get_character_voice(self, character_id):
        """查看某个角色最终会用什么声音（完整解析一遍链路）。"""
        c = self.characters.resolve(character_id)
        if not c:
            return {"status": "error", "error": f"角色不存在: {character_id}"}
        asset_id = (c.get("voice_asset_id") or "").strip()
        asset = self.library.get_voice(asset_id) if asset_id else None
        return {
            "status": "ok",
            "character_id": c.get("character_id"),
            "name": c.get("name"),
            "character_type": c.get("character_type"),
            "voice_asset_id": asset_id,
            "voice_asset": asset,
            "configured": bool(asset and asset.get("provider")),
        }

    # ==================== 试听 ====================
    def preview(self, character_id, text="你好，我是这个世界里的角色。",
                user="", account_manager=None):
        """用该角色当前配置的声音合成一小段，供管理员试听。"""
        from .ai_service import AIService
        info = self.get_character_voice(character_id)
        if not info.get("configured"):
            return {"status": "error", "error": f"角色「{character_id}」还没有配置声音",
                    "detail": info}
        svc = AIService(account_manager=account_manager)
        result = svc.tts(text=text, character_id=character_id, user=user)
        if isinstance(result, dict):
            result["previewed_character"] = character_id
            result["voice_asset"] = info.get("voice_asset")
        return result

    # ==================== 隐私：上传样本管理 ====================
    def list_samples(self):
        return {"status": "ok", "samples": self.cloner.list_retained_samples()}

    def delete_sample(self, filename):
        ok = self.cloner.delete_retained_sample(filename)
        return {"status": "ok" if ok else "error"}

    def describe(self):
        return {
            "worlds": self.worlds.describe(),
            "characters": self.characters.describe(),
            "voice_library": self.library.describe(),
            "clone": self.cloner.describe(),
        }


_default_service = None


def get_voice_admin_service():
    global _default_service
    if _default_service is None:
        _default_service = VoiceAdminService()
    return _default_service


def set_voice_admin_service(svc):
    global _default_service
    _default_service = svc
    return _default_service
