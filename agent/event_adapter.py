"""
agent/event_adapter.py - P0-2B: First Real Event Adapter

职责：
- 从"用户发送消息"这一真实事实中提取信息
- 创建 message_received Event
- 旁路观察，不改变原聊天流程

硬性约束（依据裁决）：
1. 一条消息 = 一个 Event
2. Event.ai_name = None
3. target_ais 只是只读上下文
4. 不修改 main.data
5. 不调用 LLM / drive_ai / execute_action
6. 不接 EventBus / Scheduler / Wake / Brain / TTS
7. 不新增 Event Model 顶层字段
"""

import os
from typing import List, Optional
from agent.event import Event


def observe_message(
    sender: str,
    room: str,
    content: str,
    target_ais: List[str],
    message_id: Optional[str] = None,
) -> Event:
    """
    观察用户消息，创建一个 message_received Event。

    保证：
        - 1 次调用 = 1 个 Event
        - 不写入 main.data
        - 不触发任何行为
        - target_ais 被浅拷贝

    Returns:
        Event 对象。调用方可忽略返回值。
    """
    payload = {
        "sender": sender,
        "room": room,
        "content": content,
        "target_ais": list(target_ais) if target_ais else [],
    }
    if message_id is not None:
        payload["message_id"] = message_id

    event = Event(
        event_type="message_received",
        source="user",
        ai_name=None,
        payload=payload,
    )

    # P0-2B 验证期调试输出（由环境变量控制，测试后关闭）
    if os.getenv("P0_2B_DEBUG") == "1":
        print(f"[P0-2B] Event: {event.to_dict()}")

    return event
