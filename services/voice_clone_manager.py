# services/voice_clone_manager.py
# 声音制作工具（管理员）—— V1.1 Step 6B 建立 / 6C 修正版调整职责
#
# ==================== 定位（6C 修正） ====================
# 本模块是**后台资产生产工具**：把一个音频样本变成可复用的**声音资产**。
#
#     音频样本 → clone_voice() → voice_id
#              → clone_into_library() → voice_library.json（voice_asset_id）
#
# 它**不再负责绑定角色** —— 绑定是 character_manager 的事：
#     CharacterManager.bind_voice_asset(character_id, voice_asset_id)
#
# 因为声音是「可复用资产」而非「角色私有属性」：同一份声音可以分配给
# 一个或多个角色，换供应商时也只改声音库一处。
#
# 完整管理员流程见 services/voice_admin.py。
#
# 分工：
#     providers/voice_clone.py     —— 抽象 + voice_object 结构 + 统一返回
#     providers/elevenlabs.py 等   —— 各自的真实协议（端点/参数）
#     voice_library_manager.py     —— 声音资产库（落库目标）
#     character_manager.py         —— 角色模板（引用 voice_asset_id）
#     本文件                        —— 串起来 + 原始音频的隐私策略
#
# ==================== 隐私策略（审核明确要求） ====================
# 默认**不保留**用户上传的原始音频：
#     上传 → 校验 → 送供应商 → 拿到 voice_id → **删除原始文件**
# 只在用户显式要求保留（retain=True）时，才存入 data/voice_samples/。
#
# 理由：否则 data/voice_samples/ 会无上限累积用户声音，
#       而声音属于生物特征类隐私数据，长期留存是真实风险。
#
# 注意：删除只针对**本层复制进工作区的副本**；调用方传进来的原始路径
#       如果是用户自己的文件，我们不会去动它（见 _stage_audio 的说明）。

import os
import shutil
import threading
import time
import uuid
from pathlib import Path

from .providers import PROVIDER_CLASSES
from .providers.voice_clone import (
    build_voice_object,
    clone_fail,
    clone_not_supported,
    clone_pending,
    VOICE_TYPE_CLONED,
)

# 音频扩展名白名单（与 providers/voice_clone.py 的 clone_audio_formats 呼应）
ALLOWED_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")

# 单文件大小上限（字节）—— 防止上传超大文件把内存/磁盘打满
MAX_UPLOAD_BYTES = 25 * 1024 * 1024      # 25MB

# 工作区目录（临时暂存 + 可选的长期保留区）
WORK_DIRNAME = "voice_samples"
TMP_DIRNAME = "voice_samples_tmp"

ENV_DATA_DIR = "DATA_DIR"


def _data_root():
    env_dir = (os.environ.get(ENV_DATA_DIR) or "").strip()
    if env_dir:
        return Path(env_dir)
    return Path(__file__).resolve().parent.parent / "data"


def _now():
    try:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


