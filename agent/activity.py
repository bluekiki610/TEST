# -*- coding: utf-8 -*-
"""
agent/activity.py - Phase D-2: Activity Domain Object + Runtime-scoped Activity Registry
=========================================================================================

依据：docs/V3.1_ARCHITECTURE_CONTRACT.md §5E（CC-20260930-06）
      docs/D2_ACTIVITY_CONTRACT_PREFLIGHT.md（APPROVED WITH ARCHITECTURAL CORRECTIONS）

--------------------------------------------------------------------------
D-2 的唯一目标
--------------------------------------------------------------------------

    AI 正在做什么事情，而且这个事情为什么能够跨 Event 持续？

即：**Activity = 持续世界过程**（描述「谁正在经历什么」）。

--------------------------------------------------------------------------
本模块**只**实现以下内容（授权范围）
--------------------------------------------------------------------------

    ✅ Formal Activity（Domain Object）
    ✅ Runtime-scoped Activity Registry（唯一管理入口）
    ✅ lifecycle（7 状态 + 冻结转换表 + 终态不可逆）
    ✅ actor / participant / role
    ✅ primary / secondary binding
    ✅ 基础查询 / 管理能力

--------------------------------------------------------------------------
本模块**明确不做**（Contract §5E 禁止项）
--------------------------------------------------------------------------

    ❌ 持久化（不写文件 / 不写数据库 / 不写 World 存储）
    ❌ 在 World 存储中新增 activity 相关顶层 key（ED-8）
    ❌ 调度器 / 周期任务 / 后台轮询（EP-6 / EP-10）
    ❌ expected_end_at 自动完成（EP-5 —— 到期不等于自动结束）
    ❌ Activity 产生 Event（EB-13 / EF-6）
    ❌ Capability 集成（EN-6 / EN-8）
    ❌ Movement 集成（EJ-4）
    ❌ 接入 Motivation（ET-1 / ET-7）
    ❌ Activity → Legacy 反向写入 / 双向同步（EO-9 ～ EO-12）
    ❌ 引用 World 模块（不持有 World 引用）
    ❌ 复制 World 事实为自有字段（EO-1）

--------------------------------------------------------------------------
关键语义（Contract §5E 摘要）
--------------------------------------------------------------------------

    EA-7   Activity 必须同时满足：身份 / 持续 / 参与者 / 可终止
    EB-*   Activity ≠ World Fact / Event / Goal / Commitment / Intent /
           Action / Motivation / Scheduler Entry
    EC-1   Activity 是正式 Domain Object
    EC-4   同一 activity_id 在 Runtime 中只有一个对象真相
    EE-1   存在唯一的 Runtime-scoped Activity Registry
    EE-2   Registry 是唯一管理入口
    EE-4   AgentRuntime 不得拥有自己的独立 Activity 真相
    EE-8   primary Activity 是「绑定关系」，不是「所有权」
    EF-*   lifecycle 冻结；终态不可逆
    EG-*   actor_ids / participant_ids / role_map
    EH-*   不持久化；跨 Event 连续；跨重启不保证
    EI-2   打断必须区分 PAUSED（可恢复）与 CANCELLED（终止）
    EJ-6   location_id = 过程发生地 ≠ AI 当前位置
    EK-1   同一 AI 最多一个 primary
    EK-2   可以有多个 secondary
    EL-1   goal_id 可为空
    EL-4   commitment_ids 可为空
    EM-1   创建只能来自显式 API
    EN-*   与 Capability 的边界
    EO-*   防第二 World SOT
    EP-1   Activity 不是 Scheduler
    EQ-1   type 是开放标识
    ER-*   最小结构
"""

from __future__ import annotations

import copy
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

# =========================================================
# 1. 生命周期（Contract §5E.6 / EF-1）
# =========================================================

