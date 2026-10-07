# -*- coding: utf-8 -*-
"""
docs/test_d2_activity_behavior.py
=================================

V3.1 Phase D-2 · Activity **Implementation Behavior Tests**
（Implementation Verification 阶段）

--------------------------------------------------------------------------
与 test_d2_activity_contract.py 的分工（重要）
--------------------------------------------------------------------------

    docs/test_d2_activity_contract.py
        = **架构边界**静态测试（import 边界 / 写入模式 / SOT / 文档一致性 …）
        它**不**验证运行时行为。

    本文件
        = **实现级行为**测试。
        它真正构造 `ActivityRegistry`、调用 API，验证行为是否正确。

    **为什么需要本文件（架构侧 D-2 Implementation Verification 要求）：**

        "目前只有实现，没有足够的实现级行为测试与真实运行证据，因此不得 Seal。"
        "把它从『看起来符合 Contract』推进到『行为上证明符合 Contract』。"

--------------------------------------------------------------------------
特别关注：frozen=True + mutable dict（immutable-boundary）
--------------------------------------------------------------------------

    `Activity` 是 `@dataclass(frozen=True)`。
    **但 frozen 只冻结属性重绑定，不冻结容器内容。**

    因此存在一个必须被证明或证伪的路径：

        registry.get(id)
              ↓
        activity.metadata["k"] = v      ← 是否能穿透？
        activity.role_map["x"] = "y"    ← 是否能穿透？
              ↓
        Registry 内部 Activity 真相是否被静默改变？

    本文件用 `test_i*` 组**直接验证该路径**，并**如实报告结果**。

    ⚠️ 无论结果是「已隔离」还是「可穿透」，都**不由本测试自行决定修复方案**。
       若确认可穿透，必须报告架构侧，由架构侧裁决：
           A. 修改实现，使嵌套结构真正隔离
           B. 明确 Contract 只要求属性级 frozen，接受该语义

--------------------------------------------------------------------------
设计原则
--------------------------------------------------------------------------

    * 只依赖标准库（unittest / ast / re / pathlib / sys / dataclasses）
    * **真的 import agent.activity**（它本身只依赖标准库）
    * 所有断言针对**行为**，不做生产代码文本扫描
    * 不从仓库根 import main / ext_*（避免引入 fastapi 等依赖）

--------------------------------------------------------------------------
如何运行
--------------------------------------------------------------------------

    从仓库根目录运行：

        python docs/test_d2_activity_behavior.py
        python -m unittest docs.test_d2_activity_behavior -v

    若执行环境不可用，必须如实报告：

        TEST NOT RUN
        Reason: environment execution unavailable

    不得把 TEST NOT RUN 当作 PASS。
"""

from __future__ import annotations

import ast
import re
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =========================================================
# 0. 仓库根：标记探测（兼容目录整理）
# =========================================================

_HERE = Path(__file__).resolve().parent


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / "main.py").is_file()
            and (candidate / "agent").is_dir()
            and (candidate / "ext").is_dir()
        ):
            return candidate
    return start.parent


ROOT = _find_repo_root(_HERE)
AGENT_DIR = ROOT / "agent"
DOCS_DIR = ROOT / "docs"
CONTRACT_DOC = DOCS_DIR / "V3.1_ARCHITECTURE_CONTRACT.md"
ACTIVITY_MODULE = AGENT_DIR / "activity.py"
PROJECT_DOC = DOCS_DIR / "PROJECT_V3.1_MASTER.md"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# agent.activity 只依赖标准库，因此可以安全 import
from agent import activity as act  # noqa: E402


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        try:
            return path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            return None


def _new_registry() -> "act.ActivityRegistry":
    return act.ActivityRegistry()


def _sample_activity(
    reg: "act.ActivityRegistry",
    **overrides: Any,
) -> "act.Activity":
    """创建一个标准测试 Activity（DATE：actor=AI，participant=User）。"""
    kwargs: Dict[str, Any] = {
        "type": "DATE",
        "actor_ids": ["白起"],
        "participant_ids": ["alice"],
        "role_map": {"白起": act.ROLE_ACTOR, "alice": act.ROLE_PARTNER},
        "location_id": "b2·会客厅",
        "metadata": {"note": "first", "nested": {"deep": [1, 2]}},
        "origin": "test-fixture",
    }
    kwargs.update(overrides)
    return reg.create_activity(**kwargs)


# =========================================================
# A. 创建与校验
# =========================================================

class AD2ActivityCreation(unittest.TestCase):
    """Activity 创建与字段校验（EA-7 / EG-2 / EQ-1 / EC-4）。"""

    def setUp(self) -> None:
        self.reg = _new_registry()

    def test_a1_create_returns_activity_in_planned(self) -> None:
        """创建成功返回 Activity，初始状态为 PLANNED（EF-1）。"""
        a = _sample_activity(self.reg)
        self.assertIsInstance(a, act.Activity)
        self.assertEqual(a.status, act.STATUS_PLANNED)
        self.assertEqual(a.type, "DATE")
        self.assertEqual(a.actor_ids, ("白起",))
        self.assertEqual(a.participant_ids, ("alice",))
        self.assertEqual(self.reg.count(), 1)

    def test_a2_activity_id_is_unique_and_nonempty(self) -> None:
        """`activity_id` 唯一且非空（EA-7 条件 1 / EC-4）。"""
        a1 = _sample_activity(self.reg)
        a2 = _sample_activity(self.reg)
        self.assertTrue(a1.activity_id)
        self.assertTrue(a2.activity_id)
        self.assertNotEqual(a1.activity_id, a2.activity_id)
        self.assertEqual(self.reg.count(), 2)

    def test_a3_duplicate_activity_id_rejected(self) -> None:
        """显式传入重复 `activity_id` 必须被拒绝（EC-4 / EE-3）。"""
        _sample_activity(self.reg, activity_id="act_fixed")
        with self.assertRaises(act.ActivityRegistryError):
            _sample_activity(self.reg, activity_id="act_fixed")

    def test_a4_type_must_be_nonempty(self) -> None:
        """`type` 必须是非空开放标识（EQ-1）。"""
        for bad in ("", "   "):
            with self.assertRaises(act.ActivityRegistryError):
                self.reg.create_activity(type=bad, actor_ids=["白起"])

    def test_a5_actor_ids_must_be_nonempty(self) -> None:
        """`actor_ids` 至少一个主体（EG-2 / EA-7 条件 3）。"""
        with self.assertRaises(act.ActivityRegistryError):
            self.reg.create_activity(type="DATE", actor_ids=[])

    def test_a6_actor_ids_normalized_dedup(self) -> None:
        """`actor_ids` / `participant_ids` 归一化：去重且保持顺序。"""
        a = self.reg.create_activity(
            type="MEETING",
            actor_ids=["白起", "白起", " 许墨 "],
            participant_ids=["alice", "alice"],
        )
        self.assertEqual(a.actor_ids, ("白起", "许墨"))
        self.assertEqual(a.participant_ids, ("alice",))

    def test_a7_role_map_keys_must_be_participants(self) -> None:
        """`role_map` 的键必须是该 Activity 的参与者（EG-4）。"""
        with self.assertRaises(act.ActivityRegistryError):
            self.reg.create_activity(
                type="DATE",
                actor_ids=["白起"],
                participant_ids=["alice"],
                role_map={"无关的人": act.ROLE_OBSERVER},
            )

    def test_a8_role_map_rejects_empty_role(self) -> None:
        """`role_map` 的值必须是非空角色标识（EG-4）。"""
        with self.assertRaises(act.ActivityRegistryError):
            self.reg.create_activity(
                type="DATE",
                actor_ids=["白起"],
                role_map={"白起": "   "},
            )

    def test_a9_role_of_infers_actor_and_participant(self) -> None:
        """未显式登记角色时，按主体/参与者推断（EG-4）。"""
        a = self.reg.create_activity(
            type="DATE", actor_ids=["白起"], participant_ids=["alice"]
        )
        self.assertEqual(a.role_of("白起"), act.ROLE_ACTOR)
        self.assertEqual(a.role_of("alice"), act.ROLE_PARTICIPANT)
        self.assertEqual(a.role_of("路人"), "")

    def test_a10_goal_and_commitment_are_optional(self) -> None:
        """`goal_id` / `commitment_ids` 可为空（EL-1 / EL-4）。"""
        a = _sample_activity(self.reg)
        self.assertEqual(a.goal_id, "")
        self.assertEqual(a.commitment_ids, ())

    def test_a11_at_least_one_actor_is_required_semantics(self) -> None:
        """`involves` / `all_entity_ids` 覆盖主体与参与者（EG-2 / EG-3）。"""
        a = _sample_activity(self.reg)
        self.assertTrue(a.involves("白起"))
        self.assertTrue(a.involves("alice"))
        self.assertFalse(a.involves("李泽言"))
        self.assertEqual(a.all_entity_ids(), ("白起", "alice"))


