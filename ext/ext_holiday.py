# ext/ext_holiday.py
# 恋与临空 v2 节日/系统NPC插件（通用版）
# 支持农历节日自动转换（七夕、中秋、端午、春节）
# 支持公历节日（情人节、元旦）

import threading
import time
import random
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from pydantic import BaseModel
from main import room_time, save_data, now_str

# ---------- 尝试导入农历库 ----------
try:
    from lunardate import LunarDate
    LUNAR_AVAILABLE = True
except ImportError:
    LUNAR_AVAILABLE = False
    print("⚠️ [节日] lunardate 未安装，农历节日将使用公历日期")

# ---------- 全局变量 ----------
holiday_active = False
holiday_config = {}
holiday_multiplier = 1.0
_announcement_thread = None
_stop_thread = False

# ---------- 通用节日数据库（支持农历） ----------
HOLIDAYS_DB = {
    "七夕": {
        "lunar": "07-07",           # 农历七月初七
        "duration_days": 2,          # 持续 2 天（初七、初八）
        "multiplier": 2.8,
        "npc_pool": ["💫 鹊桥仙", "🕊️ 织女", "🐮 牛郎"],
        "firework_prob": 1.0,
        "context_prompt": "今天是{festival}，牛郎织女相会的日子。空气中弥漫着浪漫的气息，你应该更主动向心上人表达爱意，邀请约会、赠送礼物。",
        "announcements": [
            "{npc}：💞 {festival}佳节至，临空市的天空飘满了粉色爱心！",
            "{npc}：🌹 今日全城购物好感度+50%，约会成功率大幅提升！",
            "{npc}：💌 传说对着流星许言，相爱的人就能永远在一起。快邀请TA去约会吧！",
            "{npc}：🎋 今夜有烟花大会，适合情侣依偎共赏。",
            "{npc}：✨ {festival}特典：世界随机掉落'同心结'，捡到可获双倍好感！"
        ]
    },
    "情人节": {
        "date_range": ("02-14", "02-14"),
        "multiplier": 2.5,
        "npc_pool": ["💘 丘比特", "🌹 红玫瑰精灵"],
        "firework_prob": 1.0,
        "context_prompt": "今天是{festival}，空气中弥漫着巧克力和玫瑰的香气。很适合和喜欢的人约会、送礼物、说甜蜜的话。",
        "announcements": [
            "{npc}：💘 {festival}快乐！临空市中心飘满了爱心气球！",
            "{npc}：🍫 今日巧克力/鲜花类商品限时折扣，快去选购吧！",
            "{npc}：💌 向心仪的TA发送一封匿名情书，也许会有惊喜哦！",
            "{npc}：🎆 今晚玫瑰广场有浪漫灯光秀，最佳观赏时间是20:00！"
        ]
    },
    "中秋节": {
        "lunar": "08-15",           # 农历八月十五
        "duration_days": 1,
        "multiplier": 2.0,
        "npc_pool": ["🌙 嫦娥", "🐇 玉兔", "🌕 月老"],
        "firework_prob": 1.0,
        "context_prompt": "今天是{festival}，月圆人团圆。适合赏月、吃月饼、和家人或喜欢的人一起度过。",
        "announcements": [
            "{npc}：🌕 {festival}快乐！临空市的月亮今晚特别圆！",
            "{npc}：🥮 市集上架了特制月饼礼盒，快去买一份送给你在意的人吧！",
            "{npc}：🏮 临空河上飘满了河灯，许个愿吧，也许会实现！",
            "{npc}：🐇 玉兔偷偷告诉我，今晚在望月亭约会的人会收获双倍幸福。"
        ]
    },
    "端午节": {
        "lunar": "05-05",           # 农历五月初五
        "duration_days": 1,
        "multiplier": 1.6,
        "npc_pool": ["🐉 龙舟使者", "🌿 艾草仙", "🥚 粽子精灵"],
        "firework_prob": 1.0,
        "context_prompt": "今天是{festival}，空气中飘着粽叶的香气。适合划龙舟、吃粽子、系五彩绳。",
        "announcements": [
            "{npc}：🐉 {festival}安康！临空河上龙舟竞渡，快来观战！",
            "{npc}：🎋 家家户户挂起了艾草，驱邪纳福。",
            "{npc}：🥚 今日市集有新鲜出炉的蛋黄粽和豆沙粽，快去尝尝！",
            "{npc}：🌿 系上五彩绳，保佑一年平安顺遂。"
        ]
    },
    "元旦": {
        "date_range": ("01-01", "01-01"),
        "multiplier": 1.5,
        "npc_pool": ["🎊 新年使者", "🕊️ 希望之翼", "🌟 福星"],
        "firework_prob": 1.0,
        "context_prompt": "今天是{festival}，新的一年开始了。适合许下新年愿望，和对的人一起迎接未来。",
        "announcements": [
            "{npc}：🎉 {festival}快乐！临空市迎来了崭新的一年！",
            "{npc}：⏰ 零点钟声敲响，烟火照亮了整个夜空！",
            "{npc}：📝 在许愿墙上写下你的新年愿望吧，说不定会实现哦！",
            "{npc}：🍾 全城酒吧/咖啡馆推出新年特饮，一起去干杯吧！"
        ]
    },
    "春节": {
        "lunar": "01-01",           # 农历正月初一
        "duration_days": 7,         # 持续 7 天（初一到初七）
        "multiplier": 2.2,
        "npc_pool": ["🧧 财神爷", "🐲 龙年守护者", "🏮 灯神"],
        "firework_prob": 1.0,
        "context_prompt": "今天是{festival}，辞旧迎新，万家团圆。适合拜年、发红包、吃年夜饭、看烟花。",
        "announcements": [
            "{npc}：🧧 {festival}快乐！祝大家新的一年万事如意，财源广进！",
            "{npc}：🧨 临空市街头响起了鞭炮声，年味十足！",
            "{npc}：🥟 年夜饭活动开启！每家每户都在包饺子，快去蹭一顿！",
            "{npc}：🎆 今夜零时，全城将燃放迎春烟花，持续20分钟！"
        ]
    }
}


