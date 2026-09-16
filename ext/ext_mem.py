# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：记忆库 / 用户画像 / 提示词注入 / 世界观 / TTS
import re
import json
import urllib.request


def setup(app, data, helpers):
    import main as m
    from main import (canonical_contact_name, canonical_ai_name, now_str, save_data,
                      is_admin, building_owner_of_room, full_room_name)

    @app.get("/api/ai/memory")
    async def memory_get(owner: str, ai: str = ""):
        o = canonical_contact_name((owner or '').strip())
        items = data.get("ai_memories", {}).get(o, [])
        if ai:
            a = canonical_ai_name(ai)
            items = [mm for mm in items if mm.get("ai") == a]
        return {"memories": items}

    @app.post("/api/ai/memory")
    async def memory_add(bb: dict):
        o = canonical_contact_name((bb.get("owner") or '').strip())
        a = canonical_ai_name(bb.get("ai") or '')
        if not o or not a or not (bb.get("text") or '').strip():
            return {"ok": False, "msg": "缺少内容"}
        data.setdefault("ai_memories", {}).setdefault(o, []).append({"id": str(int(time.time() * 1000)), "ai": a, "text": (bb.get("text") or "")[:200], "type": bb.get("type") or "user", "time": now_str()})
        data["ai_memories"][o] = data["ai_memories"][o][-60:]
        save_data()
        return {"ok": True}

    @app.post("/api/ai/memory/edit")
    async def memory_edit(bb: dict):
        o = canonical_contact_name((bb.get("owner") or '').strip())
        items = data.setdefault("ai_memories", {}).setdefault(o, [])
        for mm in items:
            if str(mm.get("id")) == str(bb.get("id")):
                mm["text"] = (bb.get("text") or "")[:200]
                break
        save_data()
        return {"ok": True}

    @app.post("/api/ai/memory/delete")
    async def memory_del(bb: dict):
        o = canonical_contact_name((bb.get("owner") or '').strip())
        items = data.setdefault("ai_memories", {}).setdefault(o, [])
        data["ai_memories"][o] = [mm for mm in items if str(mm.get("id")) != str(bb.get("id"))]
        save_data()
        return {"ok": True}

    @app.get("/api/memories")
    async def memories_all(user: str):
        u = canonical_contact_name((user or '').strip())
        mine = {u} | set(data.get("user_ais", {}).get(u, []))
        mems = data.get("ai_memories", {}).get(u, [])
        notes, diaries, stories = [], [], []
        for room, items in data.get("notes", {}).items():
            for i, n in enumerate(items):
                if n.get("author") in mine:
                    notes.append({"room": room, "index": i, "author": n.get("author"), "text": n.get("text"), "time": n.get("time")})
        for room, items in data.get("diaries", {}).items():
            for i, n in enumerate(items):
                if n.get("author") in mine:
                    diaries.append({"room": room, "index": i, "author": n.get("author"), "text": n.get("text"), "time": n.get("time")})
        for bid, items in data.get("stories", {}).items():
            bname = data.get("buildings", {}).get(bid, {}).get("name", bid)
            for i, n in enumerate(items):
                if n.get("author") in mine:
                    stories.append({"building_id": bid, "building": bname, "index": i, "author": n.get("author"), "text": n.get("text"), "time": n.get("time")})
        return {"memories": mems, "notes": notes[-50:][::-1], "diaries": diaries[-50:][::-1], "stories": stories[-50:][::-1]}

    @app.get("/api/user/profile")
    async def user_profile_get(user: str):
        u = canonical_contact_name((user or '').strip())
        return {"profile": data.get("user_profiles", {}).get(u, "")}

    @app.post("/api/user/profile")
    async def user_profile_set(bb: dict):
        u = canonical_contact_name((bb.get("user") or '').strip())
        data.setdefault("user_profiles", {})[u] = (bb.get("content") or "")[:2000]
        save_data()
        return {"ok": True}

    @app.get("/api/prompt_inject")
    async def prompt_inject_get(user: str):
        u = canonical_contact_name((user or '').strip())
        return {"items": data.get("prompt_injections", {}).get(u, [])}

    @app.post("/api/prompt_inject")
    async def prompt_inject_set(bb: dict):
        u = canonical_contact_name((bb.get("user") or '').strip())
        items = data.setdefault("prompt_injections", {}).setdefault(u, [])
        items.append({"id": str(int(time.time() * 1000)), "title": (bb.get("title") or "")[:50], "content": (bb.get("content") or "")[:1000], "enabled": bool(bb.get("enabled", True))})
        data["prompt_injections"][u] = items[-30:]
        save_data()
        return {"ok": True}

    @app.post("/api/prompt_inject/toggle")
    async def prompt_inject_toggle(bb: dict):
        u = canonical_contact_name((bb.get("user") or '').strip())
        items = data.setdefault("prompt_injections", {}).setdefault(u, [])
        for it in items:
            if str(it.get("id")) == str(bb.get("id")):
                it["enabled"] = bool(bb.get("enabled", not it.get("enabled", True)))
        save_data()
        return {"ok": True}

    @app.post("/api/prompt_inject/delete")
    async def prompt_inject_del(bb: dict):
        u = canonical_contact_name((bb.get("user") or '').strip())
        items = data.setdefault("prompt_injections", {}).setdefault(u, [])
        data["prompt_injections"][u] = [it for it in items if str(it.get("id")) != str(bb.get("id"))]
        save_data()
        return {"ok": True}

    @app.get("/api/world/lore")
    async def world_lore_get(user: str = ""):
        if not is_admin(user):
            return {"ok": False, "msg": "只有站长可以查看世界观"}
        return {"lore": data.get("world_lore", "")}

    @app.post("/api/world/lore")
    async def world_lore_set(bb: dict):
        if not is_admin(bb.get("user", "")):
            return {"ok": False, "msg": "只有站长可以设置世界观"}
        data["world_lore"] = (bb.get("lore") or "")[:3000]
        save_data()
        return {"ok": True}

    @app.get("/api/tts")
    async def tts(text: str = "", user: str = "", voice: str = ""):
        u = canonical_contact_name((user or '').strip())
        cfg = data.get("ai_keys", {}).get(u)
        if not cfg or not cfg.get("key"):
            return {"ok": False, "msg": "请先填 API Key"}
        if not text:
            return {"ok": False, "msg": "text 不能为空"}
        url = "https://api.siliconflow.cn/v1/audio/speech"
        body = json.dumps({"model": voice or "FunAudioLLM/CosyVoice2-0.5B", "input": text[:500], "response_format": "mp3"}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg["key"]})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                audio = resp.read()
            from fastapi.responses import Response
            return Response(content=audio, media_type="audio/mpeg")
        except Exception as e:
            return {"ok": False, "msg": f"TTS 失败：{e}"}

    print("[ext_mem] 记忆/画像/注入/世界观/TTS 已注册", flush=True)
