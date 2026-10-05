"""
test_c3_contract_structure.py - C-3 Contract Structure + T-B/C/D 缺口测试

从 TEST 仓库根目录运行：
    python docs/test_c3_contract_structure.py

覆盖：
- T-A Contract Structure (A1 - A10)
- T-B 缺口 G2: B11（Goal 无自动创建）
- T-C 缺口 G3: C9（hard Commitment 允许 ACTIVE → CANCELLED）
- T-C 缺口 G4: C11（无 AI↔AI negotiation）
- T-D 缺口 G5: D4（Motivation 纯函数重复调用一致）
- T-D 缺口 G6: D11（Motivation 不消费 Relationship / Memory / Recent / World Query）
- T-F 缺口 G12: F7（ContextLayers deprecated stub 状态）

边界：
- 不修改任何 .py
- 不调用 LLM / 网络
- 不创建持久化
- 不修改 main.data
"""

import sys
import re
import types
import dataclasses
import inspect
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# main 桩（在导入 agent.* 之前）
if "main" not in sys.modules:
    fake_main = types.ModuleType("main")
    fake_main.canonical_ai_name = lambda name: name
    fake_main.owner_of_ai = lambda name: None
    fake_main.strip_emoji = lambda s: s
    sys.modules["main"] = fake_main


AGENT_DIR = REPO_ROOT / "agent"


# =========================================================
# T-A: Contract Structure
# =========================================================
print("=== T-A: Contract Structure ===")

# --- A1: 文件存在 ---
for fn in ("goal.py", "commitment.py", "motivation.py", "intent.py", "runtime.py"):
    p = AGENT_DIR / fn
    assert p.exists(), f"缺少 {p}"
print("A1 PASS: 5 个文件存在")

# --- A2: Goal 必需字段 ---
from agent.goal import Goal
goal_field_names = {f.name for f in dataclasses.fields(Goal)}
expected_goal_required = {
    "goal_id", "actor", "type", "description", "source",
    "status", "created_at", "updated_at", "reason",
    "target", "completion_condition",
}
missing = expected_goal_required - goal_field_names
assert not missing, f"Goal 缺字段: {missing}"
print(f"A2 PASS: Goal 必需字段完整（{len(goal_field_names)} 字段）")

# --- A3: Commitment 必需字段 ---
from agent.commitment import Commitment
comm_field_names = {f.name for f in dataclasses.fields(Commitment)}
expected_comm_required = {
    "commitment_id", "type", "actor", "counterparty", "content",
    "strength", "status", "created_at", "updated_at", "reason",
}
missing = expected_comm_required - comm_field_names
assert not missing, f"Commitment 缺字段: {missing}"
print(f"A3 PASS: Commitment 必需字段完整（{len(comm_field_names)} 字段）")

# --- A4: Goal 状态机 ---
from agent.goal import (
    ALL_GOAL_STATUSES,
    GOAL_STATUS_CREATED, GOAL_STATUS_ACTIVE, GOAL_STATUS_COMPLETED,
    GOAL_STATUS_CANCELLED, GOAL_STATUS_EXPIRED,
)
for s in (GOAL_STATUS_CREATED, GOAL_STATUS_ACTIVE, GOAL_STATUS_COMPLETED,
          GOAL_STATUS_CANCELLED, GOAL_STATUS_EXPIRED):
    assert s in ALL_GOAL_STATUSES, f"Goal 状态缺 {s}"
print(f"A4 PASS: Goal 状态机 {sorted(ALL_GOAL_STATUSES)}")

# --- A5: Commitment 状态机 ---
from agent.commitment import (
    ALL_COMMITMENT_STATUSES,
    COMMITMENT_STATUS_CREATED, COMMITMENT_STATUS_ACTIVE,
    COMMITMENT_STATUS_FULFILLED, COMMITMENT_STATUS_CANCELLED,
    COMMITMENT_STATUS_EXPIRED,
)
for s in (COMMITMENT_STATUS_CREATED, COMMITMENT_STATUS_ACTIVE,
          COMMITMENT_STATUS_FULFILLED, COMMITMENT_STATUS_CANCELLED,
          COMMITMENT_STATUS_EXPIRED):
    assert s in ALL_COMMITMENT_STATUSES, f"Commitment 状态缺 {s}"
print(f"A5 PASS: Commitment 状态机 {sorted(ALL_COMMITMENT_STATUSES)}")

