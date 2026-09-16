import os
import json
import time
import random
import threading
import asyncio
import shutil
import re
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles

class CacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200 and not path.lower().endswith((".html", ".js")):
            response.headers["Cache-Control"] = "public, max-age=604800"
        return response
from pydantic import BaseModel
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("DATA_DIR") or (BASE_DIR / "data"))
DATA_ROOT.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR = DATA_ROOT / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)

WORLD_ID = (os.environ.get("WORLD_ID") or "main").strip() or "main"
DATA_FILE = DATA_ROOT / (f"data_{WORLD_ID}.json" if WORLD_ID != "main" else "data.json")
AI_GATE = os.environ.get("AI_INTEGRATION_ENABLED") == "1"

# ========== 数据 ==========
data = {}
def default_data():
    return {
        "messages": {}, "rooms": {}, "avatars": {}, "online": {},
        "active_room": {"current": "main"}, "room_bg": {},
        "regions": {}, "buildings": {}, "npcs": {},
        "room_access": {}, "room_requests": {}, "user_ais": {},
        "time_settings": {}, "building_seq": 1, "note_seq": 1,
        "stories": {}, "notes": {}, "diaries": {},
        "edit_pwd": "", "edit_locked": False,
        "wallets": {}, "home_jobs": {}, "work_sessions": {},
        "work_history": [], "work_switch": {}, "visits": {},
        "sms": {}, "trails": {}, "messages_cache": {},
        "pairs": [], "pairs_admin": "",
        "server_id": "",
        "writing_rhythm": {},
        "visit_state": {}, "presence": {},
        "ai_enabled": False,
        "ai_living": True,
        "ai_keys": {},
        "ai_profiles": {},
        "worldbook": {},
        "ai_location": {},
        "ai_pending": [],
        "user_profiles": {},
        "prompt_injections": {},
        "world_lore": "",
        "ai_memories": {},
        "ai_timeline": {},
        "ai_visited": {},
        "ai_follow": {},
        "ai_pending_moves": {},
        "living_rhythm": {},
        # ====== 新增副本字段 ======
        "instances": {},      # 存储所有副本数据
        "user_tags": {},      # 存储每个用户的自定义标签列表
        "instance_bg": {},    # 存储每个用户的副本选择页背景
    }


def normalize_name(name: str) -> str:
    """
    将名字规范化为：去掉所有 emoji、变体选择器、零宽字符，保留纯文字。
    这个函数作为唯一的事实来源，所有地方统一使用。
    """
    if not name:
        return ""
    # 移除所有 emoji 和变体选择器（Unicode 范围）
    # 参考：https://unicode.org/emoji/charts/emoji-list.html
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # 表情符号
        "\U0001F300-\U0001F5FF"  # 符号 & 象形文字
        "\U0001F680-\U0001F6FF"  # 运输 & 地图符号
        "\U0001F700-\U0001F77F"  # 炼金术符号
        "\U0001F780-\U0001F7FF"  # 几何形状
        "\U0001F800-\U0001F8FF"  # 补充箭头
        "\U0001F900-\U0001F9FF"  # 补充符号 & 象形文字
        "\U0001FA00-\U0001FA6F"  # 扩展象形文字
        "\U0001FA70-\U0001FAFF"  # 扩展象形文字（续）
        "\U00002702-\U000027B0"  # 装饰符号
        "\U000024C2-\U0001F251"  # 围合字母数字
        "\uFE0F"                 # 变体选择器（关键！）
        "\u200B-\u200D"          # 零宽字符
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', name).strip()

def migrate_to_data_root():
    try:
        (DATA_ROOT / "images").mkdir(parents=True, exist_ok=True)
        (DATA_ROOT / "snapshots").mkdir(parents=True, exist_ok=True)
        for f in BASE_DIR.glob("data*.json"):
            dst = DATA_ROOT / f.name
            if dst != f and not dst.exists():
                shutil.copy2(f, dst)
        s_imgs = BASE_DIR / "images"
        if s_imgs.exists():
            for sub in s_imgs.iterdir():
                if sub.is_dir():
                    for f in sub.iterdir():
                        if f.is_file():
                            d = DATA_ROOT / "images" / sub.name / f.name
                            if not d.exists():
                                d.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(f, d)
        s_snap = BASE_DIR / "snapshots"
        if s_snap.exists():
            for f in s_snap.iterdir():
                if f.is_file():
                    d = DATA_ROOT / "snapshots" / f.name
                    if not d.exists():
                        shutil.copy2(f, d)
    except Exception as e:
        print(f"[WARN] migrate_to_data_root: {e}", flush=True)

