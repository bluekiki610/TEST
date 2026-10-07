# V3.1 Phase D-2 Preflight

# Activity Contract

**Status:** PRE-FLIGHT
**Phase:** V3.1 Phase D-2
**Document Type:** Architecture Preflight / Decision Freeze Preparation
**Implementation Status:** **NO CODE IMPLEMENTATION AUTHORIZED**
**上游状态：** D-0 = **SEALED**；D-1 = **SEALED**（54 + 51 + 70 三项真实通过）
**Last Updated:** 2026-09-30

---

## 0. 文档目的与纪律

本文件是 V3.1 Phase D-2 的前置架构确认文件。

D-2 的核心问题只有一句话：

> **AI 正在做什么事情，而且这个事情为什么能够跨 Event 持续？**

即从：

```text
World Query  = 世界事实（现在是什么）
```

进入：

```text
Activity     = 持续世界过程（正在经历什么）
```

### 0.1 本阶段绝对禁止

```text
❌ agent/activity.py
❌ Activity Runtime
❌ Activity persistence
❌ scheduler
❌ Event integration
❌ Movement integration
❌ Capability integration
❌ ext_world.py migration
❌ ext_ai.py migration
```

同时继承 D-0 / D-1 的禁令：

```text
❌ 修改 AgentRuntime / Context / Goal / Commitment / Motivation / Intent
❌ 修 Memory
❌ 创建第二个 World SOT / 缓存 / 索引 / 数据库
❌ 修改前端 / HTTP API
❌ 进入 D-3
```

### 0.2 本文件的性质

本文件**只做设计冻结准备**，回答架构侧指定的 19 个问题。
**不写任何代码。** 完成后停止，等待架构审核。

---

## 1. 事实基线（以当前代码 + D-0 Audit 为准）

### 1.1 当前「活动」的真实存在形式

D-0 Audit `D0-026` 已确认：系统**没有任何名为 `Activity` 的对象**，但有 **18 类**实际承担「AI 当前正在做什么」的平行状态：

```text
dates[]                        ext_date      pending / coming / active / ended
date_invites[ai]               ext_date      无 status 字段（存在即 pending）
date_invites_out[ai]           ext_date      waiting / accepted / rejected
date_invite_out_<ai>           ext_date + ext_ai（双实现）
date_last_invite_ts[ai]        ext_date + ext_ai（双实现）
work_sessions[ai]              ext_econ      building_id / start_ts / hours / started_at
work_switch[ai]                ext_econ      bool
home_jobs[ai]                  ext_econ      建筑显示名
ai_auto_work_mark[ai]          ext_ai        日期闩锁
ai_shop_state[ai]              ext_shop      last_ts / day / day_count / reply_day /
                                             pending_reply / active_gift_day / next_shop_ts
ai_follow[ai]                  ext_ai        owner / go_to / at_ts
ai_pending_moves[ai]           ext_ai / main room / at_ts
ai_meeting[ai]                 ext_ai        room / at_ts
ai_stay_put[ai]                ext_ai        bool
ai_vacation[ai]                ext_ai        bool
ai_life_policy[ai]             （无写入方）  失效门禁
ai_spot_state[ai]              ext_world     last_bid / last_ts / story_ts / story_day / story_count
instances[user][iid]           ext_instance  status / participants[]
＋ 10 项节律/调度键（story_rhythm / writing_rhythm / living_rhythm /
   ai_home_act_next / ai_auto_next / _last_think_invite / ai_drive_log /
   ai_last_human / ai_last_auto / ai_diary_log）
```

**5 套互不兼容的取值词汇，零 `PLANNED` / `TRAVELING` / `ARRIVED` / `PAUSED` / `CANCELLED`。**

### 1.2 「当前活动」已经被三处消费（重要）

| 消费方 | 位置 | 说明 |
|--------|------|------|
| `AgentState` | `agent/state.py:38 / 164 / 184` | `current_activity` 字段，由 `_derive_activity()` 推导；docstring 自述「P0-1 临时规则，不代表最终 Agent 行为模型」 |
| `DynamicWorldProvider` | `agent/dynamic_world_provider.py:155-158 / 200` | 从 `agent_state_dict["current_activity"]` 读取并注入 Context |
| **`Motivation`** | `agent/motivation.py:114` | 从 `agent_state_snapshot["current_activity"]` 读取 |

### 1.3 一条已冻结的硬约束（决定 D-2 的边界）

**Contract §5B.8「Motivation 最小输入集合（冻结）」：**

```text
goal
commitment
agent_state_snapshot（AgentState.to_dict()，只读，现有字段）
now_ts
```

**MO-17**：C-2 Motivation **不允许**消费 Relationship / Memory / Recent / **World Query**。

**推论（必须记录）：**

1. 当前 `motivation.py` 已经在读「活动」——**但只是通过 `agent_state_snapshot` 间接读**
2. 因此：**Activity 若要进入 Motivation，只能经由 `AgentState` 字段**，不能直接注入
3. 若要**新增** `AgentState` 字段（例如 `current_activity_id`），属于**扩展 §5B.8 的最小输入集合**，**必须走 Contract Change**
4. D-1 的 World Query **被 MO-17 明确禁止**作为 Motivation 输入 —— 因此
   **「Activity 经由 World Query 进入 Motivation」这条路径是被冻结规则堵死的**

### 1.4 D-0 已为 Activity 冻结的原则

| 规则 | 内容 |
|------|------|
| **AC-2 / AC-3** | D 阶段**不修改**现有 `work_sessions` / `dates` / `ai_shop_state` / `instances` 状态字段 |
| **AC-5** | Activity 是未来**唯一**正式的「持续世界过程」抽象 |
| **AC-6** | 现有 18 类旧活动字段 = **Legacy Activity State / Legacy Projection**（只登记，不修改） |
| **AC-7** | **禁止**多个 Activity 真相并存（`main.data.activity` + `ext_date` 一套 + `ext_shop` 一套 + …） |
| **AC-8** | Activity ≠ Goal；Activity ≠ Commitment；Activity ≠ Action（INVARIANT-4 / 5 / 6） |
| **AC-9** | Activity 的 data model / lifecycle / ownership / SOT / persistence / restart / legacy mapping **一律在 D-2 建立** |
| **AC-10** | AC-2 / AC-3 继续生效 |
| **D0G-4** | 禁止创建第二套 World / 第二套 Activity SOT / 第二套 Event Bus / 第二套 Memory DB |
| **D0G-2** | 「唯一存储位置」≠「事实治理」 |
| **SOT-10** | 任何新的持久化机制**不得**产生与 `main.data` 平行、同等权威的事实源；必须是**从属**的，或**可从 `main.data` 重建的只读投影** |
| **WQ-42 ～ WQ-46** | D-1 **不实现** Activity；`world_query` 只返回 **Legacy 推导值**且 `derived=True`；**禁止**返回可被误认为 Activity 生命周期字段 |
| **WT-1** | World Tick 可靠性缺陷是 **D-3 前置 Blocker**，D-2 不修 |
| **D0-DEC-2** | Activity 归属 D-2；D-2 必须给出「18 类旧字段 → Activity」的映射关系 |

### 1.5 D-0 Preflight 已给出的候选（D-2 的起点，非最终）

**生命周期（D-0 Preflight §12，候选冻结）：**

