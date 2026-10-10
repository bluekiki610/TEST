# services/voice_admin.py
# 管理员声音 / 角色配置接口 —— V1.1 Step 6C 修正版
#
# 这一层是给未来后台「AI Studio」用的**业务接口**，不注册任何 HTTP 路由
# （保持旁路，不碰 main.py / ext_*）。
#
# ==================== 它管理的是三层资产 + 一层用户覆盖 ====================
#     World Template           world_manager
#          ↓
#     Character Template       character_manager  ──default_voice_id──┐
#          ↓                                                          │
#     Voice Library            voice_library_manager  ←───────────────┘
#       ├── system 声音（管理员）
#       └── user 自定义声音（用户覆盖用）
#          ↑
#     User Override            user_character_prefs_manager
#
# 管理员典型流程（对应你最终目标）：
#     1. 建世界            create_world("otome_a", ...)
#     2. 做声音资产        create_voice_asset(...)  或  clone_voice_asset(...)
#     3. 建角色并绑声音    create_character(...) → bind_character_voice(...)
#     4. 把角色登记进世界  add_character_to_world(...)
#     5. 试听             preview(...)
#
# 之后任何用户：
#     AIService(user=...).tts(text="晚上好", character_id="nightchen")
#         ← 无需 voice_id / 无需克隆；有覆盖用覆盖，没有就用角色默认声音

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

    # ==================== 声音资产库（系统层 / 用户层） ====================
    def list_voice_assets(self):
        return {"status": "ok", "library": self.library.describe()}

    def list_system_voices(self):
        """系统声音（管理员资产，所有用户默认可选）。"""
        return {"status": "ok", "voices": self.library.list_system_voices()}

    def list_user_voices(self, owner_user=""):
        """用户自定义声音（用于覆盖）。"""
        return {"status": "ok", "voices": self.library.list_user_voices(owner_user)}

    def create_voice_asset(self, name="", provider="", voice_id="",
                           voice_type="cloned", model="", locked=True, owner="system",
                           source="", engine="", world_id=""):
        """登记一个声音资产。

        owner="system"（默认）→ 管理员系统声音（source 默认 official）
        owner="user"          → 用户自定义声音（source 默认 custom）

        engine   —— 本地引擎名（provider="localvoice" 时用：
                    gpt_sovits / cosyvoice / fish_speech / voicestudio）
        world_id —— 归属世界（多租户隔离）。留空 = 全局可用。
        """
        if not provider:
            return {"status": "error", "error": "provider 不能为空"}
        try:
            ok, asset = self.library.add_voice(
                name=name, provider=provider, voice_id=voice_id,
                voice_type=voice_type, model=model, locked=locked, owner=owner,
                source=source, engine=engine, world_id=world_id,
            )
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        if not ok:
            return {"status": "error", "error": "写入失败（权限、磁盘或 id 冲突）"}
        return {"status": "ok", "voice_asset": asset}

    def create_user_voice_asset(self, user, name="", provider="", voice_id="",
                                voice_type="cloned", model="", engine="", world_id=""):
        """用户创建自己的声音资产（用于覆盖听感）。

        ⚠️ 边界（Step 6D）：这**不会**改变任何角色的官方默认声音，
        只影响该用户自己听到什么。要改官方声音必须走 change_character_default_voice。
        """
        if not user:
            return {"status": "error", "error": "缺少 user"}
        try:
            ok, asset = self.library.add_voice(
                name=name or f"{user} 的自定义声音", provider=provider,
                voice_id=voice_id, voice_type=voice_type, model=model,
                locked=False, owner="user", owner_user=user, created_by=user,
                source="custom", engine=engine, world_id=world_id,
            )
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        if not ok:
            return {"status": "error", "error": "写入失败（权限、磁盘或 id 冲突）"}
        return {"status": "ok", "voice_asset": asset}

    def clone_voice_asset(self, audio_file, name="", provider="localvoice",
                          user="", model="", retain=False, duration=0,
                          world_id="", account_manager=None):
        """上传样本 → 克隆 → **只建声音资产**（不绑定角色）。

        适合"先备好一批声音，再分配给角色"的工作流。

        ⚠️ Step 6D：真实克隆协议已按要求冻结（各 provider 的
        clone_implemented=False），因此现在调用会返回"协议待启用"。
        本方法是**接口占位**，引擎选型确定后无需改动上层即可生效。
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
                model=obj.get("model", ""), owner="system", source="official",
                world_id=world_id,
                extra={"source_audio": obj.get("source_audio")} if obj.get("source_audio") else None,
            )
        except ValueError as e:
            return {"status": "error", "error": str(e), "clone": result}
        if not ok:
            return {"status": "error", "error": "声音资产写入失败", "clone": result}
        return {"status": "ok", "voice_asset": asset, "clone": result}

    def delete_voice_asset(self, voice_asset_id, force=False):
        """删除声音资产。

        会检查两类引用，避免删掉之后角色变哑或用户覆盖悬空：
          · 角色默认声音（character.default_voice_id）
          · 用户覆盖（user_character_preferences）
        """
        used_by_characters = self.characters.characters_using_voice(voice_asset_id)
        used_by_users = []
        try:
            from .user_character_prefs_manager import get_user_character_prefs_manager
            used_by_users = get_user_character_prefs_manager().users_using_voice(voice_asset_id)
        except Exception as e:
            print(f"[voice_admin] 检查用户覆盖引用失败: {e}", flush=True)

        if (used_by_characters or used_by_users) and not force:
            parts = []
            if used_by_characters:
                parts.append(f"角色默认声音：{', '.join(used_by_characters)}")
            if used_by_users:
                who = ", ".join(f"{x['user']}/{x['character_id']}" for x in used_by_users[:10])
                parts.append(f"用户覆盖：{who}")
            return {"status": "error",
                    "error": "仍有引用，无法删除 —— " + "；".join(parts),
                    "used_by_characters": used_by_characters,
                    "used_by_users": used_by_users}

        ok = self.library.remove_voice(voice_asset_id)
        return {"status": "ok" if ok else "error",
                "used_by_characters": used_by_characters,
                "used_by_users": used_by_users,
                "error": "" if ok else "资产不存在或写入失败"}

    # ==================== 角色 + 绑定 ====================
    def list_characters(self, world_id=None, character_type=None):
        return {"status": "ok",
                "characters": self.characters.list_characters(world_id=world_id,
                                                              character_type=character_type)}

    def create_character(self, character_id, name="", character_type=TYPE_TEMPLATE,
                         default_voice_id="", world_id="", personality="",
                         appearance="", system_prompt="", owner="",
                         locked_voice=None, **kwargs):
        """创建角色模板。可选直接指定 default_voice_id（只存引用，不复制 voice_id）。

        locked_voice —— True 表示官方声音不可被用户改动（用户只能 override）。
                        不传则按类型默认：template=True，custom=False。
        """
        try:
            ok, c = self.characters.set_character(
                character_id, name=name, character_type=character_type,
                default_voice_id=default_voice_id, world_id=world_id,
                personality=personality, appearance=appearance,
                system_prompt=system_prompt, owner=owner,
                locked_voice=locked_voice, **kwargs
            )
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        if not ok:
            return {"status": "error", "error": "写入失败（权限或磁盘问题）"}
        return {"status": "ok", "character": c}

    def bind_character_voice(self, character_id, voice_asset_id):
        """设置角色的**默认声音**（管理员操作，所有用户共享）。"""
        ok, res = self.characters.bind_default_voice(character_id, voice_asset_id)
        if not ok:
            return {"status": "error", "error": res if isinstance(res, str) else "绑定失败"}
        return {"status": "ok", "character": res}

    def unbind_character_voice(self, character_id):
        ok, c = self.characters.clear_default_voice(character_id)
        return {"status": "ok" if ok else "error", "character": c}

    # ==================== 用户声音覆盖（用户层） ====================
    def set_user_voice_override(self, user, character_id, voice_override_id):
        """用户给自己换某角色的声音（只影响该用户）。

        voice_override_id 传空字符串 = 清除覆盖，回退角色默认声音。

        ⚠️ 边界（Step 6D）：
          · 这**不会**改动角色模板 —— 其他用户听到的仍是官方默认声音
          · 若角色设了 locked_voice=True，用户**仍然可以 override**（这是允许的），
            只是不能改 character.default_voice_id。本方法从不写角色模板，
            所以 locked_voice 天然被尊重。
          · 覆盖资产必须与该角色属于同一世界（多租户隔离）
        """
        if not user:
            return {"status": "error", "error": "缺少 user"}
        character = self.characters.resolve(character_id)
        if not character:
            return {"status": "error", "error": f"角色不存在: {character_id}"}
        cid = (character.get("character_id") or "").strip()
        wid = (character.get("world_id") or "").strip()

        if voice_override_id:
            asset = self.library.get_voice(voice_override_id, world_id=wid)
            if not asset or not (asset.get("provider") or "").strip():
                return {"status": "error",
                        "error": f"声音资产不可用或不属于该世界: {voice_override_id}"}
        try:
            from .user_character_prefs_manager import get_user_character_prefs_manager
            mgr = get_user_character_prefs_manager()
            ok, entry = mgr.set_override(user, cid, voice_override_id)
        except Exception as e:
            return {"status": "error", "error": f"写入用户偏好失败: {e}"}
        if not ok:
            return {"status": "error", "error": "写入失败（磁盘问题）"}
        return {"status": "ok", "user": user, "character_id": cid,
                "voice_override_id": (entry or {}).get("voice_override_id", ""),
                "cleared": not bool(voice_override_id)}

    def change_character_default_voice(self, character_id, voice_asset_id, as_admin=False):
        """修改角色的**官方默认声音**。

        ⚠️ 这是管理员操作。若角色 locked_voice=True 且 as_admin 不为真，
        则拒绝 —— 这正是 locked_voice 的用途：官方声音不可被用户改动。
        """
        character = self.characters.resolve(character_id)
        if not character:
            return {"status": "error", "error": f"角色不存在: {character_id}"}
        cid = (character.get("character_id") or "").strip()
        if self.characters.is_voice_locked(cid) and not as_admin:
            return {"status": "error",
                    "error": f"角色「{cid}」的官方声音已锁定（locked_voice=true），"
                             f"用户不能修改；如需更换请以管理员身份操作（as_admin=True），"
                             f"或使用 override 只改自己的听感"}
        wid = (character.get("world_id") or "").strip()
        if voice_asset_id:
            asset = self.library.get_voice(voice_asset_id, world_id=wid)
            if not asset or not (asset.get("provider") or "").strip():
                return {"status": "error",
                        "error": f"声音资产不可用或不属于该世界: {voice_asset_id}"}
        ok, res = self.characters.bind_default_voice(cid, voice_asset_id)
        if not ok:
            return {"status": "error", "error": res if isinstance(res, str) else "绑定失败"}
        return {"status": "ok", "character": res}

    def clear_user_voice_override(self, user, character_id):
        return self.set_user_voice_override(user, character_id, "")

    def get_user_voice_override(self, user, character_id):
        try:
            from .user_character_prefs_manager import get_user_character_prefs_manager
            vid = get_user_character_prefs_manager().get_override(user, character_id)
        except Exception as e:
            return {"status": "error", "error": str(e)}
        return {"status": "ok", "user": user, "character_id": character_id,
                "voice_override_id": vid or "", "has_override": bool(vid)}

    def get_effective_voice(self, user, character_id):
        """解析该用户最终会听到的声音（完整走一遍三层优先级）。"""
        from .ai_service import AIService
        svc = AIService()
        info, character, world = svc.resolve_voice(character_id, user=user)
        return {"status": "ok", "user": user, "character_id": character_id,
                "effective": info, "character": character, "world": world,
                "configured": bool(info.get("provider"))}

    def get_character_voice(self, character_id):
        """查看某个角色的**默认**声音（不含用户覆盖）。"""
        c = self.characters.resolve(character_id)
        if not c:
            return {"status": "error", "error": f"角色不存在: {character_id}"}
        asset_id = (c.get("default_voice_id") or c.get("voice_asset_id") or "").strip()
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
        from .user_character_prefs_manager import get_user_character_prefs_manager
        return {
            "worlds": self.worlds.describe(),
            "characters": self.characters.describe(),
            "voice_library": self.library.describe(),
            "user_overrides": get_user_character_prefs_manager().describe(),
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
