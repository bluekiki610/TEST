# -*- coding: utf-8 -*-
"""
agent/world_query.py - Phase D-1: World Query Foundation
========================================================

依据：docs/V3.1_ARCHITECTURE_CONTRACT.md §5D（CC-20260930-05）
      docs/D1_WORLD_QUERY_PREFLIGHT.md（APPROVED）

--------------------------------------------------------------------------
D-1 的唯一目标
--------------------------------------------------------------------------

    让 Agent Core 能通过统一、**只读**、无 LLM、无行为决策、
    无 World mutation 的接口，询问当前世界事实。

--------------------------------------------------------------------------
硬性边界（Contract §5D，违反即为架构违规）
--------------------------------------------------------------------------

    WQ-5 ～ WQ-9    READ ONLY；无任何副作用（含清理、裁剪、修复、归一化）
                    不调用 LLM / Decision / Capability
                    不修改 main.data；不调用 save_data()
                    不调用任何写入型 helper
    WQ-75           Dependency Injection：不 import main、不 import ext_*、
                    不持有全局状态
    WQ-101/102/103  不得保存 data 引用；返回值不得暴露内部可变引用；
                    只读是约定 + Architecture Tests，**不是语言级保证**
    WQ-79          不返回 main.data 的任何子对象引用
    WQ-105 ～ 108  不得读取 AgentState
    WQ-32/35       不得被 Provider / ContextAssembler 调用
    WQ-37 ～ 41    不是 Event；不产生 / 不消费 Event
    WQ-42 ～ 46    不实现 Activity；不返回正式 Activity 对象
    WQ-47 ～ 51    不实现 World Command
    WQ-52 ～ 55    AgentRuntime 暂不接入；本模块可独立测试
    WQ-56 ～ 60    不修改现有 HTTP 接口 / 前端
    WQ-61 ～ 68    不修 World Tick；不触碰 Memory；不新增 main.data key
    WQ-81 ～ 84    O(buildings × rooms) 反查禁止接入高频 tick / loop
    WQ-90 ～ 93    只回答「现在是什么」；禁止 route / planning / selection /
                    ranking / recommendation 类语义

--------------------------------------------------------------------------
D-1 静态验证策略（Contract D1G-11 ～ D1G-15、D1G-16 ～ D1G-22）
--------------------------------------------------------------------------

    这是 **D-1 的静态验证策略**，**不是永久 Python 架构原则**。

    为换取「静态可验证的只读性」，本模块**不使用任何就地修改 dict / list 的写法**：

        ✗ 追加 / 扩展 / 插入 / 删除 / 弹出 / 排序 / 反转 / 清空
        ✗ 带默认值的键设置 / 批量合并
        ✗ 下标赋值 / 下标删除

    允许：dict / list 字面量构造、列表推导、`.get()`、`next()`、`len()`、切片。

    因此：本模块**不通过调用会就地修改的现有 helper 完成反查**，
    反查逻辑自行实现（列表推导 + next），代价是重复少量线性扫描逻辑。

    ⚠️ 注意：本 docstring 刻意**不写出禁止模式的字面示例**，
       因为静态验证器是文本级的，字面示例会被误判为真实违规
       （参见 Contract `D1G-16` ～ `D1G-20`）。

--------------------------------------------------------------------------
World Fact 的来源分类（Contract §5D.1）
--------------------------------------------------------------------------

    FACT      main.data 直接存储的当前事实          → derived=False
    FACT      runtime source（世界时钟）            → derived=False
    DERIVED   既定确定性规则得到的只读投影          → derived=True
    HISTORY   不是 World Fact（Phase E）            → 本模块不返回
    CACHE     D-1 禁止产生                          → 本模块不产生

--------------------------------------------------------------------------
五态核心 + 可见性结果（Contract §5D.6 / §5D.6.1）
--------------------------------------------------------------------------

    status  = 认识论结论（世界 / schema 能否回答）
              FOUND / ABSENT / UNKNOWN / UNSUPPORTED / AMBIGUOUS
    outcome = 授权结论（requester 是否被允许知道）
              ALLOWED / FORBIDDEN

    两者**正交**：FORBIDDEN ≠ UNKNOWN ≠ ABSENT；FORBIDDEN ∉ 五态核心。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# =========================================================
# 1. 状态常量（五态核心，恰好 5 个）
# =========================================================

# 世界 / schema 能否回答（认识论结论）
STATUS_FOUND = "FOUND"
STATUS_ABSENT = "ABSENT"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_UNSUPPORTED = "UNSUPPORTED"
STATUS_AMBIGUOUS = "AMBIGUOUS"

STATUS_CORE: Tuple[str, ...] = (
    STATUS_FOUND,
    STATUS_ABSENT,
    STATUS_UNKNOWN,
    STATUS_UNSUPPORTED,
    STATUS_AMBIGUOUS,
)

# 可见性 / 授权结论（与 status 正交，不属于五态核心）
OUTCOME_ALLOWED = "ALLOWED"
OUTCOME_FORBIDDEN = "FORBIDDEN"

OUTCOME_VALUES: Tuple[str, ...] = (
    OUTCOME_ALLOWED,
    OUTCOME_FORBIDDEN,
)

# =========================================================
# 2. 固定诊断文本
# =========================================================

# 注意：这些文本用于 notes，便于审计；它们同时也是「反模式守卫」的判定依据。
_UNSUPPORTED_MAP = (
    "当前 schema 不存在 World → Map 关系：buildings.region 只是标签字符串，"
    "不是 map_id。属 UNSUPPORTED（不得猜测）。"
)
_UNSUPPORTED_NPC_LOCATION = (
    "当前 schema 中 NPC 没有位置 / 状态字段（npcs 仅按 building_id 分组）。"
    "属 UNSUPPORTED（不得猜测）。"
)
_UNSUPPORTED_PURPOSE_SEARCH = (
    "当前 schema 不存在 purpose / 营业时间 / 用途字段，"
    "无法按用途或营业状态检索地点。属 UNSUPPORTED（不得猜测）。"
)
_UNSUPPORTED_RELATIONSHIP = (
    "当前 schema 只有 affection 数值，没有 relationship 结构。"
    "属 UNSUPPORTED（不得猜测）。"
)
_UNSUPPORTED_ROUTE = (
    "当前 schema 没有路径 / 距离 / 连通性数据，无法计算路线。"
    "属 UNSUPPORTED（不得猜测）。"
)
_UNSUPPORTED_AVAILABLE_PLACES = (
    "当前 schema 没有可达性建模，无法计算「可去的地方」。"
    "属 UNSUPPORTED（不得猜测）。"
)
_UNSUPPORTED_ACTIVITY = (
    "正式 Activity 属 D-2，当前尚未实现。属 UNSUPPORTED。"
)
_FORBIDDEN_NOTE = (
    "该事实不在当前 requester 的可见范围内（visibility / authorization 结论）。"
    "注意：FORBIDDEN 表示「不被允许知道」，"
    "**不等于**「该事实不存在」，也不等于 UNKNOWN。"
)

# 反模式守卫：这些语义属于 Decision / Planning，不是 World Query（WQ-90 ～ WQ-93）
_FORBIDDEN_REQUEST_KEYS: Tuple[str, ...] = (
    "route",
    "plan",
    "choose",
    "decide",
    "suggest",
    "recommend",
    "rank",
    "best",
    "goal",
    "motivation",
    "intent",
    "command",
    "execute",
    "send",
)


# =========================================================
# 3. QueryResult（Contract §5D.6）
# =========================================================

@dataclass(frozen=True)
class QueryResult:
    """
    一次 World Query 的结构化结果。

    冻结（frozen）是刻意的：防止调用方就地修改结果对象。
    但 `value` 若为 list / dict 仍可通过其自身方法被改动 ——
    因此返回 list / dict 时**必须**使用新构造的副本（见各函数实现），
    绝不返回 main.data 的子对象引用（WQ-79 / WQ-103）。
    """

    value: Any = None
    status: str = STATUS_UNKNOWN
    outcome: str = OUTCOME_ALLOWED
    source: str = ""
    derived: bool = False
    as_of: float = 0.0
    notes: str = ""

    # --- 便捷判定（只读，不修改任何东西） -----------------

    def is_found(self) -> bool:
        return self.status == STATUS_FOUND and self.outcome == OUTCOME_ALLOWED

    def is_forbidden(self) -> bool:
        return self.outcome == OUTCOME_FORBIDDEN

    def to_dict(self) -> Dict[str, Any]:
        """
        只读序列化。

        使用 dict 字面量构造（不就地修改），符合 D-1 静态验证策略。
        """
        return {
            "value": self.value,
            "status": self.status,
            "outcome": self.outcome,
            "source": self.source,
            "derived": self.derived,
            "as_of": self.as_of,
            "notes": self.notes,
        }


# =========================================================
# 4. 内部只读工具
# =========================================================

_BEIJING_TZ = timezone(timedelta(hours=8))
_UNKNOWN_TIME = "unknown"


def _fmt_beijing(ts: float) -> str:
    """把 epoch 秒格式化为北京时间字符串（UTC+8）。"""
    try:
        return datetime.fromtimestamp(ts, tz=_BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return _UNKNOWN_TIME


def _as_dict(value: Any) -> Dict[str, Any]:
    """只读转换：非 dict 一律视为空 dict（不修改入参）。"""
    if isinstance(value, dict):
        return value
    return {}


def _as_str(value: Any) -> str:
    """只读转换：非 str 一律视为空字符串。"""
    if isinstance(value, str):
        return value
    return ""


def _result(
    value: Any = None,
    status: str = STATUS_UNKNOWN,
    outcome: str = OUTCOME_ALLOWED,
    source: str = "",
    derived: bool = False,
    as_of: float = 0.0,
    notes: str = "",
) -> QueryResult:
    """构造 QueryResult 的统一入口（便于审计来源标注）。"""
    return QueryResult(
        value=value,
        status=status,
        outcome=outcome,
        source=source,
        derived=derived,
        as_of=as_of,
        notes=notes,
    )


def _forbidden(source: str, as_of: float = 0.0) -> QueryResult:
    """可见性拒绝：返回 FORBIDDEN（不得返回事实值，也不得推断「不存在」）。"""
    return _result(
        value=None,
        status=STATUS_UNSUPPORTED,
        outcome=OUTCOME_FORBIDDEN,
        source=source,
        derived=False,
        as_of=as_of,
        notes=_FORBIDDEN_NOTE,
    )


def _unknown(source: str, as_of: float = 0.0, notes: str = "") -> QueryResult:
    """理论上可回答，但当前事实不足。"""
    return _result(
        value=None,
        status=STATUS_UNKNOWN,
        outcome=OUTCOME_ALLOWED,
        source=source,
        derived=False,
        as_of=as_of,
        notes=notes,
    )


def _absent(source: str, as_of: float = 0.0, notes: str = "") -> QueryResult:
    """权威数据明确表明不存在。"""
    return _result(
        value=None,
        status=STATUS_ABSENT,
        outcome=OUTCOME_ALLOWED,
        source=source,
        derived=False,
        as_of=as_of,
        notes=notes,
    )


def _unsupported(source: str, notes: str, as_of: float = 0.0) -> QueryResult:
    """当前 schema / Query 能力根本不能回答。"""
    return _result(
        value=None,
        status=STATUS_UNSUPPORTED,
        outcome=OUTCOME_ALLOWED,
        source=source,
        derived=False,
        as_of=as_of,
        notes=notes,
    )


def _names_equal(left: str, right: str) -> bool:
    """只读名字比较：容忍两端空白差异。"""
    return _as_str(left).strip() == _as_str(right).strip()


def _owner_invites(requester: str, data: Dict[str, Any]) -> bool:
    """
    最小可见性判断（WQ-94）：requester 是否是该 owner 的 AI，
    或 requester 本人就是该 owner。

    只使用 user_ais（现有事实），不引入新的关系模型。
    """
    user_ais = _as_dict(data.get("user_ais"))
    req = _as_str(requester).strip()
    if not req:
        return False
    if req in user_ais:
        return True
    for _owner, ais in user_ais.items():
        if not isinstance(ais, list):
            continue
        for name in ais:
            if _names_equal(name, req):
                return True
    return False


def _owner_of(agent: str, data: Dict[str, Any]) -> str:
    """
    只读反查 agent → owner（不 import main）。

    注意：main.owner_of_ai 在运行时被 ext_admin 猴补丁替换过
    （D-0 D0-036），本模块**不依赖**该猴补丁行为，
    只按 user_ais 的静态事实回答。
    """
    user_ais = _as_dict(data.get("user_ais"))
    for owner, ais in user_ais.items():
        if not isinstance(ais, list):
            continue
        for name in ais:
            if _names_equal(name, agent):
                return _as_str(owner)
    return ""


def _agent_exists(agent: str, data: Dict[str, Any]) -> bool:
    """只读存在性判断。"""
    user_ais = _as_dict(data.get("user_ais"))
    for ais in user_ais.values():
        if not isinstance(ais, list):
            continue
        for name in ais:
            if _names_equal(name, agent):
                return True
    return False


def _agent_location(agent: str, data: Dict[str, Any]) -> str:
    """只读：main.data.ai_location[agent]（未做任何归一化）。"""
    locs = _as_dict(data.get("ai_location"))
    target = _as_str(agent).strip()
    for name, room in locs.items():
        if _names_equal(name, target):
            return _as_str(room)
    return ""


def _resolve_room(room: str, data: Dict[str, Any]) -> str:
    """
    只读房间名归一化（沿用 main.full_room_name 的语义，但不 import main）。

    返回：
        归一化后的房间全名；无法唯一确定时返回 ""。
    """
    wanted = _as_str(room).strip()
    if not wanted:
        return ""

    rooms = _as_dict(data.get("rooms"))
    if wanted in rooms:
        return wanted

    buildings = _as_dict(data.get("buildings"))

    # 精确匹配：房间名全等，或「建筑名·房间名」全等
    exact = [
        r
        for bid, b in buildings.items()
        if isinstance(b, dict)
        for r in (b.get("rooms") if isinstance(b.get("rooms"), list) else [])
        if isinstance(r, str)
        and (
            r == wanted
            or (_as_str(b.get("name")) and r == _as_str(b.get("name")) + "·" + wanted)
        )
    ]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return ""

    # 宽松匹配：房间名以「·wanted」结尾
    loose = [
        r
        for bid, b in buildings.items()
        if isinstance(b, dict)
        for r in (b.get("rooms") if isinstance(b.get("rooms"), list) else [])
        if isinstance(r, str) and r.endswith("·" + wanted)
    ]
    if len(loose) == 1:
        return loose[0]

    return ""


def _building_of_room(room: str, data: Dict[str, Any]) -> Optional[str]:
    """
    只读反查 room → building_id（O(buildings × rooms)）。

    ⚠️ 高频限制（WQ-81 / WQ-82）：调用方**不得**把它接入
       任何 scheduler / tick / polling loop。
    """
    wanted = _as_str(room).strip()
    if not wanted:
        return None
    buildings = _as_dict(data.get("buildings"))
    for bid, b in buildings.items():
        if not isinstance(b, dict):
            continue
        rooms = b.get("rooms")
        if isinstance(rooms, list) and wanted in rooms:
            return _as_str(bid)
    return None


def _building_candidates(key: str, data: Dict[str, Any]) -> List[str]:
    """
    只读建筑查找：id 全等 → name 全等 → name 子串（沿用 resolve_building 语义）。

    返回候选 id 列表（不修改任何东西）。
    """
    wanted = _as_str(key).strip()
    if not wanted:
        return []
    buildings = _as_dict(data.get("buildings"))
    if wanted in buildings:
        return [wanted]

    exact = [
        bid
        for bid, b in buildings.items()
        if isinstance(b, dict) and _as_str(b.get("name")) == wanted
    ]
    if exact:
        return exact

    return [
        bid
        for bid, b in buildings.items()
        if isinstance(b, dict) and wanted in _as_str(b.get("name"))
    ]


def _agent_following(agent: str, data: Dict[str, Any]) -> bool:
    """只读：agent 是否在 ai_follow 中（Legacy Activity State）。"""
    follows = _as_dict(data.get("ai_follow"))
    target = _as_str(agent).strip()
    return any(_names_equal(name, target) for name in follows.keys())


def _agent_working(agent: str, data: Dict[str, Any]) -> bool:
    """只读：agent 是否在 work_sessions 中（Legacy Activity State）。"""
    sessions = _as_dict(data.get("work_sessions"))
    target = _as_str(agent).strip()
    return any(_names_equal(name, target) for name in sessions.keys())


def _agent_dating(agent: str, data: Dict[str, Any]) -> bool:
    """只读：agent 是否有 status ∈ {active, coming} 的约会（Legacy Activity State）。"""
    dates = data.get("dates")
    if not isinstance(dates, list):
        return False
    target = _as_str(agent).strip()
    for entry in dates:
        if not isinstance(entry, dict):
            continue
        if _names_equal(entry.get("ai"), target) and entry.get("status") in ("active", "coming"):
            return True
    return False


def _derive_activity_legacy(agent: str, data: Dict[str, Any]) -> str:
    """
    只读：Legacy 活动推导（DERIVED）。

    与 agent/state.py 的 _derive_activity 保持**同一优先级语义**，
    但本模块不读取 AgentState（WQ-105 ～ WQ-108），因此自行只读推导。

    返回 legacy 活动标签；无法判定时返回 "idle"。
    """
    target = _as_str(agent).strip()

    dates = data.get("dates")
    if isinstance(dates, list):
        for entry in dates:
            if not isinstance(entry, dict):
                continue
            if not _names_equal(entry.get("ai"), target):
                continue
            status = _as_str(entry.get("status"))
            if status == "active":
                return "dating"
            if status == "coming":
                return "traveling_to_date"
            if status == "pending":
                return "waiting_for_date"

    if _agent_working(target, data):
        return "working"
    if _agent_following(target, data):
        return "following"

    shop_state = _as_dict(_as_dict(data.get("ai_shop_state")).get(target))
    if shop_state.get("cooldown_until"):
        return "shopping_cooldown"

    writing = _as_dict(_as_dict(data.get("writing_rhythm")).get(target))
    if writing.get("ready", False):
        return "thinking_to_write"

    story = _as_dict(_as_dict(data.get("story_rhythm")).get(target))
    if story.get("ready", False):
        return "thinking_story"

    return "idle"


# =========================================================
# 5. System / 反模式守卫
# =========================================================

def is_world_query_available() -> bool:
    """自描述：World Query Foundation 已建立（D-1）。"""
    return True


def describe_capabilities() -> Dict[str, Any]:
    """
    只读自描述（供审计 / 调试）。

    明确声明本模块的能力与**非**能力，避免被误用为万能接口。
    """
    return {
        "module": "agent.world_query",
        "phase": "D-1",
        "contract": "§5D (CC-20260930-05)",
        "read_only": True,
        "status_core": list(STATUS_CORE),
        "outcomes": list(OUTCOME_VALUES),
        "capabilities": (
            "Location",
            "People",
            "Time",
        ),
        "not_capabilities": (
            "route / distance / connectivity",
            "planning / selection / ranking / recommendation",
            "activity lifecycle",
            "world command / mutation",
            "event production or consumption",
            "memory recall",
        ),
        "notes": (
            "本模块只回答「现在是什么」。"
            "不回答「应该去哪 / 选谁 / 做什么」（WQ-90 ～ WQ-93）。"
        ),
    }


def is_decision_like_request(request: Any) -> bool:
    """
    反模式守卫（WQ-90 ～ WQ-93）：

    判定一个请求是否属于 Decision / Planning 类语义
    （route / plan / choose / decide / suggest / recommend / rank / best / …）。

    本模块**不执行**这类请求；调用方可据此在 Contract 层拒绝。

    只读：不修改 request。
    """
    if not isinstance(request, dict):
        return False
    for key in request.keys():
        for token in _FORBIDDEN_REQUEST_KEYS:
            if token in _as_str(key).lower():
                return True
    return False


def get_unsupported_capabilities() -> Dict[str, Any]:
    """
    只读：当前 schema 明确 `UNSUPPORTED` 的能力清单及其原因（WQ-110 / WQ-111）。

    该清单是**冻结**的：禁止为了让示例「看起来能跑」而临时创造字段。
    """
    return {
        "status": STATUS_UNSUPPORTED,
        "source": "main.data schema",
        "items": {
            "get_map_of_building": _UNSUPPORTED_MAP,
            "get_npc_location": _UNSUPPORTED_NPC_LOCATION,
            "search_places_by_purpose": _UNSUPPORTED_PURPOSE_SEARCH,
            "get_relationship": _UNSUPPORTED_RELATIONSHIP,
            "get_route": _UNSUPPORTED_ROUTE,
            "list_available_places": _UNSUPPORTED_AVAILABLE_PLACES,
            "get_activity": _UNSUPPORTED_ACTIVITY,
        },
    }


# =========================================================
# 6. Location 事实
# =========================================================

def get_agent_location(
    agent: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    AI 当前所在房间全名。`FACT`（main.data.ai_location）。

    可能的 status：
        FOUND     有位置且**能**归属到建筑
        UNKNOWN   有位置，但无法归属到任何建筑（
                  D-0 D0-027：ai_location 可能持有建筑名而非房间名）
        ABSENT    ai_location 中没有任何记录
    """
    src = "main.data.ai_location"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0

    if not _agent_exists(agent, data):
        return _absent(src, ts, notes="该 AI 不在 user_ais 中。")

    room = _agent_location(agent, data)
    if not room:
        return _absent(src, ts, notes="ai_location 中没有该 AI 的记录。")

    if room == "main":
        return _result(
            value=room,
            status=STATUS_FOUND,
            source=src,
            derived=False,
            as_of=ts,
            notes="main 是通信频道，不是物理地点。",
        )

    if _resolve_room(room, data):
        return _result(value=room, status=STATUS_FOUND, source=src, derived=False, as_of=ts)

    return _unknown(
        src, ts,
        notes=(
            f"ai_location[{agent}] = {room!r}，但该值无法解析为任何已知房间 / 建筑。"
            "保持原值返回，不做猜测（D0-027）。"
        ),
    )