# --- A6: 4 个新文件无禁止导入 ---
import_pattern = re.compile(r'^\s*(?:import|from)\s+([\w\.]+)', re.MULTILINE)
LLM_LIBS = {"openai", "anthropic", "httpx", "aiohttp", "requests", "urllib"}
for fn in ("goal.py", "commitment.py", "motivation.py", "intent.py"):
    src = (AGENT_DIR / fn).read_text(encoding="utf-8")
    tops = {m.split('.')[0] for m in import_pattern.findall(src)}
    assert "main" not in tops, f"{fn} 导入 main"
    bad_ext = {m for m in tops if m.startswith("ext_")}
    assert not bad_ext, f"{fn} 导入 ext_*: {bad_ext}"
    assert "random" not in tops, f"{fn} 导入 random"
    bad_llm = tops & LLM_LIBS
    assert not bad_llm, f"{fn} 导入 LLM 库: {bad_llm}"
print("A6 PASS: 4 个新文件无禁止导入")

# --- A7: think 签名 -> IntentSet ---
from agent.runtime import AgentRuntime
from agent.intent import IntentSet
sig = inspect.signature(AgentRuntime.think)
assert "context" in sig.parameters, "think 缺 context 参数"
ret = sig.return_annotation
ret_name = getattr(ret, "__name__", str(ret))
assert "IntentSet" in ret_name, f"think 返回类型: {ret_name}"
print(f"A7 PASS: think 签名 -> {ret_name}")

# --- A8: runtime.py 无 LLM / drive_ai / build_ai_context ---
runtime_src = (AGENT_DIR / "runtime.py").read_text(encoding="utf-8")
assert not re.search(r'\bcall_llm\s*\(', runtime_src)
assert not re.search(r'\bdrive_ai\s*\(', runtime_src)
assert not re.search(r'\bbuild_ai_context\s*\(', runtime_src)
print("A8 PASS: runtime.py 无 LLM / drive_ai / build_ai_context")

# --- A9: ContextLayers deprecated stub ---
from agent.runtime import ContextLayers
from agent.context import AgentContext
assert ContextLayers is not AgentContext, "ContextLayers 不应被别名化"
cl = ContextLayers()
for attr in ("stable_core", "recent", "long_term", "dynamic_world"):
    assert hasattr(cl, attr), f"ContextLayers 缺 {attr}"
print("A9 PASS: ContextLayers deprecated stub 完整")

# --- A10: 未触碰的文件（静态检查：不 import 新模块） ---
for fn in ("context.py", "context_assembler.py", "state.py", "event.py"):
    p = AGENT_DIR / fn
    assert p.exists(), f"缺少 {p}"
    src = p.read_text(encoding="utf-8")
    tops = {m.split('.')[0] for m in import_pattern.findall(src)}
    # 不应引用 C-2 新增模块
    for bad in ("goal", "commitment", "motivation", "intent"):
        assert bad not in tops, f"{fn} 引用了 {bad}"
assert (REPO_ROOT / "main.py").exists()
print("A10 PASS: context/context_assembler/state/event 未引用 C-2 新增模块")


# =========================================================
# T-B 缺口 G2: B11 Goal 无自动创建
# =========================================================
print("\n=== T-B: B11 Goal 无自动创建 ===")
goal_src = (AGENT_DIR / "goal.py").read_text(encoding="utf-8")
forbidden = [
    r'\bschedule\b', r'\btimer\b', r'\blisten\b', r'\bsubscribe\b',
    r'\bwatch\b', r'\bon_event\b', r'\bauto_create\b', r'\bauto_goal\b',
]
for pat in forbidden:
    assert not re.search(pat, goal_src, re.IGNORECASE), f"goal.py 含 {pat}"
print("B11 PASS: goal.py 无自动创建机制")