```text
PLANNED → TRAVELING → ARRIVED → ACTIVE ⇄ PAUSED → COMPLETED
CANCELLED（异常）
允许转换：PLANNED→CANCELLED / TRAVELING→CANCELLED / ACTIVE→PAUSED /
          ACTIVE→COMPLETED / PAUSED→ACTIVE / PAUSED→CANCELLED
不允许随意跳跃（例如 PLANNED → COMPLETED）
```

**最小结构（D-0 Preflight §13，候选）：**

```text
activity_id / type / actor_ids / participant_ids / location_id /
status / started_at / expected_end_at / goal_id / commitment_ids /
current_step / metadata
```

**SOT 方向（D-0 Preflight §15 / §16）：**

```text
World Activity → AgentRuntime 查询 → Frontend 查询 → Event / Presentation
Runtime 可以持有 current_activity_id（绑定引用或缓存）
但：Runtime 不是 Activity 的事实来源
```

---

## 2. 核心结构性张力（必须先摆在最前面）

D-2 面对一个**真实的、无法回避的张力**：

```text
┌──────────────────────────────────────────────────────────────┐
│ ① AC-9 要求 D-2 建立 Activity 的 ownership + SOT + 持久化      │
│ ② AC-2 / AC-3 禁止修改现有 18 类活动状态字段                  │
│ ③ D0G-4 / SOT-10 禁止产生与 main.data 平行、同等权威的事实源   │
│ ④ WO-65（已用于 D-1）「不新增 main.data 顶层 key」            │
│ ⑤ AC-7 禁止多个 Activity 真相并存                             │
└──────────────────────────────────────────────────────────────┘
```

**如果 D-2 同时执行 ① 与 ③：** Activity 无处可存。
**如果 D-2 把 Activity 写进 `main.data`：** 要么新增顶层 key（与 ④ 精神冲突，需要 Contract Change），要么写入现有 18 类字段（违反 AC-2 / AC-3）。
**如果 D-2 只做派生视图：** ① 的 ownership / persistence 未兑现。

> **这是 D-2 的中心问题，必须由架构侧裁决，不得由 DS 自行选择。**
> 见 **§20 D2-OPEN-1**。
>
> 本 Preflight 提出的**最小风险方案**是：
>
> ```text
> D-2 建立「正式的 Activity Domain Object」与「正式边界」，
> 但其 SOT / persistence 在 D-2 明确**不冻结**，
> Activity 在 D-2 是 Runtime-scoped（跨 Event 连续，跨重启不保证）。
> ```

---

## 3. 决策清单（19 项，逐条对应架构侧提问）

---

## D2-DEC-1 · Activity 的严格定义

**问题：** Activity 的严格定义是什么？

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| A | Activity = 「正在发生的动作」 | 与 Action 无法区分（违反 AC-8） |
| B | Activity = 「持续世界过程」（本 Preflight 建议） | 需要精确定义「持续」与「世界」 |
| C | Activity = 「Goal 的执行实例」 | 违反 AC-8（Activity ≠ Goal） |

### 建议：**B**

> **Activity = 世界之中一个具有身份、可持续、会结束的**过程**；
> 它描述「谁，正在经历什么」，而不是「谁想做什么」或「谁做了什么」。**

**定义的四个必要条件（缺一不可）：**

| # | 条件 | 反例 |
|---|------|------|
| **1** | **有身份**（identity）：同一个过程跨 Event 保持同一，可被引用 | 每次 tick 新生成的「状态字符串」没有身份 |
| **2** | **有持续**（duration）：其生命周期跨越多个 Event | 单次 `speak` 是 Action，不是 Activity |
| **3** | **有参与者**（participants）：至少一个 actor | 「城市在下雨」是 World Fact，不是 Activity |
| **4** | **会结束**（termination）：终态必须可达 | 「AI 活着」不是 Activity |

**明确定义上的排除：**

```text
❌ Activity ≠ Action（不表示「做了某件事」）
❌ Activity ≠ Goal（不表示「想完成什么」）
❌ Activity ≠ Commitment（不表示「答应过什么」）
❌ Activity ≠ Intent（不表示「倾向于做什么」）
❌ Activity ≠ World Fact（不表示「世界现在是什么」）
❌ Activity ≠ Scheduler Entry（不表示「计划在某个时刻做某事」）
❌ Activity ≠ Event（不表示「刚刚发生了什么」）
```

### 建议冻结

| 规则 | 内容 |
|------|------|
| **A-1** | **Activity = 世界之中具有身份、可持续、会结束的过程**；描述「谁正在经历什么」 |
| **A-2** | Activity 必须同时满足四个必要条件：**身份 / 持续 / 参与者 / 可终止** |
| **A-3** | Activity **不是** Action / Goal / Commitment / Intent / World Fact / Scheduler Entry / Event |
| **A-4** | Activity 的**唯一正式抽象地位**见 `AC-5`（未来唯一正式的「持续世界过程」抽象） |

---

## D2-DEC-2 · Activity 与 Goal / Commitment / Intent / Event 的边界

**问题：** 四者边界是什么？

### 建议：冻结五层语义分离

```text
World Fact   = 世界现在是什么            （已有：World Query / D-1）
Event        = 世界刚刚发生了什么        （已有：agent.Event / EV-9）
Activity     = 谁正在经历什么持续过程    （D-2 建立）
Goal         = 我想完成什么              （已有：C-2 / Runtime-only）
Commitment   = 我答应 / 承诺了什么        （已有：C-2 / Runtime-only）
Intent       = 我当前倾向于做什么        （已有：C-2 / Runtime-only）
Decision     = 最终选择什么              （未实现 / Phase F）
Action       = 实际执行                  （Legacy：execute_action）
```

### 边界规则

| 规则 | 内容 |
|------|------|
| **A-5** | Activity **不是** Event；Activity **可以产生** Event（生命周期转换 → Event），但该 Event 的权威定义属 **D-1 / D-5 Event Coverage**，D-2 **不实现** |
| **A-6** | Activity **可以引用** `goal_id` / `commitment_ids`，但**引用 ≠ 拥有**：Goal / Commitment 仍归 Runtime holder |
| **A-7** | Activity **不得**被用作 Goal 的存储，也**不得**被用作 Commitment 的存储（`AC-8` / `SOT-8`） |
| **A-8** | Activity **不得**由 Intent 直接创建（`IN-6`：Intent 不直接触发 Action / 副作用） |
| **A-9** | Event **不得**直接修改 Activity（`EV-3` / `EV-4`：Event 不修改数据、不触发行为）；Event 只能被感知，由 Agent 链决定是否影响 Activity |
| **A-10** | Activity **不得**承担 Goal / Commitment / Intent 的持久化职责 |

**必须回答的反向问题：**

> 「AI 想和玩家约会」→ Goal
> 「19:00 与主人在咖啡馆见面」→ Commitment
> 「19:00 起在咖啡馆与主人共处」→ **Activity（Date）**
> 三者**同时成立、互不替代**。

---

## D2-DEC-3 · Activity 是否是正式 Domain Object

**问题：** Activity 是否是正式 Domain Object？

### 建议：**是**

| 规则 | 内容 |
|------|------|
| **A-11** | Activity **是**正式 Domain Object（具有身份、类型、生命周期、参与者） |
| **A-12** | Activity **不是** `AgentRuntime` 的私有实现细节；`AgentRuntime` 至多持有 `current_activity_id` 这类**绑定引用**（D-0 Preflight §15） |
| **A-13** | Activity **不是** 纯函数 / 纯派生字符串；它必须能被**引用**（因此必须有稳定身份） |
| **A-14** | Activity **不得**被实现为一个「万能 `execute_action` 式分发器」（D-0 §53 禁止的模式） |

