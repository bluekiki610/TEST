"""
agent/recent_provider.py - Phase B2-3: RecentProvider

职责：
- 从现有 Linkong 系统事实中，提取"最近、与当前 AI 决策可能相关"的结构化 Context。

Recent 只表达：
    最近发生过、可能影响当前决策的事实。

Recent 不是：
- 聊天记录数据库
- Memory
- Prompt Builder
- Decision

边界（Architecture Contract + B2 原则）：
- Provider ≠ Database / Memory / Decision / Prompt
- Provider 只负责：从已有系统事实中，取出一小块结构化数据

硬性约束：
1. 不修改 main.data
2. 不调用 LLM
3. 不缓存、不持久化
4. 不 import main
5. 不 import ext_*
6. 不返回 Prompt 字符串
7. 不返回完整聊天历史 / SMS / Memory / Timeline
8. 不猜测
9. 输出必须有明确上限（item 数量 + 时间窗口）

数据源：
- data.ai_timeline[ai]   AI 最近活动时间线（取最近 N 条）
- data.trails[ai]        AI 最近行为轨迹（时间窗口 + 条数上限）
- data.ai_visited[ai]    AI 最近访问过的地点（取前 N 个）

明确不使用：
- messages / sms / notes / diaries / stories
- ai_memories / ai_impression
- ai_keys / dev_users / pairs_admin / server_id
- wallets / work_sessions / home_jobs
- presence / online
- mood / energy / social_need / stress
"""

import time
from typing import Dict, Any, List, Optional


RECENT_LAYER = "recent"


