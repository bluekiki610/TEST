# B6 PRE-FLIGHT REVIEW — THINK / Decision 架构预检（修订版）

> 本阶段只做架构预检 / 设计文档。
> **未修改任何 `.py`、前端、数据、Memory、Provider、Assembler、Runtime、main、ext_\*、Contract。**
> 完成后停止，等待架构审核。

---

## 修订记录

| 版本 | 日期 | 修订点 |
|------|------|--------|
| v1 | 2026-09-27 | B6 初版 |
| v2 | 2026-09-27 | 修订 4 点：① 明确 `think() -> Optional[str]` 是 B5 临时占位；② 修正 Goal / Motivation / Intent / Decision / Action 定义；③ 明确 World Query 为无副作用信息查询；④ Goal 持久化位置暂不冻结 |

---

## 1. 当前基线

### 1.1 已封板阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| B1 | Context Data Contract | ✅ ACCEPTED |
| B2 | Context Providers | ✅ ACCEPTED |
| B3 | ContextAssembler | ✅ ACCEPTED |
| B4 | Runtime Connection Preflight | ✅ ACCEPTED |
| B5-0 | Context Contract Decision | ✅ ACCEPTED |
| B5-1 | Contract Change (CC-20260926-01) | ✅ ACCEPTED |
| B5-2 | Runtime Connection | ✅ ACCEPTED |
| B5-3 | Runtime Context Connection Tests | ✅ ACCEPTED |
| B5-4 | PROJECT Update | ✅ ACCEPTED |

### 1.2 当前封板 Commit

- B5-4 PROJECT commit：`a97293d7a312463748cb52029246fb27989e9873`

### 1.3 当前正式 Runtime Context 链

```text
Event
  ↓
RECEIVE
  ↓
PERCEIVE
  ↓
WAKE_DECISION
  ↓
build_context(event, now_ts=None)
  ↓
ContextAssembler.assemble(...)
  ↓
AgentContext
  ↓
think(context: AgentContext)   # 当前为 B5 临时占位，见 §2.5
```

### 1.4 当前仍保持的边界

- `LongTermProvider` = stub，返回 `[]`。
- Memory Runtime 未启用。
- `decision_constraints` = `None`。
- `think()` 仍为占位实现（返回 `None`）。
- 未接 LLM / Decision / Action。
- `ext_ai.build_ai_context()` 未接入 V3.1 正式链。
- 未产生"双 Context"。
- `ContextLayers` 为 deprecated compatibility stub。

**B1～B5 已经完成，B6 不回头修改。**

---

## 2. THINK 定义

### 2.1 为什么不能把所有概念塞进 `think()`

`think()` 如果同时承担：

- Event 解读
- State 判断
- Memory 检索
- Commitment 检查
- Goal 生成
- Motivation 计算
- Intent 形成
- Decision 选择
- Action 执行

就会变成一个新的“超级 `ext_ai`”，违反 V3.1 架构原则：

> World 负责事实和执行，Agent 负责动机与决策。

### 2.2 概念分层（正式定义 · 修订版）

| 概念 | 定义（修订版） | 时态 | 属于哪一层 |
|------|----------------|------|-----------|
| **Event** | 世界刚刚发生了什么（Fact） | 过去 | World → Agent 输入 |
| **State** | 现在是什么状态（Agent + World 投影） | 现在 | Projection |
| **Memory** | 记得什么（Experience 的编码 / 唤醒） | 跨时 | 按需检索 |
| **Commitment** | 已经答应 / 约定 / 承诺什么 | 未来 | Agent 承诺 |
| **Goal** | **我想完成什么** | 未来 | Agent 目标 |
| **Motivation** | **我为什么现在想完成它** | 现在 | Agent 动机 |
| **Intent** | **我现在倾向做什么** | 现在 → 未来 | Agent 意图 |
| **Decision** | **我最终选择做什么** | 现在 | Agent 决策 |
| **Action** | **系统真正执行什么** | 现在 | 执行层 |

### 2.3 关系图

```text
Event ──────────────┐
State ──────────────┤
Memory ─────────────┤
Commitment ─────────┼──→ Motivation ──→ Intent ──→ Decision ──→ Action
Goal ───────────────┤
World Conditions ───┘
```

### 2.4 THINK 在其中的位置

**THINK = Motivation → Intent（候选意图形成）阶段。**

- 输入：AgentContext（+ 未来可能的 Commitment / Goal）
- 输出：**Intent / candidate intention（候选意图）**
- **不产出 Decision**（Decision 是下一层）
- **不产出 Action**（Action 是再下一层）

THINK 的产物是：

> “我现在倾向做什么” + “为什么倾向这样做”

而不是“我决定了做什么”。

### 2.5 `think(context) -> Optional[str]` 的真实地位（修订点 ①）

**必须明确：**

> `think(context: AgentContext) -> Optional[str]` 是 **B5 阶段的临时占位 / 兼容接口**，
> **不代表最终 Intent 数据结构已经冻结。**