# =========================================================
# B. 生命周期
# =========================================================

class BD2Lifecycle(unittest.TestCase):
    """lifecycle 行为（EF-1 ～ EF-5 / EP-5 / EI-5）。"""

    def setUp(self) -> None:
        self.reg = _new_registry()

    def test_b1_all_allowed_transitions_succeed(self) -> None:
        """全部**合法**转换必须成功（EF-2）。"""
        for src, dst in (
            (act.STATUS_PLANNED, act.STATUS_TRAVELING),
            (act.STATUS_PLANNED, act.STATUS_CANCELLED),
            (act.STATUS_TRAVELING, act.STATUS_ARRIVED),
            (act.STATUS_TRAVELING, act.STATUS_CANCELLED),
            (act.STATUS_ARRIVED, act.STATUS_ACTIVE),
            (act.STATUS_ARRIVED, act.STATUS_CANCELLED),
            (act.STATUS_ACTIVE, act.STATUS_PAUSED),
            (act.STATUS_ACTIVE, act.STATUS_COMPLETED),
            (act.STATUS_ACTIVE, act.STATUS_CANCELLED),
            (act.STATUS_PAUSED, act.STATUS_ACTIVE),
            (act.STATUS_PAUSED, act.STATUS_CANCELLED),
        ):
            with self.subTest(f"{src} -> {dst}"):
                reg = _new_registry()
                a = _sample_activity(reg)
                # 先把状态推进到 src
                for step in self._path_to(src):
                    r = reg.transition(a.activity_id, step, reason="推进")
                    self.assertTrue(r.ok, f"推进到 {step} 失败：{r.reason}")
                reason = "测试取消" if dst == act.STATUS_CANCELLED else ""
                r = reg.transition(a.activity_id, dst, reason=reason)
                self.assertTrue(r.ok, f"{src} -> {dst} 应被允许，实际：{r.reason}")
                self.assertEqual(r.activity.status, dst)

    @staticmethod
    def _path_to(status: str) -> List[str]:
        paths = {
            act.STATUS_PLANNED: [],
            act.STATUS_TRAVELING: [act.STATUS_TRAVELING],
            act.STATUS_ARRIVED: [act.STATUS_TRAVELING, act.STATUS_ARRIVED],
            act.STATUS_ACTIVE: [
                act.STATUS_TRAVELING, act.STATUS_ARRIVED, act.STATUS_ACTIVE
            ],
            act.STATUS_PAUSED: [
                act.STATUS_TRAVELING, act.STATUS_ARRIVED,
                act.STATUS_ACTIVE, act.STATUS_PAUSED,
            ],
        }
        return list(paths.get(status, []))

    def test_b2_all_forbidden_jumps_rejected(self) -> None:
        """全部**非法跳跃**必须被拒绝（EF-2 / EF-3）。"""
        forbidden = (
            (act.STATUS_PLANNED, act.STATUS_ARRIVED),
            (act.STATUS_PLANNED, act.STATUS_ACTIVE),
            (act.STATUS_PLANNED, act.STATUS_PAUSED),
            (act.STATUS_PLANNED, act.STATUS_COMPLETED),
            (act.STATUS_TRAVELING, act.STATUS_ACTIVE),
            (act.STATUS_TRAVELING, act.STATUS_PAUSED),
            (act.STATUS_TRAVELING, act.STATUS_COMPLETED),
            (act.STATUS_ARRIVED, act.STATUS_PAUSED),
            (act.STATUS_ARRIVED, act.STATUS_COMPLETED),
            (act.STATUS_PAUSED, act.STATUS_COMPLETED),
        )
        for src, dst in forbidden:
            with self.subTest(f"{src} -/-> {dst}"):
                reg = _new_registry()
                a = _sample_activity(reg)
                for step in self._path_to(src):
                    reg.transition(a.activity_id, step, reason="推进")
                self.assertEqual(
                    reg.get(a.activity_id).status, src,
                    f"前置推进失败：期望 {src}",
                )
                r = reg.transition(a.activity_id, dst, reason="尝试")
                self.assertFalse(r.ok, f"{src} -> {dst} 必须被拒绝")
                self.assertIsNone(r.activity)
                self.assertTrue(r.reason, "拒绝必须给出可审计原因（EF-4）")
                # 状态不得被改变
                self.assertEqual(reg.get(a.activity_id).status, src)

    def test_b3_completed_is_terminal_and_irreversible(self) -> None:
        """`COMPLETED` 不可逆（EF-3）。"""
        a = _sample_activity(self.reg)
        self.reg.transition(a.activity_id, act.STATUS_TRAVELING, reason="x")
        self.reg.transition(a.activity_id, act.STATUS_ARRIVED, reason="x")
        self.reg.transition(a.activity_id, act.STATUS_ACTIVE, reason="x")
        self.assertTrue(self.reg.complete(a.activity_id).ok)

        for target in act.LIFECYCLE_STATUSES:
            with self.subTest(target=target):
                r = self.reg.transition(a.activity_id, target, reason="尝试复活")
                self.assertFalse(r.ok, f"COMPLETED -> {target} 必须被拒绝")
        self.assertEqual(self.reg.get(a.activity_id).status, act.STATUS_COMPLETED)

    def test_b4_cancelled_is_terminal_and_irreversible(self) -> None:
        """`CANCELLED` 不可逆（EF-3），且可从 PLANNED 直接取消。"""
        a = _sample_activity(self.reg)
        self.assertTrue(self.reg.cancel(a.activity_id, reason="计划取消").ok)

        for target in act.LIFECYCLE_STATUSES:
            with self.subTest(target=target):
                r = self.reg.transition(a.activity_id, target, reason="尝试复活")
                self.assertFalse(r.ok, f"CANCELLED -> {target} 必须被拒绝")
        self.assertEqual(self.reg.get(a.activity_id).status, act.STATUS_CANCELLED)

    def test_b5_cancelled_requires_reason(self) -> None:
        """`CANCELLED` 必须携带原因，不得静默取消（EF-5 / EI-4）。"""
        for bad_reason in ("", "   "):
            with self.subTest(reason=repr(bad_reason)):
                reg = _new_registry()
                a = _sample_activity(reg)
                r = reg.transition(a.activity_id, act.STATUS_CANCELLED, reason=bad_reason)
                self.assertFalse(r.ok, "无原因的 CANCELLED 必须被拒绝")
                self.assertEqual(reg.get(a.activity_id).status, act.STATUS_PLANNED)

    def test_b6_cancel_records_reason_and_ended_at(self) -> None:
        """取消成功后必须记录 `end_reason` 与 `ended_at`（EF-5 / EF-4）。"""
        a = _sample_activity(self.reg)
        r = self.reg.cancel(a.activity_id, reason="世界条件不允许", now_ts=1234.0)
        self.assertTrue(r.ok)
        self.assertEqual(r.activity.end_reason, "世界条件不允许")
        self.assertEqual(r.activity.ended_at, 1234.0)

    def test_b7_paused_to_active_keeps_same_activity_id(self) -> None:
        """`PAUSED → ACTIVE` 是**恢复**，不创建新 identity（EI-5）。"""
        a = _sample_activity(self.reg)
        aid = a.activity_id
        self.reg.transition(aid, act.STATUS_TRAVELING, reason="x")
        self.reg.transition(aid, act.STATUS_ARRIVED, reason="x")
        self.reg.transition(aid, act.STATUS_ACTIVE, reason="x")
        self.assertTrue(self.reg.pause(aid, reason="收到消息").ok)
        self.assertEqual(self.reg.get(aid).status, act.STATUS_PAUSED)

        r = self.reg.activate(aid, reason="回到约会")
        self.assertTrue(r.ok)
        self.assertEqual(r.activity.activity_id, aid, "恢复必须保持同一 activity_id")
        self.assertEqual(r.activity.status, act.STATUS_ACTIVE)
        self.assertEqual(self.reg.count(), 1, "恢复不得创建第二个 Activity")

    def test_b8_expected_end_at_does_not_auto_complete(self) -> None:
        """
        `expected_end_at` 到期**不等于**自动结束（EP-4 / EP-5）。

        这是防「Activity 退化为 Scheduler 包装」的关键行为。
        """
        a = self.reg.create_activity(
            type="WORK",
            actor_ids=["白起"],
            expected_end_at=1000.0,
        )
        self.reg.transition(a.activity_id, act.STATUS_TRAVELING, reason="x")
        self.reg.transition(a.activity_id, act.STATUS_ARRIVED, reason="x")
        self.reg.transition(a.activity_id, act.STATUS_ACTIVE, reason="x")

        # 用一个**远大于** expected_end_at 的 now_ts 触发各种读取
        far_future = 10_000_000.0
        self.assertEqual(
            self.reg.get(a.activity_id).status, act.STATUS_ACTIVE,
            "expected_end_at 到期后状态不得自动变化（EP-5）",
        )
        # 即使显式传入 now_ts，也不得自动完成
        r = self.reg.transition(a.activity_id, act.STATUS_ACTIVE, now_ts=far_future)
        self.assertFalse(r.ok, "ACTIVE -> ACTIVE 不是合法转换")
        self.assertEqual(
            self.reg.get(a.activity_id).status, act.STATUS_ACTIVE,
            "EP-5：到期不得自动结束；只有显式转换才能改变状态",
        )

    def test_b9_transition_rejects_unknown_status(self) -> None:
        """未知状态必须被拒绝（EF-1）。"""
        a = _sample_activity(self.reg)
        r = self.reg.transition(a.activity_id, "TELEPORTING", reason="x")
        self.assertFalse(r.ok)

    def test_b10_transition_rejects_unknown_activity_id(self) -> None:
        """不存在的 activity_id 必须被拒绝（不得抛异常作为控制流）。"""
        r = self.reg.transition("act_not_exist", act.STATUS_TRAVELING, reason="x")
        self.assertFalse(r.ok)
        self.assertIsNone(r.activity)

    def test_b11_require_raises_for_missing(self) -> None:
        """`require()` 对不存在的 id 抛错；`get()` 返回 None。"""
        self.assertIsNone(self.reg.get("act_not_exist"))
        with self.assertRaises(act.ActivityRegistryError):
            self.reg.require("act_not_exist")

    def test_b12_lifecycle_table_matches_contract_module(self) -> None:
        """模块导出的转换表必须与冻结语义一致（EF-2）。"""
        table = act.get_lifecycle_table()
        self.assertEqual(set(table.keys()), set(act.LIFECYCLE_STATUSES))
        for terminal in act.TERMINAL_STATUSES:
            self.assertEqual(table[terminal], (), f"{terminal} 必须无出边（EF-3）")
        for src, dsts in act.ALLOWED_TRANSITIONS.items():
            for dst in dsts:
                self.assertTrue(act.can_transition(src, dst))
        self.assertFalse(act.can_transition(act.STATUS_PLANNED, act.STATUS_COMPLETED))
        self.assertFalse(act.can_transition(act.STATUS_PAUSED, act.STATUS_COMPLETED))


