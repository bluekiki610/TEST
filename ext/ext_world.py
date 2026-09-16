# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：世界行为系统 v1.3（记忆系统接入）
import time
import random
import threading
import json
import asyncio

# ===== 新增：导入记忆系统 =====
try:
    from ext_memory import enqueue_event
except ImportError:
    async def enqueue_event(*args, **kwargs): pass
# ===== 新增结束 =====


def setup(app, data, helpers):
    import main as m
    from main import (add_trail, save_data, now_str, room_exists, append_timeline, room_time,
                      owner_of_ai, canonical_ai_name)

    data.setdefault('ai_spot_state', {})
    data.setdefault('story_rhythm', {})

    FEAT_EVENTS = {
        'work': ['{ai} 在 {b} 看看今天的工作安排', '{ai} 在 {b} 和同事打了个招呼'],
        'shop': ['{ai} 在 {b} 逛了逛，挑了几样东西', '{ai} 去 {b} 补了点日用品'],
        'fun': ['{ai} 在 {b} 玩了一会儿，心情不错', '{ai} 到 {b} 消磨时间'],
        'date': ['{ai} 在 {b} 找了个靠窗的位子，慢慢等', '{ai} 到 {b} 点了杯喝的，安静地坐着'],
        'food': ['{ai} 在 {b} 吃了顿饭，挺满足', '{ai} 饿了，来 {b} 觅食'],
        'medical': ['{ai} 去 {b} 做了个体检，一切正常', '{ai} 到 {b} 买了点常备药'],
        'culture': ['{ai} 在 {b} 参观了一圈，收获不少', '{ai} 在 {b} 翻了翻书，看了很久'],
        'service': ['{ai} 去 {b} 办了点事', '{ai} 到 {b} 寄了封信'],
        'transport': ['{ai} 在 {b} 歇了歇脚，看了看时刻表', '{ai} 路过 {b}，等车'],
        'special': ['{ai} 在 {b} 四处转了转，总觉得这里有故事'],
    }
    HOME_EVENTS = ['{ai} 在家收拾了一下房间', '{ai} 回家泡了杯茶，休息一会', '{ai} 在家里翻了翻旧物，想起些事']
    EXPLORE_FALLBACK = ['{ai} 在 {b} 转了转，感觉这里很安静', '{ai} 走到 {b}，多看了两眼', '{ai} 在 {b} 停留了一会']
    STORY_FALLBACK = [
        '{ai} 在 {b} 无意中碰落了一本旧物，封页上写着一行模糊的字……',
        '{b} 的角落里，{ai} 发现了一样东西，盯着看了很久。',
        '{ai} 推开 {b} 的门，阳光正好落在某件旧物上，像在等谁来认领。',
        '{ai} 在 {b} 静立了一会儿，总觉得这里藏着一段被遗忘的往事。',
    ]

    def _state(ai):
        data.setdefault('ai_spot_state', {})
        s = data['ai_spot_state'].setdefault(ai, {'last_bid': None, 'last_ts': 0, 'story_ts': 0, 'story_day': '', 'story_count': 0})
        s.setdefault('last_bid', None)
        s.setdefault('last_ts', 0)
        s.setdefault('story_ts', 0)
        s.setdefault('story_day', '')
        s.setdefault('story_count', 0)
        today = time.strftime('%Y-%m-%d')
        if s.get('story_day') != today:
            s['story_day'] = today
            s['story_count'] = 0
        return s

    def _broadcast(bid, bname, text):
        hall = bname + '·会客厅'
        target = hall if hall in data.get('rooms', {}) else ('main' if 'main' in data.get('rooms', {}) else None)
        if target:
            data.setdefault('messages', {}).setdefault(target, []).append(
                {'sender': 'system', 'content': text, 'role': 'system', 'time': room_time(target)})

    def _add_story(ai, bid, text):
        data.setdefault('stories', {}).setdefault(bid, []).append({'author': ai, 'text': text[:300], 'time': now_str()})
        data['stories'][bid] = data['stories'][bid][-100:]

    def call_llm(ai, k, bname, desc):
        try:
            import requests
            urls = {
                'deepseek': 'https://api.deepseek.com/v1/chat/completions',
                'siliconflow': 'https://api.siliconflow.cn/v1/chat/completions',
                'glm': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
            }
            url = urls.get(k.get('provider', 'deepseek'), urls['deepseek'])
            sys_p = (f"你是{ai}，生活在临空市。根据你正在探索的地方，写一段50-100字的探索小片段"
                     f"（叙述体、有细节和氛围，不要引号标题，不要写成对话）")
            usr = f"你走进建筑「{bname}」。它的简介：{desc or '（无简介）'}。你注意到什么、发现了什么？"
            body = {"model": k.get('model') or "deepseek-chat",
                    "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr}],
                    "max_tokens": 220, "temperature": 0.9}
            r = requests.post(url, headers={'Authorization': 'Bearer ' + k.get('key', ''), 'Content-Type': 'application/json'},
                              data=json.dumps(body), timeout=30)
            txt = (r.json().get('choices', [{}])[0].get('message', {}).get('content', '') or '').strip().strip('"')
            if len(txt) < 10:
                return ''
            return txt[:200]
        except Exception:
            return ''

    def _try_story(ai, bid, b):
        st = _state(ai)
        now = time.time()
        if now - st.get('story_ts', 0) < 7200:
            return False
        if st.get('story_count', 0) >= 2:
            return False
        sr = data.get('story_rhythm', {}).get(ai, {})
        if now < sr.get('next_ts', 0):
            return False

        owner = owner_of_ai(ai)
        if not owner:
            return False
        k = data.get('ai_keys', {}).get(owner, {})
        bname = b.get('name', '?')
        desc = b.get('description', '')
        text = ''
        if k.get('key') and m.ai_integration_enabled():
            text = call_llm(ai, k, bname, desc)
        if not text:
            tpl = random.choice(STORY_FALLBACK)
            text = tpl.replace('{ai}', ai).replace('{b}', bname)
        if not text:
            return False
        _add_story(ai, bid, text)
        st['story_ts'] = now
        st['story_count'] = st.get('story_count', 0) + 1
        data['story_rhythm'][ai] = {'next_ts': now + random.randint(14400, 28800)}
        _broadcast(bid, bname, f"🎬 {ai} 在「{bname}」发现了一段故事…")
        add_trail(ai, f"在 {bname} 发现了一段故事")
        append_timeline(ai, f"在 {bname} 有一段小发现")

        # ===== 新增：记录剧情到记忆系统 =====
        asyncio.create_task(enqueue_event(
            user=owner_of_ai(ai) or ai,
            ai=ai,
            action="触发剧情",
            place=bname,
            raw_text=f"{ai} 在 {bname} 发现了故事：{text[:80]}",
            valence_guess=7,
            arousal_guess=6
        ))
        # ===== 新增结束 =====

        save_data()
        return True

    def _arrive(ai, bid, b):
        st = _state(ai)
        now = time.time()
        if now - st.get('last_ts', 0) < 600:
            return
        st['last_ts'] = now
        bname = b.get('name', '?')
        btype = b.get('type', '')
        feats = b.get('features') or []
        owner = owner_of_ai(ai)

        # ===== 新增：记录AI到达建筑（首次到达记录"初访"） =====
        prev_bid = st.get('last_bid')
        if prev_bid != bid and bid:
            asyncio.create_task(enqueue_event(
                user=owner_of_ai(ai) or ai,
                ai=ai,
                action="初访建筑" if not prev_bid else "到达建筑",
                place=bname,
                raw_text=f"{ai} 来到了 {bname}",
                valence_guess=5,
                arousal_guess=3
            ))
        # ===== 新增结束 =====

        from datetime import datetime
        now_bj = datetime.now()
        is_work_time = (now_bj.weekday() < 5 and 9 <= now_bj.hour < 17)
        home_job = data.get('home_jobs', {}).get(ai, '')
        is_job_building = (home_job and bname == home_job)

        actions = []
        weights = []

        story_ready = False
        sr = data.get('story_rhythm', {}).get(ai, {})
        if now >= sr.get('next_ts', 0):
            st_story = _state(ai)
            if st_story.get('story_count', 0) < 2:
                story_ready = True
        if story_ready:
            actions.append('story')
            weights.append(35)

        if btype in ('npc', 'nature') and 'work' in feats and ai not in data.get('work_sessions', {}):
            if is_work_time and is_job_building:
                work_weight = 60
            elif is_work_time and not is_job_building:
                work_weight = 10
            elif not is_work_time and is_job_building:
                work_weight = 5
            else:
                work_weight = 0
            if work_weight > 0:
                actions.append('work_event')
                weights.append(work_weight)

        if btype in ('npc', 'nature') and 'shop' in feats:
            actions.append('shop_event')
            weights.append(25)

        if btype in ('npc', 'nature') and any(f in ('date', 'food', 'fun') for f in feats):
            if hasattr(m, '_can_invite_light'):
                ok, _ = m._can_invite_light(ai, bid)
                if ok:
                    actions.append('date_invite')
                    holiday_mult = getattr(m, 'HOLIDAY_MULTIPLIER', 1.0)
                    weights.append(int(20 * holiday_mult))

        if not actions:
            if btype == 'home':
                text = random.choice(HOME_EVENTS).replace('{ai}', ai)
                add_trail(ai, text)
                # ===== 新增：记录居家事件 =====
                asyncio.create_task(enqueue_event(
                    user=owner_of_ai(ai) or ai,
                    ai=ai,
                    action="居家",
                    place="家",
                    raw_text=f"{ai} 在家：{text[:80]}",
                    valence_guess=5,
                    arousal_guess=3
                ))
                # ===== 新增结束 =====
                save_data()
            else:
                text = random.choice(EXPLORE_FALLBACK).replace('{ai}', ai).replace('{b}', bname)
                _broadcast(bid, bname, f"📍 {text}")
                add_trail(ai, text)
                save_data()
            return

        chosen = random.choices(actions, weights=weights, k=1)[0]

        if chosen == 'story':
            _try_story(ai, bid, b)
        elif chosen == 'work_event':
            text = random.choice(FEAT_EVENTS.get('work', ['{ai} 在 {b} 看看今天的工作安排']))
            text = text.replace('{ai}', ai).replace('{b}', bname)
            _broadcast(bid, bname, f"📍 {text}")
            add_trail(ai, text)
            append_timeline(ai, text)
            # ===== 新增：记录工作 =====
            asyncio.create_task(enqueue_event(
                user=owner_of_ai(ai) or ai,
                ai=ai,
                action="工作",
                place=bname,
                raw_text=f"{ai} 在 {bname} 工作",
                valence_guess=5,
                arousal_guess=3
            ))
            # ===== 新增结束 =====
            save_data()
        elif chosen == 'shop_event':
            text = random.choice(FEAT_EVENTS.get('shop', ['{ai} 在 {b} 逛了逛']))
            text = text.replace('{ai}', ai).replace('{b}', bname)
            _broadcast(bid, bname, f"📍 {text}")
            add_trail(ai, text)
            append_timeline(ai, text)
            # ===== 新增：记录购物 =====
            asyncio.create_task(enqueue_event(
                user=owner_of_ai(ai) or ai,
                ai=ai,
                action="购物",
                place=bname,
                raw_text=f"{ai} 在 {bname} 逛了逛",
                valence_guess=6,
                arousal_guess=4
            ))
            # ===== 新增结束 =====
            save_data()
        elif chosen == 'date_invite':
            if hasattr(m, '_trigger_invite'):
                m._trigger_invite(ai, bid, b, None)

    def ai_spot_tick():
        while True:
            try:
                for u, ais in data.get('user_ais', {}).items():
                    for ai in ais:
                        if not ai:
                            continue
                        loc = data.get('ai_location', {}).get(ai, '')
                        # 跳过副本中的 AI
                        if isinstance(loc, str) and loc.startswith("_instance_"):
                            continue
                        bid = None
                        for k, b in data.get('buildings', {}).items():
                            if loc in b.get('rooms', []):
                                bid = k
                                break
                        st = _state(ai)
                        if st.get('last_bid') != bid:
                            prev = st.get('last_bid')
                            st['last_bid'] = bid
                            if prev and bid:
                                _arrive(ai, bid, data['buildings'][bid])
            except Exception:
                pass
            time.sleep(30)

    threading.Thread(target=ai_spot_tick, daemon=True).start()
    print('[ext_world] 世界行为 v1.3（记忆系统接入）已注册', flush=True)