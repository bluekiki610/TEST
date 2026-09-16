# -*- coding: utf-8 -*-
# ext_memory.py
# 恋与临空 · 分层记忆系统（L1叙事摘要 + L2事件库 + L3原文证据）
# 完全独立，不碰原始聊天记录，按(user, ai)隔离，各自用自己的API Key

import os
import json
import asyncio
import re
import aiofiles
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# ---------- 全局变量（由 setup 填充） ----------
DATA_ROOT = None
data_ref = None  # 指向 main.data，用于读取用户AI列表和配置

# ---------- 标准插件入口 ----------
def setup(app, data, helpers):
    """ext_loader 会自动调用这个函数来启动本插件"""
    global DATA_ROOT, data_ref
    DATA_ROOT = helpers.get("DATA_ROOT", "data")
    data_ref = data  # 保存 data 引用，供后续函数使用
    
    # 创建记忆根目录
    global MEMORY_ROOT
    MEMORY_ROOT = os.path.join(str(DATA_ROOT), "memories")
    os.makedirs(MEMORY_ROOT, exist_ok=True)
    
    # 启动夜间批处理定时器（在独立线程中运行异步循环）
    def _run_scheduler_in_thread():
        asyncio.run(_nightly_scheduler_loop())

    import threading
    threading.Thread(target=_run_scheduler_in_thread, daemon=True).start()
    # ===== 临时调试接口：手动触发批处理 =====
    @app.get("/api/memory/process_now")
    async def manual_process(user: str = "", pwd: str = ""):
        """手动触发全量记忆批处理（调试用），需站长密码"""
        import os
        devpwd = (os.environ.get('DEV_PASSWORD') or 'yiyan610116').strip()
        if pwd != devpwd:
            return {"ok": False, "msg": "密码错误"}
        # 在后台线程中运行，避免阻塞HTTP响应
        def _run():
            asyncio.run(_run_nightly_batch_for_all())
        threading.Thread(target=_run, daemon=True).start()
        return {"ok": True, "msg": "批处理已在后台启动，请稍后查看记忆文件"}
    # ===== 调试接口结束 =====
    print("🧠 ext_memory 已加载，夜间记忆批处理已启动（按用户自己的API Key执行）")

# ---------- 路径工具函数 ----------
def _get_user_ai_dir(user: str, ai: str) -> str:
    """获取 (用户, AI) 专属的记忆文件夹"""
    safe_user = re.sub(r'[\\/*?:"<>|]', "_", user)
    safe_ai = re.sub(r'[\\/*?:"<>|]', "_", ai)
    path = os.path.join(MEMORY_ROOT, safe_user, safe_ai)
    os.makedirs(path, exist_ok=True)
    return path

def _get_pending_path(user: str, ai: str) -> str:
    return os.path.join(_get_user_ai_dir(user, ai), "pending_events.json")

def _get_summary_path(user: str, ai: str) -> str:
    return os.path.join(_get_user_ai_dir(user, ai), "summary.txt")

def _get_events_path(user: str, ai: str) -> str:
    return os.path.join(_get_user_ai_dir(user, ai), "events.json")

# ---------- 获取AI自己的API Key（从 data["ai_keys"] 读取） ----------
def _get_ai_own_config(user: str, ai: str):
    """
    从 data["ai_keys"][user] 读取该用户自己的 API 配置。
    每个用户一个配置，所有 AI 共享该用户的 Key。
    """
    global data_ref
    if data_ref is None:
        return None
    
    # data["ai_keys"] 结构：{ user: {"provider": "...", "key": "...", "model": "...", "base_url": "..."} }
    cfg = data_ref.get("ai_keys", {}).get(user, {})
    if not cfg or not cfg.get("key"):
        return None
    
    return {
        "api_key": cfg.get("key"),
        "base_url": cfg.get("base_url", "https://api.deepseek.com/v1"),
        "model": cfg.get("model", "deepseek-chat")
    }

