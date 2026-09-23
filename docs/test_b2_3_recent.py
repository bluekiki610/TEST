"""
test_b2_3_recent.py - Phase B2-3 测试

从 TEST 仓库根目录运行：
    python docs/test_b2_3_recent.py

自动定位 agent/context.py / agent/recent_provider.py。
不依赖 cwd。
"""

import importlib.util
import copy
import json
import re
import sys
import time
from pathlib import Path

# =========================================================
# 路径定位（相对于仓库根，与 cwd 无关）
# =========================================================
REPO_ROOT = Path(__file__).resolve().parent.parent
CONTEXT_PATH = REPO_ROOT / "agent" / "context.py"
PROVIDER_PATH = REPO_ROOT / "agent" / "recent_provider.py"

if not CONTEXT_PATH.exists():
    print(f"[FATAL] 找不到 {CONTEXT_PATH}", file=sys.stderr)
    sys.exit(1)
if not PROVIDER_PATH.exists():
    print(f"[FATAL] 找不到 {PROVIDER_PATH}", file=sys.stderr)
    sys.exit(1)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


context_mod = _load_module("context", CONTEXT_PATH)
provider_mod = _load_module("recent_provider", PROVIDER_PATH)

RecentProvider = provider_mod.RecentProvider
ContextSection = context_mod.ContextSection
ContextBudget = context_mod.ContextBudget
LAYER_RECENT = context_mod.LAYER_RECENT


# =========================================================
# 测试数据
# =========================================================
NOW = 1700000000.0
SAMPLE_DATA = {
    "ai_timeline": {
        "Dan": [
            {"time": "2026-09-21 10:00:00", "text": "在咖啡馆喝了杯手冲"},
            {"time": "2026-09-21 12:00:00", "text": "和 Alice 聊了会儿"},
            {"time": "2026-09-21 14:00:00", "text": "去图书馆借了本书"},
        ],
    },
    "trails": {
        "Dan": [
            {"ts": NOW - 86400 * 2, "time": "2026-09-19 10:00:00", "text": "旧痕迹-应被过滤", "room": "咖啡馆"},
            {"ts": NOW - 3600, "time": "2026-09-21 13:00:00", "text": "买了杯咖啡", "room": "咖啡馆"},
            {"ts": NOW - 60, "time": "2026-09-21 13:59:00", "text": "看了一本书", "room": "图书馆"},
        ],
    },
    "ai_visited": {
        "Dan": ["图书馆", "咖啡馆", "公园", "超市", "家"],
    },
    # 以下字段禁止进入 Context
    "messages": {"main": [{"sender": "x", "content": "should not leak"}]},
    "sms": {"Alice": [{"from": "Dan", "text": "should not leak sms"}]},
    "ai_memories": {"Alice": [{"ai": "Dan", "text": "should not leak memory"}]},
    "ai_keys": {"Alice": {"key": "sk-xxx"}},
    "dev_users": ["admin"],
    "pairs_admin": "admin",
    "wallets": {"Dan": 1000},
}

SAMPLE_AGENT_STATE = {
    "current_activity": "dating",
    "is_working": False,
    "is_dating": True,
    "mood": 70,
    "energy": 70,
}


# =========================================================
print("=== T1: 空 data → 空 list ===")
p = RecentProvider()
assert p.fetch("Dan", "Alice", {}) == []
print("T1 PASS")


print("\n=== T2: 无效 ai_name → 空 list ===")
assert p.fetch("", "Alice", SAMPLE_DATA) == []
assert p.fetch(None, "Alice", SAMPLE_DATA) == []
assert p.fetch(123, "Alice", SAMPLE_DATA) == []
print("T2 PASS")


print("\n=== T3: 没有 Recent 数据 → 空 list ===")
assert p.fetch("Nobody", "Alice", SAMPLE_DATA) == []
print("T3 PASS")