# =========================================================
# T-C 缺口 G3: C9 hard Commitment 允许 ACTIVE → CANCELLED
# =========================================================
print("\n=== T-C: C9 hard Commitment 允许被 CANCELLED ===")
from agent.commitment import (
    create_commitment, transition_commitment,
    STRENGTH_HARD, COMMITMENT_TYPE_USER_PROMISE,
    COMMITMENT_STATUS_ACTIVE, COMMITMENT_STATUS_CANCELLED,
)
NOW = 1700000000.0
hard_c = create_commitment(
    type=COMMITMENT_TYPE_USER_PROMISE,
    actor="Dan", counterparty="Alice",
    content="周六陪用户过周末", strength=STRENGTH_HARD,
    reason="用户明确希望", now_ts=NOW,
)
hard_c2 = transition_commitment(
    hard_c, COMMITMENT_STATUS_ACTIVE, "激活", now_ts=NOW + 1,
)
# hard Commitment 从 ACTIVE → CANCELLED 必须被允许（不是"永远不可违背"）
hard_c3 = transition_commitment(
    hard_c2, COMMITMENT_STATUS_CANCELLED,
    "世界硬约束导致无法履行", now_ts=NOW + 2,
)
assert hard_c3.status == COMMITMENT_STATUS_CANCELLED
print("C9 PASS: hard Commitment 允许 ACTIVE → CANCELLED")


# =========================================================
# T-C 缺口 G4: C11 无 AI↔AI negotiation
# =========================================================
print("\n=== T-C: C11 无 AI↔AI negotiation ===")
comm_src = (AGENT_DIR / "commitment.py").read_text(encoding="utf-8")
# 精确检查：不允许出现"真的定义协商函数 / 调用协商 API"
# 允许 describe() 中出现 "ai_to_ai_negotiation": False 这类元数据声明
forbidden_patterns = [
    r'\bdef\s+negotiate\b',           # def negotiate(...)
    r'\bdef\s+negotiation\b',         # def negotiation(...)
    r'\.negotiate\s*\(',              # obj.negotiate(...)
    r'\bpeer_commitment\b',           # peer_commitment 变量/字段
    r'\bother_ai_commitment\b',       # other_ai_commitment
]
for pat in forbidden_patterns:
    assert not re.search(pat, comm_src), f"commitment.py 含 {pat}"
print("C11 PASS: commitment.py 无 AI↔AI negotiation 函数/调用")


# =========================================================
# T-D 缺口 G5: D4 Motivation 纯函数重复调用一致
# =========================================================
print("\n=== T-D: D4 Motivation 纯函数一致 ===")
from agent.motivation import compute_motivation
from agent.goal import create_goal
g = create_goal(
    actor="Dan", type="x", description="d", source="user_request",
    reason="r", target="t", completion_condition="c", now_ts=NOW,
)
state_snap = {"name": "Dan", "owner": "Alice",
              "current_activity": "dating", "location": "Cafe"}
m1 = compute_motivation("Dan", g, None, state_snap, now_ts=NOW)
m2 = compute_motivation("Dan", g, None, state_snap, now_ts=NOW)
assert m1.explanation == m2.explanation
assert m1.inputs_used == m2.inputs_used
assert m1.created_at == m2.created_at
assert m1.created_at == NOW
print("D4 PASS: Motivation 纯函数一致，now_ts 未重读")


# =========================================================
# T-D 缺口 G6: D11 Motivation 不消费未冻结输入
# =========================================================
print("\n=== T-D: D11 Motivation 不消费未冻结输入 ===")
motiv_src = (AGENT_DIR / "motivation.py").read_text(encoding="utf-8")
motiv_tops = {m.split('.')[0] for m in import_pattern.findall(motiv_src)}
forbidden_modules = {"relationship", "memory", "recent", "world_query"}
bad = motiv_tops & forbidden_modules
assert not bad, f"motivation.py 导入禁止模块: {bad}"
print("D11 PASS: motivation.py 无 Relationship / Memory / Recent / WorldQuery 导入")


# =========================================================
# T-F 缺口 G12: F7 ContextLayers 未接回正式链
# =========================================================
print("\n=== T-F: F7 ContextLayers 状态 ===")
rt = AgentRuntime("Dan", {"user_ais": {"Alice": ["Dan"]}})
ctx = rt.build_context(None, now_ts=NOW)
assert isinstance(ctx, AgentContext), "build_context 应返回 AgentContext"
assert not isinstance(ctx, ContextLayers)
result = rt.think(ctx)
assert isinstance(result, IntentSet), "think 应返回 IntentSet"
assert not isinstance(result, ContextLayers)
print("F7 PASS: ContextLayers 未接回正式链")


# =========================================================
# 全部通过
# =========================================================
print("\n=== 全部通过（T-A + T-B/C/D 缺口 + F7）===")
print(f"\n[定位] 仓库根 = {REPO_ROOT}")