class RecentProvider:
    """
    Recent Provider。

    使用方式：
        provider = RecentProvider()
        items = provider.fetch(
            ai_name="Dan",
            owner="Alice",
            data=data,                # main.data 只读引用
            now_ts=time.time(),       # 可选，用于时间窗口过滤
        )

    默认上限（全部可通过构造函数覆盖）：
        timeline_max_items = 5      # ai_timeline 最近 5 条
        trail_max_items = 5         # trails 时间窗口内最近 5 条
        visited_max_items = 3       # ai_visited 最近 3 个
        content_max_chars = 120     # 每条内容最大 120 字
        time_window_seconds = 86400 # trails 只取 24 小时内
    """

    name = "recent"
    layer = RECENT_LAYER

    # 允许读取的 data 字段（仅文档和审计用）
    _ALLOWED_DATA_FIELDS = ("ai_timeline", "trails", "ai_visited")

    # 明确排除的敏感字段（仅文档和审计用）
    _FORBIDDEN_DATA_FIELDS = (
        "messages", "sms",
        "notes", "diaries", "stories",
        "ai_memories", "ai_impression",
        "ai_keys", "dev_users", "pairs_admin", "server_id",
        "wallets", "work_sessions", "home_jobs",
        "presence", "online",
    )

    # 明确不生成的事实类型（仅文档和审计用）
    _NOT_GENERATED_ITEM_TYPES = (
        "recent_map",              # Map Knowledge 未实现
        "recent_building",
        "recent_region",
        "recent_place",
        "recent_decision",         # Decision 不属于 Provider
        "recent_goal",             # Goal 未实现
        "recent_memory",           # Memory 未启用
        "recent_full_chat",        # 禁止完整聊天
        "recent_full_sms",         # 禁止完整 SMS
    )

    def __init__(
        self,
        timeline_max_items: int = 5,
        trail_max_items: int = 5,
        visited_max_items: int = 3,
        content_max_chars: int = 120,
        time_window_seconds: float = 86400.0,
    ):
        if timeline_max_items < 0:
            raise ValueError("timeline_max_items must be >= 0")
        if trail_max_items < 0:
            raise ValueError("trail_max_items must be >= 0")
        if visited_max_items < 0:
            raise ValueError("visited_max_items must be >= 0")
        if content_max_chars <= 0:
            raise ValueError("content_max_chars must be > 0")
        if time_window_seconds <= 0:
            raise ValueError("time_window_seconds must be > 0")

        self.timeline_max_items = timeline_max_items
        self.trail_max_items = trail_max_items
        self.visited_max_items = visited_max_items
        self.content_max_chars = content_max_chars
        self.time_window_seconds = time_window_seconds

    # -----------------------------------------------------
    # 主入口
    # -----------------------------------------------------
    def fetch(
        self,
        ai_name: str,
        owner: str,
        data: Dict[str, Any],
        now_ts: Optional[float] = None,
        agent_state_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        从世界事实中提取 Recent 的结构化 items。

        Args:
            ai_name:          AI 名字（canonical）
            owner:            AI 主人名字（保留参数，本层暂不使用）
            data:             只读 main.data 引用
            now_ts:           Unix timestamp（可选，默认 time.time()）
            agent_state_dict: AgentState 投影（保留参数，本层不使用）
                              注：Recent 不读 AgentState，只读时间线和轨迹

        Returns:
            List[Dict[str, Any]]，每个 item：
            {
              "type":    "recent_timeline" | "recent_trail" | "recent_visited_place",
              "content": str,
              "source":  str,
            }

        保证：
            - 不修改 data
            - 不调用 LLM
            - 不 import main / ext_*
            - 不猜测
            - 输出有明确上限
            - 不返回完整聊天历史
        """
        items: List[Dict[str, Any]] = []

        if not ai_name or not isinstance(ai_name, str):
            return items
        if not isinstance(data, dict):
            return items

        now = now_ts if isinstance(now_ts, (int, float)) else time.time()

        # 1. ai_timeline 最近 N 条
        items.extend(self._fetch_timeline(ai_name, data))

        # 2. trails 时间窗口内最近 N 条
        items.extend(self._fetch_trails(ai_name, data, now))

        # 3. ai_visited 前 N 个
        items.extend(self._fetch_visited(ai_name, data))

        return items

    # -----------------------------------------------------
    # 内部方法
    # -----------------------------------------------------
    def _fetch_timeline(
        self, ai_name: str, data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """从 ai_timeline[ai] 取最近 N 条。"""
        if self.timeline_max_items <= 0:
            return []

        timeline = data.get("ai_timeline", {})
        if not isinstance(timeline, dict):
            return []

        entries = timeline.get(ai_name, [])
        if not isinstance(entries, list) or not entries:
            return []

        # 取最近 N 条（末尾是最新）
        recent = entries[-self.timeline_max_items:]

        out: List[Dict[str, Any]] = []
        for e in recent:
            if not isinstance(e, dict):
                continue
            text = e.get("text", "")
            time_str = e.get("time", "")
            if not isinstance(text, str) or not text.strip():
                continue
            # 时间信息嵌入内容，保持 type/content/source 三字段结构
            if isinstance(time_str, str) and time_str.strip():
                content = f"[{time_str.strip()}] {text.strip()}"
            else:
                content = text.strip()
            out.append({
                "type": "recent_timeline",
                "content": content[:self.content_max_chars],
                "source": "main.data.ai_timeline",
            })
        return out

    def _fetch_trails(
        self, ai_name: str, data: Dict[str, Any], now: float
    ) -> List[Dict[str, Any]]:
        """从 trails[ai] 取时间窗口内最近 N 条。"""
        if self.trail_max_items <= 0:
            return []

        trails = data.get("trails", {})
        if not isinstance(trails, dict):
            return []

        entries = trails.get(ai_name, [])
        if not isinstance(entries, list) or not entries:
            return []

        cutoff = now - self.time_window_seconds

        # 时间窗口过滤
        in_window = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            ts = e.get("ts", 0)
            if not isinstance(ts, (int, float)):
                continue
            if ts >= cutoff:
                in_window.append(e)

        # 取最近 N 条
        recent = in_window[-self.trail_max_items:]

        out: List[Dict[str, Any]] = []
        for e in recent:
            text = e.get("text", "")
            if not isinstance(text, str) or not text.strip():
                continue
            time_str = e.get("time", "")
            room = e.get("room", "")

            parts = []
            if isinstance(time_str, str) and time_str.strip():
                parts.append(time_str.strip())
            if isinstance(room, str) and room.strip():
                parts.append(room.strip())
            parts.append(text.strip())
            content = " | ".join(parts)

            out.append({
                "type": "recent_trail",
                "content": content[:self.content_max_chars],
                "source": "main.data.trails",
            })
        return out

    def _fetch_visited(
        self, ai_name: str, data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """从 ai_visited[ai] 取前 N 个（列表已有序，最新的在前）。"""
        if self.visited_max_items <= 0:
            return []

        visited = data.get("ai_visited", {})
        if not isinstance(visited, dict):
            return []

        entries = visited.get(ai_name, [])
        if not isinstance(entries, list) or not entries:
            return []

        recent = entries[:self.visited_max_items]

        out: List[Dict[str, Any]] = []
        for place in recent:
            if not isinstance(place, str) or not place.strip():
                continue
            out.append({
                "type": "recent_visited_place",
                "content": place.strip()[:self.content_max_chars],
                "source": "main.data.ai_visited",
            })
        return out

    # -----------------------------------------------------
    # 自描述（供架构审计）
    # -----------------------------------------------------
    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "layer": self.layer,
            "allowed_data_fields": list(self._ALLOWED_DATA_FIELDS),
            "forbidden_data_fields": list(self._FORBIDDEN_DATA_FIELDS),
            "not_generated_item_types": list(self._NOT_GENERATED_ITEM_TYPES),
            "returns": "List[Dict[str, Any]]",
            "supported_item_types": [
                "recent_timeline",
                "recent_trail",
                "recent_visited_place",
            ],
            "limits": {
                "timeline_max_items": self.timeline_max_items,
                "trail_max_items": self.trail_max_items,
                "visited_max_items": self.visited_max_items,
                "content_max_chars": self.content_max_chars,
                "time_window_seconds": self.time_window_seconds,
            },
        }