print("\n=== T4: 正常 Recent 数据 ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, now_ts=NOW)
types = [it["type"] for it in items]
assert "recent_timeline" in types
assert "recent_trail" in types
assert "recent_visited_place" in types
print(f"T4 PASS: {len(items)} items, types={set(types)}")


print("\n=== T5: 时间窗口过滤（trails） ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, now_ts=NOW)
full_text = json.dumps(items, ensure_ascii=False)
assert "旧痕迹-应被过滤" not in full_text, "时间窗口未生效"
assert "买了杯咖啡" in full_text, "1 小时内的痕迹被误删"
print("T5 PASS")


print("\n=== T6: item 数量上限 ===")
big_data = {
    "ai_timeline": {"Dan": [{"time": f"2026-09-21 {i:02d}:00:00", "text": f"事件{i}"} for i in range(50)]},
    "trails": {"Dan": [{"ts": NOW - i, "time": "2026-09-21 12:00:00", "text": f"痕迹{i}", "room": "x"} for i in range(50)]},
    "ai_visited": {"Dan": [f"地点{i}" for i in range(50)]},
}
items = p.fetch("Dan", "Alice", big_data, now_ts=NOW)
timeline_count = sum(1 for it in items if it["type"] == "recent_timeline")
trail_count = sum(1 for it in items if it["type"] == "recent_trail")
visited_count = sum(1 for it in items if it["type"] == "recent_visited_place")
assert timeline_count <= 5, f"timeline 超上限: {timeline_count}"
assert trail_count <= 5, f"trail 超上限: {trail_count}"
assert visited_count <= 3, f"visited 超上限: {visited_count}"
print(f"T6 PASS: timeline={timeline_count}, trail={trail_count}, visited={visited_count}")


print("\n=== T7: 不返回完整聊天历史 ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, now_ts=NOW)
full_text = json.dumps(items, ensure_ascii=False)
assert "should not leak" not in full_text, "聊天内容泄漏"
for it in items:
    assert "messages" not in it["source"], f"source 含 messages: {it['source']}"
print("T7 PASS")


print("\n=== T8: 不返回完整 SMS ===")
full_text = json.dumps(items, ensure_ascii=False)
assert "should not leak sms" not in full_text, "SMS 内容泄漏"
for it in items:
    assert "sms" not in it["source"], f"source 含 sms: {it['source']}"
print("T8 PASS")


print("\n=== T9: 不返回 Memory ===")
full_text = json.dumps(items, ensure_ascii=False)
assert "should not leak memory" not in full_text, "Memory 内容泄漏"
for it in items:
    assert "memory" not in it["source"], f"source 含 memory: {it['source']}"
print("T9 PASS")


print("\n=== T10: 不泄漏敏感字段 ===")
full_text = json.dumps(items, ensure_ascii=False)
for forbidden_value in ["sk-xxx", "admin", "1000"]:
    assert forbidden_value not in full_text, f"敏感值泄漏: {forbidden_value}"
print("T10 PASS")


print("\n=== T11: 不泄漏 AgentState placeholder ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, now_ts=NOW, agent_state_dict=SAMPLE_AGENT_STATE)
full_text = json.dumps(items, ensure_ascii=False)
for placeholder in ["mood", "energy", "social_need", "stress"]:
    assert placeholder not in full_text, f"placeholder 泄漏: {placeholder}"
for it in items:
    assert it["type"] != "current_activity", "Recent 不应包含 current_activity"
print("T11 PASS")


print("\n=== T12: 不修改传入的 data ===")
data_before = copy.deepcopy(SAMPLE_DATA)
p.fetch("Dan", "Alice", SAMPLE_DATA, now_ts=NOW)
assert SAMPLE_DATA == data_before, "Provider 修改了 data"
print("T12 PASS")


print("\n=== T13: 静态检查——无 import main / ext_* ===")
with open(PROVIDER_PATH, "r", encoding="utf-8") as f:
    src = f.read()
import_pattern = re.compile(r'^\s*(?:import|from)\s+([\w\.]+)', re.MULTILINE)
imported = import_pattern.findall(src)
top_modules = set(m.split('.')[0] for m in imported)
forbidden_modules = {"main"}
forbidden_modules |= {m for m in top_modules if m.startswith("ext_")}
bad = top_modules & forbidden_modules
assert not bad, f"含禁止导入: {bad}"
print(f"T13 PASS（导入的模块: {sorted(top_modules)}）")


print("\n=== T14: 静态检查——无 LLM / 网络调用 ===")
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
call_llm_pattern = re.compile(r'\bcall_llm\s*\(', re.MULTILINE)
assert not call_llm_pattern.search(src), "含 call_llm 调用"
print("T14 PASS")


print("\n=== T15: 输出为 List[Dict] 结构 ===")
assert isinstance(items, list)
for it in items:
    assert isinstance(it, dict), f"item 不是 dict: {type(it)}"
    assert "type" in it and isinstance(it["type"], str)
    assert "content" in it and isinstance(it["content"], str)
    assert "source" in it and isinstance(it["source"], str)
for it in items:
    assert len(it["content"]) <= 120, f"content 超长: {len(it['content'])}"
print("T15 PASS")


print("\n=== T16: Token / Budget 可控 ===")
budget = ContextBudget()
big_data = {
    "ai_timeline": {"Dan": [{"time": "2026-09-21 12:00:00", "text": "X" * 500} for _ in range(100)]},
    "trails": {"Dan": [{"ts": NOW - 1, "time": "2026-09-21 12:00:00", "text": "Y" * 500, "room": "z" * 100} for _ in range(100)]},
    "ai_visited": {"Dan": ["P" * 200 for _ in range(100)]},
}
items_big = p.fetch("Dan", "Alice", big_data, now_ts=NOW)
sec = ContextSection(layer=LAYER_RECENT, budget_max=budget.recent_max)
for it in items_big:
    sec.add_item(it)
tokens = sec.token_estimate()
assert not sec.is_over_budget(), f"Recent 超预算: {tokens} > {budget.recent_max}"
print(f"T16 PASS: token_estimate={tokens}, budget_max={budget.recent_max}")


print("\n=== T17: 历史线性增长 → Recent 非线性增长 ===")
huge_data = {
    "ai_timeline": {"Dan": [{"time": "2026-09-21 12:00:00", "text": f"e{i}"} for i in range(1000)]},
    "trails": {"Dan": [{"ts": NOW - 1, "time": "2026-09-21 12:00:00", "text": f"t{i}", "room": "r"} for i in range(1000)]},
    "ai_visited": {"Dan": [f"p{i}" for i in range(1000)]},
}
items_huge = p.fetch("Dan", "Alice", huge_data, now_ts=NOW)
assert len(items_huge) <= 5 + 5 + 3, f"超大历史未受限: {len(items_huge)}"
print(f"T17 PASS: 输入 3000 条, 输出 {len(items_huge)} 条")


print("\n=== T18: 不生成不存在的事实 ===")
empty_data = {"ai_location": {"Dan": "cafe"}}
items_empty = p.fetch("Dan", "Alice", empty_data, now_ts=NOW)
assert items_empty == [], f"空 data 应返回空，实际 {items_empty}"
partial = {"ai_timeline": {"Dan": [{"time": "t", "text": "x"}]}}
items_partial = p.fetch("Dan", "Alice", partial, now_ts=NOW)
types_partial = [it["type"] for it in items_partial]
assert "recent_timeline" in types_partial
assert "recent_trail" not in types_partial, "不应生成不存在的 trail"
assert "recent_visited_place" not in types_partial, "不应生成不存在的 visited"
print("T18 PASS")


print("\n=== 附加 T19: describe() 返回审计信息 ===")
d = p.describe()
assert d["name"] == "recent"
assert d["layer"] == "recent"
assert "ai_timeline" in d["allowed_data_fields"]
assert "messages" in d["forbidden_data_fields"]
assert "recent_memory" in d["not_generated_item_types"]
assert "recent_decision" in d["not_generated_item_types"]
assert d["limits"]["timeline_max_items"] == 5
print("T19 PASS")


print("\n=== 附加 T20: 自定义上限生效 ===")
custom = RecentProvider(timeline_max_items=2, trail_max_items=1, visited_max_items=1)
items_custom = custom.fetch("Dan", "Alice", SAMPLE_DATA, now_ts=NOW)
assert sum(1 for it in items_custom if it["type"] == "recent_timeline") <= 2
assert sum(1 for it in items_custom if it["type"] == "recent_trail") <= 1
assert sum(1 for it in items_custom if it["type"] == "recent_visited_place") <= 1
print("T20 PASS")


print("\n=== 全部通过（T1-T20）===")
print(f"\n[定位] 仓库根 = {REPO_ROOT}")
print(f"[定位] Context = {CONTEXT_PATH}")
print(f"[定位] Provider = {PROVIDER_PATH}")