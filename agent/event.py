"""
agent/event.py - P0-2A: Minimal Event Model

硬性约束：
1. 纯数据模型：不修改 main.data，不调用 LLM，不触发行为。
2. 不持久化：不写数据库 / JSON / 文件。
3. 不接 EventBus / Scheduler / Wake / Brain / TTS。
4. 不修改任何现有文件。
5. 与 AgentState 严格区分：
   - AgentState = 现在是什么状态
   - Event     = 刚刚发生了什么

本阶段只提供：
- Event 数据类
- 自动 timestamp 生成
- to_dict() 序列化

不提供：EventBus、EventStore、EventHandler、EventQueue。
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Event:
    """
    最小事件模型（纯事实数据）。

    只描述"发生了什么"，不描述"接下来该做什么"。
    禁止承载 decision / next_action / brain_result / llm_prompt 等决策层内容。
    """

    # --- 必填字段 ---
    event_type: str
    # 例： "message_received" / "work_started" / "location_changed"
    #     / "date_started" / "gift_received" ...
    # P0-2A 不建立完整事件枚举体系，只保证字段可存。

    source: str
    # 例： "user" / "system" / "world" / "date" / "chat" / "shop" ...
    # P0-2A 不建立 Source Registry，只保证字段可存。

    # --- AI 标识（兼容当前系统命名方式）---
    ai_name: Optional[str] = None
    # 说明：当前项目尚未完成稳定 ai_id 体系，P0-2A 暂用 ai_name。
    # 禁止在本阶段重构现有 AI 标识结构。

    # --- 时间戳（Unix timestamp，未提供时自动生成）---
    timestamp: Optional[float] = None

    # --- 载荷（保持为普通可序列化数据）---
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为普通 dict，用于调试 / 未来传输。"""
        return {
            "event_type": self.event_type,
            "source": self.source,
            "ai_name": self.ai_name,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }

    def __repr__(self) -> str:
        return (
            f"Event(type={self.event_type!r}, "
            f"source={self.source!r}, "
            f"ai={self.ai_name!r}, "
            f"ts={self.timestamp})"
        )