def sanitize_data():
    try:
        data["messages"] = {r: [mm for mm in ms if isinstance(mm, dict)] for r, ms in data.get("messages", {}).items()}
        for name in list(data.get("rooms", {}).keys()):
            r = data["rooms"][name]
            if not isinstance(r, dict):
                data["rooms"][name] = {"creator": "?", "has_password": False, "password": "", "created": now_str(), "description": ""}
            else:
                r.setdefault("creator", "?"); r.setdefault("has_password", False); r.setdefault("password", ""); r.setdefault("created", now_str()); r.setdefault("description", "")
        data["work_history"] = [h for h in data.get("work_history", []) if isinstance(h, dict)]
        data["wallets"] = {k: (v if isinstance(v, (int, float)) else 0) for k, v in data.get("wallets", {}).items()}
        data["work_sessions"] = {k: v for k, v in data.get("work_sessions", {}).items() if isinstance(v, dict)}
        data["home_jobs"] = {k: v for k, v in data.get("home_jobs", {}).items() if isinstance(v, str)}
        data["work_switch"] = {k: bool(v) for k, v in data.get("work_switch", {}).items()}
        data["avatars"] = {k: (v if isinstance(v, str) else "") for k, v in data.get("avatars", {}).items()}
        data["user_ais"] = {k: (v if isinstance(v, list) else []) for k, v in data.get("user_ais", {}).items()}
        data["regions"] = {k: (v if isinstance(v, dict) else {}) for k, v in data.get("regions", {}).items()}
        data["buildings"] = {k: (v if isinstance(v, dict) else {}) for k, v in data.get("buildings", {}).items()}
        data["npcs"] = {k: (v if isinstance(v, list) else []) for k, v in data.get("npcs", {}).items()}
        # 值应为 list 的字段
        for key in ["notes", "diaries", "stories", "sms", "trails", "visits", "room_access", "room_requests", "worldbook", "prompt_injections", "ai_memories", "ai_timeline", "ai_visited"]:
            v = data.get(key)
            if isinstance(v, dict):
                for k2 in list(v.keys()):
                    if not isinstance(v[k2], list):
                        v[k2] = []
        # 值应为 dict 的字段（时间设置/写作节奏/访问状态/在线状态等）
        for key in ["ai_keys", "ai_profiles", "living_rhythm", "ai_follow", "ai_pending_moves", "writing_rhythm", "time_settings", "visit_state", "presence"]:
            v = data.get(key)
            if isinstance(v, dict):
                for k2 in list(v.keys()):
                    if not isinstance(v[k2], dict):
                        v[k2] = {}
        # 值应为字符串的字段（房间背景 URL / AI 位置 / 用户画像）
        for key in ["room_bg", "ai_location", "user_profiles"]:
            v = data.get(key)
            if isinstance(v, dict):
                for k2 in list(v.keys()):
                    if not isinstance(v[k2], str):
                        v[k2] = ""
        if not isinstance(data.get("world_lore"), str):
            data["world_lore"] = ""
        if not isinstance(data.get("ai_living"), bool):
            data["ai_living"] = True
        if not isinstance(data.get("pairs"), list):
            data["pairs"] = []
        if not isinstance(data.get("pairs_admin"), str):
            data["pairs_admin"] = ""
        if not isinstance(data.get("active_room"), dict):
            data["active_room"] = {"current": "main"}
        data["active_room"].setdefault("current", "main")
        if not isinstance(data.get("rooms"), dict):
            data["rooms"] = {}
        data["rooms"].setdefault("main", {"creator": "system", "has_password": False, "password": "", "created": now_str(), "description": "城市的公共大厅，所有人都在这里聊天。"})
        if not isinstance(data.get("ai_pending"), list):
            data["ai_pending"] = []
        if not isinstance(data.get("ai_enabled"), bool):
            data["ai_enabled"] = False
    except Exception as e:
        print(f"[WARN] sanitize_data: {e}", flush=True)

def load_data():
    global data
    try:
        migrate_to_data_root()
        if DATA_FILE.exists():
            try:
                data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = default_data()
        elif WORLD_ID != "main" and (DATA_ROOT / "data.json").exists():
            try:
                data = json.loads((DATA_ROOT / "data.json").read_text(encoding="utf-8"))
            except Exception:
                data = default_data()
        else:
            data = default_data()
        for k, v in default_data().items():
            data.setdefault(k, v)
        if not data.get("server_id"):
            data["server_id"] = "LK-" + WORLD_ID.upper() + "-" + ''.join(random.choice("0123456789ABCDEF") for _ in range(6))
        sanitize_data()
        migrate_room_prefix()
        ensure_admin()
        init_writing_rhythm()
        migrate_images()
        save_data()
    except Exception as e:
        print(f"[ERROR] load_data: {e}", flush=True)

# ========== 异步防抖写入 ==========
_save_timer = None
_save_pending = False

