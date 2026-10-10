# services/world_manager.py
# World Template Manager —— V1.1 Step 6C 修正版
#
# ==================== 定位 ====================
# 层级的最顶层：一个「世界模板」定义了这个世界的基本规则，
# 未来可以复制成多个世界实例（多租户）。
#
#     World Template          ← 本模块
#           ↓
#     Character Template      ← character_manager（voice_asset_id 引用声音库）
#           ↓
#     Character Runtime       ← 未来：relationship / memory / conversation
#
# 关键：世界决定**是否允许用户创建角色**（你未来要关掉创建功能）。
#   当前测试环境：allow_custom_characters = True
#   未来官方世界：allow_custom_characters = False
#
# 存储：data/world_templates.json
#
# 结构：
#   {
#     "version": 1,
#     "worlds": {
#       "otome_a": {
#         "world_id": "otome_a",
#         "name": "乙女世界 A",
#         "description": "",
#         "allow_custom_characters": true,      // 是否开放用户创建角色
#         "character_ids": ["nightchen", "shenmo"],   // 本世界的官方角色
#         "voice_library": "default",           // 使用哪套声音资产库（未来可多套）
#         "locked": true,
#         "created_at": "...",
#         "updated_at": "..."
#       }
#     }
#   }

import json
import os
import re
import shutil
import threading
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_FILENAME = "world_templates.json"

ENV_FILE = "WORLD_TEMPLATES_FILE"
ENV_DATA_DIR = "DATA_DIR"

_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{2,64}$")


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


def empty_worlds():
    return {"version": SCHEMA_VERSION, "worlds": {}}


class WorldManager:
    """世界模板管理（顶层，管理员维护）。"""

    def __init__(self, path=None, autoload=True, create_file=True, write_guard=None):
        self.path = Path(path) if path else _default_file_path()
        self._lock = threading.RLock()
        self._data = empty_worlds()
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
            print(f"[worlds] 写保护回调异常，拒绝写入: {e}", flush=True)
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
                    self._data = empty_worlds()
                    self._stat = None
                    self._loaded = True
                    return False
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("根节点不是对象")
                worlds = raw.get("worlds")
                if not isinstance(worlds, dict):
                    worlds = {}
                ver = raw.get("version")
                self._data = {
                    "version": ver if isinstance(ver, int) else SCHEMA_VERSION,
                    "worlds": worlds,
                }
                self._stat = self._stat_now()
                self._loaded = True
                return True
            except Exception as e:
                print(f"[worlds] 读取失败，使用空结构: {e}", flush=True)
                self._data = empty_worlds()
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
            print("[worlds] 写入被拒绝（缺少管理员权限）", flush=True)
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
            print(f"[worlds] 写入失败: {e}", flush=True)
            return False

    def save(self):
        with self._lock:
            return self._write()

    # ==================== 查询 ====================
    def list_worlds(self):
        with self._lock:
            self._reload_if_changed()
            out = []
            for wid, w in (self._data.get("worlds", {}) or {}).items():
                if not isinstance(w, dict):
                    continue
                item = json.loads(json.dumps(w, ensure_ascii=False))
                item.setdefault("world_id", wid)
                out.append(item)
            out.sort(key=lambda x: x.get("world_id", ""))
            return out

    def get_world(self, world_id):
        wid = (world_id or "").strip()
        if not wid:
            return None
        with self._lock:
            self._reload_if_changed()
            w = (self._data.get("worlds", {}) or {}).get(wid)
            if not isinstance(w, dict):
                return None
            out = json.loads(json.dumps(w, ensure_ascii=False))
            out.setdefault("world_id", wid)
            return out

    def allows_custom_characters(self, world_id):
        """该世界是否允许用户创建角色。

        未登记的世界默认 True（当前测试环境行为，不改变现状）。
        """
        w = self.get_world(world_id)
        if w is None:
            return True
        return bool(w.get("allow_custom_characters", True))

    def list_character_ids(self, world_id):
        w = self.get_world(world_id)
        if not w:
            return []
        ids = w.get("character_ids")
        return list(ids) if isinstance(ids, list) else []

    # ==================== 写入（管理员） ====================
    def set_world(self, world_id, name="", description="",
                  allow_custom_characters=True, character_ids=None,
                  voice_library="default", locked=True, default_voice_id=None,
                  extra=None):
        """创建/更新世界模板。

        default_voice_id —— 世界级**兜底**声音（角色自己没配默认声音时用它）。
                            传 None 表示"保持原值不动"。
        """
        wid = (world_id or "").strip()
        if not wid:
            raise ValueError("world_id 不能为空")
        if not _ID_RE.match(wid):
            raise ValueError(f"world_id 只能包含字母/数字/下划线/中划线（2-64位），收到: {wid}")

        with self._lock:
            self._reload_if_changed()
            worlds = self._data.setdefault("worlds", {})
            old = worlds.get(wid) if isinstance(worlds.get(wid), dict) else {}
            item = {
                "world_id": wid,
                "name": (name or old.get("name") or wid).strip(),
                "description": description if description else old.get("description", ""),
                "allow_custom_characters": bool(
                    old.get("allow_custom_characters", True)
                    if allow_custom_characters is None else allow_custom_characters
                ),
                "character_ids": list(character_ids) if isinstance(character_ids, list)
                                 else list(old.get("character_ids") or []),
                "voice_library": (voice_library or old.get("voice_library") or "default"),
                # 世界级兜底声音（优先级最低的一层）
                "default_voice_id": (old.get("default_voice_id") or "")
                                    if default_voice_id is None
                                    else (default_voice_id or "").strip(),
                "locked": bool(locked),
                "created_at": old.get("created_at") or _now(),
                "updated_at": _now(),
            }
            if isinstance(extra, dict):
                for k, v in extra.items():
                    if k not in ("world_id", "created_at"):
                        item[k] = v
            worlds[wid] = item
            ok = self._write()
            return ok, (json.loads(json.dumps(item, ensure_ascii=False)) if ok else None)

    def add_character_to_world(self, world_id, character_id):
        """把角色登记进某个世界的官方角色列表。"""
        cid = (character_id or "").strip()
        if not cid:
            return False
        with self._lock:
            self._reload_if_changed()
            worlds = self._data.setdefault("worlds", {})
            w = worlds.get((world_id or "").strip())
            if not isinstance(w, dict):
                return False
            ids = w.setdefault("character_ids", [])
            if not isinstance(ids, list):
                ids = []
                w["character_ids"] = ids
            if cid not in ids:
                ids.append(cid)
                w["updated_at"] = _now()
            return self._write()

    def remove_world(self, world_id):
        with self._lock:
            self._reload_if_changed()
            worlds = self._data.setdefault("worlds", {})
            existed = worlds.pop((world_id or "").strip(), None) is not None
            if existed:
                return self._write()
            return False

    def describe(self):
        with self._lock:
            self._reload_if_changed()
            worlds = self._data.get("worlds", {}) or {}
            return {
                "file": str(self.path),
                "version": self._data.get("version", SCHEMA_VERSION),
                "count": len(worlds),
                "worlds": json.loads(json.dumps(worlds, ensure_ascii=False)),
                "write_protected": self._write_guard is not None,
            }


# ==================== 单例 ====================
_default_manager = None
_default_lock = threading.RLock()


def get_world_manager(path=None):
    global _default_manager
    with _default_lock:
        if _default_manager is None or path is not None:
            _default_manager = WorldManager(path=path)
        return _default_manager


def set_world_manager(mgr):
    global _default_manager
    with _default_lock:
        _default_manager = mgr
    return _default_manager
