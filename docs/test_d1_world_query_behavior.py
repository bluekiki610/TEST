# -*- coding: utf-8 -*-
"""
docs/test_d1_world_query_behavior.py
====================================

V3.1 Phase D-1 · World Query **Implementation Behavior** Tests
（D-1 Implementation Hardening / D1-H4）

--------------------------------------------------------------------------
与 test_d1_world_query.py 的分工（重要）
--------------------------------------------------------------------------

    docs/test_d1_world_query.py
        = **架构边界**静态测试（import 边界 / 写入模式 / Event / Activity /
          Contract 文档一致性 …）
        它**不**验证运行时行为。

    本文件
        = **实现级行为**测试。
        它真正调用 agent.world_query 的函数，验证：

            ① 私人房间授权（D1-H1）
            ② WQ-94 最小可见性白名单（D1-H2）
            ③ 返回值不穿透 main.data（D1-H3）
            ④ 五态语义正确（UNKNOWN ≠ ABSENT；UNSUPPORTED 不猜测；
               FORBIDDEN 无 value）
            ⑤ 反模式守卫（WQ-90 ～ WQ-93）

    **为什么需要本文件：**
        架构侧审核指出：
            "51 tests OK ≠ World Query Implementation 已经满足 D-1"
        因为静态边界测试无法发现「私人房间被绕过」「钱包被任意读取」
        「浅拷贝穿透」这类**行为级**违规。本文件就是补上这一层。

--------------------------------------------------------------------------
设计原则
--------------------------------------------------------------------------

    * 只依赖标准库（unittest / copy / pathlib / sys）
    * **真的 import agent.world_query**（因为它本身只依赖标准库）
    * 所有断言针对**行为**，不做源码文本扫描
    * 不从仓库根 import main / ext_*（避免引入 fastapi 等依赖）

--------------------------------------------------------------------------
如何运行
--------------------------------------------------------------------------

    从仓库根目录运行：

        python docs/test_d1_world_query_behavior.py
        python -m unittest docs.test_d1_world_query_behavior -v

    若执行环境不可用，必须如实报告：

        TEST NOT RUN
        Reason: environment execution unavailable
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

# =========================================================
# 0. 路径：标记探测（兼容目录整理）
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# agent.world_query 只依赖标准库，因此可以安全 import
from agent import world_query as wq  # noqa: E402


# =========================================================
# 1. 测试夹具（fixture）
# =========================================================

def make_data() -> Dict[str, Any]:
    """
    构造一份覆盖全部可见性分支的世界数据。

    布局：
        buildings
            b1  私人建筑，owner = alice，rooms = [b1·客厅, b1·卧室]
            b2  公共 NPC 建筑，type = npc，rooms = [b2·会客厅]
            b3  无主建筑， rooms = [b3·院子]
        rooms
            main                       公共大厅
            alice_hall ·会客厅          公共（会客厅）
            b1·客厅 / b1·卧室           私人（属 b1，owner alice）
            b2·会客厅 / b3·院子         公共
        user_ais
            alice -> [白起, 许墨]
            bob   -> [李泽言]
        ai_location
            白起 -> b1·客厅        （在私人房间）
            许墨 -> b2·会客厅      （公共）
            李泽言 -> b2·会客厅    （公共）
            未知AI -> 某个不存在的房间名（不可解析）
    """
    return {
        "buildings": {
            "b1": {
                "name": "白起的家",
                "type": "home",
                "owner": "alice",
                "rooms": ["b1·客厅", "b1·卧室"],
                "features": ["rest"],
                "region": "城北",
                "nested": {"deep": {"layer": [1, 2, 3]}},
            },
            "b2": {
                "name": "北区咖啡厅",
                "type": "npc",
                "owner": "",
                "rooms": ["b2·会客厅"],
                "features": ["food", "date"],
                "region": "市中心",
            },
            "b3": {
                "name": "旧院子",
                "type": "nature",
                "owner": "",
                "rooms": ["b3·院子"],
                "features": ["fun"],
                "region": "城南",
            },
        },
        "rooms": {
            "main": {"creator": "system", "description": "公共大厅"},
            "咖啡厅·会客厅": {"creator": "hall"},
            "b1·客厅": {"creator": "alice", "password": "SECRET", "description": "私人客厅"},
            "b1·卧室": {"creator": "alice", "password": "SECRET2", "description": "私人卧室"},
            "b2·会客厅": {"creator": "hall"},
            "b3·院子": {"creator": "hall"},
        },
        "npcs": {
            "b1": [{"name": "管家", "emoji": "🧑‍🍳", "desc": "白起家的管家"}],
            "b2": [{"name": "店员", "emoji": "👩", "desc": "咖啡厅店员"}],
        },
        "user_ais": {
            "alice": ["白起", "许墨"],
            "bob": ["李泽言"],
            # 该 AI 已登记，但其 ai_location 指向一个不存在的房间
            # → 用于验证 UNKNOWN（可回答但事实不足）≠ ABSENT
            "ghost": ["未知AI"],
        },
        "ai_location": {
            "白起": "b1·客厅",
            "许墨": "b2·会客厅",
            "李泽言": "b2·会客厅",
            "未知AI": "某个不存在的房间",
        },
        "wallets": {"白起": 1234.0, "许墨": 555.0, "李泽言": 999.0},
        "affection": {"白起": 88, "许墨": 61, "李泽言": 42},
        "dates": [
            {"ai": "白起", "status": "active", "user": "alice"},
            {"ai": "许墨", "status": "ended", "user": "alice"},
        ],
        "work_sessions": {"许墨": {"building_id": "b2", "hours": 2}},
        "ai_follow": {"李泽言": {"owner": "bob", "go_to": "b2·会客厅"}},
        "ai_shop_state": {"白起": {"cooldown_until": 9999999999}},
        "writing_rhythm": {},
        "story_rhythm": {},
        "presence": {
            "alice": {"page": "b1·客厅", "room": "b1·客厅", "ts": 1000.0},
            "bob": {"page": "b2·会客厅", "room": "b2·会客厅", "ts": 1000.0},
        },
        "time_settings": {
            "b2·会客厅": {"mode": "fixed", "fixed_time": "2026-09-30 12:00:00"},
        },
    }


def make_private_room_only_data() -> Dict[str, Any]:
    """最小夹具：一个私人建筑 + 一个无法归属的房间。"""
    return {
        "buildings": {
            "p1": {"name": "私人宅", "type": "home", "owner": "alice", "rooms": ["p1·书房"]},
        },
        "rooms": {"p1·书房": {"creator": "alice", "password": "PW"}},
        "user_ais": {"alice": ["白起"], "bob": ["李泽言"]},
        "ai_location": {"白起": "p1·书房"},
        "presence": {},
    }


# =========================================================
# 2. B1 · 私人房间授权（D1-H1）
# =========================================================

class B1PrivateRoomAuthorization(unittest.TestCase):
    """D1-H1：私人房间授权必须以**目标 owner** 为中心，不得被任意用户/AI 绕过。"""

    def setUp(self) -> None:
        self.data = make_data()

    def test_b1_1_owner_allowed(self) -> None:
        """owner 本人 → ALLOWED。"""
        r = wq.get_room("b1·客厅", self.data, requester="alice")
        self.assertEqual(r.status, wq.STATUS_FOUND)
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIsNotNone(r.value)

    def test_b1_2_owner_agent_allowed(self) -> None:
        """owner 名下的 AI → ALLOWED。"""
        r = wq.get_room("b1·客厅", self.data, requester="白起")
        self.assertEqual(r.status, wq.STATUS_FOUND)
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)

    def test_b1_3_other_user_forbidden(self) -> None:
        """**关键**：其他用户（系统里认识的人）→ FORBIDDEN，不得绕过。"""
        r = wq.get_room("b1·客厅", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)
        self.assertIsNone(r.value, "FORBIDDEN 时不得返回事实值")

    def test_b1_4_other_agent_forbidden(self) -> None:
        """**关键**：其他 owner 的 AI → FORBIDDEN。"""
        r = wq.get_room("b1·客厅", self.data, requester="李泽言")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)
        self.assertIsNone(r.value)

    def test_b1_5_unknown_requester_forbidden(self) -> None:
        """完全未知的 requester → FORBIDDEN。"""
        r = wq.get_room("b1·客厅", self.data, requester="某个陌生人")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b1_6_empty_requester_forbidden(self) -> None:
        """缺省 requester → 不得解释为「上帝视角」，必须 FORBIDDEN。"""
        r = wq.get_room("b1·客厅", self.data)
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)
        self.assertIsNone(r.value)

    def test_b1_7_unresolvable_room_is_not_public(self) -> None:
        """
        fail-closed：无法归属到建筑的房间按**不公开**处理。

        构造一个存在于 rooms 但不在任何 building.rooms 中的房间。
        """
        data = make_private_room_only_data()
        data["rooms"]["孤儿房间"] = {"creator": "someone"}
        r = wq.get_room("孤儿房间", data, requester="bob")
        self.assertEqual(
            r.outcome, wq.OUTCOME_FORBIDDEN,
            "无法归属到建筑的房间必须 fail-closed（不得假定公开）",
        )

    def test_b1_8_password_never_leaked(self) -> None:
        """私人房间内容即使可见，也不得包含 password 字段。"""
        r = wq.get_room("b1·客厅", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertNotIn("password", r.value)


# =========================================================
# 3. B2 · 公开房间 / 公开建筑
# =========================================================

class B2PublicVisibility(unittest.TestCase):

    def setUp(self) -> None:
        self.data = make_data()

    def test_b2_1_main_is_public(self) -> None:
        r = wq.get_room("main", self.data, requester="任意人")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)

    def test_b2_2_hall_room_is_public(self) -> None:
        r = wq.get_room("咖啡厅·会客厅", self.data, requester="任意人")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)

    def test_b2_3_npc_building_room_is_public(self) -> None:
        r = wq.get_room("b2·会客厅", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)

    def test_b2_4_unowned_building_room_is_public(self) -> None:
        r = wq.get_room("b3·院子", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)

    def test_b2_5_public_building_readable_by_anyone(self) -> None:
        r = wq.get_building("b2", self.data, requester="bob")
        self.assertEqual(r.status, wq.STATUS_FOUND)
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)

    def test_b2_6_private_building_forbidden_for_others(self) -> None:
        r = wq.get_building("b1", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)
        self.assertIsNone(r.value)

    def test_b2_7_private_building_allowed_for_owner(self) -> None:
        r = wq.get_building("b1", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)

    def test_b2_8_private_building_rooms_forbidden_for_others(self) -> None:
        r = wq.list_building_rooms("b1", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)
        self.assertIsNone(r.value)

    def test_b2_9_public_building_rooms_allowed(self) -> None:
        r = wq.list_building_rooms("b2", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIn("b2·会客厅", r.value)

    def test_b2_10_private_building_npcs_forbidden_for_others(self) -> None:
        r = wq.list_npcs_in_building("b1", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b2_11_public_building_npcs_allowed(self) -> None:
        r = wq.list_npcs_in_building("b2", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertEqual(len(r.value), 1)


# =========================================================
# 4. B3 · 人员可见性（D1-H2 白名单 E）
# =========================================================

class B3PeopleVisibility(unittest.TestCase):

    def setUp(self) -> None:
        self.data = make_data()

    def test_b3_1_private_room_agents_forbidden_for_others(self) -> None:
        """**关键**：私人房间里的 AI 不得被其他 requester 看到。"""
        r = wq.list_agents_in_room("b1·客厅", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)
        self.assertIsNone(r.value)

    def test_b3_2_private_room_agents_allowed_for_owner(self) -> None:
        r = wq.list_agents_in_room("b1·客厅", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIn("白起", r.value)

    def test_b3_3_public_room_agents_visible_to_all(self) -> None:
        r = wq.list_agents_in_room("b2·会客厅", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIn("许墨", r.value)
        self.assertIn("李泽言", r.value)

    def test_b3_4_private_room_people_forbidden_for_others(self) -> None:
        r = wq.list_users_present_in_room("b1·客厅", self.data, requester="bob", now_ts=1001.0)
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b3_5_public_room_people_visible(self) -> None:
        r = wq.list_users_present_in_room("b2·会客厅", self.data, requester="alice", now_ts=1001.0)
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIn("bob", r.value)

    def test_b3_6_private_building_agents_forbidden_for_others(self) -> None:
        r = wq.list_agents_in_building("b1", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)
        self.assertIsNone(r.value)

    def test_b3_7_private_building_agents_allowed_for_owner(self) -> None:
        r = wq.list_agents_in_building("b1", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIn("白起", r.value)

    def test_b3_8_public_building_agents_visible(self) -> None:
        r = wq.list_agents_in_building("b2", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIn("许墨", r.value)
        self.assertIn("李泽言", r.value)


# =========================================================
# 5. B4 · 其他 AI 私人状态不得泄露（D1-H2 白名单 B）
# =========================================================

class B4PrivateAgentState(unittest.TestCase):

    def setUp(self) -> None:
        self.data = make_data()

    def test_b4_1_wallet_forbidden_for_other_ai(self) -> None:
        """**关键**：其他 AI 不得读取白起的钱包。"""
        r = wq.get_agent_wallet("白起", self.data, requester="李泽言")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)
        self.assertIsNone(r.value)

    def test_b4_2_wallet_forbidden_for_other_user(self) -> None:
        r = wq.get_agent_wallet("白起", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b4_3_wallet_allowed_for_owner(self) -> None:
        r = wq.get_agent_wallet("白起", self.data, requester="alice")
        self.assertEqual(r.status, wq.STATUS_FOUND)
        self.assertEqual(r.value, 1234.0)

    def test_b4_4_wallet_allowed_for_self(self) -> None:
        r = wq.get_agent_wallet("白起", self.data, requester="白起")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)

    def test_b4_5_wallet_allowed_for_same_owner_sibling(self) -> None:
        """同一 owner 下的另一个 AI → ALLOWED。"""
        r = wq.get_agent_wallet("白起", self.data, requester="许墨")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)

    def test_b4_6_wallet_forbidden_for_empty_requester(self) -> None:
        """缺省 requester 不得读私人状态。"""
        r = wq.get_agent_wallet("白起", self.data)
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b4_7_affection_forbidden_for_others(self) -> None:
        r = wq.get_agent_affection("白起", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b4_8_owner_forbidden_for_others(self) -> None:
        r = wq.get_agent_owner("白起", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b4_9_owner_allowed_for_self_scope(self) -> None:
        r = wq.get_agent_owner("白起", self.data, requester="alice")
        self.assertEqual(r.status, wq.STATUS_FOUND)

    def test_b4_10_dating_forbidden_for_others(self) -> None:
        r = wq.is_agent_dating("白起", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b4_11_dating_allowed_for_owner(self) -> None:
        r = wq.is_agent_dating("白起", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIs(r.value, True)

    def test_b4_12_working_forbidden_for_others(self) -> None:
        r = wq.is_agent_working("许墨", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b4_13_working_allowed_for_owner(self) -> None:
        r = wq.is_agent_working("许墨", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIs(r.value, True)

    def test_b4_14_following_forbidden_for_others(self) -> None:
        r = wq.is_agent_following("李泽言", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b4_15_following_allowed_for_owner(self) -> None:
        r = wq.is_agent_following("李泽言", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIs(r.value, True)

    def test_b4_16_legacy_activity_forbidden_for_others(self) -> None:
        r = wq.get_agent_current_activity_legacy("白起", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b4_17_legacy_activity_allowed_and_derived(self) -> None:
        r = wq.get_agent_current_activity_legacy("白起", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIs(r.derived, True, "Legacy 活动必须是 derived=True（WQ-43）")

    def test_b4_18_own_agent_list_forbidden_for_others(self) -> None:
        r = wq.list_agent_owning_user("alice", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)

    def test_b4_19_own_agent_list_allowed_for_owner(self) -> None:
        r = wq.list_agent_owning_user("alice", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        self.assertIn("白起", r.value)


# =========================================================
# 6. B5 · 返回值不穿透 main.data（D1-H3）
# =========================================================

class B5NoReferenceLeak(unittest.TestCase):
    """D1-H3：QueryResult.value 必须与 main.data 完全脱钩（含嵌套结构）。"""

    def setUp(self) -> None:
        self.data = make_data()

    def test_b5_1_building_deep_copy(self) -> None:
        """**关键**：修改 get_building 的返回值不得影响 main.data。"""
        before = copy.deepcopy(self.data["buildings"]["b1"])
        r = wq.get_building("b1", self.data, requester="alice")
        self.assertEqual(r.status, wq.STATUS_FOUND)

        # 顶层
        r.value["name"] = "HACKED"
        # 嵌套 list
        if isinstance(r.value.get("rooms"), list):
            r.value["rooms"].append("HACKED_ROOM")
        # 深层嵌套 dict / list
        nested = r.value.get("nested")
        if isinstance(nested, dict):
            nested["deep"] = "HACKED"
            deep = nested.get("deep")
            if isinstance(deep, dict) and isinstance(deep.get("layer"), list):
                deep["layer"].append(999)

        self.assertEqual(
            self.data["buildings"]["b1"], before,
            "get_building 的 value 不是深拷贝：修改返回值穿透到了 main.data",
        )

    def test_b5_2_room_deep_copy(self) -> None:
        before = copy.deepcopy(self.data["rooms"]["b1·客厅"])
        r = wq.get_room("b1·客厅", self.data, requester="alice")
        self.assertEqual(r.outcome, wq.OUTCOME_ALLOWED)
        r.value["description"] = "HACKED"
        self.assertEqual(
            self.data["rooms"]["b1·客厅"], before,
            "get_room 的 value 穿透到了 main.data",
        )

    def test_b5_3_room_list_not_shared(self) -> None:
        r = wq.list_building_rooms("b2", self.data, requester="alice")
        original_len = len(self.data["buildings"]["b2"]["rooms"])
        r.value.append("HACKED_ROOM")
        self.assertEqual(
            len(self.data["buildings"]["b2"]["rooms"]), original_len,
            "list_building_rooms 的 value 与 main.data 共享列表",
        )

    def test_b5_4_npc_list_not_shared(self) -> None:
        r = wq.list_npcs_in_building("b2", self.data, requester="alice")
        r.value[0]["name"] = "HACKED"
        self.assertEqual(
            self.data["npcs"]["b2"][0]["name"], "店员",
            "list_npcs_in_building 的 value 穿透到了 main.data",
        )

    def test_b5_5_agent_name_lists_not_shared(self) -> None:
        r = wq.list_agents_in_room("b2·会客厅", self.data, requester="alice")
        original = len(r.value)
        r.value.append("HACKED")
        r2 = wq.list_agents_in_room("b2·会客厅", self.data, requester="alice")
        self.assertEqual(
            len(r2.value), original,
            "list_agents_in_room 的 value 与 main.data 共享列表",
        )

    def test_b5_6_own_agent_list_not_shared(self) -> None:
        r = wq.list_agent_owning_user("alice", self.data, requester="alice")
        r.value.append("HACKED")
        self.assertNotIn("HACKED", self.data["user_ais"]["alice"])


# =========================================================
# 7. B6 · 五态语义（不得伪装 / 不得猜测）
# =========================================================

class B6StatusSemantics(unittest.TestCase):

    def setUp(self) -> None:
        self.data = make_data()

    def test_b6_1_absent_is_not_value(self) -> None:
        r = wq.get_room("根本不存在的房间", self.data, requester="alice")
        self.assertEqual(r.status, wq.STATUS_ABSENT)
        self.assertIsNone(r.value)

    def test_b6_2_unknown_not_disguised_as_absent(self) -> None:
        """**关键**：不可解析的位置必须是 UNKNOWN，不是 ABSENT。"""
        r = wq.get_agent_location("未知AI", self.data, requester="alice")
        self.assertEqual(
            r.status, wq.STATUS_UNKNOWN,
            "无法解析的位置必须是 UNKNOWN（不得伪装 ABSENT）",
        )

    def test_b6_3_absent_for_unknown_agent(self) -> None:
        r = wq.get_agent_location("完全不存在的AI", self.data, requester="alice")
        self.assertEqual(r.status, wq.STATUS_ABSENT)

    def test_b6_4_unsupported_does_not_guess(self) -> None:
        """**关键**：UNSUPPORTED 不得返回猜测值。"""
        for result in (
            wq.get_map_of_building("b1", self.data, requester="alice"),
            wq.get_npc_location("管家", self.data, requester="alice"),
            wq.search_places_by_purpose("medical", self.data, requester="alice"),
            wq.get_relationship("白起", "alice", self.data, requester="alice"),
            wq.get_route("b1", "b2", self.data, requester="alice"),
            wq.list_available_places("白起", self.data, requester="alice"),
            wq.get_activity("act_1", self.data, requester="alice"),
        ):
            self.assertEqual(result.status, wq.STATUS_UNSUPPORTED)
            self.assertIsNone(result.value, "UNSUPPORTED 不得返回猜测值")
            self.assertEqual(result.outcome, wq.OUTCOME_ALLOWED)

    def test_b6_5_ambiguous_not_silently_resolved(self) -> None:
        """
        **关键**：多个候选必须返回 AMBIGUOUS，不得替调用方挑一个。

        ⚠️ 测试构造说明（首次运行后修正）：

            `_building_candidates()` 的优先级是
                id 全等 → **name 全等** → name 子串
            因此若查询键与某个建筑的 name **全等**，会立即唯一命中并返回 FOUND
            —— 这不是歧义。

            要构造真正的歧义，查询键必须**只能通过子串匹配命中多个**。
            本测试因此：
                * 夹具中不存在名为「咖啡厅」的建筑
                * 但存在两个名称**包含**「咖啡厅」的建筑（北区咖啡厅 / 南区咖啡厅二号）
                * 查询键 = "咖啡厅" → 子串命中 ≥ 2 → AMBIGUOUS
        """
        data = make_data()
        data["buildings"]["b9"] = {
            "name": "南区咖啡厅二号",
            "type": "npc",
            "owner": "",
            "rooms": [],
        }
        r = wq.get_building("咖啡厅", data, requester="alice")
        self.assertEqual(
            r.status, wq.STATUS_AMBIGUOUS,
            "多个候选必须返回 AMBIGUOUS，不得替调用方挑一个",
        )
        self.assertIsNotNone(r.value, "AMBIGUOUS 应返回候选列表供消歧")
        self.assertGreaterEqual(len(r.value), 2)

    def test_b6_6_forbidden_has_no_value_and_is_not_unknown(self) -> None:
        """**关键**：FORBIDDEN 必须 value=None，且 != UNKNOWN / ABSENT。"""
        r = wq.get_room("b1·客厅", self.data, requester="bob")
        self.assertEqual(r.outcome, wq.OUTCOME_FORBIDDEN)
        self.assertIsNone(r.value)
        self.assertEqual(
            r.status, wq.STATUS_UNSUPPORTED,
            "架构侧裁决：FORBIDDEN 不属五态核心；实现以 UNSUPPORTED + FORBIDDEN 表达",
        )
        self.assertNotEqual(r.outcome, wq.OUTCOME_ALLOWED)

    def test_b6_7_five_state_core_is_exactly_five(self) -> None:
        self.assertEqual(len(wq.STATUS_CORE), 5)
        self.assertNotIn(wq.OUTCOME_FORBIDDEN, wq.STATUS_CORE)

    def test_b6_8_status_and_outcome_are_orthogonal(self) -> None:
        self.assertEqual(len(wq.OUTCOME_VALUES), 2)
        self.assertIn(wq.OUTCOME_ALLOWED, wq.OUTCOME_VALUES)
        self.assertIn(wq.OUTCOME_FORBIDDEN, wq.OUTCOME_VALUES)


# =========================================================
# 8. B7 · 反模式守卫（WQ-90 ～ WQ-93）
# =========================================================

class B7AntiPatternGuard(unittest.TestCase):

    def test_b7_1_route_like_request_rejected(self) -> None:
        self.assertTrue(wq.is_decision_like_request({"route": "b1->b2"}))
        self.assertTrue(wq.is_decision_like_request({"choose_target": "x"}))
        self.assertTrue(wq.is_decision_like_request({"plan": "..."}))
        self.assertTrue(wq.is_decision_like_request({"suggest": "..."}))
        self.assertTrue(wq.is_decision_like_request({"recommend": "..."}))
        self.assertTrue(wq.is_decision_like_request({"rank": "..."}))

    def test_b7_2_fact_inquiry_not_rejected(self) -> None:
        self.assertFalse(wq.is_decision_like_request({"room": "b2·会客厅"}))
        self.assertFalse(wq.is_decision_like_request({"building": "b2"}))

    def test_b7_3_describe_declares_not_capabilities(self) -> None:
        d = wq.describe_capabilities()
        self.assertTrue(d["read_only"])
        self.assertEqual(len(d["status_core"]), 5)
        not_caps = " ".join(d["not_capabilities"])
        for token in ("route", "planning", "activity", "command", "memory"):
            self.assertIn(token, not_caps)

    def test_b7_4_describe_declares_visibility_whitelist(self) -> None:
        d = wq.describe_capabilities()
        self.assertIn("visibility_whitelist", d)
        self.assertEqual(len(d["visibility_whitelist"]), 5)

    def test_b7_5_namespace_is_read_only_mapping(self) -> None:
        ns = wq.get_world_query_namespace()
        for key in ("location", "people", "time", "agent", "unsupported", "guards"):
            self.assertIn(key, ns)


# =========================================================
# 9. B8 · 既有正确行为未被 Hardening 破坏（回归）
# =========================================================

class B8Regression(unittest.TestCase):

    def setUp(self) -> None:
        self.data = make_data()

    def test_b8_1_world_time(self) -> None:
        r = wq.get_world_time(self.data, now_ts=1759200000.0)
        self.assertEqual(r.status, wq.STATUS_FOUND)
        self.assertIn("clock_kind = world", r.notes)

    def test_b8_2_room_time_fixed(self) -> None:
        r = wq.get_room_time("b2·会客厅", self.data, now_ts=1759200000.0)
        self.assertEqual(r.status, wq.STATUS_FOUND)
        self.assertEqual(r.value, "2026-09-30 12:00:00")
        self.assertIn("clock_kind = room", r.notes)

    def test_b8_3_room_time_world_fallback(self) -> None:
        r = wq.get_room_time("b3·院子", self.data, now_ts=1759200000.0)
        self.assertEqual(r.status, wq.STATUS_FOUND)
        self.assertIn("clock_kind = world", r.notes)

    def test_b8_4_agent_location_resolvable(self) -> None:
        r = wq.get_agent_location("白起", self.data, requester="alice")
        self.assertEqual(r.status, wq.STATUS_FOUND)
        self.assertEqual(r.value, "b1·客厅")

    def test_b8_5_decision_like_request_does_not_mutate(self) -> None:
        payload = {"route": "x", "nested": {"list": [1, 2]}}
        before = copy.deepcopy(payload)
        wq.is_decision_like_request(payload)
        self.assertEqual(payload, before)


# =========================================================
# 入口
# =========================================================

def _print_header() -> None:
    print("=" * 72)
    print("V3.1 Phase D-1 · World Query Implementation Behavior Tests")
    print("       （D-1 Implementation Hardening / D1-H4）")
    print("=" * 72)
    print(f"ROOT              : {ROOT}")
    print(f"module            : {wq.__file__}")
    print(f"status_core       : {len(wq.STATUS_CORE)} (expected 5)")
    print(f"outcomes          : {list(wq.OUTCOME_VALUES)}")
    print("-" * 72)
    print("本文件验证**行为**：")
    print("  B1 私人房间授权（D1-H1）")
    print("  B2/B3 公开性检查（D1-H2）")
    print("  B4 其他 AI 私人状态不得泄露（D1-H2）")
    print("  B5 返回值不穿透 main.data（D1-H3）")
    print("  B6 五态语义（UNKNOWN != ABSENT；UNSUPPORTED 不猜测；FORBIDDEN 无 value）")
    print("  B7 反模式守卫（WQ-90 ～ WQ-93）")
    print("  B8 既有正确行为回归")
    print("=" * 72)


if __name__ == "__main__":
    _print_header()
    unittest.main(verbosity=2)