# =========================================================
# C. primary / secondary binding
# =========================================================

class CD2Binding(unittest.TestCase):
    """binding 行为（EE-5 ～ EE-8 / EK-1 ～ EK-5）。"""

    def setUp(self) -> None:
        self.reg = _new_registry()

    def test_c1_at_most_one_primary(self) -> None:
        """同一实体最多一个 primary（EK-1 / EK-3）。"""
        a1 = _sample_activity(self.reg)
        a2 = _sample_activity(self.reg)
        self.reg.bind("白起", a1.activity_id, act.BINDING_PRIMARY)
        with self.assertRaises(act.ActivityRegistryError):
            self.reg.bind("白起", a2.activity_id, act.BINDING_PRIMARY)
        self.assertEqual(self.reg.primary_activity_id("白起"), a1.activity_id)

    def test_c2_multiple_secondary_allowed(self) -> None:
        """可以有多个 secondary（EK-2）。"""
        a1 = _sample_activity(self.reg)
        a2 = _sample_activity(self.reg)
        a3 = _sample_activity(self.reg)
        for a in (a1, a2, a3):
            self.reg.bind("白起", a.activity_id, act.BINDING_SECONDARY)
        self.assertEqual(
            self.reg.secondary_activity_ids("白起"),
            sorted([a1.activity_id, a2.activity_id, a3.activity_id]),
        )

    def test_c3_rebinding_same_primary_is_idempotent(self) -> None:
        """对**同一个** Activity 重复绑定 primary 不算冲突。"""
        a = _sample_activity(self.reg)
        self.reg.bind("白起", a.activity_id, act.BINDING_PRIMARY)
        self.reg.bind("白起", a.activity_id, act.BINDING_PRIMARY)
        self.assertEqual(self.reg.primary_activity_id("白起"), a.activity_id)

    def test_c4_binding_is_relationship_not_ownership(self) -> None:
        """
        primary / secondary 是**绑定关系**，不是 Activity 所有权（EE-8）。

        验证：binding 只存在于 Registry 的绑定表；
        Activity 真相始终由 Registry 持有；未绑定也能取到 Activity。
        """
        a = _sample_activity(self.reg)
        # 未绑定时 Activity 依然存在且可取
        self.assertIsNotNone(self.reg.get(a.activity_id))
        self.assertEqual(self.reg.primary_activity_id("白起"), "")

        self.reg.bind("白起", a.activity_id, act.BINDING_PRIMARY)
        self.assertEqual(self.reg.primary_activity_id("白起"), a.activity_id)
        # binding 不改变 Activity 本身
        self.assertEqual(
            self.reg.get(a.activity_id).status, act.STATUS_PLANNED,
            "binding 不得改变 Activity 生命周期状态",
        )
        # 解除绑定后 Activity 仍然存在（所有权未变）
        self.reg.unbind("白起", a.activity_id)
        self.assertIsNotNone(self.reg.get(a.activity_id), "unbind 不得删除 Activity")
        self.assertEqual(self.reg.primary_activity_id("白起"), "")

    def test_c5_bind_requires_existing_activity(self) -> None:
        """不得绑定不存在的 Activity。"""
        with self.assertRaises(act.ActivityRegistryError):
            self.reg.bind("白起", "act_not_exist", act.BINDING_PRIMARY)

    def test_c6_bind_rejects_unknown_kind(self) -> None:
        """未知 binding 类型必须被拒绝。"""
        a = _sample_activity(self.reg)
        with self.assertRaises(act.ActivityRegistryError):
            self.reg.bind("白起", a.activity_id, "tertiary")

    def test_c7_unbind_does_not_change_lifecycle(self) -> None:
        """`unbind` 不改变 Activity lifecycle。"""
        a = _sample_activity(self.reg)
        self.reg.bind("白起", a.activity_id, act.BINDING_PRIMARY)
        self.reg.transition(a.activity_id, act.STATUS_TRAVELING, reason="x")
        before = self.reg.get(a.activity_id).status
        self.reg.unbind("白起", a.activity_id)
        self.assertEqual(
            self.reg.get(a.activity_id).status, before,
            "unbind 不得改变 Activity 生命周期",
        )
        self.assertEqual(before, act.STATUS_TRAVELING)

    def test_c8_primary_binding_does_not_preempt_other_activity(self) -> None:
        """绑定 primary **不会**自动改变其他 Activity 状态（EK-5：不实现抢占）。"""
        a1 = _sample_activity(self.reg)
        a2 = _sample_activity(self.reg)
        self.reg.bind("白起", a1.activity_id, act.BINDING_PRIMARY)
        self.reg.bind("白起", a2.activity_id, act.BINDING_SECONDARY)

        self.reg.transition(a1.activity_id, act.STATUS_TRAVELING, reason="x")
        self.reg.transition(a1.activity_id, act.STATUS_ARRIVED, reason="x")
        self.reg.transition(a1.activity_id, act.STATUS_ACTIVE, reason="x")
        self.reg.bind("白起", a1.activity_id, act.BINDING_PRIMARY)

        # 切换到 a2 为 primary 是不允许的（已有 primary）—— 且不得悄悄抢占
        with self.assertRaises(act.ActivityRegistryError):
            self.reg.bind("白起", a2.activity_id, act.BINDING_PRIMARY)
        self.assertEqual(
            self.reg.get(a1.activity_id).status, act.STATUS_ACTIVE,
            "EK-5：不得因绑定操作而抢占 / 改变既有 Activity",
        )

    def test_c9_secondary_removal_does_not_affect_primary(self) -> None:
        """解除某个 secondary 不影响 primary 绑定。"""
        a1 = _sample_activity(self.reg)
        a2 = _sample_activity(self.reg)
        self.reg.bind("白起", a1.activity_id, act.BINDING_PRIMARY)
        self.reg.bind("白起", a2.activity_id, act.BINDING_SECONDARY)
        self.reg.unbind("白起", a2.activity_id)
        self.assertEqual(self.reg.primary_activity_id("白起"), a1.activity_id)
        self.assertEqual(self.reg.secondary_activity_ids("白起"), [])


