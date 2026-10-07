# V3.1 Phase D-0 Architecture Decisions

**Status:** DECIDED
**Phase:** V3.1 Phase D-0（World / Activity / Capability Foundation）
**Document Type:** Architecture Decision Record（正式裁决记录）
**依据：**
- `docs/D0_WORLD_ACTIVITY_CAPABILITY_PREFLIGHT.md`（D-0 设计冻结准备文件）
- `docs/D0_CONFLICT_AUDIT.md`（D-0 冲突审计，45 项发现，**ACCEPTED**）
- 架构侧《D-0 架构裁决与 DS 下一步执行说明》

**上游状态：** D-0 Audit = **ACCEPTED**
**本文件作用：** 将架构侧裁决正式固化为可引用的 D-0 决策记录
**下游动作：** `docs/V3.1_ARCHITECTURE_CONTRACT.md` Contract Change → D-0 Tests → D-0 Seal
**Implementation Status:** **NO CODE IMPLEMENTATION AUTHORIZED**（本阶段不实现 Activity / Capability / World Query）
**Last Updated:** 2026-09-30

---

## 0. 本文件的性质与边界

本文件记录 **D-0 的架构裁决**，不记录实现方案。

它**不是**：
- 不是 Contract（Contract 是 `docs/V3.1_ARCHITECTURE_CONTRACT.md`）
- 不是实现说明
- 不是 Phase D 路线图（路线图见 `PROJECT_V3.1_MASTER.md`）
- 不是对 A/B/C Contract 的重写

它**是**：

> **在 D-0 Audit 之后、"Contract Change 之前"，把架构侧对 5 个 OPEN QUESTION 与 SOT 治理问题的裁决固定下来，使 Contract Change 有明确依据，使 D-1 不需要 DS 自行猜测架构。**

### 0.1 文档关系

```text
V3.1_PRODUCT_GUIDE.md            ← 我们到底在创造什么
        ↓
docs/V3.1_ARCHITECTURE_CONTRACT.md   ← 技术上什么允许、什么禁止（本文件的裁决将写入其中）
        ↓
docs/D0_WORLD_ACTIVITY_CAPABILITY_PREFLIGHT.md   ← Phase D 在冻结前需要决定什么
        ↓
docs/D0_CONFLICT_AUDIT.md        ← 现状与设计之间的冲突（ACCEPTED）
        ↓
docs/D0_ARCHITECTURE_DECISIONS.md ← 【本文件】裁决
        ↓
PROJECT_V3.1_MASTER.md           ← 项目现在做到哪里
```

### 0.2 冲突解决顺序

**Contract > 本文件 > D-0 Preflight > D-0 Audit > 旧文档。**

本文件中的决策在写入 Contract 后，以 Contract 为准。

### 0.3 本文件不改变的既有事实

D-0 Audit（`D0-044`）已确认，以下 A/B/C 基线**不被本裁决改变**：

| # | 事实 |
|---|------|
| 1 | `main.data` 仍是当前唯一 World 存储位置 |
| 2 | `AgentState` 仍是只读投影 |
| 3 | `Goal` / `Commitment` 仍是 Runtime-only working state，非 SOT |
| 4 | `AgentRuntime` 不被重新设计 |
| 5 | `AgentContext` 不被破坏；仍是唯一正式 Context 结构 |
| 6 | `think(context) -> IntentSet` 仍是 Stub |
| 7 | `ContextLayers` 保留为 deprecated compatibility stub |

---

## 1. 决策总览

| 决策编号 | 主题 | 对应 OPEN QUESTION / 发现 | 状态 |
|---------|------|--------------------------|------|
| **D0-DEC-1** | Memory Runtime "OFF" 的定义 | OPEN-1 | ✅ DECIDED |
| **D0-DEC-2** | Activity 的正式归属 + 旧 18 个状态的定义 | OPEN-2 / `D0-026` | ✅ DECIDED |
| **D0-DEC-3** | Event 权威收敛（三套通道） | OPEN-3 | ✅ DECIDED |
| **D0-DEC-4** | Capability 与 `execute_action` 的迁移关系 | OPEN-4 / `D0-009` | ✅ DECIDED |
| **D0-DEC-5** | World Tick 可靠性缺陷的处理时机 | OPEN-5 / `D0-030` / `D0-031` | ✅ DECIDED |
| **D0-DEC-6** | `main.data` SOT 治理原则 | `D0-034` / `D0-044` | ✅ DECIDED |
| **D0-DEC-7** | 45 项发现的重新分层（A/B/C/D/E 类） | `D0_CONFLICT_AUDIT.md` | ✅ DECIDED |
| **D0-DEC-8** | 事实基线的确定（Inventory 过时） | `D0-045` | ✅ DECIDED |

