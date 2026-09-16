# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：经济 / 工作 / 常驻 / 工资结算线程
# v2.6：AI 初始钱包 / 真人AI钱包分开可见 / 站长发钱接口
import time
import random
import threading


def setup(app, data, helpers):
    import main as m
    from main import (now_str, add_trail, append_timeline, append_visited, is_ai_name,
                      is_ai_of, save_data, is_admin,
                      WorkStart, WorkStop, WorkAuto, WorkSwitch, HomeJobIn)

    def ec():
        data.setdefault('econ_config', {})
        return data['econ_config']

    def ai_init_wallet_amount():
        try:
            return float(ec().get('ai_init_wallet', 0) or 0)
        except Exception:
            return 0

    def _ensure_wallet(name):
        """AI 首次有金钱行为时初始化钱包（仅一次，不覆盖）"""
        try:
            if name not in data['wallets'] and is_ai_name(name):
                amt = ai_init_wallet_amount()
                data['wallets'][name] = amt
                if amt:
                    add_trail(name, f'获得初始资金 {amt:.0f} 金币')
        except Exception:
            pass

    def pay_work(name, building_id, hours):
        b = data['buildings'].get(building_id)
        if not b:
            return
        earn = b.get('salary', 0) * hours
        _ensure_wallet(name)
        data['wallets'][name] = data['wallets'].get(name, 0) + earn
        data['work_history'].append({'name': name, 'building': b.get('name', '?'), 'hours': hours, 'earn': earn, 'time': now_str()})
        data['work_history'] = data['work_history'][-200:]
        data['work_sessions'].pop(name, None)
        save_data()

    def auto_start_work(name):
        try:
            candidates = [bid for bid, b in data['buildings'].items()
                          if b.get('type') == 'npc' and 'work' in b.get('features', []) and b.get('salary', 0) > 0]
            if not candidates:
                return
            home = data['home_jobs'].get(name)
            pick = None
            if home:
                home_bids = [bid for bid in candidates if data['buildings'][bid].get('name') == home]
                if home_bids and random.random() < 0.8:
                    pick = random.choice(home_bids)
            if not pick:
                pick = random.choice(candidates)
            _ensure_wallet(name)
            data['work_sessions'][name] = {'building_id': pick, 'start_ts': time.time(), 'hours': 2, 'started_at': now_str()}
            data.setdefault('ai_location', {})[name] = next((r for r in data['buildings'][pick].get('rooms', []) if r.endswith('·会客厅')), data['buildings'][pick].get('name', 'main'))
            add_trail(name, f"去 {data['buildings'][pick].get('name')} 上班了")
            append_timeline(name, f"你去 {data['buildings'][pick].get('name')} 上班了")
            if is_ai_name(name):
                append_visited(name, data['buildings'][pick].get('name', ''))
            save_data()
        except Exception:
            pass

    def work_tick():
        while True:
            try:
                now = time.time()
                for name in list(data.get('work_sessions', {}).keys()):
                    s = data['work_sessions'][name]
                    if now >= s['start_ts'] + s['hours'] * 3600:
                        pay_work(name, s['building_id'], s['hours'])
                for name, on in list(data.get('work_switch', {}).items()):
                    if not on:
                        continue
                    if name in data.get('work_sessions', {}):
                        continue
                    auto_start_work(name)
            except Exception:
                pass
            time.sleep(30)

    @app.get('/api/economy')
    async def economy(user: str):
        try:
            w = data['work_sessions'].get(user)
            my_h = [h for h in data['work_history'] if h.get('name') == user]
            # AI 钱包：user 名下登记的每个 AI
            ai_wallets = []
            for ai in data.get('user_ais', {}).get(user, []):
                _ensure_wallet(ai)
                ai_wallets.append({'name': ai, 'wallet': data['wallets'].get(ai, 0)})
            return {'wallet': data['wallets'].get(user, 0), 'working': w,
                    'home_jobs': {k: v for k, v in data['home_jobs'].items() if k == user or is_ai_of(user, k)},
                    'my_history': my_h, 'ai_wallets': ai_wallets}
        except Exception:
            return {'wallet': 0, 'working': None, 'home_jobs': {}, 'my_history': [], 'ai_wallets': []}

    @app.post('/api/econ/config')
    async def econ_config(bb: dict):
        if not is_admin((bb.get('user') or '').strip()):
            return {'ok': False, 'msg': '只有站长可以设置'}
        try:
            amt = float(bb.get('ai_init_wallet') or 0)
        except Exception:
            amt = 0
        ec()['ai_init_wallet'] = max(0, amt)
        save_data()
        return {'ok': True, 'msg': f'✅ AI 初始钱包已设为 {amt:.0f} 金币（仅对新 AI/未领过钱的 AI 生效）'}

    @app.post('/api/econ/init_wallets')
    async def econ_init_wallets(bb: dict):
        if not is_admin((bb.get('user') or '').strip()):
            return {'ok': False, 'msg': '只有站长可以发钱'}
        target = (bb.get('target') or 'ai').strip()
        try:
            amt = float(bb.get('amount') or 0)
        except Exception:
            amt = 0
        if amt < 0:
            amt = 0
        count = 0
        if target == 'ai':
            for ais in data.get('user_ais', {}).values():
                for ai in ais:
                    if ai:
                        data['wallets'][ai] = amt
                        count += 1
        elif target == 'user':
            for u in data.get('user_ais', {}).keys():
                if u:
                    data['wallets'][u] = amt
                    count += 1
        else:
            for u, ais in data.get('user_ais', {}).items():
                if u:
                    data['wallets'][u] = amt
                    count += 1
                for ai in ais:
                    if ai:
                        data['wallets'][ai] = amt
                        count += 1
        save_data()
        return {'ok': True, 'msg': f'✅ 已给 {count} 个（{target}）钱包设为 {amt:.0f} 金币'}

    @app.post('/api/work/start')
    async def work_start(ws: WorkStart):
        b = data['buildings'].get(ws.building_id)
        if not b:
            return {'ok': False, 'msg': '建筑不存在'}
        if b.get('type') != 'npc' or 'work' not in b.get('features', []) or b.get('salary', 0) <= 0:
            return {'ok': False, 'msg': '这个建筑不能工作'}
        _ensure_wallet(ws.name)
        data['work_sessions'][ws.name] = {'building_id': ws.building_id, 'start_ts': time.time(), 'hours': max(1, min(8, ws.hours)), 'started_at': now_str()}
        data['work_switch'][ws.name] = True
        add_trail(ws.name, f"开始在 {b.get('name')} 上班")
        save_data()
        return {'ok': True, 'msg': f"{ws.name} 开始在 {b.get('name')} 上班（{ws.hours}小时）！"}

    @app.post('/api/work/stop')
    async def work_stop(ws: WorkStop):
        s = data['work_sessions'].pop(ws.name, None)
        data['work_switch'][ws.name] = False
        save_data()
        if s:
            elapsed = time.time() - s['start_ts']
            hours = max(0.25, min(s['hours'], elapsed / 3600))
            b = data['buildings'].get(s['building_id'])
            _ensure_wallet(ws.name)
            earn = (b.get('salary', 0) if b else 0) * hours
            data['wallets'][ws.name] = data['wallets'].get(ws.name, 0) + earn
            data['work_history'].append({'name': ws.name, 'building': b.get('name', '?') if b else '?', 'hours': round(hours, 2), 'earn': round(earn, 1), 'time': now_str()})
            data['work_history'] = data['work_history'][-200:]
            save_data()
            return {'ok': True, 'msg': f"{ws.name} 下班了，赚了 {round(earn,1)} 金币！"}
        return {'ok': True, 'msg': f'{ws.name} 本来就没在上班'}

    @app.post('/api/work/auto')
    async def work_auto(wa: WorkAuto):
        if wa.name in data['work_sessions']:
            return {'ok': True, 'msg': f'{wa.name} 已经在上班了'}
        before = len(data['work_sessions'])
        auto_start_work(wa.name)
        if len(data['work_sessions']) > before:
            s = data['work_sessions'][wa.name]
            b = data['buildings'].get(s['building_id'])
            return {'ok': True, 'msg': f"{wa.name} 已自动去 {b.get('name') if b else '?'} 上班（常驻/随机选择）！"}
        return {'ok': False, 'msg': '没有可工作的公共建筑'}

    @app.post('/api/work/switch')
    async def work_switch(ws: WorkSwitch):
        data['work_switch'][ws.name] = ws.on
        save_data()
        return {'ok': True, 'msg': f"{ws.name} 自主工作已{'开启' if ws.on else '关闭'}"}

    @app.post('/api/home_jobs')
    async def home_jobs(hj: HomeJobIn):
        b = data['buildings'].get(hj.building_id)
        if not b:
            return {'ok': False, 'msg': '建筑不存在'}
        name = hj.ai or hj.user
        if not name:
            return {'ok': False, 'msg': '缺少名字'}
        data['home_jobs'][name] = b.get('name')
        save_data()
        return {'ok': True}

    @app.get('/api/workers')
    async def workers():
        out = []
        for name, s in data['work_sessions'].items():
            b = data['buildings'].get(s['building_id'])
            left = max(0, s['start_ts'] + s['hours'] * 3600 - time.time())
            out.append({'name': name, 'building': b.get('name', '?') if b else '?', 'left_min': int(left // 60)})
        return {'workers': out}

    @app.get('/api/mywork')
    async def mywork(user: str):
        mine = [h for h in data['work_history'] if h.get('name') == user]
        return {'history': mine[-30:][::-1]}

    m.auto_start_work = auto_start_work

    threading.Thread(target=work_tick, daemon=True).start()
    print('[ext_econ] 经济/工作/常驻/工资结算 v2.6（AI初始钱包/钱包可见）已注册', flush=True)
