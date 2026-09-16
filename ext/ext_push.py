# ext_push.py
import json
import asyncio
from fastapi import Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from main import app, data

# 全局连接池：key 是用户名，value 是该用户的所有队列（支持多开标签页）
_subscribers = {}

@app.get("/api/stream")
async def sse_stream(request: Request, user: str):
    """用户建立 SSE 长连接"""
    queue = asyncio.Queue()
    # 给这个用户注册一个队列
    if user not in _subscribers:
        _subscribers[user] = []
    _subscribers[user].append(queue)

    async def event_generator():
        try:
            while True:
                # 等待队列中有新消息
                data_payload = await queue.get()
                # 如果收到的是 None，表示连接要关闭
                if data_payload is None:
                    break
                yield {
                    "event": "update",      # 前端监听的事件名
                    "data": json.dumps(data_payload, ensure_ascii=False)
                }
        except asyncio.CancelledError:
            # 客户端断开连接
            pass
        finally:
            # 清理队列
            if user in _subscribers:
                _subscribers[user].remove(queue)
                if not _subscribers[user]:
                    del _subscribers[user]

    return EventSourceResponse(event_generator())


def push_event(user: str, event_type: str, payload: dict):
    """
    对外暴露的推送函数，供其他插件调用
    event_type: 'new_message' / 'new_sms' / 'new_notification'
    """
    if user not in _subscribers:
        return
    message = {"type": event_type, "payload": payload}
    # 给该用户的所有连接（多标签页）都推送
    for queue in _subscribers[user]:
        queue.put_nowait(message)


# 在插件加载时，挂载到 main 上供调用
app.push_event = push_event
print("[ext] 已加载主动推送 SSE 插件")