**注意与现有实现的冲突（必须记录）：**

当前 `AgentState.current_activity` 是一个**推导字符串**（`_derive_activity()`），
它**没有身份**、**不可引用**、**跨 Event 不可靠**。

→ 因此 **`AgentState.current_activity` 不是 Activity**，二者必须明确区分：

```text
AgentState.current_activity
    = Legacy 派生标签（DERIVED，无身份）
    ≠ Activity（Domain Object，有身份）
```

| 规则 | 内容 |
|------|------|
| **A-15** | `AgentState.current_activity` 与正式 Activity **不是同一事物**；前者是 Legacy 派生标签，后者是 Domain Object |
| **A-16** | D-2 **不得**把 `AgentState.current_activity` 直接改造成 Activity（那不是「建立 Domain Object」，而是「给字符串加壳」） |

---

## D2-DEC-4 · Activity 的 SOT

**问题：** Activity 的 SOT 是什么？

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| **A** | Activity 是 **Runtime-scoped Domain Object**；SOT 未冻结；跨 Event 有身份，跨重启不保证（**本 Preflight 建议用于 D-2**） | 重启丢失；AC-9 的 persistence 未兑现 |
| **B** | Activity 写入 `main.data` 新顶层 key（如 `activities`） | 需 Contract Change；接近 WL-65 禁令；但仍是 `main.data` 内，不构成第二 SOT |
| **C** | Activity 有独立持久化（文件 / 独立 JSON） | **直接违反 SOT-10 / D0G-4** —— **不可接受** |
| **D** | Activity 完全由 Legacy 字段派生（无独立身份） | 无法满足 A-1「有身份」；等于放弃 Activity |

### 建议：**A（D-2 阶段）**，并把 B / C / D 的裁决留给 **D2-OPEN-1**

**理由：**

1. **C 不可接受**：会产生与 `main.data` 平行、同等权威的事实源（违反 `SOT-10` / `D0G-4`）
2. **D 不可接受**：无身份 → 不满足 `A-1` / `A-13`，等于没建立 Activity
3. **B 需要 Contract Change**（新增 `main.data` 顶层 key），**且 AC-2 / AC-3 仍在保护现有字段** —— 但 B 在原则上是**唯一**能满足「持久化 + 单一 SOT」的路径
4. **A 是 D-2 的最小风险起点**：先建立**正确的 Domain Object 与边界**，把「存哪里」交给后续裁决

| 规则 | 内容 |
|------|------|
| **A-17** | **D-2 的 Activity 是 Runtime-scoped Domain Object**；SOT 的最终归属**在 D-2 不冻结** |
| **A-18** | D-2 **禁止**为 Activity 创建独立持久化（文件 / 独立 JSON / 数据库）—— 违反 `SOT-10` / `D0G-4` |
| **A-19** | D-2 **禁止**新增 `main.data` 顶层 key（若需要，属独立 Contract Change） |
| **A-20** | Activity 的最终 SOT 若落在 `main.data`，**必须**：① 从属于 `main.data` 的权威性；② 不构成平行事实源；③ 经 Contract Change 明确 |
| **A-21** | 在 SOT 未冻结期间，Activity **不得**被任何持久化机制隐式保存 |

> **⚠️ 这是 D-2 的中心开放问题**，见 §20 `D2-OPEN-1`。

---

## D2-DEC-5 · 是否持久化

**问题：** Activity 是否持久化？

### 建议：**D-2 不持久化**

| 规则 | 内容 |
|------|------|
| **A-22** | **D-2 的 Activity 不持久化**（不写文件、不写数据库、不写 `main.data`） |
| **A-23** | D-2 **不引入** Activity 的持久化机制（留给后续 Contract Change） |
| **A-24** | D-2 **禁止**「顺手持久化」：不得因为实现方便而落盘 |

**理由：**

- 持久化位置无法在不违反 `SOT-10` / `AC-2` / `AC-3` / `WL-65` 的前提下确定（见 §2）
- 先冻结**语义与边界**，再冻结**存储**，符合「先统一语义，再拆文件」（Contract §0）

---

## D2-DEC-6 · 重启后怎么办

**问题：** 重启后怎么办？

### 建议：**D-2 明确接受重启丢失，但必须可重建**

| 规则 | 内容 |
|------|------|
| **A-25** | D-2 明确：Activity **跨重启丢失**（与 C-2 Goal / Commitment 同一阶段限制） |
| **A-26** | 重启后，Legacy 活动状态（18 类）**仍然存在**（因为它们本就在 `main.data`） |
| **A-27** | 因此重启后 Activity **必须能从 Legacy 状态重建**；重建是**只读投影**，不得反向写入 Legacy 字段 |
| **A-28** | 重建后的 Activity **identity 不保证与重启前一致**（D-2 已知限制，必须记录） |
| **A-29** | D-2 **不得**为了让 identity 跨重启稳定而引入持久化（见 `A-22`） |

**必须诚实记录的限制：**

```text
D-2 的 Activity 连续性保证是「跨 Event」，
不是「跨重启」。

跨重启的 Activity 连续性 = 需要 SOT 冻结 = 后续阶段。
```

---

## D2-DEC-7 · Activity 生命周期

**问题：** Activity lifecycle 是什么？

### 建议：**继承 D-0 Preflight §12 的候选生命周期，并补齐转换合法性**

```text
PLANNED ——→ TRAVELING ——→ ARRIVED ——→ ACTIVE ⇄ PAUSED ——→ COMPLETED
   │             │                        │         │
   └─────────────┴────────────────────────┴─────────┴──────→ CANCELLED
```

**允许转换（冻结）：**

| From | To |
|------|-----|
| `PLANNED` | `TRAVELING` / `CANCELLED` |
| `TRAVELING` | `ARRIVED` / `CANCELLED` |
| `ARRIVED` | `ACTIVE` / `CANCELLED` |
| `ACTIVE` | `PAUSED` / `COMPLETED` / `CANCELLED` |
| `PAUSED` | `ACTIVE` / `CANCELLED` |
| `COMPLETED` | （终态） |
| `CANCELLED` | （终态） |

**禁止：**

```text
❌ PLANNED → COMPLETED（跳跃，无业务原因）
❌ PLANNED → ACTIVE（跳过 TRAVELING / ARRIVED，除非有明确 Contract 例外）
❌ COMPLETED → ACTIVE（终态不可逆）
❌ CANCELLED → ACTIVE（终态不可逆）
❌ ARRIVED → COMPLETED（跳过 ACTIVE）
```

| 规则 | 内容 |
|------|------|
| **A-30** | Activity 生命周期**继承** D-0 Preflight §12：`PLANNED → TRAVELING → ARRIVED → ACTIVE ⇄ PAUSED → COMPLETED`，异常终态 `CANCELLED` |
| **A-31** | 只允许 §D2-DEC-7 表中列出的转换；**禁止随意跳跃** |
| **A-32** | `COMPLETED` / `CANCELLED` 是**终态**，不可逆 |
| **A-33** | 状态转换必须**单向且可审计**（`LC-12` 精神） |
| **A-34** | 生命周期**变更必须产生 Event**（`A-5`），但 **D-2 不实现 Event 生产** |
| **A-35** | D-2 阶段 Activity 的状态机**只定义语义**，**不实现**转移执行（`scheduler` / Runtime 绑定均禁止） |
| **A-36** | Activity **不得**与 Scheduler 混同：Scheduler「到点触发」，Activity「描述正在经历的过程」 |

