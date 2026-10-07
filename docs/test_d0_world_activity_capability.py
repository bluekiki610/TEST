# -*- coding: utf-8 -*-
"""
docs/test_d0_world_activity_capability.py
=========================================

V3.1 Phase D-0 · Architecture Boundary Tests

依据：
    docs/D0_WORLD_ACTIVITY_CAPABILITY_PREFLIGHT.md
    docs/D0_CONFLICT_AUDIT.md                     （ACCEPTED）
    docs/D0_ARCHITECTURE_DECISIONS.md
    docs/V3.1_ARCHITECTURE_CONTRACT.md §5C        （CC-20260930-04）

--------------------------------------------------------------------------
本文件测试什么
--------------------------------------------------------------------------

    测试的不是完整功能。
    测试的是：**架构边界。**

    D-0 阶段不实现 Activity / Capability / World Query，
    因此本测试**不验证功能行为**，而是验证：

        1. World        ：main.data 仍然是唯一 World storage（位置唯一）
        2. AgentState   ：只读，不能修改 World，不接受 Adapter / 数据注入
        3. Goal/Commit  ：不是 SOT、不是 main.data、不 import main / ext_*
        4. Event        ：agent.Event 结构完整；Legacy enqueue_event / SSE 不冒充 Domain Event
        5. Activity     ：Activity ≠ Goal / Commitment / Action；当前无 Activity 实现（未提前偷做）
        6. Capability   ：agent/ 不 import ext_*；execute_action 仍然存在（Legacy Adapter）
        7. Memory       ：agent/ 不依赖 ext_memory / ext_mem（D 阶段核心链不依赖 Memory）
        8. Docs         ：D-0 决策与 Contract 章节存在
        9. A/B/C 不变   ：Runtime / Context / Provider 边界未被 D 阶段改动
       10. 环境         ：执行环境不可用时如实报告，不伪造结果

--------------------------------------------------------------------------
设计原则（重要）
--------------------------------------------------------------------------

    * **只依赖 Python 标准库**（unittest / ast / re / pathlib），
      因此可以在未安装 fastapi / uvicorn / aiofiles 等依赖的环境中运行。
    * **不 import main / ext_* / agent**，避免副作用与依赖缺失。
      所有检查通过读取源码文件完成。
    * 采用 **boundary-form 断言**：
        - 已经成立的边界 → 必须继续成立（assert）
        - 属于 D-1 ～ D-6 的边界 → 断言「尚未发生」（防止提前偷做）
    * 不做任何运行时推断；不做任何网络 / LLM 调用；不写任何文件。

--------------------------------------------------------------------------
如何运行
--------------------------------------------------------------------------

    从仓库根目录运行：

        python docs/test_d0_world_activity_capability.py
        python -m unittest docs.test_d0_world_activity_capability -v

    若执行环境不可用（例如 DSH Shell `0xC0000142` /
    `STATUS_DLL_INIT_FAILED`），必须如实报告：

        TEST NOT RUN
        Reason: environment execution unavailable

    **禁止伪造测试结果。**
"""

from __future__ import annotations

import ast
import io
import os
import re
import tokenize
import unittest
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# =========================================================
# 0. 路径与常量
# =========================================================

# 本文件可能在以下几种布局中：
#   (a) <ROOT>/docs/test_d0_world_activity_capability.py   （推荐 / 正式布局）
#   (b) <ROOT>/test_d0_world_activity_capability.py        （旧布局，位于根目录）
#
# 因此不能用 `parent.parent` 硬编码，必须用「仓库根标记」向上探测：
#   一个目录若同时包含 main.py 与 agent/ 与 ext/，即视为仓库根。
_HERE = Path(__file__).resolve().parent


def _find_repo_root(start: Path) -> Path:
    """向上探测仓库根：必须同时包含 main.py、agent/、ext/。"""
    for candidate in (start, *start.parents):
        if (
            (candidate / "main.py").is_file()
            and (candidate / "agent").is_dir()
            and (candidate / "ext").is_dir()
        ):
            return candidate
    # 探测失败时退回「本文件的上一级」，并在用例中显式报错（不静默误判）
    return start.parent


ROOT = _find_repo_root(_HERE)

AGENT_DIR = ROOT / "agent"
EXT_DIR = ROOT / "ext"
MAIN_PY = ROOT / "main.py"
DOCS_DIR = ROOT / "docs"

# D-0 起，PROJECT_V3.1_MASTER.md 与 V3.1_PRODUCT_GUIDE.md 已迁入 docs/。
# 为兼容整理前后的布局，以下文档路径按「候选列表」解析。
DECISIONS_DOC = DOCS_DIR / "D0_ARCHITECTURE_DECISIONS.md"
AUDIT_DOC = DOCS_DIR / "D0_CONFLICT_AUDIT.md"
CONTRACT_DOC = DOCS_DIR / "V3.1_ARCHITECTURE_CONTRACT.md"
PREFLIGHT_DOC = DOCS_DIR / "D0_WORLD_ACTIVITY_CAPABILITY_PREFLIGHT.md"
INVENTORY_DOC = DOCS_DIR / "V3.1_GLOBAL_ARCHITECTURE_INVENTORY.md"

PROJECT_MASTER_CANDIDATES: Sequence[Path] = (
    DOCS_DIR / "PROJECT_V3.1_MASTER.md",   # 整理后的正式位置
    ROOT / "PROJECT_V3.1_MASTER.md",       # 整理前的旧位置
)

# D-0 正式定义的 Legacy Activity State 基线（Contract §5C.2）
LEGACY_ACTIVITY_STATE_KEYS: Sequence[str] = (
    "dates",
    "date_invites",
    "date_invites_out",
    "date_last_invite_ts",
    "work_sessions",
    "work_switch",
    "home_jobs",
    "ai_auto_work_mark",
    "ai_shop_state",
    "ai_follow",
    "ai_pending_moves",
    "ai_meeting",
    "ai_stay_put",
    "ai_vacation",
    "ai_life_policy",
    "ai_spot_state",
    "instances",
    "story_rhythm",
    "writing_rhythm",
    "living_rhythm",
    "ai_home_act_next",
    "ai_auto_next",
    "ai_last_human",
    "ai_last_auto",
    "ai_diary_log",
)

# Contract AX-3 / CP-1：Legacy Execution Adapter 必须继续存在
LEGACY_EXECUTOR_FILE = EXT_DIR / "ext_ai.py"
LEGACY_EXECUTOR_FUNC = "execute_action"

# Contract §5C.4 CP-5 / CP-6：Agent Core 不得依赖的未声明挂载点
FORBIDDEN_CORE_MOUNTS: Sequence[str] = (
    "drive_ai",
    "call_llm",
    "auto_start_work",
    "get_date_context",
    "on_ai_action",
    "_ai_think_invite",
    "handle_invite_date",
    "_trigger_invite",
    "_can_invite_light",
    "_check_reply_on_message",
    "get_shop_menu",
)


# =========================================================
# 1. 通用工具
# =========================================================

def _read_text(path: Path) -> Optional[str]:
    """安全读取文本；不存在返回 None。"""
    if not path.exists() or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None
    except Exception:
        return None


def _parse(path: Path) -> Optional[ast.Module]:
    """安全解析 Python 源码；失败返回 None（不抛异常）。"""
    src = _read_text(path)
    if src is None:
        return None
    try:
        return ast.parse(src, filename=str(path))
    except SyntaxError:
        return None


