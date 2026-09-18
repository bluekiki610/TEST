# 20260918_P0-3A_Agent_Runtime_Contract.md

> 版本：2026-09-18
> 基线 commit：eabaa2779b37769d45b6f225e594982334dcedb5
> 依赖：P0-1 AgentState / P0-2A Event / P0-2B Event Adapter / P0-2D Event Semantics
> 原则：只定义 Contract；不实现 Runtime；不调用 LLM；不修改现有系统

---

## 0. P0-3A 阶段定位

**P0-3A = Agent Runtime Contract & Lifecycle Design**

只回答一个问题：

> **一个 AI 从"收到一个 Event"到"未来可能 Action"的生命周期和接口边界是什么？**

### 允许
- ✅ 定义 AgentRuntime 生命周期 Contract
- ✅ 定义 WakeDecision / ContextLayers / Decision 数据结构
- ✅ 定义 Token Cost Gate 原则
- ✅ 定义 Context Budget 边界
- ✅ 新增 `agent/runtime.py`（Contract Stub）
- ✅ 新增本文档

### 禁止
- ❌ EventBus / EventStore / Scheduler / Background Worker
- ❌ Brain / Decision Engine / Action Engine 实现
- ❌ Autonomous AI loop / AI↔AI autonomous loop
- ❌ TTS / VoiceStudio 接入
- ❌ World Clone / multi-tenant 实现
- ❌ ai_id 迁移
- ❌ Memory 重写
- ❌ Chat pagination 实现
- ❌ 修改 `data.json` schema
- ❌ 重写 `ext_ai.py` / `ext_world.py` / `ext_date.py`
- ❌ 修改 `main.py`

---

## 1. 核心原则：V3.0 不是重写 Linkong
Agent Runtime = 新的控制/编排层
ext_* = 现有世界能力

text

数据流：
Agent Runtime
↓
Decision
↓
Action
↓
现有 ext_* 能力
↓
World 改变
↓
Event

text

**绝对禁止**建立第二套平行 World。
**绝对禁止**复制 Chat / Date / Work / Shop / Economy / SMS / Instance / Memory 系统。

---

## 2. Agent Runtime 生命周期（9 阶段）
┌──────────────────────────────────────────┐
│ 1. RECEIVE 收到 Event │
│ ↓ │
│ 2. PERCEIVE 判断 Event 对 AI 是否相关 │
│ ↓ │
│ 3. WAKE_DECISION IGNORE / OBSERVE / THINK │
│ ↓ │
│ 4. CONTEXT 构造未来 LLM 所需 Context │
│ ↓ │
│ 5. THINK 未来调用 Brain / LLM │
│ ↓ │
│ 6. DECISION 未来产生结构化 Decision │
│ ↓ │
│ 7. ACTION 调用现有 Linkong 能力 │
│ ↓ │
│ 8. WORLD_CHANGE 现有系统改变 World │
│ ↓ │
│ 9. EVENT World change 产生新的 Event │
└──────────────────────────────────────────┘

text

**P0-3A 只定义 Contract，不实现完整流程。**

对应 `agent/runtime.py` 的方法：

| 阶段 | 方法 | P0-3A 状态 |
|------|------|-----------|
| 1. RECEIVE | `receive_event(event)` | Stub |
| 2. PERCEIVE | `perceive(event) -> bool` | Stub（返回 False） |
| 3. WAKE_DECISION | `should_wake(event) -> WakeDecision` | Stub（返回 IGNORE） |
| 4. CONTEXT | `build_context(event) -> ContextLayers` | Stub（返回空层） |
| 5. THINK | `think(context) -> Optional[str]` | Stub（返回 None，**绝不调 LLM**） |
| 6. DECISION | `decide(thought) -> Optional[Decision]` | Stub（返回 None） |
| 7. ACTION | `execute(decision) -> bool` | Stub（返回 False） |
| 8. WORLD_CHANGE | —— | 由现有 ext_* 负责 |
| 9. EVENT | —— | 由 P0-2B Adapter / 未来 Adapter 负责 |

---

## 3. 四种概念必须严格区分

| 概念 | 定义 | 示例 |
|------|------|------|
| **AgentState** | 现在是什么状态 | "Dan 在咖啡馆，能量 70" |
| **Event** | 刚刚发生了什么 | "message_received" |
| **Decision** | AI 决定接下来做什么 | "reply_to_user" |
| **Action** | 系统真正执行什么 | "send_message" |

**禁止混淆**：
❌ Event = "message_received" ≠ Decision ≠ Action

✅ Event: "用户给 Dan 发了一条消息"
✅ Decision: "Dan 决定回复"
✅ Action: "ext_ai.execute_action(ai='Dan', action={'action':'speak', ...})"

text

---

## 4. Wake Decision Contract

