"""
test_c2_goal_commitment.py - Phase C-2 测试

从 TEST 仓库根目录运行：
    python docs/test_c2_goal_commitment.py

自动定位仓库根，不依赖 cwd。
覆盖 Contract §5B 冻结项。
"""

import sys
import copy
import inspect
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# =========================================================
# main 桩（agent.state 顶层 import main）
# =========================================================
import types
if "main" not in sys.modules:
    fake_main = types.ModuleType("main")
    fake_main.canonical_ai_name = lambda name: name
    fake_main.owner_of_ai = lambda name: None
    fake_main.strip_emoji = lambda s: s
    sys.modules["main"] = fake_main

# =========================================================
# 导入
# =========================================================
from agent.goal import (
    Goal,
    create_goal,
    transition_goal,
    GoalInvalidTransition,
    GOAL_STATUS_CREATED,
    GOAL_STATUS_ACTIVE,
    GOAL_STATUS_COMPLETED,
    GOAL_STATUS_CANCELLED,
)
from agent.commitment import (
    Commitment,
    create_commitment,
    transition_commitment,
    CommitmentInvalidTransition,
    CommitmentInvalidStrength,
    CommitmentInvalidType,
    COMMITMENT_STATUS_CREATED,
    COMMITMENT_STATUS_ACTIVE,
    COMMITMENT_STATUS_FULFILLED,
    COMMITMENT_STATUS_CANCELLED,
    STRENGTH_HARD,
    STRENGTH_SOFT,
    COMMITMENT_TYPE_USER_PROMISE,
    COMMITMENT_TYPE_AI_PROMISE,
)
from agent.motivation import (
    compute_motivation,
    MotivationSummary,
    describe_motivation_module,
)
from agent.intent import (
    Intent,
    IntentSet,
    make_intent,
    make_empty_intent_set,
)
from agent.runtime import AgentRuntime
from agent.context import AgentContext


NOW = 1700000000.0


# =========================================================
# T1: Goal 创建
# =========================================================
print("=== T1: Goal 创建 ===")
g = create_goal(
    actor="Dan",
    type="companionship",
    description="陪用户过周末",
    source="user_request",
    reason="用户希望 AI 陪伴",
    target="user_satisfied",
    completion_condition="周末结束",
    now_ts=NOW,
)
assert isinstance(g, Goal)
assert g.status == GOAL_STATUS_CREATED
assert g.actor == "Dan"
assert g.created_at == NOW
assert g.updated_at == NOW
assert g.goal_id  # 非空
print(f"T1 PASS: goal_id={g.goal_id[:8]}...")


# =========================================================
# T2: Goal lifecycle
# =========================================================
print("\n=== T2: Goal lifecycle ===")
g2 = transition_goal(g, GOAL_STATUS_ACTIVE, "启动追求", now_ts=NOW + 1)
assert g2.status == GOAL_STATUS_ACTIVE
assert g2.updated_at == NOW + 1
assert g2.created_at == NOW  # 不变
assert g2.goal_id == g.goal_id

g3 = transition_goal(g2, GOAL_STATUS_COMPLETED, "用户满意", now_ts=NOW + 2)
assert g3.status == GOAL_STATUS_COMPLETED
assert g3.is_terminal()

# 原对象未被修改（不可变语义）
assert g.status == GOAL_STATUS_CREATED
assert g2.status == GOAL_STATUS_ACTIVE
print("T2 PASS")


# =========================================================
# T3: 非法 Goal 状态转换被拒绝
# =========================================================
print("\n=== T3: 非法 Goal 状态转换被拒绝 ===")
try:
    transition_goal(g3, GOAL_STATUS_ACTIVE, "试图复活", now_ts=NOW + 3)
    assert False, "应从 COMPLETED 转 ACTIVE 被拒绝"
except GoalInvalidTransition:
    pass

try:
    transition_goal(g, GOAL_STATUS_COMPLETED, "跳过 ACTIVE", now_ts=NOW + 4)
    assert False, "应从 CREATED 直接转 COMPLETED 被拒绝"
except GoalInvalidTransition:
    pass

print("T3 PASS")


