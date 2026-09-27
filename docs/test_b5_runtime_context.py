"""
test_b5_runtime_context.py - Phase B5-3 测试

从 TEST 仓库根目录运行：
    python docs/test_b5_runtime_context.py

自动定位仓库根，不依赖 cwd。
覆盖 T1-T12。

目的：
    验证 B5-2 Runtime Context Connection 可靠。
    不是证明"AI 已经会思考"。

边界：
    - 不修改 agent/runtime.py / agent/context.py / agent/context_assembler.py
    - 不修改任何 Provider
    - 不触碰 main.py / ext_* / Memory / 前端
    - 不调用 LLM / 网络
"""

import sys
import copy
import re
from pathlib import Path

# =========================================================
# 路径定位（相对于仓库根，与 cwd 无关）
# =========================================================
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# =========================================================
# 在导入 agent.state 之前模拟 main 模块
#
# 原因：
#   agent/state.py 顶层 `from main import ...`
#   若直接导入真实 main.py，会触发 Flask / 后台线程 / 数据库等副作用。
#   本测试只验证 Runtime↔ContextAssembler 连接，不验证 main。
#
# 隔离原则（T12）：
#   本测试不触碰 main.py 的真实业务逻辑。
# =========================================================
import types
if "main" not in sys.modules:
    fake_main = types.ModuleType("main")
    # 名字规范化：原样返回
    fake_main.canonical_ai_name = lambda name: name
    # 反向查找：交给 agent/state.py 内部 data 回退逻辑
    fake_main.owner_of_ai = lambda name: None
    # emoji 清理：原样返回
    fake_main.strip_emoji = lambda s: s
    sys.modules["main"] = fake_main

# =========================================================
# 导入
# =========================================================
from agent.runtime import AgentRuntime, ContextLayers
from agent.context import AgentContext, make_empty_context


# =========================================================
# 示例数据
# =========================================================
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
        "world_lore": "测试世界观",
        "ai_profiles": {
            "Alice": {"ai": "Dan", "persona": "测试人设"},
        },
        "user_profiles": {
            "Alice": "测试用户画像",
        },
    }


# =========================================================
# FakeAssembler（用于 T2/T3/T4）
# =========================================================
class FakeAssembler:
    """捕获 assemble() 调用，验证 Runtime 确实把责任交给 Assembler。"""

    def __init__(self):
        self.called = False
        self.captured = {}

    def assemble(
        self,
        ai_name,
        owner,
        data,
        now_ts=None,
        agent_state_dict=None,
        recall_query=None,
    ):
        self.called = True
        self.captured = {
            "ai_name": ai_name,
            "owner": owner,
            "data": data,
            "now_ts": now_ts,
            "agent_state_dict": agent_state_dict,
            "recall_query": recall_query,
        }
        return make_empty_context(ai_name)


# =========================================================
# T1: build_context 返回 AgentContext
# =========================================================
print("=== T1: build_context 返回 AgentContext ===")
data = sample_data()
rt1 = AgentRuntime("Dan", data)
ctx1 = rt1.build_context(None, now_ts=1234567890.0)
assert isinstance(ctx1, AgentContext), f"期望 AgentContext，实际 {type(ctx1)}"
print(f"T1 PASS: type={type(ctx1).__name__}")


# =========================================================
# T2: Assembler 确实被调用（用 mock 验证）
# =========================================================
print("\n=== T2: Assembler 确实被调用 ===")
fa2 = FakeAssembler()
rt2 = AgentRuntime("Dan", sample_data(), context_assembler=fa2)
rt2.build_context(None, now_ts=1234567890.0)
assert fa2.called, "Assembler.assemble 未被调用"
# 验证 Runtime 没有绕过 Assembler 去直接调用 Provider
# （若绕过，FakeAssembler 不会被调用，上面的 assert 会失败）
print("T2 PASS: FakeAssembler.assemble 被调用")


# =========================================================
# T3: owner 来源 = get_state().owner
# =========================================================
print("\n=== T3: owner 来源 = get_state().owner ===")
fa3 = FakeAssembler()
data3 = sample_data()
rt3 = AgentRuntime("Dan", data3, context_assembler=fa3)
state3 = rt3.get_state()
assert state3 is not None, "get_state() 返回 None"
expected_owner = state3.owner
rt3.build_context(None)
assert fa3.captured["owner"] == expected_owner, (
    f"owner 不匹配：期望 {expected_owner!r}，实际 {fa3.captured['owner']!r}"
)
print(f"T3 PASS: owner={expected_owner!r}")