理由：

1. B5 阶段只完成 Runtime Context Connection，THINK 只更新签名以匹配 `AgentContext`。
2. B5 阶段 `think()` 行为仍为 Stub（返回 `None`）。
3. `Optional[str]` 是 P0-3A 遗留占位类型，**不足以代表结构化 Intent**。

**B6 已定义 Intent 为：**

- 结构化；
- 可审计；
- 可能包含多个候选；
- 携带 Motivation 摘要；
- 不产生副作用。

**因此：**

- `Optional[str]` **不足以**表达最终 Intent Contract。
- **最终 Intent 数据结构留待后续 Contract Change 冻结。**
- 本阶段**不修改** `think()` 签名，**不创建** Intent 数据结构。

### 2.6 THINK 不是 LLM 的同义词

- THINK 可以是 LLM 驱动，也可以是非 LLM 驱动。
- THINK 必须是可审计、可替换的层。
- B6 不实现 THINK，只冻结其输入 / 输出 / 边界。

---

## 3. Context → THINK 边界

### 3.1 THINK 的输入类型

**当前（B5 冻结）：**

```python
def think(self, context: AgentContext) -> Optional[str]:
    ...
```

**注意：** 该签名是 B5 临时占位，见 §2.5。最终签名留待 Intent Contract 冻结。

### 3.2 是否应扩展为 `think(context, event, state, ...)`

**B6 结论：不扩展。**

理由：

1. `AgentContext` 已经是分层结构化对象。
2. Event / State / Memory / Commitment / Goal 未来应通过 Context 层表达，而不是绕过 Context 让 THINK 直读。
3. 若让 THINK 直接读取 `main.data`，会：
   - 破坏 CA-2（不修改旧 `build_ai_context`）；
   - 破坏 SOT-1（`main.data` 是唯一 Source of Truth，但只允许通过 Contract 方法访问）；
   - 破坏“单一 Context 数据链”（CA-6）。

### 3.3 Event 如何进入 THINK

- `build_context(event, now_ts=None)` 已经接受 Event。
- B6 阶段 Event 在 ContextAssembler 内部**尚未被消费**。
- 未来可以：
  - 由 `RecentProvider` 读取由 Event 派生的近期事实；
  - 或由未来 `EventLayer` 将 Event 摘要注入 `Recent` 层；
  - 但**不允许** THINK 直接读取 Event 对象。

### 3.4 State 如何进入 THINK

- State 通过 `AgentState` 投影。
- `AgentState` 通过 `DynamicWorldProvider` 注入 `dynamic_world` 层。
- 未来若有更多 state 字段，应先在 Contract 中声明，再由 Provider 提供。

### 3.5 硬边界

- THINK 不允许 `import main`。
- THINK 不允许 `import ext_*`。
- THINK 不允许直接读取 `main.data`。
- THINK 不允许直接读取 `AgentState` 对象。
- THINK 不允许调用 `ext_ai.build_ai_context`。
- THINK 不允许写 `main.data`。
- THINK 不允许触发 Action。

---

## 4. Context 是否已经足够支持 THINK

### 4.1 Stable Core

**当前内容：**

- `identity`（AI 名 + owner 名）
- `world_lore`
- `persona`
- `user_profile`

**对 THINK 是否足够：**

| THINK 需要 | Stable Core 是否提供 | 说明 |
|-----------|---------------------|------|
| AI identity | ✅ | `identity` item |
| AI persona | ✅ | `persona` item |
| User profile | ✅ | `user_profile` item |
| World lore | ✅ | `world_lore` item |
| 核心关系 | ⚠️ 部分 | 依赖 `user_profile` 中的文本 |
| 长期关系快照 | ❌ | 属于 Long-term 或未来 Relationship 层 |

**结论：**

- Stable Core 已能表达 THINK 所需的基本“我是谁 / 我面对谁 / 世界观”。
- **不扩展** Stable Core。

### 4.2 Recent

**当前内容：**

- `recent_timeline`（≤ 5 条）
- `recent_trail`（≤ 5 条 + 24h 窗口）
- `recent_visited_place`（≤ 3 个）

**对 THINK 是否足够：**

| THINK 需要 | Recent 是否提供 | 说明 |
|-----------|----------------|------|
| 最近事件 | ✅ | `recent_timeline` |
| 最近活动 | ✅ | `recent_trail` |
| 最近地点变化 | ✅ | `recent_visited_place` |
| 最近社交行为 | ⚠️ 部分 | 依赖 trail / timeline 文本 |
| 当前对话 | ❌ | 属于旧 `build_ai_context` |

**结论：**

- Recent 已足够表达“最近发生了什么”。
- **不扩展** Recent。

### 4.3 Long-term

**当前状态：**

- `LongTermProvider` = stub，返回 `[]`。

**对 THINK 是否足够：**

