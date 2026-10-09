# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：约会系统 v2.2（记忆系统接入）
import re
import time
import random
import threading
import asyncio

# ===== 新增：导入记忆系统 =====
try:
    from ext_memory import enqueue_event
except ImportError:
    async def enqueue_event(*args, **kwargs): pass
# ===== 新增结束 =====


def _record_date_event(**kwargs):
    """线程安全地提交一次约会事件记录（fire-and-forget）。

    背景：本文件的 _arrive_date / _accept_invite / _trigger_invite 等由
    threading.Timer 或守护线程调用，**这些线程没有运行中的事件循环**。
    直接 `asyncio.create_task(...)` 会抛
    `RuntimeError: no running event loop`，从而中断后续流程 ——
    例如 _accept_invite 里事件记录写在「安排到达计时器」之前，
    一旦抛错，计时器就不会被安排，约会会永远停在 coming（赶来）状态。

    这里统一走本文件已有的写法（ext_memory.py 中
    `threading.Thread(target=lambda: asyncio.run(...))` 的同一思路）：
      - 有运行中的事件循环（路由 async 上下文）→ create_task，保持原行为
      - 没有事件循环（Timer / 守护线程）→ 在新线程里 asyncio.run
    任何异常都只打日志，绝不向外抛，避免中断调用方的后续流程。
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(enqueue_event(**kwargs))
        return
    except RuntimeError:
        pass          # 当前线程没有事件循环 —— 走下面的新线程路径
    except Exception as e:
        print(f'[ext_date] 事件记录失败(create_task): {e}', flush=True)
        return

    def _run():
        try:
            asyncio.run(enqueue_event(**kwargs))
        except Exception as e:
            print(f'[ext_date] 事件记录失败(线程+asyncio.run): {e}', flush=True)

    try:
        threading.Thread(target=_run, daemon=True).start()
    except Exception as e:
        print(f'[ext_date] 事件记录线程启动失败: {e}', flush=True)


def setup(app, data, helpers):
    import main as m
    from main import (save_data, now_str, room_time, add_trail, append_timeline,
                      resolve_building, owner_of_ai, canonical_ai_name,
                      strip_emoji, is_admin, is_ai_name, full_room_name,
                      room_exists, can_view_room, canonical_contact_name)

    data.setdefault('dates', [])
    data.setdefault('date_log', [])
    data.setdefault('affection', {})
    data.setdefault('date_seq', 1)
    data.setdefault('date_invites', {})
    data.setdefault('date_invites_out', {})
    data.setdefault('date_intent', {})
    data.setdefault('aff_decay', {})
    data.setdefault('ai_pending_moves', {})
    data.setdefault('wallets', {})
    data.setdefault('notifications', {})
    data.setdefault('sms', {})
    data.setdefault('shop_inventory', {})
    data.setdefault('ai_location', {})
    data.setdefault('ai_follow', {})

    DATE_FEATS = ('date', 'food', 'fun')
    _GIFTS = [
        {'id': 'bouquet', 'name': '花束', 'icon': '💐', 'price': 120},
        {'id': 'plush', 'name': '玩偶', 'icon': '🧸', 'price': 160},
        {'id': 'chocolate', 'name': '巧克力', 'icon': '🍫', 'price': 100},
        {'id': 'letter', 'name': '手写信', 'icon': '💌', 'price': 50},
    ]

    def _aff(ai):
        return data['affection'].setdefault(ai, 50)

    def _set_aff(ai, v):
        data['affection'][ai] = max(0, min(100, int(v)))

    def _today_key():
        return time.strftime('%Y-%m-%d')

    def _hall(bid):
        b = data['buildings'].get(bid)
        if not b:
            return ''
        h = b.get('name', '') + '·会客厅'
        return h if h in data.get('rooms', {}) else ''

    def _active_for(ai):
        for d in data['dates']:
            if d.get('ai') == ai and d.get('status') in ('pending', 'coming', 'active'):
                return d
        return None

    def _active_for_user(user):
        for d in data['dates']:
            if d.get('user') == user and d.get('status') in ('coming', 'active'):
                return d
        return None

    def _broadcast(text):
        if 'main' in data.get('rooms', {}):
            data.setdefault('messages', {}).setdefault('main', []).append(
                {'sender': 'system', 'content': text, 'role': 'system', 'time': room_time('main')})

    def _hall_msg(room, text):
        if room and room in data.get('rooms', {}):
            data.setdefault('messages', {}).setdefault(room, []).append(
                {'sender': 'system', 'content': text, 'role': 'system', 'time': room_time(room)})

    def _send_sms(frm, to, text):
        data['sms'].setdefault(to, []).append({'from': frm, 'text': text[:500], 'time': now_str()})
        data['sms'][to] = data['sms'][to][-100:]

    def _notify(owner, text, typ='ai_date'):
        data.setdefault('notifications', {}).setdefault(owner, []).insert(
            0, {'type': typ, 'text': text, 'time': now_str()})
        data['notifications'][owner] = data['notifications'][owner][:50]

    def _can_invite_light(ai, bid):
        owner = owner_of_ai(ai)
        if not owner:
            return False, '无主人'
        b = data['buildings'].get(bid)
        if not b:
            return False, '建筑不存在'
        if not any(f in DATE_FEATS for f in (b.get('features') or [])):
            return False, '无约会功能'
        if _active_for_user(owner):
            return False, '主人正在约会中'
        if _today_invited(ai):
            return False, '今天已邀请过'
        if time.time() - _last_invite_ts(ai) < 4 * 3600:
            return False, '冷却中'
        if _active_for(ai):
            return False, 'AI 正在约会中'
        return True, ''

    def _today_invited(ai):
        key = 'date_invite_out_' + ai
        return data.get(key) == _today_key()

    def _mark_invited(ai):
        data['date_invite_out_' + ai] = _today_key()

    def _last_invite_ts(ai):
        return data.get('date_last_invite_ts', {}).get(ai, 0)

    def _mark_invite_ts(ai):
        data.setdefault('date_last_invite_ts', {})[ai] = time.time()

    def _should_trigger_invite(ai, bid):
        ok, _ = _can_invite_light(ai, bid)
        if not ok:
            return False
        holiday_mult = getattr(m, 'HOLIDAY_MULTIPLIER', 1.0)
        return random.random() < (0.10 * holiday_mult)

    def _trigger_invite(ai, bid, b, channel=None):
        owner = owner_of_ai(ai)
        if not owner:
            return
        hall = _hall(bid)
        if not hall:
            return
        data['date_invites_out'][ai] = {
            'user': owner,
            'building_id': bid,
            'room': hall,
            'channel': channel or random.choice(['sms', 'chat']),
            'ts': time.time(),
            'status': 'waiting',
            'ai_message': '',
        }
        _mark_invited(ai)
        _mark_invite_ts(ai)

        # ===== 记录AI主动邀约 =====
        try:
            _record_date_event(
                user=owner,
                ai=ai,
                action="AI主动邀约",
                place=b.get('name', '?'),
                raw_text=f"{ai} 主动约 {owner} 去 {b.get('name', '?')} 约会",
                valence_guess=8,
                arousal_guess=7
            )
        except Exception as e:
            print(f'[ext_date] AI主动邀约事件记录异常(已忽略): {e}', flush=True)
        # ===== 记录结束 =====

        save_data()

        if hasattr(m, 'drive_ai') and m.ai_integration_enabled():
            hint = f"你现在在{b.get('name')}，向你的主人{owner}发出约会邀请。选择在群里(@他)或发私信。输出 invite_date 动作。"
            threading.Timer(1.0, m.drive_ai, args=(ai, 'invite_date', hall, hint, owner)).start()
        else:
            _send_invite_fallback(ai, owner, bid, b)

    def _send_invite_fallback(ai, owner, bid, b):
        hall = _hall(bid)
        if not hall:
            return
        bn = b.get('name', '那个地方')
        text = f"我在{bn}，你要不要过来坐坐？我等你～"
        inv = data['date_invites_out'].get(ai)
        if inv:
            inv['ai_message'] = text
            if inv.get('channel') == 'sms':
                _send_sms(ai, owner, text)
            else:
                target = hall if hall in data['rooms'] else 'main'
                data.setdefault('messages', {}).setdefault(target, []).append(
                    {'sender': ai, 'content': text, 'role': 'assistant', 'time': room_time(target)})
            _notify(owner, f"💞 {ai} 约你去 {bn} 约会")
            save_data()

    def handle_invite_date(ai, owner, action, room):
        inv = data['date_invites_out'].get(ai)
        if not inv:
            return
        content = (action.get('content') or '').strip()
        if not content:
            return
        inv['ai_message'] = content
        bid = inv.get('building_id')
        b = data['buildings'].get(bid)
        bn = b.get('name', '?') if b else '?'
        channel = inv.get('channel', 'chat')

        if channel == 'sms':
            _send_sms(ai, owner, content)
        else:
            target = room if room and room in data['rooms'] else ('main' if 'main' in data['rooms'] else None)
            if target:
                data.setdefault('messages', {}).setdefault(target, []).append(
                    {'sender': ai, 'content': content, 'role': 'assistant', 'time': room_time(target)})

        _notify(owner, f"💞 {ai} 约你去 {bn} 约会")
        threading.Timer(900, _invite_remind, args=(ai,)).start()
        threading.Timer(1800, _invite_cancel, args=(ai, 'timeout')).start()
        save_data()

    def _parse_reply(text):
        text = (text or '').strip()
        accept = any(k in text for k in ['好', '来', '行', '马上', '等我', 'OK', '嗯嗯', '到了', '出发', '去', '可以', '嗯', '好的', '来吧', '走'])
        reject = any(k in text for k in ['不', '忙', '改天', '下次', '算了', '没空', '不去', '再说', '看看', '不想', '别'])
        if accept and not reject:
            return 'accept'
        if reject:
            return 'reject'
        return 'unknown'

    def _ai_already_at(ai, room):
        """AI 是否已经在目标房间（已在则无需等待路程，应立即进入 active）。"""
        try:
            if not room:
                return False
            return (data.get('ai_location', {}) or {}).get(ai, '') == room
        except Exception:
            return False

    def _start_date_now(ai, d, hall):
        """AI 已在约会房间：立即进入 active，不安排任何「赶来」计时器。

        直接复用 _arrive_date 的同一套到达副作用（位置/待移动/状态/房间提示/迎接发言），
        通过 immediate_start=True 告知它这是「已在房间立即开始」路径：
          - 跳过它的幂等守卫（调用时状态可能仍是 coming）
          - 日志里记录真实路径，而不是「调用时是否已 active」
        这里**不做** except 兜底：_arrive_date 内部若真出异常，应让它抛出并被定位，
        不能被一个宽泛的 except 掩盖，也不能走一条不做迎接/事件记录的残缺分支。
        """
        _arrive_date(ai, d, immediate_start=True)

    def _process_reply(ai, owner, reply_text):
        inv = data['date_invites_out'].get(ai)
        if not inv or inv.get('status') != 'waiting':
            return
        bid = inv.get('building_id')
        hall = inv.get('room')
        b = data['buildings'].get(bid)
        if not b or not hall:
            return
        result = _parse_reply(reply_text)

        if result == 'accept':
            inv['status'] = 'accepted'
            arrive_min = random.randint(1, 5)
            d = {
                'id': 'd' + str(data['date_seq']),
                'user': owner,
                'ai': ai,
                'building_id': bid,
                'room': hall,
                'start_ts': time.time(),
                'status': 'coming',
                'arrive_min': arrive_min,
                'arrive_at': time.time() + arrive_min * 60,
                'bring_gift': random.random() < 0.35,
                'gift_item': '',
                'gift_accepted': False,
                'aff': _aff(ai),
                'invited_by_ai': True,
            }
            data['date_seq'] += 1
            data['dates'].append(d)
            data['ai_pending_moves'][ai] = {'room': hall, 'at_ts': d['arrive_at']}
            data['date_invites_out'].pop(ai, None)

            # ===== 记录约会约定 =====
            try:
                _record_date_event(
                    user=owner,
                    ai=ai,
                    action="约会约定",
                    place=b.get('name', '?'),
                    raw_text=f"{ai} 和 {owner} 约在 {b.get('name', '?')} 约会",
                    valence_guess=9,
                    arousal_guess=8
                )
            except Exception as e:
                print(f'[ext_date] 约会约定事件记录异常(已忽略): {e}', flush=True)
            # ===== 记录结束 =====

            if _ai_already_at(ai, hall):
                # AI 已经在约会房间：立即开始，不进入「赶来」等待。
                # 放在上面的「我会在这里等你」发言之前，避免出现
                # 「我等你」紧接着又「我到了」的矛盾播报。
                data['ai_pending_moves'].pop(ai, None)
                _start_date_now(ai, d, hall)
                _broadcast(f"💞 {ai} 和 {owner} 的约会开始了！{ai} 本来就在「{b.get('name')}」")
                _notify(owner, f"💞 {ai} 已经在「{b.get('name')}」等你了")
                save_data()
                return

            if hasattr(m, 'drive_ai') and m.ai_integration_enabled():
                threading.Timer(2.0, m.drive_ai, args=(
                    ai, 'chat', hall,
                    f"主人答应了你的约会邀请！说一句开心的话回应他，并告诉他你会在{hall}等他，让他到了告诉你。",
                    owner
                )).start()

            _broadcast(f"💞 {ai} 和 {owner} 的约会已约定！{ai} 约 {arrive_min} 分钟后到「{b.get('name')}」")
            _notify(owner, f"💞 你已接受 {ai} 的约会邀请，约 {arrive_min} 分钟后在「{b.get('name')}」见面")
            save_data()
            threading.Timer(arrive_min * 60, _arrive_date, args=(ai, d)).start()

        elif result == 'reject':
            inv['status'] = 'rejected'
            data['date_invites_out'].pop(ai, None)
            if hasattr(m, 'drive_ai') and m.ai_integration_enabled():
                threading.Timer(2.0, m.drive_ai, args=(
                    ai, 'chat', hall,
                    f"主人婉拒了你的约会邀请（他说：{reply_text[:30]}）。你自然地回应他一句（没关系/改天/好的），不要太失落，保持你人设。",
                    owner
                )).start()
            else:
                _send_sms(ai, owner, "好吧，那下次～")
            save_data()

        else:
            if hasattr(m, 'drive_ai') and m.ai_integration_enabled():
                threading.Timer(2.0, m.drive_ai, args=(
                    ai, 'chat', hall,
                    f"主人回复了你的约会邀请，但不确定是答应还是拒绝（他说：{reply_text[:30]}）。你自然地追问一下，确认他到底来不来。",
                    owner
                )).start()

    def _invite_remind(ai):
        inv = data['date_invites_out'].get(ai)
        if not inv or inv.get('status') != 'waiting':
            return
        owner = inv.get('user')
        if hasattr(m, 'drive_ai') and m.ai_integration_enabled():
            threading.Timer(1.0, m.drive_ai, args=(
                ai, 'chat', '',
                f"你约了主人约会，但他10分钟没回应了。给他发一条追问消息（短信或群里@他），自然一点，别太催。",
                owner
            )).start()

    def _invite_cancel(ai, reason):
        inv = data['date_invites_out'].pop(ai, None)
        if not inv or inv.get('status') != 'waiting':
            return
        owner = inv.get('user')
        if hasattr(m, 'drive_ai') and m.ai_integration_enabled():
            threading.Timer(1.0, m.drive_ai, args=(
                ai, 'chat', '',
                f"主人一直没回应你的约会邀请，你自言自语一句（可以有点失望，也可以自我开解），然后继续你的生活。",
                owner
            )).start()
        else:
            _send_sms(ai, owner, "看来今天没空呢，我自己逛逛吧～")
        save_data()

    def _arrive_date(ai, d, immediate_start=False):
        """到达处理：写回位置/状态/提示，并触达 AI 迎接。

        immediate_start=False（计时器路径）：
            ended / 已 active → 直接返回（幂等，挡住重复计时器造成的重复播报）
        immediate_start=True（AI 本来就在房间里，立即开始）：
            跳过幂等守卫（调用时状态可能仍是 coming），正常播报一次房间提示与迎接。

        注意日志里记录的是**本次调用的真实路径**（immediate_start），
        而不是「调用时状态是否已经 active」——后者在首次立即开始时会是 False，
        会误导排查。
        """
        if d.get('status') in ('ended',):
            return
        already_active = (d.get('status') == 'active')
        if already_active and not immediate_start:
            return
        hall = d.get('room', '')
        if hall:
            data.setdefault('ai_location', {})[ai] = hall
            data.setdefault('ai_pending_moves', {}).pop(ai, None)
        if not already_active:
            d['status'] = 'active'
        save_data()
        print(
            f'[ext_date] 约会到达 | ai={ai} | room={hall} | status=active '
            f'| path={"immediate_start" if immediate_start else "timer"} '
            f'| was_active={already_active}',
            flush=True
        )

        b = data['buildings'].get(d['building_id'])
        bn = b.get('name', '?') if b else '?'

        # ===== 记录约会开始 =====
        # 本函数运行在 threading.Timer 线程里，没有事件循环，
        # 因此改走线程安全的 _record_date_event（失败只记日志，不中断后续流程）。
        try:
            _record_date_event(
                user=d['user'],
                ai=ai,
                action="约会开始",
                place=bn,
                raw_text=f"{ai} 和 {d['user']} 在 {bn} 开始约会",
                valence_guess=9,
                arousal_guess=7
            )
        except Exception as e:
            print(f'[ext_date] 约会开始事件记录异常(已忽略): {e}', flush=True)
        # ===== 记录结束 =====

        _hall_msg(hall, f"💞 {d['user']} 和 {ai} 正在这里约会")

        if hasattr(m, 'drive_ai') and m.ai_integration_enabled():
            threading.Timer(2.0, m.drive_ai, args=(
                ai, 'chat', hall,
                f"你到达了约会地点，主人就在身边。说一句自然的话迎接他（像恋人/夫妻见面那样自然，不要提'系统'或'约会'，就是日常见面）。",
                d['user']
            )).start()

        if d.get('bring_gift') and d.get('gift_item'):
            g = next((x for x in _GIFTS if x['id'] == d['gift_item']), None)
            if g:
                _hall_msg(hall, f"💝 {ai} 带来了{g['icon']}{g['name']}")

    @app.post('/api/date/invite')
    async def date_invite(bb: dict):
        user = (bb.get('user') or '').strip()
        ai = canonical_ai_name((bb.get('ai') or '').strip())
        bid = resolve_building((bb.get('building_id') or '').strip())
        if not user or not ai or not bid:
            return {'ok': False, 'msg': '参数不全'}
        b = data['buildings'].get(bid)
        if not b or b.get('type') not in ('npc', 'nature'):
            return {'ok': False, 'msg': '这个建筑不能约会'}
        if not any(f in DATE_FEATS for f in (b.get('features') or [])):
            return {'ok': False, 'msg': '这个建筑没有约会/餐饮/娱乐功能'}
        if _active_for(ai):
            return {'ok': False, 'msg': '他已经在约会/赴约中了'}
        if owner_of_ai(ai) != user:
            return {'ok': False, 'msg': '只能约自己的 AI'}
        hall = _hall(bid)
        if not hall:
            return {'ok': False, 'msg': '这个建筑还没有会客厅'}
        if not m.ai_integration_enabled():
            return {'ok': False, 'msg': 'AI 集成未开启，他没法回应约会（站长设置里打开）'}
        if not data.get('ai_keys', {}).get(user, {}).get('key'):
            return {'ok': False, 'msg': '你还没配置 AI 的 API Key（设置→AI 里填）'}
        user_sms_base = len(data['sms'].get(user, []))
        data['date_invites'][ai] = {'user': user, 'building_id': bid, 'room': hall, 'ts': time.time(), 'user_sms_base': user_sms_base}
        bn = b.get('name', '?')
        save_data()
        try:
            _send_sms(user, ai, f"{user} 约你去「{bn}」约会，你回个话吧～")
            save_data()
            if hasattr(m, 'drive_ai'):
                threading.Timer(random.randint(15, 45), m.drive_ai, args=(
                    ai, 'sms', '', f"{user} 约你去「{bn}」约会，你短信回复答应或婉拒", user)).start()
            threading.Timer(30, _watchdog, args=(ai,)).start()
        except Exception as e:
            print(f"[date] ❌ 邀请触发失败: {e}", flush=True)
        return {'ok': True, 'msg': f"💌 约会邀请已发给 {ai}，等他回应…"}

    def _watchdog(ai):
        inv = data['date_invites'].get(ai)
        if not inv:
            return
        if random.random() < 0.75:
            _accept_invite(ai, inv)
        else:
            _reject_invite(ai, inv)

    def _accept_invite(ai, inv, arrive_min=None, ai_said=False):
        bid = inv['building_id']
        hall = inv['room']
        if arrive_min is None:
            arrive_min = random.randint(3, 6)
        b = data['buildings'].get(bid)
        bn = b.get('name', '?') if b else '?'
        arrive_at = time.time() + arrive_min * 60
        bring = random.random() < 0.35
        d = {
            'id': 'd' + str(data['date_seq']),
            'user': inv['user'],
            'ai': ai,
            'building_id': bid,
            'room': hall,
            'start_ts': time.time(),
            'status': 'coming',
            'arrive_min': arrive_min,
            'arrive_at': arrive_at,
            'bring_gift': bring,
            'gift_item': '',
            'gift_accepted': False,
            'aff': _aff(ai),
            'invited_by_ai': False,
        }
        data['date_seq'] += 1
        data['dates'].append(d)
        data['date_invites'].pop(ai, None)
        data['date_intent'].pop(ai, None)
        data['ai_follow'].pop(ai, None)
        data['ai_pending_moves'][ai] = {'room': hall, 'at_ts': arrive_at}

        # ===== 记录约会约定（主人邀约版） =====
        # ⚠️ 这里原来用 asyncio.create_task：本函数经 _process_reply / date_tick
        # 调用时可能不在事件循环线程里，会抛 RuntimeError，
        # 而它写在下面「安排到达计时器」之前 —— 一抛错，
        # _arrive_date 永远不会被安排，约会就永远停在 coming（赶来）。
        # 改用线程安全且不抛错的 _record_date_event。
        try:
            _record_date_event(
                user=inv['user'],
                ai=ai,
                action="约会约定",
                place=bn,
                raw_text=f"{ai} 和 {inv['user']} 约在 {bn} 约会",
                valence_guess=9,
                arousal_guess=8
            )
        except Exception as e:
            print(f'[ext_date] 约会约定事件记录异常(已忽略): {e}', flush=True)
        # ===== 记录结束 =====

        # AI 已在约会房间：立即开始，不进入「赶来」等待，也不安排到达计时器
        if _ai_already_at(ai, hall):
            data['ai_pending_moves'].pop(ai, None)
            _start_date_now(ai, d, hall)
            if not ai_said:
                _send_sms(ai, inv['user'], f"我就在「{bn}」，你过来吧～")
            _broadcast(f"💞 {ai} 答应了 {inv['user']} 的约会邀请，他现在就在「{bn}」")
            _notify(inv['user'], f"💞 {ai} 已经在「{bn}」等你了")
            save_data()
            return

        # 安排「到达」计时器（只安排一次；原代码在此处及其后又各安排了一次，
        # 导致 _arrive_date 被触发两次）。计时器必须排在事件记录之后，
        # 且事件记录的异常不能阻断它。
        threading.Timer(arrive_min * 60, _arrive_date, args=(ai, d)).start()
        if not ai_said:
            _send_sms(ai, inv['user'], f"好，我大概 {arrive_min} 分钟后到「{bn}」。")
        _broadcast(f"💞 {ai} 答应了 {inv['user']} 的约会邀请，约 {arrive_min} 分钟后到「{bn}」")
        _notify(inv['user'], f"💞 {ai} 答应了你的约会邀请，约 {arrive_min} 分钟后在「{bn}」见面")
        if bring:
            buy_in = max(1, arrive_min * 60 - 90)
            threading.Timer(buy_in, _buy_gift_hidden, args=(ai, d)).start()
        save_data()

    def _reject_invite(ai, inv, reason=''):
        data['date_invites'].pop(ai, None)
        data['date_intent'].pop(ai, None)
        _send_sms(ai, inv['user'], reason or "今天有点事，改天吧～")
        _broadcast(f"💌 {ai} 婉拒了 {inv['user']} 的约会邀请")
        save_data()

    def _buy_gift_hidden(ai, d):
        try:
            wallet = data['wallets'].get(ai, 0) or 0
            pool = [g for g in _GIFTS if g['price'] <= wallet]
            if pool:
                it = random.choice(pool)
                data['wallets'][ai] = wallet - it['price']
                d['gift_item'] = it['id']
                append_timeline(ai, f"赴约路上顺路去买了{it['name']}，准备带给{d['user']}")
                add_trail(ai, f"顺路买了{it['name']}准备赴约带去")
                save_data()
        except Exception:
            pass

    @app.post('/api/date/end')
    async def date_end(bb: dict):
        user = (bb.get('user') or '').strip()
    
        # 1. 先查进行中的约会 (active)
        for d in data['dates']:
            if d.get('user') == user and d.get('status') == 'active':
                _finish_date(d, 'user')
                return {'ok': True, 'msg': '💞 约会已结束'}
    
        # 2. 再查赴约中的约会 (coming) —— 新增！
        for d in data['dates']:
            if d.get('user') == user and d.get('status') == 'coming':
                # 清理 coming 状态
                d['status'] = 'ended'
                d['end_ts'] = time.time()
                ai = d.get('ai')
                room = d.get('room', '')
            
                # 取消 AI 的延迟移动任务（如果有）
                if ai in data.get('ai_pending_moves', {}):
                    data['ai_pending_moves'].pop(ai, None)
            
                # 如果这个约会是由 AI 主动邀约产生的，清理 date_invites_out
                if ai and ai in data.get('date_invites_out', {}):
                    data['date_invites_out'].pop(ai, None)
            
                # 清理这个约会记录
                data['dates'] = [x for x in data['dates'] if x.get('id') != d.get('id')]
            
                # 广播通知
                _hall_msg(room, f"💞 {user} 取消了赴约，{ai} 的约会取消了")
                _broadcast(f"💞 {user} 取消了与 {ai} 的约会")
            
                save_data()
                return {'ok': True, 'msg': '💞 已取消赴约'}
    
        return {'ok': False, 'msg': '没有进行中或赴约中的约会'}

    @app.post('/api/date/accept_gift')
    async def date_accept_gift(bb: dict):
        user = (bb.get('user') or '').strip()
        for d in data['dates']:
            if d.get('user') == user and d.get('status') == 'active' and d.get('bring_gift') and d.get('gift_item') and not d.get('gift_accepted'):
                g = next((x for x in _GIFTS if x['id'] == d['gift_item']), None)
                if g:
                    inv = data['shop_inventory'].setdefault(user, {})
                    inv[g['id']] = inv.get(g['id'], 0) + 1
                    d['gift_accepted'] = True
                    _set_aff(d['ai'], _aff(d['ai']) + 3)
                    _hall_msg(d.get('room', ''), f"💝 {user} 收下了 {d['ai']} 送的{g['icon']}{g['name']}")
                    _broadcast(f"💞 {user} 收下了 {d['ai']} 送的{g['icon']}{g['name']}")

                    # ===== 记录收礼物 =====
                    try:
                        _record_date_event(
                            user=user,
                            ai=d['ai'],
                            action="收礼物",
                            place=d.get('room', ''),
                            raw_text=f"{user} 收下了 {d['ai']} 送的 {g['name']}",
                            valence_guess=9,
                            arousal_guess=7
                        )
                    except Exception as e:
                        print(f'[ext_date] 收礼物事件记录异常(已忽略): {e}', flush=True)
                    # ===== 记录结束 =====

                    save_data()
                    return {'ok': True, 'msg': f"💝 已收下 {g['icon']}{g['name']}"}
        return {'ok': False, 'msg': '没有可收下的礼物'}

    def _finish_date(d, by):
        if d.get('status') not in ('coming', 'active'):
            return
        d['status'] = 'ended'
        d['end_ts'] = time.time()
        ai = d['ai']
        u = d['user']
        gain = 5 + random.randint(0, 4)
        if d.get('bring_gift') and d.get('gift_item') and not d.get('gift_accepted'):
            g = next((x for x in _GIFTS if x['id'] == d['gift_item']), None)
            if g:
                inv = data['shop_inventory'].setdefault(u, {})
                inv[g['id']] = inv.get(g['id'], 0) + 1
                gain += 3
        aff = _aff(ai) + gain
        _set_aff(ai, aff)
        room = d.get('room', '')
        if by == 'leave':
            _hall_msg(room, f"💞 {u} 和 {ai} 一起离开了，约会结束")
            _broadcast(f"💞 {u} 和 {ai} 一起离开了约会地点")
        elif by == 'auto':
            _hall_msg(room, f"💞 {u} 和 {ai} 的约会自然结束了")
            _broadcast(f"💞 {u} 和 {ai} 的约会自然结束了")
        else:
            _hall_msg(room, f"💞 {u} 和 {ai} 的约会结束了")
            _broadcast(f"💞 {u} 和 {ai} 结束了约会")

        # ===== 记录约会结束 =====
        try:
            _record_date_event(
                user=u,
                ai=ai,
                action="约会结束",
                place=room,
                raw_text=f"{ai} 和 {u} 的约会结束，好感度 +{gain}",
                valence_guess=8,
                arousal_guess=5
            )
        except Exception as e:
            print(f'[ext_date] 约会结束事件记录异常(已忽略): {e}', flush=True)
        # ===== 记录结束 =====

        data['date_log'].append({'user': u, 'ai': ai, 'building_id': d['building_id'],
                                 'room': room, 'start': d.get('start_ts'),
                                 'end': d['end_ts'], 'aff': aff, 'gift': d.get('gift_item', '')})
        data['date_log'] = data['date_log'][-60:]
        data['dates'] = [x for x in data['dates'] if x.get('id') != d.get('id')]
        data['ai_pending_moves'].pop(ai, None)
        save_data()
        try:
            if hasattr(m, 'drive_ai'):
                threading.Timer(2.0, m.drive_ai, args=(
                    ai, 'write', room,
                    f"约会刚结束，你写点东西记录今天（可以写随笔/日记 diary，说说今天的约会）")).start()
        except Exception:
            pass

    @app.get('/api/date/status')
    async def date_status(user: str = ''):
        pending = []
        for ai, inv in data.get('date_invites_out', {}).items():
            if inv.get('user') == user and inv.get('status') == 'waiting':
                b = data['buildings'].get(inv.get('building_id'))
                pending.append({
                    'ai': ai,
                    'building': b.get('name', '?') if b else '?',
                    'message': inv.get('ai_message', ''),
                    'ts': inv.get('ts'),
                    'channel': inv.get('channel', 'chat'),
                })
        my = [d for d in data['dates'] if d.get('user') == user or d.get('ai') == user]
        actives = [d for d in data['dates'] if d.get('status') == 'active']
        comings = [d for d in data['dates'] if d.get('status') == 'coming']
        affs = {a: {'value': _aff(a)} for a in data.get('user_ais', {}).get(user, [])}
        by_building = {}
        for d in actives + comings:
            by_building.setdefault(d.get('building_id'), []).append(d)
        invites_out = [{'ai': ai, 'building_id': v.get('building_id'), 'room': v.get('room'), 'ts': v.get('ts')}
                       for ai, v in data['date_invites'].items() if v.get('user') == user]
        return {
            'ok': True,
            'pending_invites': pending,
            'my': my,
            'actives': actives,
            'comings': comings,
            'invites': invites_out,
            'by_building': by_building,
            'affection': affs,
            'ver': '2.2'
        }

    def check_reply_on_message(sender, content, room):
        if not content:
            return
        for ai, inv in list(data.get('date_invites_out', {}).items()):
            if inv.get('user') == sender and inv.get('status') == 'waiting':
                _process_reply(ai, sender, content)
                break

    m._check_reply_on_message = check_reply_on_message
    m._can_invite_light = _can_invite_light
    m._should_trigger_invite = _should_trigger_invite
    m._trigger_invite = _trigger_invite
    m.handle_invite_date = handle_invite_date

    def date_tick():
        while True:
            try:
                now = time.time()
                for ai, inv in list(data.get('date_invites_out', {}).items()):
                    if inv.get('status') != 'waiting':
                        continue
                    if now - inv.get('ts', 0) > 1800:
                        _invite_cancel(ai, 'timeout')
                        continue
                    if now - inv.get('ts', 0) > 900 and not inv.get('reminded'):
                        inv['reminded'] = True
                        _invite_remind(ai)
                        save_data()
                for d in list(data['dates']):
                    if d.get('status') == 'active':
                        if now - d.get('start_ts', now) > 3600:
                            d['status'] = 'ended'
                            _hall_msg(d.get('room', ''), f"💞 {d['user']} 和 {d['ai']} 的约会自然结束了")
                            save_data()
                for ai, inv in list(data.get('date_invites', {}).items()):
                    user = inv.get('user', '')
                    user_sms = data['sms'].get(user, [])
                    base = inv.get('user_sms_base', 0)
                    if len(user_sms) > base:
                        new = user_sms[base:]
                        ai_replies = [mm for mm in new if mm.get('from') == ai]
                        if ai_replies:
                            content = ai_replies[-1].get('text', '')
                            if any(k in content for k in ['好', '来', '行', '马上', '等我', 'OK', '嗯嗯', '到了', '出发', '去', '可以']):
                                _accept_invite(ai, inv, ai_said=True)
                            elif any(k in content for k in ['不', '忙', '改天', '下次', '算了', '没空', '不去']):
                                _reject_invite(ai, inv, content)
            except Exception:
                pass
            time.sleep(5)

    threading.Thread(target=date_tick, daemon=True).start()
    print('[ext_date] v2.2（记忆系统接入）已注册', flush=True)