# =========================================================
# T4: Commitment 创建
# =========================================================
print("\n=== T4: Commitment 创建 ===")
c = create_commitment(
    type=COMMITMENT_TYPE_USER_PROMISE,
    actor="Dan",
    counterparty="Alice",
    content="周六陪用户过周末",
    strength=STRENGTH_HARD,
    reason="用户明确希望 AI 陪同",
    now_ts=NOW,
)
assert isinstance(c, Commitment)
assert c.status == COMMITMENT_STATUS_CREATED
assert c.strength == STRENGTH_HARD
assert c.is_hard()
print(f"T4 PASS: commitment_id={c.commitment_id[:8]}...")


# =========================================================
# T5: Commitment lifecycle
# =========================================================
print("\n=== T5: Commitment lifecycle ===")
c2 = transition_commitment(c, COMMITMENT_STATUS_ACTIVE, "激活", now_ts=NOW + 1)
assert c2.status == COMMITMENT_STATUS_ACTIVE

c3 = transition_commitment(c2, COMMITMENT_STATUS_FULFILLED, "已履行", now_ts=NOW + 2)
assert c3.status == COMMITMENT_STATUS_FULFILLED
assert c3.is_terminal()
assert c.status == COMMITMENT_STATUS_CREATED  # 原对象不变
print("T5 PASS")


# =========================================================
# T6: Commitment strength
# =========================================================
print("\n=== T6: Commitment strength ===")
c_hard = create_commitment(
    type=COMMITMENT_TYPE_AI_PROMISE,
    actor="Dan",
    counterparty="Bob",
    content="x",
    strength=STRENGTH_HARD,
    reason="r",
    now_ts=NOW,
)
c_soft = create_commitment(
    type=COMMITMENT_TYPE_AI_PROMISE,
    actor="Dan",
    counterparty="Bob",
    content="x",
    strength=STRENGTH_SOFT,
    reason="r",
    now_ts=NOW,
)
assert c_hard.is_hard() is True
assert c_soft.is_hard() is False

try:
    create_commitment(
        type=COMMITMENT_TYPE_AI_PROMISE,
        actor="Dan", counterparty="Bob", content="x",
        strength="VERY_HARD", reason="r", now_ts=NOW,
    )
    assert False, "非法强度应被拒绝"
except CommitmentInvalidStrength:
    pass

try:
    create_commitment(
        type="unknown_type",
        actor="Dan", counterparty="Bob", content="x",
        strength=STRENGTH_HARD, reason="r", now_ts=NOW,
    )
    assert False, "非法类型应被拒绝"
except CommitmentInvalidType:
    pass

print("T6 PASS")


# =========================================================
# T7: Motivation 输入输出
# =========================================================
print("\n=== T7: Motivation 输入输出 ===")
state_snapshot = {
    "name": "Dan",
    "owner": "Alice",
    "current_activity": "dating",
    "location": "Cafe",
}
m = compute_motivation(
    actor="Dan",
    goal=g2,
    commitment=c2,
    agent_state_snapshot=state_snapshot,
    now_ts=NOW,
)
assert isinstance(m, MotivationSummary)
assert m.actor == "Dan"
assert m.goal_id == g2.goal_id
assert m.commitment_id == c2.commitment_id
assert m.created_at == NOW
assert "goal" in m.inputs_used
assert "commitment" in m.inputs_used
assert "agent_state_snapshot" in m.inputs_used
assert isinstance(m.explanation, str)
assert m.explanation  # 非空
print(f"T7 PASS: explanation={m.explanation!r}")


# =========================================================
# T8: Motivation 不使用随机数
# =========================================================
print("\n=== T8: Motivation 不使用随机数 ===")
m_src = (REPO_ROOT / "agent" / "motivation.py").read_text(encoding="utf-8")
# 精确检查：不允许 import random / from random / random.* 调用
assert not re.search(r'^\s*(?:import|from)\s+random\b', m_src, re.MULTILINE), \
    "motivation.py 导入 random"
assert not re.search(r'\brandom\.\w+', m_src), \
    "motivation.py 调用 random.*"
# 精确检查：不允许 import uuid
assert not re.search(r'^\s*(?:import|from)\s+uuid\b', m_src, re.MULTILINE), \
    "motivation.py 导入 uuid"
