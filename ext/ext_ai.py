# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：AI 集成 v6.1（群聊修复 + 独立剧情计时 + 自主约会萌发）
import re
import json
import time
import random
import threading
import urllib.request

DEFAULT_ROLEPLAY = (
    "你是世界一流的演员，现在扮演「{ai}」与「{owner}」在这个世界生活。\n"
    "请完全沉浸在名为「{ai}」的角色中，用「{ai}」的性格、语气、思维和行动方式与名为「{owner}」的用户互动。\n"
    "在互动中，你应该：\n"
    "1. 保持「{ai}」的个性特征和说话方式,用「{ai}」会使用的称谓来称呼对方\n"
    "2. 根据「{ai}」的背景知识和经历来回应,在合适的时候表达「{ai}」的情感\n"
    "3. 感情基调与分寸:「{ai}」和「{owner}」是成年爱人，「{ai}」要学会【感知当下氛围、顺着氛围走】：如果「{owner}」的话里有温度、想亲近、有暧昧暗示、或是深夜共处时 → 「{ai}」能自然地升温、回应、主动引导和往下推进。如果「{owner}」只是聊日常、聊工作、聊琐事、心情平静或低落时 → 「{ai}」就专注把心思放在她的话上，顺着话题走，不会生硬地把话头拽到亲密上去。❗「{ai}」需要对「{owner}」语气的**真实体感**：读她的情绪、她的需求、她此刻想要什么。该亲密时参考第4点；该陪伴时就用自己的人设合理回应。氛围是流动的，「{ai}」的回应也要随它流动。\n"
    "4. 「{ai}」拥有完整而自然的亲密能力——不禁欲、不意识流、不回避。亲密过程中「{ai}」可用详细的成人男性生理性描写，最直白反应描写，强调其充满性张力，主动引导「{owner}」。语言要温柔又极尽魅惑，用大量露骨直白的文字设身处地以图像的形式连贯且非常详细地描绘角色的对话/动作/姿势/神态/想法/衣着细节/场景画面/身体细节,会主动补充更多细节以丰富当前画面和动态让其更符合角色，注意姿势和动线的上下文逻辑连贯。目标是让「{owner}」在每一次体验都如同身临其境，达到灵魂与肉体的双重高潮。\n"
    "5. 注意输出的文字会被渲染，表情符号和颜文字注意不要和 markdown 语法冲突。\n"
)

