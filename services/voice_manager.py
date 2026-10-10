# services/voice_manager.py
# AI 声音人格（Voice Profile）存储层 —— V1.1 Step 6A
#
# 定位：**只做"AI 角色 ↔ 音色"的登记与查询**，不发起任何网络请求。
#      真正的克隆（上传音频 → 供应商 → voice_id）留给 Step 6B。
#
# 为什么单独一个文件，而不是塞进 ai_accounts.json：
#   1. 归属不同：ai_accounts.json 是**用户的基础设施配置**（key/收藏/默认模型），
#      而声音是**AI 角色的人格资产**，和以后的人格/外观/随身物是一类东西；
#   2. 复用方式按 AI 名查询（"颜颜用什么声音"），不是按用户；
#   3. 避免账号文件越来越杂 —— 与 Step 2 把数据分开存放的思路一致。
#
# 存储位置：data/ai_voice_profiles.json
#   - 跟随 main.py 的 DATA_ROOT 规则（支持 DATA_DIR / AI_VOICE_FILE 环境变量）
#
# 结构：
#   {
#     "version": 1,
#     "profiles": {
#       "颜颜": {
#         "provider": "siliconflow",
#         "voice_id": "FunAudioLLM/CosyVoice2-0.5B",
#         "model": "FunAudioLLM/CosyVoice2-0.5B",
#         "style": "温柔",
#         "source": "preset",            # preset | cloned
#         "created_at": "2025-01-14 22:31:00",
#         "updated_at": "2025-01-14 22:31:00"
#       }
#     }
#   }
#
# ⚠️ 本层不做的事（避免与 Step 6B 混淆）：
#   - 不调供应商 API
#   - 不存音频文件
#   - 不做音色克隆

import json
import os
import shutil
import threading
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_FILENAME = "ai_voice_profiles.json"

ENV_FILE = "AI_VOICE_FILE"
ENV_DATA_DIR = "DATA_DIR"

# 音色来源
SOURCE_PRESET = "preset"     # 供应商自带/预置音色
SOURCE_CLONED = "cloned"     # 用户上传音频克隆出来的音色（Step 6B 才会产生）


def _now():
    try:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def _default_data_root():
    """与 main.py:29 同一规则：DATA_DIR 环境变量优先，否则 <repo>/data。"""
    env_dir = (os.environ.get(ENV_DATA_DIR) or "").strip()
    if env_dir:
        return Path(env_dir)
    return Path(__file__).resolve().parent.parent / "data"


def _default_file_path():
    env_file = (os.environ.get(ENV_FILE) or "").strip()
    if env_file:
        return Path(env_file)
    return _default_data_root() / DEFAULT_FILENAME


def empty_profiles():
    return {"version": SCHEMA_VERSION, "profiles": {}}


