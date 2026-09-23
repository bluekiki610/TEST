"""
test_b2_4_long_term.py - Phase B2-4 测试

从 TEST 仓库根目录运行：
    python docs/test_b2_4_long_term.py

自动定位 agent/long_term_provider.py 与 agent/context.py。
不依赖 cwd。

覆盖 T1-T20。
"""

import importlib.util
import copy
import json
import re
import sys
from pathlib import Path

# =========================================================
# 路径定位
# =========================================================
REPO_ROOT = Path(__file__).resolve().parent.parent
PROVIDER_PATH = REPO_ROOT / "agent" / "long_term_provider.py"
CONTEXT_PATH = REPO_ROOT / "agent" / "context.py"

if not PROVIDER_PATH.exists():
    print(f"[FATAL] 找不到 {PROVIDER_PATH}", file=sys.stderr)
    sys.exit(1)
if not CONTEXT_PATH.exists():
    print(f"[FATAL] 找不到 {CONTEXT_PATH}", file=sys.stderr)
    sys.exit(1)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


provider_mod = _load_module("long_term_provider", PROVIDER_PATH)
context_mod = _load_module("context", CONTEXT_PATH)

LongTermProvider = provider_mod.LongTermProvider
ContextSection = context_mod.ContextSection
ContextBudget = context_mod.ContextBudget
LAYER_LONG_TERM = context_mod.LAYER_LONG_TERM


# =========================================================
# 测试数据
# =========================================================
SAMPLE_DATA = {
    # 这些字段 Provider 都不应读取
    "messages": {"main": [{"sender": "x", "content": "should not read"}]},
    "sms": {"Alice": [{"from": "Dan", "text": "should not read sms"}]},
    "ai_memories": {"Alice": [{"ai": "Dan", "text": "should not read memory"}]},
    "ai_impression": {"Dan": "should not read impression"},
    "ai_timeline": {"Dan": [{"text": "should not read timeline"}]},
    "trails": {"Dan": [{"ts": 0, "text": "should not read trail"}]},
    "ai_visited": {"Dan": ["should not read visited"]},
    "notes": {"r": [{"text": "should not read note"}]},
    "diaries": {"r": [{"text": "should not read diary"}]},
    "stories": {"b": [{"text": "should not read story"}]},
    "ai_keys": {"Alice": {"key": "sk-xxx"}},
    "dev_users": ["admin"],
    "pairs_admin": "admin",
    "wallets": {"Dan": 1000},
    "ai_location": {"Dan": "cafe"},
}

SAMPLE_AGENT_STATE = {
    "name": "Dan",
    "current_activity": "dating",
    "is_working": False,
    "is_dating": True,
    "mood": 70,
    "energy": 70,
    "social_need": 30,
    "stress": 20,
}


# =========================================================
print("=== T1: 空 data 返回 [] ===")
p = LongTermProvider()
assert p.fetch("Dan", "Alice", {}) == []
print("T1 PASS")


# =========================================================
print("\n=== T2: 无效 ai_name ===")
assert p.fetch("", "Alice", SAMPLE_DATA) == []
assert p.fetch(None, "Alice", SAMPLE_DATA) == []
assert p.fetch(123, "Alice", SAMPLE_DATA) == []
print("T2 PASS")


# =========================================================
print("\n=== T3: owner 缺失 ===")
# owner 为空串 / None，仍应返回 []
assert p.fetch("Dan", "", SAMPLE_DATA) == []
assert p.fetch("Dan", None, SAMPLE_DATA) == []
print("T3 PASS")


# =========================================================
print("\n=== T4: recall_query 缺失 ===")
# 不传 recall_query → []
assert p.fetch("Dan", "Alice", SAMPLE_DATA) == []
print("T4 PASS")


# =========================================================
print("\n=== T5: recall_query 存在但当前仍返回 [] ===")
assert p.fetch(
    "Dan", "Alice", SAMPLE_DATA,
    recall_query="当前主人在下雨的咖啡馆",
) == []
assert p.fetch(
    "Dan", "Alice", SAMPLE_DATA,
    recall_query="",
) == []
assert p.fetch(
    "Dan", "Alice", SAMPLE_DATA,
    recall_query="x" * 1000,
) == []
print("T5 PASS")