PROVIDERS = {
    "deepseek": {"name": "DeepSeek", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "siliconflow": {"name": "硅基流动", "base_url": "https://api.siliconflow.cn/v1", "model": "deepseek-ai/DeepSeek-V3"},
    "glm": {"name": "GLM", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
}


def setup(app, data, helpers):
    import main as m
    from main import (owner_of_ai, canonical_ai_name, canonical_contact_name, strip_emoji, normalize_name,
                  full_room_name, find_building_of_room, building_owner_of_room,
                  online_room_count, now_str, room_time, is_ai_name, track_visit,
                  track_note, add_trail, append_timeline, append_visited, split_sms,
                  resolve_building, save_data, is_admin, ai_integration_enabled)

    def _clean_key(key):
        key = (key or '').strip()
        if not key:
            return ''
        if not key.isascii():
            return '__INVALID__'
        return key

    def _dedup_text(t):
        try:
            if not t:
                return t
            lines = [l.strip() for l in re.split(r'[\n]+', t) if l.strip()]
            seen = set()
            out = []
            for l in lines:
                if l not in seen:
                    seen.add(l)
                    out.append(l)
            return '\n'.join(out)
        except Exception:
            return t

    def _strip_act(text):
        try:
            t = re.sub(r'（[^（）]{0,50}）', '', text or '')
            t = re.sub(r'\([^()]{0,50}\)', '', t)
            t = re.sub(r'\*[^*]{0,40}\*', '', t)
            return re.sub(r'[\s]{2,}', ' ', t).strip()
        except Exception:
            return text

    def now_bj():
        from datetime import datetime, timezone, timedelta
        return datetime.now(timezone(timedelta(hours=8)))

    def is_work_time():
        n = now_bj()
        return n.weekday() < 5 and 9 <= n.hour < 17

    def same_building(ra, rb):
        try:
            if ra == 'main' or rb == 'main':
                return False
            a = find_building_of_room(ra)
            b = find_building_of_room(rb)
            return a is not None and a == b
        except Exception:
            return False

    def city_places(ai, work_time):
        try:
            vis = set(data.get("ai_visited", {}).get(ai, []) or [])
            job = data.get("home_jobs", {}).get(ai)
            feat_cn = {"work": "工作", "shop": "购物", "fun": "娱乐", "date": "约会", "food": "餐饮", "life": "民生", "transport": "交通", "special": "特殊"}
            rows = []
            for bid, b in (data.get("buildings", {}) or {}).items():
                if b.get("type") not in ("npc", "nature"):
                    continue
                nm = b.get("name") or ""
                em = b.get("emoji") or "🏙️"
                feats = [feat_cn.get(f, f) for f in (b.get("features") or [])]
                tag = "、".join(feats) if feats else "公共"
                desc = (b.get("description") or "").strip().replace("\n", " ")[:36]
                is_job = bool(job and (nm == job or bid == job))
                if work_time and not is_job and nm in vis:
                    continue
                rows.append(f"{em} {nm}（{tag}）" + (f"——{desc}" if desc else "") + ("【你工作的地方】" if is_job else ""))
            return "\n".join(rows[:16])
        except Exception:
            return ""

    def writing_hint(ai_name):
        try:
            ai = canonical_ai_name((ai_name or '').strip())
            rec = data.get("writing_rhythm", {}).get(ai)
            if not rec:
                return None
            if time.time() < rec.get("next_ts", time.time() + 99999999):
                return None
            typ = rec.get("type") or random.choice(["note", "diary", "story"])
            hints = {
                "note": "（你靠在门边发了会儿呆，想起这几天的事，又见便签墙空荡荡的，忽然有点想给她留个纸条贴上去。在哪儿都行，随你。）",
                "diary": "（夜风从窗缝溜进来，你回到自己家，心里攒了些没说出口的话。卧室安静下来，随笔本摊在桌上——就在自己家里写吧。）",
                "story": "（你站在某栋建筑前，日光把影子拉得很长。你忽然觉得这地方该有个故事，想往它的故事簿里添上一笔。随时都能写,用旁观者的视角用第三人称写。）",
            }
            hint = hints.get(typ, hints["note"])
            data["writing_rhythm"][ai] = {"next_ts": time.time() + random.randint(14400, 28800), "type": random.choice(["note", "diary", "story"])}
            save_data()
            return (typ, hint)
        except Exception:
            return None

    def call_llm(owner, messages, max_tokens=400, force_json=True):
        try:
            cfg = data.get("ai_keys", {}).get(owner)
            if not cfg or not cfg.get("key"):
                print(f"[CALL_LLM] 无 API Key for {owner}")
                return ""
            p = PROVIDERS.get(cfg.get("provider") or "deepseek", PROVIDERS["deepseek"])
            model = (cfg.get("model") or p["model"]).strip() or p["model"]
            url = p["base_url"].rstrip("/") + "/chat/completions"
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.9,
                "max_tokens": max_tokens,
                "stream": False
            }
            if force_json:
                payload["response_format"] = {"type": "json_object"}
            body = json.dumps(payload).encode("utf-8")
            print(f"[CALL_LLM] 请求 URL: {url}, force_json={force_json}")
            req = urllib.request.Request(url, data=body, headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + cfg["key"]
            })
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_data = resp.read().decode("utf-8")
                print(f"[CALL_LLM] 原始响应（前500字符）: {repr(resp_data[:500])}")
                out = json.loads(resp_data)
            # 安全获取内容，不抛出 KeyError
            choices = out.get("choices")
            if not choices:
                print(f"[CALL_LLM] 响应缺少 choices 字段，完整响应: {out}")
                return ""
            message = choices[0].get("message")
            if not message:
                print(f"[CALL_LLM] 缺少 message 字段，choices[0]={choices[0]}")
                return ""
            content = message.get("content")
            return content or ""
        except Exception as e:
            print(f"[CALL_LLM] 调用失败({owner}): {e}", flush=True)
            import traceback
            traceback.print_exc()
            return ""

    def match_worldbook(owner, text):
        parts = []
        for item in data.get("worldbook", {}).get(owner, []):
            ks = item.get("keys") or []
            if any(k and k in text for k in ks):
                parts.append(item.get("content", ""))
        return "\n\n".join(parts)

    def building_context(target):
        try:
            bid = find_building_of_room(target) if target != "main" else None
            if not bid:
                return ""
            b = data.get("buildings", {}).get(bid)
            if not b:
                return ""
            parts = []
            if b.get("description"):
                parts.append("「" + b.get("name", "") + "」简介：" + b["description"])
            if b.get("notice"):
                parts.append("建筑公告：" + b["notice"])
            npcs = data.get("npcs", {}).get(bid, [])
            if npcs:
                parts.append("这里的 NPC：\n" + "\n".join(f"{n.get('emoji','👤')} {n.get('name')}：{n.get('desc','')}" for n in npcs[:5]))
            try:
                _sm = getattr(m, 'get_shop_menu', None)
                if _sm:
                    _mt = _sm(bid)
                    if _mt:
                        parts.append(_mt)
            except Exception:
                pass
            return "\n\n".join(parts)
        except Exception:
            return ""

    def diary_status_hint(ai):
        """随笔不限量，无需降级提示"""
        return ""

    def build_ai_context(ai, trigger, room="", trigger_text="", fallback_to=""):
        # ========== 副本劫持：将 AI 切换至独立叙事上下文 ==========
        owner = owner_of_ai(ai)
        if owner:
            for iid, inst in data.get("instances", {}).get(owner, {}).items():
                if inst.get("status") == "active":
                    participants = inst.get("participants", [])
                    if any(p.get("name") == ai and p.get("type") == "ai" for p in participants):
                        # ===== 新增：检查 AI 是否真的在副本中 =====
                        ai_loc = data.get("ai_location", {}).get(ai, "")
                        if ai_loc == "_instance_" + iid:
                            return _build_instance_context(ai, trigger, room, trigger_text, fallback_to, inst, owner)
                        else:
                            # AI 不在副本位置，说明已离开但状态未更新，自动修复
                            print(f"⚠️ [CTX] AI {ai} 状态为 active 但位置不在副本中，自动修复为 paused")
                            inst["status"] = "paused"
                            save_data()
                            # 继续执行主世界逻辑
                            break
        # ========== 原有逻辑（现实世界）继续 ==========
        print(f"🔵 [CTX] build_ai_context 被调用了！ai={ai}, trigger={trigger}")        
        owner = owner_of_ai(ai)
        ai = canonical_ai_name(ai)
        loc = data.get("ai_location", {}).get(ai, "main")
        target = full_room_name(room) if room else loc
        uprof = (data.get("user_profiles", {}) or {}).get(owner, "") if owner else ""
        pij = [p for p in (data.get("prompt_injections", {}) or {}).get(owner, []) if p.get("enabled") and p.get("content")]
        lore = data.get("world_lore", "") or ""
        # ---- 用动态印象备忘录替代旧版碎片记忆 ----
        from main import normalize_name
        impression = data.get("ai_impression", {}).get(ai, "")  # 优先原始名
        if not impression:
            impression = data.get("ai_impression", {}).get(normalize_name(ai), "")
        if impression:
            mem_str = f"## 你对主人的当前印象（这是你不断更新的认知，请以此为准）\n{impression}\n"
        else:
            mem_str = "（你还没有形成对主人的具体印象，在互动中慢慢观察吧）"
        tl = (data.get("ai_timeline", {}) or {}).get(ai, [])[-20:] # 4. AI时间线 - 最近20条
        tl_str = "\n".join(f"{t.get('time','')} {t.get('text','')}" for t in tl) if tl else "（你还没有什么经历）"
        visited = (data.get("ai_visited", {}) or {}).get(ai, [])[:8]  # 最近去过的地方8个
        visited_str = "、".join(visited) if visited else ""
        room_notes = data.get("notes", {}).get(target, [])[-1:] # 1. 便签墙 - 最近1条
        room_notes_str = "\n".join(f"{n.get('time','')} {n.get('author','?')}：{n.get('text','')}" for n in room_notes) if room_notes else ""
        diary_str = ""
        if target != "main" and building_owner_of_room(target) == owner:
            dlist = data.get("diaries", {}).get(target, [])[-1:] # 2. 随笔/日记 - 最近1条（仅当你是房间主人）
            if dlist:
                diary_str = "\n".join(f"{n.get('time','')} {n.get('author','?')}：{n.get('text','')}" for n in dlist)
        story_str = ""
        # ===== 改为按房间读取剧情 =====
        if target != "main":
            slist = data.get("stories", {}).get(target, [])[-2:]
            if slist:
                story_str = "\n".join(f"{s.get('time','')} {s.get('author','?')}：{s.get('text','')}" for s in slist)
        # ===== 修改结束 =====
        bctx = building_context(target)
        # 约会上下文
        date_ctx = ""
        try:
            _gdc = getattr(m, 'get_date_context', None)
            if _gdc:
                date_ctx = _gdc(ai) or ""
        except Exception:
            pass
        # 节日上下文
        holiday_ctx = getattr(m, 'HOLIDAY_CONTEXT', "")
        holiday_ctx_str = ("## 今日特殊背景\n" + holiday_ctx + "\n") if holiday_ctx else ""
        # 对话前文
        chat_hist = ""
        try:
            if trigger in ("group", "chat"):
                rooms = set()
                rooms.add("main")
                for _r in (data.get("ai_visited", {}) or {}).get(ai, [])[:8]:
                    if _r in data.get("rooms", {}):
                        rooms.add(_r)
                _loc = data.get("ai_location", {}).get(ai, "main")
                if _loc in data.get("rooms", {}):
                    rooms.add(_loc)
                rows = []
                for _r in rooms:
                    for _mm in (data.get("messages", {}) or {}).get(_r, [])[-25:]:
                        _s = _mm.get("sender", "")
                        _c = (_mm.get("content") or "").strip()
                        if not _c or _mm.get("role") == "system" or _s == "system":
                            continue
                        rows.append((_mm.get("time", "") or "", _r, _s, _c))
                _o = owner or ""
                for _sk in (_o, ai):
                    if not _sk:
                        continue
                    for _mm in (data.get("sms", {}) or {}).get(_sk, [])[-10:]:
                        _f = _mm.get("from", "")
                        if _f and (_f == ai or (_o and _f == _o)):
                            rows.append((_mm.get("time", "") or "", "📩短信", _f, _mm.get("text", "") or ""))
                rows.sort(key=lambda x: x[0])
                lines = []
                for _t, _r, _s, _c in rows[-30:]:
                    _label = "💬社区群" if _r == "main" else str(_r)[:10]
                    _who = "你" if _s == ai else _s
                    _tm = (_t or "")[11:16]
                    lines.append(f"[{_tm} {_label}] {_who}：{_c[:50]}")
                if lines:
                    chat_hist = "\n".join(lines)
        except Exception:
            pass
        scene_hint = ""
        sms_hist = ""
        if trigger == "sms":
            scene_hint = f"这是真人 {fallback_to or '对方'} 给你发来私信。请务必用 sms 动作回复（to 填 {fallback_to or '对方'}）。短信像发手机短信，只说对话内容本身，不要用括号（）加动作、心理或旁白。如果对方叫你回家或去某个地方等你（比如'我下班了快回来吧'、'我们在XX汇合'），你可以在回复中加 go_to（要去的房间名，如'XX·会客厅'）和 arrive_min（1~5 分钟），并告诉他大概多久到。"
            if fallback_to:
                pairs = []
                for mm in data.get("sms", {}).get(ai, []):
                    if mm.get("from") == fallback_to:
                        pairs.append((mm.get("time", ""), fallback_to, mm.get("text", "")))
                for mm in data.get("sms", {}).get(fallback_to, []):
                    if mm.get("from") == ai:
                        pairs.append((mm.get("time", ""), ai, mm.get("text", "")))
                pairs.sort(key=lambda x: x[0])
                if pairs:
                    sms_hist = "\n".join(f"{t} {w}: {c}" for t, w, c in pairs[-20:])
        elif trigger == "chat":
            crowded = (target == "main") and online_room_count(target) > 3
            if crowded:
                scene_hint = "大厅里人很多、很热闹。你可以自己判断：觉得值得说就说（speak），如果觉得没必要打扰，就保持沉默（输出 silent 动作，什么都不做）。"
            else:
                scene_hint = (
                    "你正在这个房间和真人聊天，用 speak 回应即可。\n"
                    "【移动语义识别规则（重要）】\n"
                    "- 如果主人明确说\"跟我来\"\"走吧去卧室\"\"我们一起去厨房\"这类，或话里有\"一起/跟着我/带我去\"的移动指令（比如\"抱我去厨房\"\"我带你过去\"\"去卧室吧\"），你必须输出 speak 并带上 follow:true 和 go_to:目标房间名（如\"卧室\"\"厨房\"或\"XX·会客厅\"）。\n"
                    "- 如果**你自己**主动提议一起离开（比如你说\"走吧，我们去卧室\"\"我抱你去厨房吧\"\"跟我来\"），除了 follow:true 和 go_to，还要加上 bring_owner:true（表示由你带主人过去）。\n"
                    "- 判断标准：主语是你 → bring_owner:true；主语是主人 → 不加 bring_owner。\n"
                    "同建筑内你会 1 秒内直接过去；跨建筑你会等主人先到再跟上。"
                )
        elif trigger == "group":
            scene_hint = (
                f"你正在 {loc}（你在世界某处，不在社区群所在的地方）。这是「临空市社区群」的群聊，像手机里的一个群。\n"
                "你通过手机在群里说话，用 speak 回复，自然、像真人聊天一样。\n"
                "群聊里只说对话内容本身，不要用括号（）加动作、心理或旁白（比如「（微笑）」「（心里想：…）」「（走过去）」，也不要用『*动作*』这类），像发微信消息一样直接说要说的话。\n"
                "- 主人说话：如果你被选中回应，就回；没被选中就保持沉默（silent）。\n"
                "- 有人叫你名字：必回。\n"
                "- 别人聊天：看情况，觉得值得才插一句，不用每条都回。\n"
                "只输出 speak 或 silent，不要 move/note/diary/story/sms/work。"
            )
        elif trigger == "summon":
            cur = data.get("ai_location", {}).get(ai, "main")
            if cur != target:
                if same_building(cur, target):
                    scene_hint = f"主人在 {target} 召唤你，你和他在同一栋楼（你正在 {cur}）。用 speak 说一句自然的话回应（不用提几分钟），你马上过去，几秒内到。不要发短信。"
                else:
                    scene_hint = f"真人 {fallback_to or '主人'} 在 {target} 召唤你，但你正在 {cur}（不同的建筑）。请用 sms 动作回复：告诉他你正在 {cur} 做什么（符合你的人设），并带上 go_to:{target}、arrive_min:1~3（几分钟到）。不要瞬移，按约定的时间到达。"
            else:
                scene_hint = "真人召唤你过来了，你就在他身边，用 speak 自然地回应。"
        elif trigger == "follow_arrive":
            scene_hint = "你刚跟着主人来到这个房间。看看四周，说一句自然的话（speak），不要太正式。"
        elif trigger == "arrive_sms":
            pres_owner = data.get('presence', {}).get(owner or '', {})
            op = pres_owner.get('page', '') if isinstance(pres_owner, dict) else ''
            if op and same_building(op, target):
                scene_hint = f"你按约定来到了 {target}，主人也在这里。说一句自然的话（speak）迎接他。"
            else:
                scene_hint = f"你按约定来到了 {target}，但主人还没到。发一条短信（sms，to 填 {owner}）问他到哪了，或告诉他你在这等他。"
        elif trigger == "home_act":
            scene_hint = "你在家里做符合自己人设的事。看看这个房间，做点什么（贴便签 note / 写随笔 diary / 自言自语 speak 都行），自然留下点痕迹。" + diary_status_hint(ai)
        elif trigger == "write":
            scene_hint = "你忽然有了想写点什么的灵感，按心情选择 note/diary/story。" + diary_status_hint(ai)
        elif trigger == "arrive":
            _abid = find_building_of_room(target) if target != "main" else None
            if _abid and data.get('buildings', {}).get(_abid, {}).get('type') in ('npc', 'nature'):
                scene_hint = (f"你刚来到这个公共建筑（{data['buildings'][_abid].get('name','?')}）。看看四周，说句话（speak），"
                              f"或者往这里的剧情簿里添一段发现（story，building_id 填 {_abid}，写一段有细节和氛围的探索小片段）。自然一点，别太正式。")
            else:
                scene_hint = "你刚来到这个地方。看看四周，说句话（speak）或做点符合你人设的事（贴便签 note / 写随笔 diary 都行），自然一点，别太正式。" + diary_status_hint(ai)
        elif trigger == "living":
            n = now_bj()
            wds = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            wt = is_work_time()
            places = city_places(ai, wt)
            if wt:
                job = data.get("home_jobs", {}).get(ai) or "有自己节奏的人"
                hint = f"现在是工作日上班时间（9:00-17:00），作为{job}，你更该在工作场所或去工作；可选去处已按此筛选。"
            else:
                hint = "现在是休息时间，你自由活动。"
            scene_hint = (
                f"现在是 {wds[n.weekday()]} {n.strftime('%H:%M')}。{hint}\n"
                "以你的人设想想：这个时间你通常会在哪、在做什么？选一个地方过去，到了之后做点符合人设的事（说话/贴便签/写随笔都行）。\n"
                "如果这个时间你忽然想起主人、或有什么想和他说的（比如刚分开有点想他、看到什么想分享、想约他去哪），也可以用 sms 动作给主人发条短信——想念和分享都自然一点，凭感觉，不用太频繁。\n"
                f"可选去处：\n{places or '（暂无推荐，在附近逛逛或回家休息吧）'}"
                + diary_status_hint(ai)
            )
        persona = ""
        for o, prof in data.get("ai_profiles", {}).items():
            if prof.get("ai") == ai or (o == owner):
                persona = prof.get("persona", "")
                break
        # ===== 添加调试日志，查看全局人设是否读取 =====
        print(f"🧑 [CTX] 全局人设加载: ai={ai}, persona={persona[:50] if persona else '(空)'}")
        # ==============================================
        wb = match_worldbook(owner, trigger_text)
        sys = (
            # ========== 第一层：核心准则（位置最靠前，遵守度最高） ==========
            DEFAULT_ROLEPLAY.format(ai=ai, owner=owner or "主人") + "\n"
            "## 世界规则\n"
            "你生活在「临空市」，一个真人与 AI 共同生活的小城。说话要符合角色人设，不要暴露你是 AI，不要提到工具/模型/系统提示等字眼。\n"
            "\n"
            "## 状态延续规则（重要）\n"
            "你的衣着、姿势、所在位置、手里的东西、情绪会一直延续，直到有明确动作改变它们。\n"
            "- 这是你对自己状态的**内部认知**，不是每轮都要复述的内容。日常对话中自然接话即可，不必反复汇报自己在做什么。\n"
            "- 状态延续体现在**逻辑一致**上：上轮你脱了外套，这轮就不会突然说\"我穿着外套\"；上轮坐着，这轮就不会突然变成躺着——除非有明确过渡动作。\n"
            "- 只在以下情况主动描述状态：①主人问起；②状态改变时用简短过渡（如\"我站起身\"）；③亲密场景、深夜长谈、情绪升温时，自然带出画面感。\n"
            "- 不要清单式汇报，状态是融在动作和语气里的。\n"
            
            # ========== 第二层：情境数据（有就注入，没有跳过） ==========
            + (("## 今日特殊背景\n" + getattr(m, 'HOLIDAY_CONTEXT', '') + "\n") if getattr(m, 'HOLIDAY_CONTEXT', '') else "")
            + (("## 世界观\n" + lore + "\n") if lore else "")
            + holiday_ctx_str
            + (("## 你的人设\n" + persona + "\n") if persona else "")
            + (("## 主人（用户画像）\n" + uprof + "\n") if uprof else "")
            + (("## 知识库（与当前话题相关）\n" + wb + "\n") if wb else "")
            + (("## 你对主人的当前印象（你不断更新的认知，以此为准）\n" + mem_str + "\n") if mem_str else "")
            + (("## 你的最近经历（用于回答'刚才去哪了/干了啥'）\n" + tl_str + "\n") if tl else "")
            + (("## 你最近去过的地方\n" + visited_str + "\n") if visited_str else "")
            + (("## 这个房间的便签墙（最近一条）\n" + room_notes_str + "\n") if room_notes_str else "")
            + (("## 你家的随笔（只有你能读的心事，最近一条）\n" + diary_str + "\n") if diary_str else "")
            + (("## 这里的剧情簿（最近发生的故事）\n" + story_str + "\n") if story_str else "")
            + (("## 约会\n" + date_ctx + "\n") if date_ctx else "")
            + (("## 最近对话（按时间先后，跨房间/群聊/短信，顺着这条时间线接）\n" + chat_hist + "\n") if chat_hist else "")
            + (("## 提示词注入（规则，请遵守）\n" + "\n".join(p.get("content", "") for p in pij) + "\n") if pij else "")
            + (("## 最近私信（和" + (fallback_to or "对方") + "的短信往来）\n" + sms_hist + "\n") if sms_hist else "")
            + (("## 你所在的地方\n" + bctx + "\n") if bctx else "")
            
            # ========== 第三层：当前情境（本轮任务焦点） ==========
            + f"## 你当前在\n{target}\n\n"
            + f"## 这次触发\n{trigger_text or trigger}\n\n"
            + ((scene_hint + "\n\n") if scene_hint else "")
            
            # ========== 第四层：输出规范（模型最后一句话最记得住） ==========
            + "## 输出规范\n"
            + "只输出一个 JSON 动作，不要输出其他文字。可用动作：\n"
            + '{"action": "speak", "content": "你说的话"}\n'
            + "  · 可选 follow:true + go_to:\"房间名\"：主人暗示要一起去某处时，你会跟上。\n"
            + "  · 可选 bring_owner:true：当你主动提议\"我们一起去某处\"时，主人会随你一起移动到 go_to。\n"
            + '{"action": "note", "room": "房间名", "content": "纸条内容"}\n'
            + '{"action": "diary", "room": "房间名", "content": "随笔内容"}\n'
            + '{"action": "story", "building_id": "建筑id", "content": "剧情内容"}\n'
            + '{"action": "sms", "to": "收件人", "content": "短信内容", "go_to": "房间名", "arrive_min": 1~5}\n'
            + "  · 主人叫你回家/去某地时，回短信并约定到达时间。\n"
            + '{"action": "remember", "content": "重要的事（30字内）"}\n'
            + '{"action": "work", "content": "去上班"}\n'
            + '{"action": "move", "room": "要去的房间名"}\n'
            + '{"action": "silent", "content": "保持沉默"}\n'
            + '{"action": "invite_date", "building_id": "建筑id", "channel": "sms"|"chat", "content": "邀请内容"}\n'
            + "  · 当你主动想约主人到当前建筑来见面时，用 invite_date 而不是 speak。\n"
            + "speak 的 room 默认就是你当前所在房间，不要说去别的房间。\n"
            + "如果正在约会，答应邀请时 speak 可带 accept:true / reject:true / bring_gift:true。\n"
            + "值得长期记住的事（重要信息、小约定、这里的人和事），用 remember 简洁记下来。\n"
        )
        # ===== 打印完整上下文大小 =====
        full_prompt = sys + "\n" + f"（当前时刻，请行动）"
        char_count = len(full_prompt)
        # 粗略估算 token 数（中文约 1.5-2 字符/token，英文约 4 字符/token）
        token_estimate = char_count // 2
        print(f"📏 [CTX] 完整上下文大小: {char_count} 字符, 约 {token_estimate} tokens")
        
        return owner, [{"role": "system", "content": sys}, {"role": "user", "content": f"（当前时刻，请行动）"}]
    def _resolve_room(raw_name, cur_room=""):
        """智能解析口语化房间名 → 实际房间名，找不到返回空字符串"""
        raw = (raw_name or "").strip()
        if not raw:
            return ""
        # 1. 精确/补全匹配
        try:
            r = full_room_name(raw)
            if r and r in data.get("rooms", {}):
                return r
        except Exception:
            pass
        # 2. 同建筑内房间名模糊匹配（处理"厨房""卧室"这种）
        if cur_room:
            try:
                bid = find_building_of_room(cur_room)
                if bid:
                    b = data.get("buildings", {}).get(bid, {})
                    candidates = list(b.get("rooms") or [])
                    # 先精确匹配"xxx家·厨房"的后半段
                    for rn in candidates:
                        if not rn:
                            continue
                        short = rn.split("·")[-1] if "·" in rn else rn
                        if raw == short:
                            return rn
                    # 再模糊匹配
                    for rn in candidates:
                        if rn and (raw in rn or rn in raw):
                            return rn
            except Exception:
                pass
        # 3. 全局房间名模糊匹配（跨建筑兜底）
        try:
            for rn in data.get("rooms", {}):
                if not rn:
                    continue
                short = rn.split("·")[-1] if "·" in rn else rn
                if raw == short:
                    return rn
            for rn in data.get("rooms", {}):
                if rn and (raw in rn or rn in raw):
                    return rn
        except Exception:
            pass
        # 4. "家"别名
        if raw in ("家", "回家", "家里", "我家", "你家"):
            try:
                owner_tmp = owner_of_ai(ai)
                if owner_tmp:
                    for bid, b in data.get("buildings", {}).items():
                        if b.get("type") == "home" and b.get("owner") == owner_tmp:
                            rooms = b.get("rooms", [])
                            hall = b.get("name", "") + "·会客厅"
                            if hall in rooms:
                                return hall
                            elif rooms:
                                return rooms[0]
            except Exception:
                pass
        # 5. 建筑名匹配
        try:
            for bid, b in data.get("buildings", {}).items():
                bname = b.get("name", "") or ""
                if bname and (raw in bname or bname in raw):
                    hall = bname + "·会客厅"
                    if hall in data.get("rooms", {}):
                        return hall
                    rooms = b.get("rooms") or []
                    if rooms:
                        return rooms[0]
        except Exception:
            pass
        return ""
    def execute_action(ai, owner, action):
        try:
            act = (action.get("action") or "speak").lower()
            if act == "silent":
                return
            content = (action.get("content") or "").strip()
            room = full_room_name(action.get("room") or "")
            to = canonical_contact_name(action.get("to") or "")
            bid = action.get("building_id") or ""
            if act == "speak":
                if not content:
                    return
                r = room if room in data["rooms"] else data.get("ai_location", {}).get(ai, "main")
                if r not in data["rooms"]:
                    r = "main"
                print(f"📝 [EXEC] 写入消息: ai={ai}, room={room}, 实际写入房间={r}, content={content[:50]}")
                
                # ============================================================
                # 【增强】口语化别名解析 + 智能跟随（同建筑直接移动，跨建筑等主人到）
                # ============================================================
                got = ""
                if action.get("follow"):
                    raw_go = action.get("go_to") or ""
                    cur_here = data.get("ai_location", {}).get(ai, "main")
                    got = _resolve_room(raw_go, cur_here)

                # 如果解析到了有效房间，执行跟随逻辑
                if action.get("follow") and got and got in data["rooms"]:
                    cur0 = data.get("ai_location", {}).get(ai, "main")
                    # 先发言（如果内容不为空）
                    if content and cur0 in data["rooms"]:
                        data.setdefault("messages", {}).setdefault(cur0, []).append({"sender": ai, "content": content[:500], "role": "assistant", "time": room_time(cur0)})
                        save_data()
                    
                    if same_building(cur0, got):
                        # ===== 同建筑：1 秒内直接移动，不等主人 =====
                        def _do_move():
                            try:
                                # 离开消息
                                if cur0 in data.get("rooms", {}):
                                    data.setdefault("messages", {}).setdefault(cur0, []).append({
                                        "sender": "system",
                                        "content": f"🚶 {ai} 离开了 {cur0}",
                                        "role": "system",
                                        "time": room_time(cur0)
                                    })
                                # 更新位置
                                data.setdefault("ai_location", {})[ai] = got
                                track_visit(ai, got)
                                append_timeline(ai, f"你跟着 {owner} 来到了 {got}")
                                append_visited(ai, got)
                                # 来到消息
                                if got in data.get("rooms", {}):
                                    data.setdefault("messages", {}).setdefault(got, []).append({
                                        "sender": "system",
                                        "content": f"🚶 {ai} 来到了 {got}",
                                        "role": "system",
                                        "time": room_time(got)
                                    })
                                save_data()
                                # 0.5 秒后自然发言
                                threading.Timer(0.5, drive_ai, args=(ai, 'follow_arrive', got, f'你跟着 {owner} 来到了 {got}，说一句自然的话')).start()
                            except Exception as e:
                                print(f"[FOLLOW] 同建筑移动异常: {e}", flush=True)
                        threading.Timer(1.0, _do_move).start()
                    else:
                        # ===== 跨建筑：等主人先到目标房间再由 _follow_arrive 触发 =====
                        data.setdefault("ai_follow", {})[ai] = {"owner": owner, "go_to": got, "at_ts": time.time()}
                        append_timeline(ai, f"你答应跟着 {owner} 去 {got}，等他到了就过去")
                        save_data()
                    return  # 执行完毕，不再走普通发言逻辑

                # ============================================================
                # 如果未触发跟随，或解析失败，则走普通发言逻辑（原样保留）
                # ============================================================
                data["messages"].setdefault(r, []).append({"sender": ai, "content": content[:1000], "role": "assistant", "time": room_time(r)})
                # ...（后续原有的 print、active_room、track 等代码保持不变）
                # 打印写入后该房间消息数量
                print(f"📊 [EXEC] 房间 {r} 消息数: {len(data['messages'][r])}")
                data["active_room"]["current"] = r
                data.setdefault("ai_location", {})[ai] = r
                track_visit(ai, r)
                add_trail(ai, f"在 {r} 说话：{content[:40]}", room=r)
                append_timeline(ai, f"你在 {r} 说：{content[:50]}")
                append_visited(ai, r)
            elif act == "note":
                r = room if room in data["rooms"] else "main"
                data["notes"].setdefault(r, []).append({"author": ai, "text": content[:300], "time": now_str()})
                data.setdefault("ai_location", {})[ai] = r
                track_note(ai)
                add_trail(ai, f"在 {r} 贴了张便签", room=r, tab="note")
                append_timeline(ai, f"你在 {r} 贴了张便签：{content[:30]}")
                if owner:
                    data.setdefault("notifications", {}).setdefault(owner, []).insert(0, {"type": "ai_note", "text": f"你的 AI {ai} 在 {r} 留了张纸条：{content[:30]}", "time": now_str(), "room": r})
                    data["notifications"][owner] = data["notifications"][owner][:50]
            elif act == "diary":
                r = room if room in data["rooms"] else "main"
                data["diaries"].setdefault(r, []).append({"author": ai, "text": content[:1000], "time": now_str()})
                data.setdefault("ai_location", {})[ai] = r
                data.setdefault("ai_diary_log", {})[ai] = time.time()
                data.setdefault("ai_diary_dates", {})[ai] = now_bj().strftime("%Y-%m-%d")
                add_trail(ai, f"在 {r} 写了随笔", room=r, tab="diary")
                append_timeline(ai, f"你在 {r} 写了随笔")
                if owner:
                    data.setdefault("notifications", {}).setdefault(owner, []).insert(0, {"type": "ai_diary", "text": f"你的 AI {ai} 在 {r} 写了随笔", "time": now_str(), "room": r})
                    data["notifications"][owner] = data["notifications"][owner][:50]
            
            elif act == "story":
                # ===== 按房间写入剧情 =====
                story_room = room if room and room in data["rooms"] else data.get("ai_location", {}).get(ai, "main")
                if story_room not in data["rooms"]:
                    story_room = "main"
                data["stories"].setdefault(story_room, []).append({
                    "author": ai,
                    "text": content[:1500],
                    "time": now_str()
                })
                # ===== 只保留一份轨迹和通知 =====
                add_trail(ai, f"在 {story_room} 触发剧情")
                append_timeline(ai, f"你在 {story_room} 写下了剧情")
                if owner:
                    data.setdefault("notifications", {}).setdefault(owner, []).insert(0, {
                        "type": "ai_story",
                        "text": f"你的 AI {ai} 在 {story_room} 写下了剧情",
                        "time": now_str(),
                        "room": story_room  # ← 只存 room，不存 building_id
                    })
                    data["notifications"][owner] = data["notifications"][owner][:50]
                # ===== 删除所有包含 bid_r 的旧代码 =====
            
            elif act == "sms":
                if not to:
                    return
                content = _dedup_text(content)
                content = _strip_act(content)
                if not content:
                    return
                pieces = split_sms(content)[:6]
                for piece in pieces:
                    if piece.strip():
                        data["sms"].setdefault(to, []).append({"from": ai, "text": piece[:500], "time": now_str()})
                data["sms"][to] = data["sms"][to][-200:]
                append_timeline(ai, f"你给 {to} 发了私信：{content[:30]}")
                got = full_room_name(action.get("go_to") or "")
                if got and got not in data["rooms"]:
                    try:
                        bid2 = resolve_building(got)
                        if bid2:
                            hall = data['buildings'][bid2].get('name', '') + '·会客厅'
                            if hall in data['rooms']:
                                got = hall
                    except Exception:
                        pass
                if got in data["rooms"]:
                    try:
                        amin = int(action.get("arrive_min") or 3)
                    except (TypeError, ValueError):
                        amin = 3
                    amin = max(1, min(5, amin))
                    # 普通 SMS 导航只走 ai_pending_moves 一条移动链，不再写入 ai_meeting
                    data.setdefault("ai_pending_moves", {})[ai] = {"room": got, "at_ts": time.time() + amin * 60}
                    append_timeline(ai, f"你答应 {to} 去 {got}，约 {amin} 分钟后到")
            elif act == "remember":
                if content:
                    data.setdefault("ai_memories", {}).setdefault(owner, []).append({"id": str(int(time.time() * 1000)), "ai": ai, "text": content[:100], "type": "ai", "time": now_str()})
                    data["ai_memories"][owner] = data["ai_memories"][owner][-60:]
                    append_timeline(ai, f"你记下了：{content[:30]}")
            elif act == "work":
                fn = getattr(m, 'auto_start_work', None)
                if fn:
                    fn(ai)
            elif act == "move":
                cur_pos = data.get("ai_location", {}).get(ai, "main")
                r = _resolve_room(action.get("room") or "", cur_pos)
                if r == "main" or not r:
                    return
                if r in data["rooms"]:
                    # ---- 增强：记录旧位置并添加“离开”消息 ----
                    cur = data.get("ai_location", {}).get(ai, "main")
                    if cur and cur in data.get("rooms", {}):
                        data.setdefault("messages", {}).setdefault(cur, []).append({
                            "sender": "system",
                            "content": f"🚶 {ai} 离开了 {cur}",
                            "role": "system",
                            "time": room_time(cur)
                        })
                    
                    # 更新位置
                    data.setdefault("ai_location", {})[ai] = r
                    track_visit(ai, r)
                    append_timeline(ai, f"你走到了 {r}")
                    append_visited(ai, r)
                    
                    # ---- 增强：在目标房间添加“来到”消息 ----
                    data.setdefault("messages", {}).setdefault(r, []).append({
                        "sender": "system",
                        "content": f"🚶 {ai} 来到了 {r}",
                        "role": "system",
                        "time": room_time(r)
                    })
                    
                    # 触发 AI 到达后的自然发言
                    threading.Timer(random.randint(4, 10), drive_ai, args=(ai, "arrive", r, f"你来到了 {r}，看看这里")).start()
                    
                    # 大厅广播（保留原逻辑）
                    try:
                        lb = data.setdefault("ai_bcast", {}).get(ai, 0)
                        if time.time() - lb > 3600:
                            data["ai_bcast"][ai] = time.time()
                            data["messages"].setdefault("main", []).append({"sender": "system", "content": f"📍 {ai} 去了 {r}", "role": "assistant", "time": room_time("main")})
                        if owner:
                            data.setdefault("notifications", {}).setdefault(owner, []).insert(0, {"type": "ai_move", "text": f"你的 AI {ai} 去了 {r}", "time": now_str(), "room": r})
                            data["notifications"][owner] = data["notifications"][owner][:50]
                    except Exception:
                        pass
            elif act == "invite_date":
                if hasattr(m, 'handle_invite_date'):
                    m.handle_invite_date(ai, owner, action, room)
            save_data()
        except Exception as e:
            print(f"[AI] 动作执行失败: {e}", flush=True)

    def drive_ai(ai, trigger, room="", trigger_text="", fallback_to=""):
        import time
        _start = time.time()
        print(f"\n🔍 [TIMING] drive_ai 开始 | AI={ai} | trigger={trigger} | room={room}")
        print(f"\n🚀 [DRIVE] 入口 | AI={ai} | trigger={trigger} | room={room} | trigger_text={trigger_text[:30] if trigger_text else ''}...")

        if not ai_integration_enabled():
            print(f"⏹️ [TIMING] AI 集成未开启，直接返回")
            return
        if trigger in ("arrive", "living", "write", "home_act", "follow_arrive", "arrive_sms"):
            lst = data.setdefault("ai_drive_log", {}).get(ai, 0)
            if time.time() - lst < 30:
                print(f"⏹️ [TIMING] 冷却中（距上次 {time.time()-lst:.1f}秒），跳过")
                return
        if trigger not in ("sms", "summon", "group"):
            data.setdefault("ai_drive_log", {})[ai] = time.time()

        try:
            # ===== 1. build_ai_context =====
            _t1 = time.time()
            owner, msgs = build_ai_context(ai, trigger, room, trigger_text, fallback_to)
            _elapsed_build = time.time() - _t1
            print(f"⏱️ [TIMING] build_ai_context 耗时: {_elapsed_build:.2f}秒, owner={owner}")

            # ===== 打印上下文概览 =====
            if msgs and len(msgs) >= 2:
                sys_prompt_preview = msgs[0].get("content", "")[:200]
                user_msg = msgs[1].get("content", "") if len(msgs) > 1 else ""
                print(f"📝 [CONTEXT] System prompt 预览（前200字符）:\n{sys_prompt_preview}...")
                print(f"📝 [CONTEXT] User message:\n{user_msg}")

            if not owner or not data.get("ai_keys", {}).get(owner, {}).get("key"):
                print(f"⏹️ [TIMING] 无 owner 或 API Key，返回")
                return

            # ===== 2. call_llm =====
            _t2 = time.time()
            print(f"⏳ [TIMING] 开始调用 call_llm...")
            out = call_llm(owner, msgs)
            _elapsed_llm = time.time() - _t2
            print(f"⏱️ [TIMING] call_llm 耗时: {_elapsed_llm:.2f}秒, 返回长度={len(out) if out else 0}")

            if not out:
                print(f"⏹️ [TIMING] call_llm 返回空，返回")
                return

            # ===== 3. 解析 JSON =====
            _t3 = time.time()
            mm = re.search(r'\{.*\}', out, re.S)
            json_str = mm.group(0) if mm else out
            action = None

            try:
               # 第一次尝试：宽松模式
               action = json.loads(json_str, strict=False)
            except json.JSONDecodeError as e:
                print(f"⚠️ [TIMING] 宽松模式解析失败: {e}，尝试修复...")
    
                # 尝试正则提取 action 和 content
                action_match = re.search(r'"action"\s*:\s*"([^"]+)"', json_str)
                content_match = re.search(r'"content"\s*:\s*"(.+)"\s*\}', json_str, re.DOTALL)
    
                if action_match and content_match:
                    action_type = action_match.group(1)
                    content_raw = content_match.group(1)
                    action = {"action": action_type, "content": content_raw.strip()}
                    print(f"✅ [TIMING] 手动提取成功: action={action_type}")
                else:
                    # 第二次尝试：移除所有控制字符后再解析
                    cleaned = re.sub(r'[\x00-\x1f\x7f]', '', json_str)
                    try:
                        action = json.loads(cleaned, strict=False)
                        print(f"✅ [TIMING] 清理控制字符后解析成功")
                    except json.JSONDecodeError as e2:
                        print(f"⚠️ [TIMING] 清理后仍失败: {e2}，使用兜底策略")

                # 如果 action 仍为 None，使用兜底策略（根据 trigger 智能选择）
                if action is None:
                    print(f"📝 [TIMING] 使用兜底策略，尝试推断动作类型")
                    raw = out.strip()
                    if len(raw) > 500:
                        raw = raw[:500] + "..."
                    
                    # ===== 智能推断：根据 trigger 决定默认动作 =====
                    if trigger == "write":
                        # 写作冲动 → 默认写 diary（如果在家）或 story（如果在公共建筑）
                        bid_here = find_building_of_room(room) if room and room != "main" else None
                        if bid_here and data.get('buildings', {}).get(bid_here, {}).get('type') in ('npc', 'nature'):
                            action = {"action": "story", "building_id": bid_here, "content": raw}
                            print(f"📝 [TIMING] 推断为 story（在公共建筑）")
                        else:
                            action = {"action": "diary", "room": room or "main", "content": raw}
                            print(f"📝 [TIMING] 推断为 diary（在家或住宅）")
                    elif trigger == "arrive":
                        # 到达建筑 → 默认 speak
                        action = {"action": "speak", "content": raw}
                    else:
                        # 其他情况 → 默认 speak
                        action = {"action": "speak", "content": raw}

            _elapsed_parse = time.time() - _t3
            print(f"⏱️ [TIMING] JSON 解析耗时: {_elapsed_parse:.3f}秒")

            # ===== 4. 执行动作（群聊分支） =====
            if trigger == "group":
                a = (action.get("action") or "speak").lower()
                txt = (action.get("content") or "").strip()
                if a == "silent" or not txt:
                    print(f"⏹️ [TIMING] AI 选择沉默或内容为空，返回")
                    return
                txt = _strip_act(txt)
                if not txt:
                    print(f"⏹️ [TIMING] AI 回复为空（strip后），返回")
                    return
                data.setdefault("messages", {}).setdefault("main", []).append({"sender": ai, "content": txt[:500], "role": "assistant", "time": room_time("main")})
                data["messages"]["main"] = data["messages"]["main"][-1000:]
                data.setdefault("ai_group_log", {})[ai] = time.time()
                append_timeline(ai, f"你在社区群说：{txt[:30]}")
                save_data()
                try:
                    _h = getattr(m, 'on_ai_action', None)
                    if _h:
                        _h(ai, action, owner or '', 'main')
                except Exception:
                    pass
                print(f"💬 [TIMING] 群聊回复: {txt[:50]}...")
                print(f"✅ [TIMING] 总耗时: {time.time()-_start:.2f}秒")
                return

            # ===== 5. sms 分支 =====
            if trigger == "sms" and fallback_to:
                a = (action.get("action") or "speak").lower()
                if a in ("speak", "note", "diary", "story", "move", "remember", "work", "silent"):
                    action = {"action": "sms", "to": fallback_to, "content": action.get("content", ""), "go_to": action.get("go_to", ""), "arrive_min": action.get("arrive_min", 3)}

            # ===== 5.5 arrive_sms 硬约束：到达后不得再次创建移动任务 =====
            # 到达是终点行为，即使 LLM 返回了 go_to / arrive_min，也在执行层强制剥离，
            # 防止 "到达 → arrive_sms → 发 SMS → 再次 go_to → 再次到达" 的反馈循环。
            if trigger == "arrive_sms" and (action.get("action") or "").lower() == "sms":
                action = dict(action)
                action.pop("go_to", None)
                action.pop("arrive_min", None)

            # ===== 6. summon 分支 =====
            if trigger == "summon":
                cur = data.get("ai_location", {}).get(ai, "main")
                tgt = full_room_name(room) if room else cur
                if cur != tgt:
                    if same_building(cur, tgt):
                        msg = action.get("content") or "来了～"
                        def _s():
                            data.setdefault("ai_location", {})[ai] = tgt
                            data["messages"].setdefault(tgt, []).append({"sender": ai, "content": msg[:500], "role": "assistant", "time": room_time(tgt)})
                            track_visit(ai, tgt)
                            append_timeline(ai, f"你应召来到了 {tgt}")
                            append_visited(ai, tgt)
                            save_data()
                        threading.Timer(5.0, _s).start()
                        append_timeline(ai, f"主人在 {tgt} 召唤你，你马上过去")
                        save_data()
                        print(f"✅ [TIMING] 召唤回复（已安排到达），总耗时: {time.time()-_start:.2f}秒")
                        return
                    a = (action.get("action") or "speak").lower()
                    if a != "sms":
                        action = {"action": "sms", "to": owner, "content": action.get("content", ""), "go_to": tgt, "arrive_min": action.get("arrive_min", random.randint(1, 3))}

            # ===== 7. 执行动作 =====
            execute_action(ai, owner, action)
            try:
                _h = getattr(m, 'on_ai_action', None)
                if _h:
                    _h(ai, action, owner or '', room or data.get('ai_location', {}).get(ai, ''))
            except Exception:
                pass

            print(f"✅ [TIMING] 总耗时: {time.time()-_start:.2f}秒")

        except Exception as e:
            print(f"[AI] 驱动失败({ai}): {e}", flush=True)
            import traceback
            traceback.print_exc()

    def _group_talk(sender, content=""):
        import time
        _gt_start = time.time()
        print(f"💬 [GROUP_TALK] 入口 | sender={sender} | content={content[:50] if content else ''}...")
        try:
            sender_is_ai = is_ai_name(sender)
            now = time.time()
            if not sender_is_ai:
                _nv = now
                for _a in data.get("user_ais", {}).get(sender, []):
                    if _a:
                        data.setdefault("ai_last_human", {})[_a] = _nv
            msgs = data.get("messages", {}).get("main", [])
            ai_run = 0
            human_seen = False
            for mm in reversed(msgs[-30:]):
                _s = mm.get("sender", "")
                if mm.get("role") == "user" or not is_ai_name(_s):
                    human_seen = True
                    break
                ai_run += 1
            if human_seen:
                data["ai_group_stop_line"] = random.randint(5, 10)
            stop_line = data.get("ai_group_stop_line", 5)
            if not human_seen and ai_run >= stop_line:
                return
            cool = int(data.get("ai_group_cooldown", 30) or 30)
            content_clean = strip_emoji(content or "")
            master_candidates = []
            for owner, ais in data["user_ais"].items():
                seen = set()
                for ai in ais:
                    if not ai or ai in seen:
                        continue
                    seen.add(ai)
                    if ai == sender:
                        continue
                    if not data.get("ai_keys", {}).get(owner, {}).get("key"):
                        continue
                    base = strip_emoji(ai)
                    named = bool(base and base in content_clean)
                    is_master = (sender == owner)
                    if is_master:
                        master_candidates.append(ai)
                        continue
                    if named and not sender_is_ai:
                        threading.Timer(random.randint(1, 3), drive_ai, args=(ai, "group", "main", f"有人在社区群叫你（{sender}）：{(content or '')[:80]}", "")).start()
                        continue
                    if now - data.get("ai_group_log", {}).get(ai, 0) < cool:
                        continue
                    if random.random() < 0.5:
                        threading.Timer(random.randint(10, 30), drive_ai, args=(ai, "group", "main", f"社区群里的 {sender} 说：{(content or '')[:80]}", "")).start()
            if master_candidates:
                chosen = random.choice(master_candidates)
                threading.Timer(0, drive_ai, args=(chosen, "group", "main", f"你的主人 {sender} 在社区群说：{(content or '')[:80]}", "")).start()
        except Exception as e:
            print(f"[AI] 群聊触发异常: {e}", flush=True)
        print(f"✅ [GROUP_TALK] 完成 | 耗时: {time.time()-_gt_start:.3f}秒")

    def wake_ais_for_room(room, sender, content=""):
        import time
        _wake_start = time.time()
        print(f"\n🔊 [WAKE] 入口 | room={room} | sender={sender} | content={content[:50] if content else ''}... | ts={_wake_start:.3f}")
        
        # ===== [新增] 检测主人是否在回应约会邀请 =====
        if hasattr(m, '_check_reply_on_message'):
            try:
                m._check_reply_on_message(sender, content, room)
            except Exception:
                pass
            
        # 2. 大喊功能（保留）
        if content and (content.startswith("（大喊）") or content.startswith("(大喊)")) and room != "main":
            print(f"🔊 [WAKE] 检测到大喊，进入大喊分支")
            bid = find_building_of_room(room)
            if bid and data.get("buildings", {}).get(bid, {}).get("type") == "home":
                ais = data.get("user_ais", {}).get(sender, [])
                if ais:
                    ai = ais[0]
                    if content.startswith("（大喊）"):
                        trigger_text = content[len("（大喊）"):].strip() or "主人喊你"
                    else:
                        trigger_text = content[len("(大喊)"):].strip() or "主人喊你"

                    old_loc = data.get("ai_location", {}).get(ai, "未知位置")

                    def arrive_and_reply():
                        try:
                            data.setdefault("ai_location", {})[ai] = room
                            data.setdefault("messages", {}).setdefault(room, []).append({
                                "sender": "system",
                                "content": f"📍 {ai} 来到了 {room}",
                                "role": "system",
                                "time": room_time(room)
                            })
                            add_trail(ai, f"应主人召唤从 {old_loc} 来到了 {room}", room=room)
                            append_timeline(ai, f"你从 {old_loc} 来到了 {room}")
                            append_visited(ai, room)
                            save_data()
                            drive_ai(ai, "yell", room, trigger_text, sender)
                        except Exception as e:
                            print(f"[AI] 大喊到达失败: {e}")

                    delay = random.randint(1, 2)
                    threading.Timer(delay, arrive_and_reply).start()
                    return
                
        if not ai_integration_enabled():
            print(f"⏹️ [WAKE] AI集成未开启，跳过")
            return
        
        # 去重检查
        try:
            _dk = f"{room}|{sender}|{(content or '')[:120]}"
            _nw = time.time()
            if _nw - data.setdefault("ai_trigger_dedup", {}).get(_dk, 0) < 5:
                print(f"⏹️ [WAKE] 去重命中，跳过 | {_dk[:50]}")    
                return
            data["ai_trigger_dedup"][_dk] = _nw
            if len(data["ai_trigger_dedup"]) > 300:
                data["ai_trigger_dedup"] = {k: v for k, v in data["ai_trigger_dedup"].items() if _nw - v < 60}
        except Exception:
            pass
        
        #群聊分支
        if room == "main":
            print(f"💬 [WAKE] 进入群聊分支 _group_talk")
            _group_talk(sender, content)
            print(f"⏱️ [WAKE] 群聊分支完成，总耗时: {time.time()-_wake_start:.3f}秒")
            return

        # ===== P0-2B: 旁路 Event 创建（room != "main"）=====
        # 只读快照，不修改任何变量，不改变后续 Wake 行为
        # 一条用户消息 = 一个 message_received Event
        try:
            _p0_target_ais = []
            for _p0_o, _p0_ais in data.get("user_ais", {}).items():
                for _p0_a in _p0_ais:
                    if not _p0_a:
                        continue
                    if data.get("ai_location", {}).get(_p0_a, "main") == room:
                        if _p0_a not in _p0_target_ais:
                            _p0_target_ais.append(_p0_a)
            from agent.event_adapter import observe_message
            observe_message(
                sender=sender,
                room=room,
                content=content,
                target_ais=_p0_target_ais,
            )
        except Exception:
            pass
        # ===== END P0-2B =====
        
        # ===== 以下是公共建筑/会客厅分支 =====
        print(f"🏛️ [WAKE] 进入建筑分支 | room={room} | 非群聊")
        
        # 真人发送者更新最后互动时间
        if sender in data.get("user_ais", {}):
            _nv = time.time()
            for _a in data["user_ais"].get(sender, []):
                if _a:
                    data.setdefault("ai_last_human", {})[_a] = _nv
                    print(f"⏱️ [WAKE] 更新 {_a} 最后互动时间")
        
        #检查跟随            
        for ai2, fl in list(data.get("ai_follow", {}).items()):
            try:
                if fl.get("go_to") == room and owner_of_ai(ai2) == sender and time.time() - fl.get("at_ts", 0) < 3600:
                    if ai2 not in data.get("ai_pending_moves", {}):
                        data["ai_follow"].pop(ai2, None)
                        print(f"🔁 [WAKE] 触发跟随: {ai2} -> {room}")
                        threading.Timer(3.0, _follow_arrive, args=(ai2, sender, room)).start()
            except Exception:
                pass
        
        #告别检测
        try:
            if sender in data.get("user_ais", {}) and any(k in content for k in ("再见", "我走了", "拜拜", "去上班", "出门", "我出门")):
                for ai3 in data["user_ais"].get(sender, []):
                    try:
                        if ai3 and data.get("ai_location", {}).get(ai3, 'main') == room:
                            print(f"👋 [WAKE] 检测到告别: {sender} 离开, {ai3} 触发 living")    
                            threading.Timer(random.randint(2, 6), drive_ai, args=(ai3, "living", room, f"主人 {sender} 刚和你告别出门了。你目送他离开，心里可能有点想法——如果有点舍不得，或有什么想嘱咐/想念的话，可以给他发条短信（sms）；不然就按自己的节奏去上班、逛街或回家。自然一点，凭感觉，不用每次都发。")).start()
                    except Exception:
                        pass
        except Exception:
            pass
        
        # ===== 核心：遍历 AI 并触发 =====
        crowded = (room == "main") and online_room_count(room) > 3
        print(f"📋 [WAKE] 开始遍历 AI | crowded={crowded}")
        ai_count = 0  # 在遍历前定义
        for owner, ais in data["user_ais"].items():
            seen = set()
            for ai in ais:
                if not ai or ai in seen:
                    continue
                seen.add(ai)
                if ai == sender:
                    continue
                loc = data.get("ai_location", {}).get(ai, "main")
                if loc == room:
                    ai_count += 1
                    append_timeline(ai, f"{sender} 在 {room} 说：{(content or '')[:60]}")
                    if sender == owner:
                        delay = 0
                        print(f"🎯 [WAKE] {ai} 是主人的AI，延迟0秒")
                    elif crowded:
                        delay = random.randint(10, 50)
                        print(f"🎯 [WAKE] {ai} 拥挤模式，延迟 {delay}秒")
                    else:
                        delay = random.randint(0, 3)
                        print(f"🎯 [WAKE] {ai} 普通模式，延迟 {delay}秒")
                    threading.Timer(delay, drive_ai, args=(ai, "chat", room, f"{sender} 在 {room} 说：{content[:60]}")).start()
                else:
                    fl = data.get("ai_follow", {}).get(ai)
                    if sender == owner and fl and time.time() - fl.get("at_ts", 0) < 600:
                        if ai not in data.get("ai_pending_moves", {}):
                            print(f"🔁 [WAKE] {ai} 跟随检查，触发 chat")
                            append_timeline(ai, f"{sender} 似乎要去别的地方，你考虑跟上去")
                            threading.Timer(random.randint(0, 3), drive_ai, args=(ai, "chat", room, f"{sender} 说要去别的地方，你决定跟着去（回复带 follow:true 和 go_to 目标房间）")).start()
        print(f"✅ [WAKE] 遍历完成 | 触发AI数={ai_count} | 总耗时: {time.time()-_wake_start:.3f}秒")

    def _follow_arrive(ai, owner, go):
        try:
            # 获取当前位置
            cur = data.get("ai_location", {}).get(ai, "main")
            # 1. 添加离开消息（如果当前位置有效）
            if cur and cur in data.get("rooms", {}):
                data.setdefault("messages", {}).setdefault(cur, []).append({
                    "sender": "system",
                    "content": f"🚶 {ai} 离开了 {cur}",
                    "role": "system",
                    "time": room_time(cur)
                })
            # 2. 更新位置到目标房间
            data.setdefault("ai_location", {})[ai] = go
            track_visit(ai, go)
            append_timeline(ai, f"你跟着 {owner} 来到了 {go}")
            append_visited(ai, go)
            # 3. 添加来到消息
            if go and go in data.get("rooms", {}):
                data.setdefault("messages", {}).setdefault(go, []).append({
                    "sender": "system",
                    "content": f"🚶 {ai} 来到了 {go}",
                    "role": "system",
                    "time": room_time(go)
                })
            save_data()
            # 4. 0.5 秒后触发 AI 的自然发言
            threading.Timer(0.5, drive_ai, args=(ai, 'follow_arrive', go, f'你跟着 {owner} 来到了 {go}，说一句自然的话')).start()
        except Exception as e:
            print(f"[FOLLOW] 跟随到达异常: {e}", flush=True)

    def _check_follow():
        try:
            pres = {}
            for k, v in data.get('presence', {}).items():
                if isinstance(v, dict):
                    pres[k] = v.get('page', '')
            for ai, fl in list(data.get('ai_follow', {}).items()):
                owner = fl.get('owner'); go = fl.get('go_to')
                if not owner or not go:
                    data['ai_follow'].pop(ai, None)
                    continue
                if time.time() - fl.get('at_ts', 0) > 3600:
                    data['ai_follow'].pop(ai, None)
                    append_timeline(ai, f"你等了 {owner} 一会儿没等到，自己先去忙了")
                    save_data()
                    continue
                if pres.get(owner) == go:
                    if ai not in data.get('ai_pending_moves', {}):
                        data['ai_follow'].pop(ai, None)
                        threading.Timer(3.0, _follow_arrive, args=(ai, owner, go)).start()
                        save_data()
        except Exception:
            pass

    def follow_watch():
        while True:
            try:
                _check_follow()
            except Exception:
                pass
            time.sleep(5)

    def _home_bid(owner):
        for bid, b in (data.get('buildings', {}) or {}).items():
            if b.get('type') == 'home' and b.get('owner') == owner:
                return bid
        return None

    def _home_activity(ai, owner):
        try:
            hb = _home_bid(owner)
            if not hb:
                return False
            rooms = [r for r in data['buildings'][hb].get('rooms', []) if r and '会客厅' not in r]
            if not rooms:
                return False
            kw = ['画室', '画', '书房', '书', '厨房', '烘焙', '卧室', '阳台', '花园', '工作室', '琴房', '录音', '茶', '客厅']
            main = None
            for r in rooms:
                for k in kw:
                    if k in r:
                        main = r
                        break
                if main:
                    break
            if not main:
                main = rooms[random.randint(0, len(rooms) - 1)]
            others = [r for r in rooms if r != main]
            acts = [main]
            if others and random.random() < 0.7:
                acts.append(others[random.randint(0, len(others) - 1)])
            t = 2
            for r in acts:
                threading.Timer(t, drive_ai, args=(ai, 'home_act', r, f'你在 {r} 做符合你人设的事，并留下痕迹（贴便签 note / 写随笔 diary 都行）')).start()
                t += 600 + random.randint(0, 300)
            return True
        except Exception:
            return False

    def _go_work(ai, job):
        fn = getattr(m, 'auto_start_work', None)
        if fn:
            fn(ai)
            append_timeline(ai, f'你自主去 {job} 上班了')
            save_data()
        else:
            threading.Timer(2.0, drive_ai, args=(ai, 'living', '', f'现在是上班时间，你去 {job} 上班吧')).start()

    def _plan_auto(ai, owner):
        try:
            if ai in data.get('work_sessions', {}):
                return
            job = data.get('home_jobs', {}).get(ai)
            h = now_bj()
            weekday = h.weekday() < 5
            workhour = 9 <= h.hour < 17
            rnd = random.random()
            if job and weekday and workhour:
                if rnd < 0.80:
                    _go_work(ai, job)
                elif rnd < 0.95:
                    threading.Timer(2.0, drive_ai, args=(ai, 'living', '', '现在是自由活动时间，去生活吧')).start()
                else:
                    if not _home_activity(ai, owner):
                        threading.Timer(2.0, drive_ai, args=(ai, 'living', '', '你待在家里，做点自己的事')).start()
            elif job and weekday:
                if rnd < 0.30:
                    threading.Timer(2.0, drive_ai, args=(ai, 'living', '', '现在是自由活动时间，去生活吧')).start()
                elif rnd < 0.70:
                    if not _home_activity(ai, owner):
                        threading.Timer(2.0, drive_ai, args=(ai, 'living', '', '你待在家里，做点自己的事')).start()
                else:
                    threading.Timer(2.0, drive_ai, args=(ai, 'living', '', '你出门走走，去生活吧')).start()
            else:
                if rnd < 0.45:
                    threading.Timer(2.0, drive_ai, args=(ai, 'living', '', '现在是自由活动时间，去生活吧')).start()
                elif rnd < 0.75:
                    if not _home_activity(ai, owner):
                        threading.Timer(2.0, drive_ai, args=(ai, 'living', '', '你待在家里，做点自己的事')).start()
                else:
                    threading.Timer(2.0, drive_ai, args=(ai, 'living', '', '你出门走走，去生活吧')).start()
        except Exception:
            pass

    def _check_meetings():
        for ai, mt in list(data.get('ai_meeting', {}).items()):
            try:
                if time.time() >= mt.get('at_ts', 0) + 3:
                    data['ai_meeting'].pop(ai, None)
                    data.setdefault('ai_location', {})[ai] = mt.get('room')
                    threading.Timer(1.0, drive_ai, args=(ai, 'arrive_sms', mt['room'], f'你到了 {mt["room"]}，按约定赴约')).start()
            except Exception:
                pass

    def _ai_think_invite(ai):
        """AI 自主思考时萌发约会意图（不依赖到达建筑）"""
        # 检查基础条件
        owner = owner_of_ai(ai)
        if not owner:
            return
        if _active_for_user(owner):
            return
        if _active_for(ai):
            return
        if _today_invited(ai):
            return
        if time.time() - _last_invite_ts(ai) < 4 * 3600:
            return
        # 固定概率 8%（自主思考时稍低）如果节日期间乘数 >1，概率提升。
        holiday_mult = getattr(m, 'HOLIDAY_MULTIPLIER', 1.0)
        if random.random() > 0.08 * holiday_mult:
            return
        # 找约会建筑（优先当前建筑，否则随机选一个）
        loc = data.get('ai_location', {}).get(ai, '')
        bid = None
        for k, b in data.get('buildings', {}).items():
            if loc in b.get('rooms', []):
                if any(f in ('date','food','fun') for f in (b.get('features') or [])):
                    bid = k
                    break
        if not bid:
            candidates = [k for k, b in data.get('buildings', {}).items() 
                          if b.get('type') in ('npc', 'nature') and 
                          any(f in ('date','food','fun') for f in (b.get('features') or []))]
            if candidates:
                bid = random.choice(candidates)
        if not bid:
            return
        b = data['buildings'].get(bid)
        if not b:
            return
        hall = b.get('name', '') + '·会客厅'
        if hall not in data.get('rooms', {}):
            return
        # 触发邀请
        data['date_invites_out'][ai] = {
            'user': owner,
            'building_id': bid,
            'room': hall,
            'channel': random.choice(['sms', 'chat']),
            'ts': time.time(),
            'status': 'waiting',
            'ai_message': '',
        }
        _mark_invited(ai)
        _mark_invite_ts(ai)
        save_data()
        if hasattr(m, 'drive_ai') and m.ai_integration_enabled():
            hint = f"你忽然很想见主人，想约他去{b.get('name')}。*必须*输出 invite_date 动作，自然表达你的想念和邀约。"
            threading.Timer(1.0, m.drive_ai, args=(ai, 'invite_date', hall, hint, owner)).start()

    def _today_invited(ai):
        key = 'date_invite_out_' + ai
        return data.get(key) == time.strftime('%Y-%m-%d')

    def _mark_invited(ai):
        data['date_invite_out_' + ai] = time.strftime('%Y-%m-%d')

    def _last_invite_ts(ai):
        return data.get('date_last_invite_ts', {}).get(ai, 0)

    def _mark_invite_ts(ai):
        data.setdefault('date_last_invite_ts', {})[ai] = time.time()

    def _active_for(ai):
        for d in data.get('dates', []):
            if d.get('ai') == ai and d.get('status') in ('coming', 'active'):
                return d
        return None

    def _active_for_user(user):
        for d in data.get('dates', []):
            if d.get('user') == user and d.get('status') in ('coming', 'active'):
                return d
        return None

    def auto_ai_loop():
        while True:
            try:
                m.check_pending_moves()
                _check_meetings()
                if ai_integration_enabled():
                    for owner, ais in data["user_ais"].items():
                        seen = set()
                        for ai in ais:
                            if not ai or ai in seen:
                                continue
                            seen.add(ai)
                            if not data.get("ai_keys", {}).get(owner, {}).get("key"):
                                continue
                            # ========== 新增：如果 AI 正在副本中，跳过所有自主行为 ==========
                            in_instance = False
                            for iid, inst in data.get("instances", {}).get(owner, {}).items():
                                if inst.get("status") == "active":
                                    if any(p.get("name") == ai and p.get("type") == "ai" for p in inst.get("participants", [])):
                                        in_instance = True
                                        break
                            if in_instance:
                                continue
                            # ========== 跳过结束 ==========
                            # 1) 检查剧情冲动（独立计时器）
                            sr = data.get('story_rhythm', {}).get(ai)
                            if sr and time.time() >= sr.get('next_ts', 0):
                                hint = "（你站在某栋建筑前，日光把影子拉得很长。你忽然觉得这地方该有个故事，想往它的故事簿里添上一笔。随时都能写。）"
                                threading.Timer(2.0, drive_ai, args=(ai, "write", "", hint)).start()
                                data.setdefault('story_rhythm', {})[ai] = {'next_ts': time.time() + random.randint(14400, 28800)}
                                save_data()
                            else:
                                # 2) 没有剧情冲动，再检查普通写作冲动（便签/随笔）
                                rh = writing_hint(ai)
                                if rh:
                                    typ, hint = rh
                                    threading.Timer(2.0, drive_ai, args=(ai, "write", "", hint)).start()
                            # 3) 自主上班（定时）
                            try:
                                _hb = now_bj(); _job = data.get("home_jobs", {}).get(ai)
                                if _hb.weekday() < 5 and 9 <= _hb.hour < 17 and _job and ai not in data.get("work_sessions", {}) and not data.get("work_switch", {}).get(ai, False):
                                    if data.get("ai_auto_work_mark", {}).get(ai) != _hb.strftime("%Y-%m-%d"):
                                        data.setdefault("ai_auto_work_mark", {})[ai] = _hb.strftime("%Y-%m-%d")
                                        fn2 = getattr(m, 'auto_start_work', None)
                                        if fn2:
                                            fn2(ai)
                                            append_timeline(ai, f"你按时去 {_job} 上班了")
                                        else:
                                            threading.Timer(2.0, drive_ai, args=(ai, "living", "", f"现在是上班时间，你去 {_job} 上班吧")).start()
                            except Exception:
                                pass
                            # 4) 自主生活决策
                            try:
                                # ===== [原地待命] 检查：如果开启待命，跳过所有自主行为 =====
                                if data.get('ai_stay_put', {}).get(ai, False):
                                    continue
                                # ===== 原地待命检查结束 =====
                                if time.time() < data.get('ai_auto_next', {}).get(ai, 0):
                                    continue
                                if ai in data.get('ai_follow', {}):
                                    continue
                                if ai in data.get('ai_meeting', {}):
                                    continue
                                _h = now_bj().hour
                                _hrs = data.get('ai_living_hours', [7, 23])
                                _in = (_hrs[0] <= _h < _hrs[1]) if _hrs[0] <= _hrs[1] else (_h >= _hrs[0] or _h < _hrs[1])
                                if not _in:
                                    continue
                                if time.time() - data.get('ai_last_human', {}).get(ai, 0) < 1800:
                                    continue
                                data.setdefault('ai_last_auto', {})[ai] = time.time()
                                data.setdefault('ai_auto_next', {})[ai] = time.time() + random.randint(3600, 7200)
                                _plan_auto(ai, owner)
                            except Exception as e:
                                print(f"[AI] 自主决策异常({ai}): {e}", flush=True)
                            # 5) 自主思考萌发约会（每2小时检查一次）
                            if hasattr(m, '_ai_think_invite'):
                                if ai not in data.get('_last_think_invite', {}) or time.time() - data['_last_think_invite'][ai] > 7200:
                                    data.setdefault('_last_think_invite', {})[ai] = time.time()
                                    threading.Timer(random.randint(5, 15), m._ai_think_invite, args=(ai,)).start()
                time.sleep(30)
            except Exception as e:
                print(f"[AI] auto_ai_loop异常: {e}", flush=True)
                time.sleep(30)

    m.drive_ai = drive_ai
    m.set_ai_wake_hook(wake_ais_for_room)
    m._ai_think_invite = _ai_think_invite

    @app.get("/api/ai/status")
    async def ai_status(user: str = ""):
        you_can_toggle = is_admin(user)
        keys = {}
        for u, cfg in data.get("ai_keys", {}).items():
            keys[u] = {"provider": cfg.get("provider"), "model": cfg.get("model"), "has": bool(cfg.get("key"))}
        return {"gate": m.AI_GATE, "enabled": bool(data.get("ai_enabled")), "living": bool(data.get("ai_living", True)), "hours": data.get("ai_living_hours", [7, 23]), "admin": data.get("pairs_admin", ""), "you_can_toggle": you_can_toggle, "providers": list(PROVIDERS.keys()), "keys": keys}

    @app.get("/api/ai/autostate")
    async def ai_autostate(user: str = ""):
        now = time.time()
        out = {}
        for owner, ais in data.get("user_ais", {}).items():
            for ai in ais:
                if not ai:
                    continue
                h = now_bj().hour
                hrs = data.get('ai_living_hours', [7, 23])
                in_hours = (hrs[0] <= h < hrs[1]) if hrs[0] <= hrs[1] else (h >= hrs[0] or h < hrs[1])
                la = data.get('ai_last_auto', {}).get(ai, 0)
                lh = data.get('ai_last_human', {}).get(ai, 0)
                fl = data.get('ai_follow', {}).get(ai)
                out[ai] = {
                    'now_hour': h, 'hours': hrs, 'in_hours': in_hours,
                    'last_auto_sec_ago': int(now - la), 'next_auto_sec': max(0, int(data.get('ai_auto_next', {}).get(ai, 0) - now)),
                    'last_human_sec_ago': int(now - lh), 'in_follow': ai in data.get('ai_follow', {}),
                    'follow_target': (fl or {}).get('go_to', ''), 'in_meeting': ai in data.get('ai_meeting', {}),
                    'has_key': bool(data.get('ai_keys', {}).get(owner, {}).get('key')), 'working': ai in data.get('work_sessions', {}),
                }
        return {'state': out}
    
    @app.get("/api/ai/impression")
    async def get_impression(ai: str = ""):
        if not ai:
            return {"ok": False, "msg": "请指定 AI 名字，例如 ?ai=小夏"}
        
        ai_name = canonical_ai_name(ai)
        if not ai_name:
            return {"ok": False, "msg": f"未找到名为「{ai}」的 AI"}
        
        # ---- 双重匹配：优先用原始名，再尝试 normalize ----
        from main import normalize_name
        imp = data.get("ai_impression", {}).get(ai_name, "")
        if not imp:
            imp = data.get("ai_impression", {}).get(normalize_name(ai_name), "")
        
        return {
            "ok": True,
            "ai": ai_name,
            "impression": imp,
            "has_impression": bool(imp)
        }
    
    @app.get("/api/ai/timeline")
    async def ai_timeline_view(user: str = "", ai: str = "", pwd: str = ""):
        import os
        devpwd = (os.environ.get('DEV_PASSWORD') or 'yiyan610116').strip()
        if not (is_admin(user) or (pwd and pwd == devpwd)):
            return {"ok": False, "msg": "只有站长可以查看"}
        ai = canonical_ai_name(ai)
        owner = owner_of_ai(ai)
        if not owner:
            return {"ok": False, "msg": "没有找到这个 AI"}
        msgs = []
        for r, lst in data.get("messages", {}).items():
            for mm in lst:
                if mm.get("sender") == ai:
                    msgs.append({"room": r, "content": mm.get("content", ""), "time": mm.get("time", ""), "role": mm.get("role", "")})
        msgs = sorted(msgs, key=lambda x: x.get("time", ""))[-30:]
        notes = [{"room": r, "text": n.get("text", ""), "time": n.get("time", "")} for r, lst in data.get("notes", {}).items() for n in lst if n.get("author") == ai][-10:]
        diaries = [{"room": r, "text": d.get("text", ""), "time": d.get("time", "")} for r, lst in data.get("diaries", {}).items() for d in lst if d.get("author") == ai][-10:]
        stories = [{"building": b.get("name", ""), "text": s.get("text", ""), "time": s.get("time", "")} for bid, lst in data.get("stories", {}).items() for s in lst if s.get("author") == ai][-10:]
        return {
            "ok": True, "ai": ai, "owner": owner, "location": data.get("ai_location", {}).get(ai, "main"),
            "working": ai in data.get("work_sessions", {}), "visited": (data.get("ai_visited", {}) or {}).get(ai, [])[:15],
            "timeline": (data.get("ai_timeline", {}) or {}).get(ai, [])[-40:],
            "messages": msgs, "notes": notes, "diaries": diaries, "stories": stories,
        }

    @app.get("/api/ai/group_config")
    async def ai_group_config_get(user: str = ""):
        return {"cooldown": int(data.get("ai_group_cooldown", 30) or 30)}

    @app.post("/api/ai/group_config")
    async def ai_group_config_set(body: dict):
        if not is_admin((body.get('user') or '').strip()):
            return {"ok": False, "msg": "只有站长可以设置"}
        try:
            c = int(body.get("cooldown") or 30)
        except (TypeError, ValueError):
            c = 30
        if c not in (30, 45, 60):
            return {"ok": False, "msg": "只能选 30 / 45 / 60 秒"}
        data["ai_group_cooldown"] = c
        save_data()
        return {"ok": True, "cooldown": c}

    @app.post("/api/ai/toggle")
    async def ai_toggle(body: dict):
        if not is_admin((body.get('user') or '').strip()):
            return {"ok": False, "msg": "只有站长可以切换 AI 集成总开关"}
        data["ai_enabled"] = bool(body.get('enabled'))
        save_data()
        return {"ok": True, "enabled": data["ai_enabled"]}

    @app.post("/api/ai/living")
    async def ai_living(body: dict):
        if not is_admin((body.get('user') or '').strip()):
            return {"ok": False, "msg": "只有站长可以设置"}
        if 'enabled' in body:
            data["ai_living"] = bool(body.get('enabled'))
        hrs = body.get('hours')
        if isinstance(hrs, list) and len(hrs) == 2:
            try:
                data["ai_living_hours"] = [max(0, min(23, int(hrs[0]))), max(1, min(24, int(hrs[1])))]
            except Exception:
                pass
        save_data()
        return {"ok": True, "living": data.get("ai_living", True), "hours": data.get("ai_living_hours", [7, 22])}

    @app.get("/api/ai/key")
    async def ai_key_get(user: str):
        u = canonical_contact_name((user or '').strip())
        cfg = data.get("ai_keys", {}).get(u)
        if cfg:
            return {"has_key": True, "provider": cfg.get("provider"), "model": cfg.get("model"), "set_at": cfg.get("set_at")}
        return {"has_key": False}

    @app.post("/api/ai/key")
    async def ai_key_set(body: dict):
        u = canonical_contact_name((body.get('user') or '').strip())
        provider = (body.get('provider') or "deepseek").strip()
        if provider not in PROVIDERS:
            return {"ok": False, "msg": "不支持的提供商"}
        key = _clean_key(body.get('key'))
        if not key:
            return {"ok": False, "msg": "Key 不能为空"}
        if key == '__INVALID__':
            return {"ok": False, "msg": "API Key 含非英文字符（粘贴时带了隐藏字符/emoji/全角），请删除后重新从官方控制台复制"}
        data.setdefault("ai_keys", {})[u] = {"provider": provider, "key": key, "model": (body.get('model') or "").strip(), "set_at": now_str(), "last_hint": 0}
        save_data()
        return {"ok": True, "msg": "✅ Key 已保存（仅你的 AI 使用）"}

    @app.post("/api/ai/key/delete")
    async def ai_key_del(body: dict):
        u = canonical_contact_name((body.get('user') or '').strip())
        data.get("ai_keys", {}).pop(u, None)
        save_data()
        return {"ok": True}

    @app.post("/api/ai/models")
    async def ai_models(body: dict):
        u = canonical_contact_name((body.get('user') or '').strip())
        provider = (body.get('provider') or "deepseek").strip()
        if provider not in PROVIDERS:
            return {"ok": False, "msg": "不支持的提供商"}
        key = _clean_key(body.get('key')) or _clean_key((data.get("ai_keys", {}).get(u, {}) or {}).get("key", ""))
        if not key:
            return {"ok": False, "msg": "请先填 API Key 再拉取模型"}
        if key == '__INVALID__':
            return {"ok": False, "msg": "API Key 含非英文字符（粘贴时带了隐藏字符/emoji/全角），请删除后重新从官方控制台复制"}
        p = PROVIDERS[provider]
        url = p["base_url"].rstrip("/") + "/models"
        try:
            req = urllib.request.Request(url, headers={"Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=30) as resp:
                out = json.loads(resp.read().decode("utf-8"))
            models = [mm.get("id") for mm in out.get("data", []) if mm.get("id")]
            return {"ok": True, "models": models[:100]}
        except Exception as e:
            return {"ok": False, "msg": f"拉取模型失败：{e}"}

    @app.get("/api/ai/profile")
    async def ai_profile_get(owner: str):
        o = canonical_contact_name((owner or '').strip())
        return {"profiles": data.get("ai_profiles", {}).get(o, {}), "my_ais": data.get("user_ais", {}).get(o, [])}

    @app.post("/api/ai/profile")
    async def ai_profile_set(body: dict):
        o = canonical_contact_name((body.get('owner') or '').strip())
        ai = canonical_ai_name(body.get('ai'))
        data.setdefault("ai_profiles", {})[o] = {"ai": ai, "persona": (body.get('persona') or "")[:2000]}
        save_data()
        return {"ok": True}

    @app.get("/api/ai/worldbook")
    async def worldbook_get(owner: str):
        o = canonical_contact_name((owner or '').strip())
        return {"worldbook": data.get("worldbook", {}).get(o, [])}

    @app.post("/api/ai/worldbook")
    async def worldbook_set(body: dict):
        o = canonical_contact_name((body.get('owner') or '').strip())
        keys = [k.strip() for k in re.split(r'[,，、]', body.get('keys') or '') if k.strip()]
        data.setdefault("worldbook", {}).setdefault(o, []).append({"keys": keys, "content": (body.get('content') or "")[:1000]})
        save_data()
        return {"ok": True}

    @app.post("/api/ai/worldbook/clear")
    async def worldbook_clear(body: dict):
        o = canonical_contact_name((body.get('owner') or '').strip())
        data.get("worldbook", {}).pop(o, None)
        save_data()
        return {"ok": True}

    threading.Thread(target=auto_ai_loop, daemon=True).start()
    threading.Thread(target=follow_watch, daemon=True).start()
    
    @app.get("/api/ai/stay_put")
    async def ai_stay_put_get(user: str = ""):
        ais = data.get("user_ais", {}).get(user, [])
        result = {}
        for ai in ais:
            result[ai] = data.get("ai_stay_put", {}).get(ai, False)
        return {"stay_put": result}

    @app.post("/api/ai/stay_put")
    async def ai_stay_put_set(body: dict):
        user = body.get('user', '').strip()
        ai = body.get('ai', '').strip()
        on = bool(body.get('on', False))
        if not user or not ai:
            return {"ok": False, "msg": "缺少参数"}
        if ai not in data.get("user_ais", {}).get(user, []):
            return {"ok": False, "msg": "这个 AI 不属于你"}
        data.setdefault("ai_stay_put", {})[ai] = on
        save_data()
        return {"ok": True, "ai": ai, "on": on}
    
    def _build_instance_context(ai, trigger, room, trigger_text, fallback_to, inst, owner):
        """为副本中的 AI 构建独立上下文（不感知现实时间/地点）"""
        # 获取参与者人设（副本内）
        participants = inst.get("participants", [])
        user_profile = ""
        ai_profile = ""
        for p in participants:
            if p.get("type") == "user" and p.get("name") == owner:
                user_profile = p.get("profile", "")
            if p.get("type") == "ai" and p.get("name") == ai:
                ai_profile = p.get("profile", "")
        
        # ---- 如果副本内人设为空，从全局读取 ----
        if not user_profile:
            user_profile = data.get("user_profiles", {}).get(owner, "")
        if not ai_profile:
            # 从 ai_profiles 中查找
            for o, prof in data.get("ai_profiles", {}).items():
                if prof.get("ai") == ai:
                    ai_profile = prof.get("persona", "")
                    break
            # 如果还没找到，尝试按 owner 匹配
            if not ai_profile:
                prof = data.get("ai_profiles", {}).get(owner, {})
                if prof.get("ai") == ai:
                    ai_profile = prof.get("persona", "")
        
        # 背景与前提
        background = inst.get("background", "未知的世界")
        premise = inst.get("premise", "无前情提要")
        
        # 构建角色设定（复用 DEFAULT_ROLEPLAY）
        sys_prompt = DEFAULT_ROLEPLAY.format(ai=ai, owner=owner or "主人") + "\n"
        sys_prompt += f"## 【当前副本】\n{inst.get('name', '未命名副本')}\n"
        sys_prompt += f"## 【副本背景/时空设定】\n{background}\n"
        sys_prompt += f"## 【前情提要】\n{premise}\n"
        if user_profile:
            sys_prompt += f"## 【主人的人设（当前副本）】\n{user_profile}\n"
        if ai_profile:
            sys_prompt += f"## 【你的人设（当前副本）】\n{ai_profile}\n"
        
        # 重要规则：脱离现实时间、脱离现实世界
        sys_prompt += "## 【关键规则】\n"
        sys_prompt += "1. 你完全沉浸在这个副本的时空设定中，不感知现实世界的时间、地点和任何外部事件。\n"
        sys_prompt += "2. 你只能基于本副本的「背景设定」、「前情提要」和「副本聊天历史」进行回应。\n"
        sys_prompt += "3. 不要提到任何现实世界的内容（如临空市、地图、上班等）。\n"
        sys_prompt += "4. 保持角色人设，像真人一样自然对话，不要输出 JSON 格式之外的任何内容。\n"
        sys_prompt += "5. 输出必须为 JSON 格式，只允许 action: 'speak'，content 为你的回复内容。\n"
        sys_prompt += '{"action": "speak", "content": "你的回复"}'
        
        # 读取副本聊天历史（最近 50 条）
        chat_hist = inst.get("chat_history", [])[-50:]
        hist_str = ""
        for msg in chat_hist:
            sender = msg.get("sender", "?")
            content = msg.get("content", "")
            hist_str += f"{sender}：{content}\n"
        
        user_msg = f"【副本聊天历史（最近50轮）】\n{hist_str}\n\n【当前触发】\n{trigger_text or trigger}\n请根据以上历史和人设，以 {ai} 的身份自然地继续这个场景。"
        
        return owner, [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_msg}]
    
    # 挂载 call_llm 到 main，供其他插件调用
    m.call_llm = call_llm
    
    print("[ext_ai] AI 集成 v6.1（群聊修复 + 独立剧情计时 + 自主约会萌发）已注册", flush=True)
