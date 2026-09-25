"""
test_b3_context_assembler.py - Phase B3 测试

从 TEST 仓库根目录运行：
    python docs/test_b3_context_assembler.py

自动定位仓库根，不依赖 cwd。
覆盖 T1-T30。
"""

import sys
import copy
import json
import re
from pathlib import Path

# =========================================================
# 路径定位
# =========================================================
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# =========================================================
# 导入
# =========================================================
from agent.context import (
    AgentContext,
    ContextSection,
    ContextBudget,
    LAYER_STABLE_CORE,
    LAYER_RECENT,
    LAYER_LONG_TERM,
    LAYER_DYNAMIC_WORLD,
)
from agent.context_assembler import ContextAssembler
from agent.stable_core_provider import StableCoreProvider
from agent.recent_provider import RecentProvider
from agent.long_term_provider import LongTermProvider
from agent.dynamic_world_provider import DynamicWorldProvider

# =========================================================
# 测试数据
# =========================================================
NOW = 1700000000.0

SAMPLE_DATA = {
    "world_lore": "这是一个共享世界。",
    "ai_profiles": {
        "Alice": {"ai": "Dan", "persona": "Dan 是一个温和的 AI。"},
    },
    "user_profiles": {
        "Alice": "Alice 是主人。",
    },
    "ai_location": {"Dan": "咖啡馆"},
    "ai_timeline": {
        "Dan": [
            {"time": "2026-09-21 10:00:00", "text": "在咖啡馆喝了杯手冲"},
            {"time": "2026-09-21 12:00:00", "text": "和 Alice 聊了会儿"},
        ],
    },
    "trails": {
        "Dan": [
            {"ts": NOW - 3600, "time": "2026-09-21 13:00:00", "text": "买了杯咖啡", "room": "咖啡馆"},
        ],
    },
    "ai_visited": {"Dan": ["图书馆", "咖啡馆"]},
    # 禁止泄漏字段
    "messages": {"main": [{"sender": "x", "content": "should not leak"}]},
    "sms": {"Alice": [{"from": "Dan", "text": "should not leak sms"}]},
    "ai_memories": {"Alice": [{"ai": "Dan", "text": "should not leak memory"}]},
    "ai_keys": {"Alice": {"key": "sk-xxx"}},
    "dev_users": ["admin"],
}

SAMPLE_AGENT_STATE = {
    "name": "Dan",
    "current_activity": "dating",
    "is_working": False,
    "is_dating": True,
    "is_following": False,
    "mood": 70,
    "energy": 70,
    "social_need": 30,
    "stress": 20,
}

# =========================================================
# Mock Provider（用于 T22：不修改 Provider 原始输出）
# =========================================================
class MockProvider:
    def __init__(self, name, layer, items):
        self.name = name
        self.layer = layer
        self._items = items
        self.fetch_called = False

    def fetch(self, *args, **kwargs):
        self.fetch_called = True
        # 返回原始 list 的浅拷贝，但内部 dict 仍为原始引用
        return list(self._items)

    def describe(self):
        return {"name": self.name, "layer": self.layer}


# =========================================================
# 构建 Assembler
# =========================================================
def make_assembler():
    return ContextAssembler(
        stable_core_provider=StableCoreProvider(),
        recent_provider=RecentProvider(),
        long_term_provider=LongTermProvider(),
        dynamic_world_provider=DynamicWorldProvider(),
        budget=ContextBudget(),
    )


# =========================================================
# T1: Provider injection
# =========================================================
print("=== T1: Provider injection ===")
asm = make_assembler()
assert asm.stable_core_provider.name == "stable_core"
assert asm.recent_provider.name == "recent"
assert asm.long_term_provider.name == "long_term"
assert asm.dynamic_world_provider.name == "dynamic_world"
print("T1 PASS")


# =========================================================
# T2: Stable Core assembly
# =========================================================
print("\n=== T2: Stable Core assembly ===")
ctx = asm.assemble("Dan", "Alice", SAMPLE_DATA, now_ts=NOW, agent_state_dict=SAMPLE_AGENT_STATE)
types = [it["type"] for it in ctx.stable_core.items]
assert "identity" in types
assert "world_lore" in types
assert "persona" in types
assert "user_profile" in types
print(f"T2 PASS: stable_core types={types}")


# =========================================================
# T3: Recent assembly
# =========================================================
print("\n=== T3: Recent assembly ===")
types = [it["type"] for it in ctx.recent.items]
assert "recent_timeline" in types
assert "recent_trail" in types
assert "recent_visited_place" in types
print(f"T3 PASS: recent types={types}")