**注意：** 「谁在什么时候推动状态转换」属 **D-2 Contract 之后的实现问题**，
且依赖未冻结的 Decision / Capability —— D-2 **不解决**。

---

## D2-DEC-8 · Activity 与 World State 的关系

**问题：** Activity 与 World State 的关系是什么？

### 建议

| 规则 | 内容 |
|------|------|
| **A-37** | Activity **属于 World 概念域**（`AC-5` / D-0 Preflight §14），但**不等于** `main.data` 的存储结构 |
| **A-38** | Activity **必须与 World State 一致**：Activity 描述的 `location_id` / 参与者 / 时间必须能对应到 World Query 可查的事实 |
| **A-39** | Activity **不得**创造独立的 World 概念（例如自定义地点、自定义时间轴） |
| **A-40** | Activity **可以引用** World Query 的查询结果作为其事实依据，但**不得**在 Activity 内复制 World 事实（避免第二 SOT） |
| **A-41** | World State 变化 **不等于** Activity 变化：World 变化需经 Agent 感知链才可能影响 Activity（`A-9`） |
| **A-42** | Activity **不得**成为 World 事实的第二来源 |

---

## D2-DEC-9 · Activity 与 Location / Movement 的关系

**问题：** Activity 与 Location / Movement 的关系是什么？

### 事实

```text
当前移动事实：ai_location（15+ 处直写）/ ai_pending_moves / ai_follow / ai_meeting
当前移动驱动：ext_ai follow_watch（5s 轮询）、Timer、随机
D-0 D0-011 / D0-027：Movement Continuity 尚未建立
D-0 WT-1：World Tick 可靠性是 D-3 前置 Blocker
```

### 建议

| 规则 | 内容 |
|------|------|
| **A-43** | Activity **可以表达** `TRAVELING`（生命周期状态之一），但**不拥有** `ai_location` |
| **A-44** | Activity **不得**直接修改 `ai_location`（`A-42` / World Mutation 边界） |
| **A-45** | 位置变更的**权威实现属 D-3**（Movement Continuity）；D-2 **不实现** |
| **A-46** | D-2 **不得**把 `ai_location` 包装成 Activity 的字段（那会制造第二 SOT） |
| **A-47** | Activity 的 `location_id` 语义 = **「这个过程发生在哪里」**，不是「AI 的当前位置」；两者可以不同（例如 TRAVELING 时） |
| **A-48** | D-2 明确：**Activity ≠ Movement**；`Query ≠ Movement`（D-1 `WQ-90` ～ `WQ-93` 的一致延伸） |

---

## D2-DEC-10 · Activity 被 Event 打断后怎么办

**问题：** Activity 被 Event 打断后怎么办？

### 建议：**区分「打断」的四种语义，不得一律 CANCELLED**

| 语义 | 建议处理 | 说明 |
|------|---------|------|
| **中断可恢复**（如收到 SMS 后回来继续） | `ACTIVE → PAUSED → ACTIVE` | 过程仍在，只是暂时挂起 |
| **被更高优先级过程取代**（如紧急事件） | `ACTIVE → CANCELLED` + 新 Activity | 原过程终止，必须有原因 |
| **自然结束** | `ACTIVE → COMPLETED` | 正常终态 |
| **World 硬约束导致不可继续** | `ACTIVE → CANCELLED` | 世界条件不允许（例如地点消失） |

| 规则 | 内容 |
|------|------|
| **A-49** | Event **不得**直接修改 Activity 状态（`A-9`）；打断必须经 Agent 链判断 |
| **A-50** | 打断处理必须区分 **PAUSED（可恢复）** 与 **CANCELLED（终止）**，**禁止**一律取消 |
| **A-51** | `CANCELLED` **必须携带原因**（为什么终止），不得静默取消 |
| **A-52** | 打断后的恢复**不得**重新创建新 identity（恢复是 `PAUSED → ACTIVE`，不是新 Activity） |
| **A-53** | Activity 的打断与恢复**不得**由随机性决定（`A-72` / `INVARIANT-18`） |
| **A-54** | 「谁有权打断 Activity」属 **D-2 Contract 之后**的问题；D-2 只冻结**语义区分** |

**关于 `A-52` 与 `A-28` 的张力（必须记录）：**

`A-52` 要求恢复不换 identity，但 `A-28` 承认重启后 identity 不稳定。
两者**不冲突**：`A-52` 约束的是**同一进程内**的 Interruption，`A-28` 描述的是**跨重启**的限制。

---

## D2-DEC-11 · 一个 AI 能否同时存在多个 Activity

**问题：** 并发性如何？

### 建议：**允许「一个 primary + 多个 secondary（可并存）」，但 primary 唯一**

| 规则 | 内容 |
|------|------|
| **A-55** | 一个 AI **在任意时刻最多只有一个 `primary` Activity** |
| **A-56** | 一个 AI **可以同时存在多个 `secondary` Activity**（如「工作中」同时「挂机等待回复」） |
| **A-57** | `primary` 的唯一性是**语义约束**，不是存储约束；D-2 不实现「唯一性强制」 |
| **A-58** | 禁止同一 AI 存在两个 `primary` Activity（`AC-7` 在多 Activity 场景下的具体化） |
| **A-59** | D-2 **不实现** primary 选举 / 抢占 / 优先级算法（那需要 Decision，属 Phase F） |
| **A-60** | 一个 World 位置 / 一个房间内可以同时存在多个 Activity（不同参与者） |

**理由：** 真实角色人生中「一边工作一边等消息」是自然的；
但「同时进行两个约会」不是。因此需要 `primary` / `secondary` 的区分，而不是「只能有一个」。

---

## D2-DEC-12 · AI↔AI / AI↔User / NPC 活动如何表达

**问题：** 参与者模型是什么？

### 建议：统一用 `participants[]` + `role`，不为每种关系造新类型

| 规则 | 内容 |
|------|------|
| **A-61** | Activity 用**统一的** `actor_ids` + `participant_ids` 表达参与者；**禁止**为 AI↔AI / AI↔User 各造一套结构 |
| **A-62** | `role` 语义至少区分：`actor`（主体）/ `partner`（对等参与，如约会另一方）/ `participant`（协作参与，如牌局）/ `observer`（在场但未参与） |
| **A-63** | AI↔AI 活动与 AI↔User 活动**使用同一结构**，仅 `role` 与参与者类型不同 |
| **A-64** | **NPC 活动**在 D-2 **不建模**（`UNSUPPORTED`）：当前 schema 中 NPC 没有位置 / 状态（D-1 已确认），无法支撑 NPC 的持续过程 |
| **A-65** | NPC **可以作为 `participant` 出现在 AI 的 Activity 中**（只要该 Activity 的 actor 是 AI） |
| **A-66** | D-2 **禁止**为「纯 NPC 之间的活动」创造建模（那需要 NPC 状态，属未冻结范围） |
| **A-67** | 一个 Activity 的 `actor_ids` **必须至少包含一个主体**（AI 或 User），不得为空 |

> **`A-64` / `A-66` 必须作为 `UNSUPPORTED` 明确记录**（与 D-1 的 `WQ-110` 精神一致）：
> schema 不存在的事实，**不猜**。

---

## D2-DEC-13 · Activity 是否允许没有 Goal

**问题：** Activity 是否一定需要 Goal？

### 建议：**允许没有 Goal**

