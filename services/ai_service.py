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

    def tts(self, text="", provider="", model="", user=None, require_configured=False,
            ai_name="", voice_id="", **kwargs):
        """语音合成：文本 → 音频。

        Step 6A 新增两个可选参数，用于「每个 AI 有自己的声音人格」：
            ai_name  —— 传了就按 voice_manager 里该 AI 登记的音色来（供应商/音色/模型）
            voice_id —— 直接指定音色，优先级高于 ai_name
        两者都不传时，行为与之前完全一致（走用户默认模型 + provider 默认音色）。
        返回统一结构，音频在 audio_base64 里（见 base.ok_audio_result）。
        """
        # 1) 音色解析：voice_id 显式指定 > 该 AI 登记的 profile > 不指定（用默认）
        eff_provider = provider
        eff_model = model
        eff_voice = voice_id or ""
        if not eff_voice and ai_name:
            try:
                from .voice_manager import get_voice_manager
                args = get_voice_manager().resolve_tts_args(ai_name, fallback_provider=provider)
                if args:
                    eff_provider = provider or args.get("provider", "")
                    eff_model = model or args.get("model", "")
                    eff_voice = args.get("voice_id", "") or ""
            except Exception as e:
                print(f"[ai_service] 读取音色配置失败（改用默认音色）: {e}", flush=True)

        return self._dispatch(
            CAPABILITY_TTS,
            prefer_provider=eff_provider,
            model=eff_model,
            kwargs={"text": text, "voice_id": eff_voice, **kwargs},
            user=user,
            require_configured=require_configured,
        )

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