| THINK 需要 | Long-term 是否提供 | 说明 |
|-----------|-------------------|------|
| Memory Recall | ❌ | Memory Runtime 未启用 |
| Relationship 历史 | ❌ | 未实现 |
| 历史事件 | ❌ | 未实现 |
| 重要承诺 | ❌ | 属于 Commitment 层 |

**结论：**

- **没有 Long-term Recall 时，THINK 第一阶段能做到：**
  - 基于 Stable Core + Recent + Dynamic World 做出**短时、局部、无历史依赖**的 Intent 候选。
  - 能处理“现在”和“刚才”，不能处理“上次”“很久以前”。

- **不能做到：**
  - 无法做“跨会话关系延续”。
  - 无法做“长期承诺的兑现”。
  - 无法做“记忆唤醒”。

- **禁止：**
  - 不允许为了让 THINK 看起来完整而偷偷激活 Memory。
  - 不允许用 `ai_timeline` / `trails` / `ai_visited` 冒充 Long-term。
  - 不允许把 `messages` / `sms` 当作 Long-term。

### 4.4 Dynamic World

**当前内容：**

- `current_time`
- `current_location`
- `current_activity`
- `is_working` / `is_dating` / `is_following`

**未来 Goal / Motivation / Intent 还需要什么（仅分析）：**

| 需要 | 当前是否提供 | 归属层 |
|------|-------------|--------|
| 当前时间 | ✅ | Dynamic World |
| 当前地点 | ✅ | Dynamic World |
| 当前活动 | ✅ | Dynamic World |
| 是否工作 | ✅ | Dynamic World |
| 是否约会 | ✅ | Dynamic World |
| 是否跟随 | ✅ | Dynamic World |
| 世界开放状态 | ❌ | World Query（Phase D） |
| 附近可用地点 | ❌ | World Query（Phase D） |
| 其他 AI 当前位置 | ❌ | 未来 World Snapshot |
| 天气 / 环境 | ❌ | 未来 World State |
| 经济状况 | ⚠️ | AgentState.wallet 已存在，未注入 Context |

**结论：**

- Dynamic World 当前覆盖 THINK 第一阶段的“现在”。
- 未来的世界查询必须走 **World Query**，不允许 Provider 自行扩展地图 / 建筑字段。

### 4.5 decision_constraints

**当前状态：**

- 保持 `None`。

**结论：**

- THINK 第一阶段**不依赖** `decision_constraints`。
- 未来由 Phase C（Goal / Motivation / Commitment）填充，但必须走 Contract 变更。
- B6 不实现。

---

## 5. Context 与 Decision 的边界

### 5.1 现状

`AgentContext` 是**信息**，不是**决策**。

### 5.2 禁止

不允许把：

- Intent
- Decision
- Action

塞进 `AgentContext` 作为状态字段。

### 5.3 未来正式结构

```text
AgentContext
    ↓
THINK
    ↓
Intent / candidate intention
    ↓
Decision
    ↓
Action
```

**而不是：**

```text
AgentContext
    ↓
THINK
    ↓
直接执行 Action
```

### 5.4 每层的可写性

| 层 | 可写性 |
|----|-------|
| AgentContext | 只读（THINK 输入） |
| Intent | THINK 输出，临时 |
| Decision | Decision 层输出，临时 |
| Action | Action 层执行 |
| main.data | 只有 Action → ext_* 可修改 |

---

## 6. Goal

### 6.1 定义（修订点 ②）

> **Goal = 我想完成什么。**

### 6.2 状态

- 未实现。
- B6 只定义位置与边界。

### 6.3 未来位置

```text
Time / State / Relationship / Recent Experience
        +
Commitment
        +
Goal
        +
World Conditions
        ↓
Motivation
```

### 6.4 职责

- Goal 回答“我想完成什么”。
- Goal 不回答“我现在做什么”。
- Goal 不回答“为什么是现在”。

### 6.5 来源（未来）

- 从 Relationship 推导。
- 从 Memory 推导。
- 从 Commitment 推导。
- **不允许凭空生成。**
- **不允许随机生成。**

### 6.6 持久性（修订点 ④）

**要求：**

- Goal **必须能够跨 Event 持续存在**。
- Goal 不因单个 Event 结束而消失。

**暂不冻结：**

- **Goal 的最终持久化位置暂不冻结。**
- 不现在确定独立数据库。
- 不现在确定是否复用 `main.data`。
- 不现在确定是否新建持久化文件。
- **最终持久化位置留待后续 Contract 决定。**

**明确禁止（本阶段）：**

- 不创建 Goal 持久化文件。
- 不创建 Goal 独立数据库。
- 不把 Goal 写入 `main.data`（SOT-1 / AS-5 仍生效）。

### 6.7 B6 禁止

- 不实现 Goal。
- 不修改 `_plan_auto`。
- 不引入随机目标。
- 不创建 Goal 持久化文件 / 数据库。

---

## 7. Motivation

### 7.1 定义（修订点 ②）

