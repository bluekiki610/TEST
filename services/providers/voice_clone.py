# services/providers/voice_clone.py
# 声音克隆 Provider 抽象 —— V1.1 Step 6B
#
# 设计原则（按审核意见：先定抽象，再写供应商接口）：
#
#   1. 克隆能力**不放进 BaseProvider**。
#      因为不是所有供应商都能克隆（例如硅基流动是聚合平台，克隆要看具体模型）。
#      把 clone_voice() 堆进 BaseProvider 会让每个不支持克隆的 provider
#      都长出一个永远 not_implemented 的方法，既误导又难维护。
#      → 用独立的 mixin：谁支持克隆，谁继承 VoiceCloneProvider。
#
#   2. 能力用类属性声明，沿用 Step 5B 的同一套语义（implemented 才是真相）。
#
#   3. 音色对象结构（VoiceObject）—— 见 build_voice_object()。
#      核心是**不让 voice_id 承担太多含义**：
#        voice_id    仅一个标识，不表达"预设还是克隆"
#        voice_type  显式表达 preset / cloned
#        source_audio 只存**元数据**，不存音频本体
#
#   4. 隐私：原始音频默认不长期保留（见 voice_clone_manager 的 retain 策略）。

from .base import STATUS_OK, STATUS_ERROR, STATUS_NOT_IMPLEMENTED

# voice_type 取值
VOICE_TYPE_PRESET = "preset"     # 供应商预置音色
VOICE_TYPE_CLONED = "cloned"     # 用户上传音频克隆出来的音色

VOICE_TYPES = (VOICE_TYPE_PRESET, VOICE_TYPE_CLONED)

# 克隆结果状态
CLONE_STATUS_OK = STATUS_OK
CLONE_STATUS_ERROR = STATUS_ERROR
CLONE_STATUS_NOT_SUPPORTED = STATUS_NOT_IMPLEMENTED


def build_voice_object(provider, voice_id, voice_type=VOICE_TYPE_PRESET,
                       model="", style="", source_audio=None, label="",
                       created_at="", updated_at="", extra=None):
    """构造标准音色对象（写进 ai_voice_profiles.json 的就是它）。

    ⚠️ 字段职责必须清晰：
        provider      —— 哪个供应商提供这个音色（换供应商 = 换声音，不能混用）
        voice_id      —— 供应商侧的音色标识。**只有标识作用**，不表达类型。
                         例：ElevenLabs "21m00Tcm4TlvDq8ikWAM"；MiniMax "voice_xxx"；
                         硅基流动可为空（它的音色绑在 model 上）
        voice_type    —— preset | cloned。显式表达来源，不要靠 voice_id 猜。
        model         —— 该音色配套的模型（有的供应商音色与模型同字段）
        style         —— 展示用的风格标签（温柔/沉稳…），仅展示，不参与调用
        source_audio  —— **仅元数据**：{filename, duration, created_at, retained}
                         绝不存音频本体；retain=False 时原始文件会被删除
        label         —— 展示名（如「温柔女声」）

    这样以后接新供应商，只要它能给出 voice_id，就能落进同一个结构，
    不需要为"克隆音色"再造一套字段。
    """
    src = None
    if isinstance(source_audio, dict):
        src = {
            "filename": source_audio.get("filename", "") or "",
            "duration": source_audio.get("duration", 0) or 0,
            "created_at": source_audio.get("created_at", "") or "",
            # 原始音频是否仍保留在本机（默认 False —— 保护隐私）
            "retained": bool(source_audio.get("retained", False)),
        }

    out = {
        "provider": (provider or "").strip(),
        "voice_id": (voice_id or "").strip(),
        "voice_type": (voice_type or VOICE_TYPE_PRESET),
        "model": (model or "").strip(),
        "style": (style or "").strip(),
        "label": (label or "").strip(),
        "source_audio": src,
        "created_at": created_at or "",
        "updated_at": updated_at or "",
    }
    if isinstance(extra, dict):
        for k, v in extra.items():
            if k not in out:
                out[k] = v
    return out


