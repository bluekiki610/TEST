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

    # ---------- 记忆库 · 副本回顾（只读；展开章节看当时的详细对话） ----------
    def _slice_chapter_msgs(history, chapter_start_round, chapter_end_round):
        """按「用户消息作为一轮开始」切片出一章的对话。

        ⚠️ 这里与 ext_instance.py 的 _slice_instance_chapter_msgs 是同一套语义
        （ext_mem 比 ext_instance 先加载，无法直接 import，故各自保留一份）。
        两处必须保持一致，否则「展开的对话」会和「这一章的总结」对不上。
        本项目「一轮 = 从一条 user 消息到下一条 user 消息之前」。
        """
        history = history or []
        user_idxs = [i for i, mm in enumerate(history) if mm.get("role") == "user"]
        if not user_idxs:
            return []
        start_pos = chapter_start_round - 1
        end_pos = chapter_end_round  # exclusive
        if start_pos < 0 or start_pos >= len(user_idxs):
            return []
        start_idx = user_idxs[start_pos]
        end_idx = user_idxs[end_pos] if end_pos < len(user_idxs) else len(history)
        return history[start_idx:end_idx]

    def _agg_instance_chapters(inst):
        out = []
        for c in (inst.get("chapters") or []):
            msgs = _slice_chapter_msgs(
                inst.get("chat_history", []),
                c.get("round_start", 1),
                c.get("round_end", 0)
            )
            out.append({
                "chapter": c.get("chapter"),
                "title": c.get("title") or ("第%s章" % c.get("chapter")),
                "summary": c.get("summary") or "",
                "round_start": c.get("round_start"),
                "round_end": c.get("round_end"),
                "time": c.get("time") or "",
                "messages": [
                    {
                        "sender": mm.get("sender", "?"),
                        "content": mm.get("content", ""),
                        "time": mm.get("time", ""),
                        "role": mm.get("role", "")
                    }
                    for mm in msgs if mm.get("content")
                ]
            })
        return out

    @app.get("/api/memory/instances")
    async def memory_instances(user: str = ""):
        """记忆库「副本」页：列出该用户已结束的副本（只读回顾用）。"""
        u = canonical_contact_name((user or '').strip())
        if not u:
            return {"ok": False, "instances": []}
        out = []
        for iid, inst in (data.get("instances", {}).get(u, {}) or {}).items():
            if not (inst.get("finished") or inst.get("status") == "ended"):
                continue
            ai_name = ""
            for p in (inst.get("participants") or []):
                if p.get("type") == "ai":
                    ai_name = p.get("name", "")
                    break
            out.append({
                "iid": iid,
                "name": inst.get("name", "未命名"),
                "cover": inst.get("cover", ""),
                "ai": ai_name,
                "tags": inst.get("tags", []) or [],
                "summary": inst.get("summary", "") or "",
                "chapter_count": len(inst.get("chapters") or []),
                "round_count": inst.get("round_count", 0),
                "ended_at": inst.get("ended_at", "") or inst.get("created_at", ""),
                "created_at": inst.get("created_at", "") or ""
            })
        out.sort(key=lambda x: x.get("ended_at") or x.get("created_at") or "", reverse=True)
        return {"ok": True, "instances": out}

    @app.get("/api/memory/instance")
    async def memory_instance_detail(user: str = "", iid: str = ""):
        """单个副本的回顾详情：最终总结 + 每章总结 + 该章详细对话。"""
        u = canonical_contact_name((user or '').strip())
        if not u or not iid:
            return {"ok": False, "msg": "缺少参数"}
        inst = (data.get("instances", {}).get(u, {}) or {}).get(iid)
        if not inst:
            return {"ok": False, "msg": "副本不存在"}
        ai_name = ""
        for p in (inst.get("participants") or []):
            if p.get("type") == "ai":
                ai_name = p.get("name", "")
                break
        return {
            "ok": True,
            "iid": iid,
            "name": inst.get("name", "未命名"),
            "cover": inst.get("cover", ""),
            "ai": ai_name,
            "status": inst.get("status", ""),
            "background": inst.get("background", "") or "",
            "premise": inst.get("premise", "") or "",
            "summary": inst.get("summary", "") or "",
            "participants": inst.get("participants", []) or [],
            "round_count": inst.get("round_count", 0),
            "ended_at": inst.get("ended_at", "") or "",
            "chapters": _agg_instance_chapters(inst)
        }

    @app.post("/api/memory/instance/delete")
    async def memory_instance_delete(body: dict):
        """删除整份副本记录（用户在记忆库里回顾后不想要了）。"""
        u = canonical_contact_name((body.get("user") or "").strip())
        iid = (body.get("iid") or "").strip()
        if not u or not iid:
            return {"ok": False, "msg": "缺少参数"}
        insts = data.get("instances", {}).get(u, {})
        if iid not in insts:
            return {"ok": False, "msg": "副本不存在"}
        insts.pop(iid, None)
        save_data()
        print(f"[ext_mem] 记忆库删除副本 {iid} (user={u})", flush=True)
        return {"ok": True}

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
