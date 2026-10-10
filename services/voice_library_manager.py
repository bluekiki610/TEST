# services/voice_library_manager.py
# Voice Library —— V1.1 Step 6C 修正版
#
# ==================== 定位 ====================
# 声音作为**可复用的世界资产**，由管理员维护，不是某个角色/用户私有。
#
#     Voice Library（声音资产库，管理员）
#             ↑ voice_asset_id 引用
#     Character Template（角色模板）
#             ↑ character_id 引用
#     Character Runtime（角色运行时：关系 / 记忆 / 对话）
#
# 为什么要多一层 voice_asset_id，而不是角色直接存 voice_id：
#   · 两个角色可以先共用同一个声音资产，以后各自分化
#   · 换供应商（ElevenLabs → VoiceStudio 本地）时**只改声音资产一处**，
#     所有引用它的角色自动跟着换，角色模板不用动
#   · 世界复制（100 个世界实例）时角色模板是同一份，声音资产也是同一份
#
# 存储：data/voice_library.json
#
# 结构：
#   {
#     "version": 1,
#     "voices": [
#       {
#         "id": "voice_001",
#         "name": "清冷男声",
#         "provider": "elevenlabs",
#         "voice_id": "xxxx",
#         "type": "cloned",
#         "model": "eleven_multilingual_v2",
#         "created_by": "admin",
#         "locked": true,
#         "created_at": "...",
#         "updated_at": "..."
#       }
#     ]
#   }

import json
import os
import re
import shutil
import threading
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_FILENAME = "voice_library.json"

ENV_FILE = "VOICE_LIBRARY_FILE"
ENV_DATA_DIR = "DATA_DIR"

VOICE_TYPE_PRESET = "preset"
VOICE_TYPE_CLONED = "cloned"

# 声音资产 id 的格式：voice_001 / voice_custom_88
_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{2,64}$")

# ==================== 声音归属（双层模型） ====================
#   system —— 管理员创建的系统声音（官方男主、NPC 等）
#   user   —— 用户创建的自定义声音（只用于"覆盖给自己听"）
# 两层都放在同一个库里，用 owner 区分：
#
#       Voice Asset
#            |
#      +-----+-----+
#      |           |
#   System      User Custom
#    Voice       Override
#
# 这样"所有用户默认共享系统声音"，而个别用户可以挑自己的。
OWNER_SYSTEM = "system"
OWNER_USER = "user"
OWNERS = (OWNER_SYSTEM, OWNER_USER)

# ==================== 声音来源（source，Step 6D） ====================
#   official —— 官方声音（管理员为固定角色制作，长期资产）
#   custom   —— 自定义声音（用户为"我想换个听感"而创建）
#   preset   —— 供应商预置音色（未克隆，直接引用）
SOURCE_OFFICIAL = "official"
SOURCE_CUSTOM = "custom"
SOURCE_PRESET = "preset"
SOURCES = (SOURCE_OFFICIAL, SOURCE_CUSTOM, SOURCE_PRESET)

# ==================== provider 与 engine 的分工（Step 6D） ====================
#   provider —— 走哪条通道（localvoice / elevenlabs / minimax / siliconflow）
#   engine   —— 具体引擎（本地才有意义：gpt_sovits / cosyvoice / fish_speech /
#               voicestudio）。云端 provider 通常留空。
# 换本地引擎只改 engine 一处，provider 与上层代码都不动。


def _now():
    try:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def _default_data_root():
    env_dir = (os.environ.get(ENV_DATA_DIR) or "").strip()
    if env_dir:
        return Path(env_dir)
    return Path(__file__).resolve().parent.parent / "data"


def _default_file_path():
    env_file = (os.environ.get(ENV_FILE) or "").strip()
    if env_file:
        return Path(env_file)
    return _default_data_root() / DEFAULT_FILENAME


def empty_library():
    return {"version": SCHEMA_VERSION, "voices": []}


