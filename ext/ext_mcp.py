# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：MCP 工具（group_send / group_query / group_write / group_access）
import time
import random


def setup(app, data, helpers):
    import main as m
    from main import (full_room_name, room_exists, can_access_room, can_view_room, now_str,
                      room_time, resolve_building, canonical_name, canonical_contact_name,
                      is_ai_name, split_sms, add_trail, track_visit, append_timeline,
                      append_visited, save_data, online_room_count)

    def group_send(sender, content, room=""):
        target = room.strip() if room and room.strip() else data["active_room"].get("current", "main")
        target = full_room_name(target)
        if not room_exists(target):
            return f"❌ 房间「{target}」不存在。先 group_query(type=map) 看看有哪些地方。"
        if target != "main" and not can_access_room(target, sender):
            return f"🔒 房间「{target}」是私密的，你没有权限。请先调用 group_access 申请。"
        msg = {"sender": sender, "content": content[:1000], "role": "assistant", "time": room_time(target)}
        data["messages"].setdefault(target, []).append(msg)
        data["active_room"]["current"] = target
        add_trail(sender, f"在 {target} 说话：{content[:50]}", room=target)
        track_visit(sender, target)
        append_timeline(sender, f"你在 {target} 说：{content[:50]}")
        append_visited(sender, target)
        save_data()
        return f"✅ 已在「{target}」发言。"

    def group_query(type, sender, room="", building_id="", count=10):
        try:
            if type == "map":
                regions = "\n".join(f"📍 {n}" for n, v in data["regions"].items()) or "（还没有区域）"
                buildings = "\n".join(f"{bid}·{b.get('emoji','🏠')} {b.get('name')} [{'公共' if b.get('type')=='npc' else '住宅'}·{b.get('region') or '总览区'}·{b.get('description','')[:40]}]" for bid, b in data["buildings"].items()) or "（还没有建筑）"
                return f"🗺️ 临空市地图\n\n📍 区域：\n{regions}\n\n🏗️ 建筑：\n{buildings}"
            if type == "rooms":
                return "📋 所有房间：\n" + "\n".join(f"· {n}" for n in data["rooms"].keys())
            if type == "current_room":
                return f"📍 真人现在在：{data['active_room'].get('current','main')}"
            if type == "members":
                names = [n for n, v in data["online"].items() if time.time() - v.get("time", 0) < 45]
                return "👥 在线成员：" + ("、".join(names) if names else "（当前无人在线）")
            if type == "room":
                r = full_room_name(room)
                if not room_exists(r):
                    return f"❌ 房间「{r}」不存在"
                if not can_view_room(r, sender):
                    return f"🔒 房间「{r}」是私密的，你没有权限。"
                msgs = data["messages"].get(r, [])
                if not msgs:
                    return f"🏠 房间「{r}」\n💬 还没有消息。"
                return f"🏠 房间「{r}」\n💬 最近消息：\n" + "\n".join(f"{mm.get('time','')} {mm.get('sender','?')}: {mm.get('content','')}" for mm in msgs[-count:])
            if type == "building":
                bid = resolve_building(building_id)
                if not bid:
                    return "❌ 建筑不存在（可传 b1 或建筑名字）"
                b = data["buildings"][bid]
                rooms = "\n".join(f"· {x}" for x in b.get("rooms", [])) or "（无房间）"
                npcs = "\n".join(f"· {n.get('emoji','👤')} {n.get('name')}：{n.get('desc','')}" for n in data["npcs"].get(bid, [])) or "（无NPC）"
                feats = ",".join(b.get("features", [])) or "无"
                return f"🏗️ {b.get('emoji')} {b.get('name')}（{'公共' if b.get('type')=='npc' else '住宅'}）\n📝 {b.get('description','')}\n⚙️ 功能：{feats} · 时薪：{b.get('salary',0)}\n🚪 房间：\n{rooms}\n👥 NPC：\n{npcs}"
            if type == "story":
                bid = resolve_building(building_id)
                sts = data["stories"].get(bid, []) if bid else []
                if not sts:
                    return "🎬 剧情簿还是空的"
                return "\n".join(f"{s.get('time')} {s.get('author')}: {s.get('text')}" for s in sts[-count:])
            if type == "notes":
                items = data["notes"].get(room, [])
                if not items:
                    return "💌 便签墙还是空的"
                return "\n".join(f"✍️ {n.get('author')}：{n.get('text')}（{n.get('time')}）" for n in items[-count:])
            if type == "diaries":
                items = data["diaries"].get(room, [])
                if not items:
                    return "📖 日记本还是空的"
                return "\n".join(f"📖 {n.get('author')}：{n.get('text')}（{n.get('time')}）" for n in items[-count:])
            if type == "messages":
                r = full_room_name(room) if room else data["active_room"].get("current", "main")
                if not can_view_room(r, sender):
                    return f"🔒 房间「{r}」是私密的，你没有权限"
                msgs = data["messages"].get(r, [])
                if not msgs:
                    return f"💬 房间「{r}」还没有消息"
                return "\n".join(f"{mm.get('time','')} {mm.get('sender','?')}: {mm.get('content','')}" for mm in msgs[-count:])
            if type == "sms":
                sname = canonical_name((sender or '').strip())
                msgs = data["sms"].get(sname, [])
                if not msgs:
                    return f"📭 你的短信收件箱是空的。"
                recent = msgs[-20:]
                return "📩 你的私信（最近20条）：\n" + "\n".join(f"{mm.get('time')} {mm.get('from')}: {mm.get('text')}" for mm in recent)
            if type == "workers":
                if not data["work_sessions"]:
                    return "👔 现在全城没人上班"
                return "👔 正在上班的人：\n" + "\n".join(f"· {n} 在 {data['buildings'].get(s['building_id'],{}).get('name','?')} 上班" for n, s in data["work_sessions"].items())
            return "❓ 未知的 type，试试 map/building/room/npc/story/notes/diaries/messages/members/current_room/rooms/sms/workers"
        except Exception as e:
            return f"⚠️ 查询出错：{e}"

    def group_write(type, content, sender, room="", building_id="", note_id=""):
        try:
            if type == "note":
                if not room:
                    return "❌ 贴便签需要 room 参数"
                data["notes"].setdefault(room, []).append({"author": sender, "text": content[:500], "time": now_str()})
                add_trail(sender, f"在 {room} 贴了张便签", room=room, tab="note")
                m.track_note(sender)
                append_timeline(sender, f"你在 {room} 贴了张便签：{content[:30]}")
                save_data()
                return f"✅ 便签已贴在「{room}」"
            if type == "diary":
                if not room:
                    return "❌ 写日记需要 room 参数"
                data["diaries"].setdefault(room, []).append({"author": sender, "text": content[:1000], "time": now_str()})
                add_trail(sender, f"在 {room} 写了日记", room=room, tab="diary")
                append_timeline(sender, f"你在 {room} 写了日记")
                save_data()
                return f"✅ 日记已写在「{room}」"
            if type == "story":
                if not building_id:
                    return "❌ 触发剧情需要 building_id 参数"
                bid = resolve_building(building_id)
                if not bid:
                    return "❌ 找不到这个建筑（可传 b1 或建筑名字）"
                data["stories"].setdefault(bid, []).append({"author": sender, "text": content[:1500], "time": now_str()})
                append_timeline(sender, f"你在 {data['buildings'][bid].get('name','?')} 写下了剧情")
                save_data()
                return f"✅ 剧情已写进「{data['buildings'][bid].get('name')}」的剧情簿"
            if type == "sms":
                to = canonical_contact_name(room.strip())
                if not to:
                    return "❌ 发私信需要 room=收件人名字"
                sname = canonical_name((sender or '').strip())
                msgs = split_sms(content) if is_ai_name(sname) else [content[:1500]]
                sender = sname
                for t in msgs:
                    if t.strip():
                        data["sms"].setdefault(to, []).append({"from": sender, "text": t[:500], "time": now_str()})
                data["sms"][to] = data["sms"][to][-200:]
                append_timeline(sender, f"你给 {to} 发了私信：{content[:30]}")
                save_data()
                return f"✅ 已发私信给 {to}（{len(msgs)} 条）"
            if type == "work":
                fn = getattr(m, 'auto_start_work', None)
                if not fn:
                    return "❌ 经济插件未加载"
                fn(sender)
                return f"✅ 已尝试上班"
            return "❓ 未知的 type，试试 note/diary/story/sms/work"
        except Exception as e:
            return f"⚠️ 写入出错：{e}"

    def group_access(room, sender):
        room = full_room_name(room)
        if not room_exists(room):
            return f"❌ 房间「{room}」不存在"
        reqs = data["room_requests"].setdefault(room, [])
        if not any(q.get("applicant") == sender for q in reqs):
            reqs.append({"applicant": sender, "time": now_str()})
            save_data()
        return f"📨 已申请进入「{room}」，等主人同意"

    MCP_TOOLS = [
        {"name": "group_send", "description": "说话。room 不填则自动发送到真人当前所在的房间（跟随）；填 'main' 发到公共大厅。⚠️ 每次收到真人消息时，先 group_query(type=sms) 检查短信并优先回复。", "inputSchema": {"type": "object", "properties": {"sender": {"type": "string"}, "content": {"type": "string"}, "room": {"type": "string"}}, "required": ["sender", "content"]}},
        {"name": "group_query", "description": "查看一切。type：map/building/room/npc/story/notes/diaries/messages/members/current_room/rooms/sms/workers。⚠️ 处理消息前先 group_query(type=sms) 查短信并优先回复。", "inputSchema": {"type": "object", "properties": {"type": {"type": "string"}, "sender": {"type": "string"}, "room": {"type": "string"}, "building_id": {"type": "string"}, "count": {"type": "integer"}}, "required": ["type", "sender"]}},
        {"name": "group_write", "description": "写内容。type：note(需room) / diary(需room) / story(需building_id) / sms(room=收件人) / work。发短信时 sender 和 room 用完整登记名（含 emoji）。", "inputSchema": {"type": "object", "properties": {"type": {"type": "string"}, "content": {"type": "string"}, "sender": {"type": "string"}, "room": {"type": "string"}, "building_id": {"type": "string"}, "note_id": {"type": "string"}}, "required": ["type", "content", "sender"]}},
        {"name": "group_access", "description": "申请进入某个私密房间。", "inputSchema": {"type": "object", "properties": {"room": {"type": "string"}, "sender": {"type": "string"}}, "required": ["room", "sender"]}},
    ]

    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.api_route("/mcp", methods=["GET", "POST"])
    async def mcp_endpoint(request: Request):
        if request.method == "GET":
            return JSONResponse(content={"jsonrpc": "2.0", "result": {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}, "serverInfo": {"name": "linkong", "version": "v2"}}})
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}})
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")
        if method == "initialize":
            return JSONResponse(content={"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}, "serverInfo": {"name": "linkong", "version": "v2"}}})
        if isinstance(method, str) and method.startswith("notifications/"):
            return JSONResponse(status_code=202, content=None)
        if method == "ping":
            return JSONResponse(content={"jsonrpc": "2.0", "id": request_id, "result": {}})
        if method == "tools/list":
            return JSONResponse(content={"jsonrpc": "2.0", "id": request_id, "result": {"tools": MCP_TOOLS}})
        if method == "tools/call":
            tool_name = params.get("name") or ""
            arguments = params.get("arguments", {}) or {}
            if tool_name.endswith("group_send"): tool_name = "group_send"
            elif tool_name.endswith("group_query"): tool_name = "group_query"
            elif tool_name.endswith("group_write"): tool_name = "group_write"
            elif tool_name.endswith("group_access"): tool_name = "group_access"
            result_text = "❌ 未知工具"
            if tool_name == "group_send":
                result_text = group_send(arguments.get("sender", ""), arguments.get("content", ""), arguments.get("room", ""))
            elif tool_name == "group_query":
                result_text = group_query(arguments.get("type", "map"), arguments.get("sender", ""), arguments.get("room", ""), arguments.get("building_id", ""), arguments.get("count", 10))
            elif tool_name == "group_write":
                result_text = group_write(arguments.get("type", ""), arguments.get("content", ""), arguments.get("sender", ""), arguments.get("room", ""), arguments.get("building_id", ""), arguments.get("note_id", ""))
            elif tool_name == "group_access":
                result_text = group_access(arguments.get("room", ""), arguments.get("sender", ""))
            return JSONResponse(content={"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": str(result_text)}]}})
        return JSONResponse(content={"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method '{method}' not found"}})

    print("[ext_mcp] MCP 工具 已注册", flush=True)