class VoiceCloneManager:
    """声音克隆编排器。

    典型用法（管理员制作声音资产）：
        cm = VoiceCloneManager()

        # 一步：克隆 + 存进声音库，拿到 voice_asset_id
        r = cm.clone_into_library(audio_file="/path/to/nightchen.wav",
                                  name="清冷男声", provider="elevenlabs",
                                  user="admin")
        # r["voice_asset_id"] == "voice_001"

        # 再把它绑给角色（在 character_manager 里，不在本模块）
        from services.character_manager import get_character_manager
        get_character_manager().bind_voice_asset("nightchen", r["voice_asset_id"])

        或者直接用管理员服务一把梭：
        from services.voice_admin import get_voice_admin_service
        get_voice_admin_service().clone_voice_asset(audio_file="...", name="清冷男声")
    """

    def __init__(self, data_root=None, providers=None):
        self._data_root = Path(data_root) if data_root else _data_root()
        # 允许注入（测试用）；默认从注册表取
        self._providers = providers
        self._lock = threading.RLock()

    # ==================== 供应商解析 ====================
    def _registry(self):
        return self._providers if self._providers is not None else PROVIDER_CLASSES

    def list_clone_providers(self):
        """**已真正接入**克隆能力的供应商 key（可直接用）。"""
        out = []
        for k, cls in self._registry().items():
            if getattr(cls, "clone_implemented", False):
                out.append(k)
        return out

    def list_clone_capable_providers(self):
        """业务上支持克隆、但协议可能尚未接入的供应商 key（供 UI 显示"即将支持"）。"""
        out = []
        for k, cls in self._registry().items():
            if getattr(cls, "supports_clone", False):
                out.append(k)
        return out

    def _resolve_provider(self, provider_key, account_manager=None, user=""):
        """取一个可用的克隆 provider 实例。

        优先用该用户在 ai_accounts 里的配置（各自的 api_key），
        没有则退回全局 ProviderManager 的实例。
        """
        registry = self._registry()
        cls = registry.get((provider_key or "").strip())
        if cls is None:
            return None, f"未知供应商: {provider_key}"

        cfg = None
        if account_manager is not None and user:
            try:
                cfg = account_manager.get_provider(user, provider_key)
            except Exception:
                cfg = None
        return cls(cfg or {}), ""

    # ==================== 音频暂存 ====================
    def _stage_audio(self, audio_file, retain=False):
        """把待克隆音频暂存到一个受控路径，返回 (工作路径, 是否我们创建的副本)。

        为什么要有这一步：
          直接把调用方的路径交给 provider，我们就无法确定
          "删掉它是否安全"。所以统一复制进我们自己的临时目录，
          这样**删除时只删我们自己的副本**，绝不动用户原始文件。

        retain=False → 放 voice_samples_tmp/（克隆完就删）
        retain=True  → 放 voice_samples/（长期保留，用户明确要求）
        """
        src = Path(audio_file)
        if not src.is_file():
            return None, False, f"音频文件不存在: {audio_file}"

        ext = src.suffix.lower()
        if ext not in ALLOWED_EXTS:
            return None, False, f"不支持的音频格式 {ext}（支持：{', '.join(ALLOWED_EXTS)}）"

        try:
            size = src.stat().st_size
        except OSError as e:
            return None, False, f"无法读取音频大小: {e}"
        if size <= 0:
            return None, False, "音频文件为空"
        if size > MAX_UPLOAD_BYTES:
            return None, False, f"音频过大（{size // 1024 // 1024}MB，上限 {MAX_UPLOAD_BYTES // 1024 // 1024}MB）"

        folder = self._data_root / (WORK_DIRNAME if retain else TMP_DIRNAME)
        try:
            folder.mkdir(parents=True, exist_ok=True)
            dst = folder / f"{uuid.uuid4().hex}{ext}"
            shutil.copyfile(src, dst)
        except Exception as e:
            return None, False, f"暂存音频失败: {e}"
        return dst, True, ""

    def _cleanup_staged(self, path, is_ours, retain):
        """按隐私策略处理暂存副本：默认删除，retain=True 时保留。"""
        if not path or not is_ours or retain:
            return False
        try:
            Path(path).unlink(missing_ok=True)
            return True
        except Exception as e:
            print(f"[voice_clone] 删除暂存音频失败（请人工检查）: {path} | {e}", flush=True)
            return False

    # ==================== 主流程 ====================
    def clone_voice(self, user="", ai_name="", audio_file="", provider="",
                    model="", label="", style="", retain=False,
                    duration=0, account_manager=None, timeout=120):
        """上传音频 → 供应商 → 返回标准 voice_object（**不落库**）。

        Step 6C 修正版：拿到 voice_id 后请用 clone_into_library() 存成声音资产，
        再由 CharacterManager.bind_voice_asset(character_id, voice_asset_id) 绑给角色。

        参数：
            user / ai_name —— user 用于取该用户的 api_key（谁付费）；
                              ai_name 只是给供应商侧的 voice 起个名字
                              （默认取音频文件名）
            audio_file     —— 音频路径（会被复制进受控目录，原始文件不动）
            provider       —— 供应商 key（如 elevenlabs）
            retain         —— True 则长期保留上传样本，默认 False（用完即删）
            duration       —— 音频时长（秒，前端可传，仅用于元数据展示）

        返回（统一结构）：
            {"status":"ok", "provider":..., "model":..., "error":"",
             "voice_id":..., "voice_type":"cloned", "voice_object":{...}}
        克隆失败/不支持时返回对应 error 结构，**不抛异常**。
        """
        provider = (provider or "").strip()
        if not provider:
            return clone_fail(error="必须指定 provider")

        prov, err = self._resolve_provider(provider, account_manager=account_manager, user=user)
        if prov is None:
            return clone_fail(provider=provider, error=err)
        # 三种情况必须区分开，不要混成一句"未接入"：
        #   can_clone() False + supports_clone True  → 有能力，协议待接（clone_pending）
        #   can_clone() False + supports_clone False → 供应商根本不支持（clone_not_supported）
        if not getattr(prov, "can_clone", lambda: False)():
            if getattr(prov, "clone_promise", lambda: False)():
                return clone_pending(provider, note=getattr(prov, "clone_note", ""))
            return clone_not_supported(provider)
        if not (getattr(prov, "api_key", "") or "").strip():
            return clone_fail(provider=provider, model=model, error=f"未配置 {prov.name or provider} API Key")

        staged, is_ours, serr = self._stage_audio(audio_file, retain=retain)
        if staged is None:
            return clone_fail(provider=provider, model=model, error=serr)

        src_name = Path(audio_file).name
        try:
            result = prov.clone_voice(
                audio_path=str(staged), name=(ai_name or src_name), model=model, timeout=timeout
            )
        except Exception as e:
            result = clone_fail(provider=provider, model=model, error=f"供应商调用异常: {e}")
        finally:
            # 隐私策略：无论成功失败，默认都清掉暂存副本
            self._cleanup_staged(staged, is_ours, retain)

        if not isinstance(result, dict):
            return clone_fail(provider=provider, model=model, error="供应商返回了非结构化结果")

        # 归一化失败路径（顺手补齐 provider/model）
        if result.get("status") != "ok":
            result.setdefault("provider", provider)
            result.setdefault("model", model)
            return result

        # 成功路径：补齐 source_audio 元数据（只元数据，不含音频）
        voice_id = (result.get("voice_id") or "").strip()
        if not voice_id:
            return clone_fail(provider=provider, model=model, error="供应商未返回 voice_id")

        source_audio = {
            "filename": src_name,
            "duration": duration or 0,
            "created_at": _now(),
            "retained": bool(retain),
        }
        obj = build_voice_object(
            provider=provider,
            voice_id=voice_id,
            voice_type=VOICE_TYPE_CLONED,
            model=(result.get("model") or model or ""),
            style=style,
            label=label or ai_name or src_name,
            source_audio=source_audio,
        )
        return {
            "status": "ok",
            "provider": provider,
            "model": obj.get("model", ""),
            "error": "",
            "voice_id": voice_id,
            "voice_type": VOICE_TYPE_CLONED,
            "voice_object": obj,
        }

    # ==================== 管理员一站式：克隆 + 存入声音资产库 ====================
    def clone_into_library(self, audio_file, name="", provider="", user="",
                           model="", style="", retain=False, duration=0,
                           locked=True, account_manager=None, voice_library=None):
        """管理员操作：上传样本 → 克隆 → 存成**声音资产**（不绑定角色）。

        Step 6C 修正版把这件事拆成两步，因为声音是可复用资产：
            1) 本方法：产出声音资产   → voice_library.json（拿到 voice_asset_id）
            2) CharacterManager.bind_voice_asset(角色, voice_asset_id)

        这样同一份声音可以先做出来，再分配给一个或多个角色。

        返回 clone_voice() 的结构，另加：
            voice_asset_id —— 新资产 id（成功时）
            stored         —— 是否已写入声音库
        """
        result = self.clone_voice(
            user=user, ai_name=name, audio_file=audio_file, provider=provider,
            model=model, label=name, style=style, retain=retain,
            duration=duration, account_manager=account_manager,
        )
        if result.get("status") != "ok":
            result["stored"] = False
            return result

        vl = voice_library
        if vl is None:
            try:
                from .voice_library_manager import get_voice_library_manager
                vl = get_voice_library_manager()
            except Exception as e:
                result["stored"] = False
                result["store_error"] = f"无法获取 VoiceLibraryManager: {e}"
                return result

        obj = result.get("voice_object") or {}
        try:
            ok, asset = vl.add_voice(
                name=name or obj.get("label", ""),
                provider=obj.get("provider", ""),
                voice_id=obj.get("voice_id", ""),
                voice_type=obj.get("voice_type", "cloned"),
                model=obj.get("model", ""),
                locked=locked,
                extra={"source_audio": obj.get("source_audio")} if obj.get("source_audio") else None,
            )
        except Exception as e:
            result["stored"] = False
            result["store_error"] = f"写入声音库失败: {e}"
            return result

        result["stored"] = bool(ok)
        if ok:
            result["voice_asset_id"] = asset.get("id", "")
            result["voice_asset"] = asset
        else:
            result["store_error"] = "写入声音库失败（权限、磁盘或 id 冲突）"
        return result

    # ==================== 保留样本的管理（retain=True 时才用得到） ====================
    def list_retained_samples(self):
        """列出被明确保留的上传样本（含大小/时间），供用户自查与删除。"""
        folder = self._data_root / WORK_DIRNAME
        out = []
        try:
            if not folder.is_dir():
                return out
            for f in sorted(folder.iterdir()):
                if not f.is_file():
                    continue
                st = f.stat()
                out.append({
                    "filename": f.name,
                    "bytes": st.st_size,
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
                })
        except Exception as e:
            print(f"[voice_clone] 列出保留样本失败: {e}", flush=True)
        return out

    def delete_retained_sample(self, filename):
        """删除某个保留样本（用户主动清理）。只允许删除本目录下的文件。"""
        folder = self._data_root / WORK_DIRNAME
        name = Path(filename or "").name          # 防目录穿越
        if not name:
            return False
        target = folder / name
        try:
            if target.is_file() and target.parent == folder:
                target.unlink()
                return True
        except Exception as e:
            print(f"[voice_clone] 删除保留样本失败: {e}", flush=True)
        return False

    def describe(self):
        return {
            "data_root": str(self._data_root),
            "clone_providers": self.list_clone_providers(),
            "retain_by_default": False,
            "max_upload_mb": MAX_UPLOAD_BYTES // 1024 // 1024,
            "allowed_exts": list(ALLOWED_EXTS),
            "retained_samples": self.list_retained_samples(),
        }


# ==================== 单例 ====================
_default_manager = None
_default_lock = threading.RLock()


def get_voice_clone_manager():
    global _default_manager
    with _default_lock:
        if _default_manager is None:
            _default_manager = VoiceCloneManager()
        return _default_manager


def set_voice_clone_manager(mgr):
    global _default_manager
    with _default_lock:
        _default_manager = mgr
    return _default_manager