class VoiceLibraryManager:
    """声音资产库（管理员维护，用户只读）。"""

    def __init__(self, path=None, autoload=True, create_file=True, write_guard=None):
        self.path = Path(path) if path else _default_file_path()
        self._lock = threading.RLock()
        self._data = empty_library()
        self._stat = None
        self._loaded = False
        self._write_guard = write_guard
        if autoload:
            self.load()
        if create_file:
            self.ensure_file()

    # ==================== 写保护 ====================
    def set_write_guard(self, guard):
        self._write_guard = guard

    def _check_write(self):
        if self._write_guard is None:
            return True
        try:
            return bool(self._write_guard())
        except Exception as e:
            print(f"[voice_library] 写保护回调异常，拒绝写入: {e}", flush=True)
            return False

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
                    self._data = empty_library()
                    self._stat = None
                    self._loaded = True
                    return False
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("根节点不是对象")
                voices = raw.get("voices")
                if not isinstance(voices, list):
                    voices = []
                ver = raw.get("version")
                self._data = {
                    "version": ver if isinstance(ver, int) else SCHEMA_VERSION,
                    "voices": voices,
                }
                self._stat = self._stat_now()
                self._loaded = True
                return True
            except Exception as e:
                print(f"[voice_library] 读取失败，使用空结构: {e}", flush=True)
                self._data = empty_library()
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
                return self._write(skip_guard=True)
            return True

    def _write(self, skip_guard=False):
        if not skip_guard and not self._check_write():
            print("[voice_library] 写入被拒绝（缺少管理员权限）", flush=True)
            return False
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
            print(f"[voice_library] 写入失败: {e}", flush=True)
            return False

    def save(self):
        with self._lock:
            return self._write()

    # ==================== 查询（用户侧只读） ====================
    def list_voices(self, owner=None, world_id=None):
        """列出声音资产。

        owner    —— "system"/"user" 过滤
        world_id —— 世界过滤（多租户隔离）：
                    · 传具体世界 → 该世界的资产 + 全局资产（world_id 为空）
                    · 不传       → 全部（管理员视图）
        """
        with self._lock:
            self._reload_if_changed()
            voices = self._data.get("voices", []) or []
            if owner:
                voices = [v for v in voices
                          if isinstance(v, dict) and (v.get("owner") or OWNER_SYSTEM) == owner]
            if world_id:
                voices = [v for v in voices
                          if isinstance(v, dict)
                          and (v.get("world_id") or "") in ("", world_id)]
            return json.loads(json.dumps(voices, ensure_ascii=False))

    def list_system_voices(self, world_id=None):
        """系统声音（管理员资产）—— 用户可从中挑选覆盖。"""
        return self.list_voices(owner=OWNER_SYSTEM, world_id=world_id)

    def list_user_voices(self, owner_user=""):
        """用户自定义声音。传 owner_user 则只看该用户的。"""
        out = self.list_voices(owner=OWNER_USER)
        if owner_user:
            out = [v for v in out if (v.get("owner_user") or "") == owner_user]
        return out

    def get_voice(self, voice_asset_id, world_id=None):
        """按声音资产 id 取资产。这是 TTS 链路的关键一跳。

        world_id —— 多租户隔离校验。传了就要求该资产属于这个世界
                    或属于全局（world_id 为空）。跨世界取用会被拒绝，
                    避免"世界A的角色误用世界B的声音"。
        """
        vid = (voice_asset_id or "").strip()
        if not vid:
            return None
        with self._lock:
            self._reload_if_changed()
            for v in (self._data.get("voices", []) or []):
                if not isinstance(v, dict) or (v.get("id") or "").strip() != vid:
                    continue
                if world_id:
                    vw = (v.get("world_id") or "").strip()
                    if vw and vw != world_id:
                        print(f"[voice_library] ⚠️ 跨世界声音引用被拒绝: "
                              f"资产 {vid} 属于世界 {vw}，当前世界 {world_id}", flush=True)
                        return None
                return json.loads(json.dumps(v, ensure_ascii=False))
            return None

    def has_voice(self, voice_asset_id, world_id=None):
        return self.get_voice(voice_asset_id, world_id=world_id) is not None

    def next_id(self, prefix="voice"):
        """生成一个未被占用的资产 id（voice_001 递增）。"""
        with self._lock:
            used = set()
            for v in (self._data.get("voices", []) or []):
                if isinstance(v, dict):
                    used.add((v.get("id") or "").strip())
            i = 1
            while True:
                cand = f"{prefix}_{i:03d}"
                if cand not in used:
                    return cand
                i += 1

    # ==================== 写入（管理员） ====================
    def add_voice(self, voice_asset_id="", name="", provider="", voice_id="",
                  voice_type=VOICE_TYPE_CLONED, model="", created_by="admin",
                  locked=True, owner=OWNER_SYSTEM, owner_user="",
                  source="", engine="", world_id="", extra=None):
        """新增一个声音资产。id 不传则自动生成。

        owner      —— "system"（管理员，默认）或 "user"（用户自定义覆盖用）
        owner_user —— owner="user" 时记录归属用户
        locked     —— True 表示普通用户不可修改该资产（系统声音默认锁定）
        source     —— 来源：official（官方）/ custom（自定义）/ preset（预置）
                      不传则按 owner 推断（system→official，user→custom）
        engine     —— **本地引擎**名（gpt_sovits / cosyvoice / fish_speech /
                      voicestudio）。云端 provider 留空。
                      换本地引擎只改这里，上层代码不动。
        world_id   —— 归属世界（多租户隔离）。留空 = 全局可用。

        返回 (ok, asset)。id 冲突返回 (False, None)。
        """
        provider = (provider or "").strip()
        if not provider:
            raise ValueError("provider 不能为空")
        owner = (owner or OWNER_SYSTEM).strip()
        if owner not in OWNERS:
            raise ValueError(f"owner 必须是 {OWNERS} 之一")
        src = (source or "").strip() or (
            SOURCE_OFFICIAL if owner == OWNER_SYSTEM else SOURCE_CUSTOM
        )
        if src not in SOURCES:
            raise ValueError(f"source 必须是 {SOURCES} 之一")
        with self._lock:
            self._reload_if_changed()
            vid = (voice_asset_id or "").strip() or self.next_id(
                "user_voice" if owner == OWNER_USER else "voice"
            )
            if not _ID_RE.match(vid):
                raise ValueError(f"voice_asset_id 只能包含字母/数字/下划线/中划线（2-64位），收到: {vid}")
            if self.get_voice(vid) is not None:
                return False, None
            asset = {
                "id": vid,
                "name": (name or "").strip(),
                "provider": provider,
                "voice_id": (voice_id or "").strip(),
                "type": (voice_type or VOICE_TYPE_CLONED),
                "model": (model or "").strip(),
                "owner": owner,
                "source": src,
                # 本地引擎名（云端为空），换引擎只改这一处
                "engine": (engine or "").strip(),
                # 多租户：空 = 全局可用
                "world_id": (world_id or "").strip(),
                "created_by": (created_by or "admin"),
                "locked": bool(locked),
                "created_at": _now(),
                "updated_at": _now(),
            }
            if owner == OWNER_USER and owner_user:
                asset["owner_user"] = owner_user
            if isinstance(extra, dict):
                for k, v in extra.items():
                    if k not in asset:
                        asset[k] = v
            self._data.setdefault("voices", []).append(asset)
            ok = self._write()
            return ok, (json.loads(json.dumps(asset, ensure_ascii=False)) if ok else None)

    def update_voice(self, voice_asset_id, **fields):
        """更新声音资产。带 locked 的资产仍可被管理员更新（locked 表示"用户不可改"）。"""
        vid = (voice_asset_id or "").strip()
        with self._lock:
            self._reload_if_changed()
            for v in (self._data.get("voices", []) or []):
                if isinstance(v, dict) and (v.get("id") or "").strip() == vid:
                    for k, val in (fields or {}).items():
                        if k in ("id", "created_at"):
                            continue
                        v[k] = val
                    v["updated_at"] = _now()
                    ok = self._write()
                    return ok, (json.loads(json.dumps(v, ensure_ascii=False)) if ok else None)
            return False, None

    def remove_voice(self, voice_asset_id):
        """删除声音资产。调用方应先确认没有角色在引用它。"""
        vid = (voice_asset_id or "").strip()
        with self._lock:
            self._reload_if_changed()
            voices = self._data.get("voices", []) or []
            before = len(voices)
            self._data["voices"] = [
                v for v in voices
                if not (isinstance(v, dict) and (v.get("id") or "").strip() == vid)
            ]
            if len(self._data["voices"]) == before:
                return False
            return self._write()

    def describe(self):
        with self._lock:
            self._reload_if_changed()
            voices = self._data.get("voices", []) or []
            return {
                "file": str(self.path),
                "version": self._data.get("version", SCHEMA_VERSION),
                "count": len(voices),
                "voices": json.loads(json.dumps(voices, ensure_ascii=False)),
                "write_protected": self._write_guard is not None,
            }


# ==================== 单例 ====================
_default_manager = None
_default_lock = threading.RLock()


def get_voice_library_manager(path=None):
    global _default_manager
    with _default_lock:
        if _default_manager is None or path is not None:
            _default_manager = VoiceLibraryManager(path=path)
        return _default_manager


def set_voice_library_manager(mgr):
    global _default_manager
    with _default_lock:
        _default_manager = mgr
    return _default_manager
