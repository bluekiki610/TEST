"""
agent/intent.py - Phase C-2: Intent / IntentSet

依据 Contract §5B.9 / §5B.10。

性质：
- Intent 是结构化对象
- Intent 必须可审计
- Intent 必须携带 Motivation / reason
- Intent 不产生副作用
- Intent 不直接修改 main.data
- Intent 不直接触发 Action
- Intent 不持久化
- Intent 不跨 Event 存活

C-2 Stub 允许：
    IntentSet(candidates=[])
    空集合是合法且默认的输出。

硬性约束：
1. 不 import main / ext_*
2. 不调用 LLM
3. 不发网络请求
4. 不写文件
5. 不修改传入数据
6. 不引入 Decision 字段
7. 不制造假 Intent
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import time


# =========================================================
# Intent 数据结构（Contract §5B.9）
# =========================================================
@dataclass
class Intent:
    """
    Intent = 我现在倾向做什么。

    必需字段：
        intent_id, actor, action_type, reason, created_at

    可选字段：
        target, source_goal, source_commitment,
        constraints, confidence, candidate_rank

    注意：
        reason = 当前 Motivation 为什么导致这个 Intent 候选
        （区别于 Goal.reason = 为什么形成长期 Goal）
    """
    intent_id: str
    actor: str
    action_type: str
    reason: str
    created_at: float = 0.0
    target: Optional[str] = None
    source_goal: Optional[str] = None
    source_commitment: Optional[str] = None
    constraints: List[str] = field(default_factory=list)
    confidence: Optional[float] = None
    candidate_rank: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "actor": self.actor,
            "action_type": self.action_type,
            "reason": self.reason,
            "created_at": self.created_at,
            "target": self.target,
            "source_goal": self.source_goal,
            "source_commitment": self.source_commitment,
            "constraints": list(self.constraints),
            "confidence": self.confidence,
            "candidate_rank": self.candidate_rank,
        }


# =========================================================
# IntentSet 数据结构（Contract §5B.9）
# =========================================================
@dataclass
class IntentSet:
    """
    Intent 候选集合。

    字段：
        actor
        created_at
        candidates: List[Intent]
        reason_summary

    C-2 Stub 允许：
        candidates == []  （合法且默认）
    """
    actor: str
    created_at: float = 0.0
    candidates: List[Intent] = field(default_factory=list)
    reason_summary: str = ""

    def is_empty(self) -> bool:
        return len(self.candidates) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actor": self.actor,
            "created_at": self.created_at,
            "candidates": [c.to_dict() for c in self.candidates],
            "reason_summary": self.reason_summary,
        }


# =========================================================
# 工厂
# =========================================================
def make_intent(
    intent_id: str,
    actor: str,
    action_type: str,
    reason: str,
    now_ts: Optional[float] = None,
    target: Optional[str] = None,
    source_goal: Optional[str] = None,
    source_commitment: Optional[str] = None,
    constraints: Optional[List[str]] = None,
    confidence: Optional[float] = None,
    candidate_rank: Optional[int] = None,
) -> Intent:
    if not intent_id or not isinstance(intent_id, str):
        raise ValueError("intent_id must be a non-empty str")
    if not actor or not isinstance(actor, str):
        raise ValueError("actor must be a non-empty str")
    if not action_type or not isinstance(action_type, str):
        raise ValueError("action_type must be a non-empty str")
    if not reason or not isinstance(reason, str):
        raise ValueError("reason must be a non-empty str")

    ts = now_ts if isinstance(now_ts, (int, float)) else time.time()

    return Intent(
        intent_id=intent_id,
        actor=actor,
        action_type=action_type,
        reason=reason,
        created_at=ts,
        target=target,
        source_goal=source_goal,
        source_commitment=source_commitment,
        constraints=list(constraints) if constraints else [],
        confidence=confidence,
        candidate_rank=candidate_rank,
    )


def make_empty_intent_set(
    actor: str,
    now_ts: Optional[float] = None,
    reason_summary: str = "",
) -> IntentSet:
    """
    C-2 Stub 的合法输出。

    Contract §5B.10：
        IntentSet(candidates=[]) 是合法且默认的输出。
    """
    ts = now_ts if isinstance(now_ts, (int, float)) else time.time()
    return IntentSet(
        actor=actor,
        created_at=ts,
        candidates=[],
        reason_summary=reason_summary,
    )


# =========================================================
# 自描述
# =========================================================
def describe_intent_module() -> Dict[str, Any]:
    return {
        "name": "intent",
        "version": "C-2",
        "persisted": False,
        "candidate_container": "IntentSet",
        "empty_allowed": True,
        "has_decision_field": False,
        "side_effects": False,
    }