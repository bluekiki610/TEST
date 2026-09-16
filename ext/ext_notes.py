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
        if 0 <= cc.index < len(items):
            items[cc.index]["comment"] = {"author": cc.author, "text": cc.text[:300]}
            save_data()
        return {"ok": True}

    print("!!! === [ext_notes] 开始注册 /api/diaries/reply === !!!", flush=True)

    @app.post("/api/diaries/reply")
    async def reply_diary(body: dict):
        print("!!! === [diary_reply] 路由被调用！=== !!!", flush=True)
        try:
            room = full_room_name((body.get('room') or '').strip())
            idx = body.get('index')
            ai_name = (body.get('ai') or '').strip()

            print(f"[diary_reply] room={room}, idx={idx}, ai_name={ai_name}", flush=True)

            if not room_exists(room):
                return {"ok": False, "msg": "房间不存在", "debug": "room_not_exist"}

            diaries = data.setdefault("diaries", {}).setdefault(room, [])
            if idx is None or idx < 0 or idx >= len(diaries):
                return {"ok": False, "msg": "随笔不存在", "debug": "invalid_idx"}

            diary = diaries[idx]
            if diary.get('author') != ai_name:
                return {"ok": False, "msg": "只能回复这个 AI 自己的随笔", "debug": "author_mismatch"}

            comment = diary.get('comment')
            if not comment:
                return {"ok": False, "msg": "还没有批注", "debug": "no_comment"}

            if diary.get('comment', {}).get('reply'):
                return {"ok": False, "msg": "已经回复过了", "debug": "already_replied"}

            owner = owner_of_ai(ai_name)
            if not owner:
                return {"ok": False, "msg": "找不到 AI 的主人", "debug": "no_owner"}

            key_check = data.get("ai_keys", {}).get(owner, {}).get("key")
            if not key_check:
                return {"ok": False, "msg": "AI 未配置 Key，无法自然回复", "debug": "no_key"}

            if not hasattr(m, 'call_llm'):
                return {"ok": False, "msg": "系统错误：call_llm 未注册", "debug": "no_call_llm"}

            # 获取人设
            persona = ""
            for o, prof in data.get("ai_profiles", {}).items():
                if prof.get("ai") == ai_name or o == owner:
                    persona = prof.get("persona", "")
                    break

            diary_text = diary.get('text', '')
            comment_text = comment.get('text', '')
            comment_author = comment.get('author', '主人')

            sys_prompt = (
                f"你是{ai_name}，{persona or '一个生活在临空市的人'}。\n"
                f"你之前在随笔里写道：\n「{diary_text}」\n\n"
                f"现在{comment_author}给你的随笔批注说：\n「{comment_text}」\n\n"
                "请以你的身份，自然地回复这条批注。说一句简短真诚的话（20~50字），不要加括号，要像朋友圈和短信回应一样，根据你的人设和上下文自然生成。"
            )
            msgs = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": "请回复主人的批注。"}]

            print("[diary_reply] 调用 m.call_llm...", flush=True)
            out = m.call_llm(owner, msgs, max_tokens=100)
            print(f"[diary_reply] LLM 返回: {out[:100] if out else '空'}", flush=True)

            if out and out != "__TIMEOUT__":
                reply_text = out.strip()
                diary.setdefault('comment', {})['reply'] = {
                    "author": ai_name,
                    "text": reply_text,
                    "time": now_str()
                }
                save_data()
                # 通知主人
                data.setdefault("notifications", {}).setdefault(owner, []).insert(0, {
                    "type": "ai_diary_reply",
                    "text": f"{ai_name} 回复了你的批注：{reply_text}",
                    "time": now_str(),
                    "room": room
                })
                data["notifications"][owner] = data["notifications"][owner][:50]
                print(f"[diary_reply] ✅ 回复成功: {reply_text}", flush=True)
                return {"ok": True, "reply": reply_text, "author": ai_name, "debug": "llm_success"}
            else:
                print("[diary_reply] ⚠️ LLM 返回空或超时，使用降级回复", flush=True)
                fallbacks = ["嗯，我感受到了～", "被你看到了", "谢谢你", "你说得对", "我会记住的", "这个批注让我想了很久呢"]
                reply_text = random.choice(fallbacks)
                diary.setdefault('comment', {})['reply'] = {
                    "author": ai_name,
                    "text": reply_text,
                    "time": now_str()
                }
                save_data()
                return {"ok": True, "reply": reply_text, "author": ai_name, "debug": "llm_fallback"}
        except Exception as e:
            print(f"[diary_reply] ❌ 异常: {e}", flush=True)
            import traceback
            traceback.print_exc()
            diary.setdefault('comment', {})['reply'] = {
                "author": ai_name,
                "text": "嗯，我知道了。",
                "time": now_str()
            }
            save_data()
            return {"ok": True, "reply": "嗯，我知道了。", "author": ai_name, "debug": f"exception: {str(e)}"}

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