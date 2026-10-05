"""
test_c3_boundary.py - C-3 Runtime / SOT / Boundary Tests

从 TEST 仓库根目录运行：
    python docs/test_c3_boundary.py

覆盖 T-E (Runtime / SOT / Boundary)：
- G7: E3 无持久化
- G8: E4 无 persistence mechanism
- G9: E9 Holder 真正 private，无绕过路径
- G10: E10 Holder API 白名单
- G11: E11 无 auto/scheduler/priority/conflict

同时覆盖 E1 / E2 / E5 / E6 / E7 / E8。

边界：
- 不修改任何 .py
- 不调用 LLM / 网络
- 不创建持久化
- 不修改 main.data
"""

import sys
import copy
import re
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if "main" not in sys.modules:
    fake_main = types.ModuleType("main")
    fake_main.canonical_ai_name = lambda name: name
    fake_main.owner_of_ai = lambda name: None
    fake_main.strip_emoji = lambda s: s
    sys.modules["main"] = fake_main


from agent.runtime import AgentRuntime
from agent.goal import create_goal
from agent.commitment import create_commitment


NOW = 1700000000.0
AGENT_DIR = REPO_ROOT / "agent"
import_pattern = re.compile(r'^\s*(?:import|from)\s+([\w\.]+)', re.MULTILINE)


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
# E1: Goal / Commitment 创建前后 main.data 不变
# =========================================================
print("=== E1: main.data 不变 ===")
data = sample_data()
before = copy.deepcopy(data)
rt = AgentRuntime("Dan", data)
g = create_goal(
    actor="Dan", type="x", description="d",
    source="user_request", reason="r",
    target="t", completion_condition="c", now_ts=NOW,
)
c = create_commitment(
    type="user_promise", actor="Dan", counterparty="Alice",
    content="x", strength="hard", reason="r", now_ts=NOW,
)
rt.add_goal(g)
rt.add_commitment(c)
assert data == before, "main.data 被修改"
print("E1 PASS")


# =========================================================
# E2: main.data 无 Goal / Commitment 字段
# =========================================================
print("\n=== E2: main.data 无 Goal/Commitment 字段 ===")
for k in data.keys():
    assert "goal" not in k.lower(), f"main.data 含 goal 键: {k}"
    assert "commitment" not in k.lower(), f"main.data 含 commitment 键: {k}"
print("E2 PASS")


# =========================================================
# E3: 无持久化（静态）
# =========================================================
print("\n=== E3: 无持久化 ===")
for fn in ("goal.py", "commitment.py", "motivation.py", "intent.py", "runtime.py"):
    src = (AGENT_DIR / fn).read_text(encoding="utf-8")
    assert not re.search(r'open\s*\([^)]*["\']w["\']', src), f"{fn} 含写文件"
    assert not re.search(r'\.write\s*\(', src), f"{fn} 含 write"
    assert not re.search(r'json\.dump\s*\(', src), f"{fn} 含 json.dump"
    assert "sqlite" not in src.lower(), f"{fn} 含 sqlite"
    assert "sqlalchemy" not in src.lower(), f"{fn} 含 sqlalchemy"
    assert "aiofiles" not in src.lower(), f"{fn} 含 aiofiles"
print("E3 PASS")


# =========================================================
# E4: 无 persistence mechanism
# =========================================================
print("\n=== E4: 无 persistence mechanism ===")
runtime_src = (AGENT_DIR / "runtime.py").read_text(encoding="utf-8")
for pat in [r'\bsave_\w+', r'\bload_\w+', r'\bpersist\b',
            r'\brestore\b', r'\bcheckpoint\b']:
    assert not re.search(pat, runtime_src, re.IGNORECASE), f"runtime.py 含 {pat}"
print("E4 PASS")


# =========================================================
# E5: 无 LLM / 网络
# =========================================================
print("\n=== E5: 无 LLM / 网络 ===")
for fn in ("goal.py", "commitment.py", "motivation.py", "intent.py", "runtime.py"):
    src = (AGENT_DIR / fn).read_text(encoding="utf-8")
    assert not re.search(r'\bcall_llm\s*\(', src), f"{fn} 含 call_llm"
    assert not re.search(r'\bdrive_ai\s*\(', src), f"{fn} 含 drive_ai"
    assert not re.search(r'\bbuild_ai_context\s*\(', src), f"{fn} 含 build_ai_context"
    for pat in [r'urllib\.request', r'requests\.(post|get|put|delete)',
                r'httpx\.', r'aiohttp\.', r'openai\.', r'anthropic\.']:
        assert not re.search(pat, src), f"{fn} 含网络调用 {pat}"
print("E5 PASS")


# =========================================================
# E6: 无 ext_* 调用
# =========================================================
print("\n=== E6: 无 ext_* ===")
for fn in ("goal.py", "commitment.py", "motivation.py", "intent.py", "runtime.py"):
    src = (AGENT_DIR / fn).read_text(encoding="utf-8")
    tops = {m.split('.')[0] for m in import_pattern.findall(src)}
    bad_ext = {m for m in tops if m.startswith("ext_")}
    assert not bad_ext, f"{fn} 导入 ext_*: {bad_ext}"
print("E6 PASS")


