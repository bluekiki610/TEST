"""
agent/context.py - Phase B1: Context Data Contract

本文件只定义 Context 的数据结构和预算模型。

硬性约束（B1）：
1. 不读取 main.data
2. 不访问 Provider
3. 不组装 Prompt
4. 不调用 LLM
5. 不进入 think / decide / execute
6. 不修改任何现有业务代码
7. 不启用 ext_memory

四层：
- Stable Core   (世界观 / 人设 / 用户画像 / 长期身份)
- Recent        (当前对话 / 最近事件 / 当前活动)
- Long-term     (Memory / Relationship / 历史事件，按需检索)
- Dynamic World (AgentState / 当前位置 / 当前世界状态)

设计原则：
- Context 是结构化对象，不是拼好的 Prompt 字符串
- 每层有独立预算上限
- 结构允许未来扩展（Decision-Relevant Constraints 已预留字段）
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import time


# =========================================================
# 层名常量
# =========================================================
LAYER_STABLE_CORE = "stable_core"
LAYER_RECENT = "recent"
LAYER_LONG_TERM = "long_term"
LAYER_DYNAMIC_WORLD = "dynamic_world"

ALL_LAYERS = (
    LAYER_STABLE_CORE,
    LAYER_RECENT,
    LAYER_LONG_TERM,
    LAYER_DYNAMIC_WORLD,
)


# =========================================================
# Token 估算
# =========================================================
def estimate_tokens(obj: Any) -> int:
    """
    粗略估算 obj 的 token 数。

    规则：
    - None → 0
    - str → max(1, len(s) // 2)（与 ext_ai.build_ai_context 的估算方式一致）
    - int/float/bool → 1
    - dict → 递归累加 key + value
    - list/tuple → 递归累加

    不引入 tokenizer 依赖（B1 只定义预算机制，不追求精确值）。
    """
    if obj is None:
        return 0
    if isinstance(obj, bool):
        return 1
    if isinstance(obj, str):
        return max(1, len(obj) // 2) if obj else 0
    if isinstance(obj, (int, float)):
        return 1
    if isinstance(obj, dict):
        return sum(estimate_tokens(k) + estimate_tokens(v) for k, v in obj.items())
    if isinstance(obj, (list, tuple)):
        return sum(estimate_tokens(x) for x in obj)
    return 1


# =========================================================
# 预算模型
# =========================================================
@dataclass
class ContextBudget:
    """
    四层 Context 的 token 预算。

    默认值基于当前 Linkong 真实上下文基线（7k-10k tokens / 对话）。
    四层之和略低于基线，留 buffer 防止超限。
    """
    stable_core_max: int = 2000
    recent_max: int = 3000
    long_term_max: int = 2500
    dynamic_world_max: int = 1000
    total_max: int = 8500

    def limit_for(self, layer: str) -> int:
        """返回指定层的预算上限。未知层返回 0。"""
        return {
            LAYER_STABLE_CORE: self.stable_core_max,
            LAYER_RECENT: self.recent_max,
            LAYER_LONG_TERM: self.long_term_max,
            LAYER_DYNAMIC_WORLD: self.dynamic_world_max,
        }.get(layer, 0)

    def to_dict(self) -> Dict[str, int]:
        return {
            "stable_core_max": self.stable_core_max,
            "recent_max": self.recent_max,
            "long_term_max": self.long_term_max,
            "dynamic_world_max": self.dynamic_world_max,
            "total_max": self.total_max,
        }


# =========================================================
# 单层 Section
# =========================================================
@dataclass
class ContextSection:
    """
    一层的结构化内容。

    items 是结构化条目列表（每个条目是 dict），不是拼好的字符串。
    B1 只负责存储 + 预算检查；具体裁剪由 B2/B3 实现。
    """
    layer: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    budget_max: int = 0
    truncated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def token_estimate(self) -> int:
        """本层当前的 token 估算。"""
        return estimate_tokens(self.items)

    def is_over_budget(self) -> bool:
        """是否超过本层预算。budget_max <= 0 视为无限制。"""
        if self.budget_max <= 0:
            return False
        return self.token_estimate() > self.budget_max

    def add_item(self, item: Dict[str, Any]) -> None:
        """追加一条结构化 item（必须是 dict）。"""
        if not isinstance(item, dict):
            raise TypeError(
                f"ContextSection item must be a dict, got {type(item).__name__}"
            )
        self.items.append(item)

    def to_dict(self) -> Dict[str, Any]:
        """只返回元信息，不返回 items（防止意外泄漏到 Prompt）。"""
        return {
            "layer": self.layer,
            "item_count": len(self.items),
            "token_estimate": self.token_estimate(),
            "budget_max": self.budget_max,
            "truncated": self.truncated,
            "metadata": dict(self.metadata),
        }


# =========================================================
# AgentContext
# =========================================================
@dataclass
class AgentContext:
    """
    一个 AI 在某一时刻的 Context 结构化视图。

    注意：
    - 这只是数据结构，不是 Prompt
    - 不负责拼装字符串（由 B3 Context Assembler 负责）
    - 不负责读取 main.data（由 B2 Providers 负责）
    """
    ai_name: str
    stable_core: ContextSection
    recent: ContextSection
    long_term: ContextSection
    dynamic_world: ContextSection
    created_at: float = field(default_factory=time.time)

    # 预留：Decision-Relevant Constraints（B1 不实现，只保留 schema 位置）
    decision_constraints: Optional[Dict[str, Any]] = None

    def sections(self) -> List[ContextSection]:
        """返回四层，顺序固定：Stable → Recent → Long-term → Dynamic。"""
        return [self.stable_core, self.recent, self.long_term, self.dynamic_world]

    def total_token_estimate(self) -> int:
        return sum(s.token_estimate() for s in self.sections())

    def is_over_budget(self, budget: ContextBudget) -> bool:
        """整体是否超过总预算。"""
        return self.total_token_estimate() > budget.total_max

    def to_debug_dict(self) -> Dict[str, Any]:
        """
        调试用序列化。

        不包含 items 内容，只包含元信息。
        目的是防止 Context 内容意外泄漏到日志或 SSE。
        """
        return {
            "ai_name": self.ai_name,
            "created_at": self.created_at,
            "total_token_estimate": self.total_token_estimate(),
            "sections": [s.to_dict() for s in self.sections()],
            "has_decision_constraints": self.decision_constraints is not None,
        }


# =========================================================
# 工厂
# =========================================================
def make_empty_context(
    ai_name: str,
    budget: Optional[ContextBudget] = None,
) -> AgentContext:
    """
    创建一个空的四层 AgentContext。

    不读取任何数据，不调用任何 Provider。
    """
    b = budget or ContextBudget()
    return AgentContext(
        ai_name=ai_name,
        stable_core=ContextSection(
            layer=LAYER_STABLE_CORE,
            budget_max=b.stable_core_max,
        ),
        recent=ContextSection(
            layer=LAYER_RECENT,
            budget_max=b.recent_max,
        ),
        long_term=ContextSection(
            layer=LAYER_LONG_TERM,
            budget_max=b.long_term_max,
        ),
        dynamic_world=ContextSection(
            layer=LAYER_DYNAMIC_WORLD,
            budget_max=b.dynamic_world_max,
        ),
    )