# =========================================================
# D. Registry 唯一真相与容器隔离
# =========================================================

class DD2RegistryTruth(unittest.TestCase):
    """Registry 是唯一 Activity 真相（EC-4 / EE-1 ～ EE-4）。"""

    def setUp(self) -> None:
        self.reg = _new_registry()

    def test_d1_registry_is_single_source_of_truth(self) -> None:
        """
        同一 id 在 Registry 中只有一个 Activity 真相（EC-4 / EE-3）。

        ⚠️ 断言语义修正（隔离修复后）：

            原断言用 `assertIs` 检查「三次读取返回同一对象」——
            那**要求返回内部引用**，与架构侧裁决 A 的隔离要求**直接冲突**。

            `EC-4` 的真正含义是「Registry 中只有一个**真相**」，
            **不是**「对外必须返回同一对象」。

            因此改为验证：
                ① 同一 id 只能得到同一个 identity（内容一致）
                ② 对外返回的是**快照**（不是内部引用）
                ③ 外部修改快照**不会**影响 Registry 真相
        """
        a = _sample_activity(self.reg)
        aid = a.activity_id

        first = self.reg.get(aid)
        second = self.reg.get(aid)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)

        # ① identity 一致（同一 Activity）
        self.assertEqual(first.activity_id, aid)
        self.assertEqual(second.activity_id, aid)
        self.assertEqual(first.status, second.status)
        self.assertEqual(first.type, second.type)

        # ② 对外是快照：两次读取互相独立（不暴露内部引用）
        self.assertIsNot(first, second, "对外应返回快照，而非内部引用")

        # ③ 修改快照不影响 Registry 真相
        try:
            first.metadata["tampered"] = "x"  # type: ignore[index]
        except TypeError:
            pass
        self.assertNotIn(
            "tampered", self.reg.get(aid).metadata,
            "EC-4：外部快照的修改不得改变 Registry 内的唯一真相",
        )

    def test_d2_transition_replaces_object_not_mutates(self) -> None:
        """转换产生**新对象**，旧对象不被就地修改（frozen 语义）。"""
        a = _sample_activity(self.reg)
        r = self.reg.transition(a.activity_id, act.STATUS_TRAVELING, reason="x")
        self.assertTrue(r.ok)
        self.assertIsNot(r.activity, a, "转换应产生新对象")
        self.assertEqual(a.status, act.STATUS_PLANNED, "旧对象不得被就地修改")
        self.assertEqual(
            self.reg.get(a.activity_id).status, act.STATUS_TRAVELING,
            "Registry 内的真相必须已更新",
        )

    def test_d3_list_methods_do_not_expose_internal_container(self) -> None:
        """`list_*` 不暴露内部容器（修改返回值不影响 Registry）。"""
        a1 = _sample_activity(self.reg)
        a2 = _sample_activity(self.reg)

        lst = self.reg.list_all()
        self.assertEqual(len(lst), 2)
        lst.clear()          # 外部清空返回列表
        lst.append("HACK")   # 外部追加
        self.assertEqual(self.reg.count(), 2, "list_all 返回值不得是内部容器")
        self.assertEqual(len(self.reg.list_all()), 2)

        for probe in (
            self.reg.list_by_status(act.STATUS_PLANNED),
            self.reg.list_by_type("DATE"),
            self.reg.list_by_entity("白起"),
            self.reg.list_by_actor("白起"),
            self.reg.list_by_participant("alice"),
            self.reg.list_by_location("b2·会客厅"),
            self.reg.list_open(),
        ):
            probe.clear()
        self.assertEqual(self.reg.count(), 2, "任何 list_* 都不得暴露内部容器")
        self.assertTrue(self.reg.exists(a1.activity_id))
        self.assertTrue(self.reg.exists(a2.activity_id))

    def test_d4_bindings_of_returns_copy(self) -> None:
        """`bindings_of` 返回副本（修改不影响 Registry）。"""
        a = _sample_activity(self.reg)
        self.reg.bind("白起", a.activity_id, act.BINDING_PRIMARY)
        snapshot = self.reg.bindings_of("白起")
        snapshot.clear()
        snapshot["FAKE"] = act.BINDING_PRIMARY
        self.assertEqual(
            self.reg.primary_activity_id("白起"), a.activity_id,
            "bindings_of 返回值不得是内部绑定表",
        )

    def test_d5_bound_activities_returns_new_list(self) -> None:
        """`bound_activities` 返回新列表（顺序：primary 优先）。"""
        a1 = _sample_activity(self.reg)
        a2 = _sample_activity(self.reg)
        self.reg.bind("白起", a1.activity_id, act.BINDING_SECONDARY)
        self.reg.bind("白起", a2.activity_id, act.BINDING_PRIMARY)
        out = self.reg.bound_activities("白起")
        self.assertEqual([x.activity_id for x in out], [a2.activity_id, a1.activity_id])
        out.clear()
        self.assertEqual(len(self.reg.bound_activities("白起")), 2)

    def test_d6_to_dict_returns_copy(self) -> None:
        """
        `to_dict()` 返回**可变副本**，但与内部真相**无共享引用**。

        注：输出侧隔离后，返回的 `role_map` / `metadata` 是**新构造**的
        dict（内部真相保存冻结版本），因此这里的修改是安全的 ——
        只要它们不穿透到 Registry 即可。
        """
        activity = _sample_activity(self.reg)
        aid = activity.activity_id

        a = self.reg.get(aid)
        d = a.to_dict()
        d["status"] = "HACKED"
        d["actor_ids"].append("HACK")
        d["metadata"]["note"] = "HACKED"
        d["role_map"]["白起"] = "HACKED"

        fresh = self.reg.get(aid)
        self.assertEqual(fresh.status, act.STATUS_PLANNED)
        self.assertEqual(fresh.actor_ids, ("白起",))
        self.assertEqual(
            fresh.metadata.get("note"), "first",
            "to_dict() 的 metadata 不得与内部真相共享引用",
        )
        self.assertEqual(
            fresh.role_map.get("白起"), act.ROLE_ACTOR,
            "to_dict() 的 role_map 不得与内部真相共享引用",
        )

    def test_d7_to_dict_covers_all_documented_fields(self) -> None:
        """`to_dict()` 必须覆盖 §5E.18 的全部字段语义。"""
        a = _sample_activity(self.reg)
        d = a.to_dict()
        for key in (
            "activity_id", "type", "actor_ids", "participant_ids", "role_map",
            "location_id", "status", "started_at", "expected_end_at", "ended_at",
            "goal_id", "commitment_ids", "current_step", "origin", "metadata",
        ):
            self.assertIn(key, d, f"to_dict 必须包含字段 {key}")

    def test_d8_no_stray_activity_from_failed_operations(self) -> None:
        """失败的创建 / 转换不得留下半成品 Activity。"""
        before = self.reg.count()
        with self.assertRaises(act.ActivityRegistryError):
            self.reg.create_activity(type="", actor_ids=["白起"])
        with self.assertRaises(act.ActivityRegistryError):
            self.reg.create_activity(type="DATE", actor_ids=[])
        self.assertEqual(self.reg.count(), before, "失败的创建不得写入 Registry")