| 规则 | 内容 |
|------|------|
| **A-68** | Activity **允许** `goal_id` 为空 |
| **A-69** | `goal_id` 为空的 Activity **不得**被视为非法 |
| **A-70** | 若 Activity 引用 Goal，该引用是**弱引用**（Goal 消失不导致 Activity 非法） |
| **A-71** | 理由：角色的日常过程（吃饭、散步、发呆）**不需要 Goal**；强制要求 Goal 会把 Goal 变成 Activity 的存储 |

---

## D2-DEC-14 · Activity 是否一定对应 Commitment

**问题：** Activity 是否一定对应 Commitment？

### 建议：**不要求**

| 规则 | 内容 |
|------|------|
| **A-72** | Activity **不要求**对应 Commitment；`commitment_ids` 可以为空 |
| **A-73** | 由 Commitment 派生的 Activity **必须**引用该 Commitment（保证可审计） |
| **A-74** | Activity **不得**被用来替代 Commitment（`AC-8`） |
| **A-75** | Commitment 被取消 / 过期时，其关联 Activity **不自动终止**（语义由后续 Contract 决定）；D-2 只冻结「不得自动同步」这一禁止项 |

**理由：** 若 Activity 必须对应 Commitment，则「无承诺的日常」无法表达，
且会让 Activity 变成 Commitment 的影子存储。

---

## D2-DEC-15 · 谁可以创建 / 修改 / 取消 Activity

**问题：** 授权模型是什么？

### 建议：**分权 + 明确禁止前端的直接写入**

| 规则 | 内容 |
|------|------|
| **A-76** | Activity 的**创建**只能来自：① Agent 链（Intent → Decision，属后续阶段）；② 明确的 Programmatic API（由 Domain 层调用），**不接受**任意模块直接构造 |
| **A-77** | Activity 的**状态修改**只能通过**显式转换 API**（与 C-2 Goal 的 `transition_*` 精神一致） |
| **A-78** | **禁止**外部直接修改 Activity 内部字段（`A-77` 的具体化） |
| **A-79** | **Frontend 不得**直接创建 / 修改 / 取消 Activity（`INVARIANT-14`：Frontend 不拥有 World 真相） |
| **A-80** | **Legacy `ext_*` 模块不得**直接创建 / 修改 Activity（迁移属 D-6） |
| **A-81** | Activity **不得**由随机性驱动创建或终止（`A-53` / `INVARIANT-18`） |
| **A-82** | 用户通过 UI 发起的活动请求必须走 `User Command → Application / Input Port → Event / Decision`，**不得**直接写 Activity（D-0 §52） |
| **A-83** | 具体 Policy / 权限矩阵**不在 D-2 冻结**（需要 Capability / Policy，属 D-4） |

---

## D2-DEC-16 · Activity 与未来 Capability 的关系

**问题：** 与 Capability 的关系是什么？

### 建议

```text
Decision
    ↓
Capability Request（执行「做某件事」）
    ↓
Capability
    ↓
World Change
    ↓
可能 产生 / 推进 / 结束 Activity
```

| 规则 | 内容 |
|------|------|
| **A-84** | Activity **不是** Capability，Capability **不是** Activity |
| **A-85** | Capability **可以**导致 Activity 的开始 / 推进 / 结束，但**必须经 World Change**，不得直接改 Activity 内部状态 |
| **A-86** | Activity **不得**被实现为一组 Capability 的别名 |
| **A-87** | `CreateActivity` 若未来成为 Capability，它属于 **D-4**，**D-2 不实现** |
| **A-88** | D-2 **禁止**任何 Capability 集成（本阶段明令禁止） |
| **A-89** | Activity 与 Capability 的具体接口**未冻结**，属 D-4 / D-5 |

---

## D2-DEC-17 · Activity 如何避免变成第二套 World SOT

**问题：** 如何避免？

### 建议：**六条防线**

| 规则 | 内容 |
|------|------|
| **A-90** | Activity **不得**复制 World 事实（位置、房间、建筑、NPC、钱包…）为自有字段；只能**引用** |
| **A-91** | Activity **不得**创建独立的持久化介质（`A-18`） |
| **A-92** | Activity **不得**成为任何 World Fact 的权威来源；若出现冲突，以 World Query / `main.data` 为准 |
| **A-93** | Activity **不得**与 Legacy Activity State **双向同步**（`SOT-9` 精神）；只允许**单向只读派生** |
| **A-94** | Activity **不得**被任何其他模块当作「事实来源」来读取 World 状态 |
| **A-95** | 一旦发现「Activity 与 World Query 对同一事实给出不同答案」，**必须**视为架构缺陷并上报 |

**「单向只读派生」的精确定义（D-2 的关键约束）：**

```text
Legacy Activity State（18 类，main.data）
        ↓  只读派生（one-way）
D-2 Activity（Runtime-scoped Domain Object）
        ✗ 不得反向写回
```

| 规则 | 内容 |
|------|------|
| **A-96** | D-2 阶段，Activity 与 Legacy Activity State 的关系是 **Legacy → Activity 的单向只读派生** |
| **A-97** | **禁止** Activity → Legacy 的反向写入（`AC-2` / `AC-3`） |
| **A-98** | **双向同步**在任何阶段都被禁止（`SOT-9`） |
| **A-99** | `D-6` 才处理 Legacy 字段的**归属迁移**（把 Legacy 字段改成 Activity 的投影）；D-2 **不迁移** |

---

## D2-DEC-18 · Activity 如何避免变成 Scheduler

**问题：** 如何避免变成 scheduler？

### 建议：**以「语义方向」为界**

| | Scheduler | Activity |
|---|---|---|
| 回答 | 「**什么时候**触发什么」 | 「**谁正在经历什么**」 |
| 时间语义 | 触发时刻（future trigger） | 持续区间（duration） |
| 存在性 | 到点即消失 / 重排 | 有生命周期与身份 |
| 驱动 | 时间推进 | World Change / Decision |

| 规则 | 内容 |
|------|------|
| **A-100** | Activity **不是** Scheduler；Activity **不得**定义「到点触发」语义 |
| **A-101** | Activity **不得**持有「下次触发时间」这类调度字段（如 `next_ts`） |
| **A-102** | Activity **可以**有 `expected_end_at`（**预期结束时间**），这是**描述**，不是**触发** |
| **A-103** | D-2 **禁止**实现任何 tick / loop / timer 驱动的 Activity 推进（本阶段明令禁止 scheduler） |
| **A-104** | Activity 的推进只能来自 **World Change → 感知 → Decision**（后续阶段），**不得**来自时间轮询 |
| **A-105** | D-2 **必须**明确：`expected_end_at` 到期**不等于** Activity 自动结束（否则就是 scheduler） |
| **A-106** | 现有 10 项节律 / 调度键（`story_rhythm` / `writing_rhythm` / `living_rhythm` / `ai_home_act_next` / `ai_auto_next` / `_last_think_invite` / `ai_drive_log` / `ai_last_human` / `ai_last_auto` / `ai_diary_log`）在 D-2 **仍属 Legacy 调度状态**，**不得**被改造成 Activity 字段 |

**`A-105` 是本节最关键的一条：**
一旦「到期即结束」被允许，Activity 就退化为 Scheduler 的包装。

---

## D2-DEC-19 · Activity 如何支持「持续角色人生」

**问题：** 如何支持 Product Guide 的核心目标？

### Product Guide 依据

```text
§1  产品最高目标：可进入的角色人生
§6  世界必须独立于玩家继续存在（Hard / Scheduled / Emergent World）
§8  AI 行为长期因果模型（完整链）
§同 禁止为了实现一个功能而在某个 ext_xxx 内偷偷建立另一套 AI Brain
```

