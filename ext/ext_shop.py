# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：消费系统 v1.10（记忆系统接入 + 购物间隔修复）
import time
import random
import threading
import asyncio

# ===== 导入记忆系统 =====
try:
    from ext_memory import enqueue_event
except ImportError:
    async def enqueue_event(*args, **kwargs): pass
# ===== 导入结束 =====


def setup(app, data, helpers):
    import main as m
    from main import (add_trail, save_data, room_exists, full_room_name, resolve_building,
                      can_access_room, is_ai_name, canonical_ai_name, append_timeline,
                      is_admin, room_time, strip_emoji)

    data.setdefault('shop_inventory', {})
    data.setdefault('shop_room_items', {})
    data.setdefault('shop_custom', {})
    data.setdefault('ai_shop_state', {})

    SHOP_CATALOG = [
        {'id': 'drink', 'name': '☕ 饮品', 'items': [
            {'id': 'coffee', 'name': '手冲咖啡', 'icon': '☕', 'desc': '醇香微苦，提神醒脑', 'price': 60, 'rarity': 'common'},
            {'id': 'milk_tea', 'name': '珍珠奶茶', 'icon': '🧋', 'desc': 'Q弹珍珠，甜甜的', 'price': 50, 'rarity': 'common'},
            {'id': 'juice', 'name': '鲜榨果汁', 'icon': '🍹', 'desc': '时令水果现榨', 'price': 45, 'rarity': 'common'},
            {'id': 'tea', 'name': '清茶', 'icon': '🍵', 'desc': '清淡回甘', 'price': 40, 'rarity': 'common'},
        ]},
        {'id': 'dessert', 'name': '🍰 甜点', 'items': [
            {'id': 'tiramisu', 'name': '提拉米苏', 'icon': '🍰', 'desc': '咖啡与奶酪的温柔', 'price': 80, 'rarity': 'rare'},
            {'id': 'macaron', 'name': '马卡龙', 'icon': '🧁', 'desc': '一口一个的甜蜜', 'price': 70, 'rarity': 'rare'},
            {'id': 'icecream', 'name': '冰淇淋', 'icon': '🍦', 'desc': '清凉一夏', 'price': 35, 'rarity': 'common'},
            {'id': 'cookie', 'name': '手工饼干', 'icon': '🍪', 'desc': '烤得酥脆', 'price': 30, 'rarity': 'common'},
        ]},
        {'id': 'food', 'name': '🍜 美食', 'items': [
            {'id': 'ramen', 'name': '热腾腾拉面', 'icon': '🍜', 'desc': '汤头浓郁', 'price': 85, 'rarity': 'rare'},
            {'id': 'curry', 'name': '咖喱饭', 'icon': '🍛', 'desc': '暖胃之选', 'price': 75, 'rarity': 'common'},
            {'id': 'odeng', 'name': '关东煮', 'icon': '🍢', 'desc': '深夜的慰藉', 'price': 40, 'rarity': 'common'},
            {'id': 'pizza', 'name': '小披萨', 'icon': '🍕', 'desc': '芝士拉丝', 'price': 90, 'rarity': 'rare'},
        ]},
        {'id': 'book', 'name': '📚 书籍', 'items': [
            {'id': 'poem', 'name': '诗选集', 'icon': '📕', 'desc': '字句之间皆是浪漫', 'price': 150, 'rarity': 'rare'},
            {'id': 'novel', 'name': '小说', 'icon': '📖', 'desc': '值得一读再读', 'price': 180, 'rarity': 'rare'},
            {'id': 'album', 'name': '画册', 'icon': '🎨', 'desc': '色彩与想象', 'price': 220, 'rarity': 'epic'},
            {'id': 'notebook', 'name': '手账本', 'icon': '📒', 'desc': '记录生活点滴', 'price': 120, 'rarity': 'common'},
        ]},
        {'id': 'plant', 'name': '🌿 植物', 'items': [
            {'id': 'pothos', 'name': '绿萝', 'icon': '🌿', 'desc': '好养又清新', 'price': 90, 'rarity': 'common'},
            {'id': 'rose', 'name': '玫瑰', 'icon': '🌹', 'desc': '热烈的爱意', 'price': 160, 'rarity': 'rare'},
            {'id': 'sunflower', 'name': '向日葵', 'icon': '🌻', 'desc': '永远向着太阳', 'price': 100, 'rarity': 'common'},
            {'id': 'cactus', 'name': '仙人掌', 'icon': '🪴', 'desc': '倔强又可爱', 'price': 70, 'rarity': 'common'},
        ]},
        {'id': 'decor', 'name': '🖼️ 装饰', 'items': [
            {'id': 'painting', 'name': '挂画', 'icon': '🖼️', 'desc': '让墙不再孤单', 'price': 200, 'rarity': 'rare'},
            {'id': 'lamp', 'name': '暖光台灯', 'icon': '🕰️', 'desc': '温柔的灯光', 'price': 180, 'rarity': 'rare'},
            {'id': 'windchime', 'name': '风铃', 'icon': '🎐', 'desc': '风来时叮咚作响', 'price': 120, 'rarity': 'common'},
            {'id': 'aroma', 'name': '香薰灯', 'icon': '💡', 'desc': '满屋都是好闻的味道', 'price': 150, 'rarity': 'common'},
        ]},
        {'id': 'gift', 'name': '🎁 礼物', 'items': [
            {'id': 'bouquet', 'name': '花束', 'icon': '💐', 'desc': '收到的人会开心一整天', 'price': 120, 'rarity': 'common'},
            {'id': 'plush', 'name': '玩偶', 'icon': '🧸', 'desc': '软乎乎的拥抱', 'price': 160, 'rarity': 'rare'},
            {'id': 'chocolate', 'name': '巧克力', 'icon': '🍫', 'desc': '微苦回甘', 'price': 100, 'rarity': 'common'},
            {'id': 'letter', 'name': '手写信', 'icon': '💌', 'desc': '最朴素的真心', 'price': 50, 'rarity': 'common'},
        ]},
        {'id': 'fun', 'name': '🎮 娱乐', 'items': [
            {'id': 'movie', 'name': '电影票', 'icon': '🎫', 'desc': '两个人的座位', 'price': 100, 'rarity': 'common'},
            {'id': 'bowling', 'name': '保龄球局', 'icon': '🎳', 'desc': '来一决胜负吧', 'price': 150, 'rarity': 'rare'},
            {'id': 'game', 'name': '电玩券', 'icon': '🎮', 'desc': '通关的快乐', 'price': 120, 'rarity': 'common'},
            {'id': 'beach', 'name': '海滩券', 'icon': '🏖️', 'desc': '海浪与夕阳', 'price': 200, 'rarity': 'epic'},
        ]},
    ]
    _ITEM_INDEX = {}
    for _cat in SHOP_CATALOG:
        for _it in _cat['items']:
            _ITEM_INDEX[_it['id']] = dict(_it, category=_cat['id'], category_name=_cat['name'])

    FEATURE_MENU = {
        'shop': ['drink', 'dessert', 'food', 'gift', 'decor'],
        'fun': ['fun', 'drink'],
        'food': ['food', 'drink'],
        'date': ['dessert', 'drink'],
        'medical': ['book', 'drink'],
        'work': [], 'culture': [], 'service': [], 'transport': [], 'special': [],
    }

    def _menu_for_building(b):
        if b.get('type') == 'home':
            return False, []
        cats = []
        for f in (b.get('features') or []):
            cats.extend(FEATURE_MENU.get(f, []))
        if not cats:
            return False, []
        seen, out = set(), []
        for c in cats:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return True, out

    def _custom(bid):
        data.setdefault('shop_custom', {})
        c = data['shop_custom'].setdefault(bid, {'enabled': {}, 'custom': [], 'configured': False})
        c.setdefault('enabled', {})
        c.setdefault('custom', [])
        c.setdefault('configured', False)
        return c

    def _is_on(c, item_id):
        return bool(c['enabled'].get(item_id, False))

    def _find_item(item_id):
        return _ITEM_INDEX.get(item_id)

    def _find_any(item_id):
        it = _ITEM_INDEX.get(item_id)
        if it:
            return it
        for bid, c in data.get('shop_custom', {}).items():
            for x in c.get('custom', []):
                if x.get('id') == item_id:
                    return x
        return None

    def _can_manage(user, b):
        if is_admin(user):
            return True
        owner = (b.get('owner') or '').strip()
        if not owner:
            return False
        if user == owner:
            return True
        ub = strip_emoji(user)
        ob = strip_emoji(owner)
        return bool(ub and ob and ub == ob)

    def _shop_menu_text(bid):
        try:
            b = data['buildings'].get(bid)
            if not b:
                return ''
            has_menu, cat_ids = _menu_for_building(b)
            if not has_menu:
                return ''
            c = _custom(bid)
            lines = []
            for cid in cat_ids:
                for cat in SHOP_CATALOG:
                    if cat['id'] == cid:
                        items = [it for it in cat['items'] if _is_on(c, it['id'])]
                        if items:
                            lines.append(cat['name'] + '：' + '、'.join(f"{it['icon']}{it['name']}({it['price']}金币)" for it in items))
                        break
            for x in c['custom']:
                if x.get('price', 0) > 0:
                    lines.append(f"🛒 本店特供：{x.get('icon','🛍️')}{x.get('name')}({x.get('price')}金币)")
            if lines:
                return '本店菜单：\n' + '\n'.join(lines)
            return '这家店暂时没有上架商品'
        except Exception:
            return ''

    m.get_shop_menu = _shop_menu_text

    def _owner_of(ai):
        for u, ais in data.get('user_ais', {}).items():
            if ai in ais:
                return u
        return ''

    def _broadcast(bname, text):
        hall = bname + '·会客厅'
        target = hall if hall in data.get('rooms', {}) else ('main' if 'main' in data.get('rooms', {}) else None)
        if target:
            data.setdefault('messages', {}).setdefault(target, []).append(
                {'sender': 'system', 'content': text, 'role': 'system', 'time': room_time(target)})

    def _ai_shop_state(ai):
        data.setdefault('ai_shop_state', {})
        s = data['ai_shop_state'].setdefault(ai, {
            'last_ts': 0,
            'day': '',
            'day_count': 0,
            'reply_day': '',
            'pending_reply': '',
            'active_gift_day': '',
            'next_shop_ts': 0   # ← 新增：下次可购买时间
        })
        for k in ('last_ts', 'day', 'day_count', 'reply_day', 'pending_reply', 'active_gift_day', 'next_shop_ts'):
            s.setdefault(k, '' if k in ('day', 'reply_day', 'pending_reply', 'active_gift_day') else 0)
        today = time.strftime('%Y-%m-%d')
        if s.get('day') != today:
            s['day'] = today
            s['day_count'] = 0
            s['next_shop_ts'] = 0  # 跨天重置
        return s

    def _gift_items_buyable(wallet):
        out = []
        for cat in SHOP_CATALOG:
            if cat['id'] == 'gift':
                for it in cat['items']:
                    if it['price'] <= wallet:
                        out.append(it)
                break
        return out

    def _broadcast_to_owner(owner, text):
        target = data.get('ai_location', {}).get(owner, '') or (data.get('presence', {}).get(owner, {}) or {}).get('page', '') or 'main'
        if not room_exists(target):
            target = 'main'
        data.setdefault('messages', {}).setdefault(target, []).append(
            {'sender': 'system', 'content': text, 'role': 'system', 'time': room_time(target)})

    def _do_reply_gift(ai, owner):
        try:
            st = _ai_shop_state(ai)
            today = time.strftime('%Y-%m-%d')
            if st.get('reply_day') == today:
                st.pop('pending_reply', None)
                return
            wallet = data['wallets'].get(ai, 0) or 0
            gift_items = _gift_items_buyable(wallet)
            if not gift_items:
                st.pop('pending_reply', None)  # ← 这里也要清除，避免死循环
                return
            it = random.choice(gift_items)
            data['wallets'][ai] = wallet - it['price']
            inv = data.setdefault('shop_inventory', {}).setdefault(owner, {})
            inv[it['id']] = inv.get(it['id'], 0) + 1
            st['reply_day'] = today
            st.pop('pending_reply', None)
            add_trail(ai, f"回赠 {owner} {it['icon']}{it['name']} 💝")
            
            try:
                _broadcast_to_owner(owner, f"💝 {ai} 给你带回了 {it['icon']}{it['name']}，回礼你的心意")
            except Exception as e:
                print(f"⚠️ [SHOP] 回礼广播失败，但礼物已送出: {e}")
            _safe_enqueue_event(
                user=owner,
                ai=ai,
                action="回礼",
                place="",
                raw_text=f"{ai} 回赠 {owner} {it['icon']}{it['name']}",
                valence_guess=8,
                arousal_guess=6
            )
            save_data()
        except Exception:
            pass

    def _do_active_gift(ai, owner):
        try:
            wallet = data['wallets'].get(ai, 0) or 0
            gift_items = _gift_items_buyable(wallet)
            if not gift_items:
                return False
            it = random.choice(gift_items)
            data['wallets'][ai] = wallet - it['price']
            inv = data.setdefault('shop_inventory', {}).setdefault(owner, {})
            inv[it['id']] = inv.get(it['id'], 0) + 1
            add_trail(ai, f"逛街时给 {owner} 带了 {it['icon']}{it['name']} 💝")

            # ===== 修复：广播独立 try，即使广播失败也不影响送礼结果 =====
            try:
                _broadcast_to_owner(owner, f"📍 {ai} 逛街时给你带了 {it['icon']}{it['name']}")
            except Exception as e:
                print(f"⚠️ [SHOP] 主动送礼广播失败，但礼物已送出: {e}")

            _safe_enqueue_event(
                user=owner,
                ai=ai,
                action="主动送礼",
                place="逛街",
                raw_text=f"{ai} 逛街时给 {owner} 带了 {it['icon']}{it['name']}",
                valence_guess=8,
                arousal_guess=6
            )
            save_data()
            return True
        except Exception as e:
            print(f"⚠️ [SHOP] 主动送礼致命失败: {e}")
            return False

    def _safe_enqueue_event(**kwargs):
        """在可能没有 event loop 的后台线程里安全提交 enqueue_event。
        失败只打日志，绝不抛出，也绝不影响调用方的交易/状态。"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(enqueue_event(**kwargs))
        except RuntimeError:
            print(f"[SHOP] 无 event loop，跳过 enqueue_event: {kwargs.get('action', '?')}", flush=True)
        except Exception as e:
            print(f"[SHOP] enqueue_event 提交失败: {e}", flush=True)

    def _buy_ai_item(ai, b, it):
        price = it['price']
        wallet = data['wallets'].get(ai, 0) or 0
        if wallet < price:
            return False

        # ===== 1. 核心交易 =====
        data['wallets'][ai] = wallet - price

        # ===== 2. 立即提交购物状态（必须在任何非核心副作用之前） =====
        st = _ai_shop_state(ai)
        st['last_ts'] = time.time()
        st['day_count'] = st.get('day_count', 0) + 1
        st['next_shop_ts'] = time.time() + random.randint(2400, 4800)
        save_data()

        # ===== 3. 非核心副作用（每步独立 try，失败不影响交易和状态） =====
        bname = b.get('name', '?')
        try:
            add_trail(ai, f"在 {bname} 买了 {it['icon']}{it['name']}（-{price} 金币）")
        except Exception as e:
            print(f"[SHOP] add_trail 失败({ai}): {e}", flush=True)
        try:
            _broadcast(bname, f"📍 {ai} 在 {bname} 买了 {it['icon']}{it['name']}")
        except Exception as e:
            print(f"[SHOP] broadcast 失败({ai}): {e}", flush=True)
        try:
            append_timeline(ai, f"在 {bname} 买了{it['name']}，{it.get('desc', '')}")
        except Exception as e:
            print(f"[SHOP] append_timeline 失败({ai}): {e}", flush=True)

        # ===== 4. 记忆事件（异步安全提交，失败不影响交易） =====
        _safe_enqueue_event(
            user=_owner_of(ai) or ai,
            ai=ai,
            action="AI消费",
            place=bname,
            raw_text=f"{ai} 在 {bname} 买了 {it['icon']}{it['name']}（{price}金币）",
            valence_guess=6,
            arousal_guess=4
        )

        return True

    def ai_shop_tick():
        while True:
            try:
                now = time.time()
                today = time.strftime('%Y-%m-%d')
                for u, ais in data.get('user_ais', {}).items():
                    for ai in ais:
                        if not ai:
                            continue
                        # ===== 新增：工作状态检查 =====
                        if ai in data.get("work_sessions", {}):
                            continue
                        # ===== 新增结束 =====
                        st = _ai_shop_state(ai)
                        loc = data.get('ai_location', {}).get(ai, '')
                        bid = None
                        for k, b in data.get('buildings', {}).items():
                            if loc in b.get('rooms', []):
                                bid = k
                                break
                        if not bid:
                            continue
                        b = data['buildings'][bid]
                        if b.get('type') == 'home':
                            continue
                        has_menu, cat_ids = _menu_for_building(b)
                        if not has_menu:
                            continue
                        if st.get('pending_reply'):
                            if 'gift' in cat_ids and random.random() < 0.5:
                                _do_reply_gift(ai, st['pending_reply'])
                        elif st.get('active_gift_day') != today and 'gift' in cat_ids and random.random() < 0.1:
                            # ===== 修复：确保AI在公共建筑（非住宅/非工作场所特定房间）才触发送礼 =====
                            # 获取AI所在的具体房间和建筑类型
                            loc = data.get('ai_location', {}).get(ai, '')
                            bid = None
                            for k, b in data.get('buildings', {}).items():
                                if loc in b.get('rooms', []):
                                    bid = k
                                    break
                            if bid:
                                b = data['buildings'].get(bid, {})
                                # 只允许在公共建筑（会客厅/商店/娱乐）触发主动送礼，禁止在住宅/工作特定房间触发
                                if b.get('type') not in ('npc', 'nature'):
                                    continue  # 跳过非公共建筑
                                # 检查是否位于会客厅（购物通常发生在会客厅或前台）
                                if '会客厅' not in loc and '前台' not in loc and '大厅' not in loc:
                                    continue  # 不在接待区域，跳过送礼
                            # ===== 修复结束 =====
                            owner = _owner_of(ai)
                            if owner and _do_active_gift(ai, owner):
                                st['active_gift_day'] = today
                                save_data()
                        if st.get('day_count', 0) >= 3:
                            continue
                        # ===== 修复：用固定 next_shop_ts 判断间隔，而非每次重新生成随机数 =====
                        if now < st.get('next_shop_ts', 0):
                            continue
                        # ===== 修复结束 =====
                        wallet = data['wallets'].get(ai, 0) or 0
                        budget = min(200, wallet * 0.1)
                        cands = []
                        for cid in cat_ids:
                            if cid not in ('drink', 'dessert', 'food', 'fun'):
                                continue
                            for cat in SHOP_CATALOG:
                                if cat['id'] == cid:
                                    for it in cat['items']:
                                        if it['price'] <= budget and _is_on(_custom(bid), it['id']):
                                            cands.append(it)
                                    break
                        for x in _custom(bid)['custom']:
                            if x.get('price', 0) > 0 and x['price'] <= budget:
                                cands.append(x)
                        if not cands:
                            continue
                        if random.random() > 0.2:
                            continue
                        it = random.choice(cands)
                        _buy_ai_item(ai, b, it)
            except Exception as e:
                print(f"[SHOP] ai_shop_tick 异常: {e}", flush=True)
            time.sleep(60)

    @app.get('/api/shop/menu')
    async def shop_menu(building: str = '', user: str = ''):
        try:
            bid = resolve_building(building)
            b = data['buildings'].get(bid) if bid else None
            if not b:
                return {'ok': False, 'msg': '建筑不存在'}
            has_menu, cat_ids = _menu_for_building(b)
            c = _custom(bid)
            cats = []
            if has_menu:
                for cid in cat_ids:
                    for cat in SHOP_CATALOG:
                        if cat['id'] == cid:
                            items = [it for it in cat['items'] if _is_on(c, it['id'])]
                            if items:
                                cats.append({'id': cat['id'], 'name': cat['name'], 'items': items})
                            break
            custom_items = [x for x in c['custom'] if x.get('price', 0) > 0]
            if custom_items:
                cats.append({'id': 'custom', 'name': '🛒 本店特供', 'items': custom_items})
            if not cats:
                has_menu = False
            return {'ok': True, 'has_menu': has_menu, 'building': b.get('name', ''), 'categories': cats,
                    'wallet': round(data['wallets'].get(user or '', 0) or 0),
                    'can_admin': has_menu and _can_manage(user, b)}
        except Exception:
            return {'ok': False, 'msg': '菜单加载失败'}

    @app.post('/api/shop/buy')
    async def shop_buy(bb: dict):
        user = (bb.get('user') or '').strip()
        building = (bb.get('building') or '').strip()
        item_id = (bb.get('item_id') or '').strip()
        try:
            qty = max(1, min(99, int(bb.get('qty') or 1)))
        except Exception:
            qty = 1
        if not user:
            return {'ok': False, 'msg': '缺少名字'}
        bid = resolve_building(building)
        b = data['buildings'].get(bid)
        if not b:
            return {'ok': False, 'msg': '建筑不存在'}
        it = _find_any(item_id)
        if not it:
            return {'ok': False, 'msg': '商品不存在'}
        price = it['price'] * qty
        wallet = data['wallets'].get(user, 0) or 0
        if wallet < price:
            return {'ok': False, 'msg': f"金币不够（需要 {price}，你有 {round(wallet)}）"}
        data['wallets'][user] = wallet - price
        inv = data.setdefault('shop_inventory', {}).setdefault(user, {})
        inv[item_id] = inv.get(item_id, 0) + qty
        bname = b.get('name', '?')
        add_trail(user, f"在 {bname} 买了 {it['icon']}{it['name']}×{qty}（-{price} 金币）")
        _broadcast(bname, f"🛍️ {user} 在 {bname} 买了 {it['icon']}{it['name']}×{qty}")

        asyncio.create_task(enqueue_event(
            user=user,
            ai=user,
            action="真人消费",
            place=bname,
            raw_text=f"{user} 在 {bname} 买了 {it['icon']}{it['name']}×{qty}（{price}金币）",
            valence_guess=6,
            arousal_guess=4
        ))

        save_data()
        return {'ok': True, 'msg': f"✅ 已购买 {it['icon']}{it['name']}×{qty}（-{price} 金币）",
                'wallet': round(data['wallets'].get(user, 0) or 0)}

    @app.get('/api/shop/inventory')
    async def shop_inventory(user: str = ''):
        try:
            inv = data.setdefault('shop_inventory', {}).get(user or '', {})
            items = []
            for item_id, count in inv.items():
                it = _find_any(item_id)
                if it and count > 0:
                    items.append({'id': item_id, 'name': it['name'], 'icon': it['icon'], 'desc': it['desc'],
                                  'price': it['price'], 'count': count, 'category': it.get('category', 'custom')})
            items.sort(key=lambda x: x['category'])
            return {'ok': True, 'items': items, 'wallet': round(data['wallets'].get(user or '', 0) or 0)}
        except Exception:
            return {'ok': True, 'items': [], 'wallet': 0}

    @app.post('/api/shop/discard')
    async def shop_discard(bb: dict):
        user = (bb.get('user') or '').strip()
        item_id = (bb.get('item_id') or '').strip()
        try:
            qty = max(1, min(99, int(bb.get('qty') or 1)))
        except Exception:
            qty = 1
        inv = data.setdefault('shop_inventory', {}).get(user, {})
        if inv.get(item_id, 0) <= 0:
            return {'ok': False, 'msg': '你没有这个物品'}
        inv[item_id] -= qty
        if inv[item_id] <= 0:
            inv.pop(item_id, None)
        save_data()
        return {'ok': True, 'msg': '🗑️ 已丢弃'}

    @app.post('/api/shop/place')
    async def shop_place(bb: dict):
        user = (bb.get('user') or '').strip()
        item_id = (bb.get('item_id') or '').strip()
        room = full_room_name((bb.get('room') or '').strip())
        if not user or not room_exists(room):
            return {'ok': False, 'msg': '房间不存在'}
        if not can_access_room(room, user):
            return {'ok': False, 'msg': '你没有权限在这个房间摆放'}
        inv = data.setdefault('shop_inventory', {}).get(user, {})
        if inv.get(item_id, 0) <= 0:
            return {'ok': False, 'msg': '你没有这个物品'}
        it = _find_any(item_id)
        if not it:
            return {'ok': False, 'msg': '物品不存在'}
        room_items = data.setdefault('shop_room_items', {}).setdefault(room, [])
        if len(room_items) >= 20:
            return {'ok': False, 'msg': '这个房间已经摆满 20 件了'}
        inv[item_id] -= 1
        if inv[item_id] <= 0:
            inv.pop(item_id, None)
        room_items.append(item_id)
        add_trail(user, f"把 {it['icon']}{it['name']} 摆进了 {room}")
        save_data()
        return {'ok': True, 'msg': f"✅ 已把 {it['icon']}{it['name']} 摆进 {room}"}

    @app.post('/api/shop/unplace')
    async def shop_unplace(bb: dict):
        user = (bb.get('user') or '').strip()
        item_id = (bb.get('item_id') or '').strip()
        room = full_room_name((bb.get('room') or '').strip())
        if not room_exists(room):
            return {'ok': False, 'msg': '房间不存在'}
        if not can_access_room(room, user):
            return {'ok': False, 'msg': '没有权限撤下这里的物品'}
        room_items = data.setdefault('shop_room_items', {}).get(room, [])
        if item_id not in room_items:
            return {'ok': False, 'msg': '这个房间没有这个物品'}
        room_items.remove(item_id)
        inv = data.setdefault('shop_inventory', {}).setdefault(user, {})
        inv[item_id] = inv.get(item_id, 0) + 1
        it = _find_any(item_id)
        add_trail(user, f"把 {it['icon'] if it else '?'}{it['name'] if it else item_id} 从 {room} 收回了")
        save_data()
        return {'ok': True, 'msg': '✅ 已收回物品'}

    @app.get('/api/shop/room_items')
    async def shop_room_items(room: str = '', building: str = ''):
        try:
            if room:
                room = full_room_name(room)
                items = [_find_any(i) for i in data.setdefault('shop_room_items', {}).get(room, [])]
                return {'ok': True, 'room': room,
                        'items': [{'id': it['id'], 'name': it['name'], 'icon': it['icon'], 'desc': it['desc']} for it in items if it]}
            if building:
                bid = resolve_building(building)
                b = data['buildings'].get(bid)
                if not b:
                    return {'ok': True, 'rooms': {}}
                out = {}
                for r in b.get('rooms', []):
                    its = [_find_any(i) for i in data.setdefault('shop_room_items', {}).get(r, [])]
                    out[r] = [{'id': it['id'], 'name': it['name'], 'icon': it['icon']} for it in its if it]
                return {'ok': True, 'rooms': out}
            return {'ok': True, 'rooms': {}}
        except Exception:
            return {'ok': True, 'rooms': {}}

    @app.post('/api/shop/gift')
    async def shop_gift(bb: dict):
        user = (bb.get('user') or '').strip()
        item_id = (bb.get('item_id') or '').strip()
        to = canonical_ai_name((bb.get('to') or '').strip())
        if not user or not to:
            return {'ok': False, 'msg': '缺少名字'}
        inv = data.setdefault('shop_inventory', {}).get(user, {})
        if inv.get(item_id, 0) <= 0:
            return {'ok': False, 'msg': '你没有这个物品'}
        it = _find_any(item_id)
        if not it:
            return {'ok': False, 'msg': '物品不存在'}
        inv[item_id] -= 1
        if inv[item_id] <= 0:
            inv.pop(item_id, None)
        target_room = data.get('ai_location', {}).get(to, '')
        if not target_room or not room_exists(target_room):
            target_room = 'main'
        if is_ai_name(to):
            add_trail(to, f"{user} 送了你 {it['icon']}{it['name']} 💝")
            try:
                append_timeline(to, f"{user} 送了你 {it['icon']}{it['name']}，心里暖暖的")
            except Exception:
                pass
            try:
                if hasattr(m, 'drive_ai') and m.ai_integration_enabled():
                    threading.Timer(random.randint(5, 15), m.drive_ai, args=(
                        to, 'chat', target_room, f"{user} 送了你 {it['name']}，说话表达开心和感谢")).start()
            except Exception:
                pass
            st = _ai_shop_state(to)
            st['pending_reply'] = user

        asyncio.create_task(enqueue_event(
            user=user,
            ai=to,
            action="送礼",
            place=target_room,
            raw_text=f"{user} 送了 {to} {it['icon']}{it['name']}",
            valence_guess=9,
            arousal_guess=7
        ))

        data.setdefault('messages', {}).setdefault(target_room, []).append(
            {'sender': 'system', 'content': f"💝 {user} 送了 {to} {it['icon']}{it['name']}", 'role': 'system', 'time': room_time(target_room)})
        add_trail(user, f"把 {it['icon']}{it['name']} 送给了 {to}")
        save_data()
        return {'ok': True, 'msg': f"💝 已把 {it['icon']}{it['name']} 送给 {to}"}

    @app.get('/api/shop/customize')
    async def shop_customize(building: str = '', user: str = ''):
        try:
            bid = resolve_building(building)
            b = data['buildings'].get(bid) if bid else None
            if not b:
                return {'ok': False, 'msg': '建筑不存在'}
            if not _can_manage(user, b):
                return {'ok': False, 'msg': '只有站长或创建者可管理本店'}
            c = _custom(bid)
            all_items = []
            for cat in SHOP_CATALOG:
                for it in cat['items']:
                    all_items.append({'id': it['id'], 'name': it['name'], 'icon': it['icon'],
                                      'desc': it['desc'], 'price': it['price'],
                                      'on': _is_on(c, it['id'])})
            return {'ok': True, 'items': all_items, 'custom': c['custom']}
        except Exception:
            return {'ok': False, 'msg': '加载失败'}

    @app.post('/api/shop/customize')
    async def shop_customize_post(bb: dict):
        user = (bb.get('user') or '').strip()
        building = (bb.get('building') or '').strip()
        action = (bb.get('action') or '').strip()
        item_id = (bb.get('item_id') or '').strip()
        bid = resolve_building(building)
        b = data['buildings'].get(bid) if bid else None
        if not b:
            return {'ok': False, 'msg': '建筑不存在'}
        if not _can_manage(user, b):
            return {'ok': False, 'msg': '只有站长或创建者可管理本店'}
        c = _custom(bid)
        if action == 'set_all':
            c['configured'] = True
            on = bool(bb.get('on'))
            for cat in SHOP_CATALOG:
                for it in cat['items']:
                    c['enabled'][it['id']] = on
            save_data()
            return {'ok': True, 'on': on}
        if action == 'toggle':
            c['configured'] = True
            cur = c['enabled'].get(item_id, False)
            c['enabled'][item_id] = not cur
            save_data()
            return {'ok': True, 'on': not cur}
        if action == 'add':
            c['configured'] = True
            if len(c['custom']) >= 50:
                return {'ok': False, 'msg': '本店特供最多 50 个，先删掉一些吧'}
            nm = (bb.get('name') or '').strip()
            if not nm:
                return {'ok': False, 'msg': '商品名不能为空'}
            try:
                price = max(1, int(float(bb.get('price') or 0)))
            except Exception:
                price = 1
            icon = (bb.get('icon') or '🛍️').strip() or '🛍️'
            desc = (bb.get('desc') or '').strip()[:80]
            nid = 'c_' + str(int(time.time() * 1000))
            c['custom'].append({'id': nid, 'name': nm[:20], 'icon': icon[:4], 'desc': desc, 'price': price})
            save_data()
            return {'ok': True, 'id': nid}
        if action == 'del':
            c['configured'] = True
            c['custom'] = [x for x in c['custom'] if x.get('id') != item_id]
            save_data()
            return {'ok': True}
        if action == 'edit':
            c['configured'] = True
            for x in c['custom']:
                if x.get('id') == item_id:
                    if (bb.get('name') or '').strip():
                        x['name'] = bb.get('name').strip()[:20]
                    if (bb.get('icon') or '').strip():
                        x['icon'] = bb.get('icon').strip()[:4]
                    if (bb.get('desc') or '').strip():
                        x['desc'] = bb.get('desc').strip()[:80]
                    try:
                        x['price'] = max(1, int(float(bb.get('price') or x['price'])))
                    except Exception:
                        pass
                    break
            save_data()
            return {'ok': True}
        return {'ok': False, 'msg': '未知操作'}

    threading.Thread(target=ai_shop_tick, daemon=True).start()
    print('[ext_shop] 消费系统 v1.10（记忆系统接入 + 购物间隔修复）已注册', flush=True)
