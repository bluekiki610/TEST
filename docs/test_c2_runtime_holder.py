"""
test_c2_runtime_holder.py - C-2 Patch Runtime holder 自测

从 TEST 仓库根目录运行：
    python docs/test_c2_runtime_holder.py

覆盖 Runtime holder 的最小 API 与边界：
- add / get / list / replace
- add 重复 ID → reject
- replace 不存在 ID → reject
- holder 未越界（无 LLM / ext_* / persistence / main.data mutation）
"""

import sys
import copy
import re
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# main 桩
if "main" not in sys.modules:
    fake_main = types.ModuleType("main")
    fake_main.canonical_ai_name = lambda name: name
    fake_main.owner_of_ai = lambda name: None
    fake_main.strip_emoji = lambda s: s
    sys.modules["main"] = fake_main

from agent.runtime import (
    AgentRuntime,
    GoalAlreadyExists,
    GoalNotFound,
    CommitmentAlreadyExists,
    CommitmentNotFound,
)
from agent.goal import Goal, create_goal
from agent.commitment import Commitment, create_commitment


NOW = 1700000000.0


def sample_data():
    return {
        "user_ais": {"Alice": ["Dan"]},
        "ai_location": {"Dan": "Cafe"},
        "wallets": {"Dan": 100.0},
        "affection": {"Dan": 60},
        "ai_follow": {},
        "work_sessions": {},
        "dates": [],
        "ai_timeline": {},
        "trails": {},
        "ai_visited": {},
        "world_lore": "",
        "ai_profiles": {},
        "user_profiles": {},
    }


# =========================================================
# H1: holder 初始为空
# =========================================================
print("=== H1: holder 初始为空 ===")
rt = AgentRuntime("Dan", sample_data())
assert rt.list_goals() == []
assert rt.list_commitments() == []
assert rt.get_goal("x") is None
assert rt.get_commitment("x") is None
print("H1 PASS")


# =========================================================
# H2: add_goal / get_goal
# =========================================================
print("\n=== H2: add_goal / get_goal ===")
g = create_goal(
    actor="Dan", type="companionship", description="陪用户过周末",
    source="user_request", reason="用户希望",
    target="user_satisfied", completion_condition="周末结束",
    now_ts=NOW,
)
rt.add_goal(g)
returned = rt.get_goal(g.goal_id)
assert returned is not None
assert returned == g, "get_goal 应返回值相等的副本"
assert returned is not g, "get_goal 不应返回 holder 内部对象（hardening）"
assert len(rt.list_goals()) == 1
print(f"H2 PASS: goal_id={g.goal_id[:8]}...")


# =========================================================
# H3: add_goal 重复 ID → reject
# =========================================================
print("\n=== H3: add_goal 重复 ID → reject ===")
try:
    rt.add_goal(g)
    assert False, "重复 ID 应被 reject"
except GoalAlreadyExists:
    pass
print("H3 PASS")


# =========================================================
# H4: replace_goal
# =========================================================
print("\n=== H4: replace_goal ===")
from agent.goal import transition_goal, GOAL_STATUS_ACTIVE
g2 = transition_goal(g, GOAL_STATUS_ACTIVE, "启动", now_ts=NOW + 1)
rt.replace_goal(g2)
returned_g = rt.get_goal(g.goal_id)
assert returned_g is not None
assert returned_g == g2
assert returned_g is not g2, "replace_goal 后 get 不应返回 holder 内部对象"
assert returned_g.status == GOAL_STATUS_ACTIVE
print("H4 PASS")


# =========================================================
# H5: replace_goal 不存在 ID → reject
# =========================================================
print("\n=== H5: replace_goal 不存在 ID → reject ===")
g_other = create_goal(
    actor="Dan", type="x", description="d", source="user_request",
    reason="r", target="t", completion_condition="c", now_ts=NOW,
)
try:
    rt.replace_goal(g_other)
    assert False, "不存在的 ID 应被 reject"
except GoalNotFound:
    pass
print("H5 PASS")


