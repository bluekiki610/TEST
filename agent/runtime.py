"""
agent/runtime.py - P0-3B + B5-2: Agent Runtime

P0-3A 定义了 Contract（Stub）。
P0-3B 第一次让 Runtime 真正处理 Event：
    Event → receive_event() → perceive() → should_wake() → IGNORE / OBSERVE

B5-2 连接 ContextAssembler：
    build_context(event, now_ts=None) → ContextAssembler → AgentContext

但本阶段仍然：
1. 0 次 LLM 调用
2. 不修改 main.data
3. 不进入 THINK / DECISION / ACTION
4. 不建立 EventBus / EventStore / Scheduler
5. 不替代旧 Wake（旧 Wake 保持原样）

生命周期：
    1. RECEIVE        ✅ P0-3B 已实现
    2. PERCEIVE       ✅ P0-3B 已实现
    3. WAKE_DECISION  ✅ P0-3B 已实现（只返回 IGNORE / OBSERVE）
    4. CONTEXT        ✅ B5-2 已连接 ContextAssembler（返回 AgentContext）
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
from agent.context import AgentContext
from agent.context_assembler import ContextAssembler
from agent.stable_core_provider import StableCoreProvider
from agent.recent_provider import RecentProvider
from agent.long_term_provider import LongTermProvider
from agent.dynamic_world_provider import DynamicWorldProvider


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
# 2. Context 分层（P0-3A 保留，已 DEPRECATED）
# =========================================================
@dataclass
class ContextLayers:
    """
    P0-3A ContextLayers —— DEPRECATED compatibility stub.

    B5-1 Contract Change CC-20260926-01 正式废弃本结构：
    - 不删除
    - 不改名
    - 不别名化（不允许 ContextLayers = AgentContext）
    - 新 V3.1 链不再引用

    V3.1 唯一正式 Context 数据结构 = AgentContext（agent/context.py）。
    """
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
    - build_context：B5-2 已连接 ContextAssembler，返回 AgentContext
    - think / decide / execute：仍为 P0-3A Stub
    """

    def __init__(
        self,
        ai_name: str,
        data: Dict[str, Any],
        context_assembler: Optional[ContextAssembler] = None,
    ):
        """
        Args:
            ai_name:           AI 名字
            data:              main.data 只读引用（不透明传递）
            context_assembler: 可选注入；不传则由 Runtime 自行构造默认 Assembler
        """
        self.ai_name = ai_name
        self._data = data
        # 环形缓冲：maxlen 自动截断，不会无限增长
        self._recent_events: deque = deque(maxlen=MAX_RECENT_EVENTS)

        # B5-2: 连接 ContextAssembler（Dependency Injection）
        if context_assembler is None:
            context_assembler = ContextAssembler(
                stable_core_provider=StableCoreProvider(),
                recent_provider=RecentProvider(),
                long_term_provider=LongTermProvider(),
                dynamic_world_provider=DynamicWorldProvider(),
            )
        self._context_assembler = context_assembler

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
    # CONTEXT（B5-2 已连接 ContextAssembler）
    # -----------------------------------------------------
    def build_context(
        self,
        event: Event,
        now_ts: Optional[float] = None,
    ) -> AgentContext:
        """
        CONTEXT 阶段：把四个 Provider 组装成统一 AgentContext。

        B5-2：连接 ContextAssembler。

        数据来源（CC-20260926-01 冻结）：
            ai_name          = self.ai_name
            owner            = self.get_state().owner
            data             = self._data
            now_ts           = 显式传入；未传则 ContextAssembler 使用当前时间
            agent_state_dict = self.get_state().to_dict()
            recall_query     = None

        保证：
        - 返回 AgentContext，不返回 ContextLayers
        - 不修改 main.data
        - 不调用 LLM
        - 不进入 THINK / DECISION / ACTION
        - 不接入 ext_ai.build_ai_context
        """
        state = self.get_state()
        owner = state.owner if state else ""
        agent_state_dict = state.to_dict() if state else None

        return self._context_assembler.assemble(
            ai_name=self.ai_name,
            owner=owner,
            data=self._data,
            now_ts=now_ts,
            agent_state_dict=agent_state_dict,
            recall_query=None,
        )

    # -----------------------------------------------------
    # 剩余方法（P0-3A Stub 保留，B5-2 未实现）
    # -----------------------------------------------------
    def think(self, context: AgentContext) -> Optional[str]:
        """
        P0-3A Stub 保留。B5-2 未实现 THINK。
        绝不调用 LLM。

        签名已在 B5-1 Contract Change CC-20260926-01 冻结：
            think(context: AgentContext) -> Optional[str]
        """
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
def get_runtime(
    ai_name: str,
    data: Dict[str, Any],
    context_assembler: Optional[ContextAssembler] = None,
) -> AgentRuntime:
    """
    获取某个 AI 的 AgentRuntime 实例。

    P0-3B 保持"每次新建"（无缓存），符合 P0-3A Contract。
    未来可能引入缓存，但保持"一个 AI 一个 Runtime"的原则。

    B5-2：可选择性注入 ContextAssembler（用于测试）。
    """
    return AgentRuntime(ai_name, data, context_assembler=context_assembler)


P0_STEP3B_PERCEPTION_CHAIN: implement first real perceive + should_wake