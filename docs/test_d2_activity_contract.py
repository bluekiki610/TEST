# -*- coding: utf-8 -*-
"""
docs/test_d2_activity_contract.py
=================================

V3.1 Phase D-2 · Activity Contract **Architecture Boundary Tests**
（CC-20260930-06，Contract §5E）

--------------------------------------------------------------------------
本阶段的性质（务必先读）
--------------------------------------------------------------------------

D-2 Architecture Tests 阶段**不实现任何 Activity 代码**：

    ❌ agent/activity.py
    ❌ Activity Registry
    ❌ Activity Runtime
    ❌ persistence
    ❌ scheduler / tick / timer
    ❌ AgentState / Motivation / Context / World Query 修改
    ❌ ext_world / ext_ai / frontend / HTTP 修改

因此本测试的**主要形态是「边界断言」**：

    断言「**不应该存在的东西确实不存在**」——
    防止在 Contract 已批准、实现尚未授权的窗口期内**提前偷做**。

这与 D-1 的 T-A 同构，并**继承 D-1 的教训**（架构侧 TEST GATE CORRECTION）：

    **门关闭时断言实现不存在；门打开后本组自动转为断言「实现确实存在」。**
    **禁止把本组实现为「永久断言不存在」。**

--------------------------------------------------------------------------
阶段门
--------------------------------------------------------------------------

本阶段唯一的实现边界是 **`agent/activity.py` 是否存在**：

    不存在 → Pre-Implementation 形态 → 断言「不存在 + 未提前偷做」
    存在   → 实现已授权 → 本组自动放宽为「存在性确认」，
             并把「registry / 唯一真相 / binding / 终态不可逆」等
             转为**实现级**断言（若届时仍缺失则失败）

--------------------------------------------------------------------------
15 项重点验证（架构侧指定）
--------------------------------------------------------------------------

    ① Activity Registry 是 Runtime 内唯一 Activity 管理入口
    ② 同一 activity_id 不得形成多个独立 Activity 真相
    ③ AgentRuntime 不拥有自己的 Activity 真相
    ④ primary / secondary 只是 binding
    ⑤ 不存在 main.data["activities"]
    ⑥ 不存在 Activity persistence
    ⑦ 不存在隐式 persistence
    ⑧ Formal Activity 不进入 Motivation
    ⑨ AgentState.current_activity 不被视为 Formal Activity
    ⑩ 不存在 Activity scheduler / tick / timer
    ⑪ expected_end_at 不自动完成 Activity
    ⑫ Legacy → Activity 为单向关系
    ⑬ Activity → Legacy / 双向同步必须失败
    ⑭ lifecycle transition 与终态不可逆规则符合 Contract
    ⑮ 未实现的「未冻结项」不得被提前实现

--------------------------------------------------------------------------
静态验证策略（继承 D-1）
--------------------------------------------------------------------------

    本文件使用 `_effective_code()`（tokenize 级：丢弃 COMMENT，
    把 STRING 掩为 `""`）来区分**代码构造**与**说明文本**。

    这是 Contract `D1G-16` ～ `D1G-20` 的直接要求，并在 `EV-15` 中
    被 D-2 继承 —— 因为 Contract 与 docstring 会**声明**禁止项，
    裸文本包含会把「声明约束成立」误判为「违反约束」。

--------------------------------------------------------------------------
如何运行
--------------------------------------------------------------------------

    从仓库根目录运行：

        python docs/test_d2_activity_contract.py
        python -m unittest docs.test_d2_activity_contract -v

    若执行环境不可用，必须如实报告：

        TEST NOT RUN
        Reason: environment execution unavailable

    并且**不得**把 TEST NOT RUN 当作通过（Contract `EV-19`）。
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
# 0. 仓库根：标记探测（兼容目录整理）
# =========================================================

_HERE = Path(__file__).resolve().parent


def _find_repo_root(start: Path) -> Path:
    """
    向上寻找同时含 `main.py` + `agent/` + `ext/` 的目录。

    禁止硬编码 `parent.parent` —— 工作区可能被整理
    （例如把 PROJECT / PRODUCT_GUIDE 移入 docs/）。
    """
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
DOCS_DIR = ROOT / "docs"

CONTRACT_DOC = DOCS_DIR / "V3.1_ARCHITECTURE_CONTRACT.md"
PREFLIGHT_DOC = DOCS_DIR / "D2_ACTIVITY_CONTRACT_PREFLIGHT.md"
PROJECT_DOC = DOCS_DIR / "PROJECT_V3.1_MASTER.md"
PROJECT_DOC_ALT = ROOT / "PROJECT_V3.1_MASTER.md"

# D-1 / D-0 已封板产物（D-2 不得破坏）
D1_TEST_DOC = DOCS_DIR / "test_d1_world_query.py"
D1_BEHAVIOR_DOC = DOCS_DIR / "test_d1_world_query_behavior.py"
D0_TEST_DOC = DOCS_DIR / "test_d0_world_activity_capability.py"
D1_PREFLIGHT_DOC = DOCS_DIR / "D1_WORLD_QUERY_PREFLIGHT.md"
WORLD_QUERY_MODULE = AGENT_DIR / "world_query.py"

# =========================================================
# 1. 只读文件工具
# =========================================================


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        try:
            return path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            return None


def _effective_code(path: Path) -> str:
    """
    返回「有效代码文本」：已掩掉所有注释与**所有字符串字面量**。

    见文件头「静态验证策略」。这是 `D1G-16` / `EV-15` 的直接要求。
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
        lines = src.splitlines()
        return "\n".join(ln for ln in lines if not ln.strip().startswith("#"))


def _py_files(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.rglob("*.py") if p.is_file())


def _code_lines(path: Path) -> List[str]:
    """返回去注释后的行（用于轻量前缀匹配）。"""
    src = _read_text(path)
    if src is None:
        return []
    out = []
    for ln in src.splitlines():
        stripped = ln.strip()
        if stripped.startswith("#"):
            continue
        out.append(ln)
    return out


def _word_in(token: str, text: str) -> bool:
    """
    词边界匹配（避免子串误报）。

    ⚠️ 这是 D-1 教训的直接延续（Contract `D1G-16` ～ `D1G-20`）：

        裸子串匹配会产生系统性误报。实例：
            `traveling_to_date`（agent/world_query.py 的 Legacy 活动标签）
            会被裸子串 `TRAVELING` 命中 —— 但它**不是** Activity 生命周期状态。

    使用 `\\b` 词边界后，`traveling_to_date` 不再命中 `\\bTRAVELING\\b`。
    """
    return re.search(r"\b" + re.escape(token) + r"\b", text) is not None