> **Motivation = 我为什么现在想完成它。**

### 7.2 状态

- 未实现。
- B6 只定义位置与边界。

### 7.3 未来位置

```text
Goal
Commitment
State
Relationship
Recent Experience
World Conditions
        ↓
Motivation
        ↓
Intent
```

### 7.4 职责

- Motivation 回答“我为什么现在想完成它”。
- Motivation 不回答“具体做什么”。
- Motivation 是 Intent 的输入。

### 7.5 随机性

- Motivation 的**核心因果**不允许随机。
- 随机性只允许出现在：
  - 非关键生活细节；
  - 候选生成；
  - 记忆偶发唤醒。

### 7.6 B6 禁止

- 不实现 Motivation。
- 不替代当前 `_plan_auto` 的随机概率。
- 不用随机概率解释核心关系 / 承诺。

---

## 8. Commitment

### 8.1 定义

AI 已经答应 / 约定 / 承诺什么。

### 8.2 状态

- 未实现。
- B6 只定义位置与边界。

### 8.3 未来位置

```text
Commitment ──→ Motivation
Commitment ──→ Intent
Commitment ──→ Decision（作为约束）
```

### 8.4 职责

- Commitment 回答“我已经答应什么”。
- Commitment 是 Decision 的**强约束**。
- Commitment 不能被随机性覆盖。

### 8.5 解决的关键问题

> “AI 为什么现在应该去那里？”

### 8.6 与现有状态的关系

**不得修改：**

- `date_invites`
- `date_invites_out`
- `ai_meeting`
- 现有 date / meeting 状态机

未来 Commitment 从这些状态中**读取**，不反向写入。

### 8.7 B6 禁止

- 不实现 Commitment。
- 不修改现有 date / meeting 状态机。

---

## 9. Intent

### 9.1 定义（修订点 ②）

> **Intent = 我现在倾向做什么。**

### 9.2 状态

- 未实现。
- 最终 Intent 数据结构留待后续 Contract Change 冻结。
- B5 阶段的 `think() -> Optional[str]` 不足以代表最终 Intent Contract（见 §2.5）。

### 9.3 未来位置

```text
Motivation
    ↓
Intent / candidate intention
    ↓
Decision
```

### 9.4 职责

- Intent 回答“我现在倾向做什么”。
- Intent 可以有多个候选。
- Intent 不是 Decision。
- Intent 不产生副作用。

### 9.5 与 THINK 的关系

**THINK 的输出就是 Intent。**

- THINK 可以产生一个或多个候选 Intent。
- THINK 不选择最终 Intent（那是 Decision）。
- THINK 不执行 Intent。

### 9.6 可审计性

- Intent 必须携带“为什么”（Motivation 摘要）。
- Intent 必须可被审计。
- Intent 不得包含 LLM 原始输出作为唯一依据。

### 9.7 B6 禁止

- 不实现 Intent。
- 不冻结最终 Intent 数据结构。
- 不让 THINK 直接产出 Decision。

---

## 10. Decision

### 10.1 定义（修订点 ②）

> **Decision = 我最终选择做什么。**

### 10.2 状态

- 未实现。
- B6 只定义位置与边界。

### 10.3 未来位置

```text
Intent / candidate intention
    ↓
Decision
    ↓
Action
```

### 10.4 职责

- Decision 回答“我最终选择做什么”。
- Decision 是**唯一**能影响 Action 的 Agent 输出。
- Decision 不直接修改 `main.data`。

### 10.5 约束

- Decision 必须遵守 Commitment。
- Decision 必须遵守世界规则。
- Decision 必须可审计。

### 10.6 B6 禁止

- 不实现 Decision。
- 不让 Decision 直接调用 ext_*。
- 不让 Decision 修改 `main.data`。

---

## 11. Action

### 11.1 定义（修订点 ②）

> **Action = 系统真正执行什么。**

### 11.2 状态

- 未实现。
- B6 只定义位置与边界。

### 11.3 未来位置

```text
Decision
    ↓
Action
    ↓
existing ext_*
    ↓
World Change
    ↓
Event
```

### 11.4 职责

- Action 只执行，不解释动机。
- Action 调用**现有** `ext_*` 能力。
- Action 是唯一能修改 `main.data` 的 Agent 链环节。

### 11.5 与现有 `ext_ai.execute_action` 的关系

- **不修改** `ext_ai.execute_action`。
- 未来迁移时必须“旧功能不能坏”。
- 迁移必须分阶段。
- Action 与 Decision 分离（不在 Action 中做决策）。

### 11.6 B6 禁止

- 不实现 Action。
- 不修改 `ext_ai.execute_action`。
- 不建立第二套业务执行系统。

---

## 12. Activity

### 12.1 定义

```text
PLANNED → TRAVELING → ARRIVED → ACTIVE → PAUSED → COMPLETED / CANCELLED
```

### 12.2 状态

- 未实现。
- B6 只定义位置与边界。

### 12.3 未来位置