**未有新增 OPEN QUESTION。** 本次裁决关闭了全部 5 个原有 OPEN QUESTION。

---

## 2. D0-DEC-1 · Memory Runtime "OFF" 的定义

### 2.1 裁决

> **Memory Runtime 在 V3.1 当前阶段属于「业务功能关闭状态」：**
> **不得产生有效 Memory 写入、不得进入 Agent Context、不得影响 Agent Decision。**

但：

> **不要求 D-0 立即删除所有 Memory 代码、线程或旧 scheduler。**

即：

```text
Memory Runtime
        │
        ├── 不产生有效 Memory
        ├── 不进入 AgentContext
        ├── 不参与 Agent Decision
        └── 不作为 D 阶段依赖
```

### 2.2 关键澄清（来自 `D0-004` / `D0-035` / `D0-042`）

| 事实 | 判定 |
|------|------|
| `ext_memory.enqueue_event` 写入路径不可达（`_enqueue_event_impl` 未定义） | 是（现状） |
| 夜间 scheduler 线程**仍然可能启动** | 是（现状） |
| `ai_memories` 只写不读（`D0-042`） | 是（现状） |
| `ext_mem.py` 缺 `import time` 导致写路由 500（`D0-040`） | 是（现状缺陷） |

因此：

> **`ext_memory.py` 的夜间 scheduler 即使代码层面仍然存在，也不能被视为「Memory 已经正常工作」。**

### 2.3 D-0 / D 阶段明确不做

- ❌ 不修 `enqueue_event`
- ❌ 不修 Memory scheduler
- ❌ 不接 LongTerm Recall
- ❌ 不把 `ai_memories` 接入 Context
- ❌ 不让 D 阶段任何环节依赖 Memory
- ❌ 不修 `ext_mem.py` 的 `import time` 缺陷（属独立缺陷修复，不属 D-0）

### 2.4 未来方向

Memory 单独进入 **Phase E**，重新设计：

```text
Event
 ↓
Memory Runtime
 ↓
Memory Decision
 ↓
Memory Store
 ↓
Recall
 ↓
Context
```

---

## 3. D0-DEC-2 · Activity 的正式归属与 Legacy Activity State

### 3.1 裁决

> **Activity 是未来唯一正式的「持续世界过程」抽象。**

但：

> **现有 18 个旧活动字段不是马上删除，也不是继续升级成 Activity SOT。**
> **它们统一定义为：Legacy Activity State / Legacy Projection。**

```text
旧系统
18 个分散状态
       ↓
Legacy Activity State
```

未来：

```text
正式 Activity
       ↓
World SOT
       ↓
各种 Projection / Compatibility
```

最终方向：

```text
Activity
  │
  ├── work
  ├── date
  ├── shopping
  ├── cooking
  ├── companion
  ├── travel
  ├── game
  └── ...
```

### 3.2 绝对禁止（否则 D 阶段会产生新的 Second SOT）

```text
main.data.activity
+
ext_date  自己一套 activity
+
ext_shop  自己一套 activity
+
ext_econ  自己一套 activity
+
ext_ai.current_activity
```

**不允许上述任一形式并存为「多个 Activity 真相」。**

### 3.3 Legacy Activity State 清单（基线，来自 `D0-026`）

以下字段在 D-0 阶段被**正式定义**为 Legacy Activity State（**只登记，不修改**）：