#: 生命周期状态（固定 7 个 —— EF-1）
STATUS_PLANNED = "PLANNED"
STATUS_TRAVELING = "TRAVELING"
STATUS_ARRIVED = "ARRIVED"
STATUS_ACTIVE = "ACTIVE"
STATUS_PAUSED = "PAUSED"
STATUS_COMPLETED = "COMPLETED"
STATUS_CANCELLED = "CANCELLED"

#: 全部生命周期状态（EF-1）
LIFECYCLE_STATUSES: Tuple[str, ...] = (
    STATUS_PLANNED,
    STATUS_TRAVELING,
    STATUS_ARRIVED,
    STATUS_ACTIVE,
    STATUS_PAUSED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
)

#: 终态（EF-3：不可逆）
TERMINAL_STATUSES: Tuple[str, ...] = (
    STATUS_COMPLETED,
    STATUS_CANCELLED,
)

#: 初始状态
INITIAL_STATUS = STATUS_PLANNED

#: 允许转换（EF-2 冻结）
ALLOWED_TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    STATUS_PLANNED: (STATUS_TRAVELING, STATUS_CANCELLED),
    STATUS_TRAVELING: (STATUS_ARRIVED, STATUS_CANCELLED),
    STATUS_ARRIVED: (STATUS_ACTIVE, STATUS_CANCELLED),
    STATUS_ACTIVE: (STATUS_PAUSED, STATUS_COMPLETED, STATUS_CANCELLED),
    STATUS_PAUSED: (STATUS_ACTIVE, STATUS_CANCELLED),
    STATUS_COMPLETED: (),
    STATUS_CANCELLED: (),
}

#: 必须携带原因的转换（EF-5：CANCELLED 不得静默取消）
REASON_REQUIRED_TARGETS: Tuple[str, ...] = (STATUS_CANCELLED,)

#: 需要记录结束时间的终态
CLOSING_STATUSES: Tuple[str, ...] = (STATUS_COMPLETED, STATUS_CANCELLED)


def is_terminal(status: str) -> bool:
    """该状态是否为终态（EF-3）。"""
    return status in TERMINAL_STATUSES


def can_transition(src: str, dst: str) -> bool:
    """
    转换是否合法（EF-2）。

    只允许 `ALLOWED_TRANSITIONS` 中列出的转换；
    终态无出边（EF-3）；未知状态一律非法。
    """
    if src not in ALLOWED_TRANSITIONS:
        return False
    return dst in ALLOWED_TRANSITIONS[src]


def allowed_next_statuses(status: str) -> Tuple[str, ...]:
    """某状态下允许到达的下一状态（只读，返回元组）。"""
    return ALLOWED_TRANSITIONS.get(status, ())


# =========================================================
# 2. 参与者角色（Contract §5E.7 / EG-4）
# =========================================================

#: 主体（承担「正在进行」的实体）
ROLE_ACTOR = "actor"
#: 对等参与者（如约会另一方）
ROLE_PARTNER = "partner"
#: 协作参与者
ROLE_PARTICIPANT = "participant"
#: 在场但未参与
ROLE_OBSERVER = "observer"

#: 冻结的基础角色（EG-10：完整取值集合未冻结，但至少要能表达主体/参与）
BASE_ROLES: Tuple[str, ...] = (
    ROLE_ACTOR,
    ROLE_PARTNER,
    ROLE_PARTICIPANT,
    ROLE_OBSERVER,
)

# =========================================================
# 3. binding 类型（Contract §5E.5 / EE-7 / EE-8 / §5E.11）
# =========================================================

BINDING_PRIMARY = "primary"
BINDING_SECONDARY = "secondary"

BINDING_KINDS: Tuple[str, ...] = (BINDING_PRIMARY, BINDING_SECONDARY)

# =========================================================
# 4. Activity Domain Object（Contract §5E.3 / §5E.18）
# =========================================================