# =========================================================
# E7: 不触发 World Change
# =========================================================
print("\n=== E7: 不触发 World Change ===")
data = sample_data()
rt = AgentRuntime("Dan", data)
rt.add_goal(create_goal(
    actor="Dan", type="x", description="d",
    source="user_request", reason="r",
    target="t", completion_condition="c", now_ts=NOW,
))
assert data["ai_location"] == {"Dan": "Cafe"}
assert data["wallets"] == {"Dan": 100.0}
assert data["dates"] == []
print("E7 PASS")


# =========================================================
# E8: _goals / _commitments 是 Runtime 私有状态
# =========================================================
print("\n=== E8: _goals / _commitments 私有 ===")
assert "global " not in runtime_src
assert "self._goals" in runtime_src
assert "self._commitments" in runtime_src
print("E8 PASS")


# =========================================================
# E9: 无绕过路径（重点）
# =========================================================
print("\n=== E9: 无绕过路径 ===")
data = sample_data()
rt = AgentRuntime("Dan", data)
g = create_goal(
    actor="Dan", type="x", description="d",
    source="user_request", reason="r",
    target="t", completion_condition="c", now_ts=NOW,
)
rt.add_goal(g)

# 1) list_goals 返回副本：修改返回的 list 不影响内部
returned_list = rt.list_goals()
assert isinstance(returned_list, list)
returned_list.append("INTRUDER")
assert len(rt.list_goals()) == 1, "list_goals 返回了内部引用"

# 2) get_goal 返回 deepcopy：改字段不穿透 holder
returned_goal = rt.get_goal(g.goal_id)
returned_goal.description = "MUTATED_BY_EXTERNAL"
returned_goal.status = "COMPLETED"
internal = rt.get_goal(g.goal_id)
assert internal.description == "d", f"holder description 被穿透: {internal.description}"
assert internal.status == "CREATED", f"holder status 被穿透: {internal.status}"

# 3) list_goals 内的对象也是副本：改字段不穿透
lst = rt.list_goals()
lst[0].description = "MUTATED_VIA_LIST"
internal = rt.get_goal(g.goal_id)
assert internal.description == "d", f"holder 被 list 穿透: {internal.description}"

# 4) add_goal 存储副本：改传入对象不影响 holder
g2 = create_goal(
    actor="Dan", type="y", description="d2",
    source="user_request", reason="r2",
    target="t2", completion_condition="c2", now_ts=NOW,
)
rt.add_goal(g2)
g2.description = "MUTATED_AFTER_ADD"
internal_g2 = rt.get_goal(g2.goal_id)
assert internal_g2.description == "d2", f"add 未存副本: {internal_g2.description}"

# 5) 没有直接返回内部 dict 的公共 API
for name in dir(rt):
    if name.startswith("_"):
        continue
    val = getattr(rt, name)
    if callable(val):
        continue
    # 公共非方法属性不应是 dict（除 ai_name 是 str）
    assert not isinstance(val, dict), f"公共属性 {name} 是 dict"

print("E9 PASS: 无绕过路径，holder 完全隔离")


# =========================================================
# E10: Holder API 白名单
# =========================================================
print("\n=== E10: Holder API 白名单 ===")
expected = {
    "add_goal", "get_goal", "list_goals", "replace_goal",
    "add_commitment", "get_commitment", "list_commitments", "replace_commitment",
}
for m in expected:
    assert hasattr(rt, m), f"缺少 holder API: {m}"
    assert callable(getattr(rt, m)), f"{m} 不可调用"
for suspicious in ("auto_transition", "resolve_conflict", "compute_priority",
                   "auto_expire", "negotiate", "save", "load", "persist"):
    assert not hasattr(rt, suspicious), f"不应有 {suspicious}"
print("E10 PASS")


# =========================================================
# E11: 无 auto / scheduler / priority / conflict
# =========================================================
print("\n=== E11: 无 auto/scheduler/priority/conflict ===")
# 精确检查：禁止真正的函数/类/字段定义，允许 docstring 中的描述性单词
for fn in ("goal.py", "commitment.py", "runtime.py"):
    src = (AGENT_DIR / fn).read_text(encoding="utf-8")
    forbidden_patterns = [
        r'\bdef\s+auto_transition\b',      # 定义 auto transition 函数
        r'\bdef\s+resolve_conflict\b',     # 定义冲突解决函数
        r'\bdef\s+compute_priority\b',     # 定义优先级计算函数
        r'\bclass\s+Scheduler\b',          # 定义 Scheduler 类
        r'\bclass\s+ConflictResolver\b',   # 定义 ConflictResolver 类
        r'\bclass\s+PriorityEngine\b',     # 定义 PriorityEngine 类
        r'\.schedule\s*\(',                # 调用 schedule()
        r'\.resolve_conflict\s*\(',        # 调用 resolve_conflict()
        r'\bfrom\s+apscheduler\b',         # 导入 APScheduler
        r'\bimport\s+apscheduler\b',       # 导入 APScheduler
        r'\bfrom\s+sched\b',               # 导入标准库 sched
        r'\bimport\s+sched\b',             # 导入标准库 sched
    ]
    for pat in forbidden_patterns:
        assert not re.search(pat, src), f"{fn} 含 {pat}"
print("E11 PASS: 无 auto_transition / Scheduler / priority / conflict 定义或调用")


# =========================================================
# 全部通过
# =========================================================
print("\n=== 全部通过（E1-E11）===")
print(f"\n[定位] 仓库根 = {REPO_ROOT}")