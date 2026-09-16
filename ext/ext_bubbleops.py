# -*- coding: utf-8 -*-
# 恋与临空 气泡操作后端：删除消息（自己/房主/站长）+ AI 重新生成
import threading
from fastapi import HTTPException


def setup(app, data, helpers):
    import main as m
    from main import (clean_room_name, room_exists, find_building_of_room, is_admin,
                      is_ai_name, canonical_ai_name, owner_of_ai, save_data)

    # 覆盖删除接口：允许删自己发的（任意房间）+ 站长 + 房主
    app.routes[:] = [r for r in app.routes if getattr(r, 'path', '') != '/api/messages/delete']

    @app.post('/api/messages/delete')
    async def delete_message(dm: dict):
        room = clean_room_name((dm.get('room') or '').strip())
        user = (dm.get('user') or '').strip()
        if not room_exists(room):
            raise HTTPException(404, '房间不存在')
        msgs = data['messages'].get(room, [])
        target = [mm for mm in msgs if mm.get('sender') == dm.get('sender') and mm.get('content') == dm.get('content') and mm.get('time') == dm.get('time')]
        if not target:
            return {'ok': True, 'deleted': 0}
        bid = find_building_of_room(room)
        is_owner = bool(bid and data.get('buildings', {}).get(bid, {}).get('owner') == user)
        if not (dm.get('sender') == user or is_admin(user) or is_owner):
            raise HTTPException(403, '只能删除自己发的消息')
        before = len(msgs)
        data['messages'][room] = [mm for mm in msgs if not (mm.get('sender') == dm.get('sender') and mm.get('content') == dm.get('content') and mm.get('time') == dm.get('time'))]
        save_data()
        return {'ok': True, 'deleted': before - len(data['messages'][room])}

    # AI 重新生成：删除该条 AI 消息 + 重新驱动它说一遍
    @app.post('/api/ai/regenerate')
    async def ai_regenerate(body: dict):
        room = (body.get('room') or 'main').strip()
        ai = canonical_ai_name((body.get('ai') or '').strip())
        if not ai or not is_ai_name(ai):
            return {'ok': False, 'msg': '没有这个 AI'}
        owner = owner_of_ai(ai)
        msgs = data['messages'].get(room, [])
        content = body.get('content') or ''
        t = body.get('time') or ''
        before = len(msgs)
        data['messages'][room] = [mm for mm in msgs if not (mm.get('sender') == ai and mm.get('content') == content and mm.get('time') == t)]
        if len(data['messages'][room]) == before:
            return {'ok': False, 'msg': '没找到那条消息'}
        save_data()
        if owner and data.get('ai_keys', {}).get(owner, {}).get('key') and hasattr(m, 'drive_ai'):
            hint = f"主人让你重新说一遍刚才那句话（原话：{(content or '')[:40]}）"
            if room == 'main':
                threading.Timer(1.0, m.drive_ai, args=(ai, 'group', 'main', hint, '')).start()
            else:
                threading.Timer(1.0, m.drive_ai, args=(ai, 'chat', room, hint)).start()
        return {'ok': True, 'msg': '已重新生成'}

    print('[ext_bubbleops] 消息删除(自己/房主/站长) + AI 重新生成 已注册', flush=True)