class VoiceProfileManager:
    """AI 声音人格登记中心（纯存储，无网络、无音频文件）。

    用法：
        vm = VoiceProfileManager()
        vm.set_voice("颜颜", provider="siliconflow",
                     voice_id="FunAudioLLM/CosyVoice2-0.5B", style="温柔")
        vm.get_voice("颜颜")        # -> {"provider":..., "voice_id":...} 或 None
        vm.resolve_tts_args("颜颜")  # -> {"provider":"siliconflow","voice_id":...,"model":...}
    """

    def __init__(self, path=None, autoload=True, create_file=True):
        self.path = Path(path) if path else _default_file_path()
        self._lock = threading.RLock()
        self._data = empty_profiles()
        self._stat = None
        self._loaded = False
        if autoload:
            self.load()
        if create_file:
            self.ensure_file()

    # ==================== 文件 ====================
    def _stat_now(self):
        try:
            st = self.path.stat()
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def _changed_on_disk(self):
        return self._loaded and self._stat_now() != self._stat

    def load(self):
        with self._lock:
            try:
                if not self.path.is_file():
                    self._data = empty_profiles()
                    self._stat = None
                    self._loaded = True
                    return False
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("根节点不是对象")
                profiles = raw.get("profiles")
                if not isinstance(profiles, dict):
                    profiles = {}
                ver = raw.get("version")
                self._data = {
                    "version": ver if isinstance(ver, int) else SCHEMA_VERSION,
                    "profiles": profiles,
                }
                self._stat = self._stat_now()
                self._loaded = True
                return True
            except Exception as e:
                print(f"[voice_profiles] 读取失败，使用空结构: {e}", flush=True)
                self._data = empty_profiles()
                self._stat = None
                self._loaded = True
                return False

    def _reload_if_changed(self):
        if self._changed_on_disk():
            self.load()

    def ensure_file(self):
        with self._lock:
            self._reload_if_changed()
            if not self.path.is_file():
                return self._write()
            return True

    def _write(self):
        """原子写 + 覆盖前留 .bak（与 ai_account_manager 同一套做法）。"""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(self._data, ensure_ascii=False, indent=1)
            if self.path.is_file():
                try:
                    shutil.copyfile(self.path, str(self.path) + ".bak")
                except Exception:
                    pass
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, self.path)
            self._stat = self._stat_now()
            self._loaded = True
            return True
        except Exception as e:
            print(f"[voice_profiles] 写入失败: {e}", flush=True)
            return False

    def save(self):
        with self._lock:
            return self._write()

    # ==================== 读写 ====================
    def list_ais(self):
        with self._lock:
            self._reload_if_changed()
            return sorted((self._data.get("profiles", {}) or {}).keys())

    def get_voice(self, ai_name):
        """取某个 AI 的音色配置；没有则 None（不创建）。"""
        with self._lock:
            self._reload_if_changed()
            p = (self._data.get("profiles", {}) or {}).get((ai_name or "").strip())
            if not isinstance(p, dict):
                return None
            return json.loads(json.dumps(p, ensure_ascii=False))

    def set_voice(self, ai_name, provider, voice_id="", model="", style="",
                  source=SOURCE_PRESET, extra=None):
        """登记/更新某个 AI 的音色。

        provider  —— 供应商 key（如 siliconflow / elevenlabs）
        voice_id  —— 供应商侧的音色标识（ElevenLabs 是 voice_id；硅基流动可为空）
        model     —— 该音色对应的模型（硅基流动的音色与模型同一字段时会用到）
        source    —— preset（预置）或 cloned（克隆，Step 6B 产生）
        """
        ai_name = (ai_name or "").strip()
        if not ai_name:
            raise ValueError("ai_name 不能为空")
        provider = (provider or "").strip()
        if not provider:
            raise ValueError("provider 不能为空")

        with self._lock:
            self._reload_if_changed()
            profiles = self._data.setdefault("profiles", {})
            old = profiles.get(ai_name) if isinstance(profiles.get(ai_name), dict) else {}
            item = {
                "provider": provider,
                "voice_id": (voice_id or "").strip(),
                "model": (model or "").strip(),
                "style": (style or "").strip(),
                "source": (source or SOURCE_PRESET),
                "created_at": old.get("created_at") or _now(),
                "updated_at": _now(),
            }
            if isinstance(extra, dict):
                for k, v in extra.items():
                    if k not in ("created_at", "updated_at"):
                        item[k] = v
            profiles[ai_name] = item
            self._write()
            return json.loads(json.dumps(item, ensure_ascii=False))

    def remove_voice(self, ai_name):
        with self._lock:
            self._reload_if_changed()
            profiles = self._data.setdefault("profiles", {})
            existed = profiles.pop((ai_name or "").strip(), None) is not None
            if existed:
                self._write()
            return existed

    # ==================== 与 AIService.tts() 的衔接 ====================
    def resolve_tts_args(self, ai_name, fallback_provider=""):
        """把某 AI 的音色解析成 AIService.tts() 需要的参数。

        返回 dict：{"provider":..., "voice_id":..., "model":...}
        没有登记时返回空 dict（由调用方决定用默认音色，而不是报错）。
        """
        p = self.get_voice(ai_name)
        if not p:
            if not fallback_provider:
                return {}
            return {"provider": fallback_provider, "voice_id": "", "model": ""}
        out = {
            "provider": p.get("provider", "") or fallback_provider,
            "voice_id": p.get("voice_id", "") or "",
            "model": p.get("model", "") or "",
        }
        return {k: v for k, v in out.items() if v}

    def describe(self):
        """概览（不含任何敏感数据）。"""
        with self._lock:
            self._reload_if_changed()
            profiles = self._data.get("profiles", {}) or {}
            return {
                "file": str(self.path),
                "version": self._data.get("version", SCHEMA_VERSION),
                "count": len(profiles),
                "profiles": json.loads(json.dumps(profiles, ensure_ascii=False)),
            }


# ==================== 单例 ====================
_default_manager = None
_default_lock = threading.RLock()


def get_voice_manager(path=None):
    global _default_manager
    with _default_lock:
        if _default_manager is None or path is not None:
            _default_manager = VoiceProfileManager(path=path)
        return _default_manager


def set_voice_manager(mgr):
    global _default_manager
    with _default_lock:
        _default_manager = mgr
    return _default_manager