def clone_ok(provider="", voice_id="", model="", label="", source_audio=None, extra=None):
    """克隆成功的统一返回。

    字段与 Step 5A 起的统一结构保持一致（status/provider/model/error），
    另带 voice_id / voice_object，方便调用方直接落库。
    """
    obj = build_voice_object(
        provider=provider, voice_id=voice_id, voice_type=VOICE_TYPE_CLONED,
        model=model, label=label, source_audio=source_audio,
    )
    if isinstance(extra, dict):
        obj.update({k: v for k, v in extra.items() if k not in obj})
    return {
        "status": CLONE_STATUS_OK,
        "provider": provider,
        "model": model,
        "error": "",
        "voice_id": voice_id,
        "voice_type": VOICE_TYPE_CLONED,
        "voice_object": obj,
    }


def clone_fail(provider="", model="", error="", **extra):
    """克隆失败的统一返回。"""
    out = {
        "status": CLONE_STATUS_ERROR,
        "provider": provider,
        "model": model,
        "error": error or "unknown error",
        "voice_id": "",
        "voice_type": VOICE_TYPE_CLONED,
        "voice_object": None,
    }
    out.update(extra)
    return out


def clone_not_supported(provider=""):
    """该供应商不具备克隆能力（业务上不支持）。"""
    return {
        "status": CLONE_STATUS_NOT_SUPPORTED,
        "provider": provider,
        "model": "",
        "error": "该供应商不具备声音克隆能力",
        "voice_id": "",
        "voice_type": VOICE_TYPE_CLONED,
        "voice_object": None,
    }


def clone_pending(provider="", note=""):
    """该供应商有能力克隆，但真实协议**尚未接入**。

    单独一个状态，避免把「架构已就绪、端点待接」伪装成「这个供应商不支持克隆」。
    """
    return {
        "status": CLONE_STATUS_NOT_SUPPORTED,
        "provider": provider,
        "model": "",
        "error": f"{provider} 的声音克隆协议尚未接入（架构已就绪，待核对官方端点/参数）",
        "note": note or "",
        "voice_id": "",
        "voice_type": VOICE_TYPE_CLONED,
        "voice_object": None,
    }


class VoiceCloneProvider:
    """声音克隆能力 mixin。

    支持克隆的 provider 这样写：

        class ElevenLabsProvider(BaseProvider, VoiceCloneProvider):
            implemented_capabilities = [CAPABILITY_TTS]
            supports_clone = True          # 供应商业务上支持克隆
            clone_implemented = True       # 且我们已接入真实协议

            def clone_voice(self, audio_path, name="", model="", **kwargs):
                ...

    三个标志位的职责（不要混）：
        supports_clone     —— 供应商**能不能**克隆（业务事实）
        clone_implemented  —— 我们**接没接**真实协议（工程进度）
        can_clone()        —— = clone_implemented，真正的可执行判断
    """

    #: 供应商业务上是否支持克隆
    supports_clone = False
    #: 我们是否已接入真实克隆协议
    clone_implemented = False
    #: 允许的音频格式（用于前置校验与给前端的提示）
    clone_audio_formats = ("mp3", "wav", "m4a")
    #: 建议的最短时长（秒）—— 给前端做提示用，不作为硬性拒绝依据
    clone_min_seconds = 20

    def can_clone(self):
        """本 provider 现在**是否真的能**执行克隆。"""
        return bool(type(self).clone_implemented)

    def clone_promise(self):
        """供应商业务上是否支持克隆（用于 UI 展示"即将支持"）。"""
        return bool(type(self).supports_clone)

    def clone_voice(self, audio_path="", name="", model="", **kwargs):
        """上传音频 → 供应商 → 返回 voice_id。

        ⚠️ 基类**不实现**真实调用：把未核实的端点写进代码，
        就是"写了但从没跑通"的代码。子类必须覆盖。
        """
        if type(self).supports_clone:
            return clone_pending(self.key)
        return clone_not_supported(self.key)