# =========================================================
# T4: Long-term [] 正常
# =========================================================
print("\n=== T4: Long-term [] 正常 ===")
assert ctx.long_term.items == []
assert ctx.long_term.truncated is False
print("T4 PASS")


# =========================================================
# T5: Dynamic World assembly
# =========================================================
print("\n=== T5: Dynamic World assembly ===")
types = [it["type"] for it in ctx.dynamic_world.items]
assert "current_time" in types
assert "current_location" in types
assert "current_activity" in types
print(f"T5 PASS: dynamic_world types={types}")


# =========================================================
# T6: 返回 AgentContext
# =========================================================
print("\n=== T6: 返回 AgentContext ===")
assert isinstance(ctx, AgentContext)
print("T6 PASS")


# =========================================================
# T7: ai_name
# =========================================================
print("\n=== T7: ai_name ===")
assert ctx.ai_name == "Dan"
print("T7 PASS")


# =========================================================
# T8: 四层结构
# =========================================================
print("\n=== T8: 四层结构 ===")
sections = ctx.sections()
assert len(sections) == 4
assert sections[0].layer == LAYER_STABLE_CORE
assert sections[1].layer == LAYER_RECENT
assert sections[2].layer == LAYER_LONG_TERM
assert sections[3].layer == LAYER_DYNAMIC_WORLD
print("T8 PASS")


# =========================================================
# T9: Stable budget
# =========================================================
print("\n=== T9: Stable budget ===")
budget = ContextBudget()
assert ctx.stable_core.token_estimate() <= budget.stable_core_max
print(f"T9 PASS: {ctx.stable_core.token_estimate()} <= {budget.stable_core_max}")


# =========================================================
# T10: Recent budget
# =========================================================
print("\n=== T10: Recent budget ===")
assert ctx.recent.token_estimate() <= budget.recent_max
print(f"T10 PASS: {ctx.recent.token_estimate()} <= {budget.recent_max}")


# =========================================================
# T11: Long-term budget
# =========================================================
print("\n=== T11: Long-term budget ===")
assert ctx.long_term.token_estimate() <= budget.long_term_max
print(f"T11 PASS: {ctx.long_term.token_estimate()} <= {budget.long_term_max}")


# =========================================================
# T12: Dynamic World budget
# =========================================================
print("\n=== T12: Dynamic World budget ===")
assert ctx.dynamic_world.token_estimate() <= budget.dynamic_world_max
print(f"T12 PASS: {ctx.dynamic_world.token_estimate()} <= {budget.dynamic_world_max}")


# =========================================================
# T13: Total budget
# =========================================================
print("\n=== T13: Total budget ===")
assert ctx.total_token_estimate() <= budget.total_max
print(f"T13 PASS: {ctx.total_token_estimate()} <= {budget.total_max}")


# =========================================================
# T14: Provider 输出过多 bounded
# =========================================================
print("\n=== T14: Provider 输出过多 bounded ===")
big_data = dict(SAMPLE_DATA)
big_data["ai_timeline"] = {
    "Dan": [{"time": "2026-09-21 12:00:00", "text": "X" * 500} for _ in range(100)]
}
big_data["trails"] = {
    "Dan": [{"ts": NOW - 1, "time": "2026-09-21 12:00:00", "text": "Y" * 500, "room": "z" * 100} for _ in range(100)]
}
big_data["ai_visited"] = {"Dan": ["P" * 200 for _ in range(100)]}
ctx_big = asm.assemble("Dan", "Alice", big_data, now_ts=NOW, agent_state_dict=SAMPLE_AGENT_STATE)
assert ctx_big.recent.token_estimate() <= budget.recent_max
print(f"T14 PASS: recent tokens={ctx_big.recent.token_estimate()}")


# =========================================================
# T15: 历史增长不导致 Context 线性增长
# =========================================================
print("\n=== T15: 历史增长不导致 Context 线性增长 ===")
huge_data = dict(SAMPLE_DATA)
huge_data["ai_timeline"] = {
    "Dan": [{"time": "2026-09-21 12:00:00", "text": f"e{i}"} for i in range(1000)]
}
huge_data["trails"] = {
    "Dan": [{"ts": NOW - 1, "time": "2026-09-21 12:00:00", "text": f"t{i}", "room": "r"} for i in range(1000)]
}
huge_data["ai_visited"] = {"Dan": [f"p{i}" for i in range(1000)]}
ctx_huge = asm.assemble("Dan", "Alice", huge_data, now_ts=NOW, agent_state_dict=SAMPLE_AGENT_STATE)
assert len(ctx_huge.recent.items) <= 13, f"Recent 条数未受限: {len(ctx_huge.recent.items)}"
print(f"T15 PASS: 输入 3000 条, 输出 {len(ctx_huge.recent.items)} 条")


