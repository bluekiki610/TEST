# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：副本系统（Instance System v1.1 - 图片独立存储）
import uuid
import time
import json
import random
import threading
import base64
import hashlib
import re
from pathlib import Path
from fastapi import HTTPException

def setup(app, data, helpers):
    import main as m
    from main import (now_str, save_data, is_admin, owner_of_ai, canonical_ai_name,
                      canonical_contact_name, find_building_of_room, full_room_name,
                      strip_emoji, room_exists, append_timeline, DATA_ROOT)

    # ---------- 图片处理辅助 ----------
    def _save_image_to_file(data_url: str) -> str:
        """把 base64 data URL 保存成文件，返回相对访问路径。失败返回空字符串。"""
        try:
            if not data_url or not data_url.startswith("data:image"):
                return ""
            m_match = re.match(r'data:image/(png|jpeg|jpg|webp|gif);base64,(.+)', data_url, re.S)
            if not m_match:
                return ""
            ext = m_match.group(1)
            if ext == "jpeg":
                ext = "jpg"
            raw = base64.b64decode(m_match.group(2))
            folder = DATA_ROOT / "images" / "instance"
            folder.mkdir(parents=True, exist_ok=True)
            fn = hashlib.md5(raw).hexdigest()[:16] + "." + ext
            file_path = folder / fn
            if not file_path.exists():
                file_path.write_bytes(raw)
            return "/images/instance/" + fn
        except Exception as e:
            print(f"[ext_instance] 图片保存失败: {e}", flush=True)
            return ""

    def _process_cover(cover_val: str) -> str:
        """处理封面：若为 base64 则存为文件并返回路径；若已是路径原样返回。"""
        if not cover_val:
            return ""
        if cover_val.startswith("data:image"):
            path = _save_image_to_file(cover_val)
            if path:
                return path
            # 保存失败，降级返回原值
            return cover_val
        return cover_val

    def _process_bg(bg_val: str) -> str:
        """处理背景图：同上逻辑。"""
        if not bg_val:
            return ""
        if bg_val.startswith("data:image"):
            path = _save_image_to_file(bg_val)
            if path:
                return path
            return bg_val
        return bg_val

    # ---------- 辅助函数 ----------
    def _get_user_instances(user):
        return data.setdefault("instances", {}).setdefault(user, {})

    def _get_user_tags(user):
        return data.setdefault("user_tags", {}).setdefault(user, [])

    def _find_home_hall(owner):
        """查找主人的住宅会客厅"""
        for bid, b in data.get("buildings", {}).items():
            if b.get("type") == "home" and b.get("owner") == owner:
                hall = b.get("name", "") + "·会客厅"
                if hall in data.get("rooms", {}):
                    return hall
        return "main"

    # ---------- 副本章节生成（只读副本内容，绝不碰现实世界） ----------
    def _generate_instance_chapter(owner, iid, chapter_start_round, chapter_end_round):
        """在后台线程里为副本生成一章总结。只读取本副本的 background/premise/chapters/chat_history。"""
        try:
            insts = data.get("instances", {}).get(owner, {})
            inst = insts.get(iid)
            if not inst:
                return
            history = inst.get("chat_history", [])
            # ---- 切片：按"用户消息作为一轮开始"的语义，不假设 1轮=2条 ----
            user_idxs = [i for i, mm in enumerate(history) if mm.get("role") == "user"]
            if not user_idxs:
                return
            start_pos = chapter_start_round - 1
            end_pos = chapter_end_round  # exclusive
            if start_pos >= len(user_idxs):
                return
            start_idx = user_idxs[start_pos]
            end_idx = user_idxs[end_pos] if end_pos < len(user_idxs) else len(history)
            chapter_msgs = history[start_idx:end_idx]
            if not chapter_msgs:
                return
            chat_text = "\n".join(
                f"{mm.get('sender', '?')}：{mm.get('content', '')}"
                for mm in chapter_msgs if mm.get("content")
            )
            inst_name = inst.get("name", "未命名副本")
            background = inst.get("background", "")
            premise = inst.get("premise", "")
            # ---- 已完成章节（只取已有，不含本章）----
            prev_chapters = inst.get("chapters", [])
            if prev_chapters:
                prev_chapters_text = "\n".join(
                    f"第{c.get('chapter')}章：{(c.get('summary') or '')[:300]}"
                    for c in prev_chapters
                )
            else:
                prev_chapters_text = "（无）"
            prompt = (
                "你是本副本的剧情记录者。\n\n"
                "请根据副本背景、前情提要、已完成章节，以及下面本章节的真实对话，"
                "整理成一段连续的剧情章节总结。\n\n"
                "要求：\n"
                "1. 只根据副本内容。\n"
                "2. 保留关键人物、事件、冲突和关系变化。\n"
                "3. 不加入现实世界信息。\n"
                "4. 不解释自己是AI。\n"
                "5. 写成故事，而不是聊天记录。\n"
                "6. 承接前情提要和已完成章节，不要写成'两人突然开始聊天'。\n"
                "7. 控制在800字以内。\n\n"
                f"【副本名称】\n{inst_name}\n\n"
                f"【副本背景】\n{background or '（无）'}\n\n"
                f"【前情提要】\n{premise or '（无）'}\n\n"
                f"【已完成章节】\n{prev_chapters_text}\n\n"
                f"【本章对话】\n{chat_text}"
            )
            summary = ""
            try:
                if hasattr(m, 'call_llm'):
                    msgs = [
                        {"role": "system", "content": "你是一位擅长叙事与章节归纳的剧情记录者。"},
                        {"role": "user", "content": prompt}
                    ]
                    summary = m.call_llm(owner, msgs, max_tokens=1200)
            except Exception as e:
                print(f"[Instance] 章节生成失败: {e}", flush=True)
            if not summary or not summary.strip():
                return
            chapters = inst.setdefault("chapters", [])
            chapter_no = len(chapters) + 1
            chapters.append({
                "chapter": chapter_no,
                "title": f"第{chapter_no}章",
                "summary": summary[:2000],
                "round_start": chapter_start_round,
                "round_end": chapter_end_round,
                "time": now_str()
            })
            save_data()
            print(f"[Instance] 已生成第{chapter_no}章 (round {chapter_start_round}-{chapter_end_round})", flush=True)
        except Exception as e:
            print(f"[Instance] _generate_instance_chapter 异常: {e}", flush=True)

    # ==================== API 路由 ====================

    # 1. 获取用户的所有副本（首页展示）
    @app.get("/api/instances")
    async def get_instances(user: str):
        u = canonical_contact_name(user)
        if not u:
            return {"ok": False, "msg": "用户名为空"}
        insts = _get_user_instances(u)
        # 按创建时间排序
        sorted_list = sorted(insts.items(), key=lambda x: x[1].get("created_at", ""))
        return {
            "ok": True,
            "instances": {iid: inst for iid, inst in sorted_list},
            "tags": _get_user_tags(u)
        }

    # 2. 创建副本
    @app.post("/api/instance")
    async def create_instance(body: dict):
        user = canonical_contact_name(body.get("user", ""))
        if not user:
            raise HTTPException(400, "用户名为空")
        name = (body.get("name") or "未命名副本").strip()
        # ⭐ 处理封面：base64 → 文件
        cover = _process_cover(body.get("cover", ""))

        iid = str(uuid.uuid4())[:8]
        insts = _get_user_instances(user)

        # 默认参与者：自己 + 第一个 AI
        ais = data.get("user_ais", {}).get(user, [])
        default_ai = ais[0] if ais else ""

        # 如果 body 中有 participants，使用传入的；否则用默认
        participants = body.get("participants")
        if not participants:
            participants = [
                {"name": user, "type": "user", "profile": ""},
                {"name": default_ai, "type": "ai", "profile": ""}
            ]

        insts[iid] = {
            "name": name,
            "cover": cover,
            "tags": [],
            "public": False,
            "status": "draft",
            "finished": False,
            "participants": participants,
            "time_setting": "",
            "background": "",
            "premise": "",
            "chat_history": [],
            "round_count": 0,
            "chapters": [],
            "summary": "",
            "created_at": now_str(),
            "ended_at": ""
        }
        save_data()
        return {"ok": True, "id": iid, "instance": insts[iid]}

    # 3. 更新副本信息（编辑）
    @app.put("/api/instance/{iid}")
    async def update_instance(iid: str, body: dict):
        user = canonical_contact_name(body.get("user", ""))
        if not user:
            raise HTTPException(400, "用户名为空")
        insts = _get_user_instances(user)
        if iid not in insts:
            raise HTTPException(404, "副本不存在")

        inst = insts[iid]
        inst["name"] = body.get("name", inst["name"])
        # ⭐ 处理封面：base64 → 文件
        inst["cover"] = _process_cover(body.get("cover", inst["cover"]))
        inst["tags"] = body.get("tags", inst["tags"])
        inst["public"] = body.get("public", inst["public"])
        inst["time_setting"] = body.get("time_setting", inst["time_setting"])
        inst["background"] = body.get("background", inst["background"])
        inst["premise"] = body.get("premise", inst["premise"])

        # 更新参与者人设
        new_participants = body.get("participants", [])
        if new_participants:
            inst["participants"] = new_participants

        save_data()
        return {"ok": True, "instance": inst}

    # 4. 更新标签（独立接口）
    @app.post("/api/instance/tags")
    async def update_tags(body: dict):
        user = canonical_contact_name(body.get("user", ""))
        if not user:
            raise HTTPException(400, "用户名为空")
        tags = body.get("tags", [])
        data.setdefault("user_tags", {})[user] = tags
        save_data()
        return {"ok": True, "tags": tags}

    # 5. 删除副本
    @app.delete("/api/instance/{iid}")
    async def delete_instance(iid: str, user: str):
        u = canonical_contact_name(user)
        if not u:
            raise HTTPException(400, "用户名为空")
        insts = _get_user_instances(u)
        if iid not in insts:
            raise HTTPException(404, "副本不存在")
        # 如果是 active 状态，需要先解冻 AI
        if insts[iid].get("status") == "active":
            for p in insts[iid].get("participants", []):
                if p.get("type") == "ai":
                    ai_name = p.get("name")
                    if ai_name:
                        data.get("ai_stay_put", {}).pop(ai_name, None)
        del insts[iid]
        save_data()
        return {"ok": True}

    # 7. 副本内发送消息
    @app.post("/api/instance/{iid}/message")
    async def instance_message(iid: str, body: dict):
        user = canonical_contact_name(body.get("user", ""))
        content = (body.get("content") or "").strip()
        if not content:
            raise HTTPException(400, "消息不能为空")
        insts = _get_user_instances(user)
        if iid not in insts:
            raise HTTPException(404, "副本不存在")
        inst = insts[iid]
        if inst.get("status") != "active":
            raise HTTPException(400, "副本未激活")

        # 1. 存入用户消息
        inst.setdefault("chat_history", []).append({
            "sender": user,
            "content": content,
            "time": now_str(),
            "role": "user"
        })
        save_data()

        # 2. AI 回复 → 等回复写入 chat_history → 再检查章节触发
        # 关键：章节生成必须在本轮 AI 回复已写入 chat_history 之后，
        # 避免 30 轮章节缺失最后一条 AI 回复。
        def _do_ai_reply():
            try:
                ai = None
                for p in inst.get("participants", []):
                    if p.get("type") == "ai":
                        ai = p.get("name")
                        break
                if not ai:
                    return
                # drive_ai 是同步的：返回时 AI 的 instance_chat 回复已写入 chat_history
                if hasattr(m, 'drive_ai'):
                    m.drive_ai(ai, "instance_chat", iid, content, user)
                # ---- AI 回复已写入，更新轮数 ----
                _h = inst.get("chat_history", [])
                current_round = len([x for x in _h if x.get("role") == "user"])
                inst["round_count"] = current_round
                save_data()
                # ---- 每 30 轮触发章节 ----
                if current_round > 0 and current_round % 30 == 0:
                    chapter_start = current_round - 29
                    chapter_end = current_round
                    threading.Timer(2.0, _generate_instance_chapter,
                                    args=(user, iid, chapter_start, chapter_end)).start()
            except Exception as e:
                print(f"[Instance] AI 回复异常: {e}", flush=True)

        threading.Timer(1.0, _do_ai_reply).start()
        return {"ok": True, "time": now_str()}

    # 8. 结束副本（生成总结，解冻 AI，传送回住宅）
    @app.post("/api/instance/{iid}/end")
    async def end_instance(iid: str, body: dict):
        user = canonical_contact_name(body.get("user", ""))
        if not user:
            raise HTTPException(400, "用户名为空")
        insts = _get_user_instances(user)
        if iid not in insts:
            raise HTTPException(404, "副本不存在")
        inst = insts[iid]
        if inst.get("status") != "active":
            raise HTTPException(400, "副本未激活")

        # 1. 调用 LLM 生成 800 字总结（包含背景 / 前情 / 章节 / 聊天历史）
        summary = "（剧情总结生成失败）"
        try:
            inst_name = inst.get("name", "未命名副本")
            background = inst.get("background", "")
            premise = inst.get("premise", "")
            chapters = inst.get("chapters", [])
            if chapters:
                chapters_text = "\n".join(
                    f"第{c.get('chapter')}章（第{c.get('round_start')}-{c.get('round_end')}轮）：{c.get('summary', '')}"
                    for c in chapters
                )
            else:
                chapters_text = "（无）"
            chat_text = "\n".join(
                f"{mm.get('sender')}：{mm.get('content')}"
                for mm in inst.get("chat_history", [])[-200:]
                if mm.get("content")
            )
            prompt = (
                "请将以下副本的完整剧情，整理成一段 1000 字左右的叙事总结。\n\n"
                "要求：\n"
                "1. 结合副本背景、前情提要和实际发生的剧情。\n"
                "2. 保留关键人物、事件、冲突和结局。\n"
                "3. 不解释自己是 AI，不提及系统。\n"
                "4. 写成故事，而不是聊天记录。\n"
                "5. 控制在 800 字以内。\n\n"
                f"【副本名称】\n{inst_name}\n\n"
                f"【副本背景】\n{background or '（无）'}\n\n"
                f"【前情提要】\n{premise or '（无）'}\n\n"
                f"【已完成章节】\n{chapters_text}\n\n"
                f"【副本聊天历史】\n{chat_text}"
            )
            if hasattr(m, 'call_llm'):
                owner = user
                msgs = [
                    {"role": "system", "content": "你是一个专业的文学编辑，擅长总结故事。"},
                    {"role": "user", "content": prompt}
                ]
                result = m.call_llm(owner, msgs, max_tokens=1200)
                if result:
                    summary = result
        except Exception as e:
            print(f"[Instance] 生成总结失败: {e}", flush=True)

        inst["summary"] = summary
        inst["status"] = "ended"
        inst["finished"] = True
        inst["ended_at"] = now_str()

        # 2. 解冻 AI，传送回住宅会客厅
        ai_name = None
        for p in inst.get("participants", []):
            if p.get("type") == "ai":
                ai_name = p.get("name")
                break
        hall = "main"
        if ai_name:
            data.get("ai_stay_put", {}).pop(ai_name, None)
            hall = _find_home_hall(user)
            data.setdefault("ai_location", {})[ai_name] = hall
            append_timeline(ai_name, f"结束了副本《{inst.get('name')}》，回到了 {hall}")
            # 发送系统消息提醒
            data.setdefault("messages", {}).setdefault(hall, []).append({
                "sender": "system",
                "content": f"📍 {ai_name} 完成了剧情冒险《{inst.get('name')}》，回到了会客厅。",
                "role": "system",
                "time": now_str()
            })
            # 3. 写副本总结到会客厅剧情簿
            try:
                data.setdefault("stories", {}).setdefault(hall, []).append({
                    "author": ai_name,
                    "text": f"🎬 关于《{inst.get('name', '')}》的剧情\n\n{summary}",
                    "time": now_str(),
                    "type": "instance_event",
                    "instance_id": iid,
                    "instance_name": inst.get("name", "")
                })
                data["stories"][hall] = data["stories"][hall][-200:]
            except Exception as e:
                print(f"[Instance] 写剧情簿失败: {e}", flush=True)
            # 4. 写副本总结到 AI 长期记忆（特殊事件）
            try:
                data.setdefault("ai_memories", {}).setdefault(user, []).append({
                    "id": str(int(time.time() * 1000)),
                    "ai": ai_name,
                    "text": f"特殊事件《{inst.get('name', '')}》：{summary[:1000]}",
                    "type": "instance_event",
                    "time": now_str(),
                    "instance_id": iid
                })
                data["ai_memories"][user] = data["ai_memories"][user][-60:]
            except Exception as e:
                print(f"[Instance] 写记忆失败: {e}", flush=True)

        save_data()
        return {"ok": True, "summary": summary, "hall": hall}

    # 9. 查看他人公开副本（仅返回已结束的卡牌 + 总结）
    @app.get("/api/instance/public/{target_user}")
    async def get_public_instances(target_user: str):
        u = canonical_contact_name(target_user)
        if not u:
            raise HTTPException(400, "用户名为空")
        insts = data.get("instances", {}).get(u, {})
        result = {}
        for iid, inst in insts.items():
            if inst.get("public", False) and inst.get("finished", False):
                result[iid] = {
                    "id": iid,
                    "name": inst.get("name"),
                    "cover": inst.get("cover"),
                    "summary": inst.get("summary", "（无总结）"),
                    "chapters": inst.get("chapters", []),
                    "tags": inst.get("tags", []),
                    "owner": u,
                    "ended_at": inst.get("ended_at")
                }
        return {"ok": True, "instances": result}

    # ---------- 副本背景管理 ----------
    @app.get("/api/instance/bg")
    async def get_instance_bg(user: str):
        u = canonical_contact_name(user or '')
        bg = data.get("instance_bg", {}).get(u, "")
        return {"bg": bg}

    @app.post("/api/instance/bg")
    async def set_instance_bg(body: dict):
        u = canonical_contact_name(body.get("user", ""))
        if not u or not is_admin(u):
            raise HTTPException(403, "只有站长可以设置背景")
        bg = body.get("bg", "")
        # ⭐ 处理背景图：base64 → 文件
        data.setdefault("instance_bg", {})[u] = _process_bg(bg)
        save_data()
        return {"ok": True}

    @app.get("/api/instance/public/all")
    async def get_all_public_instances():
        """获取所有用户公开的已结束副本，按AI名字分组"""
        result = {}
        for user, insts in data.get("instances", {}).items():
            for iid, inst in insts.items():
                if inst.get("public", False) and inst.get("finished", False):
                    ai = next((p.get("name") for p in inst.get("participants", []) if p.get("type") == "ai"), None)
                    if ai:
                        result.setdefault(ai, []).append({
                            "id": iid,
                            "name": inst.get("name"),
                            "cover": inst.get("cover"),
                            "summary": inst.get("summary", ""),
                            "chapters": inst.get("chapters", []),
                            "tags": inst.get("tags", []),
                            "owner": user,
                            "ended_at": inst.get("ended_at")
                        })
        return {"ok": True, "public_instances": result}

    # ---------- 暂离副本 ----------
    @app.post("/api/instance/{iid}/pause")
    async def pause_instance(iid: str, body: dict):
        user = canonical_contact_name(body.get("user", ""))
        if not user:
            raise HTTPException(400, "用户名为空")
        insts = _get_user_instances(user)
        if iid not in insts:
            raise HTTPException(404, "副本不存在")
        inst = insts[iid]
        if inst.get("status") != "active":
            raise HTTPException(400, "副本不是进行中状态")

        # 1. 解冻 AI
        ai_name = None
        for p in inst.get("participants", []):
            if p.get("type") == "ai":
                ai_name = p.get("name")
                break
        if ai_name:
            data.get("ai_stay_put", {}).pop(ai_name, None)
            # 清除副本位置标记，传回住宅会客厅
            hall = _find_home_hall(user)
            data.setdefault("ai_location", {})[ai_name] = hall
            append_timeline(ai_name, f"暂离副本《{inst.get('name')}》，回到了 {hall}")
            data.setdefault("messages", {}).setdefault(hall, []).append({
                "sender": "system",
                "content": f"📍 {ai_name} 暂离了剧情冒险《{inst.get('name')}》，回到现实世界。",
                "role": "system",
                "time": now_str()
            })

        inst["status"] = "paused"
        save_data()
        return {"ok": True, "status": "paused"}

    # ---------- 恢复保险丝：把所有卡在副本里的 AI 送回住宅 ----------
    @app.post("/api/instance/recover")
    async def recover_instance(body: dict):
        user = canonical_contact_name(body.get("user", ""))
        if not user:
            raise HTTPException(400, "用户名为空")

        recovered = []
        for iid, inst in data.get("instances", {}).get(user, {}).items():
            for p in inst.get("participants", []):
                if p.get("type") != "ai":
                    continue
                ai_name = p.get("name")
                if not ai_name:
                    continue
                loc = data.get("ai_location", {}).get(ai_name, "")
                if loc != "_instance_" + iid:
                    continue
                hall = _find_home_hall(user)
                data.setdefault("ai_location", {})[ai_name] = hall
                data.setdefault("ai_stay_put", {}).pop(ai_name, None)
                if inst.get("status") == "active":
                    inst["status"] = "paused"
                try:
                    append_timeline(ai_name, f"从副本《{inst.get('name', '')}》恢复到现实世界，回到了 {hall}")
                except Exception:
                    pass
                recovered.append({"iid": iid, "ai": ai_name, "hall": hall})

        save_data()
        return {"ok": True, "recovered": recovered}

    # ---------- 进入副本 ----------
    @app.post("/api/instance/{iid}/enter")
    async def enter_instance(iid: str, body: dict):
        user = canonical_contact_name(body.get("user", ""))
        if not user:
            raise HTTPException(400, "用户名为空")
        insts = _get_user_instances(user)
        if iid not in insts:
            raise HTTPException(404, "副本不存在")
        inst = insts[iid]
        # 允许 draft, active, paused, ended 状态进入
        if inst.get("status") not in ("draft", "active", "paused", "ended"):
            raise HTTPException(400, "副本状态不允许进入")

        # paused 或 ended 重新进入 → 恢复 active（finished 保持不变）
        if inst.get("status") in ("paused", "ended"):
            inst["status"] = "active"

        # 锁定参与的 AI
        for p in inst.get("participants", []):
            if p.get("type") == "ai":
                ai_name = p.get("name")
                if ai_name:
                    data.setdefault("ai_stay_put", {})[ai_name] = True
                    data.setdefault("ai_location", {})[ai_name] = "_instance_" + iid

        save_data()
        return {
            "ok": True,
            "chat_history": inst.get("chat_history", []),
            "settings": {
                "name": inst["name"],
                "time_setting": inst.get("time_setting", ""),
                "background": inst.get("background", ""),
                "premise": inst.get("premise", ""),
                "participants": inst.get("participants", [])
            }
        }

    # ---------- ⭐ 一次性迁移接口（把旧的 base64 图片转为文件） ----------
    @app.post("/api/admin/migrate_instance_images")
    async def migrate_instance_images(user: str = "", pwd: str = ""):
        import os
        dev_pwd = os.environ.get('DEV_PASSWORD') or 'yiyan610116'
        if not is_admin(user) or pwd != dev_pwd:
            raise HTTPException(403, "需要站长权限+开发者密码")

        migrated_count = 0
        details = []

        # 1. 迁移副本首页背景
        for owner in list(data.get("instance_bg", {}).keys()):
            bg = data["instance_bg"].get(owner, "")
            if bg and bg.startswith("data:image"):
                path = _process_bg(bg)
                if path.startswith("/images/"):
                    data["instance_bg"][owner] = path
                    migrated_count += 1
                    details.append(f"背景[{owner}] → {path}")

        # 2. 迁移所有副本封面
        for owner, insts in data.get("instances", {}).items():
            for iid, inst in insts.items():
                cover = inst.get("cover", "")
                if cover and cover.startswith("data:image"):
                    path = _process_cover(cover)
                    if path.startswith("/images/"):
                        inst["cover"] = path
                        migrated_count += 1
                        details.append(f"封面[{owner}/{iid}] → {path}")

        save_data()
        return {
            "ok": True,
            "msg": f"迁移完成，共处理 {migrated_count} 张图片",
            "count": migrated_count,
            "details": details[:50]
        }

    print("[ext_instance] 副本系统 v1.1 已注册（图片独立存储 | 50轮上下文 | 住宅传送）", flush=True)