| # | key | 所有者（现状） | 对应目标 Activity |
|---|-----|--------------|------------------|
| 1 | `dates[]` | `ext_date` | DATE |
| 2 | `date_invites[ai]` | `ext_date` | Commitment + Activity |
| 3 | `date_invites_out[ai]` | `ext_date` / `ext_ai` | Commitment + Activity |
| 4 | `date_invite_out_<ai>` | `ext_date` / `ext_ai`（**双实现**） | 调度标记 |
| 5 | `date_last_invite_ts[ai]` | `ext_date` / `ext_ai`（**双实现**） | 调度标记 |
| 6 | `work_sessions[ai]` | `ext_econ` | WORK |
| 7 | `work_switch[ai]` | `ext_econ` / `ext_room` | 状态位 |
| 8 | `home_jobs[ai]` | `ext_econ` | World Fact |
| 9 | `ai_auto_work_mark[ai]` | `ext_ai` | 调度标记 |
| 10 | `ai_shop_state[ai]` | `ext_shop` | SHOP |
| 11 | `ai_follow[ai]` | `ext_ai` | Movement |
| 12 | `ai_pending_moves[ai]` | `ext_ai` / `main` | Movement |
| 13 | `ai_meeting[ai]` | `ext_ai` | MEETING |
| 14 | `ai_stay_put[ai]` | `ext_ai` | 状态位 |
| 15 | `ai_vacation[ai]` | `ext_ai` | 状态位 |
| 16 | `ai_life_policy[ai]` | **无写入方**（`D0-032`） | 失效门禁 |
| 17 | `ai_spot_state[ai]` | `ext_world` | 到达检测 |
| 18 | `instances[*].status` | `ext_instance` | INSTANCE |
| 19 | 节律/调度 10 项（`story_rhythm` / `writing_rhythm` / `living_rhythm` / `ai_home_act_next` / `ai_auto_next` / `_last_think_invite` / `ai_drive_log` / `ai_last_human` / `ai_last_auto` / `ai_diary_log`） | 多模块 | Scheduler |

> **注意：** Contract **AC-2 / AC-3** 仍生效——D 阶段**不修改** `work_sessions` / `dates` / `ai_shop_state` / `instances` 等字段。

### 3.4 Activity 与 Goal / Commitment 的关系（必须保持）

```text
Goal
= 我想完成什么

Commitment
= 我答应 / 承诺了什么

Activity
= 我现在正在经历什么持续过程
```

示例：

```text
Goal:
    今晚想和主人见面

Commitment:
    19:00 与主人在咖啡馆见面

Activity:
    DateActivity
    19:00～
    咖啡馆
    participants = [AI, User]
    status = ACTIVE
```

**三者不能混为一谈。**（对应 **INVARIANT-5 / INVARIANT-6**）

### 3.5 Activity 的正式建立位置

> **Activity 的 data model / lifecycle / ownership / SOT / persistence / restart semantics / legacy mapping 一律在 D-2 建立。**
> **D-0 不实现。**

---

## 4. D0-DEC-3 · Event 权威收敛

### 4.1 裁决

> **只有 `agent.Event` 是正式的 Domain / World Event 语义。**

三套通道的正式定位：

| 通道 | 正式定位 | 是否 Domain Event |
|------|---------|------------------|
| **`agent.Event`** | **正式 Domain / World Event** | ✅ **是** |
| `ext_memory.enqueue_event` | **Legacy Memory ingestion mechanism** | ❌ 不是 |
| SSE `app.push_event` | **Presentation / Transport Notification** | ❌ 不是 |

### 4.2 对 `enqueue_event` 的约束

> **不允许：**

```text
World
 ↓
enqueue_event
 ↓
把它当 Event Bus
```

未来 Memory 必须接：

```text
World Change
 ↓
agent.Event
 ↓
Memory Runtime
```

因此：

> **`enqueue_event` 最终属于 Memory 迁移对象，不属于 D 阶段新的 Event 核心。**

### 4.3 对 SSE 的约束

```text
agent.Event
     │
     ├── Agent Runtime
     │
     ├── Memory Runtime（未来）
     │
     └── SSE Projection / Notification
                 ↓
              Frontend
```

> SSE 是「告诉前端发生了什么」；
> `agent.Event` 是「世界真的发生了什么」。

### 4.4 main channel

> **main channel 最终也必须能够产生正式 `agent.Event`。**

但：

> **不是 D-0 现在立刻改。** 放到 **D-1 / D-5 Event Coverage** 解决。

### 4.5 与既有 Contract 的关系

本裁决与 Contract **EV-8**（旧 `enqueue_event` 与新 `agent.Event` 不是同一系统，不得混用）**一致**，并进一步明确了 SSE 的定位。

**D 阶段不实现新的 Event Bus。**（Contract §17 仍生效）

---

## 5. D0-DEC-4 · Capability 与 `execute_action` 的迁移关系

### 5.1 裁决

> **不删除 `execute_action`。**
>
> **但从现在开始，禁止 Agent Core 继续新增对 `execute_action` 的直接依赖。**