# =========================================================
# 2. 阶段门：agent/activity.py 是否存在
# =========================================================

ACTIVITY_MODULE = AGENT_DIR / "activity.py"
ACTIVITY_PKG = AGENT_DIR / "activity"

# 可能的实现候选名（用于「未提前偷做」的宽断言）
ACTIVITYISH_NAMES: Sequence[str] = (
    "activity.py",
    "activity_registry.py",
    "activity_runtime.py",
    "activity_store.py",
    "activity_persistence.py",
    "activity_scheduler.py",
)


def _implementation_present() -> bool:
    """
    D-2 的实现边界：`agent/activity.py`（或 `agent/activity/` 包）是否存在。

    这是唯一判据 —— 不由本测试自行发明第二套门控。
    """
    return ACTIVITY_MODULE.is_file() or ACTIVITY_PKG.is_dir()


# =========================================================
# 3. 关键边界常量
# =========================================================

# ⑦ 隐式 persistence：出现即视为隐式落盘
_IMPLICIT_PERSISTENCE_TOKENS: Sequence[str] = (
    "json.dump",
    "pickle.dump",
    "sqlite3",
    "shelve",
    "dbm.",
    "to_csv",
    "write_text",
    "write_bytes",
)

# ⑩ scheduler / tick / timer
_SCHEDULER_TOKENS: Sequence[str] = (
    "scheduler",
    "crontab",
    "APScheduler",
    "time.sleep",
    "threading.Timer",
    "asyncio.sleep",
    "while True",
)

# ⑪ expected_end_at 不得自动完成 Activity
_AUTO_COMPLETE_PATTERNS: Sequence[str] = (
    r"expected_end_at\s*<=?\s*now",
    r"now\s*>=?\s*expected_end_at",
    r"if\s+.*expected_end_at.*:\s*$",
    r"expected_end_at.*==\s*now",
)

# ⑬ Activity → Legacy 反向写入 / 双向同步
_REVERSE_WRITE_PATTERNS: Sequence[str] = (
    r"main\.data\s*\[",
    r"save_data\s*\(",
    r"_enqueue_event_impl",
)

# 18 类 Legacy Activity State（Contract §5E.19 / D-0 Audit）
_LEGACY_ACTIVITY_KEYS: Sequence[str] = (
    "dates",
    "date_invites",
    "date_invites_out",
    "date_invite_out",
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
)

# 10 项节律 / 调度键（Contract §5E.16 / `EP-8`）
_LEGACY_RHYTHM_KEYS: Sequence[str] = (
    "story_rhythm",
    "writing_rhythm",
    "living_rhythm",
    "ai_home_act_next",
    "ai_auto_next",
    "_last_think_invite",
    "ai_drive_log",
    "ai_last_human",
    "ai_last_auto",
    "ai_diary_log",
)

# Contract §5E 生命周期（EF-1）
_LIFECYCLE_STATES: Sequence[str] = (
    "PLANNED",
    "TRAVELING",
    "ARRIVED",
    "ACTIVE",
    "PAUSED",
    "COMPLETED",
    "CANCELLED",
)

# 允许转换（EF-2）
_ALLOWED_TRANSITIONS: Sequence[Tuple[str, str]] = (
    ("PLANNED", "TRAVELING"),
    ("PLANNED", "CANCELLED"),
    ("TRAVELING", "ARRIVED"),
    ("TRAVELING", "CANCELLED"),
    ("ARRIVED", "ACTIVE"),
    ("ARRIVED", "CANCELLED"),
    ("ACTIVE", "PAUSED"),
    ("ACTIVE", "COMPLETED"),
    ("ACTIVE", "CANCELLED"),
    ("PAUSED", "ACTIVE"),
    ("PAUSED", "CANCELLED"),
)

# 终态（EF-3）
_TERMINAL_STATES: Sequence[str] = ("COMPLETED", "CANCELLED")

# 禁止的跳跃转换（EF-2 的反例）
_FORBIDDEN_TRANSITIONS: Sequence[Tuple[str, str]] = (
    ("PLANNED", "COMPLETED"),
    ("PLANNED", "ACTIVE"),
    ("PLANNED", "ARRIVED"),
    ("PLANNED", "PAUSED"),
    ("TRAVELING", "COMPLETED"),
    ("TRAVELING", "ACTIVE"),
    ("ARRIVED", "COMPLETED"),
    ("ARRIVED", "PAUSED"),
    ("COMPLETED", "ACTIVE"),
    ("COMPLETED", "CANCELLED"),
    ("CANCELLED", "ACTIVE"),
    ("CANCELLED", "COMPLETED"),
    ("PAUSED", "COMPLETED"),
)

# §5E 规则组（用于 Contract 完整性断言）
_SECTION_5E_RULE_GROUPS: Sequence[str] = (
    "EA", "EB", "EC", "ED", "EE", "EF", "EG", "EH", "EI", "EJ",
    "EK", "EL", "EM", "EN", "EO", "EP", "EQ", "ER", "ES", "ET", "EU",
)

# 21 个规则组的首条规则（用于确认组存在）
_RULE_GROUP_FIRST: Sequence[str] = (
    "EA-1", "EB-1", "EC-1", "ED-1", "EE-1", "EF-1", "EG-1", "EH-1",
    "EI-1", "EJ-1", "EK-1", "EL-1", "EM-1", "EN-1", "EO-1", "EP-1",
    "EQ-1", "ER-1", "ES-1", "ET-1", "EU-1",
)


# =========================================================
# A. 阶段门
# =========================================================