# =========================================================
# H6: add_commitment / get_commitment
# =========================================================
print("\n=== H6: add_commitment / get_commitment ===")
c = create_commitment(
    type="user_promise", actor="Dan", counterparty="Alice",
    content="周六陪用户过周末", strength="hard",
    reason="用户明确希望", now_ts=NOW,
)
rt.add_commitment(c)
returned_c = rt.get_commitment(c.commitment_id)
assert returned_c is not None
assert returned_c == c
assert returned_c is not c, "get_commitment 不应返回 holder 内部对象（hardening）"
assert len(rt.list_commitments()) == 1
print(f"H6 PASS: commitment_id={c.commitment_id[:8]}...")


# =========================================================
# H7: add_commitment 重复 ID → reject
# =========================================================
print("\n=== H7: add_commitment 重复 ID → reject ===")
try:
    rt.add_commitment(c)
    assert False, "重复 ID 应被 reject"
except CommitmentAlreadyExists:
    pass
print("H7 PASS")


# =========================================================
# H8: replace_commitment
# =========================================================
print("\n=== H8: replace_commitment ===")
from agent.commitment import transition_commitment, COMMITMENT_STATUS_ACTIVE
c2 = transition_commitment(c, COMMITMENT_STATUS_ACTIVE, "激活", now_ts=NOW + 1)
rt.replace_commitment(c2)
returned_c2 = rt.get_commitment(c.commitment_id)
assert returned_c2 is not None
assert returned_c2 == c2
assert returned_c2 is not c2, "replace_commitment 后 get 不应返回 holder 内部对象"
assert returned_c2.status == COMMITMENT_STATUS_ACTIVE
print("H8 PASS")


# =========================================================
# H9: replace_commitment 不存在 ID → reject
# =========================================================
print("\n=== H9: replace_commitment 不存在 ID → reject ===")
c_other = create_commitment(
    type="ai_promise", actor="Dan", counterparty="Bob",
    content="x", strength="soft", reason="r", now_ts=NOW,
)
try:
    rt.replace_commitment(c_other)
    assert False, "不存在的 ID 应被 reject"
except CommitmentNotFound:
    pass
print("H9 PASS")


# =========================================================
# H10: list_goals / list_commitments 返回副本
# =========================================================
print("\n=== H10: list 返回副本 ===")
list_g = rt.list_goals()
list_c = rt.list_commitments()
list_g.append("intruder")
list_c.append("intruder")
assert "intruder" not in rt.list_goals()
assert "intruder" not in rt.list_commitments()
print("H10 PASS")


# =========================================================
# H11: holder 不修改 main.data
# =========================================================
print("\n=== H11: holder 不修改 main.data ===")
data = sample_data()
data_before = copy.deepcopy(data)
rt11 = AgentRuntime("Dan", data)
g11 = create_goal(
    actor="Dan", type="x", description="d", source="user_request",
    reason="r", target="t", completion_condition="c", now_ts=NOW,
)
c11 = create_commitment(
    type="user_promise", actor="Dan", counterparty="Alice",
    content="x", strength="hard", reason="r", now_ts=NOW,
)
rt11.add_goal(g11)
rt11.add_commitment(c11)
assert data == data_before, "holder 修改了 main.data"
print("H11 PASS")


# =========================================================
# H12: think 仍 Stub
# =========================================================
print("\n=== H12: think 仍 Stub ===")
from agent.intent import IntentSet
rt12 = AgentRuntime("Dan", sample_data())
ctx = rt12.build_context(None, now_ts=NOW)
r = rt12.think(ctx)
assert isinstance(r, IntentSet)
assert r.candidates == []
print("H12 PASS")


# =========================================================
# H13: runtime.py 未越界（静态检查）
# =========================================================
print("\n=== H13: runtime.py 未越界 ===")
src = (REPO_ROOT / "agent" / "runtime.py").read_text(encoding="utf-8")
assert not re.search(r'\bcall_llm\s*\(', src)
assert not re.search(r'\bdrive_ai\s*\(', src)
assert not re.search(r'\bbuild_ai_context\s*\(', src)
assert not re.search(r'^\s*(?:import|from)\s+random\b', src, re.MULTILINE)
assert not re.search(r'^\s*(?:import|from)\s+ext_', src, re.MULTILINE)
assert not re.search(r'^\s*import\s+main\b', src, re.MULTILINE)
# ContextLayers 保留
assert "class ContextLayers" in src
print("H13 PASS")