### 5.2 迁移关系

旧：

```text
Agent
 ↓
ext_ai.execute_action()
```

新（目标）：

```text
Agent
 ↓
Capability Request
 ↓
Capability
 ↓
旧 execute_action / ext_xxx
 ↓
World
```

迁移阶段允许：

```text
Capability Adapter
       ↓
Legacy execute_action
```

因此：

> **`execute_action` 暂时作为 Legacy Execution Adapter 存活。**
> **它不是未来架构。**

### 5.3 为什么这样处理

不能为了「漂亮架构」突然删除现有 Action 系统，因为那会一次性破坏：

```text
聊天 / 移动 / SMS / Date / Shop / Economy / Work / Story / 其他现有行为
```

正确迁移方式：

```text
新 Agent Core
      ↓
Capability Port
      ↓
Legacy Adapter
      ↓
execute_action
      ↓
旧功能
```

然后 **D-6** 再逐渐把具体 Capability 从 Legacy Adapter 中拆出。

这符合 Ports & Adapters 的基本思想：核心定义抽象边界，具体旧实现可以暂时作为 Adapter 存在，之后再替换，而不是一次性重写整个系统。

### 5.4 明确的禁止项

- ❌ 删除 `execute_action`
- ❌ 在 D-0 重写 `execute_action` 内部分发结构
- ❌ Agent Core 新增 `ext_*` 直接 import
- ❌ Agent Core 新增对 `m.drive_ai` / `m.call_llm` / `m.auto_start_work` 等未声明挂载点的依赖

（Contract **AI-1 / AI-2 / AX-3** 继续生效）

---

## 6. D0-DEC-5 · World Tick 可靠性缺陷的处理时机

### 6.1 裁决

> **现在不把它当 D-0 修复任务。**
>
> **但必须列为 D-3 的前置 Blocker。**

```text
D-0
不修
 ↓
D-1
World Query
 ↓
D-2
Activity
 ↓
D-3 前置检查
 ↓
修复 World Tick 最小可靠性问题
 ↓
Movement Continuity
```

### 6.2 登记为 Blocker 的具体缺陷

| 编号 | 缺陷 | 位置 |
|------|------|------|
| `D0-030` | World→Memory 调用在**无事件循环的裸线程**中抛 `RuntimeError`，调用**未包 `try`** → 异常**截断 30 秒 World tick**，并**跳过 `save_data()`** | `ext_world.py:129 / 222 / 251 / 269`，兜底仅 `:306-307` |
| `D0-031` | `_arrive` 内「到达建筑」记忆事件分支**不可达**（`ai_spot_tick:303` 先于 `:305` 赋值 → `prev_bid != bid` 恒为 False）；且 `if prev and bid` 使**首次到达完全不触发** | `ext_world.py:154-166` / `300-305` |

### 6.3 修复原则

> **只做最小可靠性修复。**

例如：

```text
Memory failure
↓
不能杀死 World Tick
```

而不是：

> 顺便重写 `ext_world`。

更不能：

> 顺手把 Memory 修好了。

### 6.4 附带约束

- 若必须修，**走独立 Contract Change**，不夹带在 D-0 或 D-1 中
- `D0-031` 的到达语义问题必须在 **D-3 之前**处理（否则 D-3 无可靠输入）

---

## 7. D0-DEC-6 · `main.data` SOT 治理原则

### 7.1 裁决

`D0-044` 的判断被架构侧采纳：

> **`main.data` 在「位置」上是唯一存储位置，但尚未成为被架构治理的 SOT。**

```text
唯一存储位置
≠
真正被架构治理的 SOT
```

### 7.2 D 阶段的目标

> **不是创建第二个 World，而是把现有唯一 World SOT 逐渐治理起来。**

最终：

```text
                    World
                      │
              ┌───────┴───────┐
              │               │
          World Query    World Command
              │               │
            Read             Write
              │               │
              └───────┬───────┘
                      ↓
                  main.data
```

**仍然只有一个事实源。**

### 7.3 由此确立的三条治理原则

| 原则 | 内容 |
|------|------|
| **D0G-1** | `main.data` 是 **唯一 World 存储位置**（本裁决未改变这一点） |
| **D0G-2** | 「唯一存储位置」与「事实治理」是**两个不同概念**，不得混同 |
| **D0G-3** | D 阶段的治理方向是 **收拢读写入口**（World Query 读 / World Command 写），**不是**新建第二个 World、第二个 Activity SOT、或第二个 Event Bus |

