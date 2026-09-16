# -*- coding: utf-8 -*-
# 恋与临空 v2 插件：短信 / 通讯录
import random
import threading


def setup(app, data, helpers):
    import main as m
    from main import (canonical_contact_name, canonical_name, is_ai_name, split_sms,
                      now_str, append_timeline, save_data,
                      SmsIn, SmsClearIn)

    @app.get("/api/sms")
    async def get_sms(user: str):
        u = canonical_contact_name((user or '').strip())
        return {"sms": data["sms"].get(u, [])}

    @app.post("/api/sms")
    async def send_sms(ss: SmsIn):
        to = canonical_contact_name((ss.to or '').strip())
        sender = canonical_name((ss.sender or '').strip())
        if not ss.text.strip():
            return {"ok": False, "msg": "内容不能为空"}
        if not to or not sender:
            return {"ok": False, "msg": "缺少收件人或发件人"}
        msgs = split_sms(ss.text) if is_ai_name(sender) else [ss.text[:500]]
        for t in msgs:
            if t.strip():
                data["sms"].setdefault(to, []).append({"from": sender, "text": t[:500], "time": now_str()})
        data["sms"][to] = data["sms"][to][-200:]
        save_data()
        # ----- 新增：推送新短信给收件人（如果是在线真人）-----
        try:
            if hasattr(app, 'push_event') and not is_ai_name(to):
                # 检查收件人是否在线（presence 中 page 存在即可）
                if to in data.get('presence', {}):
                    app.push_event(to, 'new_sms', {
                        'from': sender,
                        'content': ss.text[:100]
                    })
        except Exception as e:
            print(f'[push] 推送短信失败: {e}', flush=True)
        # ---------------------------
        if hasattr(m, 'drive_ai') and m.ai_integration_enabled() and is_ai_name(to):
            append_timeline(to, f"{sender} 私信你：{ss.text[:60]}")
            delay = random.randint(60, 180)
            threading.Timer(delay, m.drive_ai, args=(to, "sms", "", f"{sender} 给你发来私信：{ss.text[:80]}", sender)).start()
        print(f"[SMS] {sender} → {to}（{len(msgs)} 条）: {ss.text[:80]}", flush=True)
        return {"ok": True, "to": to, "count": len(msgs)}

    @app.post("/api/sms/clear")
    async def clear_sms(ss: SmsClearIn):
        u = canonical_contact_name((ss.user or '').strip())
        c = canonical_contact_name((ss.contact or '').strip())
        if u in data["sms"]:
            data["sms"][u] = [mm for mm in data["sms"][u] if mm.get("from") != c]
        save_data()
        return {"ok": True}

    @app.get("/api/contacts")
    async def get_contacts():
        names = set()
        for b in data["buildings"].values():
            if b.get("owner"):
                names.add(b["owner"])
        for u, ais in data["user_ais"].items():
            if u:
                names.add(u)
            for a in ais:
                if a:
                    names.add(a)
        for msgs in data["sms"].values():
            for mm in msgs:
                if mm.get("from"):
                    names.add(mm["from"])
        names.discard("system")
        return {"contacts": sorted(n for n in names if n and n != "null")}

    print("[ext_sms] 短信/通讯录 已注册", flush=True)