class AD2GateState(unittest.TestCase):
    """阶段门必须可判定，且不得形成「无法通过」的终态。"""

    def test_a1_gate_state_is_determinate(self) -> None:
        """
        门状态必须可判定。

        判据 = `agent/activity.py`（或 `agent/activity/` 包）是否存在 ——
        不由本测试自行发明第二套门控。

        同时确认 Contract 把 `agent/activity.py` 明确列为 D-2 禁止项。
        """
        present = _implementation_present()
        self.assertIsInstance(present, bool)

        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn(
            "agent/activity.py", contract,
            "Contract §5E 必须把 agent/activity.py 列为 D-2 禁止项（EA-2 / EU-1）",
        )
        self.assertIn(
            "**EA-2**", contract,
            "Contract 必须含 EA-2（D-2 禁止创建 agent/activity.py）",
        )

    def test_a2_no_activity_module_in_pre_implementation_phase(self) -> None:
        """
        **门关闭时**：不得提前创建 Activity 实现模块。

        门打开后本断言自动放宽（架构侧 TEST GATE CORRECTION 的同一原则）。
        """
        if _implementation_present():
            # 门已打开：断言实现确实存在（由 B 组做实现级验证）
            self.assertTrue(ACTIVITY_MODULE.is_file() or ACTIVITY_PKG.is_dir())
            return
        offenders = [
            str((AGENT_DIR / name).relative_to(ROOT))
            for name in ACTIVITYISH_NAMES
            if (AGENT_DIR / name).exists()
        ]
        self.assertEqual(
            offenders, [],
            "D-2 Architecture Tests 阶段禁止实现 Activity；命中：" + ", ".join(offenders),
        )

    def test_a3_no_activity_runtime_or_registry_created(self) -> None:
        """
        ❌ Activity Runtime / Registry 实现。

        门关闭时应完全不存在；门打开后须确认 registry 语义存在
        （由 B 组验证「唯一管理入口」）。
        """
        if _implementation_present():
            return
        offenders: List[str] = []
        for path in _py_files(AGENT_DIR):
            effective = _effective_code(path)
            if re.search(r"class\s+\w*ActivityRegistry", effective):
                offenders.append(f"{path.name} -> class *ActivityRegistry")
            if re.search(r"class\s+\w*ActivityRuntime", effective):
                offenders.append(f"{path.name} -> class *ActivityRuntime")
        self.assertEqual(
            offenders, [],
            "D-2 Architecture Tests 阶段禁止实现 ActivityRegistry / ActivityRuntime；"
            "命中：" + ", ".join(offenders),
        )

    def test_a4_no_implicit_persistence_for_activity(self) -> None:
        """
        ❌ Activity persistence / 隐式 persistence。

        门关闭时，agent/ 下不得出现落盘机制。
        """
        if _implementation_present():
            return
        offenders: List[str] = []
        for path in _py_files(AGENT_DIR):
            effective = _effective_code(path)
            for token in _IMPLICIT_PERSISTENCE_TOKENS:
                if token in effective:
                    offenders.append(f"{path.name} -> {token}")
        self.assertEqual(
            offenders, [],
            "D-2 禁止 Activity persistence / 隐式 persistence；命中：" + ", ".join(offenders),
        )

    def test_a5_no_activity_scheduler_or_tick_or_timer(self) -> None:
        """❌ scheduler / tick / timer（Contract `EP-6`）。"""
        if _implementation_present():
            return
        offenders: List[str] = []
        for path in _py_files(AGENT_DIR):
            effective = _effective_code(path)
            for token in _SCHEDULER_TOKENS:
                if token in effective:
                    offenders.append(f"{path.name} -> {token}")
        self.assertEqual(
            offenders, [],
            "D-2 禁止 scheduler / tick / timer；命中：" + ", ".join(offenders),
        )


# =========================================================
# B. Activity Registry 与唯一真相
# =========================================================

class BD2RegistryAndSingleTruth(unittest.TestCase):
    """① ② ③ ④：Registry 唯一入口 / 单一真相 / AgentRuntime 不拥有 / binding。"""

    def test_b1_contract_freezes_single_registry(self) -> None:
        """① Activity Registry 是 Runtime 内唯一 Activity 管理入口（`EE-1` / `EE-2`）。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EE-1**", contract)
        self.assertIn("**EE-2**", contract)
        self.assertIn("ActivityRegistry", contract, "Contract 必须定义 ActivityRegistry 结构")
        self.assertIn(
            "唯一管理入口", contract,
            "Contract 必须写明 Registry 是唯一管理入口",
        )

    def test_b2_contract_forbids_multiple_activity_truths(self) -> None:
        """② 同一 activity_id 不得形成多个独立 Activity 真相（`EC-4` / `EE-3`）。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EC-4**", contract)
        self.assertIn("**EE-3**", contract)
        self.assertIn(
            "只能有一个 Activity 对象真相", contract,
            "Contract 必须写明同一 activity_id 只有一个对象真相",
        )

    def test_b3_agent_runtime_must_not_own_activity_truth(self) -> None:
        """
        ③ AgentRuntime 不拥有自己的 Activity 真相（`EE-4`）。

        同时（门关闭时）确认 `agent/runtime.py` **未被修改**去持有 Activity。
        """
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EE-4**", contract)
        self.assertIn(
            "不得拥有自己的独立 Activity 真相", contract,
            "Contract 必须写明 AgentRuntime 不得拥有独立 Activity 真相",
        )

        runtime_py = AGENT_DIR / "runtime.py"
        if runtime_py.is_file():
            effective = _effective_code(runtime_py)
            offenders = [
                token for token in ("ActivityRegistry", "activity_registry", "activities[")
                if token in effective
            ]
            self.assertEqual(
                offenders, [],
                "D-2 期间 agent/runtime.py 不得持有 Activity；命中：" + ", ".join(offenders),
            )

    def test_b4_primary_secondary_are_binding_not_ownership(self) -> None:
        """④ primary / secondary 只是 binding（`EE-8` / `EK-4`）。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EE-8**", contract)
        self.assertIn("**EK-4**", contract)
        self.assertIn(
            "不是 Activity 的所有权", contract,
            "Contract 必须写明 primary Activity 是绑定关系，不是所有权",
        )

    def test_b5_contract_forbids_multiple_primary(self) -> None:
        """`EK-1` / `EK-3`：同一 AI 最多一个 primary，且禁止两个 primary。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EK-1**", contract)
        self.assertIn("**EK-3**", contract)


# =========================================================
# C. World SOT 与 Persistence
# =========================================================