async def _do_save_async():
    """真正的异步写入：将阻塞操作扔到线程池执行"""
    global _save_pending
    try:
        def _sync_write():
            if DATA_FILE.exists():
                shutil.copyfile(DATA_FILE, str(DATA_FILE) + ".bak")
            DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        await asyncio.to_thread(_sync_write)
    except Exception as e:
        print(f"[WARN] save_data async: {e}", flush=True)
    finally:
        _save_pending = False

def save_data():
    """异步防抖写入：0.5秒内的多次调用合并为一次，且写入在后台线程执行"""
    global _save_timer, _save_pending
    _save_pending = True
    if _save_timer is not None:
        try:
            _save_timer.cancel()
        except Exception:
            pass
    def _schedule():
        global _save_timer, _save_pending
        _save_timer = None
        if _save_pending:
            try:
                # 获取当前事件循环，如果在异步上下文中则创建任务
                loop = asyncio.get_running_loop()
                asyncio.create_task(_do_save_async())
            except RuntimeError:
                # 没有运行中的事件循环，用线程安全方式
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(_do_save_async())
                    else:
                        loop.run_until_complete(_do_save_async())
                except Exception:
                    # 极端情况：直接同步写入（但几乎不会发生）
                    try:
                        if DATA_FILE.exists():
                            shutil.copyfile(DATA_FILE, str(DATA_FILE) + ".bak")
                        DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
                    except Exception as e:
                        print(f"[WARN] save_data fallback: {e}", flush=True)
    _save_timer = threading.Timer(0.5, _schedule)
    _save_timer.start()