### 建议

| 规则 | 内容 |
|------|------|
| **A-107** | Activity 的**产品意义**：让「AI 有自己的生活」成为**可查询、可解释、可进入**的事实，而不是散落的隐式布尔 |
| **A-108** | 玩家上线时能回答「他**现在正在做什么**」——这是「进入他此刻正在经历的世界」的最低要求 |
| **A-109** | Activity **必须可解释**：能回答「为什么他现在在做这个」（经 `goal_id` / `commitment_ids` / 来源），**不得**只给出一个无来源的标签 |
| **A-110** | Activity **不得**用随机性解释「他为什么在做这个」（`INVARIANT-18`） |
| **A-111** | 玩家**离线**时 Activity 概念**仍然成立**（世界独立于玩家运行，`§6`）；但 D-2 **不实现**离线推进（需要 Scheduler / World Tick，属 D-3 / 后续） |
| **A-112** | Activity **不得**成为新的「第二套 AI Brain」：它**描述**生活，不**决定**生活 |
| **A-113** | D-2 的成功标准不是「AI 会自己跑起来」，而是**「持续人生有了正确的语义承载」** |

---

## 4. 与已冻结 Contract 的一致性检查

| 已冻结规则 | D-2 是否可满足 | 本 Preflight 落点 |
|-----------|---------------|-----------------|
| `AC-2` / `AC-3`（不修改现有活动字段） | ✅ | `A-96` ～ `A-99`（单向只读派生，不迁移） |
| `AC-5`（Activity 唯一正式抽象） | ✅ | `A-4` |
| `AC-6`（18 类 = Legacy） | ✅ | §1.1 + `A-96` |
| `AC-7`（禁止多 Activity 真相） | ✅ | `A-58` / `A-90` ～ `A-95` |
| `AC-8`（Activity ≠ Goal / Commitment / Action） | ✅ | `A-3` / `A-6` / `A-7` / `A-74` |
| `AC-9`（D-2 建立 data model / lifecycle / ownership） | ⚠️ **部分**（SOT / persistence 留 D2-OPEN-1） | `A-17` |
| `AC-10`（AC-2/3 续效） | ✅ | `A-97` |
| `D0G-4`（禁止第二 Activity SOT） | ✅ | `A-18` / `A-91` |
| `SOT-10`（持久化不得平行） | ✅ | `A-18` / `A-20` |
| `SOT-9`（禁止双向同步） | ✅ | `A-98` |
| `MO-17`（Motivation 不消费 World Query） | ✅ | §1.3 —— 并由此产生 `D2-OPEN-2` |
| §5B.8（Motivation 最小输入集冻结） | ⚠️ **需注意** | `D2-OPEN-2` |
| `EV-3` / `EV-4`（Event 不改数据 / 不触发行为） | ✅ | `A-9` / `A-49` |
| `IN-6`（Intent 不直接触发副作用） | ✅ | `A-8` |
| `WQ-42` ～ `WQ-46`（D-1 不实现 Activity） | ✅ | D-2 才建立；D-1 仍只返回 Legacy 派生值 |
| `WQ-105` ～ `WQ-108`（不读 AgentState 作数据源） | ✅ | `A-15` / `A-16`（Activity ≠ AgentState.current_activity） |
| `INVARIANT-4`（Activity 属于 World） | ✅ | `A-37` |
| `INVARIANT-5` / `6`（Goal ≠ Activity；Commitment ≠ Activity） | ✅ | `A-6` / `A-7` |
| `INVARIANT-14`（Frontend 不拥有 World 真相） | ✅ | `A-79` |
| `INVARIANT-18`（随机不得承担核心行为原因） | ✅ | `A-53` / `A-81` / `A-110` |
| `WT-1`（World Tick Blocker 属 D-3） | ✅ | D-2 不修 |
| **`WL-65`（D-1 不新增 main.data 顶层 key）** | ⚠️ **张力** | `A-19` + `D2-OPEN-1` |

---

## 5. Legacy Activity State → Activity 映射（D-2 必须给出，D-0 `D0-DEC-2` 要求）

| # | Legacy key | 建议对应的目标 Activity `type` | 备注 |
|---|-----------|---------------------------|------|
| 1 | `dates[]` | `DATE` | status: pending / coming / active / ended |
| 2 | `date_invites[ai]` | `DATE`（**PLANNED 阶段**） | 无 status 字段 |
| 3 | `date_invites_out[ai]` | `DATE`（**PLANNED 阶段**） | waiting / accepted / rejected |
| 4 | `date_invite_out_<ai>` | （调度标记，**不映射**） | 双实现；属 Scheduler 类 |
| 5 | `date_last_invite_ts[ai]` | （调度标记，**不映射**） | 双实现；属 Scheduler 类 |
| 6 | `work_sessions[ai]` | `WORK` | 有 building_id / start_ts / hours |
| 7 | `work_switch[ai]` | （状态位，**不映射**） | 属自主性开关 |
| 8 | `home_jobs[ai]` | （World Fact，**不映射**） | 工作场所配置 |
| 9 | `ai_auto_work_mark[ai]` | （调度标记，**不映射**） | 日期闩锁 |
| 10 | `ai_shop_state[ai]` | `SHOP`（**部分**） | 含配额 / 冷却 / 待回礼；其中 `next_shop_ts` 属调度 |
| 11 | `ai_follow[ai]` | `COMPANION` | Movement 相关，D-3 主责 |
| 12 | `ai_pending_moves[ai]` | （Movement，**D-3 主责**） | 不映射为 Activity |
| 13 | `ai_meeting[ai]` | `MEETING`（**PLANNED / TRAVELING 阶段**） | 约定到达 |
| 14 | `ai_stay_put[ai]` | （状态位，**不映射**） | 约束，不是过程 |
| 15 | `ai_vacation[ai]` | （状态位，**不映射**） | 约束，不是过程 |
| 16 | `ai_life_policy[ai]` | （失效门禁，**不映射**） | 无写入方 |
| 17 | `ai_spot_state[ai]` | （检测状态，**不映射**） | 到达检测 |
| 18 | `instances[*].status` | `INSTANCE` | 含 participants[] |
| 19 | 10 项节律 / 调度键 | （**全部不映射**） | 属 Scheduler 类 |

**映射原则（建议冻结）：**

| 规则 | 内容 |
|------|------|
| **A-114** | 映射只覆盖**「过程」类**字段；**「调度 / 状态位 / World Fact / 检测」类字段一律不映射** |
| **A-115** | 上表是 **D-2 的设计基线**，**不是实现授权**；D-2 不实现映射代码 |
| **A-116** | 映射**不得**导致 Legacy 字段被修改或删除（`AC-2` / `AC-3`） |
| **A-117** | 映射**必须**在 D-6 才能落地为代码 |

---

## 6. Activity 最小结构（候选，D-2 Contract 冻结）

基于 D-0 Preflight §13，本 Preflight 建议如下**语义冻结**（字段名在 D-2 Contract 细化）：

