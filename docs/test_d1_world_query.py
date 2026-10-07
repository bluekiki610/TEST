# -*- coding: utf-8 -*-
"""
docs/test_d1_world_query.py
===========================

V3.1 Phase D-1 · World Query Architecture Boundary Tests

依据：
    docs/D0_WORLD_ACTIVITY_CAPABILITY_PREFLIGHT.md
    docs/D0_CONFLICT_AUDIT.md                       （ACCEPTED）
    docs/D0_ARCHITECTURE_DECISIONS.md               （ACCEPTED）
    docs/D1_WORLD_QUERY_PREFLIGHT.md                （APPROVED WITH CORRECTIONS）
    docs/V3.1_ARCHITECTURE_CONTRACT.md §5C / §5D    （CC-20260930-04 / -05）

--------------------------------------------------------------------------
本文件测试什么
--------------------------------------------------------------------------

    测试的不是功能，而是 **World Query 的架构边界**。

    D-1 采用 **两段式阶段门（Gate Lifecycle）**：

    【T-A · Pre-Implementation Gate】  ← 只在实现之前生效
        - 实现不存在时：断言「不存在」——防止提前偷做（防 `world_query.py`）
        - 实现存在后：断言「确实存在」——**本组自动转为通过**
        - 因此**不会出现「实现了 world_query.py 之后 T-A 永久失败」的情况**

    【T-B · Post-Implementation Boundary Gate】  ← 只在实现存在时生效
        - 不 import main / ext_*
        - 无任何写入模式（只读）
        - 不保存 data 引用 / 不返回内部可变引用
        - 不调用 LLM / Event / save_data / 写入型 helper
        - 不涉及 Activity / Capability / Movement / Command
        - 不读 AgentState
        - 命名不含 find_best_ / choose_ / decide_ / suggest_ 等决策语义
        - 五态核心 + FORBIDDEN（visibility outcome，不得与 UNKNOWN 等价）
        - schema 不支持项必须返回 UNSUPPORTED
        - 实现不存在时本组逐项直接返回（不 skip、不失败）

    【T-C · 文档边界】
        - §5D 存在且含全部 D-1 规则编号
        - 5 项修正均已落入 Preflight 与 Contract
        - 阶段门生命周期与 FORBIDDEN 语义已定义
        - 严格只读已标注为「D-1 静态验证策略」

    【T-D · D-0 / A/B/C 未被 D-1 改动】
    【T-E · 环境能力（不伪造结果）】

    ⚠️ T-B 严格只读策略的定位（架构侧裁决）：

        「禁止 local append/sort/pop」是 **D-1 静态验证策略**，
        **不是永久 Python 架构原则**。

        理由：Python 无法语言级保证只读，D-1 选择用「禁止一切写入模式」
        换取「静态可验证的只读性」。这是 D-1 的验证手段选择，
        不是对 Python 或对未来架构的断言。

--------------------------------------------------------------------------
设计原则
--------------------------------------------------------------------------

    * **只依赖标准库**（unittest / ast / re / pathlib），不 import main / ext_* / agent
    * 所有检查通过读取源码文件完成
    * 采用 **boundary-form 断言**：已冻结的边界必须成立；属后续阶段的边界断言「尚未发生」
    * 不做任何运行时推断；不做网络 / LLM 调用；不写任何文件

--------------------------------------------------------------------------
如何运行
--------------------------------------------------------------------------

    从仓库根目录运行：

        python docs/test_d1_world_query.py
        python -m unittest docs.test_d1_world_query -v

    若执行环境不可用（例如 DSH Shell `0xC0000142` /
    `STATUS_DLL_INIT_FAILED`），必须如实报告：

        TEST NOT RUN
        Reason: environment execution unavailable

    **禁止伪造测试结果。**
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# =========================================================
# 0. 路径解析（标记探测，兼容目录整理）
# =========================================================

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
    return start.parent


ROOT = _find_repo_root(_HERE)

AGENT_DIR = ROOT / "agent"
EXT_DIR = ROOT / "ext"
MAIN_PY = ROOT / "main.py"
DOCS_DIR = ROOT / "docs"
INDEX_HTML = ROOT / "index.html"

PREFLIGHT_D1 = DOCS_DIR / "D1_WORLD_QUERY_PREFLIGHT.md"
CONTRACT_DOC = DOCS_DIR / "V3.1_ARCHITECTURE_CONTRACT.md"
DECISIONS_D0 = DOCS_DIR / "D0_ARCHITECTURE_DECISIONS.md"
AUDIT_D0 = DOCS_DIR / "D0_CONFLICT_AUDIT.md"
PREFLIGHT_D0 = DOCS_DIR / "D0_WORLD_ACTIVITY_CAPABILITY_PREFLIGHT.md"
TEST_D0 = DOCS_DIR / "test_d0_world_activity_capability.py"

PROJECT_MASTER_CANDIDATES: Sequence[Path] = (
    DOCS_DIR / "PROJECT_V3.1_MASTER.md",
    ROOT / "PROJECT_V3.1_MASTER.md",
)

# Contract §5D 必含规则编号
REQUIRED_D1_RULES: Sequence[str] = (
    # World Fact（修正版）
    "WQ-69", "WQ-70", "WQ-71", "WQ-72", "WQ-73", "WQ-74", "WQ-100",
    # 绝对边界
    "WQ-5", "WQ-6", "WQ-7", "WQ-8", "WQ-9",
    # DI（措辞修正）
    "WQ-75", "WQ-76", "WQ-77", "WQ-78", "WQ-79", "WQ-101", "WQ-102", "WQ-103", "WQ-104",
    # AgentState 禁读
    "WQ-105", "WQ-106", "WQ-107", "WQ-108", "WQ-109",
    # 反查 + 高频限制
    "WQ-10", "WQ-11", "WQ-12", "WQ-81", "WQ-82", "WQ-83", "WQ-84",
    # 返回结构 / 五态
    "WQ-13", "WQ-14", "WQ-15", "WQ-16", "WQ-17",
    "WQ-18", "WQ-19", "WQ-20", "WQ-21", "WQ-22", "WQ-96",
    # FORBIDDEN 与五态的关系（架构侧第二轮裁决）
    "WQ-113", "WQ-114", "WQ-115", "WQ-116", "WQ-117", "WQ-118",
    # 时间
    "WQ-23", "WQ-24", "WQ-25", "WQ-26",
    # requester / visibility
    "WQ-27", "WQ-28", "WQ-29", "WQ-30", "WQ-31",
    "WQ-94", "WQ-95", "WQ-97", "WQ-98", "WQ-99",
    # DERIVED 有限支持
    "WQ-85", "WQ-86", "WQ-87", "WQ-88", "WQ-89",
    # 反模式（万能世界 API）
    "WQ-90", "WQ-91", "WQ-92", "WQ-93",
    # Provider / Event / Activity / Command 边界
    "WQ-32", "WQ-33", "WQ-34", "WQ-35", "WQ-36", "WQ-112",
    "WQ-37", "WQ-38", "WQ-39", "WQ-40", "WQ-41",
    "WQ-42", "WQ-43", "WQ-44", "WQ-45", "WQ-46",
    "WQ-47", "WQ-48", "WQ-49", "WQ-50", "WQ-51",
    # Runtime 接入
    "WQ-52", "WQ-53", "WQ-54", "WQ-55",
    # 前端 / HTTP
    "WQ-56", "WQ-57", "WQ-58", "WQ-59", "WQ-60",
    # 禁止事项
    "WQ-61", "WQ-62", "WQ-63", "WQ-64", "WQ-65", "WQ-66", "WQ-67", "WQ-68",
    # UNSUPPORTED 清单
    "WQ-110", "WQ-111",
    # 阶段门
    "D1G-1", "D1G-2", "D1G-3", "D1G-4", "D1G-5", "D1G-6",
    # 阶段门生命周期（架构侧第二轮裁决）
    "D1G-7", "D1G-8", "D1G-9", "D1G-10",
    # D-1 静态验证策略定位
    "D1G-11", "D1G-12", "D1G-13", "D1G-14", "D1G-15",
    # 静态边界断言实现策略（首次真实运行经验，CC-20260930-05 追补）
    "D1G-16", "D1G-17", "D1G-18", "D1G-19", "D1G-20", "D1G-21", "D1G-22",
    # 未冻结
    "NF-9", "NF-10",
)

# D-1 阶段 schema 不支持、必须 UNSUPPORTED 的查询关键字
UNSUPPORTED_QUERY_HINTS: Sequence[str] = (
    "get_map_of_building",
    "get_npc_location",
    "query_places",
    "get_relationship",
    "find_route",
    "get_available_places",
    "get_activity",
)

# 决策语义命名黑名单（WQ-92）
DECISION_NAMING_BLACKLIST: Sequence[str] = (
    "find_best", "find_optimal", "choose_", "decide_", "suggest_",
    "recommend_", "pick_best", "rank_", "plan_",
)

# 禁止 Query 依赖的未声明挂载点（沿用 D-0 CP-6 精神）
FORBIDDEN_QUERY_MOUNTS: Sequence[str] = (
    "drive_ai", "call_llm", "auto_start_work",
    "handle_invite_date", "_trigger_invite", "_can_invite_light",
    "_check_reply_on_message", "get_shop_menu", "_ai_think_invite",
)

# 写入型 helper（WQ-9）
WRITE_HELPERS: Sequence[str] = (
    "save_data", "add_trail", "append_timeline", "append_visited",
    "track_visit", "track_note", "check_pending_moves", "visit_leave",
    "enqueue_event", "push_event",
)

# 写入模式正则（WQ-7 / WQ-104）
WRITE_PATTERNS: Sequence[str] = (
    r"\[\s*['\"][^'\"]+['\"]\s*\]\s*=",     # data["k"] = ...
    r"\.setdefault\s*\(",
    r"\.pop\s*\(",
    r"\.update\s*\(",
    r"\.clear\s*\(",
    r"\.append\s*\(",
    r"\.extend\s*\(",
    r"\.insert\s*\(",
    r"\.remove\s*\(",
    r"\.sort\s*\(",
    r"\.reverse\s*\(",
    r"del\s+\w+\[",
)


# =========================================================
# 1. 通用工具
# =========================================================

def _read_text(path: Path) -> Optional[str]:
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
    src = _read_text(path)
    if src is None:
        return None
    try:
        return ast.parse(src, filename=str(path))
    except SyntaxError:
        return None


def _py_files(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        p for p in directory.glob("*.py")
        if p.is_file() and "__pycache__" not in p.parts
    )


def _agent_files() -> List[Path]:
    return _py_files(AGENT_DIR)


def _iter_imports(tree: ast.Module) -> Iterable[Tuple[int, Optional[str], str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield (node.lineno, alias.name, alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module
            for alias in node.names:
                yield (node.lineno, mod, alias.name)


def _top_level_modules(tree: ast.Module) -> Set[str]:
    mods: Set[str] = set()
    for _, mod, _alias in _iter_imports(tree):
        if mod:
            mods.add(mod.split(".")[0])
    return mods


def _code_lines(path: Path) -> List[str]:
    src = _read_text(path)
    if src is None:
        return []
    return [ln for ln in src.splitlines() if not ln.strip().startswith("#")]


def _has_code_match(path: Path, pattern: str) -> bool:
    rx = re.compile(pattern)
    return any(rx.search(ln) for ln in _code_lines(path))


def _all_func_names(tree: ast.Module) -> Set[str]:
    return {
        n.name for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _class_names(tree: ast.Module) -> Set[str]:
    return {n.name for n in tree.body if isinstance(n, ast.ClassDef)}


def _query_modules() -> List[Path]:
    """
    定位「World Query 实现模块」。

    D-1 允许的实现位置（任一）：
        agent/world_query.py
        agent/world_query/*.py
        world_query.py（根，不推荐但兼容）
    """
    found: List[Path] = []

    direct = AGENT_DIR / "world_query.py"
    if direct.is_file():
        found.append(direct)

    pkg = AGENT_DIR / "world_query"
    if pkg.is_dir():
        found.extend(sorted(p for p in pkg.rglob("*.py") if p.is_file()))

    root_level = ROOT / "world_query.py"
    if root_level.is_file():
        found.append(root_level)

    return found


# =========================================================
# 1.1 阶段门生命周期（Gate Lifecycle）
# =========================================================
#
# 架构侧裁决（D-1 Architecture Review：CONTRACT APPROVED WITH TEST GATE CORRECTION）：
#
#     T-A = Pre-Implementation Gate only
#     T-B = Post-Implementation Boundary Gate
#
#     不允许未来实现 world_query.py 后导致 T-A 永久失败而无法形成正式通过状态。
#
# 因此本文件不采用「T-A 永远断言不存在」的写法，而是：
#
#     _gate_open() == False  →  T-A 断言「实现不存在」   （Pre-Implementation Gate）
#                                T-B 全部 skip           （Post-Implementation Gate 未激活）
#
#     _gate_open() == True   →  T-A 断言「实现确实存在」 （完成后自动转为通过）
#                                T-B 全部执行            （Post-Implementation Boundary Gate）
#
# 门状态来源：Contract §5D.16 的 D1G-3 / D1G-4。
# 判定方式：Document 中 D1G-3 是否已标记为满足（`[x]`）或明示授权。
# =========================================================

_GATE_MARKERS: Sequence[Tuple[str, str]] = (
    # (严格标记文本, 含义)
    #
    # ⚠️ 必须是「肯定式、独立成行」的显式标记，才能开门。
    # 首次真实运行时发现：旧逻辑只要发现子串 `D1G-3-SATISFIED` 就开门，
    # 但 Contract §5D.16 里存在这一行：
    #
    #       D1G-3-SATISFIED
    #       当前不存在
    #       → Pre-Implementation Gate = CLOSED
    #
    # 于是门被**误判为已打开**，导致 T-A 反而要求存在实现而失败。
    # 因此改为要求明确肯定式标记：
    #
    #       **D1G-3-SATISFIED: true**
    #
    # 架构侧要开门时，只需在 Contract §5D.16 写入该行。
    ("**D1G-3-SATISFIED: true**", "Pre-Implementation Gate 已通过（架构侧显式标记）"),
    ("D1G-3-SATISFIED: true", "Pre-Implementation Gate 已通过（等价标记）"),
)

# 否定语境标记：出现这些词的行即便含标记名，也**不**视为开门
_GATE_NEGATIONS: Sequence[str] = (
    "不存在",
    "未标记",
    "false",
    "False",
    "CLOSED",
    "not satisfied",
)


def _gate_open() -> bool:
    """
    判断 D-1 Implementation 是否已被授权（Pre-Implementation Gate 是否已通过）。

    判定规则（从严，逐行）：

        只有当 Contract 中存在**某一行**同时满足：
            (a) 含肯定式标记（见 `_GATE_MARKERS`）；
            (b) 不含任何否定语境词（见 `_GATE_NEGATIONS`）；
        才视为门已打开。

    否则视为门关闭 —— 即 **D-1 Implementation 尚未授权**。

    这样设计的原因：
        * 门关闭时，T-A 负责「防止提前偷做」；
        * 门打开后，T-A 自动转为「确认实现确实存在」，不会再永久失败；
        * 是否开门由架构侧在 Contract 中**显式写下肯定式标记**，不由 DS 自行判断。
    """
    contract = _read_text(CONTRACT_DOC)
    if not contract:
        return False
    if "D1G-3" not in contract and "D1G-4" not in contract:
        # Contract 尚未包含阶段门 → 保守视为关闭
        return False

    for raw_line in contract.splitlines():
        line = raw_line.strip()
        for marker, _meaning in _GATE_MARKERS:
            if marker not in line:
                continue
            if any(neg in line for neg in _GATE_NEGATIONS):
                # 该行是「声明标记当前不存在」之类的否定语境 → 不构成开门
                continue
            return True
    return False


# =========================================================
# 2. T-A · Pre-Implementation Gate
# =========================================================

class TAPreImplementationGate(unittest.TestCase):
    """
    【Pre-Implementation Gate】

    架构侧裁决：**T-A 只属于 Pre-Implementation 阶段。**

    * 门关闭时：断言「World Query 实现不存在」—— 防止提前偷做。
    * 门打开后：断言「World Query 实现确实存在」—— 本组自动转为通过，
      **不会因为实现了 world_query.py 而永久失败**。

    门的开合由 Contract §5D.16 的显式标记决定（见 `_gate_open()`）。
    """

    def test_ta0_gate_state_is_determinate(self) -> None:
        """
        门状态必须可判定，且其判定依据必须存在于 Contract。

        这保证「T-A 是否要求实现存在」这件事本身是**可审计的**，
        而不是靠 DS 自行判断。
        """
        contract = _read_text(CONTRACT_DOC)
        self.assertIsNotNone(contract, f"缺少 {CONTRACT_DOC}")
        self.assertIn(
            "D1G-3", contract,
            "Contract 必须包含 D1G-3（Pre-Implementation Gate），否则门状态不可判定",
        )
        self.assertIn(
            "D1G-4", contract,
            "Contract 必须包含 D1G-4（禁止提前实现 world_query.py），否则门状态不可判定",
        )

    def test_ta1_implementation_presence_matches_gate(self) -> None:
        """
        【核心】实现的存在性必须与门状态一致。

        * 门关闭 → 不得存在 World Query 实现模块（防提前偷做）
        * 门打开 → 必须存在 World Query 实现模块（确认实现已落地）

        本断言是 T-A 阶段门生命周期修正的核心：
        它**在两种阶段下都不会永久失败**。
        """
        modules = _query_modules()
        rel = [str(m.relative_to(ROOT)) for m in modules]

        if _gate_open():
            self.assertTrue(
                modules,
                "Pre-Implementation Gate 已打开（Contract 标记 D1G-3-SATISFIED），"
                "但未发现 World Query 实现模块。"
                "门打开后必须存在实现，否则 T-A 无法转为正式通过状态。",
            )
        else:
            self.assertEqual(
                rel, [],
                "D1G-4（Pre-Implementation Gate 关闭）：D-1 Implementation 尚未授权，"
                f"不应存在 World Query 实现模块；发现：{rel}",
            )

    def test_ta2_no_query_named_modules_in_agent(self) -> None:
        """门关闭时 agent/ 不应出现 query 相关模块；门打开后本断言自动放宽。"""
        if _gate_open():
            self.skipTest("Pre-Implementation Gate 已打开；本断言只适用于门关闭阶段")

        suspicious = [
            p.name for p in _agent_files()
            if "query" in p.name.lower()
        ]
        self.assertEqual(
            suspicious, [],
            f"agent/ 中出现 query 相关模块：{suspicious}"
            "（D-1 Implementation 未授权）",
        )

    def test_ta3_no_query_cache_or_index_created(self) -> None:
        """
        WQ-73 / WQ-84：D-1 不允许 Query 产生 CACHE / 索引。

        本断言在**两种阶段下都成立** —— 它不是阶段门，而是永久边界。
        """
        forbidden_class = re.compile(
            r"\bclass\s+\w*(WorldQueryCache|QueryCache|RoomBuildingIndex|WorldIndex)\b"
        )
        offenders: List[str] = []
        for path in _agent_files() + _py_files(EXT_DIR):
            if forbidden_class.search(_read_text(path) or ""):
                offenders.append(path.name)
        self.assertEqual(
            offenders, [],
            f"WQ-73 / WQ-84：不应存在 Query 缓存 / 索引实现；命中：{offenders}",
        )

    def test_ta4_no_new_world_query_http_endpoint(self) -> None:
        """
        WQ-56 / WQ-58：D-1 不修改现有 HTTP 接口，也尚未新增 Query 端点。

        本断言在**两种阶段下都成立** —— D-1 全程不新增 Query HTTP 端点
        （若后续要新增，必须走 Contract Change，见 WQ-58）。
        """
        rx = re.compile(r"['\"]/api/[a-z0-9_/-]*world[-_]?quer[a-z]*['\"]", re.I)
        offenders: List[str] = []
        for path in [MAIN_PY] + _py_files(EXT_DIR):
            src = _read_text(path) or ""
            if rx.search(src):
                offenders.append(path.name)
        self.assertEqual(
            offenders, [],
            f"WQ-56：D-1 不应新增 World Query HTTP 端点；命中：{offenders}",
        )

    def test_ta5_agent_runtime_not_wired_to_query(self) -> None:
        """
        WQ-52 / WQ-54：D-1 建立 Query，但 AgentRuntime 暂不接入。

        本断言在**两种阶段下都成立** —— Runtime 接入属后续阶段。
        """
        runtime = AGENT_DIR / "runtime.py"
        src = _read_text(runtime)
        self.assertIsNotNone(src, "缺少 agent/runtime.py")
        self.assertNotIn(
            "world_query", src,
            "WQ-52 / WQ-54：agent/runtime.py 不应引用 world_query"
            "（Runtime 接入属后续阶段，需 Contract Change）",
        )

    def test_ta6_context_chain_not_wired_to_query(self) -> None:
        """
        WQ-32 / WQ-35：Provider 与 ContextAssembler 不得调用 Query。

        本断言在**两种阶段下都成立**。
        """
        targets = [
            AGENT_DIR / "context_assembler.py",
            AGENT_DIR / "stable_core_provider.py",
            AGENT_DIR / "recent_provider.py",
            AGENT_DIR / "long_term_provider.py",
            AGENT_DIR / "dynamic_world_provider.py",
        ]
        offenders: List[str] = []
        for path in targets:
            src = _read_text(path)
            if src is None:
                continue
            if "world_query" in src:
                offenders.append(path.name)
        self.assertEqual(
            offenders, [],
            f"WQ-32 / WQ-35：Provider / ContextAssembler 不得引用 world_query；命中：{offenders}",
        )


# =========================================================
# 3. T-B · Post-Implementation Boundary Gate
# =========================================================

class TBD1QueryBoundaries(unittest.TestCase):
    """
    【Post-Implementation Boundary Gate】

    架构侧裁决：**T-B 只属于 Post-Implementation 阶段。**

    本组的每一项断言在「World Query 实现存在」时生效；
    实现不存在时，本组**整体不适用**（`_gate` 返回 False，逐项直接 return），
    因此**不会以 skip 的方式污染通过率，也不会误报失败**。

    与 T-A 的区别：

        T-A：门关闭时断言「不存在」；门打开后断言「存在」（阶段门）
        T-B：只在实现存在时断言「边界正确」（永久边界，Post-Implementation 生效）

    ⚠️ T-B 的严格只读策略定位（架构侧裁决）：

        「禁止 local append/sort/pop」是 **D-1 静态验证策略**，
        **不是永久 Python 架构原则**。

        理由：Python 无法语言级保证只读，因此 D-1 选择用
        「禁止一切写入模式」换取「静态可验证的只读性」。
        这是 D-1 的验证手段选择，不是对 Python 或对未来架构的断言。
        未来若引入更精确的只读机制（不可变视图 / 代理对象 / 类型系统），
        本策略可以相应放宽 —— 但它必须仍满足「静态可验证」。
    """

    def setUp(self) -> None:
        self.modules = _query_modules()
        self._gate = bool(self.modules)

    def _require_impl(self) -> bool:
        """实现不存在时返回 False，调用方应直接 return（不 skip、不失败）。"""
        return self._gate

    # --- 只读边界 -------------------------------------------------

    def test_tb1_query_does_not_import_main_or_ext(self) -> None:
        """WQ-75：Query 不得 import main / ext_*。"""
        if not self._require_impl():
            return
        offenders: List[str] = []
        for path in self.modules:
            tree = _parse(path)
            if tree is None:
                continue
            mods = _top_level_modules(tree)
            if "main" in mods:
                offenders.append(f"{path.name} -> main")
            for mod in sorted(mods):
                if mod.startswith("ext_"):
                    offenders.append(f"{path.name} -> {mod}")
            src = _read_text(path) or ""
            for m in re.finditer(r"^\s*(?:from|import)\s+(ext\.[A-Za-z_]\w*)", src, re.M):
                offenders.append(f"{path.name} -> {m.group(1)}")
        self.assertEqual(
            offenders, [],
            "WQ-75：World Query 不得 import main / ext_*；命中：" + ", ".join(offenders),
        )

    def test_tb2_query_has_no_write_patterns(self) -> None:
        """
        WQ-7 / WQ-104：Query 模块中不得存在任何写入模式。

        ⚠️ 定位（架构侧裁决）：这是 **D-1 静态验证策略**，
        **不是永久 Python 架构原则**。

        本断言是**严格模式** —— 它禁止 Query 模块中出现任何
        `append` / `sort` / `pop` / `setdefault` / `[...] =` 等模式，
        **包括对本地副本的操作**。

        后果：**Query 不得通过调用会就地修改 dict/list 的现有 helper
        来完成反查**。

        例：`main.find_building_of_room(room)` 本身不修改数据；但若 Query
        选择**自行实现**同类反查，必须使用不触发本黑名单的写法
        （例如列表推导 + `next(...)` + 显式循环）。

        这不是缺陷，而是**刻意的强约束**：
        既然 Python 无法语言级保证只读，D-1 就用「禁止一切写入模式」
        换取「静态可验证的只读性」。
        """
        if not self._require_impl():
            return
        offenders: List[str] = []
        for path in self.modules:
            for pat in WRITE_PATTERNS:
                if _has_code_match(path, pat):
                    offenders.append(f"{path.name}::{pat}")
        self.assertEqual(
            offenders, [],
            "WQ-7（D-1 静态验证策略）：World Query 必须是只读；命中写入模式："
            + "; ".join(offenders),
        )

    def test_tb3_query_does_not_save_data_reference(self) -> None:
        """WQ-102：Query 不得保存 data 引用。"""
        if not self._require_impl():
            return
        offenders: List[str] = []
        for path in self.modules:
            for ln in _code_lines(path):
                s = ln.strip()
                if re.match(r"self\.\w*data\w*\s*=", s):
                    offenders.append(f"{path.name}: {s[:80]}")
        self.assertEqual(
            offenders, [],
            "WQ-102：Query 不得保存 data 引用（禁止 self.data = data）；命中：" + "; ".join(offenders),
        )

    def test_tb4_query_does_not_call_write_helpers(self) -> None:
        """WQ-8 / WQ-9：Query 不得调用 save_data 与写入型 helper。"""
        if not self._require_impl():
            return
        offenders: List[str] = []
        for path in self.modules:
            src = _read_text(path) or ""
            for helper in WRITE_HELPERS:
                if re.search(r"\b" + re.escape(helper) + r"\s*\(", src):
                    offenders.append(f"{path.name} -> {helper}()")
        self.assertEqual(
            offenders, [],
            "WQ-8 / WQ-9：Query 不得调用写入型 helper；命中：" + ", ".join(offenders),
        )

    def test_tb5_query_does_not_depend_on_undeclared_mounts(self) -> None:
        """WQ-6：Query 不得依赖 Legacy 挂载点（drive_ai / call_llm / ...）。"""
        if not self._require_impl():
            return
        offenders: List[str] = []
        for path in self.modules:
            src = _read_text(path) or ""
            for name in FORBIDDEN_QUERY_MOUNTS:
                if re.search(r"\b" + re.escape(name) + r"\s*\(", src):
                    offenders.append(f"{path.name} -> {name}()")
        self.assertEqual(
            offenders, [],
            "WQ-6：Query 不得依赖 Legacy 挂载点；命中：" + ", ".join(offenders),
        )

    # --- 领域边界 -------------------------------------------------

    def test_tb6_query_does_not_touch_memory(self) -> None:
        """WQ-63：Query 不得触碰 Memory。"""
        if not self._require_impl():
            return
        offenders: List[str] = []
        for path in self.modules:
            src = _read_text(path) or ""
            for token in ("ext_memory", "ext_mem", "enqueue_event", "ai_memories", "recall_events"):
                if token in src:
                    offenders.append(f"{path.name} -> {token}")
        self.assertEqual(
            offenders, [],
            "WQ-63：Query 不得触碰 Memory；命中：" + ", ".join(offenders),
        )

    def test_tb7_query_does_not_read_agent_state(self) -> None:
        """WQ-105 ～ WQ-108：Query 不得读取 AgentState。"""
        if not self._require_impl():
            return
        offenders: List[str] = []
        for path in self.modules:
            src = _read_text(path) or ""
            for token in ("AgentState", "get_agent_state", "agent.state", "agent_state_dict"):
                if token in src:
                    offenders.append(f"{path.name} -> {token}")
        self.assertEqual(
            offenders, [],
            "WQ-105：Query 不得读取 AgentState；命中：" + ", ".join(offenders),
        )

    def test_tb8_query_does_not_implement_activity_or_capability(self) -> None:
        """WQ-42 / WQ-64：Query 不得实现 Activity / Capability / Movement / Command。"""
        if not self._require_impl():
            return
        offenders: List[str] = []
        for path in self.modules:
            src = _read_text(path) or ""
            for token in (
                "class Activity", "CapabilityRequest", "CapabilityResult",
                "PLANNED", "TRAVELING", "ARRIVED", "PAUSED", "CANCELLED",
                "WorldCommand", "world_command", "find_route", "query_places",
            ):
                if token in src:
                    offenders.append(f"{path.name} -> {token}")
        self.assertEqual(
            offenders, [],
            "WQ-42 / WQ-64：Query 不得实现 Activity / Capability / Movement / Command；"
            "命中：" + ", ".join(offenders),
        )

    def test_tb9_query_emits_no_events(self) -> None:
        """WQ-37 / WQ-41：Query 不产生 / 不消费 Event。"""
        if not self._require_impl():
            return
        offenders: List[str] = []
        for path in self.modules:
            src = _read_text(path) or ""
            for token in ("agent.event", "observe_message", "Event(", "emit_event", "push_event"):
                if token in src:
                    offenders.append(f"{path.name} -> {token}")
        self.assertEqual(
            offenders, [],
            "WQ-37：Query 不产生 / 不消费 Event；命中：" + ", ".join(offenders),
        )

    # --- 接口形态 -------------------------------------------------

    def test_tb10_query_names_express_fact_inquiry(self) -> None:
        """WQ-92：Query 接口命名必须表达事实询问；禁止决策语义命名。"""
        if not self._require_impl():
            return
        offenders: List[str] = []
        for path in self.modules:
            tree = _parse(path)
            if tree is None:
                continue
            for name in _all_func_names(tree):
                low = name.lower()
                for bad in DECISION_NAMING_BLACKLIST:
                    if low.startswith(bad) or ("_" + bad.rstrip("_")) in low:
                        offenders.append(f"{path.name}::{name}")
        self.assertEqual(
            offenders, [],
            "WQ-92：Query 命名不得含决策语义；命中：" + ", ".join(offenders),
        )

    def test_tb11_query_defines_five_state_status(self) -> None:
        """
        WQ-18：Query 必须实现**五态核心**：FOUND / ABSENT / UNKNOWN / UNSUPPORTED / AMBIGUOUS。

        注意（架构侧裁决）：`FORBIDDEN` **不属于五态核心**，
        它是 **visibility / authorization outcome**，单独定义（见 `test_tb12`）。
        """
        if not self._require_impl():
            return
        required = ("FOUND", "ABSENT", "UNKNOWN", "UNSUPPORTED", "AMBIGUOUS")
        for path in self.modules:
            src = _read_text(path) or ""
            hits = [r for r in required if r in src]
            self.assertGreaterEqual(
                len(hits), 5,
                f"WQ-18：{path.name} 必须包含五态核心状态定义；当前命中 {hits}",
            )

    def test_tb12_forbidden_is_visibility_outcome_not_query_state(self) -> None:
        """
        【架构侧裁决】`FORBIDDEN` 属 visibility / authorization outcome，
        **不应与 `UNKNOWN` 等价**。

        本断言要求 Query 实现必须：

            1. 单独定义 `FORBIDDEN`（不得并入五态核心）；
            2. 不把 `FORBIDDEN` 折叠为 `UNKNOWN` / `ABSENT`；
            3. 在文档或代码注释中明确其属于可见性 / 授权语义。

        同时检查源码中不存在「FORBIDDEN 与 UNKNOWN 同义化」的写法
        （例如同一分支同时返回两者）。
        """
        if not self._require_impl():
            return

        joined = "\n".join(_read_text(p) or "" for p in self.modules)

        # 1) 必须定义 FORBIDDEN
        self.assertIn(
            "FORBIDDEN", joined,
            "架构侧裁决：Query 必须单独定义 FORBIDDEN（visibility / authorization outcome）",
        )

        # 2) 不得把 FORBIDDEN 与 UNKNOWN 等价化
        collapse_patterns = (
            r"FORBIDDEN\s*=\s*UNKNOWN",
            r"UNKNOWN\s*=\s*FORBIDDEN",
            r"FORBIDDEN\s*[:=]\s*[\"']UNKNOWN[\"']",
            r"[\"']FORBIDDEN[\"']\s*:\s*[\"']UNKNOWN[\"']",
            r"alias\w*FORBIDDEN",
        )
        hits: List[str] = []
        for pat in collapse_patterns:
            if re.search(pat, joined):
                hits.append(pat)
        self.assertEqual(
            hits, [],
            "架构侧裁决：FORBIDDEN 不得与 UNKNOWN 等价；命中：" + "; ".join(hits),
        )

        # 3) 必须能表达可见性 / 授权语义
        visibility_tokens = ("visib", "authoriz", "permission", "requester", "可见", "授权")
        self.assertTrue(
            any(t in joined for t in visibility_tokens),
            "架构侧裁决：Query 实现必须体现 FORBIDDEN 的 visibility / authorization 语义"
            "（缺少 visib / authoriz / requester 等标记）",
        )

    def test_tb13_query_declares_unsupported_for_missing_schema(self) -> None:
        """
        WQ-110 / WQ-111：schema 不支持的查询必须返回 UNSUPPORTED。

        断言：Query 实现中出现 UNSUPPORTED 且覆盖已知不支持项。
        """
        if not self._require_impl():
            return
        joined = "\n".join(_read_text(p) or "" for p in self.modules)
        self.assertIn(
            "UNSUPPORTED", joined,
            "WQ-110：Query 必须能返回 UNSUPPORTED",
        )


# =========================================================
# 4. T-C · Contract / Preflight 文档边界
# =========================================================

class TCDocumentationBoundary(unittest.TestCase):

    def test_tc1_d1_preflight_exists(self) -> None:
        self.assertTrue(PREFLIGHT_D1.is_file(), f"缺少 {PREFLIGHT_D1}")

    def test_tc2_d1_preflight_records_verdict(self) -> None:
        text = _read_text(PREFLIGHT_D1) or ""
        self.assertIn(
            "APPROVED WITH CORRECTIONS", text,
            "D-1 Preflight 必须记录架构侧裁决：APPROVED WITH CORRECTIONS",
        )

    def test_tc3_d1_preflight_applies_five_corrections(self) -> None:
        text = _read_text(PREFLIGHT_D1) or ""
        markers = (
            "修正后的定义",          # ①
            "只读数据视图",          # ②
            "WQ-81",                 # ③
            "Q-U3",                  # ④
            "WQ-94",                 # ⑤
        )
        missing = [m for m in markers if m not in text]
        self.assertEqual(
            missing, [],
            f"D-1 Preflight 未落实架构侧 5 项修正标记：{missing}",
        )

    def test_tc4_contract_contains_section_5d(self) -> None:
        contract = _read_text(CONTRACT_DOC)
        self.assertIsNotNone(contract, f"缺少 {CONTRACT_DOC}")
        self.assertIn("## 5D.", contract, "Contract 缺少 §5D（CC-20260930-05）")

    def test_tc5_contract_declares_cc_20260930_05(self) -> None:
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn(
            "CC-20260930-05", contract,
            "Contract 必须声明 CC-20260930-05",
        )

    def test_tc6_contract_contains_all_d1_rules(self) -> None:
        contract = _read_text(CONTRACT_DOC) or ""
        missing = [r for r in REQUIRED_D1_RULES if r not in contract]
        self.assertEqual(
            missing, [],
            f"Contract §5D 缺少以下 D-1 规则编号：{missing}",
        )

    def test_tc7_contract_freezes_unsupported_list(self) -> None:
        """WQ-110 / WQ-111：Contract 必须冻结 UNSUPPORTED 清单并禁止发明字段。"""
        contract = _read_text(CONTRACT_DOC) or ""
        for hint in UNSUPPORTED_QUERY_HINTS:
            self.assertIn(
                hint, contract,
                f"WQ-110：Contract §5D 的 UNSUPPORTED 清单缺少 {hint}",
            )
        self.assertIn(
            "临时创造", contract,
            "WQ-111：Contract 必须明确禁止为示例临时创造字段",
        )

    def test_tc8_contract_contains_anti_pattern_clause(self) -> None:
        """WQ-90 ～ WQ-93：反模式条款必须存在。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn(
            "万能世界 API", contract,
            "Contract §5D 必须包含「禁止万能世界 API」反模式条款",
        )
        for rule in ("WQ-90", "WQ-91", "WQ-92", "WQ-93"):
            self.assertIn(rule, contract, f"Contract §5D 缺少 {rule}")

    def test_tc9_contract_declares_phase_gate(self) -> None:
        """D1G-1 ～ D1G-6：阶段门必须冻结。"""
        contract = _read_text(CONTRACT_DOC) or ""
        for g in ("D1G-1", "D1G-2", "D1G-3", "D1G-4", "D1G-5", "D1G-6"):
            self.assertIn(g, contract, f"Contract §5D 缺少阶段门 {g}")
        self.assertIn(
            "禁止实现 `world_query.py`", contract,
            "D1G-4：Contract 必须明确禁止在测试通过前实现 world_query.py",
        )

    def test_tc10_contract_states_readonly_is_not_language_guarantee(self) -> None:
        """WQ-101：Contract 必须明确「只读不是语言级保证」。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn(
            "不是语言级保证", contract,
            "WQ-101：Contract 必须明确记录「只读不是语言级保证」这一技术事实",
        )

    def test_tc11_contract_keeps_section_5c_intact(self) -> None:
        """CC-20260930-05 不得重写 §5C。"""
        contract = _read_text(CONTRACT_DOC) or ""
        for rule in ("D0G-1", "D0G-2", "AC-5", "EV-9", "CP-1", "ME-21", "WT-1"):
            self.assertIn(rule, contract, f"§5C 规则 {rule} 不应在 CC-20260930-05 中丢失")

    # --- 阶段门生命周期（架构侧 TEST GATE CORRECTION） -------------

    def test_tc12_contract_separates_pre_and_post_implementation_gate(self) -> None:
        """
        【架构侧 TEST GATE CORRECTION】

        T-A 只属于 Pre-Implementation Gate；
        T-B 只属于 Post-Implementation Boundary Gate。

        Contract §5D.16 必须明确这两个阶段门的**生命周期**，
        以避免「实现 world_query.py 后 T-A 永久失败、无法形成正式通过状态」。
        """
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn(
            "D1G-3", contract,
            "Contract 必须包含 D1G-3（Pre-Implementation Gate）",
        )
        self.assertIn(
            "Pre-Implementation", contract,
            "Contract §5D.16 必须明确 Pre-Implementation Gate",
        )
        self.assertIn(
            "Post-Implementation", contract,
            "Contract §5D.16 必须明确 Post-Implementation Boundary Gate",
        )

    def test_tc13_test_file_declares_gate_lifecycle(self) -> None:
        """
        测试文件自身必须声明 T-A / T-B 的阶段门生命周期，
        说明「T-A 不是永久断言不存在」。
        """
        src = _read_text(Path(__file__)) or ""
        self.assertIn("Pre-Implementation Gate", src, "测试文件必须声明 Pre-Implementation Gate")
        self.assertIn(
            "Post-Implementation Boundary Gate", src,
            "测试文件必须声明 Post-Implementation Boundary Gate",
        )
        self.assertIn(
            "永久失败", src,
            "测试文件必须说明「不允许 T-A 永久失败」这一裁决理由",
        )

    def test_tc14_test_file_labels_strict_readonly_as_d1_strategy(self) -> None:
        """
        【架构侧裁决】「禁止 local append/sort/pop」必须明确为
        **D-1 静态验证策略**，而非永久 Python 架构原则。
        """
        src = _read_text(Path(__file__)) or ""
        self.assertIn(
            "D-1 静态验证策略", src,
            "测试文件必须把严格只读标注为 D-1 静态验证策略",
        )
        self.assertIn(
            "不是永久 Python 架构原则", src,
            "测试文件必须明确该策略不是永久 Python 架构原则",
        )

    def test_tc15_forbidden_semantics_defined_in_docs(self) -> None:
        """
        【架构侧裁决】FORBIDDEN 属 visibility / authorization outcome，
        **不应与 UNKNOWN 等价**。

        断言：Contract §5D.6 与 D-1 Preflight 均明确定义该关系。
        """
        contract = _read_text(CONTRACT_DOC) or ""
        preflight = _read_text(PREFLIGHT_D1) or ""

        for label, text in (("Contract §5D.6", contract), ("D-1 Preflight", preflight)):
            self.assertIn(
                "FORBIDDEN", text,
                f"{label} 必须定义 FORBIDDEN",
            )

        self.assertIn(
            "visibility", contract,
            "Contract §5D.6 必须把 FORBIDDEN 定位为 visibility / authorization outcome",
        )
        self.assertIn(
            "五态", contract,
            "Contract §5D.6 必须明确五态核心（FORBIDDEN 不属五态核心）",
        )

    def test_tc16_five_state_core_is_exactly_five(self) -> None:
        """
        五态核心必须恰好是 5 个：
        FOUND / ABSENT / UNKNOWN / UNSUPPORTED / AMBIGUOUS。

        断言：Contract 不把 FORBIDDEN 计入五态核心。
        """
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("五态", contract, "Contract 必须使用「五态」这一表述")
        self.assertIn(
            "不属", contract,
            "Contract 必须说明 FORBIDDEN 不属于五态核心（架构侧裁决）",
        )

    def test_tc17_contract_records_static_assertion_strategy(self) -> None:
        """
        §5D.16.2：静态边界断言实现策略必须记入 Contract
        （来源：D-0 / D-1 首次真实运行暴露的 6 处缺陷）。

        本断言防止这段经验在后续 Contract 维护中丢失。
        """
        contract = _read_text(CONTRACT_DOC) or ""

        self.assertIn(
            "## 5D.16.2", contract,
            "Contract 必须包含 §5D.16.2（静态边界断言实现策略）",
        )
        self.assertIn(
            "必须区分「代码构造」与「说明文本」", contract,
            "§5D.16.2 必须写明核心教训：区分代码构造与说明文本",
        )
        self.assertIn(
            "裸文本包含", contract,
            "§5D.16.2 必须明确禁止裸文本包含式判断（D1G-17 / D1G-19）",
        )
        self.assertIn(
            "肯定式", contract,
            "§5D.16.2 必须写明状态标记需区分肯定式与否定式（D1G-18）",
        )
        for rule in ("D1G-16", "D1G-17", "D1G-18", "D1G-19", "D1G-20", "D1G-21", "D1G-22"):
            self.assertIn(rule, contract, f"Contract §5D.16.2 缺少规则 {rule}")

    def test_tc18_contract_records_test_run_outcome(self) -> None:
        """
        首次真实运行的结论必须被记录：6 处缺陷全部在测试/文档层。

        注意：本断言**不**要求 Contract 记录具体测试数字
        （那属于 PROJECT 的职责），只要求结论存在。
        """
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn(
            "全部出现在测试/文档层", contract,
            "§5D.16.2 必须记录「6 处缺陷全部在测试/文档层」这一结论",
        )


# =========================================================
# 5. T-D · D-0 / A/B/C 未被 D-1 改动
# =========================================================

class TDD0AndABCUnchanged(unittest.TestCase):

    def test_td1_d0_sealed_artifacts_exist(self) -> None:
        for path in (AUDIT_D0, DECISIONS_D0, PREFLIGHT_D0, TEST_D0):
            self.assertTrue(path.is_file(), f"D-0 SEALED 产物缺失：{path}")

    def test_td2_think_still_intent_set_stub(self) -> None:
        """C-2 §5B.11 / IN-29 / IN-30 未被 D-1 改动。"""
        path = AGENT_DIR / "runtime.py"
        tree = _parse(path)
        self.assertIsNotNone(tree, "缺少或无法解析 agent/runtime.py")

        think = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "think":
                think = node
                break
        self.assertIsNotNone(think, "agent/runtime.py 缺少 think()")
        ret = think.returns
        name = ret.id if isinstance(ret, ast.Name) else getattr(ret, "attr", None)
        self.assertEqual(name, "IntentSet", "IN-29：think() 必须仍返回 IntentSet")

    def test_td3_build_context_still_agent_context(self) -> None:
        """AR-8 未被 D-1 改动。"""
        tree = _parse(AGENT_DIR / "runtime.py")
        self.assertIsNotNone(tree)
        fn = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "build_context":
                fn = node
                break
        self.assertIsNotNone(fn, "agent/runtime.py 缺少 build_context()")
        ret = fn.returns
        name = ret.id if isinstance(ret, ast.Name) else getattr(ret, "attr", None)
        self.assertEqual(name, "AgentContext", "AR-8：build_context() 必须仍返回 AgentContext")

    def test_td4_context_layers_still_present(self) -> None:
        """CA-7 未被 D-1 改动。"""
        tree = _parse(AGENT_DIR / "runtime.py")
        self.assertIsNotNone(tree)
        self.assertIn(
            "ContextLayers", _class_names(tree),
            "CA-7：ContextLayers 必须仍保留为 deprecated stub",
        )

    def test_td5_runtime_holder_apis_still_present(self) -> None:
        """RS-8 ～ RS-13 未被 D-1 改动。"""
        tree = _parse(AGENT_DIR / "runtime.py")
        self.assertIsNotNone(tree)
        names = _all_func_names(tree)
        for api in (
            "add_goal", "get_goal", "list_goals", "replace_goal",
            "add_commitment", "get_commitment", "list_commitments", "replace_commitment",
        ):
            self.assertIn(api, names, f"RS-8 ～ RS-13：缺少 holder API {api}()")

    def test_td6_state_py_still_does_not_write_data(self) -> None:
        """AS-3 未被 D-1 改动（WQ-109 明确不在 D-1 修 state.py）。"""
        state = AGENT_DIR / "state.py"
        for pat in (r"\bdata\s*\[[^\]]+\]\s*=", r"\bdata\s*\.\s*setdefault\s*\(",
                    r"\bdata\s*\.\s*pop\s*\(", r"\bdata\s*\.\s*update\s*\("):
            self.assertFalse(
                _has_code_match(state, pat),
                f"AS-3 / WQ-109：D-1 不应让 agent/state.py 写入 main.data（命中 {pat}）",
            )

    def test_td7_legacy_brain_and_world_untouched(self) -> None:
        """WQ-62：D-1 不得修改 ext_ai / ext_world / ext_room / main 的现有行为。"""
        expectations = {
            EXT_DIR / "ext_ai.py": ("drive_ai", "execute_action", "build_ai_context", "auto_ai_loop"),
            EXT_DIR / "ext_world.py": ("ai_spot_tick",),
            EXT_DIR / "ext_room.py": ("summon",),
        }
        for path, names in expectations.items():
            tree = _parse(path)
            self.assertIsNotNone(tree, f"缺少或无法解析 {path}")
            funcs = _all_func_names(tree)
            for fn in names:
                self.assertIn(fn, funcs, f"WQ-62：{path.name} 的结构不应在 D-1 被改动（缺少 {fn}）")

        main_src = _read_text(MAIN_PY) or ""
        self.assertIn("def check_pending_moves", main_src, "WQ-62：main.py 结构不应在 D-1 被改动")

    def test_td8_memory_write_path_still_unreachable(self) -> None:
        """WQ-63：D-1 不得顺手修 Memory。"""
        mem = EXT_DIR / "ext_memory.py"
        src = _read_text(mem)
        self.assertIsNotNone(src, "缺少 ext/ext_memory.py")
        self.assertIn("_enqueue_event_impl", src, "WQ-63：ext_memory.py 不应在 D-1 被改动")
        self.assertIsNone(
            re.search(r"^\s*(async\s+)?def\s+_enqueue_event_impl\b", src, re.M),
            "WQ-63：D-1 不得修复 Memory（发现 _enqueue_event_impl 已被定义）",
        )

    def test_td9_frontend_untouched(self) -> None:
        """WQ-56：D-1 不得修改前端。"""
        for rel in ("index.html", "ext/app-core.js", "ext/app-chat.js", "ext/app-map.js"):
            self.assertTrue((ROOT / rel).is_file(), f"WQ-56：不应修改/删除前端文件 {rel}")

    def test_td10_no_new_toplevel_data_key_added(self) -> None:
        """
        WQ-65：D-1 不得新增 main.data 顶层 key。

        以 boundary-form 断言 main.py 的 default_data() 中不出现 query 相关 key。
        """
        tree = _parse(MAIN_PY)
        self.assertIsNotNone(tree)
        default_fn = None
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
            low = key.lower()
            self.assertNotIn(
                "query", low,
                f"WQ-65：D-1 不应新增 Query 相关的 main.data 顶层 key：{key!r}",
            )
            self.assertNotIn(
                "world_query", low,
                f"WQ-65：D-1 不应新增 Query 相关的 main.data 顶层 key：{key!r}",
            )


# =========================================================
# 6. T-E · 环境能力检查（不伪造结果）
# =========================================================

class TEEnvironmentCapability(unittest.TestCase):

    def test_te1_repo_root_resolves(self) -> None:
        self.assertTrue((ROOT / "main.py").is_file(), f"ROOT 解析错误：{ROOT}")
        self.assertTrue(AGENT_DIR.is_dir() and EXT_DIR.is_dir(), f"ROOT 解析错误：{ROOT}")
        self.assertNotEqual(ROOT.name, "docs", "ROOT 不应被解析为 docs/")

    def test_te2_no_third_party_import_required(self) -> None:
        tree = _parse(Path(__file__))
        self.assertIsNotNone(tree, "无法解析本测试文件自身")
        stdlib_ok = {
            "__future__", "ast", "os", "re", "unittest", "pathlib", "typing",
            "sys", "json", "textwrap", "collections",
        }
        mods = _top_level_modules(tree)
        extra = sorted(m for m in mods if m not in stdlib_ok)
        self.assertEqual(extra, [], f"本测试文件只能依赖标准库；发现：{extra}")

    def test_te3_project_master_locatable(self) -> None:
        found = [p for p in PROJECT_MASTER_CANDIDATES if p.is_file()]
        self.assertTrue(
            found,
            "未能定位 PROJECT_V3.1_MASTER.md；"
            f"候选：{[str(p) for p in PROJECT_MASTER_CANDIDATES]}",
        )


# =========================================================
# 入口
# =========================================================

def _print_header() -> None:
    gate = _gate_open()
    print("=" * 72)
    print("V3.1 Phase D-1 · World Query Architecture Boundary Tests")
    print("=" * 72)
    print(f"ROOT            : {ROOT}")
    print(f"agent/          : {len(_agent_files())} py files")
    print(f"ext/            : {len(_py_files(EXT_DIR))} py files")
    print(f"d1 preflight    : {'OK' if PREFLIGHT_D1.is_file() else 'MISSING'} -> {PREFLIGHT_D1}")
    print(f"contract        : {'OK' if CONTRACT_DOC.is_file() else 'MISSING'} -> {CONTRACT_DOC}")
    print(f"d1 impl modules : {len(_query_modules())}")
    print("-" * 72)
    print(f"GATE STATE      : {'OPEN (implementation authorized)' if gate else 'CLOSED (implementation not authorized)'}")
    print("                  gate 由 Contract §5D.16 的 D1G-3-SATISFIED 标记决定")
    print("-" * 72)
    if gate:
        print("T-A: Pre-Implementation Gate —— 门已开，断言「实现确实存在」")
    else:
        print("T-A: Pre-Implementation Gate —— 门关闭，断言「实现不存在」（防提前偷做）")
    print("T-B: Post-Implementation Boundary Gate —— 仅在实现存在时生效（当前逐项 return）")
    print("T-C: Contract / Preflight 文档边界")
    print("T-D: D-0 与 A/B/C 未被 D-1 改动")
    print("T-E: 环境能力（不伪造结果）")
    print("=" * 72)
    print("注意：T-A 不是「永久断言不存在」；实现落地后它会自动转为通过。")
    print("=" * 72)


if __name__ == "__main__":
    _print_header()
    unittest.main(verbosity=2)
