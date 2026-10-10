# services/ai_service.py
# 统一 AI 能力入口 —— V1.1 Step 1：只做路由，不发起真实请求
#
# 业务侧未来只调用这一个类：
#     AIService.chat() / vision() / image() / asr() / tts()
# 不要直接 import 具体 provider。
#
# 第一版行为：一律返回 {"status": "not_implemented", ...}
#   （provider_manager 选不到 provider 时返回 {"status": "error", ...}）

from . import provider_manager as _pm
from .providers.base import (
    CAPABILITY_CHAT,
    CAPABILITY_VISION,
    CAPABILITY_IMAGE,
    CAPABILITY_ASR,
    CAPABILITY_TTS,
    error_result,
    not_implemented,
    not_implemented_result,
)


def _asset_to_voice(asset, source):
    """把声音资产记录转成调用 provider 需要的参数。

    source 标记这一跳来自哪一层（user_override / character_default / world_default），
    便于排查"这句为什么是这个声音"。

    engine（Step 6D）—— 本地引擎名。provider="localvoice" 时才会用到，
    云端 provider 留空。换本地引擎只改声音资产，上层代码不动。
    """
    asset = asset or {}
    return {
        "provider": (asset.get("provider") or "").strip(),
        "voice_id": (asset.get("voice_id") or "").strip(),
        "model": (asset.get("model") or "").strip(),
        "engine": (asset.get("engine") or "").strip(),
        "voice_type": asset.get("type", ""),
        "voice_asset_id": asset.get("id", ""),
        "voice_name": asset.get("name", ""),
        "asset_source": asset.get("source", ""),   # official / custom / preset
        "source": source,                          # 哪一层生效
    }