```text
Activity
├── activity_id        # 身份（必需）
├── type               # 过程类型（必需，开放枚举）
├── actor_ids          # 主体（必需，≥1；A-67）
├── participant_ids    # 参与者（可选；A-61 / A-62）
├── role_map           # 参与者角色（actor / partner / participant / observer）
├── location_id        # 这个过程发生在哪里（可选；A-47，≠ AI 当前位置）
├── status             # 生命周期（A-30 ～ A-33）
├── started_at         # 开始时间（可选）
├── expected_end_at    # **预期**结束时间（可选；A-102 / A-105）
├── ended_at           # 实际结束时间（可选）
├── goal_id            # 弱引用，可为空（A-68 ～ A-71）
├── commitment_ids     # 弱引用，可为空（A-72 ～ A-75）
├── current_step       # 过程内部步骤（可选；语义未冻结）
├── origin             # 来源说明（用于 A-109 的可解释性）
└── metadata           # 扩展位（内容未冻结）
```

| 规则 | 内容 |
|------|------|
| **A-118** | 上列结构是 **D-2 的语义候选**；字段名 / 类型 / 必填性在 **D-2 Contract** 冻结 |
| **A-119** | `type` 是**开放枚举**，D-2 **不得**冻结完整类型清单（否则会限制未来功能） |
| **A-120** | `current_step` / `metadata` 的**语义在 D-2 不冻结**（避免过度设计） |
| **A-121** | Activity **不得**包含任何 World 事实的副本字段（`A-90`） |
| **A-122** | Activity **不得**包含调度字段（`next_ts` 等；`A-101`） |

---

## 7. Activity 与现有模块的边界（实现约束）

| 模块 | 与 Activity 的关系（D-2） |
|------|------------------------|
| `main.data` | Activity **不写入**（`A-19` / `A-22`） |
| `agent/world_query.py` | **不得**被扩展为返回 Activity（D-1 `WQ-42` 仍有效）；D-2 **不修改** world_query |
| `agent/state.py` | `AgentState.current_activity` **保持不变**（`A-15` / `A-16`）；D-2 **不修改** |
| `agent/dynamic_world_provider.py` | **不修改**（继续读 `current_activity`） |
| `agent/motivation.py` | **不修改**（`MO-17` 禁止消费 World Query；见 `D2-OPEN-2`） |
| `agent/runtime.py` | **不修改**；未来至多持有 `current_activity_id` 绑定引用（D-0 Preflight §15） |
| `agent/event.py` / `event_adapter.py` | **不修改**；D-2 不实现 Event 生产（`A-34`） |
| `ext_ai.py` / `ext_world.py` / `ext_room.py` / `ext_date.py` / `ext_econ.py` / `ext_shop.py` / `ext_instance.py` | **完全不修改**；迁移属 D-6 |
| 前端 | **不修改** |
| Memory | **不触碰** |

---

## 8. D-2 建议实施形态（供 Contract 参考，非授权）

> **以下只是「如果架构侧批准，D-2 Implementation 会是什么形状」，**
> **不是实现清单，也不构成授权。**

```text
可能新增（需 Contract 批准）：
    agent/activity.py
        - Activity 数据结构（Domain Object）
        - 生命周期常量与转换合法性
        - 显式转换 API（transition_*）
        - Legacy → Activity 的只读映射函数（单向）
        - 自描述 / 边界声明

明确不新增：
    ✗ Activity 持久化
    ✗ Activity Runtime 容器（若需要，须单独 Contract Change）
    ✗ scheduler / tick / timer
    ✗ Event 集成
    ✗ Capability 集成
    ✗ world_query 扩展
```

**若 D-2 Implementation 被批准，其验收应至少包含：**

```text
① 生命周期转换合法性（非法转换被拒绝）
② 终态不可逆
③ Activity ≠ Goal / Commitment / Intent / Event / Action（结构级断言）
④ 不写入 main.data（写入模式静态扫描）
⑤ 不出现调度字段（next_ts 等）
⑥ 不 import main / ext_*
⑦ 单向只读映射（不得反向写 Legacy 字段）
⑧ primary 唯一性语义（或明确记录未实现）
⑨ NPC 活动 → UNSUPPORTED
⑩ 可拆卸性（删除 activity.py 不影响现有功能）
```

---

## 9. 本 Preflight 明确不做的事

```text
❌ 创建 agent/activity.py
❌ Activity Runtime
❌ Activity persistence
❌ scheduler（任何 tick / loop / timer）
❌ Event integration
❌ Movement integration
❌ Capability integration
❌ ext_world.py migration
❌ ext_ai.py migration
❌ 修改 AgentState / DynamicWorldProvider / Motivation / Runtime / Context
❌ 修改 world_query.py
❌ 修改 ext_* 任何行为
❌ 修改前端 / HTTP API
❌ 新增 main.data 顶层 key
❌ 创建缓存 / 索引 / 数据库
❌ 进入 D-3
```

---

## 10. D-2 Preflight 检查清单

### 定义

- [ ] Activity 严格定义已裁决（`D2-DEC-1` / `A-1` ～ `A-4`）
- [ ] 与 Goal / Commitment / Intent / Event 边界已裁决（`D2-DEC-2` / `A-5` ～ `A-10`）
- [ ] 是否正式 Domain Object 已裁决（`D2-DEC-3` / `A-11` ～ `A-16`）

### SOT 与持久化

- [ ] Activity SOT 已裁决（`D2-DEC-4` / `A-17` ～ `A-21`）→ **含 `D2-OPEN-1`**
- [ ] 是否持久化已裁决（`D2-DEC-5` / `A-22` ～ `A-24`）
- [ ] 重启语义已裁决（`D2-DEC-6` / `A-25` ～ `A-29`）

### 生命周期与并发

- [ ] Lifecycle 已裁决（`D2-DEC-7` / `A-30` ～ `A-36`）
- [ ] 并发性已裁决（`D2-DEC-11` / `A-55` ～ `A-60`）
- [ ] 打断语义已裁决（`D2-DEC-10` / `A-49` ～ `A-54`）

### 关系边界

- [ ] 与 World State 已裁决（`D2-DEC-8` / `A-37` ～ `A-42`）
- [ ] 与 Location / Movement 已裁决（`D2-DEC-9` / `A-43` ～ `A-48`）
- [ ] 参与者模型已裁决（`D2-DEC-12` / `A-61` ～ `A-67`）
- [ ] Goal 依赖已裁决（`D2-DEC-13` / `A-68` ～ `A-71`）
- [ ] Commitment 依赖已裁决（`D2-DEC-14` / `A-72` ～ `A-75`）

### 授权与反模式

- [ ] 授权模型已裁决（`D2-DEC-15` / `A-76` ～ `A-83`）
- [ ] Capability 关系已裁决（`D2-DEC-16` / `A-84` ～ `A-89`）
- [ ] 防第二 SOT 防线已裁决（`D2-DEC-17` / `A-90` ～ `A-99`）
- [ ] 防 Scheduler 防线已裁决（`D2-DEC-18` / `A-100` ～ `A-106`）

### 产品与一致性

- [ ] 产品对齐已裁决（`D2-DEC-19` / `A-107` ～ `A-113`）
- [ ] Legacy 映射表已裁决（§5 / `A-114` ～ `A-117`）
- [ ] 最小结构已裁决（§6 / `A-118` ～ `A-122`）
- [ ] 与已冻结 Contract 全部一致（§4）
- [ ] OPEN QUESTION 已明确记录（§11）

---

## 11. D-2 OPEN QUESTION

> 按 D-0 接手说明 §34：**不擅自修改设计，先记录歧义，等待架构侧确认。**

---

### D2-OPEN-1 · Activity 的 SOT 与持久化位置（**中心开放问题**）

**问题是什么**

`AC-9` 要求 D-2 建立 Activity 的 **ownership + SOT + persistence**；
但同时存在：