def get_agent_owner(
    agent: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    AI 的 owner（`FACT`，来自 main.data.user_ais 的静态事实）。

    注意：不依赖 main.owner_of_ai 的猴补丁版本（D0-036）。
    """
    src = "main.data.user_ais"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    owner = _owner_of(agent, data)
    if owner:
        return _result(value=owner, status=STATUS_FOUND, source=src, derived=False, as_of=ts)
    return _absent(src, ts, notes="未在 user_ais 中找到该 AI。")


def get_building(
    key: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    按 id / name / name 子串查找建筑（`FACT`）。

    可能的 status：
        FOUND      唯一命中 → value 为建筑 dict 的**副本**
        AMBIGUOUS  多个候选 → 必须消歧（不得替调用方挑一个）
        ABSENT     无命中
    """
    src = "main.data.buildings"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0

    candidates = _building_candidates(key, data)
    if not candidates:
        return _absent(src, ts, notes=f"未找到匹配 {key!r} 的建筑。")

    if len(candidates) > 1:
        return _result(
            value=sorted(candidates),
            status=STATUS_AMBIGUOUS,
            source=src,
            derived=False,
            as_of=ts,
            notes=f"{key!r} 命中 {len(candidates)} 个建筑，需要消歧。",
        )

    bid = candidates[0]
    building = _as_dict(_as_dict(data.get("buildings")).get(bid))
    # 复制为新的 dict（浅拷贝 + 列表重建），不暴露 main.data 内部对象引用
    copy_of_building = {
        k: (list(v) if isinstance(v, list) else v)
        for k, v in building.items()
    }
    return _result(
        value=copy_of_building,
        status=STATUS_FOUND,
        source=src,
        derived=False,
        as_of=ts,
        notes=f"building_id = {bid}",
    )


def list_building_rooms(
    building: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """某建筑当前拥有的房间全名列表（`FACT`，直接读取 buildings[bid].rooms）。"""
    src = "main.data.buildings[*].rooms"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0

    candidates = _building_candidates(building, data)
    if not candidates:
        return _absent(src, ts, notes=f"未找到匹配 {building!r} 的建筑。")
    if len(candidates) > 1:
        return _result(
            value=sorted(candidates),
            status=STATUS_AMBIGUOUS,
            source=src,
            derived=False,
            as_of=ts,
            notes=f"{building!r} 命中 {len(candidates)} 个建筑，需要消歧。",
        )

    rooms = _as_dict(_as_dict(data.get("buildings")).get(candidates[0])).get("rooms")
    room_list = [r for r in rooms if isinstance(r, str)] if isinstance(rooms, list) else []
    return _result(
        value=room_list,
        status=STATUS_FOUND if room_list else STATUS_ABSENT,
        source=src,
        derived=False,
        as_of=ts,
    )


def get_room(
    room: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    房间信息（`FACT`）。

    注意：visibility 最小规则（WQ-94）—— 非公开房间仅对
    owner 本人 / owner 的 AI 可见；否则返回 FORBIDDEN。
    """
    src = "main.data.rooms"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0

    resolved = _resolve_room(room, data)
    if not resolved:
        return _absent(src, ts, notes=f"未找到房间 {room!r}。")

    if resolved != "main" and not resolved.endswith("·会客厅"):
        bid = _building_of_room(resolved, data)
        building = _as_dict(_as_dict(data.get("buildings")).get(bid)) if bid else {}
        btype = _as_str(building.get("type"))
        owner = _as_str(building.get("owner"))
        is_public = btype == "npc" or not owner
        if not is_public:
            req = _as_str(requester).strip()
            if not (_names_equal(req, owner) or _owner_invites(req, data)):
                return _forbidden(src, ts)

    info = _as_dict(_as_dict(data.get("rooms")).get(resolved))
    copy_of_info = {
        k: (list(v) if isinstance(v, list) else v)
        for k, v in info.items()
        # 不返回密码字段（Presentation 之外也不应泄漏）
        if k != "password"
    }
    return _result(value=copy_of_info, status=STATUS_FOUND, source=src, derived=False, as_of=ts)


# =========================================================
# 7. People 事实
# =========================================================

def list_users_present_in_room(
    room: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
    presence_window_sec: float = 25.0,
) -> QueryResult:
    """
    当前在该房间的**真人**（`DERIVED`：presence 经观测时间窗口计算）。

    presence 只包含真人（G-4）；AI 请用 list_agents_in_room，NPC 请用 NPC 查询。
    """
    src = "main.data.presence"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    resolved = _resolve_room(room, data)
    target = resolved or _as_str(room).strip()

    presence = _as_dict(data.get("presence"))
    names = [
        name
        for name, info in presence.items()
        if isinstance(info, dict)
        and _names_equal(info.get("room"), target)
        and ts - float(info.get("ts", 0) or 0) < presence_window_sec
    ]
    return _result(
        value=sorted(names),
        status=STATUS_FOUND if names else STATUS_ABSENT,
        source=src,
        derived=True,
        as_of=ts,
        notes="仅包含真人（presence 不含 AI / NPC）。",
    )


def list_agents_in_room(
    room: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    当前在该房间的 AI（`DERIVED`：由 ai_location 反查）。

    无法解析自身位置的 AI 不会出现在 value 中，但仍会记入 notes（不假装不存在）。
    """
    src = "main.data.ai_location"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    resolved = _resolve_room(room, data)
    target = resolved or _as_str(room).strip()

    locs = _as_dict(data.get("ai_location"))
    found = [
        name
        for name, loc in locs.items()
        if _names_equal(loc, target)
    ]
    return _result(
        value=sorted(found),
        status=STATUS_FOUND if found else STATUS_ABSENT,
        source=src,
        derived=True,
        as_of=ts,
    )


def list_agents_in_building(
    building: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    当前在某建筑内的 AI（`DERIVED`，**有限支持** —— Contract WQ-85 ～ WQ-89）。

    实现方式：`buildings[bid].rooms[]` → `ai_location` 反查。
    限制：
        * O(buildings × rooms)（Q-87 / G-1）
        * 依赖字符串关系（ai_location 存房间全名，不是 building_id）
        * 某 AI 的 location 无法归属时，会记入 notes（**不假装不存在**，WQ-87）

    ⚠️ 高频限制（WQ-81 / WQ-82）：禁止接入任何 tick / loop。

    这不是 `UNSUPPORTED` —— 当前 schema 确实可以回答（架构侧 Q-U3 裁决）。
    """
    src = "main.data.ai_location + main.data.buildings[*].rooms"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0

    candidates = _building_candidates(building, data)
    if not candidates:
        return _absent(src, ts, notes=f"未找到匹配 {building!r} 的建筑。")
    if len(candidates) > 1:
        return _result(
            value=sorted(candidates),
            status=STATUS_AMBIGUOUS,
            source=src,
            derived=True,
            as_of=ts,
            notes=f"{building!r} 命中 {len(candidates)} 个建筑，需要消歧。",
        )

    bid = candidates[0]
    building_obj = _as_dict(_as_dict(data.get("buildings")).get(bid))
    rooms = building_obj.get("rooms")
    room_set = [r for r in rooms if isinstance(r, str)] if isinstance(rooms, list) else []

    locs = _as_dict(data.get("ai_location"))
    inside = [
        name
        for name, loc in locs.items()
        if _as_str(loc) in room_set
    ]
    # 无法归属的 AI：有位置但不在本建筑的房间集合中，
    # 且其位置也无法解析为任何已知房间 → 属 UNKNOWN（不得假装不存在）
    unresolved = [
        name
        for name, loc in locs.items()
        if _as_str(loc)
        and _as_str(loc) not in room_set
        and not _resolve_room(_as_str(loc), data)
    ]

    if not inside and unresolved:
        return _unknown(
            src, ts,
            notes=(
                "本建筑内未发现可归属的 AI，"
                f"但有 {len(unresolved)} 个 AI 的位置无法解析为任何已知房间。"
            ),
        )

    notes = ""
    if unresolved:
        notes = (
            f"另有 {len(unresolved)} 个 AI 的位置无法解析为任何已知房间，"
            "未被计入本结果（UNKNOWN，不是 ABSENT）。"
        )
    return _result(
        value=sorted(inside),
        status=STATUS_FOUND if inside else STATUS_ABSENT,
        source=src,
        derived=True,
        as_of=ts,
        notes=notes,
    )


def list_npcs_in_building(
    building: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    某建筑的 NPC 列表（`FACT`，main.data.npcs[building_id]）。

    注意：NPC **没有位置 / 状态字段**，因此
    「某 NPC 现在在哪里」属 `UNSUPPORTED`（见 get_npc_location）。
    """
    src = "main.data.npcs"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0

    candidates = _building_candidates(building, data)
    if not candidates:
        return _absent(src, ts, notes=f"未找到匹配 {building!r} 的建筑。")
    if len(candidates) > 1:
        return _result(
            value=sorted(candidates),
            status=STATUS_AMBIGUOUS,
            source=src,
            derived=False,
            as_of=ts,
            notes=f"{building!r} 命中 {len(candidates)} 个建筑，需要消歧。",
        )

    npcs = _as_dict(data.get("npcs")).get(candidates[0])
    items = [
        {"name": _as_str(n.get("name")), "emoji": _as_str(n.get("emoji")), "desc": _as_str(n.get("desc"))}
        for n in (npcs if isinstance(npcs, list) else [])
        if isinstance(n, dict)
    ]
    return _result(
        value=items,
        status=STATUS_FOUND if items else STATUS_ABSENT,
        source=src,
        derived=False,
        as_of=ts,
        notes="NPC 只归属建筑，不归属房间；NPC 没有位置 / 状态。",
    )


def get_npc_location(
    npc: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """NPC 当前位置 —— **`UNSUPPORTED`**（schema 中 NPC 没有位置字段，G-3）。"""
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    return _unsupported("main.data.npcs", _UNSUPPORTED_NPC_LOCATION, ts)


def list_agent_owning_user(
    agent: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """某 owner 名下的所有 AI（`FACT`，main.data.user_ais）。"""
    src = "main.data.user_ais"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0

    user_ais = _as_dict(data.get("user_ais"))
    ais = [
        name
        for owner, group in user_ais.items()
        if _names_equal(owner, agent) and isinstance(group, list)
        for name in group
        if isinstance(name, str)
    ]
    return _result(
        value=ais,
        status=STATUS_FOUND if ais else STATUS_ABSENT,
        source=src,
        derived=False,
        as_of=ts,
    )


# =========================================================
# 8. Agent 状态事实（含 Legacy 状态）
# =========================================================

def get_agent_wallet(
    agent: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """AI 钱包余额（`FACT`，main.data.wallets）。"""
    src = "main.data.wallets"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    wallets = _as_dict(data.get("wallets"))
    if not _agent_exists(agent, data):
        return _absent(src, ts, notes="该 AI 不在 user_ais 中。")
    for name, amount in wallets.items():
        if _names_equal(name, agent):
            return _result(value=amount, status=STATUS_FOUND, source=src, derived=False, as_of=ts)
    return _absent(src, ts, notes="wallets 中没有该 AI 的记录（可能尚未初始化）。")


def get_agent_affection(
    agent: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """AI 好感度数值（`FACT`，main.data.affection）。

    注意：这只是数值，**不是** relationship 结构（见 get_relationship）。
    """
    src = "main.data.affection"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    if not _agent_exists(agent, data):
        return _absent(src, ts, notes="该 AI 不在 user_ais 中。")
    for name, value in _as_dict(data.get("affection")).items():
        if _names_equal(name, agent):
            return _result(value=value, status=STATUS_FOUND, source=src, derived=False, as_of=ts)
    return _absent(src, ts, notes="affection 中没有该 AI 的记录。")


def is_agent_dating(
    agent: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    AI 是否正在约会（`FACT`，基于 main.data.dates 的 Legacy 状态）。

    ⚠️ 这是 **Legacy Activity State**，不是正式 Activity（AC-6 / AC-9）。
    """
    src = "main.data.dates"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    return _result(
        value=_agent_dating(agent, data),
        status=STATUS_FOUND,
        source=src,
        derived=False,
        as_of=ts,
        notes="Legacy Activity State（dates.status），不是正式 Activity。",
    )


def is_agent_working(
    agent: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """AI 是否在工作中（`FACT`，main.data.work_sessions；Legacy Activity State）。"""
    src = "main.data.work_sessions"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    return _result(
        value=_agent_working(agent, data),
        status=STATUS_FOUND,
        source=src,
        derived=False,
        as_of=ts,
        notes="Legacy Activity State（work_sessions），不是正式 Activity。",
    )


def is_agent_following(
    agent: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """AI 是否在跟随中（`FACT`，main.data.ai_follow；Legacy Activity State）。"""
    src = "main.data.ai_follow"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    return _result(
        value=_agent_following(agent, data),
        status=STATUS_FOUND,
        source=src,
        derived=False,
        as_of=ts,
        notes="Legacy Activity State（ai_follow），不是正式 Activity。",
    )


def get_agent_current_activity_legacy(
    agent: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    AI 当前活动 —— **Legacy 推导值**（`DERIVED`）。

    ⚠️ 严格边界（WQ-42 ～ WQ-46）：
        * 返回的是 **Legacy 推导结果**，不是正式 Activity
        * 必须 `derived=True` 并注明来源为 Legacy 推导
        * **禁止**把它包装成 Activity 对象
        * **禁止**返回 Activity 生命周期字段（PLANNED / TRAVELING / ACTIVE …）

    正式 Activity 属 D-2。
    """
    src = "main.data.dates|work_sessions|ai_follow|ai_shop_state|writing_rhythm|story_rhythm"
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    if not _agent_exists(agent, data):
        return _absent(src, ts, notes="该 AI 不在 user_ais 中。")
    return _result(
        value=_derive_activity_legacy(agent, data),
        status=STATUS_FOUND,
        source=src,
        derived=True,
        as_of=ts,
        notes=(
            "Legacy 推导值（非正式 Activity）。"
            "正式 Activity 属 D-2；本结果不得被当作 Activity 生命周期。"
        ),
    )


# =========================================================
# 9. Time 事实（FACT：runtime source）
# =========================================================

def get_world_time(
    data: Dict[str, Any],
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    世界时间（`FACT`，runtime source）。

    与 main.now_str() 同语义：UTC+8。
    注意：`now_ts` 是**观测时刻**，不是历史回溯（WQ-23 ～ WQ-26）。
    """
    from time import time as _now
    ts = now_ts if isinstance(now_ts, (int, float)) else _now()
    return _result(
        value=_fmt_beijing(ts),
        status=STATUS_FOUND,
        source="runtime clock (UTC+8)",
        derived=False,
        as_of=ts,
        notes="世界时间（北京时间）。clock_kind = world。",
    )


def get_room_time(
    room: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    房间时间（`FACT`，runtime source）。

    与 main.room_time() 同语义：若该房间的 time_settings.mode == "fixed"，
    则返回 fixed_time；否则返回当前世界时间。

    返回的 notes 标明 clock_kind ∈ {room, world}（WQ-26）。
    """
    from time import time as _now
    ts = now_ts if isinstance(now_ts, (int, float)) else _now()

    resolved = _resolve_room(room, data)
    if not resolved:
        return _absent("main.data.time_settings", ts, notes=f"未找到房间 {room!r}。")

    settings = _as_dict(_as_dict(data.get("time_settings")).get(resolved))
    if _as_str(settings.get("mode")) == "fixed" and _as_str(settings.get("fixed_time")):
        return _result(
            value=_as_str(settings.get("fixed_time")),
            status=STATUS_FOUND,
            source="main.data.time_settings",
            derived=False,
            as_of=ts,
            notes="clock_kind = room（该房间使用固定时间）。",
        )

    return _result(
        value=_fmt_beijing(ts),
        status=STATUS_FOUND,
        source="runtime clock (UTC+8)",
        derived=False,
        as_of=ts,
        notes="clock_kind = world（该房间未使用固定时间）。",
    )


# =========================================================
# 10. 当前 schema 明确不支持的能力（UNSUPPORTED，冻结）
# =========================================================

def get_map_of_building(
    building: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """某建筑所属地图 —— **`UNSUPPORTED`**（无 World → Map 关系，G-2）。"""
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    return _unsupported("main.data.buildings.region", _UNSUPPORTED_MAP, ts)


def search_places_by_purpose(
    purpose: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """
    按用途 / 营业状态检索地点 —— **`UNSUPPORTED`**。

    当前 schema 不存在 purpose / 营业时间字段。
    **禁止**为了让 D-0 Preflight §66 的示例「看起来能跑」而临时创造字段（WQ-111）。
    """
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    return _unsupported("main.data.buildings", _UNSUPPORTED_PURPOSE_SEARCH, ts)


def get_relationship(
    agent: str,
    user: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """AI ↔ User 关系结构 —— **`UNSUPPORTED`**（当前只有 affection 数值）。"""
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    return _unsupported("main.data.affection", _UNSUPPORTED_RELATIONSHIP, ts)


def get_route(
    origin: str,
    destination: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """路径 / 距离 —— **`UNSUPPORTED`**（无连通性数据）。"""
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    return _unsupported("main.data.buildings", _UNSUPPORTED_ROUTE, ts)


def list_available_places(
    agent: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """「可去的地方」—— **`UNSUPPORTED`**（无可达性建模）。"""
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    return _unsupported("main.data.buildings", _UNSUPPORTED_AVAILABLE_PLACES, ts)


def get_activity(
    activity_id: str,
    data: Dict[str, Any],
    requester: str = "",
    now_ts: Optional[float] = None,
) -> QueryResult:
    """正式 Activity —— **`UNSUPPORTED`**（Activity 属 D-2，WQ-42）。"""
    ts = now_ts if isinstance(now_ts, (int, float)) else 0.0
    return _unsupported("(none)", _UNSUPPORTED_ACTIVITY, ts)


# =========================================================
# 11. 只读命名空间（便于调用方一次性取得全部入口）
# =========================================================

def get_world_query_namespace() -> Dict[str, Any]:
    """
    只读返回全部 Query 入口的映射（调用方无需自行维护函数清单）。

    按 Contract §5D.11 的三类组织：Location / People / Time
    （外加 unsupported 清单与反模式守卫）。
    """
    return {
        "location": {
            "get_agent_location": get_agent_location,
            "get_building": get_building,
            "list_building_rooms": list_building_rooms,
            "get_room": get_room,
        },
        "people": {
            "list_users_present_in_room": list_users_present_in_room,
            "list_agents_in_room": list_agents_in_room,
            "list_agents_in_building": list_agents_in_building,
            "list_npcs_in_building": list_npcs_in_building,
            "list_agent_owning_user": list_agent_owning_user,
        },
        "time": {
            "get_world_time": get_world_time,
            "get_room_time": get_room_time,
        },
        "agent": {
            "get_agent_owner": get_agent_owner,
            "get_agent_wallet": get_agent_wallet,
            "get_agent_affection": get_agent_affection,
            "is_agent_dating": is_agent_dating,
            "is_agent_working": is_agent_working,
            "is_agent_following": is_agent_following,
            "get_agent_current_activity_legacy": get_agent_current_activity_legacy,
        },
        "unsupported": {
            "get_map_of_building": get_map_of_building,
            "get_npc_location": get_npc_location,
            "search_places_by_purpose": search_places_by_purpose,
            "get_relationship": get_relationship,
            "get_route": get_route,
            "list_available_places": list_available_places,
            "get_activity": get_activity,
        },
        "guards": {
            "is_world_query_available": is_world_query_available,
            "is_decision_like_request": is_decision_like_request,
            "describe_capabilities": describe_capabilities,
            "get_unsupported_capabilities": get_unsupported_capabilities,
        },
    }
