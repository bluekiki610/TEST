"""
agent/commitment.py - Phase C-2: Commitment

依据 Contract §5B.2 / §5B.3。

性质：
- Commitment 是 Agent Decision Layer 的 Runtime working state
- Commitment 不是 Source of Truth
- Commitment 不写入 main.data
- Commitment 不建立第二个 SOT
- Commitment 不持久化
- Commitment 重启丢失（C-2 已知限制）

硬性约束：
1. 不 import main / ext_*
2. 不调用 LLM
3. 不发网络请求
4. 不写文件
5. 不修改传入数据
6. 不自动创建 Commitment
7. 不使用随机数
8. 不实现 AI↔AI negotiation
9. 不实现复杂 replanning
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import time
import uuid


# =========================================================
# 状态常量（Contract §5B.3）
# =========================================================
COMMITMENT_STATUS_CREATED = "CREATED"
COMMITMENT_STATUS_ACTIVE = "ACTIVE"
COMMITMENT_STATUS_FULFILLED = "FULFILLED"
COMMITMENT_STATUS_CANCELLED = "CANCELLED"
COMMITMENT_STATUS_EXPIRED = "EXPIRED"

ALL_COMMITMENT_STATUSES = (
    COMMITMENT_STATUS_CREATED,
    COMMITMENT_STATUS_ACTIVE,
    COMMITMENT_STATUS_FULFILLED,
    COMMITMENT_STATUS_CANCELLED,
    COMMITMENT_STATUS_EXPIRED,
)

_ALLOWED_TRANSITIONS = {
    COMMITMENT_STATUS_CREATED: frozenset({
        COMMITMENT_STATUS_ACTIVE,
        COMMITMENT_STATUS_CANCELLED,
    }),
    COMMITMENT_STATUS_ACTIVE: frozenset({
        COMMITMENT_STATUS_FULFILLED,
        COMMITMENT_STATUS_CANCELLED,
        COMMITMENT_STATUS_EXPIRED,
    }),
    COMMITMENT_STATUS_FULFILLED: frozenset(),
    COMMITMENT_STATUS_CANCELLED: frozenset(),
    COMMITMENT_STATUS_EXPIRED: frozenset(),
}


# =========================================================
# 强度常量（Contract §5A.2）
# =========================================================
STRENGTH_HARD = "hard"
STRENGTH_SOFT = "soft"
STRENGTH_IMPLICIT = "implicit"

ALL_STRENGTHS = (STRENGTH_HARD, STRENGTH_SOFT, STRENGTH_IMPLICIT)

# 类型常量（Contract §5A.2）
COMMITMENT_TYPE_USER_PROMISE = "user_promise"
COMMITMENT_TYPE_AI_PROMISE = "ai_promise"
COMMITMENT_TYPE_MEETING = "meeting"
COMMITMENT_TYPE_DATE = "date"
COMMITMENT_TYPE_IMPLICIT = "implicit"

ALL_COMMITMENT_TYPES = (
    COMMITMENT_TYPE_USER_PROMISE,
    COMMITMENT_TYPE_AI_PROMISE,
    COMMITMENT_TYPE_MEETING,
    COMMITMENT_TYPE_DATE,
    COMMITMENT_TYPE_IMPLICIT,
)


# =========================================================
# Commitment 数据结构（Contract §5B.2）
# =========================================================
@dataclass
class Commitment:
    """
    Commitment = 我已经答应 / 约定 / 承诺什么。

    必需字段（Contract §5B.2）：
        commitment_id, type, actor, counterparty, content,
        strength, status, created_at, updated_at, reason

    可选字段：
        expires_at, linked_goal, linked_activity, source
    """
    commitment_id: str
    type: str
    actor: str
    counterparty: str
    content: str
    strength: str
    status: str
    created_at: float
    updated_at: float
    reason: str
    expires_at: Optional[float] = None
    linked_goal: Optional[str] = None
    linked_activity: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commitment_id": self.commitment_id,
            "type": self.type,
            "actor": self.actor,
            "counterparty": self.counterparty,
            "content": self.content,
            "strength": self.strength,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "reason": self.reason,
            "expires_at": self.expires_at,
            "linked_goal": self.linked_goal,
            "linked_activity": self.linked_activity,
            "source": self.source,
        }

    def is_terminal(self) -> bool:
        return self.status in (
            COMMITMENT_STATUS_FULFILLED,
            COMMITMENT_STATUS_CANCELLED,
            COMMITMENT_STATUS_EXPIRED,
        )

    def is_hard(self) -> bool:
        return self.strength == STRENGTH_HARD


# =========================================================
# 异常
# =========================================================
class CommitmentError(Exception):
    """Commitment 操作错误基类。"""


class CommitmentInvalidTransition(CommitmentError):
    """非法状态转换。"""


class CommitmentInvalidStatus(CommitmentError):
    """非法状态值。"""


class CommitmentInvalidStrength(CommitmentError):
    """非法强度值。"""


class CommitmentInvalidType(CommitmentError):
    """非法类型值。"""


# =========================================================
# 显式创建 API
# =========================================================
def create_commitment(
    type: str,
    actor: str,
    counterparty: str,
    content: str,
    strength: str,
    reason: str,
    now_ts: Optional[float] = None,
    expires_at: Optional[float] = None,
    linked_goal: Optional[str] = None,
    linked_activity: Optional[str] = None,
    source: Optional[str] = None,
) -> Commitment:
    """
    显式创建 Commitment。

    初始状态：CREATED
    """
    if type not in ALL_COMMITMENT_TYPES:
        raise CommitmentInvalidType(f"invalid type: {type!r}")
    if strength not in ALL_STRENGTHS:
        raise CommitmentInvalidStrength(f"invalid strength: {strength!r}")
    if not actor or not isinstance(actor, str):
        raise CommitmentError("actor must be a non-empty str")
    if not counterparty or not isinstance(counterparty, str):
        raise CommitmentError("counterparty must be a non-empty str")
    if not content or not isinstance(content, str):
        raise CommitmentError("content must be a non-empty str")
    if not reason or not isinstance(reason, str):
        raise CommitmentError("reason must be a non-empty str")

    ts = now_ts if isinstance(now_ts, (int, float)) else time.time()

    return Commitment(
        commitment_id=str(uuid.uuid4()),
        type=type,
        actor=actor,
        counterparty=counterparty,
        content=content,
        strength=strength,
        status=COMMITMENT_STATUS_CREATED,
        created_at=ts,
        updated_at=ts,
        reason=reason,
        expires_at=expires_at,
        linked_goal=linked_goal,
        linked_activity=linked_activity,
        source=source,
    )


# =========================================================
# 显式状态转换
# =========================================================
def transition_commitment(
    commitment: Commitment,
    new_status: str,
    reason: str,
    now_ts: Optional[float] = None,
) -> Commitment:
    """
    显式状态转换。返回新 Commitment（不修改原对象）。

    规则：
    - 状态必须合法
    - 转换必须被允许
    - 必须携带 reason
    - 单向
    """
    if not isinstance(commitment, Commitment):
        raise CommitmentError("commitment must be a Commitment")
    if new_status not in ALL_COMMITMENT_STATUSES:
        raise CommitmentInvalidStatus(f"invalid status: {new_status!r}")
    allowed = _ALLOWED_TRANSITIONS.get(commitment.status, frozenset())
    if new_status not in allowed:
        raise CommitmentInvalidTransition(
            f"transition {commitment.status} -> {new_status} is not allowed"
        )
    if not reason or not isinstance(reason, str):
        raise CommitmentError("transition reason must be a non-empty str")

    ts = now_ts if isinstance(now_ts, (int, float)) else time.time()

    return Commitment(
        commitment_id=commitment.commitment_id,
        type=commitment.type,
        actor=commitment.actor,
        counterparty=commitment.counterparty,
        content=commitment.content,
        strength=commitment.strength,
        status=new_status,
        created_at=commitment.created_at,
        updated_at=ts,
        reason=commitment.reason,
        expires_at=commitment.expires_at,
        linked_goal=commitment.linked_goal,
        linked_activity=commitment.linked_activity,
        source=commitment.source,
    )


# =========================================================
# 自描述
# =========================================================
def describe_commitment_module() -> Dict[str, Any]:
    return {
        "name": "commitment",
        "version": "C-2",
        "status": "runtime_working_state",
        "is_source_of_truth": False,
        "persisted": False,
        "statuses": list(ALL_COMMITMENT_STATUSES),
        "strengths": list(ALL_STRENGTHS),
        "types": list(ALL_COMMITMENT_TYPES),
        "automatic_creation": False,
        "ai_to_ai_negotiation": False,
        "uses_random": False,
    }