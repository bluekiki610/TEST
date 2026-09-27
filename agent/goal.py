"""
agent/goal.py - Phase C-2: Goal

依据 Contract §5B.1 / §5B.3 / §5B.4。

性质：
- Goal 是 Agent Decision Layer 的 Runtime working state
- Goal 不是 Source of Truth
- Goal 不写入 main.data
- Goal 不建立第二个 SOT
- Goal 不持久化
- Goal 重启丢失（C-2 已知限制）

硬性约束：
1. 不 import main / ext_*
2. 不调用 LLM
3. 不发网络请求
4. 不写文件
5. 不修改传入数据
6. 不自动创建 Goal
7. 不检测 source
8. 不使用随机数
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import time
import uuid


# =========================================================
# 状态常量（Contract §5B.3）
# =========================================================
GOAL_STATUS_CREATED = "CREATED"
GOAL_STATUS_ACTIVE = "ACTIVE"
GOAL_STATUS_COMPLETED = "COMPLETED"
GOAL_STATUS_CANCELLED = "CANCELLED"
GOAL_STATUS_EXPIRED = "EXPIRED"

ALL_GOAL_STATUSES = (
    GOAL_STATUS_CREATED,
    GOAL_STATUS_ACTIVE,
    GOAL_STATUS_COMPLETED,
    GOAL_STATUS_CANCELLED,
    GOAL_STATUS_EXPIRED,
)

# 允许的状态转换（单向）
_ALLOWED_TRANSITIONS = {
    GOAL_STATUS_CREATED: frozenset({
        GOAL_STATUS_ACTIVE,
        GOAL_STATUS_CANCELLED,
    }),
    GOAL_STATUS_ACTIVE: frozenset({
        GOAL_STATUS_COMPLETED,
        GOAL_STATUS_CANCELLED,
        GOAL_STATUS_EXPIRED,
    }),
    GOAL_STATUS_COMPLETED: frozenset(),
    GOAL_STATUS_CANCELLED: frozenset(),
    GOAL_STATUS_EXPIRED: frozenset(),
}


# =========================================================
# Goal 数据结构（Contract §5B.1）
# =========================================================
@dataclass
class Goal:
    """
    Goal = 我想完成什么。

    必需字段（Contract §5B.1）：
        goal_id, actor, type, description, source, status,
        created_at, updated_at, reason, target, completion_condition

    可选字段：
        priority, deadline, related_commitments, related_activity
    """
    goal_id: str
    actor: str
    type: str
    description: str
    source: str
    status: str
    created_at: float
    updated_at: float
    reason: str
    target: str
    completion_condition: str
    priority: Optional[int] = None
    deadline: Optional[float] = None
    related_commitments: List[str] = field(default_factory=list)
    related_activity: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "actor": self.actor,
            "type": self.type,
            "description": self.description,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "reason": self.reason,
            "target": self.target,
            "completion_condition": self.completion_condition,
            "priority": self.priority,
            "deadline": self.deadline,
            "related_commitments": list(self.related_commitments),
            "related_activity": list(self.related_activity),
        }

    def is_terminal(self) -> bool:
        return self.status in (
            GOAL_STATUS_COMPLETED,
            GOAL_STATUS_CANCELLED,
            GOAL_STATUS_EXPIRED,
        )


# =========================================================
# 异常
# =========================================================
class GoalError(Exception):
    """Goal 操作错误基类。"""


class GoalInvalidTransition(GoalError):
    """非法状态转换。"""


class GoalInvalidStatus(GoalError):
    """非法状态值。"""


# =========================================================
# 显式创建 API（Contract §5B.4）
# =========================================================
def create_goal(
    actor: str,
    type: str,
    description: str,
    source: str,
    reason: str,
    target: str,
    completion_condition: str,
    now_ts: Optional[float] = None,
    priority: Optional[int] = None,
    deadline: Optional[float] = None,
) -> Goal:
    """
    显式创建 Goal。

    Contract §5B.4：
    - C-2 只提供 explicit programmatic create API
    - 不自动检测 source
    - 不验证 source 真实性
    - 调用方负责声明正确的 source

    初始状态：CREATED
    """
    if not actor or not isinstance(actor, str):
        raise GoalError("actor must be a non-empty str")
    if not type or not isinstance(type, str):
        raise GoalError("type must be a non-empty str")
    if not source or not isinstance(source, str):
        raise GoalError("source must be a non-empty str")
    if not reason or not isinstance(reason, str):
        raise GoalError("reason must be a non-empty str")
    if not completion_condition or not isinstance(completion_condition, str):
        raise GoalError("completion_condition must be a non-empty str")

    ts = now_ts if isinstance(now_ts, (int, float)) else time.time()

    return Goal(
        goal_id=str(uuid.uuid4()),
        actor=actor,
        type=type,
        description=description,
        source=source,
        status=GOAL_STATUS_CREATED,
        created_at=ts,
        updated_at=ts,
        reason=reason,
        target=target,
        completion_condition=completion_condition,
        priority=priority,
        deadline=deadline,
        related_commitments=[],
        related_activity=[],
    )


# =========================================================
# 显式状态转换（Contract §5B.3）
# =========================================================
def transition_goal(
    goal: Goal,
    new_status: str,
    reason: str,
    now_ts: Optional[float] = None,
) -> Goal:
    """
    显式状态转换。返回新 Goal（不修改原对象）。

    规则：
    - 状态必须合法（ALL_GOAL_STATUSES）
    - 转换必须被 _ALLOWED_TRANSITIONS 允许
    - 必须携带 reason（审计）
    - 单向
    - 不改 main.data
    """
    if not isinstance(goal, Goal):
        raise GoalError("goal must be a Goal")
    if new_status not in ALL_GOAL_STATUSES:
        raise GoalInvalidStatus(f"invalid status: {new_status!r}")
    allowed = _ALLOWED_TRANSITIONS.get(goal.status, frozenset())
    if new_status not in allowed:
        raise GoalInvalidTransition(
            f"transition {goal.status} -> {new_status} is not allowed"
        )
    if not reason or not isinstance(reason, str):
        raise GoalError("transition reason must be a non-empty str")

    ts = now_ts if isinstance(now_ts, (int, float)) else time.time()

    return Goal(
        goal_id=goal.goal_id,
        actor=goal.actor,
        type=goal.type,
        description=goal.description,
        source=goal.source,
        status=new_status,
        created_at=goal.created_at,
        updated_at=ts,
        reason=goal.reason,
        target=goal.target,
        completion_condition=goal.completion_condition,
        priority=goal.priority,
        deadline=goal.deadline,
        related_commitments=list(goal.related_commitments),
        related_activity=list(goal.related_activity),
    )


# =========================================================
# 自描述（供审计）
# =========================================================
def describe_goal_module() -> Dict[str, Any]:
    return {
        "name": "goal",
        "version": "C-2",
        "status": "runtime_working_state",
        "is_source_of_truth": False,
        "persisted": False,
        "statuses": list(ALL_GOAL_STATUSES),
        "automatic_creation": False,
        "source_detection": False,
        "uses_random": False,
    }