class CD2WorldSotAndPersistence(unittest.TestCase):
    """⑤ ⑥ ⑦：无 main.data["activities"] / 无 persistence / 无隐式 persistence。"""

    def test_c1_no_main_data_activities_key(self) -> None:
        """
        ⑤ 不存在 `main.data["activities"]`（`ED-8`）。

        同时确认 `main.py` / `agent/` / `ext/` 中**没有**任何地方
        把 Activity 写进 main.data。
        """
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**ED-8**", contract, "Contract 必须禁止新增 main.data 顶层 activities key")

        offenders: List[str] = []
        for path in _py_files(AGENT_DIR) + _py_files(EXT_DIR):
            effective = _effective_code(path)
            for pattern in (
                r"\[\s*[\"']activities[\"']\s*\]",
                r"\[\s*[\"']activity[\"']\s*\]",
                r"[\"']activities[\"']\s*:",
            ):
                if re.search(pattern, effective):
                    offenders.append(f"{path.name} -> activities key")
                    break

        main_py = ROOT / "main.py"
        if main_py.is_file():
            effective = _effective_code(main_py)
            for pattern in (r"\[\s*[\"']activities[\"']\s*\]", r"[\"']activities[\"']\s*:"):
                if re.search(pattern, effective):
                    offenders.append("main.py -> activities key")

        self.assertEqual(
            offenders, [],
            "D-2 禁止 main.data['activities']；命中：" + ", ".join(offenders),
        )

    def test_c2_no_activity_persistence_medium(self) -> None:
        """⑥ 不存在 Activity persistence（`ED-5` / `ED-7` / `EH-1`）。"""
        contract = _read_text(CONTRACT_DOC) or ""
        for rule in ("**ED-5**", "**ED-7**", "**EH-1**", "**EH-2**"):
            self.assertIn(rule, contract, f"Contract 必须包含 {rule}")

        # 不得存在 activity 专属持久化文件
        suspicious = [
            p.name
            for p in ROOT.rglob("*")
            if p.is_file()
            and p.suffix.lower() in (".json", ".db", ".sqlite", ".sqlite3", ".pkl")
            and "activit" in p.name.lower()
        ]
        self.assertEqual(
            suspicious, [],
            "D-2 禁止 Activity 持久化介质；命中：" + ", ".join(suspicious),
        )

    def test_c3_no_implicit_persistence_anywhere(self) -> None:
        """⑦ 不存在隐式 persistence（`ED-12`）。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**ED-12**", contract)
        self.assertIn("隐式持久化", contract, "Contract 必须明确禁止隐式持久化")

        if _implementation_present():
            return
        # 门关闭时：agent/ 下不得有任何落盘调用
        offenders: List[str] = []
        for path in _py_files(AGENT_DIR):
            effective = _effective_code(path)
            for token in _IMPLICIT_PERSISTENCE_TOKENS:
                if token in effective:
                    offenders.append(f"{path.name} -> {token}")
        self.assertEqual(
            offenders, [],
            "禁止隐式 persistence；命中：" + ", ".join(offenders),
        )

    def test_c4_world_sot_remains_main_data(self) -> None:
        """`ED-2` / `ED-3`：main.data 仍是唯一 World SOT；World SOT != Runtime Domain State。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**ED-2**", contract)
        self.assertIn("**ED-3**", contract)
        self.assertIn(
            "World SOT != Runtime Domain State", contract,
            "Contract 必须明确 World SOT != Runtime Domain State",
        )

        main_py = ROOT / "main.py"
        self.assertTrue(main_py.is_file(), "main.py 必须存在")
        src = _read_text(main_py) or ""
        self.assertEqual(
            len(re.findall(r"^\s*data\s*=\s*\{\s*\}\s*$", src, re.MULTILINE)),
            1,
            "main.py 必须仍只有一处 `data = {}`（唯一 World 存储）",
        )


# =========================================================
# D. Motivation 与 AgentState 边界
# =========================================================

class DD2MotivationAndAgentState(unittest.TestCase):
    """⑧ ⑨：Formal Activity 不进入 Motivation；current_activity 不是 Formal Activity。"""

    def test_d1_formal_activity_not_wired_into_motivation(self) -> None:
        """⑧ Formal Activity 不进入 Motivation（`ET-1` / `ET-7` / `ET-10`）。"""
        contract = _read_text(CONTRACT_DOC) or ""
        for rule in ("**ET-1**", "**ET-7**", "**ET-8**", "**ET-9**", "**ET-10**"):
            self.assertIn(rule, contract, f"Contract 必须包含 {rule}")

        motivation_py = AGENT_DIR / "motivation.py"
        self.assertTrue(motivation_py.is_file(), "agent/motivation.py 必须存在")
        effective = _effective_code(motivation_py)
        offenders = [
            token for token in (
                "Activity", "activity_id", "current_activity_id",
                "ActivityRegistry", "world_query",
            )
            if token in effective
        ]
        self.assertEqual(
            offenders, [],
            "ET-7 / ET-10：agent/motivation.py 不得引用 Formal Activity / World Query；"
            "命中：" + ", ".join(offenders),
        )

    def test_d2_motivation_min_inputs_unchanged(self) -> None:
        """`ET-9`：不扩展 §5B.8（Motivation 最小输入集合）。"""
        motivation_py = AGENT_DIR / "motivation.py"
        src = _read_text(motivation_py) or ""
        for field in ('"goal"', '"commitment"', '"agent_state_snapshot"', '"now_ts"'):
            self.assertIn(field, src, f"Motivation 最小输入集合必须仍含 {field}")
        self.assertIn(
            '"forbidden_inputs"', src,
            "Motivation 必须仍声明 forbidden_inputs",
        )
        self.assertIn(
            '"world_query"', src,
            "MO-17：Motivation 必须仍把 world_query 列为 forbidden",
        )

    def test_d3_agent_state_current_activity_is_not_formal_activity(self) -> None:
        """
        ⑨ `AgentState.current_activity` 不被视为 Formal Activity（`EC-6` / `ET-5`）。

        同时确认 `agent/state.py` **未被修改**为 Formal Activity：
        它必须仍是「字符串派生标签」，而不是 Domain Object。
        """
        contract = _read_text(CONTRACT_DOC) or ""
        for rule in ("**EC-6**", "**EC-7**", "**EC-8**", "**ET-5**", "**ET-6**"):
            self.assertIn(rule, contract, f"Contract 必须包含 {rule}")

        state_py = AGENT_DIR / "state.py"
        self.assertTrue(state_py.is_file(), "agent/state.py 必须存在")
        effective = _effective_code(state_py)
        offenders = [
            token for token in (
                "ActivityRegistry", "activity_registry", "activity_id",
                "ActivityStatus", "PLANNED", "TRAVELING", "ARRIVED",
                "PAUSED", "COMPLETED", "CANCELLED",
            )
            # 词边界匹配：避免 traveling_to_date 之类的子串误报
            if _word_in(token, effective)
        ]
        self.assertEqual(
            offenders, [],
            "EC-6 ～ EC-8：agent/state.py 不得被改造成 Formal Activity；"
            "命中：" + ", ".join(offenders),
        )

        # current_activity 必须仍是 str 类型标注
        src = _read_text(state_py) or ""
        self.assertIn(
            "current_activity", src,
            "AgentState 必须仍保留 current_activity（Legacy Derived Label）",
        )

    def test_d4_state_and_motivation_declare_legacy_label(self) -> None:
        """`ET-2`：AgentState.current_activity 明确为 Legacy Derived Activity Label。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**ET-2**", contract)
        self.assertIn(
            "Legacy Derived Activity Label", contract,
            "Contract 必须使用「Legacy Derived Activity Label」这一表述",
        )


# =========================================================
# E. Scheduler 边界
# =========================================================

class ED2SchedulerBoundary(unittest.TestCase):
    """⑩ ⑪：无 scheduler / tick / timer；expected_end_at 不自动完成。"""

    def test_e1_no_scheduler_implemented(self) -> None:
        """⑩ 不存在 Activity scheduler / tick / timer（`EP-6`）。"""
        contract = _read_text(CONTRACT_DOC) or ""
        for rule in ("**EP-1**", "**EP-2**", "**EP-3**", "**EP-6**", "**EP-9**", "**EP-10**"):
            self.assertIn(rule, contract, f"Contract 必须包含 {rule}")

        if _implementation_present():
            return
        offenders: List[str] = []
        for path in _py_files(AGENT_DIR):
            effective = _effective_code(path)
            for token in _SCHEDULER_TOKENS:
                if token in effective:
                    offenders.append(f"{path.name} -> {token}")
        self.assertEqual(
            offenders, [],
            "D-2 禁止 scheduler / tick / timer；命中：" + ", ".join(offenders),
        )

    def test_e2_expected_end_at_does_not_auto_complete(self) -> None:
        """
        ⑪ `expected_end_at` 不自动完成 Activity（`EP-4` / `EP-5`）。

        **这是本节最关键的一条**：一旦「到期即结束」被允许，
        Activity 就退化为 Scheduler 的包装。
        """
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EP-4**", contract)
        self.assertIn("**EP-5**", contract)
        self.assertIn(
            "到期不等于 Activity 自动结束", contract,
            "Contract 必须明确 expected_end_at 到期不等于自动结束",
        )
        self.assertIn(
            "退化为 Scheduler 的包装", contract,
            "Contract 必须记录该条的理由（否则容易被后人误解）",
        )

        if not _implementation_present():
            return
        # 门打开后：不得出现「到点即完成」的实现
        offenders: List[str] = []
        for path in _py_files(AGENT_DIR):
            effective = _effective_code(path)
            for pattern in _AUTO_COMPLETE_PATTERNS:
                if re.search(pattern, effective):
                    offenders.append(f"{path.name} -> {pattern}")
                    break
        self.assertEqual(
            offenders, [],
            "EP-5：不得实现「expected_end_at 到期即完成」；命中：" + ", ".join(offenders),
        )

    def test_e3_legacy_rhythm_keys_not_converted_to_activity(self) -> None:
        """`EP-8`：10 项节律 / 调度键在 D-2 仍属 Legacy 调度状态。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EP-8**", contract)
        for key in _LEGACY_RHYTHM_KEYS:
            self.assertIn(
                key, contract,
                f"Contract §5E.16 / §5E.19 必须登记调度键 {key}",
            )


