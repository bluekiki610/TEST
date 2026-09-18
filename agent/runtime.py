"""
agent/runtime.py - P0-3A: Agent Runtime Contract & Lifecycle Design

本文件只定义"接口契约"（Contract），不实现真实逻辑。

硬性约束：
1. 不调用 LLM
2. 不修改 main.data
3. 不启动 Scheduler / EventBus / Wake / Brain
4. 不触碰任何 ext_*.py 行为
5. 所有方法返回"结构化占位"或"未实现占位"
6. 不持久化任何数据

设计目标：
- 明确一个 AI 从"收到 Event"到"未来可能 Action"的生命周期
- 明确 AgentState / Event / Decision / Action 四种概念边界
- 明确 Context Budget 分层
- 为未来 Brain / Scheduler / Wake / AI-AI 社交 / VoiceStudio / World Clone 留接口

⚠️ P0-3A 中所有方法均为 Contract Stub，不产生任何世界变化。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from agent.event import Event
from agent.state import AgentState, get_agent_state


# =========================================================
# 1. Wake Decision 枚举（P0-3A 只定义，不实现调度）
# =========================================================
class WakeDecision(str, Enum):
    """
    Agent 对一个 Event 的唤醒决策。

    注意：这是 P0-3A 的 Contract 层枚举，不是已实现的调度系统。
    NONE / LOW / HIGH 属于 Event Semantics 层（P0-2D），
    本枚举属于 Agent Runtime 层。两者不应混淆。
    """
    IGNORE = "ignore"      # 事件与当前 AI 无关，不感知
    OBSERVE = "observe"    # 感知并记录，但不触发 LLM
    THINK = "think"        # 值得进入 Brain / Context 构建


# =========================================================
# 2. Context 分层（P0-3A 只定义，不实现 Builder）
# =========================================================
@dataclass
class ContextLayers:
    """
    未来 Context Builder 的输入分层。

    P0-3A 仅定义边界，不实现具体拼装逻辑。
    目标：历史数据可以持续增长，
         但单次 LLM Context 不应跟着历史数据线性增长。
    """
    stable_core: Dict[str, Any] = field(default_factory=dict)
    # 世界设定 / AI 人设 / 核心用户信息 / 长期身份

    recent: Dict[str, Any] = field(default_factory=dict)
    # 当前对话 / 最近 Event / 当前活动

    long_term: Dict[str, Any] = field(default_factory=dict)
    # Memory / Relationship / 历史事件（按需检索）

    dynamic_world: Dict[str, Any] = field(default_factory=dict)
    # AgentState / 当前地点 / 当前世界状态


# =========================================================
# 3. Decision 结构（P0-3A 只定义，不产生真实决策）
# =========================================================
@dataclass
class Decision:
    """
    Agent 思考后的结构化决策。

    P0-3A 只定义字段，不实现决策引擎。
    """
    action_type: Optional[str] = None
    # "speak" / "sms" / "move" / "note" / "diary" / "story" / "work" / "invite_date" / "silent"

    payload: Dict[str, Any] = field(default_factory=dict)
    # 动作参数

    reason: Optional[str] = None
    # 决策理由（用于调试/日志）

    confidence: Optional[float] = None
    # 0.0 ~ 1.0 置信度（未来）

    _stub: bool = True  # P0-3A 标记：所有 Decision 都是占位


# =========================================================
# 4. AgentRuntime Contract（P0-3A 骨架）
# =========================================================
class AgentRuntime:
    """
    单个 AI 的 Agent Runtime 契约。

    原则：
    - 一个 AI 一个 Runtime 实例（不是"一个超级 Runtime 管理所有 AI"）
    - Runtime 只编排，不复制 ext_* 能力
    - Runtime 不修改 World，只通过 Decision → Action 让现有系统修改

    生命周期（9 阶段）：
        RECEIVE → PERCEIVE → WAKE_DECISION → CONTEXT
        → THINK → DECISION → ACTION → WORLD_CHANGE → EVENT(新)

    P0-3A 中上述阶段全部为 Contract Stub。
    """

    def __init__(self, ai_name: str, data: Dict[str, Any]):
        """
        Args:
            ai_name: AI 名字（规范化后的 canonical 名）
            data:    main.data 引用（只读，Runtime 不允许直接修改）

        注意：P0-3A 不注册任何后台线程，不启动任何循环。
        """
        self.ai_name = ai_name
        self._data = data
        self._stub = True  # 标记：P0-3A Contract 层

    # -----------------------------------------------------
    # 阶段 1：RECEIVE
    # -----------------------------------------------------
    def receive_event(self, event: Event) -> None:
        """
        接收一个 Event。

        P0-3A Contract：只做记录，不做任何响应。
        未来：可能更新内部事件队列。
        """
        # STUB：什么都不做
        return None

    # -----------------------------------------------------
    # 阶段 2：PERCEIVE
    # -----------------------------------------------------
    def perceive(self, event: Event) -> bool:
        """
        判断该 Event 对当前 AI 是否相关。

        Returns:
            True  = 相关，继续后续阶段
            False = 无关，此 Event 对当前 AI 无需处理

        P0-3A Contract：直接返回 False（不实现真实感知逻辑）。
        未来：根据 event.source / ai_name / payload 做相关性判断。
        """
        # STUB：暂不感知
        return False

    # -----------------------------------------------------
    # 阶段 3：WAKE_DECISION
    # -----------------------------------------------------
    def should_wake(self, event: Event) -> WakeDecision:
        """
        判断是否需要唤醒 Agent。

        Returns:
            WakeDecision.IGNORE / OBSERVE / THINK

        P0-3A Contract：返回 IGNORE。
        未来：结合 Event 级别（P0-2D）+ AgentState + Wake Score 综合判断。
        """
        # STUB：默认忽略
        return WakeDecision.IGNORE

    # -----------------------------------------------------
    # 阶段 4：CONTEXT
    # -----------------------------------------------------
    def build_context(self, event: Event) -> ContextLayers:
        """
        构造未来 LLM 所需的 Context（分层返回）。

        P0-3A Contract：返回空的 ContextLayers。
        未来：从 main.data 中按层提取内容，交由 Context Builder 组装。
        """
        # STUB：返回空层
        return ContextLayers()

    # -----------------------------------------------------
    # 阶段 5：THINK
    # -----------------------------------------------------
    def think(self, context: ContextLayers) -> Optional[str]:
        """
        调用 Brain / LLM 进行推理。

        P0-3A Contract：绝不调用 LLM，返回 None。
        未来：调用 ext_ai.call_llm()，返回原始推理文本。
        """
        # STUB：绝不调用 LLM
        return None

    # -----------------------------------------------------
    # 阶段 6：DECISION
    # -----------------------------------------------------
    def decide(self, thought: Optional[str]) -> Optional[Decision]:
        """
        将推理结果结构化为 Decision。

        P0-3A Contract：返回 None。
        未来：解析 LLM JSON 输出 → Decision 对象。
        """
        # STUB：无决策
        return None

    # -----------------------------------------------------
    # 阶段 7：ACTION
    # -----------------------------------------------------
    def execute(self, decision: Optional[Decision]) -> bool:
        """
        将 Decision 派发给现有 Linkong 能力执行。

        P0-3A Contract：什么都不做，返回 False。
        未来：调用 ext_ai.execute_action() 或对应的 ext_* 接口。

        关键约束：
        - Runtime 不直接修改 main.data
        - Runtime 只调用现有 ext_* 能力
        - 现有系统负责真正的世界变化
        """
        # STUB：不执行任何 Action
        return False

    # -----------------------------------------------------
    # 辅助：状态投影（只读）
    # -----------------------------------------------------
    def get_state(self) -> Optional[AgentState]:
        """
        返回当前 AI 的 AgentState 投影。

        这是 P0-1 已实现的能力，Runtime 只透传调用。
        不修改任何数据。
        """
        return get_agent_state(self.ai_name, self._data)


# =========================================================
# 5. Runtime 工厂（P0-3A Contract）
# =========================================================
def get_runtime(ai_name: str, data: Dict[str, Any]) -> AgentRuntime:
    """
    获取（未来可能缓存）某个 AI 的 AgentRuntime 实例。

    P0-3A Contract：每次都新建实例（无缓存）。
    未来：可能引入缓存，但保持"一个 AI 一个 Runtime"的原则。
    """
    return AgentRuntime(ai_name, data)