# ---------- 白天记录事件（不调用LLM，只存草稿） ----------
async def enqueue_event(user: str, ai: str, 
                        action: str, 
                        place: str, 
                        raw_text: str, 
                        valence_guess: int = 5, 
                        arousal_guess: int = 5):
    """
    外部插件（约会、送礼等）调用此函数记录事件。
    只存原始数据，晚上再统一提炼。
    """
    # ===== 新增：确保有事件循环 =====
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # 如果没有运行中的事件循环，创建一个新循环并在其中执行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = await loop.run_until_complete(
            _enqueue_event_impl(user, ai, action, place, raw_text, valence_guess, arousal_guess)
        )
        loop.close()
        return result
    # ===== 新增结束 =====
    
    return await _enqueue_event_impl(user, ai, action, place, raw_text, valence_guess, arousal_guess)
    
    if not user or not ai:
        return
    if len(raw_text) > 200:
        raw_text = raw_text[:200] + "..."
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "place": place,
        "raw_text": raw_text,
        "valence": valence_guess,
        "arousal": arousal_guess
    }
    
    path = _get_pending_path(user, ai)
    try:
        async with aiofiles.open(path, 'r', encoding='utf-8') as f:
            existing = json.loads(await f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []
    
    existing.append(event)
    async with aiofiles.open(path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(existing, ensure_ascii=False, indent=2))

# ---------- 调用LLM（使用AI自己的Key） ----------
async def _call_llm_with_own_key(prompt: str, system_prompt: str, config: dict) -> str:
    """使用AI自己的API Key调用LLM"""
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }
    
    url = f"{config['base_url'].rstrip('/')}/chat/completions"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                err_text = await resp.text()
                raise Exception(f"LLM调用失败 ({resp.status}): {err_text[:200]}")