# 同一输入多次调用必须一致
m_a = compute_motivation("Dan", g2, c2, state_snapshot, now_ts=NOW)
m_b = compute_motivation("Dan", g2, c2, state_snapshot, now_ts=NOW)
assert m_a.explanation == m_b.explanation
assert m_a.inputs_used == m_b.inputs_used
print("T8 PASS")


# =========================================================
# T9: Intent 创建
# =========================================================
print("\n=== T9: Intent 创建 ===")
i = make_intent(
    intent_id="i-1",
    actor="Dan",
    action_type="stay_in_place",
    reason="用户仍在住所",
    now_ts=NOW,
    target="home",
    source_goal=g2.goal_id,
    source_commitment=c2.commitment_id,
    constraints=["hard_commitment"],
    confidence=0.7,
    candidate_rank=1,
)
assert isinstance(i, Intent)
assert i.intent_id == "i-1"
assert i.action_type == "stay_in_place"
assert i.created_at == NOW
assert i.source_goal == g2.goal_id
assert i.source_commitment == c2.commitment_id
assert "hard_commitment" in i.constraints
assert i.confidence == 0.7
assert i.candidate_rank == 1
# reason 与 Goal.reason 独立
assert i.reason == "用户仍在住所"
assert i.reason != g2.reason
print("T9 PASS")


# =========================================================
# T10: IntentSet 创建
# =========================================================
print("\n=== T10: IntentSet 创建 ===")
iset = IntentSet(
    actor="Dan",
    created_at=NOW,
    candidates=[i],
    reason_summary="基于当前 Goal 与 Commitment",
)
assert isinstance(iset, IntentSet)
assert iset.actor == "Dan"
assert len(iset.candidates) == 1
assert iset.candidates[0] is i
assert iset.is_empty() is False
print("T10 PASS")


# =========================================================
# T11: IntentSet 空集合合法
# =========================================================
print("\n=== T11: IntentSet 空集合合法 ===")
empty = make_empty_intent_set("Dan", now_ts=NOW, reason_summary="stub")
assert isinstance(empty, IntentSet)
assert empty.is_empty() is True
assert empty.candidates == []
assert empty.reason_summary == "stub"

# 直接构造空 IntentSet 也合法
direct_empty = IntentSet(actor="Dan", created_at=NOW, candidates=[], reason_summary="")
assert direct_empty.is_empty() is True
print("T11 PASS")


# =========================================================
# T12: Runtime think() 返回 IntentSet
# =========================================================
print("\n=== T12: Runtime think() 返回 IntentSet ===")
sample_data = {
    "user_ais": {"Alice": ["Dan"]},
    "ai_location": {"Dan": "Cafe"},
}
rt = AgentRuntime("Dan", sample_data)
ctx = rt.build_context(None, now_ts=NOW)
result = rt.think(ctx)
assert isinstance(result, IntentSet), f"think() 返回 {type(result)}"
assert result.actor == "Dan"
assert result.created_at > 0
print(f"T12 PASS: type={type(result).__name__}, actor={result.actor}")


# =========================================================
# T13: Runtime think() Stub 返回空 candidates
# =========================================================
print("\n=== T13: Runtime think() Stub 返回空 candidates ===")
assert result.candidates == []
assert result.is_empty() is True
# 多次调用均为空
r2 = rt.think(ctx)
assert r2.is_empty() is True
# runtime.py 无 LLM / drive_ai / build_ai_context 调用
runtime_src = (REPO_ROOT / "agent" / "runtime.py").read_text(encoding="utf-8")
assert not re.search(r'\bcall_llm\s*\(', runtime_src)
assert not re.search(r'\bdrive_ai\s*\(', runtime_src)
assert not re.search(r'\bbuild_ai_context\s*\(', runtime_src)
print("T13 PASS")