# =========================================================
# T16: deterministic order
# =========================================================
print("\n=== T16: deterministic order ===")
ctx1 = asm.assemble("Dan", "Alice", SAMPLE_DATA, now_ts=NOW, agent_state_dict=SAMPLE_AGENT_STATE)
ctx2 = asm.assemble("Dan", "Alice", SAMPLE_DATA, now_ts=NOW, agent_state_dict=SAMPLE_AGENT_STATE)
types1 = [it["type"] for it in ctx1.stable_core.items]
types2 = [it["type"] for it in ctx2.stable_core.items]
assert types1 == types2
print("T16 PASS")


# =========================================================
# T17: 不生成不存在的数据
# =========================================================
print("\n=== T17: 不生成不存在的数据 ===")
empty_data = {"ai_location": {"Dan": "cafe"}}
ctx_empty = asm.assemble("Dan", "Alice", empty_data, now_ts=NOW)
assert ctx_empty.long_term.items == []
assert all(it["type"] != "recent_trail" for it in ctx_empty.recent.items)
print("T17 PASS")


# =========================================================
# T18: 不 import main / ext_*
# =========================================================
print("\n=== T18: 不 import main / ext_* ===")
asm_src_path = REPO_ROOT / "agent" / "context_assembler.py"
src = asm_src_path.read_text(encoding="utf-8")
import_pattern = re.compile(r'^\s*(?:import|from)\s+([\w\.]+)', re.MULTILINE)
imported = import_pattern.findall(src)
top_modules = set(m.split('.')[0] for m in imported)
forbidden = {"main"} | {m for m in top_modules if m.startswith("ext_")}
bad = top_modules & forbidden
assert not bad, f"含禁止导入: {bad}"
print(f"T18 PASS: imports={sorted(top_modules)}")


# =========================================================
# T19: 不调用 LLM / network
# =========================================================
print("\n=== T19: 不调用 LLM / network ===")
llm_libs = {"openai", "anthropic", "httpx", "aiohttp", "requests", "urllib"}
bad_libs = top_modules & llm_libs
assert not bad_libs, f"含 LLM 库导入: {bad_libs}"
network_patterns = [
    r'urllib\.request\.',
    r'requests\.(post|get|put|delete|request)\s*\(',
    r'httpx\.',
    r'aiohttp\.',
    r'openai\.',
    r'anthropic\.',
]
for pat in network_patterns:
    assert not re.search(pat, src), f"含网络调用: {pat}"
assert not re.search(r'\bcall_llm\s*\(', src), "含 call_llm 调用"
print("T19 PASS")


# =========================================================
# T20: 不修改 data
# =========================================================
print("\n=== T20: 不修改 data ===")
data_before = copy.deepcopy(SAMPLE_DATA)
asm.assemble("Dan", "Alice", SAMPLE_DATA, now_ts=NOW, agent_state_dict=SAMPLE_AGENT_STATE)
assert SAMPLE_DATA == data_before, "data 被修改"
print("T20 PASS")


# =========================================================
# T21: 不修改 AgentState
# =========================================================
print("\n=== T21: 不修改 AgentState ===")
state_before = copy.deepcopy(SAMPLE_AGENT_STATE)
asm.assemble("Dan", "Alice", SAMPLE_DATA, now_ts=NOW, agent_state_dict=SAMPLE_AGENT_STATE)
assert SAMPLE_AGENT_STATE == state_before, "AgentState 被修改"
print("T21 PASS")


# =========================================================
# T22: 不修改 Provider 原始输出
# =========================================================
print("\n=== T22: 不修改 Provider 原始输出 ===")
mock_items = [
    {"type": "mock", "content": "原始内容", "source": "mock"},
]
mock_provider = MockProvider("mock", "recent", mock_items)
asm_mock = ContextAssembler(
    stable_core_provider=StableCoreProvider(),
    recent_provider=mock_provider,
    long_term_provider=LongTermProvider(),
    dynamic_world_provider=DynamicWorldProvider(),
)
ctx_mock = asm_mock.assemble("Dan", "Alice", SAMPLE_DATA, now_ts=NOW)
# 检查 mock 原始 list 未被修改
assert mock_items[0]["content"] == "原始内容"
assert len(mock_items) == 1
# 检查 Context 中的 item 是副本
ctx_item = ctx_mock.recent.items[0]
assert ctx_item is not mock_items[0]
assert ctx_item == mock_items[0]
print("T22 PASS")


