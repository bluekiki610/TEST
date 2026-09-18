"""
agent/runtime.py - P0-3B: Agent Runtime - First Real Perception Chain

P0-3A 定义了 Contract（Stub）。
P0-3B 第一次让 Runtime 真正处理 Event：
    Event → receive_event() → perceive() → should_wake() → IGNORE / OBSERVE

但本阶段仍然：
1. 0 次 LLM 调用
2. 不修改 main.data
3. 不进入 CONTEXT / THINK / DECISION / ACTION
4. 不建立 EventBus / EventStore / Scheduler
5. 不替代旧 Wake（旧 Wake 保持原样）

生命周期（P0-3B 只覆盖前 3 阶段）：
    1. RECEIVE        ✅ P0-3B 已实现
    2. PERCEIVE       ✅ P0-3B 已实现
    3. WAKE_DECISION  ✅ P0-3B 已实现（只返回 IGNORE / OBSERVE）
    4. CONTEXT        ❌ 仍是 P0-3A Stub
    5. THINK          ❌ 仍是 P0-3A Stub（绝不调 LLM）
    6. DECISION       ❌ 仍是 P0-3A Stub
    7. ACTION         ❌ 仍是 P0-3A Stub
    8. WORLD_CHANGE   —— 由现有 ext_* 负责（未改动）
    9. EVENT          —— 由 P0-2B Adapter 负责（未改动）
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from collections import deque

from agent.event import Event
from agent.state import AgentState, get_agent_state


# =========================================================
# 1. Wake Decision 枚举（P0-3A 保留）
# =========================================================
class WakeDecision(str, Enum):
    """
    Agent 对一个 Event 的唤醒决策。

    P0-3B 只返回 IGNORE / OBSERVE，不返回 THINK。
    """
    IGNORE = "ignore"
    OBSERVE = "observe"
    THINK = "think"  # 保留枚举，但 P0-3B 不产生


# =========================================================
# 2. Context 分层（P0-3A 保留，P0-3B 未使用）
# =========================================================
@dataclass
class ContextLayers:
    stable_core: Dict[str, Any] = field(default_factory=dict)
    recent: Dict[str, Any] = field(default_factory=dict)
    long_term: Dict[str, Any] = field(default_factory=dict)
    dynamic_world: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# 3. Decision 结构（P0-3A 保留，P0-3B 未使用）
# =========================================================
@dataclass
class Decision:
    action_type: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None
    confidence: Optional[float] = None
    _stub: bool = True


# =========================================================
# 4. PerceptionResult（P0-3B 新增）
# =========================================================
@dataclass
class PerceptionResult:
    """
    P0-3B: 一个 Event 被一个 AI 处理后的结构化结果。

    语义边界：
    - 描述"这个 Event 对这个 AI 是否相关"
    - 描述"是否值得进一步处理（OBSERVE）"
    - 不描述"AI 接下来要做什么"（那是 Decision）
    """
    ai_name: str
    event_type: str
    perceived: bool
    wake_decision: WakeDecision
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ai_name": self.ai_name,
            "event_type": self.event_type,
            "perceived": self.perceived,
            "wake_decision": self.wake_decision.value,
            "reason": self.reason,
        }


# =========================================================
# 5. 常量
# =========================================================
MAX_RECENT_EVENTS = 20
# 极小的本地环形缓冲，防止 Runtime 内存无限增长。
# 注意：这不是 EventStore，不持久化，不共享，不查询。


# =========================================================
# 6. AgentRuntime
# =========================================================
class AgentRuntime:
    """
    单个 AI 的 Agent Runtime。

    原则：
    - 一个 AI 一个 Runtime 实例
    - Runtime 只编排，不复制 ext_* 能力
    - Runtime 不修改 World

    P0-3B 状态：
    - receive_event / perceive / should_wake：已实现（确定性规则）
    - build_context / think / decide / execute：仍为 P0-3A Stub
    """

    def __init__(self, ai_name: str, data: Dict[str, Any]):
        self.ai_name = ai_name
        self._data = data
        # 环形缓冲：maxlen 自动截断，不会无限增长
        self._recent_events: deque = deque(maxlen=MAX_RECENT_EVENTS)

    # -----------------------------------------------------
    # 生命周期：RECEIVE → PERCEIVE → WAKE_DECISION
    # -----------------------------------------------------
    def receive_event(self, event: Event) -> PerceptionResult:
        """
        接收一个 Event，并立即执行感知 + Wake Decision。

        保证：
        - 不建立 EventStore
        - 不持久化
        - 不修改 main.data
        - 不调用 LLM
        - 不触发旧 Wake（旧 Wake 独立运行）
        """
        # 1. 存入小型环形缓冲（maxlen 自动截断）
        if event is not None:
            self._recent_events.append({
                "event_type": event.event_type,
                "source": event.source,
                "ai_name": event.ai_name,
                "timestamp": event.timestamp,
            })

        # 2. 感知
        perceived = self.perceive(event)

        # 3. Wake Decision
        wake = self.should_wake(event, perceived)

        # 4. 结构化返回
        return PerceptionResult(
            ai_name=self.ai_name,
            event_type=(event.event_type if event else ""),
            perceived=perceived,
            wake_decision=wake,
            reason=self._explain(event, perceived),
        )

    # -----------------------------------------------------
    # PERCEIVE（确定性规则）
    # -----------------------------------------------------
    def perceive(self, event: Event) -> bool:
        """
        确定性相关性规则（P0-3B 第一版）：

        1. message_received:
             payload.target_ais 包含 self.ai_name → True
             否则 → False（不猜测）

        2. message_sent:
             event.ai_name == self.ai_name → True
             否则 → False

        3. 通用：event.ai_name 明确 == self.ai_name → True

        4. 默认：False
        """
        if event is None:
            return False

        et = event.event_type or ""

        # 规则 1：message_received
        if et == "message_received":
            payload = event.payload or {}
            targets = payload.get("target_ais") or []
            if not isinstance(targets, (list, tuple)):
                return False
            return self.ai_name in targets

        # 规则 2：message_sent
        if et == "message_sent":
            return event.ai_name == self.ai_name

        # 规则 3：通用——明确指向本 AI 的 Event
        if event.ai_name and event.ai_name == self.ai_name:
            return True

        # 默认：不感知
        return False

    # -----------------------------------------------------
    # WAKE DECISION（P0-3B 最小规则）
    # -----------------------------------------------------
    def should_wake(
        self,
        event: Event,
        perceived: Optional[bool] = None,
    ) -> WakeDecision:
        """
        P0-3B 最小规则：

        未感知 → IGNORE
        已感知 → OBSERVE

        ⚠️ 不自动返回 THINK。
        未来（P0-3C+）：Event importance + AgentState + Relationship
              + Activity + Need + Cooldown + Budget → 决定 THINK
        """
        if perceived is None:
            perceived = self.perceive(event)
        return WakeDecision.OBSERVE if perceived else WakeDecision.IGNORE

    # -----------------------------------------------------
    # 剩余方法（P0-3A Stub 保留，P0-3B 未实现）
    # -----------------------------------------------------
    def build_context(self, event: Event) -> ContextLayers:
        """P0-3A Stub 保留。P0-3B 不实现。"""
        return ContextLayers()

    def think(self, context: ContextLayers) -> Optional[str]:
        """P0-3A Stub 保留。P0-3B 绝不调用 LLM。"""
        return None

    def decide(self, thought: Optional[str]) -> Optional[Decision]:
        """P0-3A Stub 保留。P0-3B 不实现。"""
        return None

    def execute(self, decision: Optional[Decision]) -> bool:
        """P0-3A Stub 保留。P0-3B 不实现。"""
        return False

    # -----------------------------------------------------
    # 辅助
    # -----------------------------------------------------
    def get_state(self) -> Optional[AgentState]:
        """透传 P0-1 能力（只读）"""
        return get_agent_state(self.ai_name, self._data)

    def recent_events_count(self) -> int:
        """测试用：验证环形缓冲不会无限增长"""
        return len(self._recent_events)

    def _explain(self, event: Optional[Event], perceived: bool) -> str:
        """可读的理由，用于调试 / 测试"""
        if event is None:
            return "Event is None"
        et = event.event_type or ""
        if not perceived:
            if et == "message_received":
                return "target_ais 不含本 AI"
            if et == "message_sent":
                return "发送者不是本 AI"
            if event.ai_name:
                return f"Event 指向 {event.ai_name}，不是本 AI"
            return "Event 未指向本 AI"
        return f"{et} 与本 AI 相关"


# =========================================================
# 7. Runtime 工厂
# =========================================================
def get_runtime(ai_name: str, data: Dict[str, Any]) -> AgentRuntime:
    """
    获取某个 AI 的 AgentRuntime 实例。

    P0-3B 保持"每次新建"（无缓存），符合 P0-3A Contract。
    未来可能引入缓存，但保持"一个 AI 一个 Runtime"的原则。
    """
    return AgentRuntime(ai_name, data)
P0_STEP3B_PERCEPTION_CHAIN: implement first real perceive + should_wake
