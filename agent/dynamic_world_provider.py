"""
agent/dynamic_world_provider.py - Phase B2-2: DynamicWorldProvider

职责：
- 从现有 Linkong 世界事实中，提取 Dynamic World 层的结构化 Context。

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
7. 不返回整个 main.data
8. 不猜测地图 / 建筑 / 地点（找不到就 absent）

Dynamic World 只包含：
- current_time     当前时间（北京时间）
- current_location 当前房间名（直接读 ai_location）
- current_activity 当前活动（可选，从 AgentState 投影读）
- is_working / is_dating / is_following（可选，同上）

明确不含：
- current_map / current_region / current_place
  （需要多步推断，本阶段 absent）
- mood / energy / social_need / stress
  （AgentState placeholder，禁止进入 Context）
- ai_keys / dev_users / pairs_admin / server_id
- messages / sms / trails / ai_timeline / ai_memories
- wallets / work_sessions / home_jobs
- presence / online

Map Knowledge 预留（本阶段不实现）：
- 未来 Map / Region / Building / Place / NaturalFeature 的层级
- 未来 Map Ownership / Purpose / Description / Tags / Environment
- 本阶段只在 describe() 中声明预留位置
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional


DYNAMIC_WORLD_LAYER = "dynamic_world"


def _format_bj_time(ts: float) -> str:
    """Unix timestamp → 北京时间字符串（与 main.now_str 格式一致）"""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc) + timedelta(hours=8)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class DynamicWorldProvider:
    """
    Dynamic World Provider。

    使用方式：
        provider = DynamicWorldProvider()
        items = provider.fetch(
            ai_name="Dan",
            owner="Alice",
            data=data,                      # main.data 只读引用
            now_ts=time.time(),             # 可选
            agent_state_dict=state.to_dict(),  # 可选
        )
    """

    name = "dynamic_world"
    layer = DYNAMIC_WORLD_LAYER

    # 允许读取的 data 字段（仅文档和审计用）
    _ALLOWED_DATA_FIELDS = ("ai_location",)

    # 明确排除的敏感字段（仅文档和审计用）
    _FORBIDDEN_DATA_FIELDS = (
        "ai_keys", "dev_users", "pairs_admin", "server_id",
        "messages", "sms", "trails", "ai_timeline", "ai_memories",
        "wallets", "work_sessions", "home_jobs",
        "presence", "online",
    )

    # Map Knowledge 预留字段（本阶段不实现）
    _MAP_KNOWLEDGE_RESERVED = (
        "map_id", "map_name", "map_type", "map_region",
        "map_owner", "map_purpose", "map_description",
        "map_tags", "map_environment", "map_places",
    )

    def fetch(
        self,
        ai_name: str,
        owner: str,
        data: Dict[str, Any],
        now_ts: Optional[float] = None,
        agent_state_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        从世界事实中提取 Dynamic World 的结构化 items。

        Args:
            ai_name:          AI 名字（canonical）
            owner:            AI 主人名字（保留参数，本层暂不使用）
            data:             只读 main.data 引用
            now_ts:           Unix timestamp（可选，默认 time.time()）
            agent_state_dict: AgentState.to_dict() 结果（可选）
                              Provider 不 import agent.state，
                              由调用方负责生成并传入。

        Returns:
            List[Dict[str, Any]]

        保证：
            - 不修改 data
            - 不调用 LLM
            - 不 import main / ext_*
            - 不猜测地图 / 建筑 / 地点
            - 找不到就 absent（不生成该 item）
        """
        items: List[Dict[str, Any]] = []

        if not ai_name or not isinstance(ai_name, str):
            return items
        if not isinstance(data, dict):
            return items

        # 1. current_time
        ts = now_ts if isinstance(now_ts, (int, float)) else time.time()
        items.append({
            "type": "current_time",
            "content": _format_bj_time(ts),
            "source": "provider.clock",
        })

        # 2. current_location（直接从 ai_location 读）
        locations = data.get("ai_location", {})
        location = ""
        if isinstance(locations, dict):
            raw = locations.get(ai_name, "")
            if isinstance(raw, str):
                location = raw.strip()

        if location:
            items.append({
                "type": "current_location",
                "content": location,
                "source": "main.data.ai_location",
            })

        # 3-6. 从 AgentState 投影读（可选，由调用方提供）
        if isinstance(agent_state_dict, dict):
            activity = agent_state_dict.get("current_activity")
            if isinstance(activity, str) and activity and activity != "idle":
                items.append({
                    "type": "current_activity",
                    "content": activity,
                    "source": "agent_state.projection",
                })

            if agent_state_dict.get("is_working") is True:
                items.append({
                    "type": "is_working",
                    "content": "true",
                    "source": "agent_state.projection",
                })

            if agent_state_dict.get("is_dating") is True:
                items.append({
                    "type": "is_dating",
                    "content": "true",
                    "source": "agent_state.projection",
                })

            if agent_state_dict.get("is_following") is True:
                items.append({
                    "type": "is_following",
                    "content": "true",
                    "source": "agent_state.projection",
                })

        return items

    def describe(self) -> Dict[str, Any]:
        """
        Provider 自描述（供架构审计）。
        """
        return {
            "name": self.name,
            "layer": self.layer,
            "allowed_data_fields": list(self._ALLOWED_DATA_FIELDS),
            "forbidden_data_fields": list(self._FORBIDDEN_DATA_FIELDS),
            "map_knowledge_reserved": list(self._MAP_KNOWLEDGE_RESERVED),
            "returns": "List[Dict[str, Any]]",
            "supported_item_types": [
                "current_time",
                "current_location",
                "current_activity",
                "is_working",
                "is_dating",
                "is_following",
            ],
            "unsupported_item_types_reserved": [
                "current_building",   # 需要反查，暂不提供
                "current_map",        # 需要多步推断，暂不提供
                "current_region",     # 同上
                "current_place",      # 同上
            ],
        }