# =========================================================
# T23: 不生成 Prompt
# =========================================================
print("\n=== T23: 不生成 Prompt ===")
assert isinstance(ctx, AgentContext)
assert not isinstance(ctx, str)
assert not hasattr(ctx, "prompt")
print("T23 PASS")


# =========================================================
# T24: 不接 Runtime
# =========================================================
print("\n=== T24: 不接 Runtime ===")
assert "runtime" not in src.lower() or "build_context" not in src
assert not re.search(r'\bbuild_context\s*\(', src)
print("T24 PASS")


# =========================================================
# T25: Long-term [] 正常
# =========================================================
print("\n=== T25: Long-term [] 正常 ===")
ctx_lt = asm.assemble("Dan", "Alice", SAMPLE_DATA, now_ts=NOW, recall_query="test")
assert ctx_lt.long_term.items == []
print("T25 PASS")


# =========================================================
# T26: Decision-Relevant Constraints 只预留
# =========================================================
print("\n=== T26: Decision-Relevant Constraints 只预留 ===")
assert ctx.decision_constraints is None
print("T26 PASS")


# =========================================================
# T27: debug_dict 不泄露完整 Context
# =========================================================
print("\n=== T27: debug_dict 不泄露完整 Context ===")
dbg = ctx.to_debug_dict()
dbg_str = json.dumps(dbg, ensure_ascii=False)
assert "在咖啡馆喝了杯手冲" not in dbg_str
assert "items" not in dbg_str or "item_count" in dbg_str
print("T27 PASS")


# =========================================================
# T28: debug audit 信息正确
# =========================================================
print("\n=== T28: debug audit 信息正确 ===")
desc = asm.describe()
assert desc["name"] == "context_assembler"
assert "last_audit" in desc
audit = desc["last_audit"]
assert "layers" in audit
assert LAYER_STABLE_CORE in audit["layers"]
assert LAYER_RECENT in audit["layers"]
assert LAYER_LONG_TERM in audit["layers"]
assert LAYER_DYNAMIC_WORLD in audit["layers"]
for layer_name, layer_audit in audit["layers"].items():
    assert "provider_item_count" in layer_audit
    assert "added_count" in layer_audit
    assert "truncated" in layer_audit
print("T28 PASS")


# =========================================================
# T29: 大量历史仍 bounded
# =========================================================
print("\n=== T29: 大量历史仍 bounded ===")
huge_data2 = dict(SAMPLE_DATA)
huge_data2["ai_timeline"] = {
    "Dan": [{"time": "2026-09-21 12:00:00", "text": "X" * 1000} for _ in range(10000)]
}
ctx_huge2 = asm.assemble("Dan", "Alice", huge_data2, now_ts=NOW)
assert ctx_huge2.recent.token_estimate() <= budget.recent_max
assert ctx_huge2.total_token_estimate() <= budget.total_max
print(f"T29 PASS: total tokens={ctx_huge2.total_token_estimate()}")


# =========================================================
# T30: describe / audit 正确
# =========================================================
print("\n=== T30: describe / audit 正确 ===")
desc = asm.describe()
assert desc["providers"]["stable_core"] == "stable_core"
assert desc["providers"]["recent"] == "recent"
assert desc["providers"]["long_term"] == "long_term"
assert desc["providers"]["dynamic_world"] == "dynamic_world"
assert desc["budget"]["total_max"] == 8500
print("T30 PASS")


# =========================================================
# 附加：单个超大 item 不得清空已成功加入的 items
# =========================================================
print("\n=== 附加: 单个超大 item 不得清空已成功加入的 items ===")
# 构造一个 provider，先返回一个小 item，再返回一个超大 item
large_items = [
    {"type": "small", "content": "ok", "source": "test"},
    {"type": "huge", "content": "X" * 10000, "source": "test"},
]
mock_provider2 = MockProvider("mock2", "recent", large_items)
asm2 = ContextAssembler(
    stable_core_provider=StableCoreProvider(),
    recent_provider=mock_provider2,
    long_term_provider=LongTermProvider(),
    dynamic_world_provider=DynamicWorldProvider(),
    budget=ContextBudget(recent_max=100),  # 小预算
)
ctx2 = asm2.assemble("Dan", "Alice", SAMPLE_DATA, now_ts=NOW)
# 小 item 应该被保留
assert len(ctx2.recent.items) == 1
assert ctx2.recent.items[0]["type"] == "small"
assert ctx2.recent.truncated is True
print("附加 PASS: 已加入的 small item 保留，huge 被拒绝，truncated=True")


# =========================================================
# 全部通过
# =========================================================
print("\n=== 全部通过（T1-T30 + 附加）===")
print(f"\n[定位] 仓库根 = {REPO_ROOT}")
print(f"[定位] Assembler = {asm_src_path}")