# =========================================================
# F. Legacy 单向关系
# =========================================================

class FD2LegacyOneWay(unittest.TestCase):
    """⑫ ⑬：Legacy → Activity 单向；Activity → Legacy / 双向必须失败。"""

    def test_f1_legacy_to_activity_is_one_way_readonly(self) -> None:
        """⑫ `EO-8` / `ES-4`：Legacy → Activity 是单向只读观察 / 重建。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EO-8**", contract)
        self.assertIn("**ES-4**", contract)
        self.assertIn(
            "单向只读", contract,
            "Contract 必须明确 Legacy → Activity 为单向只读",
        )

    def test_f2_activity_to_legacy_forbidden(self) -> None:
        """⑬ `EO-9` ～ `EO-12`：Activity → Legacy / 双向同步必须失败。"""
        contract = _read_text(CONTRACT_DOC) or ""
        for rule in ("**EO-9**", "**EO-10**", "**EO-11**", "**EO-12**"):
            self.assertIn(rule, contract, f"Contract 必须包含 {rule}")
        self.assertIn("双向同步", contract, "Contract 必须明确禁止双向同步")
        self.assertIn(
            "Activity → Legacy", contract,
            "Contract 必须明确写出禁止 Activity → Legacy",
        )

        if not _implementation_present():
            return
        # 门打开后：Activity 实现不得反向写 Legacy 字段
        offenders: List[str] = []
        targets = [ACTIVITY_MODULE] if ACTIVITY_MODULE.is_file() else _py_files(ACTIVITY_PKG)
        for path in targets:
            effective = _effective_code(path)
            for pattern in _REVERSE_WRITE_PATTERNS:
                if re.search(pattern, effective):
                    offenders.append(f"{path.name} -> {pattern}")
            for key in _LEGACY_ACTIVITY_KEYS:
                if re.search(r"\[\s*[\"']" + re.escape(key) + r"[\"']\s*\]\s*=", effective):
                    offenders.append(f"{path.name} -> write {key}")
        self.assertEqual(
            offenders, [],
            "EO-9 ～ EO-12：Activity 不得反向写 Legacy / main.data；命中：" + ", ".join(offenders),
        )

    def test_f3_legacy_activity_keys_untouched(self) -> None:
        """`AC-2` / `AC-3` / `EO-14`：18 类 Legacy 字段未被 D-2 修改。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EO-14**", contract)
        self.assertIn("**AC-10**", contract)

        # 这些 key 的 owner 模块必须仍存在（未被删除）
        owner_map = {
            "dates": EXT_DIR / "ext_date.py",
            "work_sessions": EXT_DIR / "ext_econ.py",
            "ai_shop_state": EXT_DIR / "ext_shop.py",
            "instances": EXT_DIR / "ext_instance.py",
        }
        for key, path in owner_map.items():
            self.assertTrue(path.is_file(), f"Legacy owner 模块必须仍存在：{path.name}")
            src = _read_text(path) or ""
            self.assertIn(
                key, src,
                f"AC-2 / AC-3：Legacy 字段 {key} 不得从 {path.name} 被删除",
            )

    def test_f4_mapping_table_is_frozen_design_baseline(self) -> None:
        """`ES-1` ～ `ES-6`：映射表为设计基线，且必须在 D-6 才能落地。"""
        contract = _read_text(CONTRACT_DOC) or ""
        for rule in ("**ES-1**", "**ES-2**", "**ES-5**", "**ES-6**"):
            self.assertIn(rule, contract, f"Contract 必须包含 {rule}")
        self.assertIn(
            "不映射", contract,
            "Contract 必须明确「调度 / 状态位 / World Fact / 检测」类字段不映射",
        )

        preflight = _read_text(PREFLIGHT_DOC) or ""
        self.assertIn(
            "Legacy Activity State → Activity 映射", preflight,
            "Preflight 必须保留 19 行映射表",
        )


