# services/user_character_prefs_manager.py
# 用户角色偏好（声音覆盖）—— V1.1 Step 6C 修正版
#
# ==================== 双层声音绑定模型 ====================
#
#              Voice Library（声音资产库）
#                     |
#          ---------------------
#          |                   |
#     System Voice        Custom Voice
#     （管理员）           （用户自定义）
#          |                   |
#          ↓                   ↓
#      Character 默认      User Override 覆盖
#          |                   |
#          ---------+-----------
#                   ↓
#                TTS Engine
#      (VoiceStudio / ElevenLabs / MiniMax)
#
# 本模块只管**用户覆盖层**：
#     用户不想听角色默认声音时，可以给自己换一个（只影响他自己）。
#
# 关键设计：
#   · 覆盖是**每用户每角色**一条，互不影响
#   · 覆盖**不改角色模板** —— 夜辰的默认声音对所有其他用户仍然不变
#   · 覆盖指向的声音资产 id 必须存在于 voice_library（解析时校验，
#     失效则自动回退到角色默认，不会让 TTS 直接失败）
#
# 存储：data/user_character_preferences.json
#
# 结构：
#   {
#     "version": 1,
#     "users": {
#       "user123": {
#         "nightchen": { "voice_override_id": "voice_custom_88", "updated_at": "..." }
#       }
#     }
#   }

import json
import os
import shutil
import threading
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_FILENAME = "user_character_preferences.json"

ENV_FILE = "USER_CHARACTER_PREFS_FILE"
ENV_DATA_DIR = "DATA_DIR"


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


def empty_prefs():
    return {"version": SCHEMA_VERSION, "users": {}}