### 4.1 枚举

```python
class WakeDecision(str, Enum):
    IGNORE  = "ignore"   # 不感知
    OBSERVE = "observe"  # 感知但不触发 LLM
    THINK   = "think"    # 值得进入 Brain
4.2 与 P0-2D Event 级别的关系
⚠️ P0-3A 不把它们错误地实现成已存在的调度系统。

层面	概念	归属
Event Semantics 层	NONE / LOW / HIGH	P0-2D 已冻结
Agent Runtime 层	IGNORE / OBSERVE / THINK	P0-3A 定义
关键区分：

text
✅ Event → Wake Decision → 是否需要 Agent 思考
❌ Event → 直接 LLM
4.3 未来推演（未实现）
text
Event 级别（P0-2D）   →   Wake Decision（P0-3A）
─────────────────────────────────────────────
NONE                  →   IGNORE（通常）
LOW                   →   OBSERVE（通常）
HIGH                  →   候选 THINK（还需 Wake Score 二次筛选）

⚠️ 这不是硬映射，最终由未来 Wake Score 综合判断。
5. Token Cost Gate（P0-3 最重要约束）
5.1 当前真实基线
普通 AI 对话的完整上下文目前约：7,000–10,000 tokens（P0-2D 已冻结）。

5.2 关键约束
未来自主世界事件不能默认每次都发送 7,000–10,000 tokens 的完整上下文给 LLM。

5.3 成本模型
text
LLM Cost ≈ LLM Call Count × Context Size
因此：

text
Event 数量增加
    ≠
LLM 调用数量等比例增加
5.4 未来 Gate 结构（P0-3A 只定义）
text
Event
    ↓
Wake Gate（未来 Scheduler + Wake Score）
    ↓
是否值得思考
    ↓
Context Budget（未来 Context Builder）
    ↓
LLM
6. Context Budget 边界（P0-3A 只定义接口）
6.1 四层结构
层级	内容	特性	是否长期增长
A. Stable Core	世界设定 / AI 人设 / 核心用户信息 / 长期身份	固定	❌ 稳定
B. Recent	当前对话 / 最近 Event / 当前活动	短期	❌ 有界
C. Long-term	Memory / Relationship / 历史事件	按需检索	✅ 可增长
D. Dynamic World	AgentState / 当前地点 / 当前世界状态	动态	❌ 瞬时
6.2 核心原则
历史数据可以持续增长，但单次 LLM Context 不应该跟着历史数据线性增长。

6.3 未来实现（P1 阶段）
A / B / D 层：每次注入（有界）

C 层：按需检索（Memory Recall / Cue）

具体机制由 P1 Memory / Context Architecture 设计

7. 为 5 AI 共同世界留下接口
7.1 目标架构
未来最多支持：

text
一个 World：
    User A → AI A
    User B → AI B
    User C → AI C
    User D → AI D
    User E → AI E
7.2 Runtime 实例化模型
text
✅ 正确：
    AgentRuntime(AI_A)
    AgentRuntime(AI_B)
    AgentRuntime(AI_C)
    AgentRuntime(AI_D)
    AgentRuntime(AI_E)

❌ 错误：
    一个超级 AI Runtime 管理所有 AI 的人格
7.3 每个 AI 独立拥有
AgentState

perception

future goals

future memory access

future relationship context

future voice identity

7.4 共享
World

Event

World rules

existing Linkong capabilities

8. 为未来 AI ↔ AI 留接口
8.1 当前状态
维度	状态
多 AI 共享世界	✅ 已具备
群聊同时响应	✅ 已具备
真正独立的 AI↔AI 自主社交生命周期	❌ 尚未形成
8.2 P0-3A 只确保未来可实现
text
AI A
    ↓
Action
    ↓
World Event
    ↓
AI B perceives
    ↓
AI B decides
    ↓
Action
    ↓
World Event
禁止：AI A 直接调用 AI B 的 Brain。

9. 为 VoiceStudio 留接口
9.1 未来 Action / Output Contract
text
Decision
    ↓
Action
    ↓
message / speech
    ↓
Voice Identity
    ↓
VoiceStudio
9.2 未来每个 AI 可拥有
text
agent_id
voice_id
9.3 P0-3A 约束
❌ 不接 TTS

❌ 不修改现有 AI identity 系统

❌ 不进行 ai_id migration

10. 为 World Clone / Community Instance 留接口
10.1 当前基础
main.py 已存在 WORLD_ID

data 文件存在 data_<WORLD_ID>.json

10.2 P0-3A 约束
❌ 不改造 WORLD_ID

❌ 不创建 multi-tenant 系统

✅ 只在架构文档中定义未来目标

10.3 未来目标
text
world_A
world_B
world_C
每个 World 最终拥有独立：

users / AIs / rooms / messages

relationships / memories / economy / activities

instances / voice mappings / world configuration

10.4 核心原则
不同五人组之间的数据必须完全隔离。

这是未来架构目标，不是 P0-3A 实现内容。

11. Realism vs Token Cost
11.1 设计原则
真人感 ≠ 每件事情都让 LLM 思考。

11.2 分类
事件类型	是否触发 LLM
机械世界变化	❌ 不需要
低价值 Event	❌ 不需要
普通状态变化	❌ 不需要
高价值社交事件	✅ 可以触发 THINK
重大关系变化	✅ 可以触发 THINK
重要活动	✅ 可以触发 THINK
用户直接与 AI 对话	✅ 保持现有高质量上下文
11.3 目标
用少量高价值思考，制造持续的"AI 活着"的感觉。

12. P0-3A 禁止事项（完整清单）
text
❌ EventBus
❌ EventStore
❌ Scheduler
❌ Background Worker
❌ Brain implementation
❌ Decision Engine implementation
❌ Action Engine implementation
❌ Autonomous AI loop
❌ AI↔AI autonomous loop
❌ TTS
❌ VoiceStudio integration
❌ World clone implementation
❌ multi-tenant implementation
❌ ai_id migration
❌ Memory rewrite
❌ Chat pagination implementation
❌ 修改 data.json schema
❌ 重写 ext_ai.py
❌ 重写 ext_world.py
❌ 重写 ext_date.py
❌ 修改 main.py
13. 允许修改的文件
只允许新增：

文件	内容
agent/runtime.py	AgentRuntime Contract Stub（~200 行）
20260918_P0-3A_Agent_Runtime_Contract.md	本文档
不修改任何其他文件。

14. Runtime Contract 方法清单
方法	输入	输出	P0-3A 状态
__init__(ai_name, data)	AI 名 + data 引用	AgentRuntime 实例	✅ 已定义
receive_event(event)	Event	None	Stub
perceive(event)	Event	bool	Stub（False）
should_wake(event)	Event	WakeDecision	Stub（IGNORE）
build_context(event)	Event	ContextLayers	Stub（空层）
think(context)	ContextLayers	Optional[str]	Stub（None，绝不调 LLM）
decide(thought)	Optional[str]	Optional[Decision]	Stub（None）
execute(decision)	Optional[Decision]	bool	Stub（False）
get_state()	——	Optional[AgentState]	透传 P0-1 能力
15. 架构验收表
15.1 Capability Preservation
能力	是否保留
[ ] Chat	✅ 未修改
[ ] World	✅ 未修改
[ ] Date	✅ 未修改
[ ] Work	✅ 未修改
[ ] Shop	✅ 未修改
[ ] Economy	✅ 未修改
[ ] SMS	✅ 未修改
[ ] Room	✅ 未修改
[ ] Instance	✅ 未修改
[ ] Memory	✅ 未修改
[ ] AI living	✅ 未修改
[ ] AI↔AI groundwork	✅ 保留接口
[ ] 5 AI shared World	✅ 保留接口
[ ] VoiceStudio future integration	✅ 保留接口
[ ] World Clone future architecture	✅ 保留接口
15.2 Token Safety
检查项	状态
[ ] 不会因为 Event 数量增加而自动等比例增加 LLM	✅ 通过 Runtime Gate 设计
[ ] 不默认每个 Event 使用 7,000–10,000 token context	✅ NONE/LOW 不调 LLM
[ ] Context Budget 已有明确边界	✅ 4 层结构定义
[ ] 历史数据不会被设计成每次全部塞进 prompt	✅ Long-term 层按需检索
16. P0-3A 最终目标
目标不是"让 AI 今天就开始疯狂调用 LLM"。

目标是：给未来真正活起来的 AI，建立一个不会失控、不会爆 token、不会破坏旧世界的生命循环骨架。

17. 完成状态
已完成（Contract 定义）
✅ AgentRuntime 生命周期 Contract

✅ WakeDecision / ContextLayers / Decision 数据结构

✅ Token Cost Gate 原则

✅ Context Budget 4 层边界

✅ 5 AI 独立 Runtime 接口

✅ AI↔AI 接口预留

✅ VoiceStudio 接口预留

✅ World Clone 接口预留

✅ 架构验收表

尚未实现（未来 P0-3B+）
❌ EventBus

❌ Scheduler

❌ Wake Score 实现

❌ Brain / LLM 调用

❌ Decision Engine

❌ Action Engine

❌ AI↔AI autonomous loop

❌ TTS / VoiceStudio

❌ World Clone

❌ Context Builder

因此
P0-3A 不是"Agent Runtime 已实现"。

P0-3A 是：

"把 Agent Runtime 的生命周期与接口边界冻结下来。"