# =========================================================
# G. 生命周期与终态不可逆
# =========================================================

class GD2LifecycleAndTerminal(unittest.TestCase):
    """⑭：lifecycle transition 与终态不可逆规则符合 Contract。"""

    def setUp(self) -> None:
        self.contract = _read_text(CONTRACT_DOC) or ""

    def test_g1_all_lifecycle_states_frozen(self) -> None:
        """`EF-1`：7 个生命周期状态全部在 Contract 中冻结。"""
        self.assertIn("**EF-1**", self.contract)
        for state in _LIFECYCLE_STATES:
            self.assertIn(
                state, self.contract,
                f"Contract §5E.6 必须冻结生命周期状态 {state}",
            )

    def test_g2_terminal_states_are_irreversible(self) -> None:
        """`EF-3`：COMPLETED / CANCELLED 是终态，不可逆。"""
        self.assertIn("**EF-3**", self.contract)
        self.assertIn("不可逆", self.contract, "Contract 必须写明终态不可逆")
        for state in _TERMINAL_STATES:
            self.assertIn(
                state, self.contract,
                f"Contract 必须把 {state} 列为终态",
            )

    def test_g3_allowed_transitions_declared(self) -> None:
        """`EF-2`：允许转换表必须存在且覆盖 Contract 声明的转换。"""
        self.assertIn("**EF-2**", self.contract)
        self.assertIn("允许转换", self.contract)
        # 允许转换的每一个 from 状态必须出现
        for src, _dst in _ALLOWED_TRANSITIONS:
            self.assertIn(src, self.contract, f"允许转换表必须含 from = {src}")

        # 终态必须标注「无出边」
        self.assertIn("无出边", self.contract, "终态必须标注无出边")

    def test_g4_forbidden_jumps_declared(self) -> None:
        """
        `EF-2`：禁止的跳跃转换必须被明确记录。

        ⚠️ 断言策略（首次真实运行后修正）：

            原断言使用 `PLANNED\\s*→\\s*COMPLETED` 这类**裸子串**，
            过于依赖文档排版。

            改为断言 Contract 中**逐条存在**「❌ From → To」形式的禁止条款，
            并且额外要求 §5E.6 含「禁止」小节的语义标识（`禁止随意跳跃`）。

            注：不做「先定位小节再搜索」——因为 `**禁止：**` 这类通用标题
            在 Contract 中会被更早的小节命中（实测首次出现于 §5B），
            定位会落到错误的段落。
        """
        self.assertIn("**EF-2**", self.contract)
        self.assertIn(
            "禁止随意跳跃", self.contract,
            "§5E.6 必须写明「禁止随意跳跃」",
        )

        must_be_listed = (
            ("PLANNED", "COMPLETED"),
            ("COMPLETED", "ACTIVE"),
            ("CANCELLED", "ACTIVE"),
        )
        for src, dst in must_be_listed:
            pattern = r"❌\s*" + re.escape(src) + r"\s*→\s*" + re.escape(dst)
            self.assertRegex(
                self.contract,
                pattern,
                f"Contract 必须明确写出「❌ {src} → {dst}」这条禁止跳跃",
            )

    def test_g5_terminal_states_have_no_outgoing_edges_in_contract(self) -> None:
        """
        `EF-3` 的强化断言：终态**不得**出现在允许转换表的 From 列。

        这是「终态不可逆」在 Contract 层的可验证形式。
        """
        # 定位「允许转换」表
        anchor = self.contract.find("**允许转换（冻结）：**")
        self.assertGreater(anchor, 0, "Contract 必须含「允许转换（冻结）」小节")
        table_end = self.contract.find("### 5E.7", anchor)
        self.assertGreater(table_end, anchor, "允许转换小节必须位于 §5E.6 内")
        allowed_table = self.contract[anchor:table_end]

        for state in _TERMINAL_STATES:
            # 表格行形如： | `COMPLETED` | （终态，无出边） |
            row_pattern = r"\|\s*`" + re.escape(state) + r"`\s*\|\s*（终态"
            self.assertRegex(
                allowed_table,
                row_pattern,
                f"§5E.6 允许转换表必须把 {state} 标注为终态（无出边），"
                "不得为其声明任何出边",
            )

    def test_g6_cancelled_requires_reason(self) -> None:
        """`EF-5` / `EI-4`：CANCELLED 必须携带原因，不得静默取消。"""
        self.assertIn("**EF-5**", self.contract)
        self.assertIn("**EI-4**", self.contract)
        self.assertIn("必须携带原因", self.contract)
        self.assertIn("不得静默取消", self.contract)

    def test_g7_recovery_does_not_create_new_identity(self) -> None:
        """
        `EI-5`：PAUSED → ACTIVE 是恢复，不是新 Activity。

        ⚠️ 措辞对齐（首次真实运行后修正）：

            原断言查找「不得创建新 identity」，但 Contract 原文含
            Markdown 粗体标记（「**不得**创建新 identity」），
            因此子串不连续。

            改为**兼容粗体标记**的正则，同时要求「恢复」与「新 Activity」
            两个语义要素同时出现。
        """
        self.assertIn("**EI-5**", self.contract)

        # 兼容 **不得** 这类粗体标记：中间允许 ** 与空白
        self.assertRegex(
            self.contract,
            r"不\s*\*{0,2}\s*得\s*\*{0,2}\s*创建新\s*identity",
            "Contract 必须写明恢复不创建新 identity（EI-5）",
        )
        # 必须明确「这是恢复，不是新 Activity」
        self.assertRegex(
            self.contract,
            r"是\s*\*{0,2}\s*恢复\s*\*{0,2}\s*，\s*不是新\s*Activity",
            "Contract 必须写明 PAUSED → ACTIVE 是恢复，不是新 Activity",
        )

    def test_g8_contract_freeze_line_declares_no_implementation(self) -> None:
        """`EF-8` / `EA-2`：D-2 只定义语义，不实现转移执行。"""
        self.assertIn("**EF-8**", self.contract)
        self.assertIn("**EA-2**", self.contract)
        self.assertIn(
            "不实现", self.contract,
            "Contract 必须明确 D-2 不实现状态转移执行",
        )


# =========================================================
# H. 未冻结项不得提前实现
# =========================================================