# =========================================================
# E. 不可变边界（frozen=True + mutable dict）
# =========================================================

class ED2ImmutableBoundary(unittest.TestCase):
    """
    **immutable-boundary 行为证明**（架构侧裁决 A）。

    核心语义（必须被证明，而不是被假设）：

        内部真相 = **永远冻结**
        对外返回 = **防穿透快照**（与内部无共享引用）

    必须覆盖**全部返回 Activity 的路径**：

        get() / require() / list_*() / primary_activity() / bound_activities()
        / create_activity() / transition().activity

    以及**输入侧别名**：

        调用方传入的 metadata / role_map **不得**保留外部可变别名。

    ⚠️ 本组**不指定实现方式**（深拷贝 / MappingProxyType / tuple 均可），
       只验证**架构行为**：外部引用无法改变 Registry 内部真相。
    """

    def setUp(self) -> None:
        self.reg = _new_registry()
        self.activity = _sample_activity(self.reg)
        self.aid = self.activity.activity_id

    # --- 基础：frozen 到底保证什么 -------------------------------

    def test_e1_frozen_blocks_attribute_rebinding(self) -> None:
        """`frozen=True` 必须阻止**属性重绑定**（这是它真正保证的东西）。"""
        a = self.reg.get(self.aid)
        with self.assertRaises((FrozenInstanceError, Exception)):
            a.status = act.STATUS_ACTIVE  # type: ignore[misc]
        with self.assertRaises((FrozenInstanceError, Exception)):
            a.type = "HACKED"  # type: ignore[misc]
        self.assertEqual(self.reg.get(self.aid).status, act.STATUS_PLANNED)

    def test_e2_transition_does_not_fork_truth(self) -> None:
        """转换后 Registry 真相以**新对象**为准，不产生分叉真相。"""
        old = self.reg.get(self.aid)
        r = self.reg.transition(self.aid, act.STATUS_TRAVELING, reason="x")
        self.assertTrue(r.ok)
        self.assertEqual(old.status, act.STATUS_PLANNED, "旧快照不得被就地修改")
        self.assertEqual(self.reg.get(self.aid).status, act.STATUS_TRAVELING)
        self.assertIsNot(self.reg.get(self.aid), old)

    # --- 输出侧：全部返回路径必须防穿透 -------------------------

    def test_e3_get_nested_penetration_blocked(self) -> None:
        """
        【架构侧指定反向测试】`get()` 不允许嵌套结构穿透。

            a = registry.get(id)
            a.metadata["x"] = "attacker"
            b = registry.get(id)
            assert b.metadata["x"] != "attacker"
        """
        a = self.reg.get(self.aid)
        self.assertIsNotNone(a)
        try:
            a.metadata["x"] = "attacker"  # type: ignore[index]
        except TypeError:
            pass  # 不可变视图也满足隔离语义

        b = self.reg.get(self.aid)
        self.assertNotEqual(
            b.metadata.get("x"), "attacker",
            "IMMUTABLE-BOUNDARY VIOLATION：get() 的嵌套结构被穿透",
        )

    def test_e4_get_role_map_penetration_blocked(self) -> None:
        """
        【架构侧指定反向测试】`get()` 的 `role_map` 不允许穿透。

            a = registry.get(id)
            a.role_map["someone"] = "forged"
            b = registry.get(id)
            assert "someone" not in b.role_map
        """
        a = self.reg.get(self.aid)
        self.assertIsNotNone(a)
        try:
            a.role_map["someone"] = "forged"  # type: ignore[index]
        except TypeError:
            pass

        b = self.reg.get(self.aid)
        self.assertNotIn(
            "someone", b.role_map,
            "IMMUTABLE-BOUNDARY VIOLATION：get() 的 role_map 被穿透",
        )

    def test_e5_get_deeply_nested_penetration_blocked(self) -> None:
        """深层嵌套（dict → dict → list）也**不得**穿透。"""
        a = self.reg.get(self.aid)
        nested = a.metadata.get("nested")
        if isinstance(nested, dict):
            deep = nested.get("deep")
            if isinstance(deep, list):
                deep.append("INJECTED")
            else:
                self.fail("夹具必须包含 metadata['nested']['deep'] 为 list")

        b = self.reg.get(self.aid)
        observed = b.metadata.get("nested", {})
        observed_deep = observed.get("deep", []) if isinstance(observed, dict) else []
        self.assertNotIn(
            "INJECTED", list(observed_deep),
            "IMMUTABLE-BOUNDARY VIOLATION：深层嵌套 list 被穿透",
        )

    def test_e6_require_path_blocked(self) -> None:
        """`require()` 路径与 `get()` 同级隔离。"""
        a = self.reg.require(self.aid)
        try:
            a.metadata["via_require"] = "attacker"  # type: ignore[index]
        except TypeError:
            pass
        b = self.reg.require(self.aid)
        self.assertNotIn(
            "via_require", b.metadata,
            "IMMUTABLE-BOUNDARY VIOLATION：require() 路径被穿透",
        )

    def test_e7_list_paths_blocked(self) -> None:
        """**全部** `list_*` 路径的每项都必须防穿透。"""
        self.reg.bind("白起", self.aid, act.BINDING_PRIMARY)
        self.reg.transition(self.aid, act.STATUS_TRAVELING, reason="x")

        probes = {
            "list_all": self.reg.list_all(),
            "list_by_status": self.reg.list_by_status(act.STATUS_TRAVELING),
            "list_by_type": self.reg.list_by_type("DATE"),
            "list_by_entity": self.reg.list_by_entity("白起"),
            "list_by_actor": self.reg.list_by_actor("白起"),
            "list_by_participant": self.reg.list_by_participant("alice"),
            "list_by_location": self.reg.list_by_location("b2·会客厅"),
            "list_open": self.reg.list_open(),
        }
        for label, items in probes.items():
            self.assertTrue(items, f"{label} 应返回至少一项（夹具问题）")
            for item in items:
                try:
                    item.metadata[f"via_{label}"] = "attacker"  # type: ignore[index]
                    item.role_map["forged"] = "x"  # type: ignore[index]
                except TypeError:
                    pass

        fresh = self.reg.get(self.aid)
        for label in probes:
            self.assertNotIn(
                f"via_{label}", fresh.metadata,
                f"IMMUTABLE-BOUNDARY VIOLATION：{label} 路径被穿透",
            )
        self.assertNotIn(
            "forged", fresh.role_map,
            "IMMUTABLE-BOUNDARY VIOLATION：list_* 的 role_map 被穿透",
        )

    def test_e8_primary_and_bound_paths_blocked(self) -> None:
        """`primary_activity()` / `bound_activities()` 路径防穿透。"""
        self.reg.bind("白起", self.aid, act.BINDING_PRIMARY)

        primary = self.reg.primary_activity("白起")
        self.assertIsNotNone(primary)
        try:
            primary.metadata["via_primary"] = "attacker"  # type: ignore[index]
            primary.role_map["forged_primary"] = "x"  # type: ignore[index]
        except TypeError:
            pass

        bound = self.reg.bound_activities("白起")
        self.assertTrue(bound)
        for item in bound:
            try:
                item.metadata["via_bound"] = "attacker"  # type: ignore[index]
                item.role_map["forged_bound"] = "x"  # type: ignore[index]
            except TypeError:
                pass

        fresh = self.reg.get(self.aid)
        self.assertNotIn(
            "via_primary", fresh.metadata,
            "IMMUTABLE-BOUNDARY VIOLATION：primary_activity() 路径被穿透",
        )
        self.assertNotIn(
            "forged_primary", fresh.role_map,
            "IMMUTABLE-BOUNDARY VIOLATION：primary_activity() 的 role_map 被穿透",
        )
        self.assertNotIn(
            "via_bound", fresh.metadata,
            "IMMUTABLE-BOUNDARY VIOLATION：bound_activities() 路径被穿透",
        )
        self.assertNotIn(
            "forged_bound", fresh.role_map,
            "IMMUTABLE-BOUNDARY VIOLATION：bound_activities() 的 role_map 被穿透",
        )

    def test_e9_transition_result_blocked(self) -> None:
        """`transition().activity` 也必须防穿透。"""
        r = self.reg.transition(self.aid, act.STATUS_TRAVELING, reason="x")
        self.assertTrue(r.ok)
        try:
            r.activity.metadata["via_transition"] = "attacker"  # type: ignore[index]
            r.activity.role_map["forged_transition"] = "x"  # type: ignore[index]
        except TypeError:
            pass

        fresh = self.reg.get(self.aid)
        self.assertNotIn(
            "via_transition", fresh.metadata,
            "IMMUTABLE-BOUNDARY VIOLATION：transition().activity 被穿透",
        )
        self.assertNotIn(
            "forged_transition", fresh.role_map,
            "IMMUTABLE-BOUNDARY VIOLATION：transition().activity 的 role_map 被穿透",
        )

    def test_e10_create_return_value_blocked(self) -> None:
        """`create_activity()` 的返回值也必须防穿透。"""
        created = _sample_activity(self.reg)
        try:
            created.metadata["via_create"] = "attacker"  # type: ignore[index]
        except TypeError:
            pass
        fresh = self.reg.get(created.activity_id)
        self.assertNotIn(
            "via_create", fresh.metadata,
            "IMMUTABLE-BOUNDARY VIOLATION：create_activity() 返回值被穿透",
        )

    # --- 输入侧：不得保留外部别名 -------------------------------

    def test_e11_input_metadata_alias_isolated(self) -> None:
        """
        输入侧隔离：调用方**事后修改**自己传入的 metadata，
        不得改变 Activity。
        """
        caller_metadata: Dict[str, Any] = {
            "note": "original",
            "nested": {"deep": [1, 2]},
        }
        a = self.reg.create_activity(
            type="DATE", actor_ids=["白起"], metadata=caller_metadata
        )

        # 调用方事后修改自己的 dict（含嵌套）
        caller_metadata["note"] = "CHANGED-AFTER-CREATE"
        caller_metadata["injected"] = "attacker"
        caller_metadata["nested"]["deep"].append(999)

        fresh = self.reg.get(a.activity_id)
        self.assertEqual(
            fresh.metadata.get("note"), "original",
            "IMMUTABLE-BOUNDARY VIOLATION：输入 metadata 产生外部别名",
        )
        self.assertNotIn(
            "injected", fresh.metadata,
            "IMMUTABLE-BOUNDARY VIOLATION：输入 metadata 的顶层被外部别名影响",
        )
        deep = fresh.metadata.get("nested", {}).get("deep", [])
        self.assertNotIn(
            999, list(deep),
            "IMMUTABLE-BOUNDARY VIOLATION：输入 metadata 的嵌套 list 被外部别名影响",
        )

    def test_e12_input_role_map_alias_isolated(self) -> None:
        """输入侧隔离：调用方事后修改 `role_map` 不得改变 Activity。"""
        caller_roles: Dict[str, str] = {"白起": act.ROLE_ACTOR, "alice": act.ROLE_PARTNER}
        a = self.reg.create_activity(
            type="DATE",
            actor_ids=["白起"],
            participant_ids=["alice"],
            role_map=caller_roles,
        )

        caller_roles["白起"] = "FORGED-AFTER-CREATE"
        caller_roles["intruder"] = "forged"

        fresh = self.reg.get(a.activity_id)
        self.assertEqual(
            fresh.role_map.get("白起"), act.ROLE_ACTOR,
            "IMMUTABLE-BOUNDARY VIOLATION：输入 role_map 产生外部别名",
        )
        self.assertNotIn(
            "intruder", fresh.role_map,
            "IMMUTABLE-BOUNDARY VIOLATION：输入 role_map 被外部别名影响",
        )

    def test_e13_two_reads_are_independent(self) -> None:
        """两次读取返回的对象必须**互相独立**（且都与内部真相独立）。"""
        a = self.reg.get(self.aid)
        b = self.reg.get(self.aid)
        self.assertIsNot(a, b, "两次读取应返回不同对象（防穿透快照）")

        try:
            a.metadata["only_in_a"] = "x"  # type: ignore[index]
        except TypeError:
            pass

        self.assertNotIn(
            "only_in_a", b.metadata,
            "IMMUTABLE-BOUNDARY VIOLATION：两次读取共享同一容器",
        )
        self.assertNotIn(
            "only_in_a", self.reg.get(self.aid).metadata,
            "IMMUTABLE-BOUNDARY VIOLATION：读取快照与内部真相共享容器",
        )

    def test_e14_direct_construction_is_also_isolated(self) -> None:
        """
        即使用户**绕过 Registry** 直接构造 Activity，
        容器也不得被外部别名穿透（构造期冻结）。
        """
        caller_metadata: Dict[str, Any] = {"note": "direct"}
        direct = act.Activity(
            activity_id="act_direct",
            type="DATE",
            actor_ids=("白起",),
            role_map={"白起": act.ROLE_ACTOR},
            metadata=caller_metadata,
        )
        caller_metadata["note"] = "CHANGED"
        caller_metadata["late"] = "attacker"

        # 直接构造的对象：容器应为冻结视图（写操作抛错）
        #   —— 无论实现方式如何，行为要求是「外部不能改变它」
        try:
            direct.metadata["late2"] = "attacker"  # type: ignore[index]
            mutated = True
        except TypeError:
            mutated = False

        if mutated:
            self.fail(
                "IMMUTABLE-BOUNDARY VIOLATION：直接构造的 Activity "
                "允许就地修改 metadata（构造期未冻结）"
            )
        self.assertNotIn(
            "late", direct.metadata,
            "IMMUTABLE-BOUNDARY VIOLATION：直接构造保留输入别名",
        )

    def test_e15_activity_is_frozen_dataclass(self) -> None:
        """`Activity` 必须确实是 frozen dataclass（EC-1 的基础）。"""
        import dataclasses

        self.assertTrue(dataclasses.is_dataclass(act.Activity))
        params = getattr(act.Activity, "__dataclass_params__", None)
        self.assertIsNotNone(params)
        self.assertTrue(params.frozen, "Activity 必须是 frozen dataclass")