class UserCharacterPrefsManager:
    """用户 × 角色 的偏好（目前只有声音覆盖）。"""

    def __init__(self, path=None, autoload=True, create_file=True):
        self.path = Path(path) if path else _default_file_path()
        self._lock = threading.RLock()
        self._data = empty_prefs()
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
                    self._data = empty_prefs()
                    self._stat = None
                    self._loaded = True
                    return False
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("根节点不是对象")
                users = raw.get("users")
                if not isinstance(users, dict):
                    users = {}
                ver = raw.get("version")
                self._data = {
                    "version": ver if isinstance(ver, int) else SCHEMA_VERSION,
                    "users": users,
                }
                self._stat = self._stat_now()
                self._loaded = True
                return True
            except Exception as e:
                print(f"[user_prefs] 读取失败，使用空结构: {e}", flush=True)
                self._data = empty_prefs()
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
            print(f"[user_prefs] 写入失败: {e}", flush=True)
            return False

    def save(self):
        with self._lock:
            return self._write()

    # ==================== 用户名归一化 ====================
    @staticmethod
    def _refine(name):
        """与 ai_account_manager._refine_name 同规则，避免同一个人两套键。"""
        try:
            from .ai_account_manager import _refine_name
            return _refine_name(name)
        except Exception:
            return str(name or "").strip()

    def _match_key(self, user):
        target = self._refine(user)
        users = self._data.get("users", {}) or {}
        raw = str(user or "").strip()
        if raw in users:
            return raw
        if target in users:
            return target
        for k in users.keys():
            if self._refine(k) == target:
                return k
        return target

    # ==================== 读取 ====================
    def get_override(self, user, character_id):
        """取某用户对某角色的声音覆盖。没有则 None。"""
        u = self._match_key(user)
        cid = (character_id or "").strip()
        with self._lock:
            self._reload_if_changed()
            entry = ((self._data.get("users", {}) or {}).get(u) or {}).get(cid)
            if not isinstance(entry, dict):
                return None
            vid = (entry.get("voice_override_id") or "").strip()
            return vid or None

    def get_user_prefs(self, user):
        """取某用户的全部角色偏好（副本）。"""
        u = self._match_key(user)
        with self._lock:
            self._reload_if_changed()
            entry = (self._data.get("users", {}) or {}).get(u)
            return json.loads(json.dumps(entry, ensure_ascii=False)) if isinstance(entry, dict) else {}

    def list_users(self):
        with self._lock:
            self._reload_if_changed()
            return sorted((self._data.get("users", {}) or {}).keys())

    # ==================== 写入 ====================
    def set_override(self, user, character_id, voice_override_id):
        """为某用户设置某角色的声音覆盖。

        voice_override_id 为空字符串表示**清除覆盖**（回退到角色默认声音）。
        """
        cid = (character_id or "").strip()
        if not cid:
            raise ValueError("character_id 不能为空")
        vid = (voice_override_id or "").strip()
        if not vid:
            return self.clear_override(user, cid)

        with self._lock:
            self._reload_if_changed()
            u = self._match_key(user)
            users = self._data.setdefault("users", {})
            entry = users.setdefault(u, {})
            entry[cid] = {"voice_override_id": vid, "updated_at": _now()}
            ok = self._write()
            return ok, (json.loads(json.dumps(entry[cid], ensure_ascii=False)) if ok else None)

    def clear_override(self, user, character_id):
        """清除某用户对某角色的覆盖（回退默认声音）。

        返回 (ok, None) 以便与 set_override 的返回形状一致。
        """
        cid = (character_id or "").strip()
        with self._lock:
            self._reload_if_changed()
            u = self._match_key(user)
            users = self._data.setdefault("users", {})
            entry = users.get(u)
            if not isinstance(entry, dict) or cid not in entry:
                return False, None
            entry.pop(cid, None)
            if not entry:
                users.pop(u, None)     # 用户没别的偏好就整体移除，保持文件干净
            return self._write(), None

    def clear_user(self, user):
        with self._lock:
            self._reload_if_changed()
            u = self._match_key(user)
            users = self._data.setdefault("users", {})
            existed = users.pop(u, None) is not None
            if existed:
                return self._write()
            return False

    def remove_character_refs(self, character_id):
        """角色被删除时，清掉所有用户对它的覆盖（避免悬空引用）。"""
        cid = (character_id or "").strip()
        if not cid:
            return 0
        with self._lock:
            self._reload_if_changed()
            users = self._data.setdefault("users", {})
            n = 0
            for u in list(users.keys()):
                entry = users.get(u)
                if isinstance(entry, dict) and cid in entry:
                    entry.pop(cid, None)
                    n += 1
                    if not entry:
                        users.pop(u, None)
            if n:
                self._write()
            return n

    def users_using_voice(self, voice_asset_id):
        """反查哪些用户把这个资产当覆盖用（删除资产前要查）。"""
        vid = (voice_asset_id or "").strip()
        if not vid:
            return []
        with self._lock:
            self._reload_if_changed()
            out = []
            for u, entry in (self._data.get("users", {}) or {}).items():
                if not isinstance(entry, dict):
                    continue
                for cid, pref in entry.items():
                    if isinstance(pref, dict) and (pref.get("voice_override_id") or "").strip() == vid:
                        out.append({"user": u, "character_id": cid})
            return out

    def describe(self):
        with self._lock:
            self._reload_if_changed()
            users = self._data.get("users", {}) or {}
            return {
                "file": str(self.path),
                "version": self._data.get("version", SCHEMA_VERSION),
                "user_count": len(users),
                "users": json.loads(json.dumps(users, ensure_ascii=False)),
            }


# ==================== 单例 ====================
_default_manager = None
_default_lock = threading.RLock()


def get_user_character_prefs_manager(path=None):
    global _default_manager
    with _default_lock:
        if _default_manager is None or path is not None:
            _default_manager = UserCharacterPrefsManager(path=path)
        return _default_manager


def set_user_character_prefs_manager(mgr):
    global _default_manager
    with _default_lock:
        _default_manager = mgr
    return _default_manager