```text
Decision
    ↓
Action
    ↓
Activity Lifecycle
    ↓
World Change
```

### 12.4 职责

- Activity 表达“正在进行的、有连续性的活动”。
- Activity 具有：
  - `activity_id`
  - `type`
  - `actor`
  - `participants`
  - `place`
  - `started_at`
  - `expected_end_at`
  - `status`
  - `reason`
  - `linked_commitments`

### 12.5 与现有状态的关系

**不得修改：**

- `work_sessions`
- `dates`
- `ai_shop_state`
- `instances`

未来 Activity 从这些状态中**读取 / 兼容**。

### 12.6 B6 禁止

- 不实现 Activity Lifecycle。
- 不修改现有 date / world / shop / instance 的状态字段。

---

## 13. World Query（修订点 ③）

### 13.1 定义（修订）

> **World Query 是**无副作用的信息查询能力**，不是决策层。**

例如：

```python
query_places(purpose="medical", urgency="high", open_now=True)
```

### 13.2 状态

- 未实现。
- B6 只定义位置与边界。

### 13.3 正式链路（修订）

**推荐链：**

```text
Motivation
    ↓
Intent
    ↓
World Query
    ↓
Query Result
    ↓
Decision
    ↓
Action
```

**说明：**

- World Query 可以被 **THINK / Decision 阶段调用**。
- World Query 可以出现在 Intent 形成后、Decision 前的信息查询环节。
- World Query **不能自己决定最终行为**。
- World Query **不能修改 `main.data`**。
- World Query **不能触发 Action**。

### 13.4 职责

- 回答“世界中有哪些可用的地点 / 建筑 / 房间”。
- 回答“是否开放 / 是否可进入”。
- 不修改 `main.data`。
- 不触发 Action。
- 不产生副作用。
- 不产生 Decision。

### 13.5 与现有数据结构的关系

**基于现有：**

- `buildings`
- `rooms`
- `npcs`

**不引入：**

- 新索引
- 新 schema
- 第二套 World

### 13.6 医疗案例中的位置（修订）

- “找到医院”是 **World Query 的信息查询**，不是 Decision，不是 Action。
- “陪用户去医院”是 **Intent → Decision → Activity**，不是 World Query。

### 13.7 B6 禁止

- 不实现 World Query。
- 不修改 `find_building_of_room` / `resolve_building` / `can_access_room`。
- 不修改 `buildings` / `rooms` / `npcs` schema。

---

## 14. Memory

### 14.1 定义

```text
Experience
→ Emotional Encoding
→ Association
→ Dormant Memory
→ Cue
→ Recall
```

### 14.2 状态

- Memory Runtime 未启用。
- `ext_memory` 未修复。
- `LongTermProvider` = stub，返回 `[]`。

### 14.3 B6 立场

**不允许因为 B6 而启用 Memory Runtime。**

### 14.4 未来位置

```text
Memory Runtime
    ↓
Recall
    ↓
LongTermProvider
    ↓
ContextAssembler
    ↓
AgentContext
    ↓
THINK
```

### 14.5 关键原则

- Memory ≠ Chat History。
- Recall 不是搜索，是“被想起”（Cue-driven）。
- 普通聊天 Recall 0 是常态。
- 特殊情境 Recall 1-2。
- 真正重要：少量高价值记忆。

### 14.6 B6 禁止

- 不修复 `ext_memory`。
- 不启用 Memory Runtime。
- 不实现 Recall。
- 不实现 Memory Encoding。
- 不创建第二套 Memory DB。
- 不创建持久化文件。

---

## 15. Communication

### 15.1 定义

```text
Chat / SMS / Group Chat / SNS / Comment / Notification
Date Invitation / AI↔AI
```

### 15.2 状态

- 现有 `ext_sms` / `ext_ai` / `ext_notes` 保持。
- SNS 本阶段不实现。
- AI↔AI autonomous loop 本阶段不实现。

### 15.3 未来位置

```text
Brain / Decision
    ↓
决定：是否沟通 / 对象 / 原因 / 渠道 / 时机
    ↓
Action
    ↓
底层插件执行（ext_sms / ext_ai / ext_notes / ext_core）
```

### 15.4 B6 禁止

- 不实现 SNS。
- 不实现 AI↔AI autonomous loop。
- 不修改现有 `ext_sms` / `ext_ai.wake_ais_for_room` / `ext_ai._group_talk`。

---

## 16. Scheduler

### 16.1 定义

统一调度，替代散落的 `threading.Timer` 和后台循环。

### 16.2 状态

- 未实现。
- 现有 10 个常驻后台循环保持不变。

### 16.3 未来位置

```text
Scheduler
    ↓
什么时候提醒 / 唤醒
    ↓
Brain / THINK
    ↓
醒来以后为什么做什么
    ↓
Decision
    ↓
Action
```

### 16.4 职责

- Scheduler 回答“什么时候”。
- Scheduler **不回答**“为什么 / 做什么”。
- Scheduler 不能代替 Brain 做行为决策。