### 7.4 明确登记的治理缺陷（D-6 / D-4 处理，D-0 不修）

| 编号 | 缺陷 |
|------|------|
| `D0-034` | `default_data()` 只声明 54 个 key，实际使用约 95 个；约 40 个顶层 key 无声明方，`sanitize_data()` 不校验、不回填 |
| `D0-023` | 3 个扩展就地改写 `app.routes` |
| `D0-037` | `main.py` 4 个路由处理器被物理删除成为死代码 |
| `D0-036` | `ext_admin` 猴补丁替换 `main.is_admin` / `main.owner_of_ai`，静默改写授权语义 |
| `D0-022` | `save_data()` 是未受管的全局写路径（0.5s debounce） |

---

## 8. D0-DEC-7 · 45 项发现的重新分层

> **重要：** 45 项发现**不是** 45 个待修任务。
> 它们是分层记录，**禁止一次性全部修复**。

### A 类 · D 阶段核心架构问题（立即进入 D 设计）

```text
World Query
Activity
Event
Capability
Movement Continuity
Application Command
Legacy Brain Migration
```

对应发现：`D0-014`、`D0-019`、`D0-026`、`D0-033`、`D0-044`

### B 类 · D-6 Legacy Migration

```text
ext_ai 第二大脑
random decision
execute_action
旧 Timer
旧 autonomous life
多处直接 World mutation
旧 movement
旧 date trigger
```

对应发现：`D0-001`、`D0-002`、`D0-006`、`D0-007`、`D0-008`、`D0-009`、`D0-010`、`D0-011`、`D0-012`、`D0-015`、`D0-016`、`D0-017`、`D0-018`、`D0-020`、`D0-021`、`D0-022`、`D0-023`、`D0-025`、`D0-027`、`D0-028`、`D0-029`、`D0-031`、`D0-032`、`D0-036`、`D0-037`、`D0-039`、`D0-041`

### C 类 · Phase E（Memory）

```text
Memory
ai_memories
ext_memory
Memory scheduler
Recall
Impression
Memory SOT
```

对应发现：`D0-003`、`D0-004`、`D0-005`、`D0-030`（Memory 侧）、`D0-035`、`D0-040`、`D0-042`

### D 类 · Presentation / Frontend（D-4 / D-6 处理，现在不改前端）

```text
frontend World mutation
localStorage restore
client-side AI speech
frontend 自己推断状态
```

对应发现：`D0-024`、`D0-025`、`D0-043`

### E 类 · 历史文档错误（D-0 Closure 时统一修订 / 标记）

`D0-045`：Phase A Inventory 已确认部分事实过时。

---

## 9. D0-DEC-8 · 事实基线的确定

### 9.1 裁决

> **当前代码 + `docs/D0_CONFLICT_AUDIT.md` 是 D 阶段的事实基线。**
>
> **旧 `docs/V3.1_GLOBAL_ARCHITECTURE_INVENTORY.md` 不再作为当前代码事实依据。**

但：

> **不要现在自行修改历史 Inventory。** 等 D-0 Closure 时统一修订 / 标记。

### 9.2 理由

`D0-045` 记录了 Inventory 的 10 项过时事实，包括但不限于：

- `ext_world.py` 的 `enqueue_event` 计数（6 → 实际 5，其中 1 处不可达）
- 「16 处调用全部静默失败」的判断（在 `ext_world` 路径上实为**中断 tick**）
- 后台线程数量（9/10 → 实际 11+）
- 未记载 `ai_life_policy` / `ai_vacation` / `ai_stay_put` / `app.routes` 改写 / `ext_mem.py` 缺陷 / 前端 World 回写

---

## 10. D-0 新的正式通过标准

D-0 必须**同时**达到以下 13 条，才可 Seal：