# =========================================================
# F. 不产生 Event / 不写 World / 不持久化 / 不依赖 scheduler
# =========================================================

class FD2ExternalCoupling(unittest.TestCase):
    """
    外部耦合边界（EB-13 / EO-* / EP-6 / ET-1）。

    本组为**模块级**断言：Activity 必须与 Event / World 存储 /
    持久化 / 调度器 / Motivation 解耦。
    """

    def _effective_code(self) -> str:
        import io
        import tokenize

        src = _read_text(ACTIVITY_MODULE)
        self.assertIsNotNone(src, f"必须存在 {ACTIVITY_MODULE}")
        try:
            tokens = []
            for tok in tokenize.generate_tokens(io.StringIO(src or "").readline):
                if tok.type == tokenize.COMMENT:
                    continue
                if tok.type == tokenize.STRING:
                    tokens.append(tokenize.TokenInfo(
                        type=tokenize.STRING,
                        string='""',
                        start=tok.start,
                        end=tok.end,
                        line=tok.line,
                    ))
                    continue
                tokens.append(tok)
            return tokenize.untokenize(tokens)
        except Exception:  # noqa: BLE001
            return src or ""

    def test_f1_no_event_production_or_consumption(self) -> None:
        """Activity 不产生 / 不消费 Event（EB-13 / EF-6）。"""
        eff = self._effective_code()
        for token in ("EventBus", "EventStore", "emit_event", "push_event", "enqueue_event"):
            self.assertNotRegex(
                eff, r"\b" + re.escape(token) + r"\b",
                f"EB-13：Activity 不得涉及 Event：{token}",
            )

    def test_f2_does_not_write_world_storage(self) -> None:
        """Activity 不写 World 存储（ED-6 / EO-9 ～ EO-12）。"""
        eff = self._effective_code()
        for pattern in (
            r"main\.data\s*\[",
            r"save_data\s*\(",
            r"\[\s*[\"']activities[\"']\s*\]",
            r"[\"']activities[\"']\s*:",
        ):
            self.assertNotRegex(eff, pattern, f"ED-6：Activity 不得写 World 存储：{pattern}")

    def test_f3_does_not_persist(self) -> None:
        """
        Activity 不持久化（ED-5 / ED-7 / EH-1）。

        ⚠️ 误报修正（首次真实运行暴露）：

            原断言用 `assertNotIn("open(", eff)`。
            但 `copy.deepcopy(` 的 **`deepcopy(`** 内部恰好含子串 `open(`，
            于是产生纯文本误报 —— 与持久化毫无关系。

            这是裸子串匹配的又一变体（`D1G-16` ～ `D1G-20`）。
            改为**词边界 + 排除属性访问**：只有作为独立函数调用的
            `open(...)` 才算落盘；`x.open(` 这类属性名也不算。
        """
        eff = self._effective_code()

        # 明确的持久化 API（子串足够特殊，直接用 in 即可）
        for token in (
            "json.dump", "pickle.dump", "sqlite3", "shelve", "dbm.",
            "write_text", "write_bytes",
        ):
            self.assertNotIn(token, eff, f"ED-5：Activity 不得持久化：{token}")

        # 内建 open()：必须用词边界，排除 deepcopy( 之类的子串
        self.assertNotRegex(
            eff,
            r"(?<![\w.])open\s*\(",
            "ED-5：Activity 不得调用内建 open() 落盘"
            "（注意：deepcopy( 不是 open( —— 需词边界判定）",
        )

    def test_f4_does_not_depend_on_scheduler(self) -> None:
        """Activity 不依赖 scheduler / tick / timer（EP-6 / EP-10）。"""
        eff = self._effective_code()
        for token in (
            "scheduler", "threading.Timer", "asyncio.sleep",
            "time.sleep", "while True", "crontab",
        ):
            self.assertNotIn(token, eff, f"EP-6：Activity 不得依赖调度：{token}")

    def test_f5_does_not_touch_motivation_or_state_or_query(self) -> None:
        """不接入 Motivation / AgentState / World Query（ET-1 / EC-8 / WQ-75）。"""
        eff = self._effective_code()
        for token in (
            "motivation", "agent_state_snapshot",
            "AgentState", "agent.state",
            "world_query", "QueryResult",
        ):
            self.assertNotRegex(
                eff, r"\b" + re.escape(token) + r"\b",
                f"ET-1 / EC-8：Activity 不得依赖 {token}",
            )

    def test_f6_does_not_import_main_or_ext(self) -> None:
        """不 import main / ext_*（不持有 World 引用）。"""
        eff = self._effective_code()
        for pattern in (
            r"\bimport\s+main\b",
            r"\bfrom\s+main\s+import\b",
            r"\bimport\s+ext_",
            r"\bfrom\s+ext_\w*\s+import\b",
        ):
            self.assertNotRegex(eff, pattern, f"不得 import World 模块：{pattern}")

    def test_f7_no_capability_integration(self) -> None:
        """不接 Capability（EN-6 / EN-8）。"""
        eff = self._effective_code()
        for token in ("execute_action", "CapabilityRequest", "CapabilityResult"):
            self.assertNotRegex(
                eff, r"\b" + re.escape(token) + r"\b",
                f"EN-6：Activity 不得接入 Capability：{token}",
            )

    def test_f8_no_legacy_activity_key_write(self) -> None:
        """不反向写 Legacy 活动字段（EO-9 ～ EO-12）。"""
        eff = self._effective_code()
        for key in (
            "dates", "date_invites", "work_sessions", "ai_shop_state",
            "ai_follow", "ai_meeting", "instances", "ai_pending_moves",
        ):
            self.assertNotRegex(
                eff,
                r"\[\s*[\"']" + re.escape(key) + r"[\"']\s*\]\s*=",
                f"EO-12：不得反向写 Legacy 字段：{key}",
            )

    def test_f9_module_declares_scope_honestly(self) -> None:
        """模块必须诚实声明实现范围（便于审计）。"""
        info = act.describe_activity_module()
        self.assertEqual(info["phase"], "D-2")
        self.assertEqual(info["sot_identity"], "Runtime-scoped Domain State")
        self.assertIn("ActivityRegistry", info["registry"])
        self.assertIn("Activity", info["domain_object"])
        self.assertIsInstance(info["implemented"], tuple)
        self.assertIsInstance(info["not_implemented"], tuple)
        not_impl = " ".join(info["not_implemented"])
        for keyword in ("持久化", "调度", "Event", "Capability", "Motivation"):
            self.assertIn(keyword, not_impl, f"自描述必须声明未实现：{keyword}")


