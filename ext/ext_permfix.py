# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：私密房间权限申请兜底清理（通过/授权后申请自动消失）
# 原因：审批接口实现在 ext_room，通过后可能没从 room_requests 移除申请，
#      导致前端一直看到「待处理」。本插件每 5 秒清理「已授权但还在申请列表」的用户。
import time
import threading


def setup(app, data, helpers):
    from main import save_data, strip_emoji

    def _key(u):
        if isinstance(u, dict):
            u = u.get('user') or u.get('applicant') or u.get('name') or u.get('who') or ''
        return strip_emoji(str(u or ''))

    def cleanup():
        try:
            changed = False
            reqs = data.get('room_requests', {})
            accs = data.get('room_access', {})
            if not isinstance(reqs, dict) or not isinstance(accs, dict):
                return
            for room, req_list in list(reqs.items()):
                if not isinstance(req_list, list):
                    reqs[room] = []
                    continue
                acc_list = accs.get(room)
                if not isinstance(acc_list, list):
                    continue
                granted = {_key(x) for x in acc_list}
                if not granted:
                    continue
                new_list = [r for r in req_list if _key(r) not in granted]
                if len(new_list) != len(req_list):
                    reqs[room] = new_list
                    changed = True
            if changed:
                save_data()
        except Exception:
            pass

    def loop():
        while True:
            try:
                cleanup()
            except Exception:
                pass
            time.sleep(5)  # 每 5 秒兜底一次，通过后申请很快消失

    @app.get('/api/perm/cleanup')
    async def perm_cleanup(user: str = ''):
        from main import is_admin
        if not is_admin(user):
            return {'ok': False, 'msg': '只有站长可以手动清理'}
        cleanup()
        return {'ok': True, 'msg': '✅ 已清理已授权的申请'}

    threading.Thread(target=loop, daemon=True).start()
    print('[ext_permfix] 权限申请兜底清理已注册（每5秒）', flush=True)