@dataclass(frozen=True)
class Activity:
    """
    Formal Activity —— 正式的「持续世界过程」Domain Object（`EC-1`）。

    ## 为什么是 frozen

        `EC-1` / `EC-4`：Activity 是 Domain Object，且同一 `activity_id`
        在 Runtime 中只有一个对象真相。frozen 保证其他 Holder
        **无法就地篡改** Activity，只能通过 Registry 的显式转换产生新对象。

    ## 字段（语义见 Contract §5E.18 / ER-1 / ER-2）

        必需：activity_id / type / actor_ids / status
        可选：participant_ids / role_map / location_id / started_at /
              expected_end_at / ended_at / goal_id / commitment_ids /
              current_step / origin / metadata

    ## 明确禁止的字段（Contract）

        ❌ 任何 World 事实的**副本**（位置详情、钱包、好感…）—— `EO-1`
        ❌ 调度字段（`next_ts` / `timer` / `schedule` / `cron`）—— `EP-3` / `ER-7`
        ❌ `owner` / `data` 引用、Prompt / LLM 输出、持久化元字段 —— `ER-3`
    """

    activity_id: str
    type: str
    actor_ids: Tuple[str, ...]
    status: str = INITIAL_STATUS

    participant_ids: Tuple[str, ...] = ()
    role_map: Dict[str, str] = field(default_factory=dict)

    #: 「这个过程发生在哪里」——**不是** AI 的当前位置（`EJ-6`）
    location_id: str = ""

    started_at: float = 0.0
    #: **预期**结束时间 —— 是描述，不是触发（`EP-4`）；到期**不等于**自动结束（`EP-5`）
    expected_end_at: float = 0.0
    ended_at: float = 0.0

    #: 弱引用，可为空（`EL-1` / `EL-3`）
    goal_id: str = ""
    #: 弱引用，可为空（`EL-4`）
    commitment_ids: Tuple[str, ...] = ()

    #: 过程内部步骤（语义未冻结 —— `ER-5`）
    current_step: str = ""
    #: 来源说明（用于可解释性 —— `EA-9`）
    origin: str = ""
    #: 扩展位（内容未冻结 —— `ER-5`）
    metadata: Dict[str, Any] = field(default_factory=dict)

    #: 终止原因（`EF-5`：CANCELLED 必须有原因）
    end_reason: str = ""

    # --- 只读便捷判定 ---------------------------------------

    def is_terminal(self) -> bool:
        return is_terminal(self.status)

    def is_active_like(self) -> bool:
        """是否处于「正在进行」的非终态（PLANNED 之外的非终态）。"""
        return self.status in (
            STATUS_TRAVELING,
            STATUS_ARRIVED,
            STATUS_ACTIVE,
            STATUS_PAUSED,
        )

    def all_entity_ids(self) -> Tuple[str, ...]:
        """主体 + 参与者的并集（保持顺序、去重）。"""
        seen: List[str] = []
        for name in tuple(self.actor_ids) + tuple(self.participant_ids):
            if name not in seen:
                seen.append(name)
        return tuple(seen)

    def involves(self, entity: str) -> bool:
        """该实体是否参与此 Activity（主体或参与者）。"""
        return entity in self.all_entity_ids()

    def role_of(self, entity: str) -> str:
        """返回该实体的角色；未显式登记时按主体/参与者推断。"""
        explicit = self.role_map.get(entity, "")
        if explicit:
            return explicit
        if entity in self.actor_ids:
            return ROLE_ACTOR
        if entity in self.participant_ids:
            return ROLE_PARTICIPANT
        return ""

    def to_dict(self) -> Dict[str, Any]:
        """
        只读序列化（返回新 dict；嵌套结构为副本）。

        ⚠️ 本方法**不**使 Activity 可持久化 —— 仅用于调试 / 呈现。
        """
        return {
            "activity_id": self.activity_id,
            "type": self.type,
            "actor_ids": list(self.actor_ids),
            "participant_ids": list(self.participant_ids),
            "role_map": copy.deepcopy(dict(self.role_map)),
            "location_id": self.location_id,
            "status": self.status,
            "started_at": self.started_at,
            "expected_end_at": self.expected_end_at,
            "ended_at": self.ended_at,
            "goal_id": self.goal_id,
            "commitment_ids": list(self.commitment_ids),
            "current_step": self.current_step,
            "origin": self.origin,
            "metadata": copy.deepcopy(dict(self.metadata)),
            "end_reason": self.end_reason,
        }


