"""
test_b2_2_dynamic_world.py - Phase B2-2 测试

验证：
1. 基础字段提取
2. AgentState 可选字段
3. 保守缺省（不猜测）
4. 无 LLM / main / ext_* 依赖
5. 预算可控
"""

import importlib.util
import copy
import json
import re
import time

# 加载 context.py（用于预算测试）
spec_ctx = importlib.util.spec_from_file_location("context", "./context.py")
context_mod = importlib.util.module_from_spec(spec_ctx)
spec_ctx.loader.exec_module(context_mod)

# 加载 dynamic_world_provider.py
spec_p = importlib.util.spec_from_file_location(
    "dynamic_world_provider", "./dynamic_world_provider.py"
)
provider_mod = importlib.util.module_from_spec(spec_p)
spec_p.loader.exec_module(provider_mod)

DynamicWorldProvider = provider_mod.DynamicWorldProvider
ContextSection = context_mod.ContextSection
ContextBudget = context_mod.ContextBudget
LAYER_DYNAMIC_WORLD = context_mod.LAYER_DYNAMIC_WORLD


SAMPLE_DATA = {
    "ai_location": {"Dan": "黎深的江边大别墅·会客厅"},
    # 以下字段禁止进入 Context
    "messages": {"main": [{"sender": "x", "content": "should not leak"}]},
    "ai_keys": {"Alice": {"key": "sk-xxx"}},
    "dev_users": ["admin"],
    "pairs_admin": "admin",
    "server_id": "LK-MAIN-ABC123",
    "ai_impression": {"Dan": "主人很温柔"},
    "wallets": {"Dan": 1000},
    "work_sessions": {"Dan": {"building_id": "b1"}},
}

SAMPLE_AGENT_STATE = {
    "name": "Dan",
    "owner": "Alice",
    "location": "黎深的江边大别墅·会客厅",
    "wallet": 1000.0,
    "affection": 60,
    "is_following": False,
    "is_dating": True,
    "is_working": False,
    "current_activity": "dating",
    "current_goal": None,
    "mood": 70,
    "energy": 70,
    "social_need": 30,
    "stress": 20,
}


# =========================================================
print("=== T1: ai_name 为空 → 空 list ===")
p = DynamicWorldProvider()
assert p.fetch("", "Alice", SAMPLE_DATA) == []
assert p.fetch(None, "Alice", SAMPLE_DATA) == []
print("T1 PASS")


# =========================================================
print("\n=== T2: data 非 dict → 空 list ===")
assert p.fetch("Dan", "Alice", None) == []
assert p.fetch("Dan", "Alice", "not a dict") == []
print("T2 PASS")


# =========================================================
print("\n=== T3: 空 data → 至少有 current_time ===")
items = p.fetch("Dan", "Alice", {}, now_ts=1700000000.0)
assert len(items) >= 1
assert items[0]["type"] == "current_time"
print(f"T3 PASS: {[it['type'] for it in items]}")


# =========================================================
print("\n=== T4: current_time 是北京时间格式 ===")
items = p.fetch("Dan", "Alice", {}, now_ts=0)  # Unix epoch
time_item = next(it for it in items if it["type"] == "current_time")
# epoch = 1970-01-01 00:00:00 UTC = 1970-01-01 08:00:00 北京时间
assert time_item["content"] == "1970-01-01 08:00:00", \
    f"时间格式错误: {time_item['content']}"
print(f"T4 PASS: {time_item['content']}")