```text
AC-2 / AC-3   禁止修改现有 18 类活动状态字段
D0G-4         禁止第二套 Activity SOT
SOT-10        持久化不得与 main.data 平行、同等权威
WL-65         D-1 已确立「不新增 main.data 顶层 key」的先例
AC-7          禁止多个 Activity 真相并存
```

**为什么存在歧义**

把 ①（要 SOT）与 ③（不能有平行 SOT）同时执行时，Activity **无处可存**：

| 可能的落点 | 阻碍 |
|-----------|------|
| 新增 `main.data` 顶层 key（如 `activities`） | 需 Contract Change；与 `WL-65` 先例冲突；但原则上是**唯一**能同时满足「单一 SOT + 持久化」的路径 |
| 写入现有 18 类字段 | **直接违反 `AC-2` / `AC-3`** |
| 独立持久化（文件 / JSON） | **直接违反 `SOT-10` / `D0G-4`** |
| 不持久化 | `AC-9` 的 persistence 未兑现 |

**当前代码是什么**

```text
18 类 Legacy Activity State 全在 main.data 内
没有任何 Activity 对象
没有任何持久化介质为 Activity 预留
```

**可能影响什么**

- 若选「新增 `main.data` 顶层 key」：需明确它**不是**第二 SOT，且与 Legacy 字段的关系（`A-96` 单向派生）
- 若选「不持久化」：必须接受 `AC-9` 部分未兑现，**且必须明确记为已知限制**（本 Preflight 建议的路径）
- 该决定直接决定 D-2 Implementation 是否存在（若 SOT 无法裁决，D-2 只能停留在「语义冻结」）

**需要架构侧回答**

1. D-2 的 Activity 是否**必须**持久化？还是可以先 Runtime-scoped？
2. 若持久化，落点是「`main.data` 新增顶层 key」还是「从 Legacy 可重建的只读投影」？
3. `WL-65`（不新增 `main.data` 顶层 key）是 **D-1 专属约束**，还是**贯穿 D 阶段的通用约束**？

---

### D2-OPEN-2 · Activity 如何进入 Motivation（与 `MO-17` / §5B.8 的张力）

**问题是什么**

`motivation.py:114` 当前**已经在读**：

```python
activity = agent_state_snapshot.get("current_activity")
```

但：

- §5B.8 冻结的 Motivation 最小输入集合是 `goal / commitment / agent_state_snapshot / now_ts`
- `MO-17` 明确**禁止** Motivation 消费 **World Query**
- `MO-16` 规定 Motivation **只消费** §5B.8 所列最小输入集合

**为什么存在歧义**

```text
若 Activity 应该影响 Motivation：
    路径 A：经 AgentState 字段（需要新增 AgentState 字段 → 扩展 §5B.8 → Contract Change）
    路径 B：经 World Query（被 MO-17 明确禁止）
    → 两条路都需要 Contract Change，D-2 无法自行选择

若 Activity 不应该影响 Motivation：
    → 则当前 motivation.py 读取的 current_activity 是「Legacy 派生标签」，
       它已经在影响 Motivation，但这与「Activity 是正式 Domain Object」形成语义落差
```

**当前代码是什么**

```text
motivation.py:114                 读 agent_state_snapshot["current_activity"]
agent/state.py:164/184            current_activity 由 _derive_activity() 推导
agent/dynamic_world_provider.py   current_activity 经 AgentState 注入 Context
```

**可能影响什么**

- 若不解决：D-2 建立的正式 Activity 与「Motivation 实际读到的标签」会**长期不一致**
- 若经 AgentState：需要新增字段（如 `current_activity_id`），属 **§5B.8 扩展**，必须 Contract Change
- 这个决定直接决定 D-2 的 Activity 是否有**行为意义**（还是只是一个可查询但无人使用的对象）

**需要架构侧回答**

1. D-2 的 Activity 是否必须进入 Motivation？
2. 若进入，路径是「新增 `AgentState` 字段」还是其他？
3. `MO-17` 禁止的是「World Query 作为 Motivation 输入」，是否包括「由 World Query 派生的 Activity」？

---

### D2-OPEN-3 · Activity 类型清单是否冻结

**问题是什么**

D-0 Preflight 与 D-0 决策文档给出了 Activity 的目标方向
（`work` / `date` / `shopping` / `cooking` / `companion` / `travel` / `game` / `surgery` …），
但**未给出完整清单**，也未说明这是否是完整枚举。

**为什么存在歧义**

- 若在 D-2 冻结完整类型清单 → 未来新增功能必须改 Contract，且可能限制产品演进
- 若不冻结 → Activity 的 `type` 语义可能被各模块随意扩展，形成「隐式类型系统」

**当前代码是什么**

Legacy 侧与 type 相关的只有「标签字符串」（如 `_derive_activity` 返回 `dating` / `working` / `following` / `idle`），
**没有任何类型注册表**。

**可能影响什么**

决定 D-2 是否需要引入「类型注册 / 校验」机制（本 Preflight 建议**不引入**，`A-119`）。

**需要架构侧回答**

1. `type` 是开放字符串，还是受控枚举？
2. 若受控，谁负责注册新类型？
3. 是否需要「未知 type 的处理规则」（拒绝 / 接受 / UNSUPPORTED）？

---

### D2-OPEN-4 · Activity 的「谁真正拥有它」在 D-2 是否存在

**问题是什么**

D-0 Preflight §15 指出 Runtime 至多持有 `current_activity_id`，
但**没有说明「谁真正拥有 Activity 集合」**（World？Domain 层？Agent 各自的 holder？）。

**为什么存在歧义**

- 若由 World 拥有 → 需要一个 World 侧的 Activity 容器（但 D-2 禁止第二 SOT）
- 若由每个 Agent 各自持有 → 会形成「每 Agent 一套 Activity」，可能出现重复与不一致（`AC-7` 风险）
- 若由 Domain 层统一持有 → 需要一个新模块，其职责与 SOT 归属仍待定

**当前代码是什么**

不存在任何 Activity 容器。

**可能影响什么**

直接决定 D-2 Implementation 的模块形状，以及 `A-55`（primary 唯一性）是否有归属主体。

**需要架构侧回答**

1. D-2 是否需要 Activity 容器？若需要，归谁？
2. 若不需要容器，Activity 如何被引用与查询？
3. 与 D2-OPEN-1 的组合：容器是否就是 SOT？

---

## 12. D-2 Preflight 状态

```text
Status:
    PRE-FLIGHT

Implementation:
    NOT AUTHORIZED
    （agent/activity.py / Activity Runtime / persistence /
      scheduler / Event / Movement / Capability 集成全部禁止）

Decisions Proposed:
    D2-DEC-1  ～ D2-DEC-19（19 项，对应架构侧 19 个提问）
    A-1       ～ A-122（122 条候选规则）

Open Questions:
    D2-OPEN-1  Activity SOT 与持久化位置（中心问题）
    D2-OPEN-2  Activity 如何进入 Motivation（与 MO-17 / §5B.8 的张力）
    D2-OPEN-3  Activity 类型清单是否冻结
    D2-OPEN-4  Activity 的归属容器在 D-2 是否存在

Next:
    Review / Resolve D2-DEC-1 ～ D2-DEC-19 + 4 个 OPEN QUESTION

After Approval:
    D-2 Contract Change（Contract §5E）

After Contract:
    D-2 Architecture Tests

After Tests:
    D-2 Implementation
```

**End of D-2 Activity Contract Preflight**