| # | 标准 | 本文件对应 |
|---|------|-----------|
| 1 | World Fact 定义明确 | D-0 Preflight §4 + D0-DEC-6 |
| 2 | `main.data` 仍然是唯一 World SOT | D0-DEC-6 / D0G-1 |
| 3 | 明确「唯一存储位置」与「事实治理」是两个概念 | **D0-DEC-6 / D0G-2** |
| 4 | Activity 的正式归属确定 | **D0-DEC-2 §3.1** |
| 5 | 18 个旧活动状态被定义为 Legacy State / Projection | **D0-DEC-2 §3.3** |
| 6 | `agent.Event` 被确定为正式 Domain Event | **D0-DEC-3 §4.1** |
| 7 | `enqueue_event` 不再被视为 Domain Event | **D0-DEC-3 §4.2** |
| 8 | SSE 不再被视为 Domain Event | **D0-DEC-3 §4.3** |
| 9 | Capability 与 `execute_action` 的迁移关系确定 | **D0-DEC-4** |
| 10 | Memory 不进入 D 阶段核心链 | **D0-DEC-1** |
| 11 | World Tick 可靠性问题被登记为 D-3 前置 Blocker | **D0-DEC-5** |
| 12 | A/B/C Contract 不需要重写 | §0.3 + D-0 Audit `D0-044` |
| 13 | D-1 不需要 DS 自己猜架构 | 本文件 + Contract Change 后 |

---

## 11. D-0 Seal 条件

只有以下四项全部完成，D-0 才 Seal：

```text
docs/D0_CONFLICT_AUDIT.md              ✅ 已完成（ACCEPTED）
        +
docs/D0_ARCHITECTURE_DECISIONS.md      ← 本文件
        +
docs/V3.1_ARCHITECTURE_CONTRACT.md     ← Contract Change
        +
docs/test_d0_world_activity_capability.py   ← D-0 Architecture Tests
```

> 在四者完成并经架构审核前，**D-0 不得 Seal，D-1 不得开始**。

---

## 12. 职责边界：D 阶段各子阶段"谁负责什么"

| 阶段 | 负责内容 | 明确不做 |
|------|---------|---------|
| **D-0** | World Fact 定义、SOT 治理原则、Activity 归属、Event 权威、Capability 迁移关系、Legacy 分层、Boundary Tests | 不实现任何功能 |
| **D-1** | **World Query**：只读统一入口（"我在哪里？这是什么地方？谁在这里？现在几点？这里有什么？我正在做什么？"） | 不调用 LLM、不做 Decision、不修改 World |
| **D-2** | **Activity**：data model / lifecycle / ownership / SOT / persistence / restart semantics / legacy mapping | 不改 AC-2 / AC-3 保护字段 |
| **D-3** | **Movement Continuity**：Goal + Commitment + Activity + Decision → Movement Capability → Location Change → Event | 修 World Tick 仅做最小可靠性修复 |
| **D-4** | **Capability**：Capability Port / Request / Result；`execute_action` 作为 Legacy Execution Adapter | 不删除 `execute_action` |
| **D-5** | **Agent Decision → Capability**：Intent → Decision → Capability Request → Capability → Action | 这是"AI 真正开始用新架构做事"的节点 |
| **D-6** | **Legacy Migration**：ext_ai / ext_world / ext_date / ext_sms / ext_shop / ext_econ 的旧行为逐项迁移 | 不一次性重写 |

---

## 13. D-0 当前状态

```text
D0 Audit
       ✅ ACCEPTED

D0 Architecture Decisions
       ✅ 本文件

Contract Change
       ⏳ 进行中

D0 Architecture Tests
       ⏳ 进行中

D0 Seal
       ⏸ 等待以上完成

D-1 World Query
       ⛔ 暂未开始
```

---

## 14. 本阶段仍然绝对不做的事

再次固化，防止越界：

```text
❌ 不要 D-1
❌ 不要 Activity implementation
❌ 不要 Capability implementation
❌ 不要 Memory（修复 / 启用 / 接入）
❌ 不要 VoiceStudio
❌ 不要前端重构
❌ 不要重写 ext_ai
❌ 不要重写 ext_world
❌ 不要删除 execute_action
❌ 不要建立新的 Event Bus
❌ 不要创建第二个 World
❌ 不要创建第二套 Activity SOT
❌ 不要修改 A/B/C 已冻结 Contract
❌ 不要修改任何生产代码
```

---

## 15. 一句话总结

> 这次 D-0 Audit 真正证明的是：
> **问题不是「缺少更多 AI 功能」，而是旧系统里已经存在太多地方可以偷偷决定 AI 的行为。**

D 阶段要做的不是让旧系统全部消失，而是：

> **逐渐让「谁有资格决定什么」变得清楚。**

---

**End of D0_ARCHITECTURE_DECISIONS.md**