def get_lunar_date(year, month, day):
    """获取某天对应的农历日期"""
    if not LUNAR_AVAILABLE:
        return None
    try:
        return LunarDate.fromSolarDate(year, month, day)
    except Exception:
        return None


def find_lunar_start_date(year, lunar_month, lunar_day):
    """查找某年农历日期对应的公历日期"""
    if not LUNAR_AVAILABLE:
        return None
    try:
        # 遍历该年的每一天，找到农历匹配的日期
        # 农历正月初一通常在 1月21日~2月20日之间
        # 简单方法：遍历 1月20日 ~ 3月1日 之间足够覆盖所有农历节日
        start_date = datetime(year, 1, 15)
        end_date = datetime(year, 3, 1)
        # 对七夕（七月），需要扩展到 8月
        if lunar_month >= 7:
            start_date = datetime(year, 6, 1)
            end_date = datetime(year, 9, 1)
        # 对中秋（八月），扩展到 9月
        if lunar_month >= 8:
            start_date = datetime(year, 7, 1)
            end_date = datetime(year, 10, 1)
        current = start_date
        while current <= end_date:
            ld = get_lunar_date(current.year, current.month, current.day)
            if ld and ld.month == lunar_month and ld.day == lunar_day:
                return current
            current += timedelta(days=1)
        return None
    except Exception as e:
        print(f"[节日] 查找农历日期失败: {e}")
        return None


def get_current_holiday():
    """检测当前日期命中的第一个节日（支持农历）"""
    today = datetime.now()
    today_str = today.strftime("%m-%d")

    for name, cfg in HOLIDAYS_DB.items():
        # 农历节日
        if "lunar" in cfg:
            if not LUNAR_AVAILABLE:
                continue
            try:
                lunar_month, lunar_day = cfg["lunar"].split("-")
                lunar_month = int(lunar_month)
                lunar_day = int(lunar_day)

                # 获取今天的农历日期
                today_lunar = get_lunar_date(today.year, today.month, today.day)
                if not today_lunar:
                    continue

                # 检查今天的农历是否匹配
                if today_lunar.month == lunar_month and today_lunar.day == lunar_day:
                    return name, cfg

                # 检查是否在持续期内（从农历初七开始的 duration_days 天）
                # 查找今年的起始日期
                start_date = find_lunar_start_date(today.year, lunar_month, lunar_day)
                if start_date:
                    duration = cfg.get("duration_days", 1)
                    diff_days = (today - start_date).days
                    if 0 <= diff_days < duration:
                        return name, cfg
            except Exception as e:
                print(f"[节日] 农历节日检查失败 ({name}): {e}")
                continue

        # 公历节日（原逻辑）
        elif "date_range" in cfg:
            start, end = cfg["date_range"]
            if start <= today_str <= end:
                return name, cfg

    return None, None


