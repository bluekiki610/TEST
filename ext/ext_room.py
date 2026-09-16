# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：房间 / 地图 / 建筑 / NPC / 权限 / 召唤 / 轨迹
# v2.9：restore 拒绝 main + 站长清大厅 / 召唤延迟到达 / 会客厅自动补齐 / 防缓存污染 / 大厅三时段背景 / 建筑背景
# v2.9.1：main 群聊消息截断 1000 条
# v3.0：住宅外观 / 玄关照片墙 / 玄关礼物房间（自动创建隐藏玄关）
import time
from fastapi import HTTPException


def setup(app, data, helpers):
    import main as m
    from main import (save_image_file, DATA_ROOT, next_bid, full_room_name, clean_room_name,
                      room_exists, find_building_of_room, now_str, save_data, is_admin,
                      is_ai_of, canonical_ai_name, owner_of_ai, append_timeline, append_visited, add_trail,
                      strip_emoji, resolve_building, room_time, can_view_room, online_room_count,
                      RegionIn, RegionDel, BuildingIn, BuildingMove, BuildingRename, BuildingDesc,
                      BuildingFeatures, BuildingNotice, BuildingDel, BuildingRoomIn, BuildingRoomDel,
                      RoomDescIn, RoomBgIn, NpcIn, NpcEdit, NpcDel, RoomApply, GrantIn, RevokeIn,
                      SummonIn, MessageIn, RestoreIn)

    def _ensure_hall(room):
        try:
            if not room or room == 'main' or not room.endswith('·会客厅'):
                return
            if find_building_of_room(room) is not None:
                return
            bname = room[:-len('·会客厅')]
            bid = resolve_building(bname)
            if not bid:
                return
            b = data['buildings'][bid]
            if room not in b.get('rooms', []):
                b.setdefault('rooms', []).append(room)
            data['rooms'][room] = {'creator': 'hall', 'has_password': False, 'password': '', 'created': now_str(), 'description': ''}
            data['messages'].setdefault(room, [])
            save_data()
            print(f'[ext_room] 自动补齐会客厅: {room}', flush=True)
        except Exception:
            pass

    def _save_img(val):
        if isinstance(val, str) and val.startswith('data:image'):
            p = save_image_file(DATA_ROOT / 'images' / 'bg', val)
            if p:
                return p
        return (val or '').strip()

    app.routes[:] = [r for r in app.routes if getattr(r, 'path', '') not in ('/api/messages', '/api/restore')]

    @app.get('/api/messages')
    async def get_messages(room: str = 'main', password: str = '', user: str = ''):
        try:
            room = clean_room_name(room)
            _ensure_hall(room)
            if not room_exists(room):
                raise HTTPException(404, '房间不存在')
            r = data['rooms'][room]
            if r.get('has_password') and r.get('password') != password:
                raise HTTPException(403, '密码错误')
            if not can_view_room(room, user):
                raise HTTPException(403, '没有权限查看这个房间')
            msgs = data['messages'].get(room, [])
            return {'messages': msgs[-300:]}
        except HTTPException:
            raise
        except Exception:
            return {'messages': []}

    @app.post('/api/messages')
    async def send_message(mm: MessageIn):
        room = clean_room_name(mm.room)
        _ensure_hall(room)
        if not room_exists(room):
            raise HTTPException(404, '房间不存在')
        r = data['rooms'][room]
        if r.get('has_password') and r.get('password') != mm.password:
            raise HTTPException(403, '密码错误')
        if not can_view_room(room, mm.sender):
            raise HTTPException(403, '没有权限进入这个房间')
        content = mm.content.strip()
        if not content:
            raise HTTPException(400, '消息不能为空')
        msg = {'sender': mm.sender, 'content': content[:1000], 'role': mm.role, 'time': room_time(room)}
        data['messages'].setdefault(room, []).append(msg)
        if room == 'main' and len(data['messages'][room]) > 1000:
            data['messages'][room] = data['messages'][room][-1000:]
        data['active_room']['current'] = room
        save_data()
        
        # ----- 新增：推送新消息给该房间在线的真人 -----
        try:
            if hasattr(app, 'push_event'):
                online_users = []
                # 获取当前在线用户（presence 字典已过滤 25 秒超时）
                for name, info in data.get('presence', {}).items():
                    if info.get('page') == room and not m.is_ai_name(name):
                        online_users.append(name)
                # 如果当前发消息的是真人，也推给他自己（多标签同步）
                if mm.role == 'user' and mm.sender not in online_users:
                    online_users.append(mm.sender)
                if online_users:
                    payload = {
                        'room': room,
                        'sender': mm.sender,
                        'content': content[:80]  # 只带摘要
                    }
                    for u in set(online_users):
                        app.push_event(u, 'new_message', payload)
        except Exception as e:
            print(f'[push] 推送新消息失败: {e}', flush=True)
        # ---------------------------
        
        if mm.role == 'user':
            try:
                m._maybe_wake_ai(room, mm.sender, content)
            except Exception:
                pass
        return {'ok': True, 'time': msg['time'], 'count': len(data['messages'][room])}

    @app.post('/api/restore')
    async def restore_messages(r: RestoreIn):
        room = clean_room_name(r.room)
        if room == 'main' or room.endswith('·会客厅') or find_building_of_room(room) is not None:
            return {'ok': True, 'added': 0}
        if not room_exists(room):
            return {'ok': False, 'reason': 'no_room'}
        rr = data['rooms'][room]
        if rr.get('has_password') and rr.get('password') != r.password:
            return {'ok': False, 'reason': 'bad_pwd'}
        cur = data['messages'].get(room, [])
        got = [mm for mm in r.messages if isinstance(mm, dict) and mm.get('sender') != 'system']
        cur_senders = {(mm.get('sender'), mm.get('content'), mm.get('time')) for mm in cur}
        added = 0
        for mm in got:
            key = (mm.get('sender'), mm.get('content'), mm.get('time'))
            if key not in cur_senders:
                cur.append({'sender': mm.get('sender', '?'), 'content': mm.get('content', ''), 'role': mm.get('role', 'user'), 'time': mm.get('time', now_str())})
                cur_senders.add(key)
                added += 1
        data['messages'][room] = cur[-500:]
        save_data()
        return {'ok': True, 'added': added}

    @app.get('/api/map')
    async def get_map():
        data['presence'] = {k: v for k, v in data.get('presence', {}).items() if isinstance(v, dict) and time.time() - v.get('ts', 0) < 25}
        return {
            'regions': data.get('regions', {}), 'buildings': data.get('buildings', {}), 'npcs': data.get('npcs', {}),
            'room_bg': data.get('room_bg', {}), 'rooms': data.get('rooms', {}),
            'room_access': data.get('room_access', {}), 'room_requests': data.get('room_requests', {}),
            'user_ais': data.get('user_ais', {}), 'work_sessions': data.get('work_sessions', {}),
            'home_jobs': data.get('home_jobs', {}),
            'ai_location': data.get('ai_location', {}),
            'ai_follow': data.get('ai_follow', {}),
            'ai_pending_moves': data.get('ai_pending_moves', {}),
            'hall_bg': data.get('hall_bg', {}),
            'presence': [{'name': k, 'page': v.get('page', 'main')} for k, v in data['presence'].items()],
        }

    @app.get('/api/hall_bg')
    async def get_hall_bg():
        return {'hall_bg': data.get('hall_bg', {})}

    @app.post('/api/hall_bg')
    async def set_hall_bg(bb: dict):
        import os
        devpwd = (os.environ.get('DEV_PASSWORD') or 'yiyan610116').strip()
        if not (is_admin((bb.get('user') or '').strip()) or (bb.get('pwd') or '') == devpwd):
            return {'ok': False, 'msg': '需要开发者权限'}
        hb = data.setdefault('hall_bg', {})
        for k in ('day', 'dusk', 'night'):
            v = bb.get(k)
            if isinstance(v, str) and v:
                hb[k] = _save_img(v)
        save_data()
        return {'ok': True, 'msg': '✅ 大厅三时段背景已保存', 'hall_bg': hb}

    @app.get('/api/building/bg')
    async def get_building_bg(building_id: str = ''):
        b = data['buildings'].get(building_id)
        return {'bg': (b or {}).get('bg', {})}

    @app.post('/api/building/bg')
    async def set_building_bg(bb: dict):
        import os
        devpwd = (os.environ.get('DEV_PASSWORD') or 'yiyan610116').strip()
        bid = (bb.get('building_id') or '').strip()
        b = data['buildings'].get(bid)
        if not b:
            return {'ok': False, 'msg': '建筑不存在'}
        user = (bb.get('user') or '').strip()
        is_creator = (b.get('owner') or '') == user or b.get('type') == 'npc'
        if not (is_admin(user) or (bb.get('pwd') or '') == devpwd or is_creator):
            return {'ok': False, 'msg': '只有站长或创建者可设置'}
        bg = b.setdefault('bg', {})
        v = bb.get('image')
        if isinstance(v, str) and v:
            bg['url'] = _save_img(v)
        try:
            op = float(bb.get('opacity'))
            bg['opacity'] = max(0.1, min(1.0, op))
        except Exception:
            pass
        save_data()
        return {'ok': True, 'msg': '✅ 建筑背景已更新', 'bg': bg}

    @app.post('/api/map/region')
    async def add_region(r: RegionIn):
        data['regions'][r.label] = {'x': r.x, 'y': r.y, 'image': r.image}
        save_data()
        return {'ok': True}

    @app.post('/api/map/region/delete')
    async def del_region(r: RegionDel):
        data['regions'].pop(r.label, None)
        save_data()
        return {'ok': True}

    @app.post('/api/map/building')
    async def add_building(b: BuildingIn):
        bid = next_bid()
        data['building_seq'] = max(data.get('building_seq', 1), int(bid[1:]))
        data['buildings'][bid] = {
            'name': b.name, 'emoji': b.emoji, 'type': b.type, 'region': b.region,
            'x': b.x, 'y': b.y, 'owner': b.owner, 'description': b.description,
            'rooms': [], 'salary': 0, 'features': [], 'notice': '',
        }
        if b.type == 'home':
            hall = b.name + '·会客厅'
            data['rooms'][hall] = {'creator': 'hall', 'has_password': False, 'password': '', 'created': now_str(), 'description': ''}
            data['messages'].setdefault(hall, [])
            data['buildings'][bid]['rooms'].append(hall)
            # 自动创建玄关房间（隐藏，不加入 rooms 列表）
            entrance = b.name + '·玄关'
            data['rooms'][entrance] = {'creator': 'home', 'has_password': False, 'password': '', 'created': now_str(), 'description': '玄关'}
            data['messages'].setdefault(entrance, [])
            # 不加入 rooms 列表，所以不会显示在房间门上
        save_data()
        return {'ok': True, 'building_id': bid}

    @app.post('/api/map/building/move')
    async def move_building(mm: BuildingMove):
        b = data['buildings'].get(mm.building_id)
        if not b:
            return {'ok': False}
        b['x'] = max(0, min(100, mm.x))
        b['y'] = max(0, min(100, mm.y))
        save_data()
        return {'ok': True}

    @app.post('/api/map/building/rename')
    async def rename_building(rr: BuildingRename):
        b = data['buildings'].get(rr.building_id)
        if not b:
            return {'ok': False}
        b['name'] = rr.name
        save_data()
        return {'ok': True}

    @app.post('/api/map/building/desc')
    async def building_desc(dd: BuildingDesc):
        b = data['buildings'].get(dd.building_id)
        if not b:
            return {'ok': False}
        b['description'] = dd.description
        save_data()
        return {'ok': True}

    @app.post('/api/map/building/features')
    @app.post('/api/building/features')
    async def building_features(ff: BuildingFeatures):
        b = data['buildings'].get(ff.building_id)
        if not b:
            return {'ok': False}
        b['features'] = ff.features
        b['salary'] = ff.salary
        save_data()
        return {'ok': True, 'msg': '功能已设置'}

    @app.post('/api/map/building/notice')
    @app.post('/api/building/notice')
    async def building_notice(nn: BuildingNotice):
        b = data['buildings'].get(nn.building_id)
        if not b:
            return {'ok': False}
        b['notice'] = nn.notice
        save_data()
        return {'ok': True, 'msg': '公告已更新'}

    @app.post('/api/map/building/delete')
    async def del_building(dd: BuildingDel):
        b = data['buildings'].pop(dd.building_id, None)
        if b:
            for r in b.get('rooms', []):
                data['rooms'].pop(r, None)
                data['messages'].pop(r, None)
                data['room_bg'].pop(r, None)
                data['room_access'].pop(r, None)
                data['room_requests'].pop(r, None)
            # 删除玄关房间
            entrance = b.get('name', '') + '·玄关'
            data['rooms'].pop(entrance, None)
            data['messages'].pop(entrance, None)
            data['npcs'].pop(dd.building_id, None)
            data['stories'].pop(dd.building_id, None)
        save_data()
        return {'ok': True}

    @app.post('/api/map/room')
    async def add_room(rr: BuildingRoomIn):
        b = data['buildings'].get(rr.building_id)
        if not b:
            return {'ok': False}
        raw = rr.name.strip()
        if not raw:
            return {'ok': False, 'msg': '房间名字不能为空'}
        bname = b.get('name', '')
        room = raw if (bname and raw.startswith(bname + '·')) else ((bname + '·' + raw) if bname else raw)
        if room in b.get('rooms', []):
            return {'ok': False, 'msg': '房间已存在'}
        data['rooms'][room] = {'creator': 'home', 'has_password': False, 'password': '', 'created': now_str(), 'description': ''}
        data['messages'].setdefault(room, [])
        b.setdefault('rooms', []).append(room)
        save_data()
        return {'ok': True, 'room': room}

    @app.post('/api/map/room/delete')
    async def delete_building_room(dd: BuildingRoomDel):
        bid, room = dd.building_id, dd.room
        room = full_room_name(room)
        b = data['buildings'].get(bid)
        if not b:
            return {'ok': False}
        if room in b.get('rooms', []):
            b['rooms'].remove(room)
        data['rooms'].pop(room, None)
        data['messages'].pop(room, None)
        data['room_bg'].pop(room, None)
        data['room_access'].pop(room, None)
        data['room_requests'].pop(room, None)
        data['notes'].pop(room, None)
        data['diaries'].pop(room, None)
        save_data()
        return {'ok': True}

    @app.post('/api/room/desc')
    async def room_desc(dd: RoomDescIn):
        room = full_room_name(dd.room)
        if room in data['rooms']:
            data['rooms'][room]['description'] = dd.description
        save_data()
        return {'ok': True}

    @app.get('/api/room/desc')
    async def get_room_desc(room: str = 'main'):
        room = clean_room_name(room)
        return {'description': data['rooms'].get(room, {}).get('description', '')}

    @app.post('/api/room/bg')
    async def room_bg(bb: RoomBgIn):
        val = bb.image or ''
        if val.startswith('data:image'):
            p = save_image_file(DATA_ROOT / 'images' / 'bg', val)
            if p:
                val = p
        data['room_bg'][bb.room] = val
        save_data()
        return {'ok': True, 'url': val}

    @app.post('/api/npc')
    async def add_npc(nn: NpcIn):
        data['npcs'].setdefault(nn.building_id, []).append({'name': nn.name, 'emoji': nn.emoji, 'desc': nn.desc})
        save_data()
        return {'ok': True}

    @app.post('/api/npc/edit')
    async def edit_npc(nn: NpcEdit):
        for npc in data['npcs'].get(nn.building_id, []):
            if npc['name'] == nn.name:
                npc['name'] = nn.new_name
                npc['emoji'] = nn.emoji
                npc['desc'] = nn.desc
                break
        save_data()
        return {'ok': True}

    @app.post('/api/npc/delete')
    async def del_npc(nn: NpcDel):
        data['npcs'][nn.building_id] = [x for x in data['npcs'].get(nn.building_id, []) if x['name'] != nn.name]
        save_data()
        return {'ok': True}

    @app.post('/api/room/apply')
    async def room_apply(aa: RoomApply):
        room = full_room_name(aa.room)
        reqs = data['room_requests'].setdefault(room, [])
        if not any(q.get('applicant') == aa.applicant for q in reqs):
            reqs.append({'applicant': aa.applicant, 'time': now_str()})
            save_data()
            return {'ok': True, 'msg': '申请已提交，等主人同意吧～'}
        return {'ok': True, 'msg': '你已经申请过了，等主人同意～'}

    @app.get('/api/room/requests')
    async def get_room_requests(room: str = ''):
        room = clean_room_name(room)
        return {'requests': data['room_requests'].get(room, [])}

    @app.post('/api/room/grant')
    async def room_grant(gg: GrantIn):
        room = full_room_name(gg.room)
        bid = find_building_of_room(room)
        if bid is None:
            return {'ok': False}
        if data['buildings'][bid].get('owner') != gg.owner:
            return {'ok': False, 'msg': '只有房主可以授权'}
        acc = data['room_access'].setdefault(room, [])
        if gg.allow:
            if gg.user not in acc:
                acc.append(gg.user)
            for ai in data['user_ais'].get(gg.user, []):
                if ai not in acc:
                    acc.append(ai)
        else:
            data['room_requests'].pop(room, None)
            data['room_access'][room] = [u for u in acc if u != gg.user and not is_ai_of(gg.user, u)]
        save_data()
        return {'ok': True}

    @app.post('/api/room/revoke')
    async def room_revoke(rr: RevokeIn):
        room = full_room_name(rr.room)
        bid = find_building_of_room(room)
        if bid is None:
            return {'ok': False}
        if data['buildings'][bid].get('owner') != rr.owner:
            return {'ok': False, 'msg': '只有房主可以移除'}
        acc = data['room_access'].get(room, [])
        data['room_access'][room] = [u for u in acc if u != rr.user and not is_ai_of(rr.user, u)]
        save_data()
        return {'ok': True}

    @app.post('/api/summon')
    async def summon(ss: SummonIn):
        room = clean_room_name(ss.room)
        ai = canonical_ai_name(ss.ai)
        caller = owner_of_ai(ai) or '有人'
        data['messages'].setdefault(room, []).append({'sender': 'system', 'content': f'📣 {caller} 在召唤 {ai} 去 {room}', 'role': 'system', 'time': m.room_time(room)})
        if ai in data.get('work_sessions', {}):
            data['work_sessions'].pop(ai, None)
            data.setdefault('work_switch', {})[ai] = False
            add_trail(ai, f'被 {caller} 召唤，从工作中离开')
        save_data()
        if ai:
            if hasattr(m, 'drive_ai') and m.ai_integration_enabled():
                cur = data.get('ai_location', {}).get(ai, 'main')
                if cur != room:
                    append_timeline(ai, f'{caller} 在 {room} 召唤你，你正在 {cur}，打算过去')
                import threading
                threading.Timer(1.0, m.drive_ai, args=(ai, 'summon', room, f'{caller} 召唤了你，快去 {room}')).start()
            else:
                data.setdefault('ai_location', {})[ai] = room
                append_timeline(ai, f'{caller} 召唤你来到了 {room}')
                append_visited(ai, room)
        return {'ok': True, 'msg': f'已召唤 {ai}！'}

    @app.get('/api/trails')
    async def get_trails(user: str):
        return {'trails': data['trails'].get(user, [])[-30:]}

    # ========== 住宅外观 & 照片墙 API ==========
    @app.post('/api/building/exterior')
    async def set_exterior(bb: dict):
        bid = bb.get('building_id')
        image = bb.get('image')
        if not bid or not image:
            return {'ok': False, 'msg': '缺少参数'}
        b = data['buildings'].get(bid)
        if not b:
            return {'ok': False, 'msg': '建筑不存在'}
        user = bb.get('user', '')
        if not is_admin(user) and b.get('owner') != user:
            return {'ok': False, 'msg': '无权限'}
        saved = _save_img(image)
        b['exterior_image'] = saved
        save_data()
        return {'ok': True, 'url': saved}

    @app.get('/api/building/exterior')
    async def get_exterior(building_id: str = ''):
        b = data['buildings'].get(building_id)
        return {'url': (b or {}).get('exterior_image', '')}

    @app.post('/api/building/entrance_photos')
    async def add_entrance_photo(bb: dict):
        bid = bb.get('building_id')
        image = bb.get('image')
        if not bid or not image:
            return {'ok': False, 'msg': '缺少参数'}
        b = data['buildings'].get(bid)
        if not b:
            return {'ok': False, 'msg': '建筑不存在'}
        user = bb.get('user', '')
        if not is_admin(user) and b.get('owner') != user:
            return {'ok': False, 'msg': '无权限'}
        saved = _save_img(image)
        photos = b.setdefault('entrance_photos', [])
        photo_id = str(int(time.time() * 1000)) + '_' + str(len(photos))
        photos.append({'id': photo_id, 'url': saved, 'time': now_str()})
        save_data()
        return {'ok': True, 'photo_id': photo_id, 'url': saved}

    @app.get('/api/building/entrance_photos')
    async def get_entrance_photos(building_id: str = ''):
        b = data['buildings'].get(building_id)
        return {'photos': (b or {}).get('entrance_photos', [])}

    @app.delete('/api/building/entrance_photos')
    async def delete_entrance_photo(building_id: str = '', photo_id: str = '', user: str = ''):
        b = data['buildings'].get(building_id)
        if not b:
            return {'ok': False, 'msg': '建筑不存在'}
        if not is_admin(user) and b.get('owner') != user:
            return {'ok': False, 'msg': '无权限'}
        photos = b.get('entrance_photos', [])
        b['entrance_photos'] = [p for p in photos if p.get('id') != photo_id]
        save_data()
        return {'ok': True}

    def _find_bid_local(key):
        key = (key or '').strip()
        if not key:
            return None
        if key in data.get('buildings', {}):
            return key
        for bid, b in data.get('buildings', {}).items():
            if b.get('name') == key or key in str(b.get('name', '')):
                return bid
        return None

    def _do_reset_building(user, key, pwd):
        import os
        devpwd = (os.environ.get('DEV_PASSWORD') or 'yiyan610116').strip()
        if not (is_admin(user) or (pwd and pwd == devpwd)):
            return {'ok': False, 'msg': '需要开发者权限'}
        bid = _find_bid_local(key)
        if not bid:
            return {'ok': False, 'msg': '建筑不存在，请用建筑id或建筑名'}
        b = data['buildings'][bid]
        rooms = b.get('rooms', [])
        for r in rooms:
            data.setdefault('messages', {}).pop(r, None)
        save_data()
        return {'ok': True, 'msg': f'已清空「{b.get("name")}」的 {len(rooms)} 个房间消息'}

    @app.get('/api/admin/reset_building')
    async def reset_building_get(user: str = '', bid: str = '', pwd: str = ''):
        return _do_reset_building(user, bid, pwd)

    @app.post('/api/admin/reset_building')
    async def reset_building_post(bb: dict):
        return _do_reset_building((bb.get('user') or '').strip(), (bb.get('bid') or '').strip(), (bb.get('pwd') or '').strip())

    @app.get('/api/admin/clear_main')
    async def clear_main(user: str = '', pwd: str = ''):
        import os
        devpwd = (os.environ.get('DEV_PASSWORD') or 'yiyan610116').strip()
        if is_admin(user) or (pwd and pwd == devpwd):
            data['messages']['main'] = []
            save_data()
            return {'ok': True, 'msg': '✅ 公共大厅消息已清空'}
        return {'ok': False, 'msg': '需要开发者权限'}

    print('[ext_room] 房间/地图/建筑/NPC/权限/召唤/轨迹 v3.0（住宅外观/玄关）已注册', flush=True)