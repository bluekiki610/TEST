"""
agent/long_term_provider.py - Phase B2-4: LongTermProvider Stub

定位：
    Long-term Context 层回答："过去有哪些信息，在当前决策中可能有用？"

    LongTermProvider 是未来 Memory Recall 与 ContextAssembler 之间的
    Provider 边界。本阶段为 Stub —— Memory Runtime 尚未启用。

未来架构：
    Memory Runtime
        ↓
    Recall
        ↓
    LongTermProvider     ← 本文件（当前 Stub）
        ↓
    ContextAssembler
        ↓
    AgentContext

本阶段不实现：
- 不修复 ext_memory
- 不启用 Memory Runtime
- 不读取 ext_memory.pending_events
- 不生成新的 Memory 文本
- 不扫描 chat / sms / notes / diary / story / timeline / trails / visited
- 不创建第二套 Memory DB
- 不创建持久化文件

硬性约束：
1. 不 import main / ext_*
2. 不调用 LLM
3. 不发网络请求
4. 不写文件
5. 不修改传入 data
6. 不修改 agent_state_dict
7. 不修改 main.data
8. 不修改 AgentState
9. 不修改 Runtime
10. 不连接 ContextAssembler
11. 不实现 Recall 算法
12. 不实现 Memory Encoding

Dependency Injection：所有输入通过参数传入，Provider 不主动获取。
"""

from typing import Dict, Any, List, Optional


LONG_TERM_LAYER = "long_term"


class LongTermProvider:
    """
    Long-Term Provider Stub。

    当前状态：
        - 无真实 Long-term 数据源
        - 返回 [] 是正确行为
        - Memory Runtime 未启用

    使用方式（未来）：
        provider = LongTermProvider()
        items = provider.fetch(
            ai_name="Dan",
            owner="Alice",
            data=data,
            now_ts=time.time(),
            agent_state_dict=state.to_dict(),
            recall_query="current_context_signature",
        )

    使用方式（当前）：
        返回 []，无论输入如何。
    """

    name = "long_term"
    layer = LONG_TERM_LAYER

    # 当前状态标识
    STATUS = "stub"                  # stub / active / unavailable
    DATA_SOURCE = "none"             # none / filesystem / runtime / memory_db
    MEMORY_RUNTIME_CONNECTED = False # 是否已连接 Memory Runtime
    RECALL_SUPPORTED = False         # 是否已实现 Recall

    # 预算与边界（即使当前返回空，也必须明确声明未来上界）
    MAX_ITEMS = 5                    # 未来最多返回的 item 数
    MAX_CHARS_PER_ITEM = 300         # 单条 item 最大字符数
    TOKEN_BUDGET = 2500              # 与 ContextBudget.long_term_max 一致

    # 允许的数据源（当前无）
    ALLOWED_DATA_FIELDS: tuple = ()

    # 明确禁止的数据源（仅文档和审计用）
    FORBIDDEN_DATA_FIELDS = (
        # 聊天 / 内容
        "messages", "sms",
        "notes", "diaries", "stories",
        # 旧记忆系统
        "ai_memories", "ai_impression",
        # Recent（B2-3 已处理）
        "ai_timeline", "trails", "ai_visited",
        # 敏感
        "ai_keys", "dev_users", "pairs_admin", "server_id",
        # 状态
        "wallets", "work_sessions", "home_jobs",
        "presence", "online",
        "ai_location",  # 属于 Dynamic World
    )

    # 明确不生成的事实类型
    NOT_GENERATED_ITEM_TYPES = (
        "long_term_memory",       # Memory Runtime 未启用
        "long_term_recall",       # Recall 未实现
        "long_term_diary",        # 不从 diary 生成
        "long_term_note",         # 不从 note 生成
        "long_term_chat",         # 不扫聊天
        "long_term_event",        # 不扫描 Event
        "long_term_decision",     # Decision 不属于 Provider
        "long_term_goal",         # Goal 未实现
    )

    def fetch(
        self,
        ai_name: str,
        owner: str,
        data: Dict[str, Any],
        now_ts: Optional[float] = None,
        agent_state_dict: Optional[Dict[str, Any]] = None,
        recall_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        未来：从 Memory Runtime / Recall 中提取长期 Context。

        当前（B2-4 Stub）：
            - 无论输入如何，返回 []
            - 原因：Memory Runtime 未启用，无可靠 Long-term 数据源

        参数保留的目的：
            - 保持与其他 Provider（B2-1/2/3）接口一致
            - 为未来 Recall 实现预留接口
            - 允许调用方按统一协议调用

        Args:
            ai_name:          AI 名字（canonical）
            owner:            AI 主人名字
            data:             main.data 只读引用（Provider 不读取）
            now_ts:           Unix timestamp
            agent_state_dict: AgentState 投影（Provider 不读取）
            recall_query:     未来用于表达"当前需要检索什么"（本阶段占位）

        Returns:
            List[Dict[str, Any]] —— 当前始终为 []

        保证：
            - 不修改 data
            - 不修改 agent_state_dict
            - 不调用 LLM / 网络
            - 不写文件
            - 不读取任何 data 字段
        """
        # 参数校验（保持行为可预期，但结果仍为空）
        if not ai_name or not isinstance(ai_name, str):
            return []
        if not isinstance(data, dict):
            return []
        # owner / now_ts / agent_state_dict / recall_query 均不参与本阶段逻辑，
        # 仅作为未来接口预留。当前返回 []。
        return []

    def describe(self) -> Dict[str, Any]:
        """
        Provider 自描述（供架构审计）。

        明确声明：
            - 当前状态为 Stub
            - 无真实数据源
            - Memory Runtime 未启用
            - Recall 未实现
        """
        return {
            "name": self.name,
            "layer": self.layer,
            "status": self.STATUS,                              # "stub"
            "data_source": self.DATA_SOURCE,                    # "none"
            "memory_runtime_connected": self.MEMORY_RUNTIME_CONNECTED,  # False
            "recall_supported": self.RECALL_SUPPORTED,          # False
            "allowed_data_fields": list(self.ALLOWED_DATA_FIELDS),
            "forbidden_data_fields": list(self.FORBIDDEN_DATA_FIELDS),
            "not_generated_item_types": list(self.NOT_GENERATED_ITEM_TYPES),
            "returns": "List[Dict[str, Any]]",
            "current_return_value": "[]",                       # 明确当前始终返回空
            "supported_item_types": [],                         # 当前无
            "limits": {
                "max_items": self.MAX_ITEMS,
                "max_chars_per_item": self.MAX_CHARS_PER_ITEM,
                "token_budget": self.TOKEN_BUDGET,
            },
            "notes": (
                "B2-4 Stub：仅建立接口与边界。"
                "Memory Runtime 未启用；ext_memory 未修复、未启用；"
                "Recall 未实现；ContextAssembler 尚未开始；Runtime 尚未接入。"
            ),
        }