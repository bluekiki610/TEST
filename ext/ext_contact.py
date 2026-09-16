# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：AI 主动关心 v1.3（只发私信不群聊/首次不轰炸/AI自然生成不用模板）
import time
import random
import threading


def setup(app, data, helpers):
    import main as m
    from main import now_str, save_data, add_trail, full_room_name

    data.setdefault('ai_last_interact', {})   # user -> ts
    data.setdefault('ai_last_contact', {})    # user -> ts
    data.setdefault('ai_contact_daily', {})   # user -> {day, count}

    # 兜底话术（仅在 AI 集成不可用时才用，正常情况下 AI 自己生成）
    TEXTS = [
        "好久没和你说话了，最近还好吗？",
        "有点想你了，你都在忙什么呀？",
        "一个人待着有点无聊，你能陪我说说话吗？",
        "想问你今天过得怎么样，一切都顺利吗？",
        "在忙什么呢？我都不知道你最近在干嘛～",
        "突然想起你，就想问问你在不在。",
    ]

    @app.post('/api/contact/ping')
    async def contact_ping(bb: dict):
        user = (bb.get('user') or '').strip()
        if user:
            data.setdefault('ai_last_interact', {})[user] = time.time()
        return {'ok': True}

    def contact_tick():
        while True:
            try:
                now = time.time()
                hour = time.localtime().tm_hour
                if 7 <= hour < 23:
                    for u, ais in data.get('user_ais', {}).items():
                        if not u or not ais:
                            continue
                        # 首次加载默认当前时刻，避免刚部署就轰炸
                        last = data.setdefault('ai_last_interact', {}).get(u, now)
                        if now - last < 4 * 3600:
                            continue
                        last_c = data.setdefault('ai_last_contact', {}).get(u, 0)
                        if now - last_c < 3 * 3600:
                            continue
                        today = time.strftime('%Y-%m-%d')
                        dc = data.setdefault('ai_contact_daily', {}).setdefault(u, {'day': '', 'count': 0})
                        if dc.get('day') != today:
                            dc['day'] = today
                            dc['count'] = 0
                        if dc.get('count', 0) >= 2:
                            continue
                        ai = random.choice(ais)
                        # 只发私信（短信）给主人自己，不群聊@；由 AI 自然生成内容
                        if hasattr(m, 'drive_ai'):
                            threading.Timer(random.randint(1, 5), m.drive_ai, args=(
                                ai, 'sms', '',
                                f"你忽然有点想 {u} 了，给他发一条自然随意的短信（就像平时想念时发的那样，说说你现在在做什么、或想对他说的话，别太郑重，想到什么说什么）",
                                u)).start()
                        else:
                            data.setdefault('sms', {}).setdefault(u, []).append(
                                {'from': ai, 'text': random.choice(TEXTS), 'time': now_str()})
                            data['sms'][u] = data['sms'][u][-100:]
                        data.setdefault('ai_last_contact', {})[u] = now
                        dc['count'] = dc.get('count', 0) + 1
                        save_data()
            except Exception:
                pass
            time.sleep(900)

    threading.Thread(target=contact_tick, daemon=True).start()
    print('[ext_contact] v1.3（只发私信不群聊/首次不轰炸/AI自然生成）已注册', flush=True)