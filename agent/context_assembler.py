"""
agent/context_assembler.py - Phase B3: ContextAssembler

职责：
- 把四个 Provider 组装成统一 AgentContext。
- 采用 Dependency Injection。
- 负责 validate、bounded assembly、budget enforcement、deterministic truncation。

核心链路：
    Provider
        ↓
    ContextAssembler
        ↓
    AgentContext

本阶段不做：
- 不接 Runtime
- 不调用 LLM
- 不访问网络
- 不生成 Prompt
- 不修改 main.data
- 不修改 AgentState
- 不修改 Provider 原始返回对象
- 不创建缓存 / 新数据源
- 不启用 / 修复 Memory
"""

import copy
from typing import Dict, Any, List, Optional

from agent.context import (
    AgentContext,
    ContextSection,
    ContextBudget,
    make_empty_context,
    LAYER_STABLE_CORE,
    LAYER_RECENT,
    LAYER_LONG_TERM,
    LAYER_DYNAMIC_WORLD,
)


class ContextAssembler:
    """
    Context Assembler。

    使用方式：
        assembler = ContextAssembler(
            stable_core_provider=StableCoreProvider(),
            recent_provider=RecentProvider(),
            long_term_provider=LongTermProvider(),
            dynamic_world_provider=DynamicWorldProvider(),
            budget=ContextBudget(),  # 可选
        )
        ctx = assembler.assemble(
            ai_name="Dan",
            owner="Alice",
            data=data,
            now_ts=time.time(),
            agent_state_dict=state.to_dict(),
            recall_query=None,
        )
    """

    def __init__(
        self,
        stable_core_provider,
        recent_provider,
        long_term_provider,
        dynamic_world_provider,
        budget: Optional[ContextBudget] = None,
    ):
        self.stable_core_provider = stable_core_provider
        self.recent_provider = recent_provider
        self.long_term_provider = long_term_provider
        self.dynamic_world_provider = dynamic_world_provider
        self.budget = budget or ContextBudget()
        self._last_audit: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    def assemble(
        self,
        ai_name: str,
        owner: str,
        data: Dict[str, Any],
        now_ts: Optional[float] = None,
        agent_state_dict: Optional[Dict[str, Any]] = None,
        recall_query: Optional[str] = None,
    ) -> AgentContext:
        """
        组装四层 AgentContext。

        保证：
        - 返回 AgentContext，不是 dict / prompt / string
        - 不修改 data
        - 不修改 agent_state_dict
        - 不修改 Provider 原始返回对象
        - 预算真正 enforcement
        - deterministic truncation
        """
        ctx = make_empty_context(ai_name, self.budget)

        audit: Dict[str, Any] = {
            "ai_name": ai_name,
            "owner": owner,
            "now_ts": now_ts,
            "layers": {},
        }

        # 1. Stable Core
        stable_items = self._safe_fetch(
            self.stable_core_provider,
            ai_name,
            owner,
            data,
            use_now_ts=False,
            use_agent_state=False,
            use_recall=False,
            now_ts=now_ts,
            agent_state_dict=agent_state_dict,
            recall_query=recall_query,
        )
        self._fill_section(ctx.stable_core, stable_items, audit, LAYER_STABLE_CORE)

        # 2. Recent
        recent_items = self._safe_fetch(
            self.recent_provider,
            ai_name,
            owner,
            data,
            use_now_ts=True,
            use_agent_state=True,
            use_recall=False,
            now_ts=now_ts,
            agent_state_dict=agent_state_dict,
            recall_query=recall_query,
        )
        self._fill_section(ctx.recent, recent_items, audit, LAYER_RECENT)

        # 3. Long-term
        long_term_items = self._safe_fetch(
            self.long_term_provider,
            ai_name,
            owner,
            data,
            use_now_ts=True,
            use_agent_state=True,
            use_recall=True,
            now_ts=now_ts,
            agent_state_dict=agent_state_dict,
            recall_query=recall_query,
        )
        self._fill_section(ctx.long_term, long_term_items, audit, LAYER_LONG_TERM)

        # 4. Dynamic World
        dynamic_items = self._safe_fetch(
            self.dynamic_world_provider,
            ai_name,
            owner,
            data,
            use_now_ts=True,
            use_agent_state=True,
            use_recall=False,
            now_ts=now_ts,
            agent_state_dict=agent_state_dict,
            recall_query=recall_query,
        )
        self._fill_section(ctx.dynamic_world, dynamic_items, audit, LAYER_DYNAMIC_WORLD)

        # 总预算审计
        total_tokens = ctx.total_token_estimate()
        audit["total_token_estimate"] = total_tokens
        audit["total_budget"] = self.budget.total_max
        audit["total_over_budget"] = total_tokens > self.budget.total_max

        self._last_audit = audit
        return ctx

    # ------------------------------------------------------------------
    # 内部：安全调用 Provider
    # ------------------------------------------------------------------
    def _safe_fetch(
        self,
        provider,
        ai_name: str,
        owner: str,
        data: Dict[str, Any],
        use_now_ts: bool,
        use_agent_state: bool,
        use_recall: bool,
        now_ts: Optional[float],
        agent_state_dict: Optional[Dict[str, Any]],
        recall_query: Optional[str],
    ) -> List[Dict[str, Any]]:
        """根据 Provider 的真实签名调用 fetch()。"""
        kwargs: Dict[str, Any] = {}
        if use_now_ts:
            kwargs["now_ts"] = now_ts
        if use_agent_state:
            kwargs["agent_state_dict"] = agent_state_dict
        if use_recall:
            kwargs["recall_query"] = recall_query

        try:
            items = provider.fetch(ai_name, owner, data, **kwargs)
        except TypeError:
            # 回退：只传三个基础参数（用于 StableCoreProvider 等）
            items = provider.fetch(ai_name, owner, data)

        if not isinstance(items, list):
            return []
        return items

    # ------------------------------------------------------------------
    # 内部：填充 Section + Budget Enforcement + Truncation
    # ------------------------------------------------------------------
    def _fill_section(
        self,
        section: ContextSection,
        items: List[Dict[str, Any]],
        audit: Dict[str, Any],
        layer_name: str,
    ) -> None:
        """
        将 items 复制后加入 section。

        策略：
        - 逐条尝试加入
        - 加入后若超过 section.budget_max，则回退该 item，标记 truncated=True，并停止添加该层后续 item
        - 已成功加入的合法 items 保留
        - 不修改 Provider 原始返回对象
        """
        layer_audit: Dict[str, Any] = {
            "provider_item_count": len(items),
            "added_count": 0,
            "rejected_count": 0,
            "truncated": False,
            "token_estimate": 0,
            "budget_max": section.budget_max,
        }

        for item in items:
            if not isinstance(item, dict):
                layer_audit["rejected_count"] += 1
                continue

            # 复制 item，避免修改 Provider 原始输出
            item_copy = copy.deepcopy(item)

            # 尝试加入
            section.items.append(item_copy)
            current_tokens = section.token_estimate()

            if section.budget_max > 0 and current_tokens > section.budget_max:
                # 超预算：回退当前 item
                section.items.pop()
                section.truncated = True
                layer_audit["truncated"] = True
                layer_audit["rejected_count"] += 1
                # deterministic：一旦超预算，停止添加该层后续 item（尾部截断）
                break
            else:
                layer_audit["added_count"] += 1

        layer_audit["token_estimate"] = section.token_estimate()
        audit["layers"][layer_name] = layer_audit

    # ------------------------------------------------------------------
    # 审计 / 自描述
    # ------------------------------------------------------------------
    def describe(self) -> Dict[str, Any]:
        """返回审计信息（不包含完整 Context 内容）。"""
        return {
            "name": "context_assembler",
            "providers": {
                "stable_core": getattr(self.stable_core_provider, "name", "unknown"),
                "recent": getattr(self.recent_provider, "name", "unknown"),
                "long_term": getattr(self.long_term_provider, "name", "unknown"),
                "dynamic_world": getattr(self.dynamic_world_provider, "name", "unknown"),
            },
            "budget": self.budget.to_dict(),
            "last_audit": self._last_audit,
        }