def snapshot():
    try:
        name = f"auto_{WORLD_ID}_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
        (SNAPSHOT_DIR / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        files = sorted(SNAPSHOT_DIR.glob(f"auto_{WORLD_ID}_*.json"))
        for f in files[:-20]:
            f.unlink(missing_ok=True)
    except Exception:
        pass

def save_image_file(folder: Path, data_url: str, max_bytes: int = 3 * 1024 * 1024):
    try:
        m = re.match(r'data:image/(png|jpeg|jpg|webp|gif);base64,(.+)', data_url or '', re.S)
        if not m:
            return None
        ext = m.group(1)
        if ext == "jpeg":
            ext = "jpg"
        raw = base64.b64decode(m.group(2))
        if len(raw) > max_bytes:
            return None
        folder.mkdir(parents=True, exist_ok=True)
        fn = hashlib.md5(data_url.encode()).hexdigest()[:16] + "." + ext
        (folder / fn).write_bytes(raw)
        return "/images/" + folder.name + "/" + fn
    except Exception:
        return None

def migrate_images():
    try:
        av_dir = DATA_ROOT / "images" / "avatars"
        bg_dir = DATA_ROOT / "images" / "bg"
        av_dir.mkdir(parents=True, exist_ok=True)
        bg_dir.mkdir(parents=True, exist_ok=True)
        changed = False
        for name, val in data.get("avatars", {}).items():
            if isinstance(val, str) and val.startswith("data:image"):
                p = save_image_file(av_dir, val)
                if p:
                    data["avatars"][name] = p
                    changed = True
        for room, val in data.get("room_bg", {}).items():
            if isinstance(val, str) and val.startswith("data:image"):
                p = save_image_file(bg_dir, val)
                if p:
                    data["room_bg"][room] = p
                    changed = True
        if changed:
            save_data()
    except Exception as e:
        print(f"[WARN] migrate_images: {e}", flush=True)

# ========== 工具函数 ==========
def strip_emoji(s: str) -> str:
    return re.sub(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]', '', s or '').strip()
def canonical_ai_name(name: str) -> str:
    base = strip_emoji(name)
    for ais in data["user_ais"].values():
        for a in ais:
            if a == name or (base and strip_emoji(a) == base):
                return a
    return name
def canonical_contact_name(name: str) -> str:
    base = strip_emoji(name)
    if not base:
        return name
    candidates = set()
    for u in data["user_ais"].keys():
        if u:
            candidates.add(u)
    for b in data["buildings"].values():
        if b.get("owner"):
            candidates.add(b["owner"])
    candidates.discard("system")
    for c in candidates:
        if c == name or (base and strip_emoji(c) == base):
            return c
    return name
def canonical_name(name: str) -> str:
    n = canonical_ai_name(name)
    if n != name:
        return n
    return canonical_contact_name(name)
def is_ai_name(name: str) -> bool:
    base = strip_emoji(name)
    for ais in data["user_ais"].values():
        for a in ais:
            if a == name or (base and strip_emoji(a) == base):
                return True
    return False
def owner_of_ai(ai: str) -> str:
    base = strip_emoji(ai)
    for u, ais in data["user_ais"].items():
        for a in ais:
            if a == ai or (base and strip_emoji(a) == base):
                return u
    return ""
def is_ai_of(owner: str, name: str) -> bool:
    return name in data["user_ais"].get(owner, [])
def ensure_admin():
    if data.get("pairs_admin"):
        return
    for u in data["user_ais"].keys():
        if u and strip_emoji(u) == "亦言":
            data["pairs_admin"] = u
            return
    data["pairs_admin"] = "亦言❄️"
def is_admin(user: str) -> bool:
    u = canonical_contact_name((user or '').strip())
    admin = data.get("pairs_admin", "")
    return bool(u and admin and (u == admin or strip_emoji(u) == strip_emoji(admin)))
def migrate_room_prefix():
    try:
        changed = False
        for bid, b in data["buildings"].items():
            bname = b.get("name", "")
            if not bname:
                continue
            new_rooms = []
            for r in list(b.get("rooms", [])):
                if r.startswith(bname + "·"):
                    new_rooms.append(r)
                    continue
                nr = bname + "·" + r
                for key in ["rooms", "messages", "room_bg", "room_access", "room_requests", "notes", "diaries"]:
                    store = data.get(key)
                    if isinstance(store, dict) and r in store and nr not in store:
                        store[nr] = store.pop(r)
                new_rooms.append(nr)
                changed = True
            b["rooms"] = new_rooms
        if changed:
            save_data()
    except Exception:
        pass
def append_timeline(ai: str, text: str):
    try:
        ai = canonical_ai_name(ai or '')
        if not ai:
            return
        data.setdefault("ai_timeline", {}).setdefault(ai, []).append({"time": now_str(), "text": (text or "")[:200]})
        data["ai_timeline"][ai] = data["ai_timeline"][ai][-100:]
    except Exception:
        pass
def append_visited(ai: str, place: str):
    try:
        ai = canonical_ai_name(ai or '')
        place = (place or '').strip()
        if not ai or not place or not is_ai_name(ai):
            return
        items = data.setdefault("ai_visited", {}).setdefault(ai, [])
        if place in items:
            items.remove(place)
        items.insert(0, place)
        data["ai_visited"][ai] = items[:20]
    except Exception:
        pass
def init_writing_rhythm():
    try:
        data.setdefault("writing_rhythm", {})
        data.setdefault("living_rhythm", {})
        changed = False
        for ais in data["user_ais"].values():
            for ai in ais:
                if not ai:
                    continue
                if ai not in data["writing_rhythm"]:
                    data["writing_rhythm"][ai] = {"next_ts": time.time() + random.randint(3600, 21600), "type": random.choice(["note", "diary", "story"])}
                    changed = True
                if ai not in data["living_rhythm"]:
                    data["living_rhythm"][ai] = {"next_ts": time.time() + random.randint(900, 2700)}
                    changed = True
        if changed:
            save_data()
    except Exception:
        pass
def visit_leave(name: str):
    try:
        st = data.get("visit_state", {}).pop(name, None)
        if st and st.get("owner"):
            data["visits"].setdefault(st["owner"], []).append({"who": name, "arrive": st.get("arrive"), "action": st.get("action", "聊了天"), "leave": now_str()})
            data["visits"][st["owner"]] = data["visits"][st["owner"]][-50:]
            save_data()
    except Exception:
        pass
def track_visit(name: str, target: str):
    if not is_ai_name(name):
        return
    try:
        cur = data.get("visit_state", {}).get(name)
        cur_room = cur.get("room") if cur else None
        if target.endswith("·会客厅"):
            if cur_room != target:
                visit_leave(name)
                bid = find_building_of_room(target)
                if bid:
                    owner = data["buildings"][bid].get("owner")
                    if owner and owner != name and not is_ai_of(owner, name):
                        data.setdefault("visit_state", {})[name] = {"owner": owner, "room": target, "arrive": now_str(), "action": "聊了天"}
            else:
                if cur:
                    cur["action"] = "聊了天"
        elif cur_room and cur_room != target:
            visit_leave(name)
    except Exception:
        pass
def track_note(name: str):
    if is_ai_name(name):
        cur = data.get("visit_state", {}).get(name)
        if cur:
            cur["action"] = "留了张纸条"
def clean_room_name(name: str) -> str:
    return name.strip()
def room_exists(name: str) -> bool:
    return name in data["rooms"]
def now_str() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
def room_time(room: str) -> str:
    try:
        s = data["time_settings"].get(room) or data["time_settings"].get("main") or {}
        if s.get("mode") == "fixed" and s.get("fixed_time"):
            return s["fixed_time"]
    except Exception:
        pass
    return now_str()
def split_sms(text: str):
    text = (text or '').strip()
    if not text:
        return [""]
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if len(lines) > 1:
        return lines[:10]
    sentences = re.split(r'(?<=[。！？；～…!?])', text)
    out = [s.strip() for s in sentences if s.strip()]
    if len(out) > 1:
        return out[:10]
    return [text]
def find_building_of_room(room: str):
    for bid, b in data["buildings"].items():
        if room in b.get("rooms", []):
            return bid
    return None
def building_owner_of_room(room: str) -> str:
    try:
        bid = find_building_of_room(room)
        if bid:
            return data.get("buildings", {}).get(bid, {}).get("owner", "")
    except Exception:
        pass
    return ""
def can_access_room(room: str, user: str) -> bool:
    if room == "main":
        return True
    bid = find_building_of_room(room)
    if bid is None:
        return True
    b = data["buildings"][bid]
    if b.get("type") == "npc":
        return True
    if room.endswith("·会客厅"):
        return True
    if b.get("owner") == user:
        return True
    acc = data["room_access"].get(room, [])
    if user in acc:
        return True
    for granted in acc:
        if is_ai_of(granted, user):
            return True
    return False
def can_view_room(room: str, user: str) -> bool:
    return can_access_room(room, user)
def resolve_building(key):
    key = (key or '').strip()
    if not key:
        return None
    if key in data["buildings"]:
        return key
    for bid, b in data["buildings"].items():
        if b.get("name") == key:
            return bid
    for bid, b in data["buildings"].items():
        if key in b.get("name", ""):
            return bid
    return None
def next_bid():
    max_n = 0
    for bid in data["buildings"].keys():
        if bid.startswith("b"):
            try:
                max_n = max(max_n, int(bid[1:]))
            except ValueError:
                pass
    return "b" + str(max_n + 1)
def full_room_name(room: str) -> str:
    room = clean_room_name(room)
    if not room:
        return room
    if room in data["rooms"]:
        return room
    for bid, b in data["buildings"].items():
        bname = b.get("name", "")
        for r in b.get("rooms", []):
            if r == room or (bname and r == bname + "·" + room):
                return r
    return room
def online_room_count(room: str) -> int:
    try:
        return len([n for n, v in data.get("online", {}).items() if v.get("room") == room and time.time() - v.get("time", 0) < 45])
    except Exception:
        return 0
def check_pending_moves():
    try:
        now = time.time()
        changed = False
        for ai in list(data.get("ai_pending_moves", {}).keys()):
            mv = data["ai_pending_moves"][ai]
            if now >= mv.get("at_ts", 0):
                r = mv.get("room", "")
                if room_exists(r):
                    data.setdefault("ai_location", {})[ai] = r
                    append_timeline(ai, f"你回到了 {r}")
                    append_visited(ai, r)
                    data["messages"].setdefault(r, []).append({"sender": "system", "content": f"📍 {ai} 来到了 {r}", "role": "system", "time": room_time(r)})
                data["ai_pending_moves"].pop(ai, None)
                changed = True
        if changed:
            save_data()
    except Exception:
        pass
def add_trail(user: str, text: str, room: str = "", tab: str = ""):
    if not user or user == "system":
        return
    data["trails"].setdefault(user, []).append({"ts": time.time(), "time": now_str(), "text": text[:200], "room": room, "tab": tab})
    cutoff = time.time() - 7 * 86400
    data["trails"][user] = [t for t in data["trails"][user] if t.get("ts", 0) >= cutoff][-100:]
def ai_integration_enabled() -> bool:
    if not AI_GATE:
        return False
    return bool(data.get("ai_enabled"))

# ========== 模型 ==========
class MessageIn(BaseModel): sender: str; content: str; role: str = "user"; room: str = "main"; password: str = ""
class RoomCreate(BaseModel): name: str; password: str = ""; creator: str = ""
class RoomJoin(BaseModel): name: str; password: str = ""
class RoomDelete(BaseModel): name: str; password: str = ""
class RemoveMember(BaseModel): name: str; room: str = "main"; password: str = ""
class DeleteMsg(BaseModel): room: str; sender: str; content: str; time: str; user: str
class RestoreIn(BaseModel): messages: list; room: str = "main"; password: str = ""
class NameIn(BaseModel): name: str; image: str = ""
class AvatarIn(BaseModel): name: str; image: str
class HeartIn(BaseModel): name: str; room: str = "main"
class RoomNameIn(BaseModel): room: str; password: str = ""
class RegionIn(BaseModel): label: str; x: float; y: float; image: str = ""
class RegionDel(BaseModel): label: str
class BuildingIn(BaseModel): name: str; emoji: str; type: str; region: str = ""; x: float; y: float; owner: str = ""; description: str = ""
class BuildingRename(BaseModel): building_id: str; name: str
class BuildingMove(BaseModel): building_id: str; x: float; y: float
class BuildingDesc(BaseModel): building_id: str; description: str
class BuildingFeatures(BaseModel): building_id: str; features: list = []; salary: float = 0
class BuildingNotice(BaseModel): building_id: str; notice: str = ""
class BuildingDel(BaseModel): building_id: str
class BuildingRoomIn(BaseModel): building_id: str; name: str
class BuildingRoomDel(BaseModel): building_id: str; room: str
class RoomDescIn(BaseModel): room: str; description: str
class RoomBgIn(BaseModel): room: str; image: str
class NpcIn(BaseModel): building_id: str; name: str; emoji: str = "👤"; desc: str = ""
class NpcEdit(BaseModel): building_id: str; name: str; new_name: str; emoji: str; desc: str
class NpcDel(BaseModel): building_id: str; name: str
class NoteIn(BaseModel): room: str; author: str; text: str
class NoteReplyIn(BaseModel): room: str; note_id: str; author: str; text: str
class DiaryComment(BaseModel): room: str; index: int; author: str; text: str
class StoryIn(BaseModel): building_id: str; author: str; text: str
class RoomApply(BaseModel): room: str; applicant: str
class GrantIn(BaseModel): room: str; owner: str; user: str; allow: bool = True
class RevokeIn(BaseModel): room: str; owner: str; user: str
class UserAisIn(BaseModel): user: str; ais: list = []
class EditPwdIn(BaseModel): pwd: str
class TimeSet(BaseModel): mode: str = "real"; fixed_time: str = ""; room: str = "main"
class SummonIn(BaseModel): ai: str; room: str = "main"
class WorkStart(BaseModel): name: str; building_id: str; hours: int = 2
class WorkStop(BaseModel): name: str
class WorkAuto(BaseModel): name: str
class WorkSwitch(BaseModel): name: str; on: bool = True
class HomeJobIn(BaseModel): user: str = ""; ai: str = ""; building_id: str
class SmsIn(BaseModel): sender: str; to: str; text: str
class SmsClearIn(BaseModel): user: str; contact: str
class PairsIn(BaseModel): user: str; pairs: list = []
class PresenceIn(BaseModel): name: str; page: str = "main"
class AiKeyIn(BaseModel): user: str; provider: str = "deepseek"; key: str = ""; model: str = ""
class AiProfileIn(BaseModel): owner: str; ai: str; persona: str = ""
class WorldbookIn(BaseModel): owner: str; keys: str; content: str
class AiToggleIn(BaseModel): user: str; enabled: bool
class AdminNameIn(BaseModel): user: str; from_name: str; to_name: str
class AdminDelIn(BaseModel): user: str; name: str

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
(DATA_ROOT / "images").mkdir(parents=True, exist_ok=True)
app.mount("/images", CacheStaticFiles(directory=str(DATA_ROOT / "images")), name="images")

# ========== AI 唤醒钩子（由 ext_ai 插件注册） ==========
_ai_wake_hook = None
def set_ai_wake_hook(fn):
    global _ai_wake_hook
    _ai_wake_hook = fn

def _maybe_wake_ai(room, sender, content):
    h = _ai_wake_hook
    if h:
        try:
            return h(room, sender, content)   # ← 返回 task_id
        except Exception as e:
            print(f"[WARN] AI wake hook: {e}", flush=True)
    return None

# ========== 基础路由 ==========
@app.get("/")
async def root(): return FileResponse(BASE_DIR / "index.html")

@app.get("/api/health")
async def health():
    return {"ok": True, "rooms": len(data["rooms"]), "world": WORLD_ID, "v": "v2-core"}

@app.post("/api/presence")
async def set_presence(p: PresenceIn):
    name = (p.name or '').strip()
    page = (p.page or '').strip() or 'main'
    if name:
        data.setdefault("presence", {})[name] = {"page": page, "ts": time.time()}
        data["presence"] = {k: v for k, v in data["presence"].items() if time.time() - v.get("ts", 0) < 25}
    return {"ok": True}

@app.get("/api/presence")
async def get_presence():
    data["presence"] = {k: v for k, v in data["presence"].items() if time.time() - v.get("ts", 0) < 25}
    return {"presence": [{"name": k, "page": v.get("page", "main")} for k, v in data["presence"].items()]}

@app.get("/api/messages")
async def get_messages(room: str = "main", password: str = "", user: str = ""):
    room = clean_room_name(room)
    if not room_exists(room):
        raise HTTPException(404, "房间不存在")
    r = data["rooms"][room]
    if r.get("has_password") and r.get("password") != password:
        raise HTTPException(403, "密码错误")
    if not can_view_room(room, user):
        raise HTTPException(403, "没有权限查看这个房间")
    msgs = data["messages"].get(room, [])
    return {"messages": msgs[-300:]}

@app.post("/api/messages")
async def send_message(m: MessageIn):
    room = clean_room_name(m.room)
    if not room_exists(room):
        raise HTTPException(404, "房间不存在")
    r = data["rooms"][room]
    if r.get("has_password") and r.get("password") != m.password:
        raise HTTPException(403, "密码错误")
    if not can_view_room(room, m.sender):
        raise HTTPException(403, "没有权限进入这个房间")
    content = m.content.strip()
    if not content:
        raise HTTPException(400, "消息不能为空")
    msg = {"sender": m.sender, "content": content[:1000], "role": m.role, "time": room_time(room)}
    data["messages"].setdefault(room, []).append(msg)
    data["active_room"]["current"] = room
    save_data()
    task_id = None
    if m.role == "user":
        task_id = _maybe_wake_ai(room, m.sender, content)
    return {"ok": True, "time": msg["time"], "count": len(data["messages"][room]), "task_id": task_id}

@app.post("/api/messages/delete")
async def delete_message(dm: DeleteMsg):
    room = clean_room_name(dm.room)
    if not room_exists(room):
        raise HTTPException(404, "房间不存在")
    bid = find_building_of_room(room)
    if bid is None:
        raise HTTPException(403, "只有房主可以删除房间消息")
    if data["buildings"][bid].get("owner") != dm.user:
        raise HTTPException(403, "只有房主可以删除")
    before = len(data["messages"].get(room, []))
    data["messages"][room] = [m for m in data["messages"].get(room, [])
                               if not (m.get("sender") == dm.sender and m.get("content") == dm.content and m.get("time") == dm.time)]
    save_data()
    return {"ok": True, "deleted": before - len(data["messages"].get(room, []))}

@app.post("/api/restore")
async def restore_messages(r: RestoreIn):
    room = clean_room_name(r.room)
    if not room_exists(room):
        return {"ok": False, "reason": "no_room"}
    rr = data["rooms"][room]
    if rr.get("has_password") and rr.get("password") != r.password:
        return {"ok": False, "reason": "bad_pwd"}
    cur = data["messages"].get(room, [])
    got = [m for m in r.messages if isinstance(m, dict) and m.get("sender") != "system"]
    cur_senders = {(m.get("sender"), m.get("content"), m.get("time")) for m in cur}
    added = 0
    for m in got:
        key = (m.get("sender"), m.get("content"), m.get("time"))
        if key not in cur_senders:
            cur.append({"sender": m.get("sender", "?"), "content": m.get("content", ""), "role": m.get("role", "user"), "time": m.get("time", now_str())})
            cur_senders.add(key)
            added += 1
    data["messages"][room] = cur[-500:]
    save_data()
    return {"ok": True, "added": added}

@app.get("/api/rooms")
async def get_rooms():
    out = []
    for name, r in data["rooms"].items():
        out.append({"name": name, "creator": r.get("creator", ""), "has_password": bool(r.get("has_password")), "description": r.get("description", ""), "created": r.get("created", "")})
    return {"rooms": out}

@app.post("/api/rooms/create")
@app.post("/api/rooms")
async def create_room(rc: RoomCreate):
    name = clean_room_name(rc.name)
    if not name:
        raise HTTPException(400, "房间名字不能为空")
    if room_exists(name):
        raise HTTPException(400, "房间已存在")
    data["rooms"][name] = {"creator": rc.creator, "has_password": bool(rc.password), "password": rc.password, "created": now_str(), "description": ""}
    data["messages"].setdefault(name, [])
    save_data()
    return {"ok": True, "room": name}

@app.post("/api/rooms/join")
async def join_room(rj: RoomJoin):
    name = clean_room_name(rj.name)
    if not room_exists(name):
        raise HTTPException(404, "房间不存在")
    r = data["rooms"][name]
    if r.get("has_password") and r.get("password") != rj.password:
        raise HTTPException(403, "密码错误")
    return {"ok": True, "room": name}

@app.post("/api/rooms/delete")
async def delete_room(rd: RoomDelete):
    name = clean_room_name(rd.name)
    if not room_exists(name):
        return {"ok": False}
    r = data["rooms"][name]
    if r.get("creator") == "system":
        raise HTTPException(403, "不能删除公共大厅")
    if r.get("has_password") and r.get("password") != rd.password:
        raise HTTPException(403, "密码错误")
    data["messages"].pop(name, None)
    data["room_bg"].pop(name, None)
    data.pop(name, None)
    data["rooms"].pop(name, None)
    save_data()
    return {"ok": True}

@app.post("/api/remove_member")
async def remove_member(rm: RemoveMember):
    name = clean_room_name(rm.room)
    if not room_exists(name):
        return {"ok": False}
    r = data["rooms"][name]
    if r.get("has_password") and r.get("password") != rm.password:
        raise HTTPException(403, "密码错误")
    data["messages"][name] = [m for m in data["messages"].get(name, []) if m.get("sender") != rm.name]
    save_data()
    return {"ok": True}

@app.post("/api/current_room")
async def current_room(rn: RoomNameIn):
    data["active_room"]["current"] = clean_room_name(rn.room)
    save_data()
    return {"ok": True}

@app.post("/api/heartbeat")
async def heartbeat(h: HeartIn):
    name = h.name.strip()
    data["online"][name] = {"time": time.time(), "room": clean_room_name(h.room)}
    data["online"] = {k: v for k, v in data["online"].items() if time.time() - v.get("time", 0) < 45}
    return {"ok": True}

@app.get("/api/online")
async def get_online():
    data["online"] = {k: v for k, v in data["online"].items() if time.time() - v.get("time", 0) < 45}
    return {"online": [{"name": k, "room": v.get("room", "main")} for k, v in data["online"].items()]}

@app.get("/api/avatar")
async def get_avatar():
    return JSONResponse(content={"avatars": data["avatars"]}, headers={"Cache-Control": "public, max-age=300"})

@app.post("/api/avatar")
async def set_avatar(a: AvatarIn):
    val = a.image or ""
    if val.startswith("data:image"):
        p = save_image_file(DATA_ROOT / "images" / "avatars", val)
        if p:
            val = p
    data["avatars"][a.name] = val
    save_data()
    return {"ok": True, "url": val}

@app.get("/api/edit_status")
async def edit_status():
    return {"locked": bool(data["edit_locked"])}

@app.post("/api/set_edit_pwd")
async def set_edit_pwd(p: EditPwdIn):
    data["edit_pwd"] = p.pwd
    data["edit_locked"] = True
    save_data()
    return {"ok": True, "locked": True}

@app.post("/api/check_edit_pwd")
async def check_edit_pwd(p: EditPwdIn):
    return {"ok": data["edit_pwd"] == p.pwd}

@app.get("/api/time_settings")
async def get_time(room: str = "main"):
    return {"settings": data["time_settings"].get(room, {})}

@app.post("/api/time_settings")
async def set_time(t: TimeSet):
    data["time_settings"][t.room] = {"mode": t.mode, "fixed_time": t.fixed_time}
    save_data()
    return {"ok": True}

@app.get("/api/backup")
async def backup(user: str = "", pwd: str = ""):
    import os
    dev_pwd = os.environ.get('DEV_PASSWORD') or 'yiyan610116'
    # ===== 安全验证：必须同时满足：1) 是管理员 2) 密码正确 =====
    if not is_admin(user):
        raise HTTPException(403, "只有站长可以查看备份")
    if pwd != dev_pwd:
        raise HTTPException(403, "开发者密码错误")
    # ===========================================================
    return data

@app.get("/api/backup/list")
async def backup_list(user: str = ""):
    if not is_admin(user):
        raise HTTPException(403, "只有站长可以查看服务器快照")
    files = sorted(SNAPSHOT_DIR.glob(f"auto_{WORLD_ID}_*.json"), reverse=True)
    return {"backups": [{"name": f.name, "size": f.stat().st_size} for f in files[:20]]}

@app.post("/api/restore_backup")
async def restore_backup(d: dict):
    if not is_admin(d.get("user", "")):
        raise HTTPException(403, "只有站长可以恢复备份")
    for k, v in d.items():
        if k not in ("user", "ts"):
            data[k] = v
    for k, v in default_data().items():
        data.setdefault(k, v)
    sanitize_data()
    migrate_room_prefix()
    ensure_admin()
    init_writing_rhythm()
    save_data()
    return {"ok": True}

# ========== 插件系统 ==========
_ext_names = []
def _load_extensions():
    global _ext_names
    import importlib.util
    ext_dir = BASE_DIR / "ext"
    if not ext_dir.exists():
        return
    helpers = {
        "default_data": default_data, "sanitize_data": sanitize_data,
        "migrate_room_prefix": migrate_room_prefix, "ensure_admin": ensure_admin,
        "init_writing_rhythm": init_writing_rhythm, "migrate_images": migrate_images,
        "DATA_ROOT": DATA_ROOT, "save_data": save_data,
    }
    for f in sorted(ext_dir.glob("*.py")):
        if f.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location("ext_" + f.stem, f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "setup"):
                mod.setup(app, data, helpers)
                _ext_names.append(f.name)
                print(f"[ext] 已加载 {f.name}", flush=True)
        except Exception as e:
            print(f"[ext] 加载 {f.name} 失败: {e}", flush=True)

# ========== 启动 ==========
load_data()
print(f"[Linkong] v2-core 启动 | world={WORLD_ID} | AI_GATE={AI_GATE} | data_root={DATA_ROOT} | file={DATA_FILE.name}", flush=True)

_load_extensions()

def snapshot_loop():
    while True:
        time.sleep(1800)
        snapshot()
threading.Thread(target=snapshot_loop, daemon=True).start()

def run():
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

if __name__ == "__main__":
    run()
