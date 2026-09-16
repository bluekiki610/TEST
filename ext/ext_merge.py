# -*- coding: utf-8 -*-
# 一次性合并工具：把某个「基础名」的所有 emoji 变体统一到目标名（站长+开发者密码）
# 例：把 亦言❄ / 亦言❄️ 等所有 strip_emoji==亦言 的名字统一为 亦言❄️
# 覆盖字段：登记/Key/人设/画像/知识库/注入/记忆/通知/短信/消息/便签/日记/剧情/钱包/工作/轨迹/在线/头像/配对/授权/跟随
import os
from fastapi import HTTPException


def setup(app, data, helpers):
    import main as m
    from main import strip_emoji

    def _base(s):
        return strip_emoji(s or '')

    def _do_merge(user, pwd, base, target):
        devpwd = (os.environ.get('DEV_PASSWORD') or 'yiyan610116').strip()
        if not (m.is_admin(user) or (pwd and pwd == devpwd)):
            raise HTTPException(403, '需要站长权限')
        if not base:
            return {'ok': False, 'msg': '需要 base'}
        if not target:
            target = data.get('pairs_admin') or '亦言❄️'
        if _base(target) != base:
            return {'ok': False, 'msg': 'target 的基础名不等于 base'}
        changed = {}
        variants_found = []

        def merge_dict_key(key):
            d = data.get(key)
            if not isinstance(d, dict):
                return
            src = [k for k in d if k != target and _base(k) == base]
            if not src:
                return
            for s in src:
                variants_found.append({'name': s, 'code': [hex(ord(c)) for c in s], 'len': len(s)})
                if s not in d:
                    continue
                val = d.pop(s)
                if isinstance(val, list):
                    cur = d.setdefault(target, [])
                    for it in val:
                        if it not in cur:
                            cur.append(it)
                elif isinstance(val, dict):
                    cur = d.setdefault(target, {})
                    cur.update({k2: v2 for k2, v2 in val.items() if k2 not in cur})
                else:
                    if target not in d:
                        d[target] = val
                changed[key] = changed.get(key, 0) + 1

        for k in ['user_ais', 'ai_keys', 'ai_profiles', 'user_profiles', 'worldbook', 'prompt_injections',
                  'ai_memories', 'notifications', 'wallets', 'home_jobs', 'work_sessions', 'work_switch',
                  'visits', 'trails', 'presence', 'online', 'avatars']:
            merge_dict_key(k)

        def fix_field_in_list(lst, field):
            n = 0
            if not isinstance(lst, list):
                return n
            for it in lst:
                if isinstance(it, dict) and it.get(field) and _base(it.get(field)) == base and it.get(field) != target:
                    it[field] = target
                    n += 1
            return n

        for room, lst in data.get('messages', {}).items():
            changed['messages'] = changed.get('messages', 0) + fix_field_in_list(lst, 'sender')
        for room, lst in data.get('notes', {}).items():
            changed['notes'] = changed.get('notes', 0) + fix_field_in_list(lst, 'author')
        for room, lst in data.get('diaries', {}).items():
            changed['diaries'] = changed.get('diaries', 0) + fix_field_in_list(lst, 'author')
        for bid, lst in data.get('stories', {}).items():
            changed['stories'] = changed.get('stories', 0) + fix_field_in_list(lst, 'author')

        # sms：key 是收件人 + 消息里的 from
        sms_d = data.get('sms')
        if isinstance(sms_d, dict):
            src = [k for k in sms_d if k != target and _base(k) == base]
            for s in src:
                variants_found.append({'name': s, 'code': [hex(ord(c)) for c in s], 'len': len(s)})
                cur = sms_d.setdefault(target, [])
                for it in sms_d.pop(s, []):
                    if isinstance(it, dict) and it.get('from') and _base(it.get('from')) == base and it.get('from') != target:
                        it['from'] = target
                    if it not in cur:
                        cur.append(it)
                changed['sms'] = changed.get('sms', 0) + 1

        # pairs：配对名单里的名字
        if isinstance(data.get('pairs'), list):
            for p in data['pairs']:
                if not isinstance(p, dict):
                    continue
                if isinstance(p.get('names'), list):
                    p['names'] = [target if (_base(x) == base and x != target) else x for x in p['names']]
                if p.get('owner') and _base(p.get('owner')) == base and p.get('owner') != target:
                    p['owner'] = target
                changed['pairs'] = changed.get('pairs', 0) + 1

        # 房间授权 / 申请
        for room, acc in data.get('room_access', {}).items():
            if isinstance(acc, list):
                acc[:] = [target if (_base(x) == base and x != target) else x for x in acc]
        for room, reqs in data.get('room_requests', {}).items():
            if isinstance(reqs, list):
                for q in reqs:
                    if isinstance(q, dict) and q.get('applicant') and _base(q.get('applicant')) == base and q.get('applicant') != target:
                        q['applicant'] = target

        # 跟随
        for ai, fl in data.get('ai_follow', {}).items():
            if isinstance(fl, dict) and fl.get('owner') and _base(fl.get('owner')) == base and fl.get('owner') != target:
                fl['owner'] = target

        # 站长名
        if data.get('pairs_admin') and _base(data.get('pairs_admin')) == base and data.get('pairs_admin') != target:
            data['pairs_admin'] = target

        helpers['save_data']()
        return {'ok': True, 'msg': f'已将「{base}」所有变体统一为「{target}」', 'changed': changed, 'variants': variants_found}

    @app.get('/api/admin/merge_name_base')
    async def merge_name_base_get(user: str = '', pwd: str = '', base: str = '', target: str = ''):
        return _do_merge(user, pwd, base, target)

    @app.post('/api/admin/merge_name_base')
    async def merge_name_base_post(body: dict):
        return _do_merge((body.get('user') or '').strip(), (body.get('pwd') or '').strip(),
                         (body.get('base') or '').strip(), (body.get('target') or '').strip())

    print('[ext_merge] 姓名 emoji 变体一键合并工具 已注册（/api/admin/merge_name_base）', flush=True)