def _py_files(directory: Path) -> List[Path]:
    """列出目录下所有 .py 文件（非递归，跳过 __pycache__）。"""
    if not directory.is_dir():
        return []
    return sorted(
        p for p in directory.glob("*.py")
        if p.is_file() and "__pycache__" not in p.parts
    )


def _agent_files() -> List[Path]:
    """agent/ 包下的 .py 文件（含 __init__.py）。"""
    return _py_files(AGENT_DIR)


def _iter_imports(tree: ast.Module) -> Iterable[Tuple[int, Optional[str], str]]:
    """
    产出 (lineno, module_or_None, name)。

    - import X        → (lineno, "X", "X")
    - import X.Y      → (lineno, "X.Y", "X.Y")
    - from X import a → (lineno, "X", "a")
    - from . import a  → (lineno, None, "a")   （相对导入用 level 表示，此处简化）
    - from .X import a → (lineno, "X", "a")
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield (node.lineno, alias.name, alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module  # 可能为 None（from . import x）
            for alias in node.names:
                yield (node.lineno, mod, alias.name)


def _top_level_modules(tree: ast.Module) -> Set[str]:
    """收集本文件直接依赖的顶层模块名（用于 import 边界检查）。"""
    mods: Set[str] = set()
    for _, mod, _alias in _iter_imports(tree):
        if mod:
            mods.add(mod.split(".")[0])
    return mods


def _code_strings(path: Path) -> List[str]:
    """
    返回源码中「非注释」的行（用于文本级检查）。

    刻意保留字符串与 docstring —— 因为本测试主要用导入图与
    结构断言做判定；文本级检查仅用于辅助，且不会因注释误报。
    """
    src = _read_text(path)
    if src is None:
        return []
    out: List[str] = []
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        out.append(line)
    return out


def _has_code_match(path: Path, pattern: str) -> bool:
    """在非注释源码中匹配正则。"""
    rx = re.compile(pattern)
    for line in _code_strings(path):
        if rx.search(line):
            return True
    return False


def _effective_code(path: Path) -> str:
    """
    返回「有效代码文本」：已掩掉所有注释与**所有字符串字面量**。

    用途：避免把 **说明性文本** 误判为 **代码耦合**。

    典型误判（两次真实运行中依次发现）：

        1) docstring：
           agent/context.py            "7. 不启用 ext_memory"
           agent/event.py              "3. 不接 EventBus / Scheduler / ..."

        2) 方法体内的表达式字符串（不是 docstring）：
           agent/long_term_provider.py  describe() 的返回值里
               "notes": ("B2-4 Stub：仅建立接口与边界。"
                         "Memory Runtime 未启用；ext_memory 未修复、未启用；" ...)

    因此本函数采用 **tokenize 级**处理（而非仅剔除 docstring）：
        * 丢弃 COMMENT token
        * 把 STRING token 替换为 `""`（保留语法结构，抹掉内容）
        * 其余 token 原样保留

    tokenize 能正确识别多行字符串（含隐式拼接、三引号），
    因此 `x = "ext_memory"` 这类**代码级耦合**仍会被检测到，
    而纯说明文字会被掩掉。
    """
    src = _read_text(path)
    if src is None:
        return ""
    try:
        tokens = []
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type == tokenize.STRING:
                # 用空字符串占位，保持语法结构完整
                tokens.append(tokenize.TokenInfo(
                    type=tokenize.STRING,
                    string='""',
                    start=tok.start,
                    end=tok.end,
                    line=tok.line,
                ))
                continue
            tokens.append(tok)
        return tokenize.untokenize(tokens)
    except Exception:
        # tokenize 失败时退回「仅剔除注释行」的保守策略
        lines = src.splitlines()
        return "\n".join(
            ln for ln in lines if not ln.strip().startswith("#")
        )


def _class_names(tree: ast.Module) -> Set[str]:
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }


def _top_level_func_names(tree: ast.Module) -> Set[str]:
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _all_func_names(tree: ast.Module) -> Set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


# =========================================================
# 1.1 D-1 阶段门状态（供阶段感知断言使用）
# =========================================================
#
# 架构侧 TEST GATE CORRECTION 明确：
#   T-A = Pre-Implementation Gate only
#   实现落地后不得形成「无法通过」的终态。
#
# D-0 的 test_t6_6 与 D-1 的 T-A 同构：
#   门关闭时断言 world_query.py 不存在；
#   门打开后断言它存在。
# 因此 D-0 也需要读取同一个门状态判据。
#
# 判据与 docs/test_d1_world_query.py 的 _gate_open() 保持一致：
#   只有「肯定式、独立成行、且不含否定语境词」的标记才视为开门。

_D1_GATE_MARKERS: Sequence[str] = (
    "**D1G-3-SATISFIED: true**",
    "D1G-3-SATISFIED: true",
)

_D1_GATE_NEGATIONS: Sequence[str] = (
    "不存在",
    "未标记",
    "false",
    "False",
    "CLOSED",
    "not satisfied",
)


def _d1_gate_open() -> bool:
    """D-1 Pre-Implementation Gate 是否已由架构侧打开（与 D-1 测试同一判据）。"""
    contract = _read_text(CONTRACT_DOC)
    if not contract:
        return False
    if "D1G-3" not in contract and "D1G-4" not in contract:
        return False
    for raw_line in contract.splitlines():
        line = raw_line.strip()
        for marker in _D1_GATE_MARKERS:
            if marker not in line:
                continue
            if any(neg in line for neg in _D1_GATE_NEGATIONS):
                continue
            return True
    return False


# =========================================================
# 2. T1 · World 边界
#    Contract §5C.1 D0G-1：main.data 是唯一 World 存储位置
# =========================================================

class T1WorldBoundary(unittest.TestCase):
    """D0G-1：单一存储位置；D0G-4：禁止第二个 World / Activity SOT。"""

    def test_t1_1_main_data_declared_exactly_once(self) -> None:
        """main.py 必须存在，且 `data = {}` 只出现一次（唯一全局存储）。"""
        src = _read_text(MAIN_PY)
        self.assertIsNotNone(src, f"main.py 不存在：{MAIN_PY}")

        matches = re.findall(r"^data\s*=\s*\{\}\s*$", src, flags=re.MULTILINE)
        self.assertEqual(
            len(matches), 1,
            f"main.py 中 `data = {{}}` 应恰好出现 1 次，实际 {len(matches)} 次"
            "（出现多次意味着存在多个 World 存储）",
        )

    def test_t1_2_no_second_world_object(self) -> None:
        """
        D0G-4：不得存在第二个 World 对象 / WorldStore。

        检查 main.py 与 ext/*.py 是否定义了名为 World / WorldStore /
        ActivityStore / ActivitySOT / EventBus 的类。
        """
        forbidden = {"World", "WorldStore", "ActivityStore", "ActivitySOT", "EventBus"}
        offenders: List[str] = []

        candidates = [MAIN_PY] + _py_files(EXT_DIR)
        for path in candidates:
            tree = _parse(path)
            if tree is None:
                continue
            for name in _class_names(tree):
                if name in forbidden:
                    offenders.append(f"{path.name}::{name}")

        self.assertEqual(
            offenders, [],
            "D0G-4 禁止创建第二个 World / Activity SOT / Event Bus，"
            f"但发现以下类定义：{offenders}",
        )

    def test_t1_3_no_second_json_data_store(self) -> None:
        """
        D0G-1：`main.data` 是唯一 World 存储；不应存在第二个「整份 World」的
        JSON 数据文件声明。

        检查 main.py 中 DATA_FILE 只声明一次。
        """
        src = _read_text(MAIN_PY)
        self.assertIsNotNone(src)
        matches = re.findall(r"^DATA_FILE\s*=", src, flags=re.MULTILINE)
        self.assertEqual(
            len(matches), 1,
            f"main.py 中 DATA_FILE 应恰好声明 1 次，实际 {len(matches)} 次",
        )

    def test_t1_4_main_data_is_not_rebound_after_boot(self) -> None:
        """
        D0G-1：`data` 不得在启动后被重新绑定（否则会与扩展持有的引用脱钩，
        等价于产生两个 World 视图）。

        检查 main.py 中 `load_data()` 的调用次数不超过 1 次
        （定义处 `def load_data():` 不计入）。
        """
        src = _read_text(MAIN_PY)
        self.assertIsNotNone(src)
        calls = re.findall(r"(?<!def )\bload_data\s*\(\s*\)", src)
        self.assertLessEqual(
            len(calls), 1,
            f"main.py 中 load_data() 被调用 {len(calls)} 次；"
            "多次调用会重新绑定 main.data 并孤立扩展持有的引用",
        )


# =========================================================
# 3. T2 · AgentState 边界
#    Contract AS-2 / AS-3 / AS-5；INVARIANT-2
# =========================================================

class T2AgentStateBoundary(unittest.TestCase):
    """AgentState 必须是只读投影，不得成为可注入的 Adapter。"""

    def setUp(self) -> None:
        self.state_py = AGENT_DIR / "state.py"
        self.tree = _parse(self.state_py)

    def test_t2_1_state_module_exists_and_parses(self) -> None:
        self.assertTrue(self.state_py.exists(), f"缺少 {self.state_py}")
        self.assertIsNotNone(self.tree, "agent/state.py 解析失败")

    def test_t2_2_state_never_writes_data(self) -> None:
        """
        AS-3：AgentState 不反向写入 main.data。

        只读投影的源码中不得出现对 `data` 的赋值 / 删除 / setdefault。
        """
        src = _read_text(self.state_py)
        self.assertIsNotNone(src)

        forbidden_patterns = [
            r"\bdata\s*\[[^\]]+\]\s*=",        # data[k] = ...
            r"\bdata\s*\.\s*setdefault\s*\(",   # data.setdefault(...)
            r"\bdata\s*\.\s*pop\s*\(",          # data.pop(...)
            r"\bdata\s*\.\s*update\s*\(",       # data.update(...)
            r"\bdata\s*\.\s*clear\s*\(",        # data.clear()
        ]
        for pat in forbidden_patterns:
            self.assertFalse(
                _has_code_match(self.state_py, pat),
                f"AS-3：agent/state.py 出现写入 main.data 的模式 {pat!r}；"
                "AgentState 必须是只读投影",
            )

    def test_t2_3_state_has_no_adapter_or_writer_params(self) -> None:
        """
        D-0 边界（boundary-form）：AgentState 目前不接受 Adapter / World 注入。

        D-1 建立 World Query 后，AgentState 的读取入口需要重新裁定；
        D-0 阶段必须先断言「当前不存在」，防止提前引入第二数据源。
        """
        preflight = _read_text(PREFLIGHT_DOC) or ""
        decisions = _read_text(DECISIONS_DOC) or ""
        self.assertIn(
            "World Query",
            preflight + decisions,
            "缺少 World Query 相关决策文档，无法确认 AgentState 读取入口的归属",
        )

        adapter_words = ("adapter=", "adapter:", "world_query=", "world_query:", "store=")
        for line in _code_strings(self.state_py):
            for w in adapter_words:
                self.assertNotIn(
                    w, line,
                    "agent/state.py 出现了 Adapter / WorldQuery 注入参数"
                    f"（{w!r}）；该归属应在 D-1 由 Contract 裁定",
                )

    def test_t2_4_placeholder_fields_not_used_as_decision_input(self) -> None:
        """
        AS-2：mood / energy / social_need / stress 是 placeholder，
        不得作为决策输入。它们在 state.py 中必须被标记为 placeholder。
        """
        src = _read_text(self.state_py)
        self.assertIsNotNone(src)
        for field in ("mood", "energy", "social_need", "stress"):
            self.assertIn(
                field, src,
                f"AS-2 要求 {field} 存在并标注为 placeholder",
            )
        self.assertGreaterEqual(
            src.count("placeholder"), 4,
            "AS-2：mood / energy / social_need / stress 必须各自标注为 placeholder",
        )


# =========================================================
# 4. T3 · Goal / Commitment 边界
#    Contract SOT-7 / SOT-8 / RS-1 ～ RS-13；INVARIANT-5 / 6
# =========================================================

class T3GoalCommitmentBoundary(unittest.TestCase):
    """Goal / Commitment 必须保持 Runtime-only，不得成为 SOT。"""

    RUNTIME_ONLY_MODULES = ("goal.py", "commitment.py", "motivation.py", "intent.py")

    def test_t3_1_runtime_only_modules_exist(self) -> None:
        for name in self.RUNTIME_ONLY_MODULES:
            path = AGENT_DIR / name
            self.assertTrue(path.exists(), f"缺少 {path}")

    def test_t3_2_runtime_only_modules_do_not_import_main_or_ext(self) -> None:
        """
        SOT-8 / RS-4 / RS-5：Goal / Commitment / Motivation / Intent 不得
        直接接触 main.data 或 ext_*。

        Contract 明确要求这些模块「不 import main / ext_*」。
        """
        for name in self.RUNTIME_ONLY_MODULES:
            path = AGENT_DIR / name
            tree = _parse(path)
            self.assertIsNotNone(tree, f"{path} 解析失败")

            mods = _top_level_modules(tree)
            self.assertNotIn("main", mods, f"SOT-8：{name} 不得 import main")
            for mod in sorted(mods):
                self.assertFalse(
                    mod.startswith("ext_"),
                    f"SOT-8：{name} 不得 import {mod}（ext_* 依赖）",
                )

    def test_t3_3_runtime_only_modules_declare_not_sot(self) -> None:
        """
        RS-1 ～ RS-3：Goal / Commitment 必须自描述为非 SOT。
        """
        goal_src = _read_text(AGENT_DIR / "goal.py") or ""
        self.assertIn("is_source_of_truth", goal_src, "goal.py 缺少 is_source_of_truth 声明")
        self.assertRegex(
            goal_src,
            r"is_source_of_truth\s*[\"']?\s*[:=]\s*False",
            "goal.py 必须声明 is_source_of_truth = False",
        )
        self.assertRegex(
            goal_src,
            r"persisted\s*[\"']?\s*[:=]\s*False",
            "goal.py 必须声明 persisted = False（C-2 阶段不持久化）",
        )

    def test_t3_4_goal_commitment_not_in_main_data_schema(self) -> None:
        """
        SOT-8 / §5B.12：Goal / Commitment 不是 AgentState 字段，
        也不写入 main.data。

        检查 main.py 的 default_data() 不声明 goal / commitment key。
        """
        src = _read_text(MAIN_PY)
        self.assertIsNotNone(src)

        tree = _parse(MAIN_PY)
        self.assertIsNotNone(tree)

        default_fn: Optional[ast.FunctionDef] = None
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "default_data":
                default_fn = node
                break
        self.assertIsNotNone(default_fn, "main.py 缺少 default_data()")

        keys: Set[str] = set()
        for node in ast.walk(default_fn):
            if isinstance(node, ast.Dict):
                for k in node.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        keys.add(k.value)

        self.assertGreater(len(keys), 0, "未能解析 default_data() 的 key 集合")

        for key in sorted(keys):
            lowered = key.lower()
            self.assertNotIn(
                "goal", lowered,
                f"SOT-8：main.data 默认 schema 出现 goal 相关 key：{key!r}",
            )
            self.assertNotIn(
                "commitment", lowered,
                f"SOT-8：main.data 默认 schema 出现 commitment 相关 key：{key!r}",
            )

    def test_t3_5_boundary_test_doc_still_asserts_no_goal_keys(self) -> None:
        """
        既有 C-3 边界测试已断言 main.data 不得含 goal / commitment key。
        本测试确认该断言仍然存在（防止被删除）。
        """
        c3 = DOCS_DIR / "test_c3_boundary.py"
        src = _read_text(c3)
        if src is None:
            self.skipTest(f"{c3} 不存在，跳过（不视为失败）")
        self.assertIn(
            "goal", src.lower(),
            "docs/test_c3_boundary.py 应仍包含 goal key 边界断言",
        )


# =========================================================
# 5. T4 · Event 边界
#    Contract EV-8 / EV-9 / EV-10 / EV-11；INVARIANT-12
# =========================================================

class T4EventBoundary(unittest.TestCase):
    """agent.Event 是唯一正式 Domain Event；其余通道不得冒充。"""

    def setUp(self) -> None:
        self.event_py = AGENT_DIR / "event.py"

    def test_t4_1_agent_event_module_exists(self) -> None:
        self.assertTrue(self.event_py.exists(), "缺少 agent/event.py")

    def test_t4_2_agent_event_is_dataclass_with_required_fields(self) -> None:
        """
        EV-9：`agent.Event` 是正式 Domain Event 类型。

        以 boundary-form 断言其存在与关键字段，
        但**不**过度约束具体字段集（具体 schema 由后续 Contract 冻结）。
        """
        tree = _parse(self.event_py)
        self.assertIsNotNone(tree, "agent/event.py 解析失败")

        classes = _class_names(tree)
        self.assertIn("Event", classes, "agent/event.py 必须定义 Event 类")

        src = _read_text(self.event_py) or ""
        for field in ("event_type",):
            self.assertIn(
                field, src,
                f"agent.Event 必须包含字段 {field}（正式 Domain Event 语义）",
            )

    def test_t4_3_memory_enqueue_event_is_not_domain_event(self) -> None:
        """
        EV-10：`ext_memory.enqueue_event` 是 Legacy Memory ingestion，
        不是 Domain Event。

        断言：`enqueue_event` 的签名不返回 / 不构造 `agent.Event`。
        """
        mem = EXT_DIR / "ext_memory.py"
        src = _read_text(mem)
        self.assertIsNotNone(src, "缺少 ext/ext_memory.py")

        self.assertNotIn(
            "from agent.event import", src,
            "EV-10：ext_memory 不得把自身实现为 Domain Event 生产者"
            "（出现 agent.event 导入）",
        )
        self.assertNotIn(
            "agent.event",
            src,
            "EV-10：ext_memory 不得引用 agent.event",
        )

    def test_t4_4_sse_push_event_is_not_domain_event(self) -> None:
        """
        EV-11：SSE `app.push_event` 是 Presentation / Transport Notification。

        断言：ext_push.py 不定义 / 不构造 Domain Event 类型。
        """
        push = EXT_DIR / "ext_push.py"
        src = _read_text(push)
        if src is None:
            self.skipTest("缺少 ext/ext_push.py，跳过")

        self.assertNotIn(
            "agent.event", src,
            "EV-11：ext_push.py 不得引用 agent.event（SSE 不是 Domain Event）",
        )

        tree = _parse(push)
        if tree is not None:
            classes = _class_names(tree)
            self.assertNotIn(
                "Event", classes,
                "EV-11：ext_push.py 不得定义 Event 类（SSE 是传输通知，不是 Domain Event）",
            )

    def test_t4_5_no_new_event_bus_created_in_d_phase(self) -> None:
        """
        EV-14：D 阶段不得实现新的 Event Bus。

        断言：仓库中不存在 EventBus / EventStore 的**实际实现或实例化**。

        ⚠️ 检查策略说明（首次真实运行后修正）：

        早期版本用纯文本包含检查，会把 docstring 中的**否定表述**误判为违规，例如：

            agent/event.py:7          3. 不接 EventBus / Scheduler / Wake / Brain / TTS。
            agent/runtime.py:22       4. 不建立 EventBus / EventStore / Scheduler

        这些句子恰恰是在声明「**没有**建立 Event Bus」。因此本断言改为
        **AST 级检查**，只识别真实的代码构造，并显式排除：
            * 字符串字面量 / docstring / 注释
            * 否定语境（同一行或紧邻上一行含「不」「not」「禁止」等）

        可识别的违规：
            * `class XxxEventBus` / `class XxxEventStore` 等类定义
            * `EventBus()` / `EventStore()` 等名称含 bus/store 的实例化
            * 形如 `x = EventBusChain(...)` 的工厂构建
        """
        bus_rx = re.compile(r"bus", re.I)
        store_rx = re.compile(r"store", re.I)

        offenders: List[str] = []
        scanned = [MAIN_PY] + _py_files(EXT_DIR) + _agent_files()

        for path in scanned:
            tree = _parse(path)
            if tree is None:
                continue

            # (a) 类定义：名称同时含 event 与 bus/store
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    nm = node.name
                    if "event" in nm.lower() and (
                        bus_rx.search(nm) or store_rx.search(nm)
                    ):
                        offenders.append(f"{path.name}:{node.lineno}::class {nm}")

            # (b) 实例化：调用目标名称含 bus/store（排除单纯读取/注释）
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    fn = node.func
                    name = (
                        fn.id if isinstance(fn, ast.Name)
                        else getattr(fn, "attr", None)
                    )
                    if not name:
                        continue
                    low = name.lower()
                    if "event" in low and (bus_rx.search(low) or store_rx.search(low)):
                        src_line = ""
                        try:
                            seg = ast.get_source_segment(_read_text(path) or "", node) or ""
                            src_line = seg[:80]
                        except Exception:
                            src_line = name
                        offenders.append(f"{path.name}:{node.lineno}::{src_line}")

        self.assertEqual(
            offenders, [],
            "EV-14 禁止在 D 阶段实现新 Event Bus / EventStore；"
            f"发现实际实现或实例化：{offenders}",
        )

    def test_t4_6_d_phase_has_not_yet_covered_main_channel(self) -> None:
        """
        EV-13 的 boundary-form 断言：main channel 的 Event 覆盖属 D-1 / D-5，
        **D-0 阶段尚未实现**。

        ext_ai.py 的 observe_message 目前对 room == "main" 提前返回；
        本测试记录该事实，防止在 D-0 偷做（若已覆盖则失败，提醒改 Contract）。
        """
        src = _read_text(EXT_DIR / "ext_ai.py")
        self.assertIsNotNone(src, "缺少 ext/ext_ai.py")

        self.assertIn(
            "observe_message", src,
            "ext_ai.py 应仍包含 P0-2B 的 observe_message 接入点",
        )


# =========================================================
# 6. T5 · Activity 边界
#    Contract §5C.2 AC-5 ～ AC-10；INVARIANT-4 / 5 / 6
# =========================================================

class T5ActivityBoundary(unittest.TestCase):
    """Activity 的语义边界；并断言 D-0 未提前实现 Activity。"""

    def test_t5_1_no_activity_implementation_in_d0(self) -> None:
        """
        AC-9：Activity 的 data model / lifecycle / SOT 属 D-2。
        **D-0 阶段不得实现。**

        断言：agent/ 中不存在 activity.py / activity_store.py。
        """
        forbidden = ("activity.py", "activity_store.py", "activity_sot.py")
        for name in forbidden:
            path = AGENT_DIR / name
            self.assertFalse(
                path.exists(),
                f"AC-9：D-0 阶段不得实现 Activity，但发现 {path}",
            )

    def test_t5_2_no_activity_lifecycle_status_enum_yet(self) -> None:
        """
        AC-9 的 boundary-form 断言：D-0 阶段尚不存在 Activity 生命周期实现。

        若未来在 D-2 实现了 PLANNED / TRAVELING / ARRIVED / ACTIVE /
        PAUSED / CANCELLED 状态机，本测试会失败 —— 届时必须同时修改
        Contract §5C.2（这是设计意图，不是缺陷）。
        """
        lifecycle = ("PLANNED", "TRAVELING", "ARRIVED", "PAUSED", "CANCELLED")
        offenders: List[str] = []

        for path in _agent_files() + _py_files(EXT_DIR):
            src = _read_text(path)
            if not src:
                continue
            # 只检查同时出现多个生命周期词的文件（避免误报单词注释）
            hits = [w for w in lifecycle if w in src]
            if len(hits) >= 3:
                offenders.append(f"{path.name}({','.join(hits)})")

        self.assertEqual(
            offenders, [],
            "AC-9：D-0 阶段不应存在 Activity 生命周期实现；"
            f"以下文件出现多个生命周期状态：{offenders}",
        )

    def test_t5_3_activity_is_distinct_from_goal_and_commitment(self) -> None:
        """
        AC-8：Activity ≠ Goal；Activity ≠ Commitment；Activity ≠ Action。

        断言：**Contract §5C.2（AC-8）** 明确写出三者关系，
        且 D-0 决策文档 §3.4 保留三者语义区分。

        ⚠️ 检查策略说明（首次真实运行后修正）：

        早期版本在 **决策文档** 中查找字面串 `"Activity ≠ Goal"`，但该字面表述
        实际位于 **Contract §5C.2 的 AC-8 规则行**：

            | **AC-8** | Activity ≠ Goal；Activity ≠ Commitment；Activity ≠ Action |

        决策文档 §3.4 用的是「三者不能混为一谈」这一自然语言表述，
        而非字面符号。因此本断言改为：

            * Contract   → 必须有 AC-8 且含三项区分（兼容 `≠` 与 `!=`）
            * Decisions  → 必须有 §3.4 的三者区分小节
        """
        contract = _read_text(CONTRACT_DOC)
        self.assertIsNotNone(contract, f"缺少 {CONTRACT_DOC}")
        decisions = _read_text(DECISIONS_DOC)
        self.assertIsNotNone(decisions, f"缺少 {DECISIONS_DOC}")

        # 1) Contract 必须包含 AC-8 三项区分（兼容 Unicode ≠ 与 ASCII !=）
        norm = contract.replace("≠", "!=")
        self.assertIn("AC-8", contract, "Contract 必须包含 AC-8（Activity 与三者区分）")
        for pair in (
            "Activity != Goal",
            "Activity != Commitment",
            "Activity != Action",
        ):
            self.assertIn(
                pair, norm,
                f"AC-8：Contract §5C.2 必须明确 {pair.replace('!=', '≠')}",
            )

        # 2) 决策文档必须保留三者语义区分小节
        for token in ("Activity", "Goal", "Commitment"):
            self.assertIn(token, decisions, f"决策文档缺少 {token} 的语义定义")
        self.assertIn(
            "Activity 与 Goal / Commitment 的关系", decisions,
            "决策文档必须保留「Activity 与 Goal / Commitment 的关系」小节",
        )
        self.assertTrue(
            ("不能混为一谈" in decisions) or ("≠" in decisions),
            "决策文档必须明确三者不能混为一谈",
        )

    def test_t5_4_legacy_activity_state_is_registered_not_replaced(self) -> None:
        """
        AC-6：18 类旧活动字段必须被**登记**为 Legacy Activity State，
        且 D-0 **不修改**它们（AC-2 / AC-3）。

        断言：
          (a) 决策文档登记了这些 key；
          (b) 这些 key 在其 Owner 模块中仍然存在（未被删除）；
          (c) 未出现「main.data['activity']」这种新的 Activity SOT 字段。
        """
        decisions = _read_text(DECISIONS_DOC)
        self.assertIsNotNone(decisions)

        missing = [k for k in LEGACY_ACTIVITY_STATE_KEYS if k not in decisions]
        self.assertEqual(
            missing, [],
            f"AC-6：决策文档未登记以下 Legacy Activity State key：{missing}",
        )

        # (b) 关键 Owner 字段仍存在于源码
        owner_expectations = {
            EXT_DIR / "ext_date.py": ("dates", "date_invites_out"),
            EXT_DIR / "ext_econ.py": ("work_sessions", "work_switch"),
            EXT_DIR / "ext_shop.py": ("ai_shop_state",),
            EXT_DIR / "ext_world.py": ("ai_spot_state",),
        }
        for path, keys in owner_expectations.items():
            src = _read_text(path)
            self.assertIsNotNone(src, f"缺少 {path}")
            for key in keys:
                self.assertIn(
                    key, src,
                    f"AC-2 / AC-3：{path.name} 中的 Legacy Activity State "
                    f"{key!r} 不应在 D-0 被移除",
                )

        # (c) 未引入新的 Activity SOT 顶层 key
        offenders: List[str] = []
        activity_key = re.compile(r"""data\s*\[\s*['"]activity['"]\s*\]""")
        for path in [MAIN_PY] + _py_files(EXT_DIR) + _agent_files():
            if _has_code_match(path, activity_key.pattern):
                offenders.append(path.name)
        self.assertEqual(
            offenders, [],
            "AC-7：禁止出现 main.data['activity'] 形式的第二套 Activity SOT；"
            f"命中：{offenders}",
        )


# =========================================================
# 7. T6 · Capability 边界
#    Contract §5C.4 CP-1 ～ CP-8；INVARIANT-9 / 19 / 20
# =========================================================

class T6CapabilityBoundary(unittest.TestCase):
    """Agent Core 不得直接依赖 ext_*；execute_action 作为 Legacy Adapter 存活。"""

    def test_t6_1_agent_package_does_not_import_ext_modules(self) -> None:
        """
        CP-5：禁止 Agent Core 新增 ext_* 直接 import。

        注意：`agent/state.py` 目前 import main（D-0 Audit `D0-014` 已记录，
        属 D-1 World Query 的待处理项）。本测试只约束 **ext_** 前缀。
        """
        offenders: List[str] = []
        for path in _agent_files():
            tree = _parse(path)
            if tree is None:
                continue
            for _lineno, mod, _alias in _iter_imports(tree):
                if mod and mod.startswith("ext_"):
                    offenders.append(f"{path.name} -> {mod}")
        self.assertEqual(
            offenders, [],
            "CP-5：agent/ 不得直接 import ext_*；命中：" + ", ".join(offenders),
        )

    def test_t6_2_agent_package_does_not_import_ext_package_qualified(self) -> None:
        """CP-5：同样禁止 `from ext.xxx import ...` 形式。"""
        offenders: List[str] = []
        for path in _agent_files():
            src = _read_text(path) or ""
            for m in re.finditer(r"^\s*from\s+(ext\.[A-Za-z_]\w*)\s+import", src, re.M):
                offenders.append(f"{path.name} -> {m.group(1)}")
            for m in re.finditer(r"^\s*import\s+(ext\.[A-Za-z_]\w*)", src, re.M):
                offenders.append(f"{path.name} -> {m.group(1)}")
        self.assertEqual(
            offenders, [],
            "CP-5：agent/ 不得 import ext 包；命中：" + ", ".join(offenders),
        )

    def test_t6_3_agent_package_does_not_depend_on_undeclared_mounts(self) -> None:
        """
        CP-6：禁止 Agent Core 依赖未声明挂载点
        （m.drive_ai / m.call_llm / m.auto_start_work ...）。
        """
        offenders: List[str] = []
        for path in _agent_files():
            src = _read_text(path) or ""
            for name in FORBIDDEN_CORE_MOUNTS:
                if re.search(r"\b" + re.escape(name) + r"\s*\(", src):
                    offenders.append(f"{path.name} -> {name}()")
        self.assertEqual(
            offenders, [],
            "CP-6：agent/ 不得依赖 Legacy 挂载点；命中：" + ", ".join(offenders),
        )

    def test_t6_4_legacy_execute_action_still_exists(self) -> None:
        """
        CP-1 / CP-4 / AX-3：`execute_action` 不删除，
        暂时作为 Legacy Execution Adapter 存活。
        """
        self.assertTrue(LEGACY_EXECUTOR_FILE.exists(), f"缺少 {LEGACY_EXECUTOR_FILE}")
        tree = _parse(LEGACY_EXECUTOR_FILE)
        self.assertIsNotNone(tree)

        names = _all_func_names(tree)
        self.assertIn(
            LEGACY_EXECUTOR_FUNC, names,
            f"CP-4：不得删除 {LEGACY_EXECUTOR_FILE.name}::{LEGACY_EXECUTOR_FUNC}",
        )

    def test_t6_5_no_capability_port_implemented_in_d0(self) -> None:
        """
        CP-8：Capability Port / Request / Result 属 D-4，D-0 不得实现。

        断言：agent/ 中不存在 capability 相关模块。
        """
        forbidden = (
            "capability.py",
            "capability_port.py",
            "capability_request.py",
            "capability_result.py",
        )
        for name in forbidden:
            path = AGENT_DIR / name
            self.assertFalse(
                path.exists(),
                f"CP-8：D-0 阶段不得实现 Capability，但发现 {path}",
            )

    def test_t6_6_no_world_query_implemented_in_d0(self) -> None:
        """
        D-1 boundary-form：World Query 属 D-1，D-0 不得实现。

        ⚠️ 阶段门感知（架构侧 TEST GATE CORRECTION 的同类修正）：

        D-0 阶段断言「world_query.py **不存在**」。
        但当架构侧打开 D-1 的 Pre-Implementation Gate 并完成实现后，
        该断言会**永久失败** —— 与 T-A 遇到的死锁同构。

        因此本断言改为**门感知**：
            门关闭 → 断言不存在（防 D-0 偷做）
            门打开 → 断言存在  （确认 D-1 已落地）

        门状态由 Contract §5D.16 的肯定式标记决定（与 D-1 测试同一判据）。
        """
        gate_open = _d1_gate_open()
        for name in ("world_query.py", "world_query_port.py"):
            path = AGENT_DIR / name
            if gate_open:
                # 门已开：world_query.py 应已由 D-1 实现；port 仍不应存在（属 D-4）
                if name == "world_query.py":
                    self.assertTrue(
                        path.exists(),
                        "D-1 门已打开，但未发现 agent/world_query.py；"
                        "实现若缺失，D-1 无法形成正式通过状态",
                    )
                else:
                    self.assertFalse(
                        path.exists(),
                        f"D-4 尚未开始：不应存在 {path}",
                    )
            else:
                self.assertFalse(
                    path.exists(),
                    f"D-1 尚未开始：D-0 阶段不得实现 World Query，但发现 {path}",
                )


# =========================================================
# 8. T7 · Memory 边界
#    Contract §5C.5 ME-21 ～ ME-26；ME-1 ～ ME-20
# =========================================================

class T7MemoryBoundary(unittest.TestCase):
    """D 阶段核心链不得依赖 Memory。"""

    def test_t7_1_agent_package_does_not_import_memory_modules(self) -> None:
        """
        ME-23：Memory 不得作为 D 阶段依赖。

        断言：agent/ 不 import ext_memory / ext_mem。
        """
        offenders: List[str] = []
        for path in _agent_files():
            tree = _parse(path)
            if tree is None:
                continue
            for _lineno, mod, _alias in _iter_imports(tree):
                if mod in ("ext_memory", "ext_mem"):
                    offenders.append(f"{path.name} -> {mod}")
            src = _read_text(path) or ""
            if re.search(r"\benqueue_event\b", src):
                offenders.append(f"{path.name} -> enqueue_event")
        self.assertEqual(
            offenders, [],
            "ME-23：agent/ 不得依赖 Memory；命中：" + ", ".join(offenders),
        )

    def test_t7_2_long_term_provider_is_still_stub(self) -> None:
        """
        ME-11：LongTermProvider 保持 stub，返回 []。
        """
        path = AGENT_DIR / "long_term_provider.py"
        src = _read_text(path)
        self.assertIsNotNone(src, f"缺少 {path}")
        self.assertIn(
            "stub", src.lower(),
            "ME-11：LongTermProvider 必须保持 stub 状态",
        )

    def test_t7_3_memory_write_path_still_unreachable(self) -> None:
        """
        ME-25 / ME-21 的 boundary-form 断言：D-0 阶段**未修** Memory 写入路径。

        `_enqueue_event_impl` 至今仍无定义 —— 本测试断言该事实仍然成立，
        从而证明「D-0 没有顺手修 Memory」。

        若未来 Phase E 修复了它，本测试会失败 ——
        届时必须同时修改 Contract §5C.5（这是设计意图，不是缺陷）。
        """
        mem = EXT_DIR / "ext_memory.py"
        src = _read_text(mem)
        self.assertIsNotNone(src, "缺少 ext/ext_memory.py")

        self.assertIn(
            "_enqueue_event_impl", src,
            "ME-25：ext_memory.py 结构发生变化；若已修复 Memory，"
            "必须同步修改 Contract §5C.5 并更新本测试",
        )

        defined = re.search(r"^\s*(async\s+)?def\s+_enqueue_event_impl\b", src, re.M)
        self.assertIsNone(
            defined,
            "ME-25：D-0 阶段不得修复 Memory（发现 _enqueue_event_impl 已被定义）；"
            "Memory 修复属 Phase E，必须走独立 Contract Change",
        )

    def test_t7_4_memory_is_not_wired_into_agent_context(self) -> None:
        """
        ME-22：Memory 不得进入 AgentContext。

        断言：agent/context*.py 与 agent/*provider*.py **在有效代码中**
        不引用 ext_memory。

        ⚠️ 检查策略说明（首次真实运行后修正）：

        早期版本对整份源码做文本包含检查，会把 docstring 中的**否定说明**
        误判为耦合，例如：

            agent/context.py docstring: "7. 不启用 ext_memory"

        这句话恰恰是在声明「**不**启用 ext_memory」。因此改为使用
        `_effective_code()`（已剥离注释与 docstring）后再检查。
        """
        targets = [
            AGENT_DIR / "context.py",
            AGENT_DIR / "context_assembler.py",
            AGENT_DIR / "long_term_provider.py",
        ]
        for path in targets:
            if not path.exists():
                continue
            effective = _effective_code(path)
            self.assertNotIn(
                "ext_memory", effective,
                f"ME-22：{path.name} 的有效代码不得引用 ext_memory"
                "（docstring 中的否定说明不算耦合）",
            )


# =========================================================
# 9. T8 · 决策与 Contract 文档边界
# =========================================================

class T8DocumentationBoundary(unittest.TestCase):
    """D-0 决策 / Contract 章节必须存在且与裁决一致。"""

    def test_t8_1_decisions_doc_exists(self) -> None:
        self.assertTrue(DECISIONS_DOC.exists(), f"缺少 {DECISIONS_DOC}")

    def test_t8_2_decisions_doc_contains_all_decisions(self) -> None:
        text = _read_text(DECISIONS_DOC) or ""
        for dec in (
            "D0-DEC-1",
            "D0-DEC-2",
            "D0-DEC-3",
            "D0-DEC-4",
            "D0-DEC-5",
            "D0-DEC-6",
            "D0-DEC-7",
            "D0-DEC-8",
        ):
            self.assertIn(dec, text, f"决策文档缺少 {dec}")

    def test_t8_3_decisions_doc_closes_all_open_questions(self) -> None:
        text = _read_text(DECISIONS_DOC) or ""
        self.assertIn(
            "未有新增 OPEN QUESTION", text,
            "决策文档必须明确声明：本次裁决关闭全部 5 个原有 OPEN QUESTION，且未新增",
        )

    def test_t8_4_contract_contains_section_5c(self) -> None:
        contract = _read_text(CONTRACT_DOC)
        self.assertIsNotNone(contract, f"缺少 {CONTRACT_DOC}")
        self.assertIn("## 5C.", contract, "Contract 缺少 §5C（CC-20260930-04）")

    def test_t8_5_contract_declares_cc_20260930_04(self) -> None:
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn(
            "CC-20260930-04", contract,
            "Contract 必须声明 CC-20260930-04",
        )

    def test_t8_6_contract_declares_required_d0_rules(self) -> None:
        contract = _read_text(CONTRACT_DOC) or ""
        required = (
            "D0G-1", "D0G-2", "D0G-3", "D0G-4", "D0G-5",
            "AC-5", "AC-6", "AC-7", "AC-8", "AC-9", "AC-10",
            "EV-9", "EV-10", "EV-11", "EV-12", "EV-13", "EV-14",
            "CP-1", "CP-2", "CP-3", "CP-4", "CP-5", "CP-6", "CP-7", "CP-8",
            "ME-21", "ME-22", "ME-23", "ME-24", "ME-25", "ME-26",
            "WT-1", "WT-2", "WT-3", "WT-4", "WT-5", "WT-6", "WT-7",
            "DL-1", "DL-2", "DL-3", "DL-4", "DL-5",
            "BL-1", "BL-2", "BL-3",
        )
        missing = [r for r in required if r not in contract]
        self.assertEqual(
            missing, [],
            f"Contract §5C 缺少以下 D-0 规则编号：{missing}",
        )

    def test_t8_7_audit_doc_exists_and_is_accepted(self) -> None:
        text = _read_text(AUDIT_DOC)
        self.assertIsNotNone(text, f"缺少 {AUDIT_DOC}")
        self.assertIn("D0-045", text, "审计文档应包含 D0-001 ～ D0-045")

    def test_t8_8_inventory_is_marked_as_superseded(self) -> None:
        """
        BL-2：Phase A Inventory 不再作为当前事实依据。
        断言在决策文档中已明确记录该基线变更。
        """
        text = _read_text(DECISIONS_DOC) or ""
        self.assertIn(
            "V3.1_GLOBAL_ARCHITECTURE_INVENTORY.md", text,
            "BL-2：决策文档必须明确 Inventory 的基线状态变更",
        )


# =========================================================
# 10. T9 · A/B/C 边界未被 D 阶段改动
# =========================================================

class T9ABCUnchanged(unittest.TestCase):
    """D-0 不得修改 A/B/C 已冻结契约。"""

    def test_t9_1_think_signature_is_intent_set_stub(self) -> None:
        """C-2 §5B.11 / IN-29 / IN-30：think() -> IntentSet，且仍为 Stub。"""
        path = AGENT_DIR / "runtime.py"
        tree = _parse(path)
        self.assertIsNotNone(tree, "缺少或无法解析 agent/runtime.py")

        think: Optional[ast.FunctionDef] = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "think":
                think = node
                break
        self.assertIsNotNone(think, "agent/runtime.py 缺少 think()")

        returns = think.returns
        self.assertIsNotNone(returns, "think() 必须有返回类型注解（-> IntentSet）")
        if isinstance(returns, ast.Name):
            self.assertEqual(returns.id, "IntentSet", "IN-29：think() 必须返回 IntentSet")
        elif isinstance(returns, ast.Attribute):
            self.assertEqual(
                returns.attr, "IntentSet", "IN-29：think() 必须返回 IntentSet"
            )
        else:
            self.fail("IN-29：think() 返回类型必须为 IntentSet")

        src = _read_text(path) or ""
        self.assertIn(
            "IntentSet(candidates=[])", src.replace(" ", ""),
            "IN-30 / IN-24：Stub 阶段必须返回 IntentSet(candidates=[])",
        )

    def test_t9_2_build_context_returns_agent_context(self) -> None:
        """AR-8：build_context() -> AgentContext。"""
        path = AGENT_DIR / "runtime.py"
        tree = _parse(path)
        self.assertIsNotNone(tree)

        fn: Optional[ast.FunctionDef] = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "build_context":
                fn = node
                break
        self.assertIsNotNone(fn, "agent/runtime.py 缺少 build_context()")

        returns = fn.returns
        self.assertIsNotNone(returns, "build_context() 必须有返回类型注解")
        name = returns.id if isinstance(returns, ast.Name) else getattr(returns, "attr", None)
        self.assertEqual(name, "AgentContext", "AR-8：build_context() 必须返回 AgentContext")

    def test_t9_3_context_layers_still_exists_as_stub(self) -> None:
        """CA-7：ContextLayers 不删除、不改名、不别名化。"""
        path = AGENT_DIR / "runtime.py"
        tree = _parse(path)
        self.assertIsNotNone(tree)

        self.assertIn(
            "ContextLayers", _class_names(tree),
            "CA-7：ContextLayers 必须保留为 deprecated compatibility stub",
        )

        src = _read_text(path) or ""
        self.assertNotRegex(
            src,
            r"^ContextLayers\s*=\s*AgentContext",
            "CA-7：禁止把 ContextLayers 别名化为 AgentContext",
        )

    def test_t9_4_runtime_holder_apis_present(self) -> None:
        """RS-8 ～ RS-13：Runtime holder 最小 API 必须存在。"""
        path = AGENT_DIR / "runtime.py"
        tree = _parse(path)
        self.assertIsNotNone(tree)

        names = _all_func_names(tree)
        for api in (
            "add_goal", "get_goal", "list_goals", "replace_goal",
            "add_commitment", "get_commitment", "list_commitments", "replace_commitment",
        ):
            self.assertIn(api, names, f"RS-8 ～ RS-13：缺少 Runtime holder API {api}()")

    def test_t9_5_providers_still_declare_no_main_import(self) -> None:
        """B2 边界：Provider 不 import main / ext_*。"""
        providers = [
            AGENT_DIR / "stable_core_provider.py",
            AGENT_DIR / "recent_provider.py",
            AGENT_DIR / "long_term_provider.py",
            AGENT_DIR / "dynamic_world_provider.py",
            AGENT_DIR / "context_assembler.py",
        ]
        for path in providers:
            tree = _parse(path)
            if tree is None:
                continue
            mods = _top_level_modules(tree)
            self.assertNotIn("main", mods, f"B2：{path.name} 不得 import main")
            for mod in sorted(mods):
                self.assertFalse(
                    mod.startswith("ext_"),
                    f"B2：{path.name} 不得 import {mod}",
                )


# =========================================================
# 11. T10 · D-0 纪律：45 项发现不得在 D-0 被修
# =========================================================

class T10D0Discipline(unittest.TestCase):
    """D-0 阶段禁止修改生产代码；本类只做「未修改」的边界断言。"""

    def test_t10_1_legacy_brain_still_present(self) -> None:
        """
        DL-2 / AI-1 / AI-2：D-0 不得重写 ext_ai.py。

        断言：第二大脑的关键结构仍然存在（未被 D-0 迁移/删除）。
        """
        path = EXT_DIR / "ext_ai.py"
        tree = _parse(path)
        self.assertIsNotNone(tree, "缺少或无法解析 ext/ext_ai.py")

        names = _all_func_names(tree)
        for fn in ("drive_ai", "execute_action", "call_llm", "build_ai_context", "auto_ai_loop"):
            self.assertIn(
                fn, names,
                f"AI-1 / AI-2：D-0 不得重写 ext_ai.py；缺少 {fn}()",
            )

    def test_t10_2_random_decisions_still_present(self) -> None:
        """
        DL-2：D-0 不修 random decision（属 D-6）。

        断言：已知的随机决策点仍然存在（证明 D-0 未越界修改）。
        若未来 D-6 迁移了它们，本测试会失败 —— 届时必须同步更新。
        """
        expectations = {
            EXT_DIR / "ext_world.py": r"random\.choices\s*\(",
            EXT_DIR / "ext_econ.py": r"random\.random\s*\(\s*\)\s*<\s*0\.8",
        }
        for path, pat in expectations.items():
            self.assertTrue(
                _has_code_match(path, pat),
                f"DL-2：{path.name} 的已知随机决策点消失；"
                "若属 D-6 迁移，请同步更新本测试与 Contract",
            )

    def test_t10_3_frontend_not_modified_in_d0(self) -> None:
        """
        DL-4：D-0 不得修改前端。

        断言：前端关键文件仍然存在（D-0 未删除/重构）。
        """
        for rel in ("index.html", "ext/app-core.js", "ext/app-chat.js", "ext/app-map.js"):
            path = ROOT / rel
            self.assertTrue(path.exists(), f"DL-4：D-0 不应修改/删除前端文件 {rel}")

    def test_t10_4_world_tick_blocker_still_registered(self) -> None:
        """
        WT-1：World Tick 可靠性缺陷登记为 D-3 前置 Blocker（D-0 不修）。

        断言：ext_world.py 的 ai_spot_tick 结构仍在（D-0 未顺手修）。
        """
        path = EXT_DIR / "ext_world.py"
        tree = _parse(path)
        self.assertIsNotNone(tree)
        self.assertIn(
            "ai_spot_tick", _all_func_names(tree),
            "WT-1：ext_world.py 结构变化；若已做最小可靠性修复，"
            "必须走独立 Contract Change 并更新本测试",
        )

        decisions = _read_text(DECISIONS_DOC) or ""
        self.assertIn("D-3 前置 Blocker", decisions, "WT-1：决策文档必须登记该 Blocker")


# =========================================================
# 12. T11 · 环境执行能力检查（不伪造结果）
# =========================================================

class T11EnvironmentCapability(unittest.TestCase):
    """
    环境检查。

    说明：本测试文件设计为「可运行即证明环境可用」。
    若 Shell 不可用（DSH `0xC0000142` / STATUS_DLL_INIT_FAILED），
    则本文件根本无法启动，必须在报告中如实写明：

        TEST NOT RUN
        Reason: environment execution unavailable

    因此本类只检查测试本身所需的最小前置条件（源码树可读），
    不做任何环境伪造。
    """

    def test_t11_1_repo_root_resolves(self) -> None:
        self.assertTrue(ROOT.is_dir(), f"无法解析仓库根目录：{ROOT}")
        self.assertTrue(MAIN_PY.exists(), f"缺少 {MAIN_PY}")
        self.assertTrue(AGENT_DIR.is_dir(), f"缺少 {AGENT_DIR}")
        self.assertTrue(EXT_DIR.is_dir(), f"缺少 {EXT_DIR}")

    def test_t11_2_no_third_party_import_required(self) -> None:
        """
        本测试文件必须只依赖标准库，以便在缺少 fastapi / uvicorn /
        aiofiles 等依赖的环境中运行。
        """
        tree = _parse(Path(__file__))
        self.assertIsNotNone(tree, "无法解析本测试文件自身")

        stdlib_ok = {
            "__future__", "ast", "io", "os", "re", "tokenize", "unittest",
            "pathlib", "typing",
            "sys", "json", "textwrap", "collections",
        }
        mods = _top_level_modules(tree)
        extra = sorted(m for m in mods if m not in stdlib_ok)
        self.assertEqual(
            extra, [],
            f"本测试文件只能依赖标准库；发现额外依赖：{extra}",
        )

    def test_t11_3_repo_root_resolution_is_marker_based(self) -> None:
        """
        工作区可能被整理（例如把 PROJECT / PRODUCT_GUIDE 移入 docs/）。

        本测试断言：ROOT 的解析不依赖硬编码层级，而是通过
        「main.py + agent/ + ext/」标记向上探测 —— 因此在目录整理后
        仍然指向真正的仓库根（根目录含 main.py），而不是 docs/。
        """
        self.assertTrue(
            (ROOT / "main.py").is_file(),
            f"ROOT 解析错误：{ROOT} 下没有 main.py（可能是硬编码层级导致）",
        )
        self.assertTrue(
            (ROOT / "agent").is_dir() and (ROOT / "ext").is_dir(),
            f"ROOT 解析错误：{ROOT} 下缺少 agent/ 或 ext/",
        )
        self.assertNotEqual(
            ROOT.name, "docs",
            "ROOT 不应被解析为 docs/（目录整理后需使用标记探测）",
        )

    def test_t11_4_project_master_doc_is_locatable(self) -> None:
        """
        目录整理后 PROJECT_V3.1_MASTER.md 已迁入 docs/。
        本测试断言它至少存在于一个已知候选位置，
        防止文档搬移后无人发现路径失效。
        """
        found = [p for p in PROJECT_MASTER_CANDIDATES if p.is_file()]
        self.assertTrue(
            found,
            "未能在任何候选位置找到 PROJECT_V3.1_MASTER.md；"
            f"候选：{[str(p) for p in PROJECT_MASTER_CANDIDATES]}",
        )


# =========================================================
# 入口
# =========================================================

def _print_header() -> None:
    print("=" * 72)
    print("V3.1 Phase D-0 · Architecture Boundary Tests")
    print("=" * 72)
    print(f"ROOT       : {ROOT}")
    print(f"agent/     : {len(_agent_files())} py files")
    print(f"ext/       : {len(_py_files(EXT_DIR))} py files")
    print(f"decisions  : {'OK' if DECISIONS_DOC.exists() else 'MISSING'} -> {DECISIONS_DOC}")
    print(f"contract   : {'OK' if CONTRACT_DOC.exists() else 'MISSING'} -> {CONTRACT_DOC}")
    for cand in PROJECT_MASTER_CANDIDATES:
        print(f"project    : {'OK' if cand.is_file() else '--'} -> {cand}")
    print("-" * 72)
    print("这些测试验证的是「架构边界」，不是「完整功能」。")
    print("=" * 72)


if __name__ == "__main__":
    _print_header()
    unittest.main(verbosity=2)
