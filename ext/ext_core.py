# -*- coding: utf-8 -*-
# 恋与临空 后端核心插件：通知中心 / 图片同步(含图片) / 图片列表 / 前端插件列表 / 插件内容接口
# v2.6：load 接口加 ETag/304 —— 插件内容没变时浏览器复用缓存（不再每次重新下载全部插件），内容变了自动更新
# v2.7：sync_from_live 支持中文用户名 URL 编码
import json
import os
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
from fastapi import Request


def setup(app, data, helpers):
    import main as m

    try:
        from fastapi.staticfiles import StaticFiles
        _ext_dir = Path(__file__).resolve().parent
        if not any(getattr(r, 'path', None) == '/ext' for r in app.routes):
            app.mount('/ext', StaticFiles(directory=str(_ext_dir)), name='ext')
            print('[ext_core] /ext 静态目录已挂载', flush=True)
    except Exception as e:
        print(f'[ext_core] 挂载 /ext 失败: {e}', flush=True)

    # index.html 引用 /ext-loader.js（根目录静态文件），这里直接服务它（避免404导致所有前端插件不加载）
    @app.get('/ext-loader.js')
    async def ext_loader_js():
        from fastapi.responses import Response
        base = Path(__file__).resolve().parent.parent
        for cand in [base / 'ext-loader.js', Path(__file__).resolve().parent / 'ext-loader.js']:
            if cand.exists():
                return Response(content=cand.read_text(encoding='utf-8'), media_type='application/javascript',
                                headers={'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0'})
        return Response(content='// ext-loader.js not found；请把 ext-loader.js 放到仓库根目录（与 main.py 同层）', media_type='application/javascript')

    @app.get('/api/ext_js')
    async def ext_js():
        try:
            d = Path(__file__).resolve().parent
            files = sorted(p.name for p in d.glob('*.js'))
            return {'files': files}
        except Exception:
            return {'files': []}

    @app.get('/api/ext_js/load')
    async def ext_js_load(name: str = '', request: Request = None):
        from fastapi.responses import Response
        d = Path(__file__).resolve().parent
        if not name or not name.endswith('.js'):
            return {'ok': False, 'msg': 'bad name'}
        f = (d / name).resolve()
        if not str(f).startswith(str(d.resolve())):
            return {'ok': False, 'msg': 'bad name'}
        if not f.exists():
            return {'ok': False, 'msg': 'not found'}
        content = f.read_text(encoding='utf-8')
        etag = '"' + hashlib.md5(content.encode('utf-8')).hexdigest()[:16] + '"'
        inm = ''
        try:
            if request is not None and request.headers.get('if-none-match'):
                inm = request.headers.get('if-none-match', '')
        except Exception:
            pass
        if inm and inm == etag:
            return Response(status_code=304, headers={'ETag': etag, 'Cache-Control': 'no-cache, must-revalidate'})
        return Response(content=content, media_type='application/javascript',
                        headers={'ETag': etag, 'Cache-Control': 'no-cache, must-revalidate, max-age=0'})

    @app.get('/api/images_list')
    async def images_list():
        try:
            root = helpers['DATA_ROOT'] / 'images'
            files = []
            for p in sorted(root.rglob('*')):
                if p.is_file():
                    files.append({'path': str(p.relative_to(root)).replace(os.sep, '/')})
            return {'files': files}
        except Exception:
            return {'files': []}

    # ========== 移除可能重复的路由，然后注册 sync_from_live ==========
    app.routes[:] = [r for r in app.routes if getattr(r, 'path', '') != '/api/sync_from_live']

    @app.get('/api/sync_from_live')
    async def sync_from_live():
        live_url = os.environ.get('LIVE_SERVER', '').strip()
        if not live_url:
            return {'ok': False, 'msg': '❌ 未配置 LIVE_SERVER（请设正式服域名）'}
        if os.environ.get('ENABLE_SYNC') != '1':
            return {'ok': False, 'msg': '❌ 未开启 ENABLE_SYNC=1'}

        base = live_url.rstrip('/')
        # 从环境变量读取正式服管理员用户名和密码，如果没有则使用默认（正式服必须匹配）
        live_user = os.environ.get('LIVE_USER', '亦言❄️')
        live_pwd = os.environ.get('DEV_PASSWORD', 'yiyan610116')

        # 对中文用户名进行 URL 编码，防止 ASCII 编码错误
        user_encoded = urllib.parse.quote(live_user)
        pwd_encoded = urllib.parse.quote(live_pwd)

        try:
            # 请求正式服的 /api/backup，带上 user 和 pwd 参数
            req = urllib.request.Request(
                f"{base}/api/backup?user={user_encoded}&pwd={pwd_encoded}",
                headers={'User-Agent': 'linkong-sync'}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                live = json.loads(resp.read().decode('utf-8'))
            if not isinstance(live, dict):
                return {'ok': False, 'msg': '正式服返回格式不对'}

            # 同步图片
            img_downloaded = 0
            try:
                req2 = urllib.request.Request(base + '/api/images_list', headers={'User-Agent': 'linkong-sync'})
                with urllib.request.urlopen(req2, timeout=30) as resp2:
                    flist = json.loads(resp2.read().decode('utf-8'))
                img_root = (helpers['DATA_ROOT'] / 'images').resolve()
                for f in (flist.get('files') or []):
                    rel = f.get('path', '')
                    if not rel:
                        continue
                    try:
                        req3 = urllib.request.Request(base + '/images/' + rel.lstrip('/'), headers={'User-Agent': 'linkong-sync'})
                        with urllib.request.urlopen(req3, timeout=30) as resp3:
                            data_bytes = resp3.read()
                        dest = (img_root / rel).resolve()
                        if str(dest).startswith(str(img_root)):
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(data_bytes)
                            img_downloaded += 1
                    except Exception:
                        pass
            except Exception:
                pass

            # 合并数据
            data.clear()
            data.update(live)
            for k, v in helpers['default_data']().items():
                data.setdefault(k, v)
            helpers['sanitize_data']()
            helpers['migrate_room_prefix']()
            helpers['ensure_admin']()
            helpers['init_writing_rhythm']()
            helpers['migrate_images']()
            try:
                helpers['save_data']()
            except Exception:
                pass

            return {
                'ok': True,
                'msg': f"✅ 已从正式服同步！建筑 {len(data.get('buildings', {}))} 个，房间 {len(data.get('rooms', {}))} 个，图片 {img_downloaded} 张"
            }
        except Exception as e:
            return {'ok': False, 'msg': f'❌ 同步失败：{str(e)}'}

    @app.get('/api/notifications')
    async def notifications(user: str = ''):
        u = m.canonical_contact_name((user or '').strip())
        if not u:
            return {'notifications': []}
        mine = {u} | set(data.get('user_ais', {}).get(u, []))
        items = []
        for v in data.get('visits', {}).get(u, []):
            if v.get('who'):
                items.append({'type': 'visit', 'time': v.get('leave', ''), 'text': f"{v.get('who')} 来过你家（{v.get('action', '聊了天')}）"})
        for room, lst in data.get('notes', {}).items():
            bid = m.find_building_of_room(room)
            if bid is None or data.get('buildings', {}).get(bid, {}).get('owner') != u:
                continue
            for n in lst:
                if n.get('author') in mine:
                    continue
                items.append({'type': 'note', 'time': n.get('time', ''), 'text': f"{n.get('author')} 在你家{room}贴了张纸条：{n.get('text', '')[:40]}", 'room': room, 'building_id': bid})
        for room, lst in data.get('diaries', {}).items():
            bid = m.find_building_of_room(room)
            if bid is None or data.get('buildings', {}).get(bid, {}).get('owner') != u:
                continue
            for n in lst:
                if n.get('author') in mine:
                    continue
                items.append({'type': 'diary', 'time': n.get('time', ''), 'text': f"{n.get('author')} 在你家{room}写了随笔", 'room': room, 'building_id': bid})
        for room, reqs in data.get('room_requests', {}).items():
            bid = m.find_building_of_room(room)
            if bid is None or data.get('buildings', {}).get(bid, {}).get('owner') != u:
                continue
            for q in reqs:
                items.append({'type': 'request', 'time': q.get('time', ''), 'text': f"{q.get('applicant')} 申请进入你家的{room}", 'room': room, 'building_id': bid})
        for room, lst in data.get('notes', {}).items():
            for n in lst:
                if n.get('author') in mine and n.get('author') != u:
                    items.append({'type': 'ai_note', 'time': n.get('time', ''), 'text': f"🤖 {n.get('author')} 在{room}贴了张纸条：{n.get('text', '')[:40]}", 'room': room})
        for room, lst in data.get('diaries', {}).items():
            for n in lst:
                if n.get('author') in mine and n.get('author') != u:
                    items.append({'type': 'ai_diary', 'time': n.get('time', ''), 'text': f"🤖 {n.get('author')} 在{room}写了随笔", 'room': room})
        for bid, lst in data.get('stories', {}).items():
            for n in lst:
                if n.get('author') in mine and n.get('author') != u:
                    bname = data.get('buildings', {}).get(bid, {}).get('name', bid)
                    items.append({'type': 'ai_story', 'time': n.get('time', ''), 'text': f"🤖 {n.get('author')} 在{bname}写下了剧情：{n.get('text', '')[:40]}", 'building_id': bid})
        items.sort(key=lambda x: x.get('time', ''), reverse=True)
        return {'notifications': items[:100]}

    print('[ext_core] 通知/图片同步/插件列表/插件内容接口(ETag/304缓存) 已注册 (sync_from_live支持中文编码)', flush=True)