# =========================================================
# H14: get_goal 返回副本，外部修改不影响 holder
# =========================================================
print("\n=== H14: get_goal 返回副本 ===")
rt14 = AgentRuntime("Dan", sample_data())
g14 = create_goal(
    actor="Dan", type="x", description="d", source="user_request",
    reason="r", target="t", completion_condition="c", now_ts=NOW,
)
rt14.add_goal(g14)

# 外部通过 get_goal 拿到对象，修改其字段
fetched = rt14.get_goal(g14.goal_id)
assert fetched is not None
fetched.description = "MUTATED_BY_EXTERNAL"
fetched.status = "COMPLETED"
fetched.reason = "MUTATED_REASON"

# holder 内部必须不变
internal = rt14.get_goal(g14.goal_id)
assert internal.description == "d", f"holder 被外部穿透：{internal.description!r}"
assert internal.status == "CREATED", f"holder status 被穿透：{internal.status!r}"
assert internal.reason == "r", f"holder reason 被穿透：{internal.reason!r}"
print("H14 PASS: get_goal 返回副本，holder 未被穿透")


# =========================================================
# H15: list_goals 返回副本，外部修改不影响 holder
# =========================================================
print("\n=== H15: list_goals 返回副本 ===")
lst = rt14.list_goals()
assert len(lst) == 1
lst[0].description = "MUTATED_BY_LIST"
lst[0].status = "CANCELLED"

internal = rt14.get_goal(g14.goal_id)
assert internal.description == "d", f"holder 被 list 穿透：{internal.description!r}"
assert internal.status == "CREATED", f"holder status 被 list 穿透：{internal.status!r}"
print("H15 PASS: list_goals 返回副本，holder 未被穿透")


# =========================================================
# H16: get_commitment 返回副本，外部修改不影响 holder
# =========================================================
print("\n=== H16: get_commitment 返回副本 ===")
rt16 = AgentRuntime("Dan", sample_data())
c16 = create_commitment(
    type="user_promise", actor="Dan", counterparty="Alice",
    content="原始内容", strength="hard", reason="r", now_ts=NOW,
)
rt16.add_commitment(c16)

fetched_c = rt16.get_commitment(c16.commitment_id)
assert fetched_c is not None
fetched_c.content = "MUTATED_CONTENT"
fetched_c.strength = "soft"
fetched_c.status = "FULFILLED"

internal_c = rt16.get_commitment(c16.commitment_id)
assert internal_c.content == "原始内容", f"holder 被穿透：{internal_c.content!r}"
assert internal_c.strength == "hard", f"holder strength 被穿透：{internal_c.strength!r}"
assert internal_c.status == "CREATED", f"holder status 被穿透：{internal_c.status!r}"
print("H16 PASS: get_commitment 返回副本，holder 未被穿透")


# =========================================================
# H17: list_commitments 返回副本，外部修改不影响 holder
# =========================================================
print("\n=== H17: list_commitments 返回副本 ===")
lst_c = rt16.list_commitments()
assert len(lst_c) == 1
lst_c[0].content = "MUTATED_BY_LIST"
lst_c[0].status = "CANCELLED"

internal_c = rt16.get_commitment(c16.commitment_id)
assert internal_c.content == "原始内容", f"holder 被 list 穿透：{internal_c.content!r}"
assert internal_c.status == "CREATED", f"holder status 被 list 穿透：{internal_c.status!r}"
print("H17 PASS: list_commitments 返回副本，holder 未被穿透")

# =========================================================
# 全部通过
# =========================================================
print("\n=== 全部通过（H1-H17）===")
print(f"\n[定位] 仓库根 = {REPO_ROOT}")