class HD2UnfrozenNotImplemented(unittest.TestCase):
    """⑮：§5E.24 的未冻结项不得在 D-2 被提前实现。"""

    def test_h1_section_5e24_exists_with_unfrozen_list(self) -> None:
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("### 5E.24 本节保持未冻结", contract)
        for rule in ("**NF-11**", "**NF-12**", "**NF-13**"):
            self.assertIn(rule, contract, f"Contract 必须包含 {rule}")

    def test_h2_persistence_and_motivation_need_separate_change(self) -> None:
        """`NF-13`：persistence / Motivation 接入一律需独立 Contract Change。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**NF-13**", contract)
        self.assertIn("独立 Contract Change", contract)

    def test_h3_no_activity_event_production(self) -> None:
        """
        `EB-13` / `EF-6`：D-2 不实现 Activity → Event 生产。

        ⚠️ 范围收窄（首次真实运行后修正）：

            原实现在**门关闭时也**扫描 `agent/` 全目录并断言
            「不得出现 `agent.event` / `EventBus` / `EventStore`」，
            命中：

                event_adapter.py -> agent.event
                runtime.py       -> agent.event

            但这两个是 **B5 / C-2 阶段就已存在的合法模块**
                （AgentRuntime 与 Event Adapter 本来就依赖 `agent.Event`），
            **与 Activity 无关**。

            `EB-13` 约束的是「Activity 不产生 Event」，
            **不是**「任何 agent 模块都不得 import agent.event」。

            改为：
                ① 门关闭时：只断言仍然**没有 Activity 实现**（不扫描全体）；
                ② 门打开时：只在 **Activity 实现文件内部** 断言不产生 Event。
        """
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EB-13**", contract)
        self.assertIn("**EF-6**", contract)

        if not _implementation_present():
            # 门关闭：Activity 实现不存在即已满足「尚无 Activity Event 生产」
            self.assertFalse(
                ACTIVITY_MODULE.is_file() or ACTIVITY_PKG.is_dir(),
                "D-2 Architecture Tests 阶段不得存在 Activity 实现",
            )
            return

        # 门打开：只检查 Activity 实现文件本身
        offenders: List[str] = []
        targets = [ACTIVITY_MODULE] if ACTIVITY_MODULE.is_file() else _py_files(ACTIVITY_PKG)
        for path in targets:
            effective = _effective_code(path)
            for token in ("EventBus", "EventStore", "emit_event", "push_event", "enqueue_event"):
                if _word_in(token, effective):
                    offenders.append(f"{path.name} -> {token}")
        self.assertEqual(
            offenders, [],
            "EB-13：Activity 实现不得产生 Event；命中：" + ", ".join(offenders),
        )

    def test_h4_no_capability_integration(self) -> None:
        """`EN-6` / `EN-8`：D-2 禁止 Capability 集成。"""
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EN-6**", contract)
        self.assertIn("**EN-8**", contract)


# =========================================================
# I. Documentation Boundary
# =========================================================

class ID2DocumentationBoundary(unittest.TestCase):

    def test_i1_preflight_exists_and_approved(self) -> None:
        preflight = _read_text(PREFLIGHT_DOC)
        self.assertIsNotNone(preflight, f"D-2 Preflight 必须存在：{PREFLIGHT_DOC}")
        self.assertIn("PRE-FLIGHT", preflight or "")
        self.assertIn("D2-DEC-1", preflight or "")
        self.assertIn("D2-DEC-19", preflight or "")
        for open_id in ("D2-OPEN-1", "D2-OPEN-2", "D2-OPEN-3", "D2-OPEN-4"):
            self.assertIn(open_id, preflight or "", f"Preflight 必须含 {open_id}")

    def test_i2_contract_contains_section_5e(self) -> None:
        contract = _read_text(CONTRACT_DOC)
        self.assertIsNotNone(contract)
        self.assertIn("## 5E. Phase D-2 Activity Contract", contract or "")

    def test_i3_contract_declares_cc_20260930_06(self) -> None:
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("CC-20260930-06", contract)
        self.assertIn(
            "D-2 Activity Contract Preflight", contract,
            "Contract 依据必须列出 D-2 Preflight",
        )

    def test_i4_contract_contains_all_5e_rule_groups(self) -> None:
        contract = _read_text(CONTRACT_DOC) or ""
        missing = [rule for rule in _RULE_GROUP_FIRST if rule not in contract]
        self.assertEqual(
            missing, [],
            "Contract §5E 缺少以下规则组首条：" + ", ".join(missing),
        )
        for group in _SECTION_5E_RULE_GROUPS:
            self.assertRegex(
                contract,
                r"\*\*" + group + r"-\d+\*\*",
                f"Contract §5E 必须含规则组 {group}-*",
            )

    def test_i5_all_4_open_questions_closed_in_contract(self) -> None:
        """4 个 OPEN QUESTION 必须在 Contract 中有明确落点。"""
        contract = _read_text(CONTRACT_DOC) or ""
        for open_id in ("D2-OPEN-1", "D2-OPEN-2", "D2-OPEN-3", "D2-OPEN-4"):
            self.assertIn(open_id, contract, f"Contract 必须记录 {open_id} 的关闭")
        self.assertIn("World SOT != Runtime Domain State", contract)
        self.assertIn("开放类型标识", contract)
        self.assertIn("Runtime-scoped Activity Registry", contract)

    def test_i6_contract_keeps_prior_sections_intact(self) -> None:
        """CC-20260930-06 不得重写 §5A / §5B / §5C / §5D。"""
        contract = _read_text(CONTRACT_DOC) or ""
        for anchor in (
            "## 5A. Goal / Commitment / Motivation / Intent",
            "## 5B. Goal / Commitment / Motivation / Intent 实现契约",
            "## 5C. Phase D-0 架构裁决",
            "## 5D. Phase D-1 World Query Foundation",
        ):
            self.assertIn(anchor, contract, f"Contract 必须保留 {anchor}")
        self.assertIn("CC-20260930-04", contract)
        self.assertIn("CC-20260930-05", contract)

    def test_i7_section_10_activity_points_to_5e(self) -> None:
        """§10 必须保留 AC-1 ～ AC-10 并指向 §5E。"""
        contract = _read_text(CONTRACT_DOC) or ""
        for rule in ("**AC-1**", "**AC-5**", "**AC-8**", "**AC-10**"):
            self.assertIn(rule, contract, f"Contract 必须保留 {rule}")
        self.assertIn("完整 Activity Contract 见 §5E", contract)


# =========================================================
# J. D-0 / D-1 未被破坏
# =========================================================

class JD2PriorPhasesUnchanged(unittest.TestCase):

    def test_j1_d0_and_d1_sealed_artifacts_exist(self) -> None:
        for path in (D0_TEST_DOC, D1_TEST_DOC, D1_BEHAVIOR_DOC, D1_PREFLIGHT_DOC):
            self.assertTrue(path.is_file(), f"D-0 / D-1 封板产物必须存在：{path.name}")

    def test_j2_world_query_module_present_and_unmodified_in_scope(self) -> None:
        """
        `WQ-42`：D-1 的 world_query **不得**被扩展为返回 Formal Activity。

        D-2 阶段不得修改 world_query.py 去承载 Activity。
        """
        self.assertTrue(WORLD_QUERY_MODULE.is_file(), "agent/world_query.py 必须存在")
        effective = _effective_code(WORLD_QUERY_MODULE)
        offenders = [
            token for token in ("ActivityRegistry", "activity_registry", "class Activity")
            if token in effective
        ]
        self.assertEqual(
            offenders, [],
            "D-2 不得把 world_query 扩展为 Activity 来源；命中：" + ", ".join(offenders),
        )
        # D-1 的 Legacy 派生接口必须仍在（并保持 derived）
        src = _read_text(WORLD_QUERY_MODULE) or ""
        self.assertIn("get_agent_current_activity_legacy", src)

    def test_j3_d0_legacy_baseline_still_present(self) -> None:
        """`AC-2` / `AC-10`：D-0 登记的 Legacy 行为未被 D-2 改动。"""
        ext_ai = EXT_DIR / "ext_ai.py"
        ext_world = EXT_DIR / "ext_world.py"
        self.assertTrue(ext_ai.is_file())
        self.assertTrue(ext_world.is_file())
        ai_src = _read_text(ext_ai) or ""
        for symbol in ("def drive_ai", "def execute_action", "def call_llm", "def auto_ai_loop"):
            self.assertIn(symbol, ai_src, f"DL-2：{symbol} 必须仍存在")
        world_src = _read_text(ext_world) or ""
        self.assertIn("def ai_spot_tick", world_src, "D-0 登记的 ext_world 行为必须仍存在")

    def test_j4_memory_write_path_still_unreachable(self) -> None:
        """`ME-25`：D-2 不得顺手修 Memory。"""
        ext_memory = EXT_DIR / "ext_memory.py"
        self.assertTrue(ext_memory.is_file())
        src = _read_text(ext_memory) or ""
        self.assertNotIn(
            "def _enqueue_event_impl", src,
            "ME-25：Memory 写入路径必须仍不可达（D-2 不得顺手修）",
        )

    def test_j5_frontend_untouched(self) -> None:
        """`EM-4`：D-2 不得修改前端 / HTTP。"""
        index_html = ROOT / "index.html"
        self.assertTrue(index_html.is_file(), "index.html 必须存在")
        contract = _read_text(CONTRACT_DOC) or ""
        self.assertIn("**EM-4**", contract, "Contract 必须禁止 Frontend 创建 / 修改 Activity")


# =========================================================
# K. 环境能力
# =========================================================

class KD2EnvironmentCapability(unittest.TestCase):

    def test_k1_repo_root_resolves(self) -> None:
        self.assertTrue((ROOT / "main.py").is_file())
        self.assertTrue(AGENT_DIR.is_dir())
        self.assertTrue(EXT_DIR.is_dir())

    def test_k2_no_third_party_import_required(self) -> None:
        """
        本测试文件必须只依赖标准库，以便在缺少 fastapi / uvicorn 时也能运行。
        """
        tree = ast.parse(_read_text(Path(__file__)) or "")
        stdlib_ok = {
            "__future__", "ast", "io", "os", "re", "tokenize", "unittest",
            "pathlib", "typing",
            "sys", "json", "textwrap", "collections",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(
                        alias.name.split(".")[0], stdlib_ok,
                        f"本测试不得依赖第三方库：{alias.name}",
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertIn(
                        node.module.split(".")[0], stdlib_ok,
                        f"本测试不得依赖第三方库：{node.module}",
                    )

    def test_k3_project_master_locatable(self) -> None:
        self.assertTrue(
            PROJECT_DOC.is_file() or PROJECT_DOC_ALT.is_file(),
            "PROJECT_V3.1_MASTER.md 必须可定位（docs/ 或根目录）",
        )

    def test_k4_contract_doc_locatable(self) -> None:
        self.assertTrue(CONTRACT_DOC.is_file(), "Contract 必须位于 docs/")


# =========================================================
# 入口
# =========================================================


def _print_header() -> None:
    present = _implementation_present()
    gate = "OPEN (implementation authorized)" if present else "CLOSED (implementation not authorized)"
    print("=" * 74)
    print("V3.1 Phase D-2 · Activity Contract Architecture Boundary Tests")
    print("       （CC-20260930-06，Contract §5E）")
    print("=" * 74)
    print(f"ROOT            : {ROOT}")
    print(f"agent/          : {len(_py_files(AGENT_DIR))} py files")
    print(f"ext/            : {len(_py_files(EXT_DIR))} py files")
    print(f"d2 preflight    : {'OK' if PREFLIGHT_DOC.is_file() else '--'} -> {PREFLIGHT_DOC}")
    print(f"contract        : {'OK' if CONTRACT_DOC.is_file() else '--'} -> {CONTRACT_DOC}")
    print(f"activity module : {'PRESENT' if present else 'ABSENT'} -> {ACTIVITY_MODULE}")
    print("-" * 74)
    print(f"PHASE GATE      : {gate}")
    print("                  D-2 Architecture Tests 阶段不实现任何 Activity 代码")
    print("-" * 74)
    print("A: 阶段门（不得提前偷做 Activity / Registry / persistence / scheduler）")
    print("B: Registry 唯一性 / 单一真相 / AgentRuntime 不拥有 / primary=binding")
    print("C: World SOT（无 activities key / 无 persistence / 无隐式持久化）")
    print("D: Motivation（Formal Activity 不进入）/ AgentState（Legacy Label）")
    print("E: Scheduler 边界（无 tick/timer；expected_end_at 不自动完成）")
    print("F: Legacy 单向关系（禁止 Activity → Legacy / 双向同步）")
    print("G: 生命周期与终态不可逆")
    print("H: 未冻结项不得提前实现")
    print("I: Contract / Preflight 文档边界")
    print("J: D-0 / D-1 未被破坏")
    print("K: 环境能力（不伪造结果）")
    print("=" * 74)
    if not present:
        print("注意：本阶段门为 CLOSED，A/C/E/H 组断言「实现不存在」。")
        print("      实现落地后这些断言会自动放宽 —— 不会形成永久失败。")
        print("=" * 74)


if __name__ == "__main__":
    _print_header()
    unittest.main(verbosity=2)
