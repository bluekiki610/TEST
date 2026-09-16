"""
agent/state.py - P0-1: Agent State Projection Layer

硬性约束：
1. 这是投影层（Projection），不是事实来源。只读，不写 data。
2. mood/energy/social_need/stress 是 placeholder，不影响任何旧行为。
3. 不触碰 ext_ai / ext_world / ext_date / ext_econ / ext_shop / ext_sms / ext_room。
4. _derive_activity() 的优先级是 P0-1 临时规则，不代表最终 Agent 行为模型。
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field

# 只读依赖 main.py 的工具函数
from main import canonical_ai_name, owner_of_ai, strip_emoji


# =========================================================
# AgentState 数据类（只读投影）
# =========================================================
@dataclass
class AgentState:
    """AI 当前状态的投影视图（只读，不写回 data）"""

    # --- 核心标识 ---
    name: str
    owner: str

    # --- 直接映射字段（源自 main.data）---
    location: str
    wallet: float
    affection: int
    is_following: bool
    is_dating: bool
    is_working: bool

    # --- 推导字段 ---
    current_activity: str

    # --- 可选 / 占位字段 ---
    current_goal: Optional[str] = None
    mood: int = 70          # placeholder
    energy: int = 70        # placeholder
    social_need: int = 30   # placeholder
    stress: int = 20        # placeholder

    # --- 元数据：标记字段来源，防止未来误用 ---
    _meta: Dict[str, str] = field(default_factory=lambda: {
        "mood": "placeholder",
        "energy": "placeholder",
        "social_need": "placeholder",
        "stress": "placeholder",
        "location": "direct_map",
        "wallet": "direct_map",
        "affection": "direct_map",
        "is_following": "direct_map",
        "is_dating": "direct_map",
        "is_working": "direct_map",
        "current_activity": "derived",
        "current_goal": "none",
    })

    def to_dict(self) -> Dict[str, Any]:
        """安全输出，包含字段来源标记"""
        return {
            "name": self.name,
            "owner": self.owner,
            "location": self.location,
            "wallet": self.wallet,
            "affection": self.affection,
            "current_activity": self.current_activity,
            "current_goal": self.current_goal,
            "mood": self.mood,
            "energy": self.energy,
            "social_need": self.social_need,
            "stress": self.stress,
            "is_following": self.is_following,
            "is_dating": self.is_dating,
            "is_working": self.is_working,
            "_sources": self._meta,
        }


# =========================================================
# 核心投影函数
# =========================================================
def get_agent_state(ai_name: str, data: Dict[str, Any]) -> Optional[AgentState]:
    """
    从现有 data 生成 AI 状态投影。

    安全读取原则：任何字段缺失都不抛异常，优雅降级。
    如果 AI 不存在，返回 None。
    """
    # 1. 规范化 + 存在性检查
    try:
        canonical = canonical_ai_name(ai_name)
    except Exception:
        canonical = None

    if not canonical:
        return None

    # 2. 获取 Owner（反向查找容错）
    owner = None
    try:
        owner = owner_of_ai(canonical)
    except Exception:
        owner = None

    if not owner:
        for o, ais in data.get("user_ais", {}).items():
            try:
                if canonical in [strip_emoji(a) for a in ais]:
                    owner = o
                    break
            except Exception:
                continue
        if not owner:
            owner = "unknown"  # 容错，不阻塞

    # 3. 安全读取基础字段（缺失即默认值）
    wallets = data.get("wallets", {}) or {}
    locations = data.get("ai_location", {}) or {}
    affections = data.get("affection", {}) or {}
    follows = data.get("ai_follow", {}) or {}
    work_sessions = data.get("work_sessions", {}) or {}
    dates = data.get("dates", []) or []

    location = locations.get(canonical, "unknown")
    wallet = wallets.get(canonical, 0.0)
    affection = affections.get(canonical, 50)
    is_following = canonical in follows
    is_working = canonical in work_sessions

    # 4. 判断是否在约会中
    is_dating = False
    for d in dates:
        try:
            if d.get("ai") == canonical and d.get("status") in ("active", "coming"):
                is_dating = True
                break
        except Exception:
            continue

    # 5. 推导当前活动
    current_activity = _derive_activity(canonical, data)

    # 6. 返回投影对象
    return AgentState(
        name=canonical,
        owner=owner,
        location=location,
        wallet=wallet,
        affection=affection,
        is_following=is_following,
        is_dating=is_dating,
        is_working=is_working,
        current_activity=current_activity,
        current_goal=None,  # P0-1 暂不实现 Goal
    )


# =========================================================
# 活动推导器（P0-1 临时规则，非最终模型）
# =========================================================
def _derive_activity(ai: str, data: Dict[str, Any]) -> str:
    """
    推导当前活动。

    P0-1 临时优先级（高 -> 低）：
    1. 约会中       -> dating / traveling_to_date / waiting_for_date
    2. 工作中       -> working
    3. 跟随中       -> following
    4. 购物冷却中   -> shopping_cooldown
    5. 写作冲动     -> thinking_to_write
    6. 剧情冲动     -> thinking_story
    7. 空闲         -> idle

    ⚠️ 注意：此优先级是 P0-1 的 Projection 规则，不代表最终 Agent 行为模型。
       后续 Agent Runtime 会重新设计 Activity / Goal / Attention / Event 的关系。
    """
    # 1. 约会状态
    for d in data.get("dates", []) or []:
        try:
            if d.get("ai") == ai:
                status = d.get("status", "")
                if status == "active":
                    return "dating"
                if status == "coming":
                    return "traveling_to_date"
                if status == "pending":
                    return "waiting_for_date"
        except Exception:
            continue

    # 2. 工作
    if ai in (data.get("work_sessions", {}) or {}):
        return "working"

    # 3. 跟随
    if ai in (data.get("ai_follow", {}) or {}):
        return "following"

    # 4. 购物冷却
    shop_state = (data.get("ai_shop_state", {}) or {}).get(ai, {}) or {}
    if shop_state.get("cooldown_until"):
        return "shopping_cooldown"

    # 5. 写作冲动
    writing = (data.get("writing_rhythm", {}) or {}).get(ai, {}) or {}
    if writing.get("ready", False):
        return "thinking_to_write"

    # 6. 剧情冲动
    story = (data.get("story_rhythm", {}) or {}).get(ai, {}) or {}
    if story.get("ready", False):
        return "thinking_story"

    return "idle"


# =========================================================
# Debug Shadow 输出（仅手动调用）
# =========================================================
def debug_print_state(ai_name: str, data: Dict[str, Any]) -> None:
    """调试用，生产环境不自动调用。需 DEBUG=1 环境变量。"""
    import os
    if os.getenv("DEBUG", "").lower() not in ("1", "true", "yes"):
        return

    state = get_agent_state(ai_name, data)
    if not state:
        print(f"[AGENT_STATE] AI '{ai_name}' not found")
        return

    print(f"[AGENT_STATE] Projection for {state.name}:")
    print(f"  Owner:        {state.owner}")
    print(f"  Location:     {state.location} (direct_map)")
    print(f"  Activity:     {state.current_activity} (derived)")
    print(f"  Mood:         {state.mood} (placeholder)")
    print(f"  Energy:       {state.energy} (placeholder)")
    print(f"  Social Need:  {state.social_need} (placeholder)")
    print(f"  Stress:       {state.stress} (placeholder)")
    print(f"  Wallet:       {state.wallet} (direct_map)")
    print(f"  Affection:    {state.affection} (direct_map)")
    print(f"  Following:    {state.is_following}")
    print(f"  Dating:       {state.is_dating}")
    print(f"  Working:      {state.is_working}")