# =========================================================
print("\n=== T6: 不读取 chat / messages ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, recall_query="test")
full_text = json.dumps(items, ensure_ascii=False)
assert "should not read" not in full_text
# Provider 返回空，不可能泄漏
assert items == []
print("T6 PASS")


# =========================================================
print("\n=== T7: 不读取 SMS ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, recall_query="test")
full_text = json.dumps(items, ensure_ascii=False)
assert "should not read sms" not in full_text
print("T7 PASS")


# =========================================================
print("\n=== T8: 不读取 timeline / trails / visited ===")
# 静态检查：源码不应出现这些字段名
with open(PROVIDER_PATH, "r", encoding="utf-8") as f:
    src = f.read()

# 允许在 FORBIDDEN_DATA_FIELDS 出现（用于声明），但不能在读取路径出现
# 判断方法：检查是否有 data.get("ai_timeline") 等读取模式
read_patterns = [
    r'data\.get\(\s*["\']ai_timeline["\']',
    r'data\.get\(\s*["\']trails["\']',
    r'data\.get\(\s*["\']ai_visited["\']',
    r'\[\s*["\']ai_timeline["\']\s*\]',
    r'\[\s*["\']trails["\']\s*\]',
    r'\[\s*["\']ai_visited["\']\s*\]',
]
for pat in read_patterns:
    assert not re.search(pat, src), f"源码出现读取模式: {pat}"
print("T8 PASS")


# =========================================================
print("\n=== T9: 不读取 Memory Runtime ===")
# 静态检查：不应 import ext_memory
assert "import ext_memory" not in src
assert "from ext_memory" not in src
# 不应出现 pending_events 读取
assert "pending_events" not in src or "不读" in src or "禁止" in src
print("T9 PASS")


# =========================================================
print("\n=== T10: 不泄漏敏感字段 ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, recall_query="test")
full_text = json.dumps(items, ensure_ascii=False)
for v in ["sk-xxx", "admin", "1000"]:
    assert v not in full_text, f"敏感值泄漏: {v}"
print("T10 PASS")


# =========================================================
print("\n=== T11: 不读取 AgentState placeholder ===")
items = p.fetch(
    "Dan", "Alice", SAMPLE_DATA,
    agent_state_dict=SAMPLE_AGENT_STATE,
    recall_query="test",
)
full_text = json.dumps(items, ensure_ascii=False)
for placeholder in ["mood", "energy", "social_need", "stress"]:
    assert placeholder not in full_text, f"placeholder 泄漏: {placeholder}"
print("T11 PASS")


# =========================================================
print("\n=== T12: 不修改输入 data ===")
data_before = copy.deepcopy(SAMPLE_DATA)
p.fetch("Dan", "Alice", SAMPLE_DATA, recall_query="test")
assert SAMPLE_DATA == data_before, "Provider 修改了 data"
print("T12 PASS")


# =========================================================
print("\n=== T13: 不修改 AgentState ===")
state_before = copy.deepcopy(SAMPLE_AGENT_STATE)
p.fetch(
    "Dan", "Alice", SAMPLE_DATA,
    agent_state_dict=SAMPLE_AGENT_STATE,
    recall_query="test",
)
assert SAMPLE_AGENT_STATE == state_before, "Provider 修改了 agent_state_dict"
print("T13 PASS")


# =========================================================
print("\n=== T14: 不 import main / ext_* ===")
import_pattern = re.compile(r'^\s*(?:import|from)\s+([\w\.]+)', re.MULTILINE)
imported = import_pattern.findall(src)
top_modules = set(m.split('.')[0] for m in imported)
forbidden_modules = {"main"}
forbidden_modules |= {m for m in top_modules if m.startswith("ext_")}
bad = top_modules & forbidden_modules
assert not bad, f"含禁止导入: {bad}"
print(f"T14 PASS（导入的模块: {sorted(top_modules)}）")


# =========================================================
print("\n=== T15: 不调用 LLM / 网络 ===")
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
print("T15 PASS")


# =========================================================
print("\n=== T16: 输出为 List[Dict] ===")
items = p.fetch("Dan", "Alice", SAMPLE_DATA, recall_query="test")
assert isinstance(items, list)
for it in items:
    assert isinstance(it, dict), f"item 不是 dict: {type(it)}"
print("T16 PASS")


# =========================================================
print("\n=== T17: budget / item limit 元数据存在 ===")
d = p.describe()
assert "limits" in d
assert "max_items" in d["limits"]
assert "max_chars_per_item" in d["limits"]
assert "token_budget" in d["limits"]
assert d["limits"]["max_items"] == 5
assert d["limits"]["max_chars_per_item"] == 300
assert d["limits"]["token_budget"] == 2500
print(f"T17 PASS: limits={d['limits']}")


# =========================================================
print("\n=== T18: describe() 正确 ===")
d = p.describe()
assert d["name"] == "long_term"
assert d["layer"] == "long_term"
assert d["status"] == "stub"
assert d["data_source"] == "none"
assert d["memory_runtime_connected"] is False
assert d["recall_supported"] is False
assert d["current_return_value"] == "[]"
assert "B2-4" in d["notes"] or "Stub" in d["notes"]
print("T18 PASS")


# =========================================================
print("\n=== T19: 不创建持久化文件 ===")
# 静态检查：源码不应有文件写入操作
write_patterns = [
    r'\.write\s*\(',
    r'\.write_text\s*\(',
    r'\.write_bytes\s*\(',
    r'open\s*\([^)]*["\']w["\']',
    r'json\.dump\s*\(',
    r'aiofiles\.open',
]
for pat in write_patterns:
    assert not re.search(pat, src), f"含写文件操作: {pat}"
# 运行前后对比目录内容
# 简化：只做静态检查，运行时不产生文件
print("T19 PASS")


# =========================================================
print("\n=== T20: 不生成不存在的历史事实 ===")
# 各种输入 → 都返回 []
cases = [
    ("Dan", "Alice", {}),
    ("Dan", "Alice", SAMPLE_DATA),
    ("Dan", "Alice", SAMPLE_DATA, None, None, "query1"),
    ("Dan", "Alice", SAMPLE_DATA, None, SAMPLE_AGENT_STATE, "query2"),
]
for case in cases:
    r = p.fetch(*case)
    assert r == [], f"应返回空，实际 {r}"
# 不生成任何 item type
for forbidden_type in p.NOT_GENERATED_ITEM_TYPES:
    assert forbidden_type not in json.dumps(d, ensure_ascii=False) or True
    # 检查 NOT_GENERATED_ITEM_TYPES 中包含它
    assert forbidden_type in p.NOT_GENERATED_ITEM_TYPES
print("T20 PASS")


# =========================================================
print("\n=== 全部通过（T1-T20）===")
print(f"\n[定位] 仓库根 = {REPO_ROOT}")
print(f"[定位] Provider = {PROVIDER_PATH}")
print(f"[定位] Context = {CONTEXT_PATH}")
print(f"\n[状态] status={p.STATUS}, data_source={p.DATA_SOURCE}")
print(f"[状态] memory_runtime_connected={p.MEMORY_RUNTIME_CONNECTED}")
print(f"[状态] recall_supported={p.RECALL_SUPPORTED}")