# =========================================================
# 5. 转换结果
# =========================================================


@dataclass(frozen=True)
class TransitionResult:
    """
    生命周期转换结果（只读）。

        ok       转换是否成功
        activity 成功时为**新** Activity 对象；失败时为 None
        reason   失败原因（可审计 —— `EF-4`）
    """

    ok: bool
    activity: Optional[Activity] = None
    reason: str = ""


# =========================================================
# 6. Runtime-scoped Activity Registry（Contract §5E.5）
# =========================================================


class ActivityRegistryError(Exception):
    """Registry 操作被拒绝（违反 Contract 约束）。"""


class ActivityRegistry:
    """
    Runtime-scoped Activity Registry —— **当前运行期 Activity 对象的唯一管理入口**。

    ## 架构定位（Contract §5E.4 / §5E.5）

        World Runtime
        └── ActivityRegistry          ← 唯一管理入口（`EE-1` / `EE-2`）
            ├── Activity A
            ├── Activity B
            └── Activity C

        AgentRuntime
            ├── 当前绑定的 activity id  ← 绑定引用（`EE-5`）
            ├── primary / secondary   ← 绑定关系（`EE-7` / `EE-8`）
            ✗ 不得拥有自己的独立 Activity 真相（`EE-4`）

    ## 边界（必须牢记）

        ✅ Activity = **Runtime-scoped Domain State**（`ED-1`）
        ✅ `main.data` 仍是唯一 World SOT（`ED-2`）——
           本类**不是**第二个 World SOT（`ED-3` / `ED-4`）
        ❌ 不持久化（`ED-5` / `EH-1`）
        ❌ 不产生 Event（`EB-13`）
        ❌ 不承担调度职责（`EP-9` / `EE-12`）
        ✅ 跨 Event 连续（`ED-9`）；跨重启不保证（`ED-10` / `EH-3`）
    """

    def __init__(self) -> None:
        #: activity_id -> Activity（Runtime 内唯一真相 —— `EC-4` / `EE-3`）
        self._activities: Dict[str, Activity] = {}
        #: activity_id -> type（便于只读筛选）
        self._type_index: Dict[str, str] = {}
        #: entity -> {activity_id: binding kind}（绑定关系，非所有权 —— `EE-8`）
        self._bindings: Dict[str, Dict[str, str]] = {}

    # ------------------------------------------------------------------
    # 6.1 创建（EM-1：只能来自显式 API）
    # ------------------------------------------------------------------

    @staticmethod
    def new_activity_id() -> str:
        """生成新的 `activity_id`（身份 —— `EA-7` 条件 1）。"""
        return "act_" + uuid.uuid4().hex

    def create_activity(
        self,
        type: str,
        actor_ids: Sequence[str],
        participant_ids: Sequence[str] = (),
        role_map: Optional[Dict[str, str]] = None,
        location_id: str = "",
        expected_end_at: float = 0.0,
        goal_id: str = "",
        commitment_ids: Sequence[str] = (),
        origin: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        current_step: str = "",
        activity_id: str = "",
        now_ts: Optional[float] = None,
    ) -> Activity:
        """
        创建一个处于 `PLANNED` 的 Activity（`EM-1`）。

        校验（违反即拒绝）：
            * `type` 非空（`EQ-1`：开放标识，但不允许空）
            * `actor_ids` 至少一个主体（`EG-2` / `EA-7` 条件 3）
            * `activity_id` 未重复（`EC-4` / `EE-3`）
            * `role_map` 的键必须是参与者（`EG-4`）
        """
        if not isinstance(type, str) or not type.strip():
            raise ActivityRegistryError("EQ-1：Activity.type 必须是非空开放标识")

        actors = self._normalize_ids(actor_ids, "actor_ids")
        if not actors:
            raise ActivityRegistryError(
                "EG-2：actor_ids 必须至少包含一个主体（EA-7 条件 3）"
            )

        participants = self._normalize_ids(participant_ids, "participant_ids")
        roles = self._normalize_role_map(role_map, actors, participants)

        aid = activity_id or self.new_activity_id()
        if aid in self._activities:
            raise ActivityRegistryError(
                f"EC-4 / EE-3：activity_id 已存在，禁止重复创建：{aid}"
            )

        ts = self._now(now_ts)
        activity = Activity(
            activity_id=aid,
            type=type.strip(),
            actor_ids=actors,
            status=INITIAL_STATUS,
            participant_ids=participants,
            role_map=roles,
            location_id=location_id,
            started_at=0.0,
            expected_end_at=float(expected_end_at or 0.0),
            ended_at=0.0,
            goal_id=goal_id,
            commitment_ids=self._normalize_ids(commitment_ids, "commitment_ids"),
            current_step=current_step,
            origin=origin,
            metadata=copy.deepcopy(dict(metadata or {})),
            end_reason="",
        )
        self._store(activity)
        return activity

    # ------------------------------------------------------------------
    # 6.2 读取
    # ------------------------------------------------------------------

    def get(self, activity_id: str) -> Optional[Activity]:
        """按 id 取 Activity（不存在返回 None）。"""
        return self._activities.get(activity_id)

    def require(self, activity_id: str) -> Activity:
        """按 id 取 Activity；不存在则抛错（供显式调用方使用）。"""
        activity = self._activities.get(activity_id)
        if activity is None:
            raise ActivityRegistryError(f"activity_id 不存在：{activity_id}")
        return activity

    def exists(self, activity_id: str) -> bool:
        return activity_id in self._activities

    def count(self) -> int:
        return len(self._activities)

    def list_all(self) -> List[Activity]:
        """列出全部 Activity（新列表；不暴露内部容器）。"""
        return [self._activities[k] for k in sorted(self._activities.keys())]

    def list_by_status(self, status: str) -> List[Activity]:
        return [a for a in self.list_all() if a.status == status]

    def list_by_type(self, type: str) -> List[Activity]:
        return [a for a in self.list_all() if a.type == type]

    def list_by_entity(self, entity: str) -> List[Activity]:
        """某实体（主体或参与者）涉及的全部 Activity。"""
        return [a for a in self.list_all() if a.involves(entity)]

    def list_by_actor(self, entity: str) -> List[Activity]:
        return [a for a in self.list_all() if entity in a.actor_ids]

    def list_by_participant(self, entity: str) -> List[Activity]:
        return [a for a in self.list_all() if entity in a.participant_ids]

    def list_by_location(self, location_id: str) -> List[Activity]:
        """
        按「过程发生地」筛选（`EJ-6`）。

        ⚠️ `location_id` 是**该过程发生的地方**，**不是** AI 的当前位置；
        且本模块**不拥有** `ai_location`（`EJ-2` / `EJ-5`）。
        """
        return [a for a in self.list_all() if a.location_id == location_id]

    def list_open(self) -> List[Activity]:
        """全部非终态 Activity。"""
        return [a for a in self.list_all() if not a.is_terminal()]

    # ------------------------------------------------------------------
    # 6.3 生命周期转换（EF-7：只能通过显式转换 API）
    # ------------------------------------------------------------------

    def transition(
        self,
        activity_id: str,
        target_status: str,
        reason: str = "",
        now_ts: Optional[float] = None,
        current_step: str = "",
    ) -> TransitionResult:
        """
        执行一次生命周期转换（`EF-2` / `EF-7`）。

        规则：
            * 只允许 `ALLOWED_TRANSITIONS` 中的转换（`EF-2`）
            * 终态不可逆（`EF-3`）
            * 进入终态时记录 `ended_at`
            * 目标为 `CANCELLED` 时**必须**携带 `reason`（`EF-5`）
            * **不产生 Event**（`EF-6`：D-2 不实现 Event 生产）
            * **不因 `expected_end_at` 到期而自动结束**（`EP-5`）
        """
        current = self._activities.get(activity_id)
        if current is None:
            return TransitionResult(False, None, f"activity_id 不存在：{activity_id}")

        src = current.status
        dst = target_status

        if dst not in LIFECYCLE_STATUSES:
            return TransitionResult(False, None, f"未知状态：{dst}（EF-1）")

        if is_terminal(src):
            return TransitionResult(
                False, None,
                f"EF-3：{src} 是终态，不可逆；拒绝 {src} → {dst}",
            )

        if not can_transition(src, dst):
            return TransitionResult(
                False, None,
                f"EF-2：不允许的跳跃 {src} → {dst}；"
                f"允许目标：{list(allowed_next_statuses(src))}",
            )

        if dst in REASON_REQUIRED_TARGETS and not (reason or "").strip():
            return TransitionResult(
                False, None,
                f"EF-5：转换到 {dst} 必须携带原因，不得静默取消",
            )

        ts = self._now(now_ts)
        updates: Dict[str, Any] = {"status": dst}

        if current_step:
            updates["current_step"] = current_step

        # 进入「进行中」某阶段时记录开始时间（仅首次）
        if dst in (STATUS_TRAVELING, STATUS_ACTIVE) and not current.started_at:
            updates["started_at"] = ts

        if dst in CLOSING_STATUSES:
            updates["ended_at"] = ts
            if reason:
                updates["end_reason"] = reason

        updated = replace(current, **updates)
        self._store(updated)
        return TransitionResult(True, updated, "")

    # --- 语义化便捷方法（全部走 transition，不绕过规则） ---------------

    def start_travel(self, activity_id: str, **kw: Any) -> TransitionResult:
        """PLANNED → TRAVELING。"""
        return self.transition(activity_id, STATUS_TRAVELING, **kw)

    def mark_arrived(self, activity_id: str, **kw: Any) -> TransitionResult:
        """TRAVELING → ARRIVED。"""
        return self.transition(activity_id, STATUS_ARRIVED, **kw)

    def activate(self, activity_id: str, **kw: Any) -> TransitionResult:
        """ARRIVED → ACTIVE，或 PAUSED → ACTIVE（恢复，不换 identity —— EI-5）。"""
        return self.transition(activity_id, STATUS_ACTIVE, **kw)

    def pause(self, activity_id: str, **kw: Any) -> TransitionResult:
        """ACTIVE → PAUSED（可恢复的中断 —— EI-2）。"""
        return self.transition(activity_id, STATUS_PAUSED, **kw)

    def complete(self, activity_id: str, **kw: Any) -> TransitionResult:
        """ACTIVE → COMPLETED（自然结束）。"""
        return self.transition(activity_id, STATUS_COMPLETED, **kw)

    def cancel(self, activity_id: str, reason: str, **kw: Any) -> TransitionResult:
        """
        任意非终态 → CANCELLED（终止；**必须**携带原因 —— EF-5 / EI-4）。

        注意与 `pause()` 的语义区分（`EI-2` / `EI-3`）：
            中断可恢复 → `pause()`
            过程终止   → `cancel()`
        **禁止**把一切打断一律处理为 CANCELLED。
        """
        return self.transition(activity_id, STATUS_CANCELLED, reason=reason, **kw)

    # ------------------------------------------------------------------
    # 6.4 primary / secondary binding（EE-5 ～ EE-8 / EK-1 ～ EK-4）
    # ------------------------------------------------------------------

    def bind(
        self,
        entity: str,
        activity_id: str,
        kind: str = BINDING_SECONDARY,
    ) -> None:
        """
        建立 **binding**（`EE-7`）。

        ⚠️ **binding 是「绑定关系」，不是「所有权」**（`EE-8`）。
        Activity 的真相始终在 Registry 中，AgentRuntime 只持有 id。

        约束：
            * 一个实体最多一个 `primary`（`EK-1` / `EK-3`）
            * 可以有多个 `secondary`（`EK-2`）
            * 绑定 primary 时，**不会**自动改变其他 Activity 的状态
              （D-2 不实现抢占 / 优先级 —— `EK-5`）
        """
        if kind not in BINDING_KINDS:
            raise ActivityRegistryError(f"未知 binding 类型：{kind}")
        if not self.exists(activity_id):
            raise ActivityRegistryError(f"activity_id 不存在：{activity_id}")

        table = self._bindings.setdefault(entity, {})

        if kind == BINDING_PRIMARY:
            existing = [
                aid for aid, k in table.items() if k == BINDING_PRIMARY and aid != activity_id
            ]
            if existing:
                raise ActivityRegistryError(
                    "EK-1 / EK-3：该实体已存在 primary binding，"
                    f"禁止第二个 primary（现有：{existing}）；"
                    "D-2 不实现抢占（EK-5）"
                )
        table[activity_id] = kind

    def unbind(self, entity: str, activity_id: str) -> None:
        """解除 binding（不影响 Activity 本身的状态）。"""
        table = self._bindings.get(entity)
        if not table:
            return
        table.pop(activity_id, None)
        if not table:
            self._bindings.pop(entity, None)

    def bindings_of(self, entity: str) -> Dict[str, str]:
        """返回该实体的 binding 表**副本**（`{activity_id: kind}`）。"""
        return dict(self._bindings.get(entity, {}))

    def primary_activity_id(self, entity: str) -> str:
        """该实体的 primary Activity id；无则返回空字符串。"""
        table = self._bindings.get(entity, {})
        for aid, kind in table.items():
            if kind == BINDING_PRIMARY:
                return aid
        return ""

    def primary_activity(self, entity: str) -> Optional[Activity]:
        """该实体的 primary Activity；无则 None。"""
        aid = self.primary_activity_id(entity)
        return self._activities.get(aid) if aid else None

    def secondary_activity_ids(self, entity: str) -> List[str]:
        """该实体的全部 secondary Activity id（排序后返回）。"""
        table = self._bindings.get(entity, {})
        return sorted(aid for aid, kind in table.items() if kind == BINDING_SECONDARY)

    def bound_activities(self, entity: str) -> List[Activity]:
        """该实体已绑定的全部 Activity（primary 优先，其余按 id 排序）。"""
        table = self._bindings.get(entity, {})
        primaries = sorted(aid for aid, k in table.items() if k == BINDING_PRIMARY)
        secondaries = sorted(aid for aid, k in table.items() if k == BINDING_SECONDARY)
        out: List[Activity] = []
        for aid in primaries + secondaries:
            activity = self._activities.get(aid)
            if activity is not None:
                out.append(activity)
        return out

    # ------------------------------------------------------------------
    # 6.5 内部
    # ------------------------------------------------------------------

    def _store(self, activity: Activity) -> None:
        """
        写入 Registry（Runtime 内唯一真相 —— `EC-4`）。

        ⚠️ 这是「替换对象引用」，**不是**就地修改：
        旧对象因 frozen 且不被复用而自然失效，因此不存在两个真相。
        """
        self._activities[activity.activity_id] = activity
        self._type_index[activity.activity_id] = activity.type

    @staticmethod
    def _now(now_ts: Optional[float]) -> float:
        if isinstance(now_ts, (int, float)):
            return float(now_ts)
        return time.time()

    @staticmethod
    def _normalize_ids(values: Sequence[str], label: str) -> Tuple[str, ...]:
        """归一化 id 序列：仅保留非空 str，去重且保持顺序。"""
        if values is None:
            return ()
        if isinstance(values, (str, bytes)):
            raise ActivityRegistryError(f"{label} 必须是序列，不能是单个字符串")
        seen: List[str] = []
        for raw in values:
            if not isinstance(raw, str):
                continue
            name = raw.strip()
            if name and name not in seen:
                seen.append(name)
        return tuple(seen)

    @staticmethod
    def _normalize_role_map(
        role_map: Optional[Dict[str, str]],
        actors: Tuple[str, ...],
        participants: Tuple[str, ...],
    ) -> Dict[str, str]:
        """
        归一化 role_map（`EG-4`）。

        规则：
            * 键必须是该 Activity 的参与者（主体或参与者）
            * 值必须是非空字符串（取值集合未冻结 —— `EG-10`）
            * **不**为未显式登记的实体补默认角色（由 `Activity.role_of` 推断）
        """
        if not role_map:
            return {}
        if not isinstance(role_map, dict):
            raise ActivityRegistryError("role_map 必须是 dict")
        allowed = set(actors) | set(participants)
        out: Dict[str, str] = {}
        for entity, role in role_map.items():
            if entity not in allowed:
                raise ActivityRegistryError(
                    f"EG-4：role_map 的键必须是该 Activity 的参与者；"
                    f"未参与者：{entity}"
                )
            if not isinstance(role, str) or not role.strip():
                raise ActivityRegistryError(
                    f"EG-4：role_map[{entity}] 必须是非空角色标识"
                )
            out[entity] = role.strip()
        return out