# =========================================================
print("\n=== T5: current_location 从 ai_location 读 ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA)
loc_item = next((it for it in items if it["type"] == "current_location"), None)
assert loc_item is not None
assert loc_item["content"] == "黎深的江边大别墅·会客厅"
assert loc_item["source"] == "main.data.ai_location"
print(f"T5 PASS: {loc_item['content']}")


# =========================================================
print("\n=== T6: missing location → 不生成 location item ===")
items = p.fetch("Nobody", "Alice", SAMPLE_DATA)
loc_item = next((it for it in items if it["type"] == "current_location"), None)
assert loc_item is None
print("T6 PASS")


# =========================================================
print("\n=== T7: 传入 AgentState → activity / is_dating 等 ===")
items = p.fetch(
    "Dan", "Alice", SAMPLE_DATA,
    agent_state_dict=SAMPLE_AGENT_STATE,
)
types = [it["type"] for it in items]
assert "current_activity" in types
assert "is_dating" in types
# is_working / is_following = False → 不提供
assert "is_working" not in types
assert "is_following" not in types
activity = next(it for it in items if it["type"] == "current_activity")
assert activity["content"] == "dating"
print(f"T7 PASS: {types}")


# =========================================================
print("\n=== T8: 未传 AgentState → 只有 time + location ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA)
types = [it["type"] for it in items]
assert "current_activity" not in types
assert "is_dating" not in types
assert "is_working" not in types
assert "current_time" in types
assert "current_location" in types
print(f"T8 PASS: {types}")


# =========================================================
print("\n=== T9: AgentState activity='idle' → 不提供 ===")
state_idle = dict(SAMPLE_AGENT_STATE, current_activity="idle")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, agent_state_dict=state_idle)
types = [it["type"] for it in items]
assert "current_activity" not in types
print(f"T9 PASS: {types}")


# =========================================================
print("\n=== T10: 不提供 current_building / current_map / current_region / current_place ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, agent_state_dict=SAMPLE_AGENT_STATE)
types = [it["type"] for it in items]
for forbidden_type in ("current_building", "current_map", "current_region", "current_place", "current_building_id"):
    assert forbidden_type not in types, f"不应提供 {forbidden_type}"
print(f"T10 PASS: {types}")


# =========================================================
print("\n=== T11: 不修改传入的 data ===")
data_before = copy.deepcopy(SAMPLE_DATA)
p.fetch("Dan", "Alice", SAMPLE_DATA, agent_state_dict=SAMPLE_AGENT_STATE)
assert SAMPLE_DATA == data_before, "Provider 修改了 data"
print("T11 PASS")


# =========================================================
print("\n=== T12: 不泄漏禁止字段 ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, agent_state_dict=SAMPLE_AGENT_STATE)
full_text = json.dumps(items, ensure_ascii=False)
forbidden_values = [
    "should not leak", "sk-xxx", "admin", "LK-MAIN-ABC123",
    "主人很温柔", "1000", "b1",
]
for v in forbidden_values:
    assert v not in full_text, f"禁止值泄漏: {v!r}"
# mood / energy 等 placeholder 也不能出现
for placeholder in ("mood", "energy", "social_need", "stress"):
    assert placeholder not in full_text, f"placeholder 泄漏: {placeholder}"
print("T12 PASS")


# =========================================================
print("\n=== T13: 静态检查——无 import main / ext_* ===")
with open("./dynamic_world_provider.py", "r", encoding="utf-8") as f:
    src = f.read()
import_pattern = re.compile(r'^\s*(?:import|from)\s+([\w\.]+)', re.MULTILINE)
imported = import_pattern.findall(src)
top_modules = set(m.split('.')[0] for m in imported)
forbidden_modules = {"main"}
forbidden_modules |= {m for m in top_modules if m.startswith("ext_")}
bad = top_modules & forbidden_modules
assert not bad, f"含禁止导入: {bad}"
print(f"T13 PASS（导入的模块: {sorted(top_modules)}）")


# =========================================================
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


# =========================================================
print("\n=== T15: describe() 返回审计信息 ===")
d = p.describe()
assert d["name"] == "dynamic_world"
assert d["layer"] == "dynamic_world"
assert "ai_location" in d["allowed_data_fields"]
assert "ai_keys" in d["forbidden_data_fields"]
assert "map_id" in d["map_knowledge_reserved"]
assert "current_building" in d["unsupported_item_types_reserved"]
print("T15 PASS")


# =========================================================
print("\n=== T16: 预算可控 ===")
budget = ContextBudget()
items = p.fetch("Dan", "Alice", SAMPLE_DATA, agent_state_dict=SAMPLE_AGENT_STATE)
sec = ContextSection(layer=LAYER_DYNAMIC_WORLD, budget_max=budget.dynamic_world_max)
for it in items:
    sec.add_item(it)
tokens = sec.token_estimate()
assert not sec.is_over_budget(), \
    f"Dynamic World 超预算: {tokens} > {budget.dynamic_world_max}"
print(f"T16 PASS: token_estimate={tokens}, budget_max={budget.dynamic_world_max}")


# =========================================================
print("\n=== T17: 返回结构化 list[dict]，非 Prompt ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, agent_state_dict=SAMPLE_AGENT_STATE)
assert isinstance(items, list)
for it in items:
    assert isinstance(it, dict)
    assert "type" in it and isinstance(it["type"], str)
    assert "content" in it and isinstance(it["content"], str)
    assert "source" in it and isinstance(it["source"], str)
assert not isinstance(items, ContextSection)
print("T17 PASS")


# =========================================================
print("\n=== T18: 不生成 map / building / region / place 任何变体 ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, agent_state_dict=SAMPLE_AGENT_STATE)
full_text = json.dumps(items, ensure_ascii=False).lower()
# 这些关键词不能在 type 或 source 里出现（content 里可能有 location 名不算）
for it in items:
    it_type = it["type"].lower()
    it_source = it["source"].lower()
    for kw in ("map", "region", "place", "building"):
        if kw == "place" and "location" in it_type:
            continue  # location 里含 "place" 字符，跳过
        assert kw not in it_type, f"type 含禁止词 {kw}: {it_type}"
        assert kw not in it_source, f"source 含禁止词 {kw}: {it_source}"
print("T18 PASS")


# =========================================================
print("\n=== 全部通过（T1-T18）===")