# =========================================================
# T4: agent_state_dict 来源 = get_state().to_dict()
# =========================================================
print("\n=== T4: agent_state_dict 来源 = get_state().to_dict() ===")
fa4 = FakeAssembler()
rt4 = AgentRuntime("Dan", sample_data(), context_assembler=fa4)
state4 = rt4.get_state()
assert state4 is not None
expected_asd = state4.to_dict()
rt4.build_context(None)
captured_asd = fa4.captured["agent_state_dict"]
assert captured_asd == expected_asd, (
    f"agent_state_dict 不匹配：\n期望 {expected_asd}\n实际 {captured_asd}"
)
assert captured_asd is not None
assert captured_asd.get("name") == "Dan"
assert captured_asd.get("owner") == "Alice"
assert "_sources" in captured_asd, "缺少 P0-1 元数据 _sources"
print(f"T4 PASS: agent_state_dict.name={captured_asd.get('name')}, owner={captured_asd.get('owner')}")


# =========================================================
# T5: now_ts 注入 → DynamicWorldProvider 使用该时间
# =========================================================
print("\n=== T5: now_ts 注入 → 固定时间生效 ===")
# 1234567890.0 UTC = 2009-02-13 23:31:30 UTC
# +8h 北京时间   = 2009-02-14 07:31:30
EXPECTED_BJ_TIME = "2009-02-14 07:31:30"

rt5 = AgentRuntime("Dan", sample_data())
ctx5 = rt5.build_context(None, now_ts=1234567890.0)
time_items = [it for it in ctx5.dynamic_world.items if it["type"] == "current_time"]
assert len(time_items) == 1, f"期望 1 个 current_time，实际 {len(time_items)}"
actual_time = time_items[0]["content"]
assert actual_time == EXPECTED_BJ_TIME, (
    f"now_ts 注入未生效：期望 {EXPECTED_BJ_TIME}，实际 {actual_time}"
)
print(f"T5 PASS: now_ts=1234567890.0 → current_time={actual_time}")


# =========================================================
# T6: 默认 now_ts = 不使用固定值
# =========================================================
print("\n=== T6: 默认 now_ts = 当前时间 ===")
rt6 = AgentRuntime("Dan", sample_data())
ctx6 = rt6.build_context(None)  # 不传 now_ts
time_items6 = [it for it in ctx6.dynamic_world.items if it["type"] == "current_time"]
assert len(time_items6) == 1
actual_default = time_items6[0]["content"]
assert actual_default != EXPECTED_BJ_TIME, (
    "未传 now_ts 时不应该使用 1234567890 的固定时间"
)
print(f"T6 PASS: 默认时间 = {actual_default}（非固定值）")


# =========================================================
# T7: LongTerm 仍为空
# =========================================================
print("\n=== T7: LongTerm 仍为空 ===")
rt7 = AgentRuntime("Dan", sample_data())
ctx7 = rt7.build_context(None)
assert ctx7.long_term.items == [], (
    f"Long-term 应仍为空，实际 {len(ctx7.long_term.items)} items"
)
assert ctx7.long_term.truncated is False
print("T7 PASS: long_term.items == []")


# =========================================================
# T8: decision_constraints 仍为 None
# =========================================================
print("\n=== T8: decision_constraints 仍为 None ===")
rt8 = AgentRuntime("Dan", sample_data())
ctx8 = rt8.build_context(None)
assert ctx8.decision_constraints is None, (
    f"decision_constraints 应为 None，实际 {ctx8.decision_constraints}"
)
print("T8 PASS")


# =========================================================
# T9: THINK 仍为 Stub + 无 LLM 调用
# =========================================================
print("\n=== T9: THINK 仍为 Stub ===")
rt9 = AgentRuntime("Dan", sample_data())
ctx9 = rt9.build_context(None)
result9 = rt9.think(ctx9)
assert result9 is None, f"think() 应返回 None，实际 {result9!r}"

# 静态验证 runtime.py 不含 LLM / drive_ai / build_ai_context 调用
runtime_src = (REPO_ROOT / "agent" / "runtime.py").read_text(encoding="utf-8")
assert not re.search(r'\bcall_llm\s*\(', runtime_src), "runtime.py 含 call_llm 调用"
assert not re.search(r'\bdrive_ai\s*\(', runtime_src), "runtime.py 含 drive_ai 调用"
assert not re.search(r'\bbuild_ai_context\s*\(', runtime_src), "runtime.py 含 build_ai_context 调用"
print("T9 PASS: think() 返回 None；runtime.py 无 LLM / drive_ai / build_ai_context 调用")