# =========================================================
# 7. 自描述 / 边界声明（便于审计；不产生副作用）
# =========================================================


def describe_activity_module() -> Dict[str, Any]:
    """
    只读自描述：诚实声明本模块实现了什么、**没有**实现什么。

    对应 Contract `EC-*` / `EO-*` / `EP-*` 的边界要求。
    """
    return {
        "module": "agent.activity",
        "phase": "D-2",
        "contract": "§5E (CC-20260930-06)",
        "domain_object": "Activity",
        "registry": "ActivityRegistry",
        "sot_identity": "Runtime-scoped Domain State",
        "lifecycle": list(LIFECYCLE_STATUSES),
        "terminal_statuses": list(TERMINAL_STATUSES),
        "initial_status": INITIAL_STATUS,
        "roles_base": list(BASE_ROLES),
        "binding_kinds": list(BINDING_KINDS),
        "implemented": (
            "Formal Activity Domain Object",
            "Runtime-scoped Activity Registry",
            "lifecycle（冻结转换表 + 终态不可逆）",
            "actor / participant / role",
            "primary / secondary binding",
            "基础查询 / 管理能力",
        ),
        "not_implemented": (
            "持久化（不写文件 / 不写数据库 / 不写 World 存储）",
            "World 存储中的 activity 顶层 key",
            "调度器 / 周期任务 / 后台轮询",
            "expected_end_at 自动完成",
            "Activity → Event 产生",
            "Capability 集成",
            "Movement 集成",
            "Motivation 接入",
            "Activity → Legacy 反向写入 / 双向同步",
            "World 事实副本",
        ),
        "notes": (
            "Activity = 持续世界过程，描述「谁正在经历什么」。"
            "本模块不落盘、不产生 Event、不承担调度职责。"
            "World SOT 仍是 main.data（ED-2）。"
        ),
    }


def get_lifecycle_table() -> Dict[str, Tuple[str, ...]]:
    """只读返回冻结的允许转换表（`EF-2`）。"""
    return {src: tuple(dsts) for src, dsts in ALLOWED_TRANSITIONS.items()}