def setup(app: FastAPI, data, helpers):
    global holiday_active, holiday_config, holiday_multiplier, _announcement_thread, _stop_thread

    name, cfg = get_current_holiday()

    if cfg:
        holiday_active = True
        holiday_config = cfg
        holiday_multiplier = cfg.get("multiplier", 1.0)

        npc_name = random.choice(cfg.get("npc_pool", ["🎉 节日使者"]))
        festival_name = name

        print(f"🎉 [节日系统] 检测到今日节日：{festival_name}，NPC：{npc_name}，概率加成 x{holiday_multiplier}")

        import main as m
        m.HOLIDAY_MULTIPLIER = holiday_multiplier
        m.HOLIDAY_CONTEXT = cfg.get("context_prompt", "").format(festival=festival_name)
        m.HOLIDAY_NAME = festival_name
        m.HOLIDAY_NPC = npc_name

        # ---------- 公告线程 ----------
        _stop_thread = False
        ann_templates = cfg.get("announcements", [])

        def announcement_worker():
            if not ann_templates:
                return
            while not _stop_thread:
                now_hour = datetime.now().hour
                if 8 <= now_hour <= 23:
                    template = random.choice(ann_templates)
                    msg = template.format(npc=npc_name, festival=festival_name)
                    try:
                        if 'main' in data.get('rooms', {}):
                            data.setdefault('messages', {}).setdefault('main', []).append({
                                'sender': 'system',
                                'content': f"📢 {msg}",
                                'role': 'system',
                                'time': now_str()
                            })
                            save_data()
                    except Exception as e:
                        print(f"公告发送失败: {e}")
                sleep_sec = random.randint(30 * 60, 60 * 60)
                time.sleep(sleep_sec)

        _announcement_thread = threading.Thread(target=announcement_worker, daemon=True)
        _announcement_thread.start()

        # ---------- 烟花系统 ----------
        data.setdefault("fireworks", {"active": False, "building_id": None, "end_ts": 0})

        FIREWORK_IDS = ["b99", "b46", "b43"]
        if FIREWORK_IDS:
            candidates = [bid for bid in FIREWORK_IDS if bid in data["buildings"]]
        else:
            candidates = [
                bid for bid, b in data["buildings"].items()
                if b.get("type") in ("npc", "nature") and
                any(f in ('date', 'fun', 'food') for f in (b.get('features') or []))
            ]

        def schedule_firework(building_id, duration_minutes=12):
            b = data["buildings"].get(building_id)
            if not b:
                print(f"❌ [烟花] 建筑 {building_id} 不存在")
                return
            b_name = b.get("name", "那座建筑")
            fw = data.setdefault("fireworks", {})
            fw["active"] = True
            fw["building_id"] = building_id
            fw["building_name"] = b_name
            fw["end_ts"] = time.time() + duration_minutes * 60
            save_data()
            print(f"🎇 [烟花] 已调度：{b_name}，持续 {duration_minutes} 分钟")

            notice_template = random.choice([
                "{npc}：🎆 烟花通告：今夜 {festival} 烟火，将在「{building}」绽放！持续约 {dur} 分钟，欢迎共赏！",
                "{npc}：✨ 浪漫烟花秀即将在「{building}」上演，持续 {dur} 分钟，不要错过！",
                "{npc}：🎇 全城注意！「{building}」上空将燃放 {festival} 特供烟花，约 {dur} 分钟！"
            ])
            notice = notice_template.format(
                npc=npc_name,
                festival=festival_name,
                building=b_name,
                dur=duration_minutes
            )

            try:
                if 'main' not in data.get('rooms', {}):
                    data.setdefault('rooms', {})['main'] = {
                        "creator": "system",
                        "has_password": False,
                        "password": "",
                        "created": now_str(),
                        "description": "城市的公共大厅，所有人都在这里聊天。"
                    }
                data.setdefault('messages', {}).setdefault('main', []).append({
                    'sender': 'system',
                    'content': notice,
                    'role': 'system',
                    'time': now_str()
                })
                save_data()
                print(f"📢 [烟花] 公告已写入 main 群聊")
            except Exception as e:
                print(f"❌ [烟花] 写入公告失败: {e}")

        def send_countdown_announcement(minutes_left, building_name):
            if minutes_left <= 0:
                return
            if minutes_left == 1:
                msg = f"⏰ {npc_name}：距离「{building_name}」烟花开始还有 1 分钟！快去占个好位置吧！"
            elif minutes_left <= 5:
                msg = f"⏰ {npc_name}：距离「{building_name}」烟花开始还有 {minutes_left} 分钟，抓紧时间哦！"
            elif minutes_left <= 10:
                msg = f"⏰ {npc_name}：距离「{building_name}」烟花开始还有 {minutes_left} 分钟，准备好去观赏了吗？"
            else:
                msg = f"⏰ {npc_name}：距离「{building_name}」烟花开始还有 {minutes_left} 分钟，记得准时来！"
            try:
                if 'main' in data.get('rooms', {}):
                    data.setdefault('messages', {}).setdefault('main', []).append({
                        'sender': 'system',
                        'content': msg,
                        'role': 'system',
                        'time': now_str()
                    })
                    save_data()
                print(f"⏰ [倒计时] 距离烟花开始还有 {minutes_left} 分钟")
            except Exception as e:
                print(f"❌ [倒计时] 发送失败: {e}")

        # ---------- 自动预约（今晚 22:00） ----------
        if candidates:
            target_bid = random.choice(candidates)
            b = data["buildings"][target_bid]
            b_name = b.get("name", "那座建筑")
            target_dt = datetime.now().replace(hour=22, minute=0, second=0, microsecond=0)
            delay = (target_dt - datetime.now()).total_seconds()
            if delay < 0:
                target_dt = target_dt.replace(day=target_dt.day + 1)
                delay = (target_dt - datetime.now()).total_seconds()
            if delay > 0:
                def trigger_job():
                    schedule_firework(target_bid, random.randint(10, 18))
                threading.Timer(delay, trigger_job).start()

                countdown_minutes = []
                for m in range(60, 10, -5):
                    countdown_minutes.append(m)
                for m in range(10, 0, -1):
                    countdown_minutes.append(m)

                now_ts = time.time()
                for target_minutes in countdown_minutes:
                    wait_sec = delay - (target_minutes * 60)
                    if wait_sec > 0:
                        def make_task(minutes):
                            def task():
                                send_countdown_announcement(minutes, b_name)
                            return task
                        threading.Timer(wait_sec, make_task(target_minutes)).start()
                        print(f"⏰ [倒计时] 已安排 {target_minutes} 分钟公告（{wait_sec:.0f} 秒后）")
                print(f"⏰ [烟花] 已预约今晚 22:00 在 {b_name} 放烟花，并安排了倒计时通告")
            else:
                schedule_firework(target_bid, random.randint(10, 18))

        # ---------- API ----------
        @app.get("/api/holiday/status")
        async def get_holiday_status():
            import main as m
            return {
                "active": holiday_active,
                "name": m.HOLIDAY_NAME if holiday_active else None,
                "npc": m.HOLIDAY_NPC if holiday_active else None,
                "multiplier": holiday_multiplier,
                "context": m.HOLIDAY_CONTEXT if holiday_active else "",
            }

        @app.get("/api/fireworks/status")
        async def get_fireworks_status():
            fw = data.get("fireworks", {})
            if fw.get("active") and time.time() > fw.get("end_ts", 0):
                fw["active"] = False
                save_data()
            return {
                "active": fw.get("active", False),
                "building_id": fw.get("building_id"),
                "building_name": fw.get("building_name", "")
            }

        @app.post("/api/fireworks/trigger")
        async def trigger_firework_manual(req: Request):
            try:
                body = await req.json()
            except:
                body = {}
            pwd = body.get('pwd', '')
            import os
            devpwd = (os.environ.get('DEV_PASSWORD') or 'yiyan610116').strip()
            if pwd != devpwd:
                return {"code": 403, "msg": "密码错误"}

            bid = body.get('building_id')
            if not bid or bid not in data["buildings"]:
                if candidates:
                    bid = random.choice(candidates)
                else:
                    return {"code": 400, "msg": "请提供有效的 building_id，且当前没有可用的烟花场地"}
            dur = body.get('duration', 12)
            schedule_firework(bid, dur)
            return {"code": 200, "msg": f"已手动触发 {data['buildings'][bid].get('name')} 的烟花"}

        print(f"🌺 [ext_holiday] 节日系统加载完成！当前节日：{festival_name}，主理NPC：{npc_name}")

    else:
        holiday_active = False
        holiday_multiplier = 1.0
        import main as m
        m.HOLIDAY_MULTIPLIER = 1.0
        m.HOLIDAY_CONTEXT = ""
        m.HOLIDAY_NAME = None
        m.HOLIDAY_NPC = None
        print("🎄 [节日系统] 今日无特殊节日，正常运行。")

        @app.get("/api/fireworks/status")
        async def get_fireworks_status():
            fw = data.get("fireworks", {})
            if fw.get("active") and time.time() > fw.get("end_ts", 0):
                fw["active"] = False
                save_data()
            return {
                "active": fw.get("active", False),
                "building_id": fw.get("building_id"),
                "building_name": fw.get("building_name", "")
            }