### 16.5 迁移策略

- 只读观察 → 并行 → 切换。
- 不替代任何现有 `threading.Timer`。
- 不替代任何现有后台循环。
- 必须解决“重启丢失 Timer”问题（持久化）。

### 16.6 B6 禁止

- 不实现 Scheduler。
- 不替代 `auto_ai_loop` / `ai_spot_tick` / `work_tick` / `ai_shop_tick` / `date_tick` / `contact_tick`。

---

## 17. Randomness

### 17.1 当前旧系统随机机制

- `autonomous life random planning`
- `invite probability`
- `movement weighted random`

### 17.2 B6 结论

Randomness 只允许出现在**非关键细节 / 候选生成**层。

### 17.3 允许出现的位置

- 非关键生活细节（如“喝咖啡还是喝茶”）。
- 候选生成（提供多个候选给 Decision）。
- 记忆偶发唤醒。
- 不影响核心关系 / 承诺的选择。

### 17.4 禁止出现的位置

- Goal 生成。
- Motivation 核心因果。
- Commitment 覆盖。
- Decision 最终选择。
- “AI 为什么现在做这件事情”的最终原因。

### 17.5 兼容策略

- **不删除**旧随机机制。
- `ext_ai` 等旧系统仍处于兼容阶段。
- 未来逐步过渡到 V3.1 决策层。

### 17.6 B6 禁止

- 不删除旧随机机制。
- 不引入新的随机决策层。

---

## 18. AI↔AI

### 18.1 正确链路

```text
AI A THINK
    ↓
Decision
    ↓
Action
    ↓
Event
    ↓
AI B RECEIVE
    ↓
PERCEIVE
    ↓
...
```

### 18.2 错误链路

```text
AI A Brain
    ↓
直接调用
    ↓
AI B Brain
```

### 18.3 原则

- AI↔AI 必须通过 **World / Event**。
- AI A 不允许直接调用 AI B 的 Brain。
- 一个 AI 一个 Runtime 实例。

### 18.4 状态

- 未实现。
- B6 只定义位置与边界。

### 18.5 B6 禁止

- 不实现 AI↔AI autonomous loop。
- 不实现 AI A → AI B 的直接 Brain 调用。
- 不修改 `ext_ai._group_talk`。

---

## 19. ext_ai 迁移边界

### 19.1 当前事实

- `ext_ai` 是当前 AI orchestration hub。
- 被 8+ 模块调用。
- 通过 `m.drive_ai` / `m.call_llm` / `m.set_ai_wake_hook` 挂载。

### 19.2 迁移原则

- **不重写** `ext_ai.py`。
- **不删除** `ext_ai.py`。
- 先迁移接口，后迁移实现。
- 迁移过程必须“旧功能不能坏”。
- 迁移必须分阶段。
- 未来 `ext_ai` 从“总控制器”退化为兼容 / 编排层。

### 19.3 B6 立场

- **不修改** `ext_ai.py`。
- **不重写** `ext_ai.py`。
- **不删除** `ext_ai.py`。
- **不**把所有旧 autonomous life 逻辑直接搬进 AgentRuntime。
- **不**在 B6 阶段接入 `build_ai_context` 到 V3.1 链。

### 19.4 未来迁移顺序（仅设计，不实施）

1. 只读观察：V3.1 Runtime 并行观察 `ext_ai` 行为，不接管。
2. 并行：V3.1 Runtime 与新逻辑并行运行，输出对照。
3. 切换：逐步让 V3.1 Runtime 接管行为，`ext_ai` 退化为兼容层。
4. 清理：在 Contract 变更通过后，逐步清理死代码。

---

## 20. Prompt Adapter

### 20.1 未来位置

```text
AgentContext
    ↓
Prompt Adapter
    ↓
LLM
    ↓
THINK result
```

### 20.2 职责

- Prompt Adapter 负责把结构化 `AgentContext` 序列化为 LLM 输入。
- Prompt Adapter 不产生决策。
- Prompt Adapter 不读取 `main.data`。
- Prompt Adapter 不修改 Context。

### 20.3 为什么 Prompt Adapter 不应直接读取 `main.data`

1. 破坏单一 Source of Truth 原则。
2. 会与 `ContextAssembler` 产生职责重叠。
3. 会形成“双 Context”（旧 `build_ai_context` + Prompt Adapter 直读）。
4. 会让预算控制失效。
5. 会让审计困难。

### 20.4 是否应该直接序列化 `AgentContext`

- 应该。
- 但需要注意：
  - 不把 `ContextSection` 元信息（如 `metadata`）注入 Prompt；
  - 不把 `decision_constraints` 在未实现时注入；
  - 不把 Provider 内部 source 标记注入（除非用于调试）。

### 20.5 B6 禁止

- 不创建 Prompt Adapter。
- 不调用 LLM。
- 不写 Prompt。

---