# =========================================================
# G. Activity Domain Object 语义
# =========================================================

class GD2DomainSemantics(unittest.TestCase):
    """EA-7 四必要条件与语义排除（EB-*）。"""

    def setUp(self) -> None:
        self.reg = _new_registry()

    def test_g1_has_identity_and_duration_and_participant(self) -> None:
        """EA-7：身份 / 持续 / 参与者 / 可终止。"""
        a = _sample_activity(self.reg)
        # 身份
        self.assertTrue(a.activity_id)
        # 参与者
        self.assertTrue(a.actor_ids)
        # 可终止：终态可达
        self.assertTrue(any(
            act.is_terminal(t) for t in act.LIFECYCLE_STATUSES
        ))
        # 持续：生命周期跨越多个 Event —— 由状态机（多步转换）承载
        r1 = self.reg.transition(a.activity_id, act.STATUS_TRAVELING, reason="x")
        r2 = self.reg.transition(a.activity_id, act.STATUS_ARRIVED, reason="x")
        self.assertTrue(r1.ok and r2.ok, "生命周期必须支持多步转换（持续性）")

    def test_g2_activity_is_not_goal_or_commitment(self) -> None:
        """Activity 的 goal / commitment 只是**弱引用**，不是存储（EB-9 / EB-10）。"""
        a = self.reg.create_activity(
            type="DATE", actor_ids=["白起"],
            goal_id="goal_1", commitment_ids=["cm_1", "cm_2"],
        )
        self.assertEqual(a.goal_id, "goal_1")
        self.assertEqual(a.commitment_ids, ("cm_1", "cm_2"))
        d = a.to_dict()
        # 不得包含 Goal / Commitment 的**内容**字段（只有引用 id）
        for forbidden in ("goal", "commitment", "goals", "commitments", "reason"):
            self.assertNotIn(forbidden, d, f"EB-9：Activity 不得持有 {forbidden} 内容")

    def test_g3_location_is_process_location_not_current_position(self) -> None:
        """`location_id` 是过程发生地，不是 AI 当前位置（EJ-6）。"""
        a = _sample_activity(self.reg, location_id="b1·客厅")
        self.assertEqual(a.location_id, "b1·客厅")
        # 不得包含位置细节副本（EO-1）
        d = a.to_dict()
        for forbidden in ("room", "building", "rooms", "ai_location", "position"):
            self.assertNotIn(forbidden, d, f"EO-1：Activity 不得复制 World 事实：{forbidden}")

    def test_g4_no_scheduler_fields(self) -> None:
        """不得有调度字段（EP-3 / ER-7）。"""
        a = _sample_activity(self.reg)
        d = a.to_dict()
        for forbidden in ("next_ts", "timer", "schedule", "cron", "interval"):
            self.assertNotIn(forbidden, d, f"EP-3：Activity 不得有调度字段：{forbidden}")

    def test_g5_expected_end_at_is_descriptive_only(self) -> None:
        """`expected_end_at` 只是描述，不触发任何行为（EP-4 / EP-5）。"""
        a = self.reg.create_activity(
            type="WORK", actor_ids=["白起"], expected_end_at=1.0
        )
        self.assertEqual(a.expected_end_at, 1.0)
        # 创建后状态不受影响
        self.assertEqual(self.reg.get(a.activity_id).status, act.STATUS_PLANNED)

    def test_g6_is_terminal_and_is_active_like(self) -> None:
        """`is_terminal` / `is_active_like` 语义正确。"""
        a = _sample_activity(self.reg)
        self.assertFalse(a.is_terminal())
        self.assertFalse(a.is_active_like())
        self.reg.transition(a.activity_id, act.STATUS_TRAVELING, reason="x")
        self.assertTrue(self.reg.get(a.activity_id).is_active_like())
        self.assertFalse(self.reg.get(a.activity_id).is_terminal())