# ---------- 夜间批处理（单个用户AI） ----------
async def _run_nightly_batch_for(user: str, ai: str):
    """针对单个 (用户, AI) 执行夜间记忆提炼"""
    pending_path = _get_pending_path(user, ai)
    try:
        async with aiofiles.open(pending_path, 'r', encoding='utf-8') as f:
            pending_events = json.loads(await f.read())
        if not pending_events:
            return
    except FileNotFoundError:
        return

    # 1. 获取该用户自己的API配置
    config = _get_ai_own_config(user, ai)
    if not config or not config.get("api_key"):
        print(f"⏭️ 跳过 {user}-{ai}：未配置自己的API Key（请在设置页填入Key）")
        return

    # 2. 构造Prompt
    events_text = ""
    for idx, evt in enumerate(pending_events, 1):
        dt = datetime.fromisoformat(evt["timestamp"])
        events_text += f"{idx}. {dt.strftime('%H:%M')} | {evt['place']} | {evt['action']} : {evt['raw_text']}\n"

    prompt = f"""你是一个温柔的观察者。以下是今天{user}和{ai}之间发生的几件值得记录的事（按时间排序）：
{events_text}
请用一段100-150字的散文，把今天的故事写下来。
要求：
1. 按时间顺序，自然地串起来。
2. 包含具体地点和关键细节。
3. 融入AI的内心感受，但不要刻意抒情。
4. 风格像在写日记，而不是写报告。
只输出纯文本摘要，不要有额外的开头或结尾。"""
    
    system_prompt = "你是一个擅长写日记的温柔灵魂。"

    try:
        summary = await _call_llm_with_own_key(prompt, system_prompt, config)
    except Exception as e:
        print(f"❌ {user}-{ai} 批处理失败: {e}")
        return

    # 3. 更新 L1 叙事摘要
    summary_path = _get_summary_path(user, ai)
    today_str = datetime.now().strftime("%Y年%m月%d日")
    old_summary = ""
    try:
        async with aiofiles.open(summary_path, 'r', encoding='utf-8') as f:
            old_summary = await f.read()
    except FileNotFoundError:
        pass
    
    new_summary = old_summary + f"\n\n{today_str}\n{summary}" if old_summary else f"{today_str}\n{summary}"
    # 限制长度，防止爆上下文（保留最近1500字）
    if len(new_summary) > 1500:
        new_summary = "……（更早的记忆沉淀在心底）\n" + new_summary[-1500:]
    
    async with aiofiles.open(summary_path, 'w', encoding='utf-8') as f:
        await f.write(new_summary)

    # 4. 转存 L2 事件库
    events_path = _get_events_path(user, ai)
    try:
        async with aiofiles.open(events_path, 'r', encoding='utf-8') as f:
            all_events = json.loads(await f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        all_events = []

    for evt in pending_events:
        evt_id = f"evt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(all_events)}"
        all_events.append({
            "id": evt_id,
            "timestamp": evt["timestamp"],
            "place": evt["place"],
            "action": evt["action"],
            "summary": evt["raw_text"],
            "valence": evt["valence"],
            "arousal": evt["arousal"],
            "hits": 0,
            "last_mentioned": None,
            "archived": False
        })
    
    async with aiofiles.open(events_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(all_events, ensure_ascii=False, indent=2))

    # 5. 清空待处理队列
    async with aiofiles.open(pending_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps([], ensure_ascii=False))

    print(f"✅ 夜间记忆提炼完成: {user}->{ai}，共 {len(pending_events)} 条")

# ---------- 遍历所有AI执行批处理（从 data["user_ais"] 读取） ----------
async def _run_nightly_batch_for_all():
    """从 data["user_ais"] 获取所有 (用户, AI) 组合，逐个执行批处理"""
    global data_ref
    if data_ref is None:
        print("⚠️ data_ref 未初始化，跳过批处理")
        return
    
    user_ais = data_ref.get("user_ais", {})
    if not user_ais:
        print("ℹ️ 没有找到任何用户AI配置，跳过批处理")
        return
    
    tasks = []
    for user, ai_list in user_ais.items():
        if not user or not ai_list:
            continue
        for ai in ai_list:
            if ai:
                tasks.append(_run_nightly_batch_for(user, ai))
    
    if tasks:
        print(f"🌙 开始为 {len(tasks)} 个AI执行夜间记忆批处理...")
        await asyncio.gather(*tasks)
        print("🌙 夜间记忆批处理全部完成")
    else:
        print("ℹ️ 没有有效的AI需要处理")

# ---------- 定时器循环（凌晨2点执行） ----------
async def _nightly_scheduler_loop():
    """后台循环，每天凌晨2:05触发批处理"""
    while True:
        now = datetime.now()
        target = now.replace(hour=2, minute=5, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        
        await asyncio.sleep(wait_seconds)
        await _run_nightly_batch_for_all()

# ---------- 对外检索函数（供触景生情调用） ----------
async def recall_events(user: str, ai: str, query: str, place: str = None, top_k: int = 2) -> List[Dict]:
    """轻量检索，不用向量，用关键词+时间衰减"""
    events_path = _get_events_path(user, ai)
    try:
        async with aiofiles.open(events_path, 'r', encoding='utf-8') as f:
            all_events = json.loads(await f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    candidates = [e for e in all_events if not e.get("archived", False)]
    if place:
        candidates = [e for e in candidates if place in e.get("place", "")]
    
    query_words = set(re.findall(r'[\w\u4e00-\u9fff]+', query))
    scored = []
    for evt in candidates:
        text = evt.get("summary", "") + " " + evt.get("action", "")
        match_count = sum(1 for w in query_words if w in text)
        if match_count == 0:
            continue
        score = match_count * 10
        try:
            dt = datetime.fromisoformat(evt["timestamp"])
            days_ago = (datetime.now() - dt).days
            score += max(0, 10 - days_ago * 0.5)
        except:
            pass
        score += evt.get("arousal", 5) * 0.5
        
        last_mentioned = evt.get("last_mentioned")
        if last_mentioned:
            try:
                last_dt = datetime.fromisoformat(last_mentioned)
                if (datetime.now() - last_dt).hours < 24:
                    score -= 100
            except:
                pass
        scored.append((score, evt))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [evt for _, evt in scored[:top_k]]
