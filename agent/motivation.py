"""
agent/motivation.py - Phase C-2: Motivation

依据 Contract §5B.8。

性质：
- Motivation 是动态计算结果
- Motivation 不需要 ID
- Motivation 不持久化
- Motivation 不写入 main.data
- Motivation 不进入 Context
- Motivation 不允许随机数
- Motivation 在 THINK 内部使用

C-2 最小输入集合（Contract §5B.8）：
    goal
    commitment
    agent_state_snapshot
    now_ts

明确不消费（留待后续 Contract Change）：
    Relationship / Memory / Recent Experience / World Conditions

硬性约束：
1. 不 import main / ext_*
2. 不调用 LLM
3. 不发网络请求
4. 不写文件
5. 不修改传入数据
6. 不使用随机数
7. 不实现复杂最终算法（MO-18）
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import time


# =========================================================
# Motivation 摘要结构（结构化输出）
# =========================================================
@dataclass
class MotivationSummary:
    """
    Motivation 的结构化摘要。

    不持久化；不进入 Context。
    """
    actor: str
    goal_id: Optional[str]
    commitment_id: Optional[str]
    explanation: str
    inputs_used: List[str] = field(default_factory=list)
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actor": self.actor,
            "goal_id": self.goal_id,
            "commitment_id": self.commitment_id,
            "explanation": self.explanation,
            "inputs_used": list(self.inputs_used),
            "created_at": self.created_at,
        }


# =========================================================
# 纯函数
# =========================================================
def compute_motivation(
    actor: str,
    goal: Optional[Any],
    commitment: Optional[Any],
    agent_state_snapshot: Optional[Dict[str, Any]],
    now_ts: Optional[float] = None,
) -> MotivationSummary:
    """
    计算 Motivation 摘要。

    C-2 只做"最小输入集合 + 纯函数 + 结构化输出"。
    不做复杂算法（MO-18）。
    不使用随机数（MO-19）。

    参数：
        actor: AI 名
        goal: Goal 对象或 None（C-2 使用 duck typing，不 import goal 模块）
        commitment: Commitment 对象或 None
        agent_state_snapshot: AgentState.to_dict() 结果或 None
        now_ts: 当前时间

    返回：
        MotivationSummary
    """
    if not actor or not isinstance(actor, str):
        raise ValueError("actor must be a non-empty str")

    ts = now_ts if isinstance(now_ts, (int, float)) else time.time()

    inputs_used: List[str] = []

    goal_id: Optional[str] = None
    if goal is not None:
        goal_id = getattr(goal, "goal_id", None)
        inputs_used.append("goal")

    commitment_id: Optional[str] = None
    if commitment is not None:
        commitment_id = getattr(commitment, "commitment_id", None)
        inputs_used.append("commitment")

    state_hint = ""
    if isinstance(agent_state_snapshot, dict):
        inputs_used.append("agent_state_snapshot")
        activity = agent_state_snapshot.get("current_activity")
        location = agent_state_snapshot.get("location")
        if isinstance(activity, str) and activity and activity != "idle":
            state_hint = f"activity={activity}"
        if isinstance(location, str) and location:
            if state_hint:
                state_hint += ", "
            state_hint += f"location={location}"

    parts: List[str] = []
    if goal_id:
        parts.append(f"goal:{goal_id}")
    if commitment_id:
        parts.append(f"commitment:{commitment_id}")
    if state_hint:
        parts.append(state_hint)

    explanation = "motivation[" + "; ".join(parts) + "]" if parts else "motivation[none]"

    return MotivationSummary(
        actor=actor,
        goal_id=goal_id,
        commitment_id=commitment_id,
        explanation=explanation,
        inputs_used=inputs_used,
        created_at=ts,
    )


# =========================================================
# 自描述
# =========================================================
def describe_motivation_module() -> Dict[str, Any]:
    return {
        "name": "motivation",
        "version": "C-2",
        "status": "dynamic_computation",
        "persisted": False,
        "in_context": False,
        "uses_random": False,
        "min_inputs": ["goal", "commitment", "agent_state_snapshot", "now_ts"],
        "forbidden_inputs": ["relationship", "memory", "recent", "world_query"],
        "final_algorithm_frozen": False,
    }