class AIService:
    """多供应商 / 多模型 / 多能力的统一服务入口。

    用法（未来真实接入后不变）：
        svc = AIService()
        svc.chat(messages=[...])
        svc.vision(image=..., prompt=...)
        svc.image(prompt=...)
        svc.asr(audio=...)
        svc.tts(text=...)

    可选参数：
        provider —— 指定供应商（不传则按能力自动选型）
        model    —— 指定模型（不传则用 provider_manager 里登记的模型）
    """

    def __init__(self, manager=None, user=None, account_manager=None, user_config=None):
        """
        manager         —— ProviderManager；不传则用全局单例（Step 1 行为不变）
        user            —— Step 4：用户身份。传入后本实例默认按该用户的 ai_accounts 配置选型
        account_manager —— AIAccountManager；不传则用其全局单例（仅当 user 有值时才会用到）
        user_config     —— 预取的 to_manager_payload() 结果；给了就不再自己取（便于批量/测试）
        """
        # 允许注入 manager（便于测试 / 后续接设置页）
        self._manager = manager or _pm.get_manager()
        self._user = (user or "").strip() or None
        self._accounts = account_manager          # 惰性解析，避免强制依赖
        self._user_config = user_config

    # ---------- Step 4：用户配置解析 ----------
    @property
    def user(self):
        return self._user

    def _get_account_manager(self):
        """惰性取 AIAccountManager（只有真正用到 user 时才 import）。"""
        if self._accounts is None:
            from .ai_account_manager import get_account_manager
            self._accounts = get_account_manager()
        return self._accounts

    def resolve_user_config(self, user=None):
        """取某用户的 ProviderManager 配置切片。

        返回 (user_key, payload)：
            user_key —— 归一化后的实际存储键；用户不存在时为空串
            payload  —— {"config": {...}, "capability_prefs": {...}}；取不到时为 None
        任何异常都降级为 (user_key, None)，不影响后续走全局配置。
        """
        u = (user or self._user or "").strip()
        if not u:
            return "", None
        try:
            mgr = self._get_account_manager()
            ukey = mgr.user_key(u)
            payload = mgr.to_manager_payload(u)
            return ukey, payload
        except Exception as e:
            print(f"[ai_service] 读取用户 AI 配置失败（降级为全局配置）: {e}", flush=True)
            return u, None

    @classmethod
    def for_user(cls, user, manager=None, account_manager=None):
        """便捷构造：AIService.for_user("亦言").chat(...)"""
        return cls(manager=manager, user=user, account_manager=account_manager)

    # ---------- 内部：统一选型 + 分发 ----------
    def _dispatch(self, capability, prefer_provider="", model="", kwargs=None,
                  user=None, require_configured=False):
        """按能力选型并把请求交给对应 provider。

        选型优先级（Step 4）：
            1. 本次显式 prefer_provider
            2. 用户配置：defaults[capability] 指定的 provider/model
            3. 用户配置：该能力位收藏列表的顺序
            4. 全局 ProviderManager 的登记（Step 1 行为，用户没配置时完全走这里）

        返回统一结构；provider 选不到时返回 error，而不是抛异常，
        这样业务侧可以安全地「先接上、后实现」。
        """
        kwargs = dict(kwargs or {})
        prefer = [prefer_provider] if prefer_provider else None

        # ===== Step 4：解析用户配置（没传 user 时完全走原有逻辑）=====
        eff_user = (user or self._user or "").strip()
        extra_cfg = None
        user_model = ""
        if eff_user:
            payload = self._user_config if (self._user_config is not None and not user) else None
            if payload is None:
                _ukey, payload = self.resolve_user_config(eff_user)
            if payload:
                extra_cfg = payload.get("config") or None
                # 用户为该能力位设定的默认模型直接作为 prefer，保证「用哪个模型」可控
                dprov = ""
                try:
                    mgr = self._get_account_manager()
                    dprov, user_model = mgr.get_default_model(eff_user, capability)
                except Exception:
                    dprov, user_model = "", ""
                if dprov:
                    prefer = [dprov] + (prefer or [])
                # 能力偏好顺序也带上，让收藏顺序参与选型
                if not prefer:
                    prefs = (payload.get("capability_prefs") or {}).get(capability)
                    if prefs:
                        prefer = list(prefs)
                # 过滤掉「不支持该能力位」的供应商，避免偏好顺序把一个
                # 不支持 chat/tts/vision 的 provider 顶到最前面。
                if prefer:
                    filtered = []
                    for _k in prefer:
                        _p = self._manager.get_provider(_k)
                        if _p is not None and _p.supports(capability):
                            filtered.append(_k)
                    prefer = filtered or None

        pkey, reg_model = self._manager.resolve(
            capability, prefer=prefer, require_configured=require_configured, extra_config=extra_cfg
        )
        if not pkey:
            _hint = (f"（用户 {eff_user} 未配置该能力，且全局也未登记）" if eff_user
                     else "（provider_manager 未登记）")
            return error_result(
                provider=prefer_provider or "",
                capability=capability,
                message=f"没有可用于 {capability} 的供应商" + _hint,
            )

        # 命中用户配置时，用用户那份 api_key 构造 provider 实例（不写入全局 manager）
        provider = None
        if extra_cfg and pkey in extra_cfg:
            try:
                from .providers import PROVIDER_CLASSES
                cls = PROVIDER_CLASSES.get(pkey)
                if cls is not None:
                    provider = cls(extra_cfg[pkey])
            except Exception as e:
                print(f"[ai_service] 用用户配置构造 provider 失败: {e}", flush=True)
        if provider is None:
            provider = self._manager.get_provider(pkey)
        if provider is None:
            return error_result(
                provider=pkey,
                capability=capability,
                message=f"未知供应商: {pkey}",
            )

        # 显式传入的 model > 用户默认模型 > 登记表里的 model
        use_model = model or user_model or reg_model

        # ===== Step 5B：能力位以 provider 自己的声明为准 =====
        # 不再维护任何硬编码的 (provider, capability) 名单 —— 那是硬编码地狱。
        # provider.supports() 读取该 provider 的 implemented_capabilities，
        # 所以「接一个新供应商/新能力」= 只改那一个 provider 文件，AIService 不动。
        if not provider.supports(capability):
            return not_implemented_result(provider=pkey, model=use_model, capability=capability)

        handler = {
            CAPABILITY_CHAT: provider.chat,
            CAPABILITY_VISION: provider.vision,
            CAPABILITY_IMAGE: provider.image,
            CAPABILITY_ASR: provider.asr,
            CAPABILITY_TTS: provider.tts,
        }.get(capability)

        if handler is None:
            return error_result(
                provider=pkey,
                capability=capability,
                message=f"未知能力位: {capability}",
            )

        try:
            result = handler(model=use_model, **kwargs)
        except Exception as e:
            # provider 内部已自行兜异常；这里再兜一层，避免影响调用方
            return error_result(provider=pkey, capability=capability, message=f"provider 调用异常: {e}")

        # 统一结构：补齐 provider / model / error 字段，便于业务侧统一判断
        if isinstance(result, dict):
            result.setdefault("provider", pkey)
            if use_model:
                result.setdefault("model", use_model)
            result.setdefault("error", "")
            result.setdefault("capability", capability)
            return result

        # provider 返回了非 dict（异常情况）→ 归一化
        return not_implemented(pkey, capability)

    # ---------- 五个能力位 ----------
    # Step 4：新增两个可选关键字参数
    #   user                —— 本次调用使用的用户身份（覆盖实例级 user）
    #   require_configured  —— 只选「已填 api_key」的供应商（用户级场景推荐 True）
    def chat(self, messages=None, provider="", model="", user=None, require_configured=False, **kwargs):
        """对话。messages 为 OpenAI 风格的消息数组。"""
        return self._dispatch(
            CAPABILITY_CHAT,
            prefer_provider=provider,
            model=model,
            kwargs={"messages": messages or [], **kwargs},
            user=user,
            require_configured=require_configured,
        )

    def vision(self, image=None, prompt="", provider="", model="", user=None, require_configured=False, **kwargs):
        """识图：给一张图（路径/URL/base64）+ 提示词，返回理解结果。"""
        return self._dispatch(
            CAPABILITY_VISION,
            prefer_provider=provider,
            model=model,
            kwargs={"image": image, "prompt": prompt, **kwargs},
            user=user,
            require_configured=require_configured,
        )

    def image(self, prompt="", provider="", model="", user=None, require_configured=False, **kwargs):
        """生图：给提示词，返回图片（第一版未实现）。"""
        return self._dispatch(
            CAPABILITY_IMAGE,
            prefer_provider=provider,
            model=model,
            kwargs={"prompt": prompt, **kwargs},
            user=user,
            require_configured=require_configured,
        )

    def asr(self, audio=None, provider="", model="", user=None, require_configured=False, **kwargs):
        """语音识别：音频 → 文本。"""
        return self._dispatch(
            CAPABILITY_ASR,
            prefer_provider=provider,
            model=model,
            kwargs={"audio": audio, **kwargs},
            user=user,
            require_configured=require_configured,
        )

    def resolve_voice(self, character_id_or_name, user=""):
        """解析「角色 + 用户 → 最终声音资产 → provider/voice_id」。

        ==================== 双层绑定优先级（Step 6C 修正版） ====================
            1. 用户自定义覆盖（user_character_preferences）—— 有就用它
            2. 角色默认声音（character.default_voice_id）—— 所有用户共享
            3. 世界默认声音（world.default_voice_id）    —— 兜底
            4. 都没有 → 回退 provider 默认音色

        覆盖失效（指向的资产已被删除）时**自动回退**到角色默认，不让 TTS 直接失败。

        返回 dict：
            {"provider","voice_id","model","voice_type","voice_asset_id",
             "voice_name","source"}    // source: user_override | character_default
                                        //         | world_default | none
            以及 character / world（可能为 None）
        """
        out = {"provider": "", "voice_id": "", "model": "", "voice_type": "",
               "voice_asset_id": "", "voice_name": "", "source": "none"}
        character = None
        world = None
        if not character_id_or_name:
            return out, character, world

        try:
            from .character_manager import get_character_manager
            cm = get_character_manager()
            character = cm.resolve(character_id_or_name)
            if not character:
                print(f"[ai_service] 未找到角色模板: {character_id_or_name}", flush=True)
                return out, None, None
            cid = (character.get("character_id") or "").strip()
            # 多租户隔离：角色所属世界。声音资产若属于别的世界会被拒绝。
            wid = (character.get("world_id") or "").strip()

            from .voice_library_manager import get_voice_library_manager
            vl = get_voice_library_manager()

            # ---------- 1. 用户覆盖 ----------
            if user and cid:
                try:
                    from .user_character_prefs_manager import get_user_character_prefs_manager
                    override_id = get_user_character_prefs_manager().get_override(user, cid)
                except Exception as e:
                    print(f"[ai_service] 读取用户声音覆盖失败: {e}", flush=True)
                    override_id = None
                if override_id:
                    asset = vl.get_voice(override_id, world_id=wid)
                    if asset and (asset.get("provider") or "").strip():
                        out.update(_asset_to_voice(asset, "user_override"))
                        return out, character, world
                    # 覆盖失效 → 回退，并留下可排查的日志
                    print(f"[ai_service] 用户覆盖声音 {override_id} 不可用，回退角色默认", flush=True)

            # ---------- 2. 角色默认声音（官方声音） ----------
            default_id = (character.get("default_voice_id")
                          or character.get("voice_asset_id") or "").strip()
            if default_id:
                asset = vl.get_voice(default_id, world_id=wid)
                if asset and (asset.get("provider") or "").strip():
                    out.update(_asset_to_voice(asset, "character_default"))
                    return out, character, world
                print(f"[ai_service] 角色默认声音 {default_id} 不可用", flush=True)

            # ---------- 3. 世界默认声音 ----------
            if wid:
                try:
                    from .world_manager import get_world_manager
                    wm = get_world_manager()
                    world = wm.get_world(wid)
                except Exception as e:
                    print(f"[ai_service] 读取世界配置失败: {e}", flush=True)
                world_default = ((world or {}).get("default_voice_id") or "").strip()
                if world_default:
                    asset = vl.get_voice(world_default, world_id=wid)
                    if asset and (asset.get("provider") or "").strip():
                        out.update(_asset_to_voice(asset, "world_default"))
                        return out, character, world

            print(f"[ai_service] 角色 {character.get('name') or cid} 未配置任何可用声音", flush=True)
            return out, character, world
        except Exception as e:
            print(f"[ai_service] 解析角色声音失败（回退默认音色）: {e}", flush=True)
            return out, character, world

    def resolve_voice_for_character(self, character_id_or_name, user=""):
        """兼容旧名：等价于 resolve_voice()。返回 (voice_info|None, character)。"""
        info, character, _world = self.resolve_voice(character_id_or_name, user=user)
        return (info if info.get("provider") else None), character

    def tts(self, text="", provider="", model="", user=None, require_configured=False,
            character_id="", ai_name="", voice_id="", **kwargs):
        """语音合成：文本 → 音频。

        ==================== Step 6C 修正版：双层声音绑定 ====================
        AIService(user="user123").tts(text="你好", character_id="nightchen")
            character_id + user
                → 1. 用户覆盖？      （user_character_preferences）
                → 2. 角色默认声音？  （character.default_voice_id）
                → 3. 世界默认声音？  （world.default_voice_id）
                → voice_library → provider + voice_id → provider.tts() → 音频

        规则：
          · character_id 是首选入参（稳定英文 id）；ai_name 作为兼容别名，
            既接受角色 id 也接受显示名（如「夜辰」）
          · 传了 user 才会考虑该用户的声音覆盖；不传则用角色默认（所有用户共享）
          · 用户覆盖**不改角色模板** —— 其他用户听到的仍然是官方声音
          · 覆盖失效（资产被删）会自动回退到角色默认，不让 TTS 直接失败
          · 都没有声音时回退 provider 默认音色（不让调用直接失败）
          · 显式传 voice_id 仅供管理员试听/调试，不作为常规用法
        """
        eff_provider = provider
        eff_model = model
        eff_voice = voice_id or ""
        eff_engine = ""
        voice_info = None
        character = None
        eff_user = (user or self._user or "").strip()

        # 1) 角色 + 用户 → 最终声音资产（双层绑定的唯一真相来源）
        target = character_id or ai_name
        if target and not eff_voice:
            voice_info, character, _world = self.resolve_voice(target, user=eff_user)
            if voice_info.get("provider"):
                eff_provider = provider or voice_info.get("provider", "")
                eff_model = model or voice_info.get("model", "")
                eff_voice = voice_info.get("voice_id", "") or ""
                # 本地引擎名（云端为空）：让 LocalVoiceProvider 知道用哪个引擎
                eff_engine = voice_info.get("engine", "") or ""
            else:
                voice_info = None    # 没解析出可用声音 → 标记为回退

        tts_kwargs = {"text": text, "voice_id": eff_voice}
        if eff_engine:
            tts_kwargs["engine"] = eff_engine

        result = self._dispatch(
            CAPABILITY_TTS,
            prefer_provider=eff_provider,
            model=eff_model,
            kwargs={**tts_kwargs, **kwargs},
            user=user,
            require_configured=require_configured,
        )
        # 便于排查"这句到底用的谁的声音"
        if isinstance(result, dict):
            result.setdefault("character_id", (character or {}).get("character_id", character_id or ""))
            result.setdefault("character_name", (character or {}).get("name", ai_name or ""))
            result.setdefault("ai_name", ai_name or (character or {}).get("name", ""))
            # voice_source 直接反映双层绑定的哪一层生效，便于排查
            result.setdefault("voice_source",
                              (voice_info or {}).get("source", "provider_default"))
            if voice_info:
                result.setdefault("voice_asset_id", voice_info.get("voice_asset_id", ""))
                result.setdefault("voice_name", voice_info.get("voice_name", ""))
        return result

    # ---------- 只读查询（供 UI / 调试） ----------
    @property
    def manager(self):
        return self._manager

    def capabilities(self, user=None):
        """返回各能力位的可用供应商与当前选中项（不发起网络请求）。

        Step 4：传入 user（或实例带 user）时，选中项会体现该用户的默认模型与收藏顺序。
        """
        eff_user = (user or self._user or "").strip()
        extra_cfg = None
        prefs = {}
        if eff_user:
            _ukey, payload = self.resolve_user_config(eff_user)
            if payload:
                extra_cfg = payload.get("config") or None
                prefs = payload.get("capability_prefs") or {}

        out = {}
        for cap in (CAPABILITY_CHAT, CAPABILITY_VISION, CAPABILITY_IMAGE, CAPABILITY_ASR, CAPABILITY_TTS):
            available = []
            for k in self._manager.list_providers():
                p = self._manager.get_provider(k)
                if p is not None and p.supports(cap):
                    available.append(k)

            # 偏好顺序：用户已配置的供应商 → 该能力位的收藏顺序 → 其余可用供应商。
            # 这样 capabilities() 报出的 selected 与真正调用时会选到的一致，
            # 而不是"用户没设默认就显示空"。
            pref = []
            for k in sorted((extra_cfg or {}).keys()):
                if k not in pref:
                    pref.append(k)
            for k in (prefs.get(cap) or []):
                if k not in pref:
                    pref.append(k)
            for k in available:
                if k not in pref:
                    pref.append(k)

            selected, selected_model = self._manager.resolve(
                cap, prefer=(pref or None), extra_config=extra_cfg
            )
            out[cap] = {
                "selected": selected,
                "selected_model": selected_model,
                "available": available,
                "user": eff_user or "",
                "configured_for_user": sorted((extra_cfg or {}).keys()),
            }
        return out

    def describe(self, user=None):
        """自描述。传 user 时附带该用户的配置概览（不含 api_key 明文）。"""
        base = self._manager.describe()
        eff_user = (user or self._user or "").strip()
        if eff_user:
            try:
                base["user"] = self._get_account_manager().describe().get("users", {}).get(eff_user, {})
                base["user_key"] = self._get_account_manager().user_key(eff_user)
            except Exception as e:
                base["user"] = {"error": str(e)}
        return base