## 21. 医疗案例验证

### 21.1 场景

用户告诉 AI：“我受伤了。”

### 21.2 未来链路

```text
Event（用户消息）
    ↓
Perception
    ↓
Context（AgentContext）
    ↓
Motivation（用户受伤，AI 关心，需要帮助）
    ↓
Intent（倾向陪用户去医院）
    ↓
World Query（查询可用医院）
    ↓
Query Result
    ↓
Decision（选择某家医院 + 前往方式）
    ↓
Action（调用现有 ext_* 执行）
    ↓
World Change（AI 与用户位置变化）
    ↓
Event（location_changed）
```

### 21.3 关键问题回答（修订）

| 问题 | 回答 |
|------|------|
| World Query 属于 THINK、Decision 还是 Action？ | **无副作用信息查询能力**，可被 THINK / Decision 调用，不属于 Action |
| “找到医院”是 Decision 还是 Action？ | **World Query 的信息查询**，不是 Decision，不是 Action |
| “陪用户去医院”是 Intent、Decision 还是 Activity？ | **Intent → Decision → Activity（Lifecycle）→ Action** 多阶段 |
| 地图数据应怎样提供给 THINK？ | 通过 **World Query 接口**，不作为 Context 层直接注入 |

### 21.4 边界

- THINK 不直接读地图。
- Decision 不直接调用 ext_*。
- Action 不解释动机。
- 地图查询必须基于现有 `buildings` / `rooms`。
- World Query 不产生副作用。
- World Query 不修改 `main.data`。

---

## 22. 周末住所连续性案例验证

### 22.1 场景

AI 昨天和用户一起在某个住所度过周末。第二天早上，AI 不能莫名其妙跑到另一个地图。它应该知道自己为什么留在那里、接下来有什么安排。

### 22.2 各层职责

| 概念 | 职责 | 归属层 |
|------|------|--------|
| Event | “用户昨天邀请 AI 到住所” | Event |
| Memory | “和用户一起过周末” | Memory（未来） |
| Commitment | “AI 答应周末陪用户” | Commitment（未来） |
| Goal | “继续陪伴用户” | Goal（未来） |
| Motivation | “用户还在住所，且 AI 有意愿继续陪伴” | Motivation（未来） |
| Intent | “留在住所 / 准备早餐 / 提议出门” | Intent（未来） |
| Decision | “留在住所” | Decision（未来） |
| Action | “不移动 / 与用户互动” | Action（未来） |
| Activity | “ACTIVE（陪伴用户）” | Activity（未来） |
| Location | “保持在同一住所” | World（现有 `ai_location`） |

### 22.3 关键结论

- **不能只说“放 Context”。**
- 每一层的职责必须明确：
  - Context 提供**信息**。
  - Memory 提供**经历**。
  - Commitment 提供**约束**。
  - Goal 提供**方向**。
  - Motivation 提供**原因**。
  - Intent 提供**倾向**。
  - Decision 提供**选择**。
  - Action 提供**执行**。
  - Activity 提供**连续性**。
  - Location 提供**世界事实**。

### 22.4 B6 阶段结论

- 当前 `LongTermProvider = Stub`，因此此案例在 B6 阶段**不能完整实现**。
- 这是**正确的**：不允许为了让案例看起来完整而提前启用 Memory / Commitment / Goal。

---

## 23. 完整架构图（修订）

```text
                         ┌──────────────────┐
                         │      Event       │
                         └────────┬─────────┘
                                  ↓
                         RECEIVE / PERCEIVE
                                  ↓
                          WAKE_DECISION
                                  ↓
                         Context Assembly
                                  ↓
                          AgentContext
                                  ↓
                              THINK
                                  ↓
                              Intent
                                  ↓
                  ┌───────────────┴───────────────┐
                  ↓                               ↓
            World Query                  candidate reasoning
                  ↓
            Query Result
                  ↓
              Decision
                  ↓
                Action
                  ↓
            existing ext_*
                  ↓
            World Change
                  ↓
                Event
```

### 23.1 各模块位置

| 模块 | 位置 |
|------|------|
| **Goal** | 在 THINK 之前，由 Relationship / Memory / Commitment 推导；持久化位置**暂不冻结** |
| **Motivation** | 在 THINK 内部，由 Goal + State + Relationship + Memory + World Conditions 推导 |
| **Commitment** | 在 THINK / Decision 之前，作为强约束 |
| **Intent** | THINK 输出；最终数据结构留待后续 Contract Change 冻结 |
| **World Query** | 在 Intent 与 Decision 之间，作为无副作用信息查询层 |
| **Activity** | 在 Action 之后，作为 World Change 的连续性表达 |
| **Memory** | 在 Context Assembly 之前（通过 Recall → LongTermProvider） |
| **Scheduler** | 在 RECEIVE 之前，作为“什么时候提醒 / 唤醒” |
| **Communication** | 在 Decision → Action 之间，通过现有 ext_* 执行 |