# =========================================================
# T10: 旧 ContextLayers 保留，但未接回正式链
# =========================================================
print("\n=== T10: ContextLayers 保留为 deprecated stub ===")
# 存在
assert ContextLayers is not None
# 可以被实例化
cl = ContextLayers()
assert hasattr(cl, "stable_core")
assert hasattr(cl, "recent")
assert hasattr(cl, "long_term")
assert hasattr(cl, "dynamic_world")
# build_context 返回 AgentContext，而不是 ContextLayers
rt10 = AgentRuntime("Dan", sample_data())
ctx10 = rt10.build_context(None)
assert isinstance(ctx10, AgentContext)
assert not isinstance(ctx10, ContextLayers), "build_context 不应返回 ContextLayers"
# 未被别名化
assert ContextLayers is not AgentContext, "ContextLayers 不应被别名化为 AgentContext"
print("T10 PASS: ContextLayers 保留、未别名化；build_context 返回 AgentContext")


# =========================================================
# T11: 数据只读
# =========================================================
print("\n=== T11: build_context 不修改 data ===")
data11 = sample_data()
data_before = copy.deepcopy(data11)
rt11 = AgentRuntime("Dan", data11)
rt11.build_context(None, now_ts=1234567890.0)
assert data11 == data_before, "build_context 修改了 data"
print("T11 PASS: data 未被修改")


# =========================================================
# T12: 隔离性检查（不触碰 main / ext_* / Memory / 前端）
# =========================================================
print("\n=== T12: 隔离性检查 ===")
runtime_src = (REPO_ROOT / "agent" / "runtime.py").read_text(encoding="utf-8")

# 12.1 静态导入检查
import_pattern = re.compile(r'^\s*(?:import|from)\s+([\w\.]+)', re.MULTILINE)
imported = import_pattern.findall(runtime_src)
top_modules = set(m.split('.')[0] for m in imported)

# 不直接导入 main
assert "main" not in top_modules, f"runtime.py 直接导入 main: {top_modules}"

# 不导入 ext_*
forbidden_ext = {m for m in top_modules if m.startswith("ext_")}
assert not forbidden_ext, f"runtime.py 导入 ext_*: {forbidden_ext}"

# 12.2 不导入 LLM 库
llm_libs = {"openai", "anthropic", "httpx", "aiohttp", "requests", "urllib"}
bad_libs = top_modules & llm_libs
assert not bad_libs, f"runtime.py 含 LLM 库导入: {bad_libs}"

# 12.3 无网络调用
network_patterns = [
    r'urllib\.request\.',
    r'requests\.(post|get|put|delete|request)\s*\(',
    r'httpx\.',
    r'aiohttp\.',
    r'openai\.',
    r'anthropic\.',
]
for pat in network_patterns:
    assert not re.search(pat, runtime_src), f"runtime.py 含网络调用: {pat}"

# 12.4 不导入 Memory
assert "ext_memory" not in runtime_src, "runtime.py 含 ext_memory"
assert "ext_mem" not in runtime_src.replace("ext_memory", ""), "runtime.py 含 ext_mem"

# 12.5 不修改前端（源文件层面）
#     本项目 .py 文件不应引用 .html / .js
assert ".html" not in runtime_src, "runtime.py 含 .html 引用"
assert ".js" not in runtime_src, "runtime.py 含 .js 引用"

print(f"T12 PASS: imports={sorted(top_modules)}")


# =========================================================
# 附加：ContextAssembler 边界确认
# =========================================================
print("\n=== 附加: ContextAssembler 未被本阶段修改 ===")
assembler_src = (REPO_ROOT / "agent" / "context_assembler.py").read_text(encoding="utf-8")
# 不导入 LLM / 网络
for pat in network_patterns:
    assert not re.search(pat, assembler_src), f"context_assembler.py 含网络调用: {pat}"
assert not re.search(r'\bcall_llm\s*\(', assembler_src), "context_assembler.py 含 call_llm"
# 不导入 main / ext_*
assembler_imports = import_pattern.findall(assembler_src)
assembler_top = set(m.split('.')[0] for m in assembler_imports)
assert "main" not in assembler_top, "context_assembler.py 直接导入 main"
forbidden_ext_a = {m for m in assembler_top if m.startswith("ext_")}
assert not forbidden_ext_a, f"context_assembler.py 导入 ext_*: {forbidden_ext_a}"
print("附加 PASS: ContextAssembler 边界完好")


# =========================================================
# 全部通过
# =========================================================
print("\n=== 全部通过（T1-T12 + 附加）===")
print(f"\n[定位] 仓库根 = {REPO_ROOT}")
print(f"[定位] Runtime = {REPO_ROOT / 'agent' / 'runtime.py'}")
print(f"[定位] Assembler = {REPO_ROOT / 'agent' / 'context_assembler.py'}")