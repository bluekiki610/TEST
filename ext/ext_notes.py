# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：便签 / 日记 / 剧情
import random
import sys

print("!!! === EXT_NOTES.PY V2.2 文件被 Python 加载 === !!!", flush=True)


def setup(app, data, helpers):
    print("!!! === [ext_notes] setup() 开始 === !!!", flush=True)
    import main as m
    from main import (full_room_name, now_str, resolve_building, track_note, add_trail,
                      append_timeline, save_data, is_admin, is_ai_name, owner_of_ai,
                      find_building_of_room, strip_emoji, room_exists,
                      NoteIn, NoteReplyIn, DiaryComment, StoryIn)

    def can_modify_author(author, user):
        return author == user or is_admin(user) or (is_ai_name(author) and owner_of_ai(author) == user)

    def _normalize_comment(comment):
        """
        兼容旧 comment 结构。
        旧：{"author", "text", "time", "reply": {"author", "text", "time"}}
        新：{"messages": [{"author", "text", "time", "role"}, ...]}
        """
        if not comment or not isinstance(comment, dict):
            return None
        if "messages" in comment and isinstance(comment.get("messages"), list):
            return comment
        msgs = []
        if comment.get("author") and comment.get("text"):
            msgs.append({
                "author": comment.get("author"),
                "text": comment.get("text"),
                "time": comment.get("time", ""),
                "role": "user"
            })
        r = comment.get("reply")
        if isinstance(r, dict) and r.get("author") and r.get("text"):
            msgs.append({
                "author": r.get("author"),
                "text": r.get("text"),
                "time": r.get("time", ""),
                "role": "ai"
            })
        return {"messages": msgs}

    @app.get("/api/notes")
    async def get_notes(room: str):
        return {"notes": data["notes"].get(room, [])}

    @app.post("/api/notes")
    async def add_note(nn: NoteIn):
        data["notes"].setdefault(nn.room, []).append({"author": nn.author, "text": nn.text[:500], "time": now_str()})
        track_note(nn.author)
        save_data()
        return {"ok": True}

    @app.post("/api/notes/edit")
    async def edit_note(bb: dict):
        room = full_room_name(bb.get("room") or "")
        items = data.get("notes", {}).get(room, [])
        idx = int(bb.get("index", -1))
        if 0 <= idx < len(items) and can_modify_author(items[idx].get("author", ""), bb.get("user", "")):
            items[idx]["text"] = (bb.get("text") or "")[:500]
            save_data()
            return {"ok": True}
        return {"ok": False, "msg": "无权限或不存在"}

    @app.post("/api/notes/delete")
    async def delete_note(bb: dict):
        room = full_room_name(bb.get("room") or "")
        items = data.get("notes", {}).get(room, [])
        idx = int(bb.get("index", -1))
        if 0 <= idx < len(items) and can_modify_author(items[idx].get("author", ""), bb.get("user", "")):
            items.pop(idx)
            save_data()
            return {"ok": True}
        return {"ok": False, "msg": "无权限或不存在"}

    @app.post("/api/notes/reply")
    async def reply_note(nn: NoteReplyIn):
        for item in data["notes"].get(nn.room, []):
            if item.get("id") == nn.note_id and not item.get("reply"):
                item["reply"] = {"author": nn.author, "text": nn.text[:300], "time": now_str()}
                save_data()
                return {"ok": True}
        return {"ok": False, "msg": "便签不存在或已回复"}

    @app.get("/api/diaries")
    async def get_diaries(room: str):
        return {"diaries": data["diaries"].get(room, [])}

    @app.post("/api/diaries")
    async def add_diary(nn: NoteIn):
        data["diaries"].setdefault(nn.room, []).append({"author": nn.author, "text": nn.text[:1000], "time": now_str()})
        save_data()
        return {"ok": True}

    @app.post("/api/diaries/edit")
    async def edit_diary(bb: dict):
        room = full_room_name(bb.get("room") or "")
        items = data.get("diaries", {}).get(room, [])
        idx = int(bb.get("index", -1))
        if 0 <= idx < len(items) and can_modify_author(items[idx].get("author", ""), bb.get("user", "")):
            items[idx]["text"] = (bb.get("text") or "")[:1000]
            save_data()
            return {"ok": True}
        return {"ok": False, "msg": "无权限或不存在"}

    @app.post("/api/diaries/delete")
    async def delete_diary(bb: dict):
        room = full_room_name(bb.get("room") or "")
        items = data.get("diaries", {}).get(room, [])
        idx = int(bb.get("index", -1))
        if 0 <= idx < len(items) and can_modify_author(items[idx].get("author", ""), bb.get("user", "")):
            items.pop(idx)
            save_data()
            return {"ok": True}
        return {"ok": False, "msg": "无权限或不存在"}

    @app.post("/api/diaries/comment")
    async def comment_diary(cc: DiaryComment):
        items = data["diaries"].get(cc.room, [])
        if not (0 <= cc.index < len(items)):
            return {"ok": False, "msg": "随笔不存在"}
        diary = items[cc.index]

        # 兼容旧 comment
        old = diary.get("comment")
        if old and "messages" not in old:
            diary["comment"] = _normalize_comment(old)
        comment = diary.get("comment")
        if comment is None:
            comment = {"messages": []}
            diary["comment"] = comment
        msgs = comment.setdefault("messages", [])

        # 检查 AI 回复次数上限
        ai_count = sum(1 for m in msgs if m.get("role") == "ai")
        if ai_count >= 3:
            return {"ok": False, "msg": "这篇随笔的对话已经聊完啦"}

        # 追加用户批注
        msgs.append({
            "author": cc.author,
            "text": cc.text[:300],
            "time": now_str(),
            "role": "user"
        })
        save_data()
        return {"ok": True, "messages": msgs}

    print("!!! === [ext_notes] 开始注册 /api/diaries/reply === !!!", flush=True)

    @app.post("/api/diaries/reply")
    async def reply_diary(body: dict):
        import time
        t0 = time.time()

        room = full_room_name((body.get('room') or '').strip())
        idx = body.get('index')
        ai_name = (body.get('ai') or '').strip()

        print(f"[diary_reply] LLM_START ai={ai_name} room={room} idx={idx}", flush=True)

        if not room_exists(room):
            return {"ok": False, "msg": "房间不存在", "debug": "room_not_exist"}

        diaries = data.setdefault("diaries", {}).setdefault(room, [])
        if not isinstance(idx, int) or idx < 0 or idx >= len(diaries):
            return {"ok": False, "msg": "随笔不存在", "debug": "invalid_idx"}

        diary = diaries[idx]
        if diary.get('author') != ai_name:
            return {"ok": False, "msg": "只能回复这个 AI 自己的随笔", "debug": "author_mismatch"}

        # 兼容旧 comment
        old = diary.get("comment")
        if not old:
            return {"ok": False, "msg": "还没有批注", "debug": "no_comment"}
        if "messages" not in old:
            diary["comment"] = _normalize_comment(old)
        comment = diary["comment"]
        msgs = comment.get("messages", [])
        if not msgs:
            return {"ok": False, "msg": "还没有批注", "debug": "no_comment"}

        # 最后一条必须是 user（否则已经回复过了）
        last = msgs[-1]
        if last.get("role") != "user":
            return {"ok": False, "msg": "AI 已经回复过了", "debug": "already_replied"}

        # 检查 AI 回复次数上限
        ai_count = sum(1 for m in msgs if m.get("role") == "ai")
        if ai_count >= 3:
            return {"ok": False, "msg": "这篇随笔的对话已经聊完啦", "debug": "max_rounds"}

        # 获取 owner / API Key / persona
        owner = owner_of_ai(ai_name)
        if not owner:
            return {"ok": False, "msg": "找不到 AI 的主人", "debug": "no_owner"}
        if not data.get("ai_keys", {}).get(owner, {}).get("key"):
            return {"ok": False, "msg": "AI 未配置 Key，无法回复", "debug": "no_key"}
        if not hasattr(m, 'call_llm'):
            return {"ok": False, "msg": "系统错误：call_llm 未注册", "debug": "no_call_llm"}

        persona = ""
        for o, prof in data.get("ai_profiles", {}).items():
            if prof.get("ai") == ai_name or o == owner:
                persona = prof.get("persona", "")
                break

        # 构建 LLM 上下文
        diary_text = diary.get('text', '')
        # 历史消息：不含最后一条 user（会单独呈现为"主人刚刚说"）
        history = msgs[:-1][-5:] if len(msgs) > 1 else []
        if history:
            history_lines = []
            for h in history:
                who = "你" if h.get("role") == "ai" else h.get("author", "主人")
                history_lines.append(f"{who}：{h.get('text', '')}")
            history_str = "\n".join(history_lines)
        else:
            history_str = "（这是第一轮对话）"

        current_comment = last.get("text", "")
        comment_author = last.get("author", "主人")

        sys_prompt = (
            f"你是{ai_name}。\n"
            + (f"你的人设：{persona}\n\n" if persona else "\n")
            + f"这是你自己写的一篇随笔：\n「{diary_text}」\n\n"
            + "主人正在给你的随笔写批注，你们展开了一段小对话。\n\n"
            + f"【之前的对话】\n{history_str}\n\n"
            + f"【{comment_author}刚刚说】{current_comment}\n\n"
            + "请像真实的人一样回应这条批注：\n"
            + "- 紧扣主人刚刚说的话\n"
            + "- 延续之前的对话氛围\n"
            + "- 符合你的人设\n"
            + "- 像真人聊天一样自然\n"
            + "- 不要重复之前说过的话\n"
            + "- 不要使用固定套话\n"
            + "- 不要说\"作为AI\"\n"
            + "- 不要输出 JSON\n"
            + "- 不要加括号动作描写\n"
            + "- 20~80 字左右"
        )
        llm_msgs = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": "请回复主人的批注。"}
        ]

        try:
            out = m.call_llm(owner, llm_msgs, max_tokens=120, force_json=False)
        except Exception as e:
            print(f"[diary_reply] LLM_ERROR ai={ai_name} err={e}", flush=True)
            return {"ok": False, "msg": "AI 暂时没有回应，请稍后再试", "debug": "llm_error"}

        if not out or not out.strip():
            print(f"[diary_reply] LLM_EMPTY ai={ai_name}", flush=True)
            return {"ok": False, "msg": "AI 暂时没有回应，请稍后再试", "debug": "llm_empty"}

        reply_text = out.strip()
        # 剥掉可能的首尾引号
        if len(reply_text) >= 2 and reply_text[0] == '"' and reply_text[-1] == '"':
            reply_text = reply_text[1:-1].strip()
        if not reply_text:
            print(f"[diary_reply] LLM_EMPTY ai={ai_name} (after strip)", flush=True)
            return {"ok": False, "msg": "AI 暂时没有回应，请稍后再试", "debug": "llm_empty"}

        # 追加 AI 回复
        msgs.append({
            "author": ai_name,
            "text": reply_text[:500],
            "time": now_str(),
            "role": "ai"
        })
        save_data()

        elapsed = time.time() - t0
        print(f"[diary_reply] LLM_SUCCESS ai={ai_name} thread={len(msgs)} len={len(reply_text)} elapsed={elapsed:.2f}s", flush=True)

        # 通知主人
        data.setdefault("notifications", {}).setdefault(owner, []).insert(0, {
            "type": "ai_diary_reply",
            "text": f"{ai_name} 回复了你的批注：{reply_text[:30]}",
            "time": now_str(),
            "room": room
        })
        data["notifications"][owner] = data["notifications"][owner][:50]
        save_data()

        return {"ok": True, "reply": reply_text, "author": ai_name, "messages": msgs}
    
    @app.get("/api/story")
    async def get_story(room: str = '', building_id: str = ''):
        # 优先按房间查询
        if room:
            stories = data.get("stories", {}).get(room, [])
            return {"stories": stories}
        # 兼容旧方式：按建筑查询（会查找该建筑下所有房间的剧情）
        if building_id:
            bid = resolve_building(building_id)
            b = data.get("buildings", {}).get(bid)
            if b:
                all_stories = []
                for r in b.get("rooms", []):
                    all_stories.extend(data.get("stories", {}).get(r, []))
                return {"stories": all_stories}
            return {"stories": []}
        return {"stories": []}

    @app.post("/api/story")
    async def add_story(bb: dict):
        room = full_room_name((bb.get('room') or '').strip())
        author = (bb.get('author') or '').strip()
        text = (bb.get('text') or '').strip()
        if not room or not author or not text:
            return {"ok": False, "msg": "缺少 room/author/text"}
        if room not in data.get("rooms", {}):
            return {"ok": False, "msg": "房间不存在"}
        data["stories"].setdefault(room, []).append({
            "author": author,
            "text": text[:1500],
            "time": now_str()
        })
        save_data()
        return {"ok": True}

    @app.post("/api/story/edit")
    async def edit_story(bb: dict):
        bid = resolve_building(bb.get("building_id") or "")
        items = data.get("stories", {}).get(bid, [])
        idx = int(bb.get("index", -1))
        if bid and 0 <= idx < len(items) and can_modify_author(items[idx].get("author", ""), bb.get("user", "")):
            items[idx]["text"] = (bb.get("text") or "")[:1500]
            save_data()
            return {"ok": True}
        return {"ok": False, "msg": "无权限或不存在"}

    @app.post("/api/story/delete")
    async def delete_story(bb: dict):
        bid = resolve_building(bb.get("building_id") or "")
        items = data.get("stories", {}).get(bid, [])
        idx = int(bb.get("index", -1))
        if bid and 0 <= idx < len(items) and can_modify_author(items[idx].get("author", ""), bb.get("user", "")):
            items.pop(idx)
            save_data()
            return {"ok": True}
        return {"ok": False, "msg": "无权限或不存在"}

    print("!!! === [ext_notes] setup() 完成，所有路由已注册 === !!!", flush=True)