# =========================================================
# H. 环境能力
# =========================================================

class HD2EnvironmentCapability(unittest.TestCase):

    def test_h1_repo_root_resolves(self) -> None:
        self.assertTrue((ROOT / "main.py").is_file())
        self.assertTrue(AGENT_DIR.is_dir())

    def test_h2_activity_module_present(self) -> None:
        self.assertTrue(ACTIVITY_MODULE.is_file(), f"必须存在 {ACTIVITY_MODULE}")

    def test_h3_no_third_party_import_required(self) -> None:
        """本测试文件必须只依赖标准库。"""
        src = _read_text(Path(__file__)) or ""
        tree = ast.parse(src)
        stdlib_ok = {
            "__future__", "ast", "io", "re", "sys", "unittest",
            "pathlib", "typing", "dataclasses", "tokenize", "copy",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(
                        alias.name.split(".")[0], stdlib_ok,
                        f"不得依赖第三方库：{alias.name}",
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module and not node.module.startswith("agent"):
                    self.assertIn(
                        node.module.split(".")[0], stdlib_ok,
                        f"不得依赖第三方库：{node.module}",
                    )

    def test_h4_activity_module_depends_on_stdlib_only(self) -> None:
        """`agent/activity.py` 必须只依赖标准库（可独立测试）。"""
        src = _read_text(ACTIVITY_MODULE) or ""
        tree = ast.parse(src)
        stdlib_ok = {
            "__future__", "copy", "time", "uuid", "dataclasses", "typing",
            "types",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(
                        alias.name.split(".")[0], stdlib_ok,
                        f"agent/activity.py 不得依赖非标准库：{alias.name}",
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertIn(
                        node.module.split(".")[0], stdlib_ok,
                        f"agent/activity.py 不得依赖非标准库：{node.module}",
                    )


# =========================================================
# 入口
# =========================================================


def _print_header() -> None:
    print("=" * 74)
    print("V3.1 Phase D-2 · Activity Implementation Behavior Tests")
    print("       （Implementation Verification）")
    print("=" * 74)
    print(f"ROOT            : {ROOT}")
    print(f"implementation  : {ACTIVITY_MODULE}")
    print(f"statuses        : {len(act.LIFECYCLE_STATUSES)} (expected 7)")
    print(f"terminal        : {list(act.TERMINAL_STATUSES)}")
    print(f"initial         : {act.INITIAL_STATUS}")
    print(f"roles (base)    : {list(act.BASE_ROLES)}")
    print(f"bindings        : {list(act.BINDING_KINDS)}")
    print("-" * 74)
    print("A: Activity 创建与字段校验")
    print("B: lifecycle（全部合法转换 / 非法跳跃 / 终态不可逆 / EP-5）")
    print("C: primary / secondary binding（binding ≠ ownership）")
    print("D: Registry 唯一真相与容器隔离")
    print("E: **不可变边界**（frozen=True + mutable dict 穿透验证）")
    print("F: 不产生 Event / 不写 World / 不持久化 / 不依赖 scheduler")
    print("G: Activity Domain Object 语义（EA-7 / EB-* / EO-1 / EP-3）")
    print("H: 环境能力")
    print("=" * 74)
    print("注意：E 组为 immutable-boundary 验证。若发现穿透，将如实记录并")
    print("      报告架构侧裁决（A 修改实现 / B 接受属性级 frozen 语义）。")
    print("=" * 74)


if __name__ == "__main__":
    _print_header()
    unittest.main(verbosity=2)
