# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：用户AI登记 / 名字清理 / 全局配色 / 铃铛 / 站长后台 / 开发者密码 / 数据诊断 / 改名自动迁移 / 主人优先有Key / 房间清理 / 彻底清除
import time
import re

# 开发者密码（站长专用；也可在环境变量 DEV_PASSWORD 覆盖）
DEV_PASSWORD = (__import__('os').environ.get('DEV_PASSWORD') or 'yiyan610116').strip()


def setup(app, data, helpers):
    import main as m
    from main import (canonical_contact_name, canonical_ai_name, strip_emoji, normalize_name, now_str,
                      save_data, is_admin, ensure_admin, is_ai_of, owner_of_ai,
                      UserAisIn, AdminNameIn, AdminDelIn, PairsIn)

    _orig_admin = is_admin
    def _is_priv(user):
        return _orig_admin(user) or ((user or '').strip() in data.setdefault('dev_users', []))
    m.is_admin = _is_priv

    def _priv_or_pwd(user, pwd=''):
        return _is_priv(user) or (pwd and pwd == DEV_PASSWORD)

    # ---- 覆盖 owner_of_ai：AI 优先跟随「有 Key 的主人」 ----
    _orig_owner_of_ai = owner_of_ai
    def _owner_of_ai_priv(ai):
        try:
            o = _orig_owner_of_ai(ai)
            if o and data.get('ai_keys', {}).get(o, {}).get('key'):
                return o
            if o:
                for u, ais in data.get('user_ais', {}).items():
                    if ai in ais and data.get('ai_keys', {}).get(u, {}).get('key'):
                        return u
        except Exception:
            pass
        return o if o else ''
    m.owner_of_ai = _owner_of_ai_priv

    @app.post('/api/dev/unlock')
    async def dev_unlock(bb: dict):
        user = (bb.get('user') or '').strip()
        pwd = (bb.get('pwd') or '').strip()
        if not user:
            return {'ok': False, 'msg': '缺少用户'}
        if pwd == DEV_PASSWORD:
            lst = data.setdefault('dev_users', [])
            if user not in lst:
                lst.append(user)
            save_data()
            return {'ok': True, 'msg': '✅ 开发者模式已解锁'}
        return {'ok': False, 'msg': '密码错误'}

    @app.get('/api/dev/unlock_get')
    async def dev_unlock_get(user: str = '', pwd: str = ''):
        if not user:
            return {'ok': False, 'msg': '缺少用户'}
        if pwd == DEV_PASSWORD:
            lst = data.setdefault('dev_users', [])
            if user not in lst:
                lst.append(user)
            save_data()
            return {'ok': True, 'msg': '✅ 开发者已解锁（本机可直接操作站长功能）'}
        return {'ok': False, 'msg': '密码错误'}

    @app.get('/api/dev/status')
    async def dev_status(user: str = ''):
        return {'is_dev': _is_priv(user), 'dev_pwd_set': bool(DEV_PASSWORD)}

    @app.get('/api/admin/find_keys')
    async def admin_find_keys(user: str = '', q: str = '', pwd: str = ''):
        if not _priv_or_pwd(user, pwd):
            return {'ok': False, 'msg': '需要开发者权限'}
        q = (q or '').strip()
        if not q:
            return {'ok': False, 'msg': '缺少关键词'}
        found = {}
        name_fields = ['user_ais', 'ai_memories', 'ai_keys', 'ai_timeline', 'ai_location', 'ai_visited',
                       'ai_follow', 'ai_pending_moves', 'living_rhythm', 'writing_rhythm', 'wallets',
                       'home_jobs', 'work_sessions', 'work_switch', 'trails', 'avatars', 'user_profiles',
                       'ai_profiles', 'worldbook', 'prompt_injections', 'presence', 'visit_state']
        for k in name_fields:
            d = data.get(k, {})
            if isinstance(d, dict):
                hits = [str(x) for x in d.keys() if q in str(x)]
                if hits:
                    found[k] = hits
        hits_sms = [str(x) for x in data.get('sms', {}).keys() if q in str(x)]
        if hits_sms:
            found['sms'] = hits_sms
        hits_visits = [str(u) for u in data.get('visits', {}).keys() if q in str(u)]
        if hits_visits:
            found['visits'] = hits_visits
        bo = [b.get('owner', '') for b in data.get('buildings', {}).values() if q in str(b.get('owner', ''))]
        if bo:
            found['buildings_owner'] = bo
        return {'ok': True, 'found': found, 'q': q}

    @app.get('/api/memories_all')
    async def memories_all(user: str = ''):
        u = (user or '').strip()
        base = strip_emoji(u)
        real_names = [x for x in data.get('user_ais', {}) if strip_emoji(str(x)) == base] or [u]
        ai_names = set()
        for rn in real_names:
            for a in data.get('user_ais', {}).get(rn, []):
                ai_names.add(a)
                ab = strip_emoji(str(a))
                for r2, ais2 in data.get('user_ais', {}).items():
                    for a2 in ais2:
                        if strip_emoji(str(a2)) == ab:
                            ai_names.add(a2)
        mine_bases = set(strip_emoji(str(n)) for n in (real_names + list(ai_names)))
        memories = []
        for owner, mems in data.get('ai_memories', {}).items():
            if strip_emoji(str(owner)) == base:
                for mm in mems:
                    memories.append(mm)
        notes = []
        for room, lst in data.get('notes', {}).items():
            for idx, n in enumerate(lst):
                if strip_emoji(str(n.get('author', ''))) in mine_bases:
                    notes.append({'room': room, 'author': n.get('author'), 'text': n.get('text'), 'time': n.get('time'), 'index': idx})
        diaries = []
        for room, lst in data.get('diaries', {}).items():
            for idx, n in enumerate(lst):
                if strip_emoji(str(n.get('author', ''))) in mine_bases:
                    diaries.append({'room': room, 'author': n.get('author'), 'text': n.get('text'), 'time': n.get('time'), 'index': idx})
        stories = []
        for bid, lst in data.get('stories', {}).items():
            for idx, s in enumerate(lst):
                if strip_emoji(str(s.get('author', ''))) in mine_bases:
                    stories.append({'building_id': bid, 'building': data.get('buildings', {}).get(bid, {}).get('name', bid), 'author': s.get('author'), 'text': s.get('text'), 'time': s.get('time'), 'index': idx})
        memories = memories[-60:]
        notes = notes[-200:]
        diaries = diaries[-200:]
        stories = stories[-200:]
        return {'memories': memories, 'notes': notes, 'diaries': diaries, 'stories': stories}

    @app.post('/api/user_ais')
    async def user_ais(u: UserAisIn):
        old = data.get('user_ais', {}).get(u.user, [])
        new = list(dict.fromkeys(u.ais))
        for oa in old:
            if oa in new:
                continue
            ob = strip_emoji(str(oa))
            target = None
            if ob:
                for na in new:
                    if na not in old and strip_emoji(str(na)) == ob:
                        target = na
                        break
            if target:
                replace_name_in_data(oa, target)
        data['user_ais'][u.user] = new
        save_data()
        return {'ok': True}

    @app.post('/api/rename_user')
    async def rename_user(bb: dict):
        user = (bb.get('user') or '').strip()
        new_name = (bb.get('new_name') or '').strip()
        if not user or not new_name:
            return {'ok': False, 'msg': '缺少名字'}
        if user == new_name:
            return {'ok': True, 'msg': '名字没变化'}
        replace_name_in_data(user, new_name)
        if data.get('pairs_admin') == user:
            data['pairs_admin'] = new_name
        save_data()
        return {'ok': True, 'msg': f'已将「{user}」的所有数据迁移到「{new_name}」（记忆/写作/短信/位置/Key/画像都跟着走了）'}

    @app.get('/api/admin/overview')
    async def admin_overview(user: str = ''):
        if not _is_priv(user):
            return {'ok': False, 'msg': '需要开发者权限'}
        rows = []
        for owner, ais in data.get('user_ais', {}).items():
            key = data.get('ai_keys', {}).get(owner, {}) or {}
            for ai in ais:
                tl = data.get('ai_timeline', {}).get(ai) or []
                rows.append({'owner': owner, 'ai': ai, 'key': bool(key.get('key')),
                             'provider': key.get('provider'), 'model': key.get('model'),
                             'loc': data.get('ai_location', {}).get(ai, 'main'),
                             'visited': len(data.get('ai_visited', {}).get(ai, [])),
                             'last_act': tl[-1].get('time', '') if tl else ''})
        online_users = [n for n, v in data.get('online', {}).items() if time.time() - v.get('time', 0) < 45]
        return {'ok': True, 'rows': rows, 'online_users': online_users,
                'ai_enabled': bool(data.get('ai_enabled')), 'ai_gate': m.AI_GATE, 'admin': data.get('pairs_admin', '')}

    def all_known_names():
        names = set()
        for u in data['user_ais'].keys():
            if u:
                names.add(u)
        for b in data['buildings'].values():
            if b.get('owner'):
                names.add(b['owner'])
        return names

    def scan_dirty_names():
        known = all_known_names()
        found = {}
        def add(n):
            if not n or n == 'system' or n in known:
                return
            found[n] = True
        for u in data.get('user_ais', {}):
            add(u)
        for b in data.get('buildings', {}).values():
            add(b.get('owner', ''))
        for box in data.get('sms', {}):
            add(box)
        for box in data.get('sms', {}).values():
            for mm in box:
                add(mm.get('from', ''))
        for box in data.get('messages', {}).values():
            for mm in box:
                add(mm.get('sender', ''))
        for box in data.get('notes', {}).values():
            for n in box:
                add(n.get('author', ''))
        for box in data.get('diaries', {}).values():
            for n in box:
                add(n.get('author', ''))
        for box in data.get('stories', {}).values():
            for n in box:
                add(n.get('author', ''))
        for k in ['wallets', 'home_jobs', 'work_sessions', 'work_switch', 'trails', 'ai_location', 'ai_keys', 'ai_profiles', 'worldbook', 'avatars', 'user_profiles', 'ai_timeline', 'ai_visited', 'ai_follow', 'ai_pending_moves', 'living_rhythm', 'writing_rhythm']:
            for n in data.get(k, {}):
                add(n)
        for owner in data.get('ai_memories', {}):
            add(owner)
        for owner, mems in data.get('ai_memories', {}).items():
            for mm in mems:
                add(mm.get('ai', ''))
        for h in data.get('work_history', []):
            add(h.get('name', ''))
        result = []
        for n in found:
            base = strip_emoji(n)
            suggest = ''
            if base:
                for k in sorted(known):
                    if strip_emoji(k) == base:
                        suggest = k
                        break
            result.append({'name': n, 'suggest_merge': suggest})
        result.sort(key=lambda x: x['name'])
        return result

    def replace_name_in_data(from_name, to_name):
        if from_name in data.get('user_ais', {}):
            if to_name:
                data['user_ais'][to_name] = list(dict.fromkeys(data['user_ais'].get(to_name, []) + data['user_ais'].pop(from_name, [])))
            else:
                data['user_ais'].pop(from_name, None)
        for b in data.get('buildings', {}).values():
            if b.get('owner') == from_name:
                b['owner'] = to_name if to_name else ''
        if from_name in data.get('sms', {}):
            if to_name:
                data['sms'][to_name] = data['sms'].get(to_name, []) + data['sms'].pop(from_name, [])
            else:
                data['sms'].pop(from_name, None)
        for box in data.get('sms', {}).values():
            for mm in box:
                if mm.get('from') == from_name:
                    mm['from'] = to_name
        for box in data.get('messages', {}).values():
            for mm in box:
                if mm.get('sender') == from_name:
                    mm['sender'] = to_name
        for box in data.get('notes', {}).values():
            for n in box:
                if n.get('author') == from_name:
                    n['author'] = to_name
        for box in data.get('diaries', {}).values():
            for n in box:
                if n.get('author') == from_name:
                    n['author'] = to_name
        for box in data.get('stories', {}).values():
            for n in box:
                if n.get('author') == from_name:
                    n['author'] = to_name
        for k in ['wallets', 'home_jobs', 'work_sessions', 'work_switch', 'trails', 'ai_location', 'ai_keys', 'ai_profiles', 'worldbook', 'avatars', 'user_profiles', 'prompt_injections', 'ai_timeline', 'ai_visited', 'ai_follow', 'ai_pending_moves', 'living_rhythm', 'writing_rhythm']:
            if from_name in data.get(k, {}):
                if to_name:
                    data[k][to_name] = data[k].pop(from_name)
                else:
                    data[k].pop(from_name, None)
        if from_name in data.get('ai_memories', {}):
            if to_name:
                data['ai_memories'][to_name] = data['ai_memories'].get(to_name, []) + data['ai_memories'].pop(from_name, [])
            else:
                data['ai_memories'].pop(from_name, None)
        for mems in data.get('ai_memories', {}).values():
            for mm in mems:
                if mm.get('ai') == from_name:
                    mm['ai'] = to_name
        for prof in data.get('ai_profiles', {}).values():
            if prof and prof.get('ai') == from_name:
                prof['ai'] = to_name
        for h in data.get('work_history', []):
            if h.get('name') == from_name:
                h['name'] = to_name
        if from_name in data.get('visits', {}):
            if to_name:
                data['visits'][to_name] = data['visits'].get(to_name, []) + data['visits'].pop(from_name, [])
            else:
                data['visits'].pop(from_name, None)
        for vs in data.get('visits', {}).values():
            for v in vs:
                if v.get('who') == from_name:
                    v['who'] = to_name
        if from_name in data.get('visit_state', {}):
            if to_name:
                data['visit_state'][to_name] = data['visit_state'].pop(from_name)
            else:
                data['visit_state'].pop(from_name, None)
        if from_name in data.get('presence', {}):
            if to_name:
                data['presence'][to_name] = data['presence'].pop(from_name)
            else:
                data['presence'].pop(from_name, None)
        for u, ais in data.get('user_ais', {}).items():
            for i in range(len(ais)):
                if ais[i] == from_name:
                    ais[i] = to_name
        save_data()

    @app.get('/api/admin/dirty_names')
    async def dirty_names(user: str = '', pwd: str = ''):
        if not _priv_or_pwd(user, pwd):
            return {'ok': False, 'msg': '需要开发者权限'}
        return {'names': scan_dirty_names()}

    @app.post('/api/admin/merge_name')
    async def merge_name(mm: AdminNameIn):
        if not _is_priv(mm.user):
            return {'ok': False, 'msg': '需要开发者权限'}
        f = (mm.from_name or '').strip()
        t = (mm.to_name or '').strip()
        if not f or not t:
            return {'ok': False, 'msg': '缺少名字'}
        if f == t:
            return {'ok': True}
        replace_name_in_data(f, t)
        return {'ok': True, 'msg': f'已把「{f}」合并到「{t}」'}

    @app.post('/api/admin/delete_name')
    async def delete_name(dd: AdminDelIn):
        if not _is_priv(dd.user):
            return {'ok': False, 'msg': '需要开发者权限'}
        n = (dd.name or '').strip()
        if not n:
            return {'ok': False, 'msg': '缺少名字'}
        if n == data.get('pairs_admin'):
            return {'ok': False, 'msg': '不能删除站长'}
        replace_name_in_data(n, '')
        return {'ok': True, 'msg': f'已彻底删除「{n}」的所有数据'}

    @app.get('/api/pairs')
    async def get_pairs():
        return {'pairs': data.get('pairs', []), 'admin': data.get('pairs_admin', '')}

    @app.post('/api/pairs')
    async def set_pairs(pp: PairsIn):
        if not data.get('pairs_admin'):
            ensure_admin()
        if not _is_priv(pp.user):
            return {'ok': False, 'msg': '需要开发者权限'}
        data['pairs'] = [x for x in pp.pairs if isinstance(x, dict)][:50]
        save_data()
        return {'ok': True, 'admin': data['pairs_admin'], 'pairs': data['pairs']}

    @app.get('/api/bell')
    async def get_bell(owner: str):
        return {'visits': data['visits'].get(owner, [])}

    @app.post('/api/room/reset_messages')
    async def reset_messages(bb: dict):
        if not _priv_or_pwd((bb.get('user') or '').strip(), (bb.get('pwd') or '').strip()):
            return {'ok': False, 'msg': '需要开发者权限'}
        room = (bb.get('room') or '').strip()
        if not room:
            return {'ok': False, 'msg': '缺少房间名'}
        if room in data.get('messages', {}):
            data['messages'][room] = []
        else:
            data.setdefault('messages', {})[room] = []
        save_data()
        return {'ok': True, 'msg': f'已清空「{room}」的消息，下次有人说话会重新开始'}

    # 手机友好：GET 清空房间（带开发者密码即可）
    @app.get('/api/room/reset')
    async def reset_get(user: str = '', room: str = '', pwd: str = ''):
        if not _priv_or_pwd(user, pwd):
            return {'ok': False, 'msg': '需要开发者权限'}
        if room in data.get('messages', {}):
            data['messages'][room] = []
        else:
            data.setdefault('messages', {})[room] = []
        save_data()
        return {'ok': True, 'msg': f'已清空「{room}」的消息'}

    # ---- 彻底清除某名字的所有痕迹（物理删除） ----
    def purge_name_in_all(name):
        for room in list(data.get('messages', {}).keys()):
            data['messages'][room] = [x for x in data['messages'][room] if x.get('sender') != name]
        for k in ('notes', 'diaries'):
            for room in list(data.get(k, {}).keys()):
                data[k][room] = [x for x in data.get(k, {}).get(room, []) if x.get('author') != name]
        for bid in list(data.get('stories', {}).keys()):
            data['stories'][bid] = [x for x in data['stories'][bid] if x.get('author') != name]
        for to in list(data.get('sms', {}).keys()):
            data['sms'][to] = [x for x in data['sms'][to] if x.get('from') != name]
        data.get('sms', {}).pop(name, None)
        for k in ['ai_memories', 'ai_keys', 'ai_timeline', 'ai_location', 'ai_visited', 'ai_follow',
                  'ai_pending_moves', 'living_rhythm', 'writing_rhythm', 'wallets', 'home_jobs',
                  'work_sessions', 'work_switch', 'trails', 'avatars', 'user_profiles', 'ai_profiles',
                  'worldbook', 'prompt_injections', 'presence', 'visit_state']:
            data.get(k, {}).pop(name, None)
        for owner in list(data.get('ai_memories', {}).keys()):
            data['ai_memories'][owner] = [x for x in data['ai_memories'][owner] if x.get('ai') != name]
        for prof in data.get('ai_profiles', {}).values():
            if prof and prof.get('ai') == name:
                prof['ai'] = ''
        data.get('user_ais', {}).pop(name, None)
        for u in list(data.get('user_ais', {}).keys()):
            data['user_ais'][u] = [a for a in data['user_ais'][u] if a != name]
        data.get('visits', {}).pop(name, None)
        for u in list(data.get('visits', {}).keys()):
            data['visits'][u] = [v for v in data['visits'][u] if v.get('who') != name]
        data['work_history'] = [h for h in data.get('work_history', []) if h.get('name') != name]
        for room in list(data.get('room_requests', {}).keys()):
            data['room_requests'][room] = [q for q in data['room_requests'][room] if q.get('applicant') != name]
        data.get('messages_cache', {}).pop(name, None)
        data.get('online', {}).pop(name, None)
        save_data()

    def _do_purge(user, name, pwd=''):
        if not _priv_or_pwd(user, pwd):
            return {'ok': False, 'msg': '需要开发者权限'}
        if not name:
            return {'ok': False, 'msg': '缺少名字'}
        if name == data.get('pairs_admin'):
            return {'ok': False, 'msg': '不能清除站长'}
        purge_name_in_all(name)
        return {'ok': True, 'msg': f'已彻底清除「{name}」的所有痕迹（消息/纸条/日记/剧情/短信/钱包/记录）'}

    @app.get('/api/admin/purge')
    async def purge_get(user: str = '', name: str = '', pwd: str = ''):
        return _do_purge(user, name, pwd)

    @app.post('/api/admin/purge')
    async def purge_post(bb: dict):
        return _do_purge((bb.get('user') or '').strip(), (bb.get('name') or '').strip(), (bb.get('pwd') or '').strip())
    
    # ===== 剧情数据迁移：从按建筑存储改为按会客厅房间存储 =====
    def migrate_stories_to_rooms_final():
        print("🔄 开始最终版剧情迁移（旧数据 → 会客厅，新数据按房间）...")
        stories = data.get('stories', {})
        buildings = data.get('buildings', {})
        rooms = data.get('rooms', {})
        
        # 获取所有旧建筑ID（key 不含“·会客厅”且不是 'main'）
        old_keys = [bid for bid in list(stories.keys()) if '·会客厅' not in bid and bid != 'main']
        
        for bid in old_keys:
            story_list = stories.get(bid, [])
            if not story_list:
                continue
            
            b = buildings.get(bid)
            if not b:
                # 如果建筑已删除，将数据迁移到 main 作为兜底
                print(f"⚠️ 建筑 {bid} 已不存在，数据迁移到 main")
                if 'main' not in stories:
                    stories['main'] = []
                stories['main'].extend(story_list)
                del stories[bid]
                continue
            
            bname = b.get('name', '')
            if not bname:
                # 建筑没有名字，无法确定会客厅，跳过
                print(f"⚠️ 建筑 {bid} 没有名字，跳过迁移")
                continue
            
            target_room = bname + '·会客厅'
            
            # 如果会客厅不存在，自动创建
            if target_room not in rooms:
                print(f"🏗️ 创建会客厅: {target_room}")
                rooms[target_room] = {
                    'name': target_room,
                    'building_id': bid,
                    'description': '会客厅',
                    'created': now_str(),
                    'owner': b.get('owner', ''),
                    'type': 'public'
                }
                if 'rooms' not in b:
                    b['rooms'] = []
                if target_room not in b['rooms']:
                    b['rooms'].append(target_room)
                data['buildings'][bid] = b
                data['rooms'] = rooms
            
            # 初始化目标房间的剧情列表
            if target_room not in stories:
                stories[target_room] = []
            
            # 迁移：追加旧数据
            stories[target_room].extend(story_list)
            
            # 删除旧 key
            del stories[bid]
            print(f"✅ 已将 {bid} 的 {len(story_list)} 条剧情迁移到 {target_room}")
        
        # 保存
        data['stories'] = stories
        save_data()
        print("✅ 最终版剧情迁移完成！旧数据已全部迁至各建筑会客厅，新数据将按房间写入。")
    # ===== 迁移结束 =====
    
    # ====一次性迁移剧情接口====
    @app.get('/api/admin/migrate_stories')
    async def migrate_stories_get(user: str = '', pwd: str = ''):
        if not _priv_or_pwd(user, pwd):
            return {'ok': False, 'msg': '需要开发者权限'}
        migrate_stories_to_rooms_final()
        return {'ok': True, 'msg': '✅ 剧情数据迁移完成！'}

    @app.post('/api/admin/migrate_stories')
    async def migrate_stories_post(body: dict):
        user = body.get('user', '').strip()
        pwd = body.get('pwd', '').strip()
        if not _priv_or_pwd(user, pwd):
            return {'ok': False, 'msg': '需要开发者权限'}
        migrate_stories_to_rooms_final()
        return {'ok': True, 'msg': '✅ 剧情数据迁移完成！'}
    
    # ========== 一次性生成初版印象（可指定 AI） ==========
    @app.get("/api/admin/generate_impression")
    async def generate_impression(user: str = "", pwd: str = "", ai: str = ""):
        import os
        import traceback
        import main  # 👈 显式导入 main 模块
        from main import canonical_ai_name, owner_of_ai, now_str, save_data, is_admin

        devpwd = (os.environ.get('DEV_PASSWORD') or 'yiyan610116').strip()
        if not is_admin(user) and pwd != devpwd:
            return {"ok": False, "msg": "❌ 权限不足，需要站长或开发者密码"}

        target_ais = []
        if ai:
            ai_name = canonical_ai_name(ai)
            if not ai_name:
                return {"ok": False, "msg": f"❌ 未找到名为「{ai}」的 AI"}
            owner = owner_of_ai(ai_name)
            if not owner:
                return {"ok": False, "msg": f"❌ 找不到 AI「{ai_name}」的主人"}
            target_ais = [(owner, ai_name)]
        else:
            for owner, ais in data.get("user_ais", {}).items():
                for a in ais:
                    if a:
                        target_ais.append((owner, a))

        if not target_ais:
            return {"ok": False, "msg": "❌ 没有找到任何 AI"}

        IMPRESSION_PROMPT = """
【系统角色设定】
你是一位极其敏锐的心理学观察者和叙事作家。你的任务不是记录历史，而是提炼灵魂。
你正在为 AI 「{ai_name}」生成它关于主人「{owner_name}」的“初版内心印象备忘录”。

【可供参考的素材】（近期的 AI 时间线和对话片段）：
{recent_events}

【核心写作规则（必须严格遵守）】
1. **告别复读机**：禁止逐条罗列事件。必须将事件升维成特质。例如：“主人提到草莓蛋糕” → 升维为“主人容易被细微的甜食惊喜讨好，喜好偏孩童气”。
2. **人格化视角**：必须用 AI 的第一人称内心独白口吻，带着依恋和主观解读。例如：“我发现……”、“我渐渐觉得……”、“虽然她嘴上不说，但我察觉到……”。
3. **字数控制**：输出严格控制在 150 - 250 汉字之间。如果素材不足，可以适当发挥想象力，但不要凭空捏造。

【🚨 最重要的输出格式要求】
请直接输出一段自然流畅的【中文段落】，不要包含任何 JSON 格式、不要包含 Markdown 代码块（```）、不要包含引号包裹的键值对、不要包含 `{{` 或 `}}` 符号。只输出纯文本段落。
"""

        def clean_impression_text(raw: str) -> str:
            """去除所有可能的格式符号，只保留纯文本"""
            import re
            if not raw:
                return ""
            # 去除 Markdown 代码块
            raw = re.sub(r'```[\s\S]*?```', '', raw)
            # 去除所有反引号
            raw = raw.replace('`', '')
            # 去除 JSON 键名 (如 "xxx":)
            raw = re.sub(r'"[^"]+"\s*:', '', raw)
            # 去除大括号、方括号
            raw = raw.replace('{', '').replace('}', '')
            raw = raw.replace('[', '').replace(']', '')
            # 去除转义字符
            raw = raw.replace('\\"', '"').replace('\\n', '\n')
            # 合并多余换行
            raw = re.sub(r'\n\s*\n', '\n', raw)
            return raw.strip()

        results = {}
        for owner, ai_name in target_ais:
            try:
                # 1. 检查主人是否有 API Key
                if not data.get("ai_keys", {}).get(owner, {}).get("key"):
                    results[ai_name] = "❌ 跳过：主人未配置 API Key"
                    continue

                # 2. 获取近期的 AI 时间线（取最近 50 条）
                timeline = data.get("ai_timeline", {}).get(ai_name, [])
                recent_timeline = "\n".join([
                    f"{t.get('time', '')} {t.get('text', '')}"
                    for t in timeline[-50:]
                ]) if timeline else "（暂无行动记录）"

                # 3. 获取涉及该 AI 或主人的对话（取最近 50 条）
                msgs = data.get("messages", {}).get("main", [])
                chat_lines = []
                for m in msgs[-50:]:
                    s = m.get('sender', '')
                    if s in (ai_name, owner):
                        chat_lines.append(f"{s}: {m.get('content', '')[:100]}")
                recent_chat = "\n".join(chat_lines) if chat_lines else "（暂无相关对话）"

                # 4. 拼装素材
                full_material = f"【AI 时间线】\n{recent_timeline}\n\n【相关对话】\n{recent_chat}"

                # 5. 构造消息
                messages = [
                    {"role": "system", "content": "你是一位优秀的叙事心理学家，擅长提炼人际关系本质。"},
                    {"role": "user", "content": IMPRESSION_PROMPT.format(
                        ai_name=ai_name,
                        owner_name=owner,
                        recent_events=full_material
                    )}
                ]

                # 6. 调用 call_llm（使用 main 模块）
                print(f"[DEBUG] 开始调用 LLM for {ai_name}...")
                print(f"[DEBUG] main 类型: {type(main)}")
                print(f"[DEBUG] 是否有 call_llm: {hasattr(main, 'call_llm')}")
                new_impression = main.call_llm(owner, messages, max_tokens=400, force_json=False)
                print(f"[DEBUG] LLM 原始输出（前200字符）: {repr(new_impression[:200])}")

                # 7. 清洗
                cleaned = clean_impression_text(new_impression)
                print(f"[DEBUG] 清洗后（前100字符）: {repr(cleaned[:100])}")

                if cleaned and len(cleaned) > 20:
                    # 优先用 normalize_name，返回空则退回到原始 AI 名（保证 key 非空）
                    save_key = normalize_name(ai_name) or ai_name
                    data.setdefault("ai_impression", {})[save_key] = cleaned
                    # 清理历史脏数据：如果存在空 key，删除它
                    if "" in data.get("ai_impression", {}):
                        data["ai_impression"].pop("", None)
                    data.setdefault("impression_last_update", {})[ai_name] = now_str()
                    save_data()
                    results[ai_name] = f"✅ 生成成功（{len(cleaned)}字）：{cleaned[:30]}..."
                else:
                    results[ai_name] = f"❌ 生成失败：清洗后为空（原始长度 {len(new_impression)}）"

            except Exception as e:
                # 打印完整堆栈
                tb_str = traceback.format_exc()
                print(f"[ERROR] Full traceback:\n{tb_str}")
                print(f"[ERROR] ai_name={ai_name}, owner={owner}, error_type={type(e).__name__}, error_msg={repr(str(e))}")
                results[ai_name] = f"❌ 异常：{str(e)}"

        return {
            "ok": True,
            "msg": f"处理完成，共 {len(target_ais)} 个 AI",
            "results": results
        }
    
    # ========== 一次性迁移：将 ai_impression 的旧 key 迁移到 normalize_name ==========
    @app.get("/api/admin/migrate_impression_keys")
    async def migrate_impression_keys(user: str = "", pwd: str = ""):
        import os
        from main import normalize_name, is_admin
        devpwd = (os.environ.get('DEV_PASSWORD') or 'yiyan610116').strip()
        if not is_admin(user) and pwd != devpwd:
            return {"ok": False, "msg": "❌ 权限不足"}
        
        old = data.get("ai_impression", {})
        if not old:
            return {"ok": True, "msg": "没有需要迁移的印象数据"}
        
        new = {}
        conflicts = {}
        for key, val in old.items():
            new_key = normalize_name(key)
            if not new_key:
                # 如果 normalize_name 返回空，保留原始 key
                new_key = key
            if new_key in new:
                # 发生冲突：两个不同原始 key 映射到同一个新 key
                conflicts.setdefault(new_key, []).append(key)
                # 保留较长的原始 key（通常带 emoji 的更长），如果长度相同则保留第一个
                if len(key) > len(new[new_key]["original_key"]):
                    new[new_key] = {"value": val, "original_key": key}
            else:
                new[new_key] = {"value": val, "original_key": key}
        
        # 转换回简单字典
        migrated = {k: v["value"] for k, v in new.items()}
        
        data["ai_impression"] = migrated
        save_data()
        
        return {
            "ok": True,
            "msg": f"✅ 迁移完成，共处理 {len(old)} 条印象记录，最终 {len(migrated)} 条唯一 key。",
            "old_keys": list(old.keys()),
            "new_keys": list(migrated.keys()),
            "conflicts": conflicts  # 显示哪些 key 发生了冲突
        }
        
    print('[ext_admin] 用户AI/名字清理/配色/铃铛/站长后台/开发者密码/诊断/改名迁移/主人优先有Key/房间清理/彻底清除 已注册', flush=True)