### 23.2 关键边界

```text
World       负责事实和执行
Agent       负责动机与决策
Event       是世界共同语言
Context     是 Agent 的信息视图
Intent      是 THINK 的输出，不是 Decision
World Query 是无副作用信息查询，不是决策层
Decision    是唯一能影响 Action 的 Agent 输出
Action      是唯一能修改 main.data 的链环节
```

---

## 24. B6 禁止事项

### 修改类

- ❌ 修改 `agent/runtime.py`
- ❌ 修改 `agent/context.py`
- ❌ 修改 `agent/context_assembler.py`
- ❌ 修改 `agent/state.py`
- ❌ 修改 `agent/event.py`
- ❌ 修改任何 Provider
- ❌ 修改 `main.py`
- ❌ 修改任何 `ext_*.py`
- ❌ 修改前端
- ❌ 修改 Memory
- ❌ 修改 `docs/V3.1_ARCHITECTURE_CONTRACT.md`

### 实现类

- ❌ 接 LLM
- ❌ 写 Prompt
- ❌ 实现 THINK
- ❌ 实现 Decision
- ❌ 实现 Action
- ❌ 实现 Brain
- ❌ 实现 Goal
- ❌ 实现 Motivation
- ❌ 实现 Commitment
- ❌ 实现 Intent
- ❌ 实现 Activity
- ❌ 实现 World Query
- ❌ 实现 Scheduler
- ❌ 实现 AI↔AI
- ❌ 激活 Memory Runtime
- ❌ 修改 `ext_ai.build_ai_context()`
- ❌ 修改 `main.data`
- ❌ 建立新的数据库
- ❌ 建立第二套 Agent State
- ❌ 创建 Goal 持久化文件 / 数据库

### 阶段纪律类

- ❌ 直接进入 B7
- ❌ 跳过架构审核
- ❌ 绕过 Contract Change 流程
- ❌ 删除 / 改名 / 别名化 `ContextLayers`
- ❌ 冻结最终 Intent 数据结构（本阶段）
- ❌ 冻结 Goal 持久化位置（本阶段）

---

## 25. 下一阶段建议

### 25.1 不建议直接进入 B7 编码

理由：

1. Phase C 的 Goal / Motivation / Commitment 语义尚未冻结。
2. THINK 的输入 / 输出契约尚未冻结。
3. Intent 数据结构尚未冻结。
4. Prompt Adapter 的设计尚未冻结。
5. Decision / Action 的接口尚未冻结。
6. Scheduler / World Query 的位置尚未冻结。
7. Goal 持久化位置尚未冻结。

### 25.2 建议的下一步

**Phase C Preflight → Contract Change → 编码。**

顺序：

1. **C-0 Preflight**：定义 Goal / Motivation / Commitment / Intent 的数据结构与边界。
2. **C-1 Contract Change**：更新 `docs/V3.1_ARCHITECTURE_CONTRACT.md`，包括：
   - Goal / Motivation / Commitment / Intent 语义；
   - Goal 持久化位置；
   - Intent 数据结构；
   - World Query 调用位置。
3. **C-2 实现**：只实现 Goal / Motivation / Commitment / Intent 的最小核心。
4. **C-3 测试**。
5. **C-4 PROJECT Update**。

### 25.3 不建议的顺序

- ❌ 先实现 THINK。
- ❌ 先接 LLM。
- ❌ 先实现 Decision。
- ❌ 先实现 Action。
- ❌ 先启用 Memory。

### 25.4 THINK 的最早可能时机

- THINK 实现必须在：
  - Goal / Motivation / Commitment 至少部分实现；
  - Intent 数据结构冻结；
  - Decision / Action 的接口契约冻结；
  - Prompt Adapter 契约冻结；
  - Contract Change 通过。

---

## 26. B6 完成确认

> **B6 只完成 THINK / Decision 架构预检（修订版）。**
>
> **未修改任何 `.py` 文件。**
> **未修改 `agent/runtime.py`。**
> **未修改 `agent/context.py`。**
> **未修改 `agent/context_assembler.py`。**
> **未修改 `agent/state.py` / `agent/event.py`。**
> **未修改任何 Provider。**
> **未修改 `main.py` / `ext_*.py`。**
> **未修改前端。**
> **未修改 Memory。**
> **未修改 `docs/V3.1_ARCHITECTURE_CONTRACT.md`。**
>
> **B6 没有实现 THINK / Decision / Action / Brain / Goal / Motivation / Commitment / Intent / Activity / World Query / Scheduler / AI↔AI。**
> **B6 没有接 LLM / 网络。**
> **B6 没有启用 Memory Runtime。**
> **B6 没有产生"双 Context"。**
> **B6 没有冻结 Intent 数据结构。**
> **B6 没有冻结 Goal 持久化位置。**
>
> **B6 只输出设计决策文档，不进入 B7 编码。**

---



---

**B6 修订版完成后停止，等待架构审核。不进入 B7。**