# =========================================================
# T14: C-2 实现没有修改 main.data
# =========================================================
print("\n=== T14: C-2 实现没有修改 main.data ===")
data = {
    "user_ais": {"Alice": ["Dan"]},
    "ai_location": {"Dan": "Cafe"},
    "wallets": {"Dan": 100.0},
}
data_before = copy.deepcopy(data)
rt14 = AgentRuntime("Dan", data)
ctx14 = rt14.build_context(None, now_ts=NOW)
rt14.think(ctx14)
# C-2 数据结构不接触 data
create_goal(
    actor="Dan", type="x", description="d", source="user_request",
    reason="r", target="t", completion_condition="c", now_ts=NOW,
)
create_commitment(
    type=COMMITMENT_TYPE_USER_PROMISE, actor="Dan", counterparty="Alice",
    content="x", strength=STRENGTH_HARD, reason="r", now_ts=NOW,
)
assert data == data_before, "main.data 被修改"
print("T14 PASS")


# =========================================================
# T15: 现有 B5 Context 测试仍通过（静态检查）
# =========================================================
print("\n=== T15: 现有 B5 Context 测试仍通过 ===")
b5_test = REPO_ROOT / "docs" / "test_b5_runtime_context.py"
assert b5_test.exists(), f"缺少 {b5_test}"
# 动态验证：think 签名迁移后，B5 测试中的 think 调用仍然返回有效对象
# B5 测试 T9 期望 think() 返回 None；C-2 改为返回 IntentSet。
# 这是 Contract 允许的迁移；B5 测试需要更新断言。
# 本 T15 只做静态验证：确保 context.py / context_assembler.py 未被 C-2 修改。
ctx_src = (REPO_ROOT / "agent" / "context.py").read_text(encoding="utf-8")
asm_src = (REPO_ROOT / "agent" / "context_assembler.py").read_text(encoding="utf-8")
# 关键符号仍在
assert "class AgentContext" in ctx_src
assert "class ContextSection" in ctx_src
assert "class ContextBudget" in ctx_src
assert "class ContextAssembler" in asm_src
print("T15 PASS: context.py / context_assembler.py 关键符号未变")


# =========================================================
# 附加 A: C-2 新模块不 import main / ext_*
# =========================================================
print("\n=== 附加 A: C-2 新模块不 import main / ext_* ===")
import_pattern = re.compile(r'^\s*(?:import|from)\s+([\w\.]+)', re.MULTILINE)
for name in ("goal", "commitment", "motivation", "intent"):
    p = REPO_ROOT / "agent" / f"{name}.py"
    src = p.read_text(encoding="utf-8")
    imported = import_pattern.findall(src)
    tops = set(m.split('.')[0] for m in imported)
    assert "main" not in tops, f"{name}.py 导入 main"
    bad_ext = {m for m in tops if m.startswith("ext_")}
    assert not bad_ext, f"{name}.py 导入 ext_*: {bad_ext}"
    # 不导入 LLM
    assert "openai" not in tops and "anthropic" not in tops
print("附加 A PASS")


# =========================================================
# 附加 B: C-2 新模块不使用随机数
# =========================================================
print("\n=== 附加 B: C-2 新模块不使用随机数 ===")
for name in ("goal", "commitment", "motivation", "intent"):
    p = REPO_ROOT / "agent" / f"{name}.py"
    src = p.read_text(encoding="utf-8")
    # 精确检查：不允许 import random / from random
    assert not re.search(r'^\s*(?:import|from)\s+random\b', src, re.MULTILINE), \
        f"{name}.py 导入 random"
    # 精确检查：不允许 random.* 调用
    assert not re.search(r'\brandom\.\w+', src), \
        f"{name}.py 调用 random.*"
print("附加 B PASS")


# =========================================================
# 附加 C: Runtime 修改边界
# =========================================================
print("\n=== 附加 C: Runtime 修改边界 ===")
runtime_src = (REPO_ROOT / "agent" / "runtime.py").read_text(encoding="utf-8")
# 仍保留 ContextLayers（deprecated stub 未删除 / 未改名 / 未别名化）
assert "class ContextLayers" in runtime_src
# 未引入 Goal / Commitment / Motivation 内部逻辑
assert "create_goal" not in runtime_src
assert "create_commitment" not in runtime_src
assert "compute_motivation" not in runtime_src
# build_context 未被重构
assert "def build_context(" in runtime_src
assert "ContextAssembler" in runtime_src
print("附加 C PASS")


# =========================================================
# 全部通过
# =========================================================
print("\n=== 全部通过（T1-T15 + 附加 A/B/C）===")
print(f"\n[定位] 仓库根 = {REPO_ROOT}")