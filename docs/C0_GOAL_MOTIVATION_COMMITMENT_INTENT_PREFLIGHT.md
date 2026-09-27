# C-0 GOAL / MOTIVATION / COMMITMENT / INTENT CONTRACT PREFLIGHT

> 本阶段只做架构预检 / 设计文档。
> **未修改任何 `.py`、前端、数据、Memory、Provider、Assembler、Runtime、main、ext_\*、Contract。**
> 完成后停止，等待架构审核。
> **不进入 C-1 / C-2 编码，不实现 Goal / Motivation / Commitment / Intent，不接 LLM。**

---

## 0. 文档性质与输出分类

本文档严格区分五类内容：

| 分类 | 含义 |
|------|------|
| **A. 已冻结架构事实** | 来自 B1～B6 已 ACCEPTED 的 Contract / Preflight，**不可在本阶段推翻** |
| **B. C-0 新提出的设计候选** | 本阶段新提出，供 C-1 Contract Change 评估，**尚未冻结** |
| **C. 推荐方案** | 在 B 类候选中，C-0 倾向推荐的一个，**仍未冻结** |
| **D. 尚未冻结的问题** | 明确留给 C-1 或更后续阶段决定的问题 |
| **E. 禁止本阶段实现的内容** | 本阶段不实现、不修改、不接入的所有内容 |

**关键原则：**

> **不要把"设计建议"写成已冻结的 Contract。**
> **C-0 认为需要冻结的项，必须明确提出"为什么"，不得自行修改 Contract。**

---

## 1. 当前基线（A 类）

### 1.1 已封板阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| B1 ～ B4 | Context Foundation 前四阶段 | ✅ ACCEPTED |
| B5-0 ～ B5-4 | Context Contract / Change / Connection / Tests / PROJECT | ✅ ACCEPTED |
| B6 | THINK / Decision 架构预检（修订版） | ✅ ACCEPTED |

### 1.2 必须保持的架构事实

1. `main.data` 仍是唯一 Source of Truth。
2. `AgentState` 仍然只是 projection。
3. `AgentRuntime` 不是第二数据库。
4. `AgentContext` 是 V3.1 正式 Context。
5. `ContextLayers` 继续作为 deprecated compatibility stub。
6. `LongTermProvider` 继续返回 `[]`。
7. Memory Runtime 不启用。
8. `ext_ai` 不重写、不删除。
9. `ext_ai.build_ai_context` 不接入 V3.1 正式链。
10. 不接 LLM。
11. 不实现 THINK。
12. 不实现 Decision。
13. 不实现 Action。
14. 不修改 `main.py`。
15. 不修改任何 `ext_*.py`。
16. 不修改 frontend。
17. 不建立第二套数据库。
18. 不建立第二套 Agent State。
19. 不建立 Goal 数据库或 Goal 独立持久化文件。
20. 不进入 C-1 / C-2 编码。

### 1.3 B6 已冻结的定义

```text
Goal       = 我想完成什么
Commitment = 我已经答应 / 约定 / 承诺什么
Motivation = 我为什么现在想完成它
Intent     = 我现在倾向做什么
Decision   = 我最终选择做什么
Action     = 系统真正执行什么
```

### 1.4 B6 已冻结的边界

- `Intent ≠ Decision`。
- `World Query ≠ Decision`。
- `Action ≠ Decision`。
- THINK 不直接执行 Action。
- `think(context) -> Optional[str]` 是 B5 临时占位，不代表最终 Intent Contract。
- World Query 是无副作用信息查询，可被 THINK / Decision 调用，不修改 `main.data`。
- Goal 的最终持久化位置暂不冻结。

---

## 2. 概念总览

```text
Relationship ────┐
Memory ──────────┼──→ Goal ──────┐
Commitment ──────┘               │
                                 ↓
State ──────────────────→ Motivation
Recent Experience ──────→        │
World Conditions ───────→        │
                                 ↓
                            IntentSet
                                 │
                                 ↓
                            World Query
                                 │
                                 ↓
                            Query Result
                                 │
                                 ↓
                             Decision
                                 │
                                 ↓
                              Action
                                 │
                                 ↓
                          existing ext_*
                                 │
                                 ↓
                           World Change
                                 │
                                 ↓
                               Event
```

---

## 3. Goal

### 3.1 Goal 数据结构设计草案（B 类）

**建议字段（不冻结字段名，不冻结类型）：**

| 字段 | 含义 | 建议来源 |
|------|------|---------|
| `goal_id` | Goal 唯一标识 | 系统生成 |
| `owner` / `actor` | 拥有者（AI 名） | Agent identity |
| `type` | 类型（如 `companionship` / `medical` / `work` / `social` / `personal`） | 创建时指定 |
| `description` | 人类可读描述 | 创建时指定 |
| `source` | 来源（见 3.5） | 创建时指定 |
| `status` | 生命周期状态（见 3.2） | 状态机 |
| `priority` | 优先级（待 C-1 定义算法） | 创建/更新时计算 |
| `created_at` | 创建时间 | 系统 |
| `updated_at` | 最近更新 | 系统 |
| `target` / `desired_state` | 期望达成的状态 | 创建时指定 |
| `deadline` | 可选，截止时间 | 创建时指定 |
| `related_commitments` | 关联 Commitment IDs | 创建时指定 |
| `related_activity` | 关联 Activity IDs | 创建时指定 |
| `completion_condition` | 何时视为完成 | 创建时指定 |
| `reason` | 为什么创建（审计用） | 创建时指定 |

**关键约束：**

- `reason` 必须可审计。
- `source` 必须是 3.5 中的允许来源。
- `completion_condition` 必须明确，不能是"感觉完成了"。

### 3.2 Goal 生命周期（B 类）

**建议状态机：**

```text
CREATED ──→ ACTIVE ──→ COMPLETED
              │
              ├──→ CANCELLED
              │
              └──→ EXPIRED
```

| 状态 | 含义 | 是否终态 |
|------|------|---------|
| `CREATED` | 刚被创建，未激活 | 否 |
| `ACTIVE` | 正在追求 | 否 |
| `COMPLETED` | 已达成 | 是 |
| `CANCELLED` | 主动取消 | 是 |
| `EXPIRED` | 被动过期 | 是 |

**是否需要其他状态：**

- **是否需要 `PAUSED`？**
  - C-0 倾向**不引入** `PAUSED`。
  - 理由：Goal 的暂停应通过 Motivation 层动态反映，而不是把 Goal 状态复杂化。
- **是否需要 `BLOCKED`？**
  - C-0 倾向**不引入** `BLOCKED`。
  - 理由：被阻塞应通过 World Query 结果反映，而不是把 Goal 状态复杂化。
- **是否需要 `SUPERSEDED`？**
  - C-0 倾向**不引入**。
  - 理由：被更高优先级覆盖时，应记录为 `CANCELLED` + `reason`。

**约束：**

- 状态转换必须单向（不允许 `COMPLETED → ACTIVE`）。
- 状态转换必须可审计。
- 状态转换不直接修改 `main.data`。

### 3.3 Goal 是否允许多个同时存在（B 类）

**结论（推荐 C 类）：允许，但有限制。**

- 允许多个 Goal 同时存在。
- 每个 Goal 有独立生命周期。
- **允许多个 `ACTIVE`**，但需要优先级。
- **不允许多个 Goal 语义冲突且同时 `ACTIVE`**。

**优先级处理（待 C-1 冻结）：**

C-0 建议优先级至少考虑：

1. `hard` Commitment 关联的 Goal。
2. 用户直接要求的 Goal。
3. 未完成 Activity 关联的 Goal。
4. Relationship / Memory 推导的 Goal。
5. AI 自身长期偏好 / 愿望的 Goal。

**冲突处理（待 C-1 冻结）：**

C-0 建议：

- 冲突时，Commitment 关联的 Goal 优先。
- 用户要求 vs AI 自主：用户要求不自动覆盖 AI 核心自主 Goal，但需要在 Decision 层显式权衡。
- 冲突必须可审计。

**判断当前哪个 Goal 更重要（待 C-1 冻结）：**

- 不由随机决定。
- 不由 LLM 自由决定。
- 应基于优先级 + Motivation + World Conditions + Commitment。

### 3.4 Goal 如何跨 Event 持续（A + B 类）

**已冻结要求（A 类）：**

- 一个 Event 不能让 Goal 无故消失。
- Goal 必须能够跨 Event 持续存在。

**C-0 建议（B 类）：**

- Goal 持久化位置暂不冻结（见 §13）。
- Goal 不能被单次 Event 覆盖。
- Goal 只能通过状态机转换改变状态。

### 3.5 Goal 的来源分类（B 类）

**允许来源（仅这七类）：**

| 来源 | 示例 | 说明 |
|------|------|------|
| **用户要求** | 用户说"陪我过周末" | 用户明确表达 |
| **Commitment** | AI 答应陪用户过周末 | 从承诺推导 |
| **Relationship** | 想和主人多相处 | 从关系状态推导 |
| **Memory** | 记得上次没说完的事 | 从记忆唤醒推导 |
| **未完成 Activity** | 陪伴活动尚未结束 | 从 Activity Lifecycle 推导 |
| **工作 / 日程 / 世界约束** | 需要上班 / 需要就医 | 从世界规则推导 |
| **AI 自身长期偏好 / 愿望** | 想去看画展 | **AI 自己的目标，不是用户要求** |

**关键约束：**

> **不要把 AI 的所有 Goal 都变成"用户说了什么"。**
> **AI 必须未来能够存在自己的生活目标。**

**禁止来源（E 类）：**

- ❌ 凭空生成。
- ❌ 随机生成。
- ❌ LLM 自由生成（未经验证的 LLM 输出不能直接成为 Goal）。
- ❌ 从 chat / sms / timeline / trails 直接推导。

### 3.6 Goal 禁止随机生成（A 类）

**已冻结：**

> 随机性不能作为核心 Goal 因果。

**允许随机：**

- 非关键生活细节。
- 候选生成。
- 非关键偏好。
- 偶发记忆唤醒。

**禁止随机：**

- 核心 Goal 生成。
- Goal 来源选择。
- Goal 优先级决定。
- Goal 是否取消 / 完成。

---

## 4. Commitment

### 4.1 Commitment 数据结构设计草案（B 类）

**建议字段（不冻结字段名，不冻结类型）：**

| 字段 | 含义 |
|------|------|
| `commitment_id` | 唯一标识 |
| `type` | `user_promise` / `ai_promise` / `meeting` / `date` / `implicit` |
| `actor` | 承诺方 |
| `counterparty` | 被承诺方（用户 / AI / 自己） |
| `content` | 承诺内容 |
| `created_at` | 创建时间 |
| `updated_at` | 最近更新 |
| `expires_at` | 可选，过期时间 |
| `status` | 生命周期状态 |
| `strength` | 强度（见 4.5） |
| `linked_goal` | 可选，关联 Goal |
| `linked_activity` | 可选，关联 Activity |
| `source` | 来源（event / chat / date / meeting） |
| `reason` | 为什么形成（审计用） |

### 4.2 谁对谁承诺（B 类）

**必须分别考虑四类：**

| 类型 | actor | counterparty | 强度默认 | 说明 |
|------|-------|--------------|---------|------|
| **AI → 用户** | AI | 用户 | `hard` | AI 答应用户 |
| **用户 → AI** | 用户 | AI | `hard` | 用户答应 AI |
| **AI → AI** | AI A | AI B | `soft` | AI A 答应 AI B |
| **AI 对自己** | AI | 自己 | `soft` | AI 对自己说"我要..." |

**关键约束：**

- 用户承诺**不得**被 AI↔AI 承诺覆盖。
- AI↔AI 承诺**不得**被随机性覆盖。
- AI 对自己的承诺**不得**被随机性覆盖。
- AI 对自己的承诺是 AI 自主性的基础，**不是用户要求的衍生**。

### 4.3 Commitment 生命周期（B 类）

**建议状态机：**

```text
CREATED ──→ ACTIVE ──→ FULFILLED
              │
              ├──→ CANCELLED
              │
              └──→ EXPIRED
```

| 状态 | 含义 | 是否终态 |
|------|------|---------|
| `CREATED` | 刚形成 | 否 |
| `ACTIVE` | 有效 | 否 |
| `FULFILLED` | 已兑现 | 是 |
| `CANCELLED` | 已取消 | 是 |
| `EXPIRED` | 已过期 | 是 |

### 4.4 创建 / 完成 / 取消 / 过期 / 冲突（B 类）

**创建方式：**

- 从 Event 中提取（用户消息 / date / meeting）。
- 从 AI↔AI Event 中提取。
- 从 AI 自身决策中提取（AI 对自己承诺）。
- 必须有 `reason`。

**完成方式：**

- 满足承诺条件。
- 必须可审计。
- 不直接修改 `main.data`。

**取消方式：**

- 被更高强度 Commitment 覆盖。
- 被用户明确取消。
- 被 AI 自身决策取消（需 `reason`）。
- 不直接修改 `main.data`。

**过期方式：**

- 超过 `expires_at`。
- 自动进入 `EXPIRED`。
- 不直接修改 `main.data`。

**冲突方式：**

- `hard` 优先于 `soft`。
- 用户承诺优先于 AI↔AI。
- 时间早的优先（同强度）。
- 冲突必须可审计。

### 4.5 强度 / 约束等级（B 类）

**建议三级：**

| 强度 | 含义 | Decision 约束力 |
|------|------|----------------|
| `hard` | 明确承诺 | 不可被随机性覆盖 |
| `soft` | 模糊承诺 | 可被更高优先级覆盖 |
| `implicit` | 隐含承诺 | 视上下文 |

**约束规则：**

- `hard` Commitment **必须**被 Decision 遵守。
- `soft` Commitment 可以被 `hard` Commitment 覆盖。
- `implicit` Commitment 需要显式确认才能升级为 `hard`。
- Commitment **不能**被随机性忽略。

### 4.6 Commitment 与 Goal 的关系（B 类）

```text
Commitment ──→ Goal（可作为 Goal 来源之一）
Commitment ──→ Motivation（作为强约束）
Commitment ──→ Decision（作为强约束）
```

- Commitment 可以**产生** Goal。
- Commitment 可以**约束** Motivation。
- Commitment 可以**约束** Decision。
- Goal **不能**反向修改 Commitment。

### 4.7 Commitment 与 Activity 的关系（B 类）

- Commitment 可以**关联** Activity。
- 例如：Commitment "周六陪用户过周末" 关联 Activity "周末陪伴"。
- Activity 生命周期可以反映 Commitment 履行状态。
- 但 **Commitment ≠ Activity**：
  - Commitment 是承诺。
  - Activity 是正在进行的活动。
- Activity 完成不自动等于 Commitment 履行（需显式判断）。

### 4.8 关键问题回答（B 类）

**问题：**

> 如果 AI 已经答应用户周六一起过周末，新的随机活动是否可以覆盖？

**C-0 回答：**

> **不能。**

理由：

1. "答应用户周六一起过周末" 是 `hard` Commitment。
2. `hard` Commitment 不可被随机性覆盖。
3. 随机性只能用于非关键生活细节 / 候选生成。
4. 若新的随机活动与 `hard` Commitment 冲突，必须被拒绝或重新规划。
5. Decision 层必须以 Commitment 为强约束。

---

## 5. Goal 与 Commitment 的关系（B 类）

### 5.1 Commitment 是否可以产生 Goal

**可以。**

例如：

```text
Commitment: "周六陪用户过周末"
        ↓
Goal: "周六继续陪伴用户"
```

### 5.2 Goal ≠ Commitment

| 维度 | Goal | Commitment |
|------|------|-----------|
| 定义 | 我想完成什么 | 我已经答应什么 |
| 约束力 | 方向性 | 强约束 |
| 来源 | 七类（见 3.5） | 承诺行为 |
| 可取消性 | 可主动取消 | 取消需 `reason` |
| 对 Decision | 参与 | 强约束 |

### 5.3 Goal 可以没有 Commitment 吗

**可以。**

- AI 自身长期偏好 / 愿望产生的 Goal 不一定有 Commitment。
- 例如：AI 想去看画展，没有对任何人承诺。
- 这是 AI 自主性的基础。

### 5.4 Commitment 可以没有 Goal 吗

**可以。**

- 简单的承诺（如"我马上回消息"）不一定形成 Goal。
- 但重要的 Commitment 通常会形成 Goal。

### 5.5 Goal 和 Commitment 发生冲突时怎么办

**C-0 建议（B 类）：**

- Commitment 优先。
- 冲突必须可审计。
- 若 Goal 与 `hard` Commitment 冲突，Goal 应被 `CANCELLED` 或推迟。
- 若 Goal 与 `soft` Commitment 冲突，需要显式权衡。

---

## 6. Motivation

### 6.1 Motivation 是持久状态还是动态计算结果（B 类）

**结论（推荐 C 类）：动态计算结果。**

理由：

1. Motivation 是**当前时刻**的派生量。
2. Motivation 由以下输入计算：
   - Goal
   - Commitment
   - State
   - Relationship
   - Recent Experience
   - World Conditions
3. 持久化 Motivation 会导致：
   - 数据冗余；
   - 状态不一致；
   - 难以审计"为什么当时这样算"。

### 6.2 Motivation 是否需要自己的 ID（B 类）

**结论（推荐 C 类）：不需要持久 ID。**

- Motivation 是瞬时计算结果。
- 若需审计，Motivation **摘要**可以随 Intent 临时携带（不持久化）。
- 不需要 `motivation_id`。

### 6.3 Motivation 是否需要保存（B 类）

**结论（推荐 C 类）：不需要保存。**

- 不写入 `main.data`。
- 不写入独立文件 / 数据库。
- 是瞬时计算结果。

### 6.4 Motivation 是否可以随着时间变化（B 类）

**可以。**

- 同一 Goal 在不同时间可以产生不同 Motivation。
- 这是 Motivation 动态性的核心。

### 6.5 同一个 Goal 能否产生不同 Motivation（B 类）

**可以。**

**示例：**

```text
Goal: "陪用户度过周末"

上午：
Motivation: "用户还在住所，我想继续陪伴。"

下午：
Motivation: "天气很好，我想和用户出去走走。"
```

Goal 没变，但 Motivation 可以变化。

**结论：**

- Motivation 是 Goal + State + World Conditions 的**动态函数**。
- 同一 Goal 在不同时间 / 状态下产生不同 Motivation。

### 6.6 Motivation 核心因果不能由随机概率产生（A 类）

**已冻结：**

> Motivation 的核心因果不能由随机概率产生。

**允许随机：**

- 非关键生活细节。
- 候选生成。
- 记忆偶发唤醒。

**禁止随机：**

- 核心 Motivation。
- "为什么现在想做"的核心原因。

---

## 7. Intent

### 7.1 Intent 正式设计草案（B 类）

**建议字段（不冻结字段名，不冻结类型）：**

| 字段 | 含义 |
|------|------|
| `intent_id` | 唯一标识 |
| `goal_id` | 关联 Goal（可选） |
| `motivation` | Motivation 摘要 |
| `action_type` / `proposed_action` | 倾向的动作类型 |
| `target` | 倾向的目标（人 / 地点 / 物体） |
| `participants` | 参与者（可选） |
| `place` | 地点（可选） |
| `reason` | 为什么倾向这样做 |
| `constraints` | 约束列表（来自 Commitment / World Conditions） |
| `validity` / `expiry` | 有效期 |
| `confidence` | 置信度（可选） |
| `candidate_rank` | 候选排序（可选） |
| `created_at` | 创建时间 |

### 7.2 THINK 是否可以产生多个候选 Intent（B 类）

**可以。**

- THINK 输出 `IntentSet`（或等价结构）。
- 每个 candidate 有独立 `reason` / `confidence`。

### 7.3 如果多个，谁负责选择（B 类）

**Decision 负责选择。**

- THINK 生成候选。
- Decision 选择最终。
- 严格分离。

### 7.4 Decision 是否负责最终选择（B 类）

**是。**

```text
THINK
  ↓
Intent candidates
  ↓
Decision
  ↓
Action
```

### 7.5 Intent 是否允许直接执行（B 类）

**不允许。**

- Intent 是候选。
- Intent 不产生副作用。
- Intent 不直接触发 Action。

### 7.6 Intent 是否有副作用（B 类）

**没有。**

- Intent 是纯数据。
- Intent 不修改 `main.data`。
- Intent 不触发 Action。

### 7.7 Intent 是否应该保存（B 类）

**C-0 建议（B 类）：**

- Intent **不持久化**。
- Intent 是 THINK 的瞬时输出。
- 若需审计，Intent **摘要**可以随 Event 或 Decision 记录。

### 7.8 Intent 是否应该跨 Event 存活（B 类）

**C-0 建议（B 类）：**

- Intent **不跨 Event 存活**。
- 每个 Event 触发新的 THINK。
- 跨 Event 的连续性由 Goal / Commitment / Activity 表达。

### 7.9 Intent 什么时候失效（B 类）

- 被 Decision 选择后失效。
- 超过 `validity` / `expiry` 后失效。
- 被新 Event 触发的新 THINK 覆盖后失效。

### 7.10 必须保持的链（A 类）

```text
THINK
  → Intent candidates
  → Decision
  → Action
```

**而不是：**

```text
THINK
  → Action
```

---

## 8. Decision 边界（B 类）

### 8.1 Decision 与 Intent 的关系

| 维度 | Intent | Decision |
|------|--------|----------|
| 定义 | 我倾向做什么 | 我最终选择做什么 |
| 数量 | 多个候选 | 单一选择 |
| 副作用 | 无 | 无（通过 Action 执行） |
| 对 Action | 不直接触发 | 通过 Action 层执行 |

### 8.2 Decision 根据什么选择

**C-0 建议（B 类）：**

- Commitment（强约束）。
- Goal（方向）。
- Motivation（原因）。
- World Query 结果（事实）。
- 世界规则（必须满足）。

### 8.3 关键问题回答

| 问题 | 回答 |
|------|------|
| Commitment 是否是强约束？ | 是，`hard` Commitment 不可被覆盖 |
| Goal 是否参与？ | 是，作为方向 |
| World Query 是否提供事实？ | 是，作为信息输入 |
| 世界规则是否必须满足？ | 是，不可违反 |
| Decision 是否允许因为随机性改变核心选择？ | **不允许** |

---

## 9. World Query 边界（A 类）

**B6 已冻结：World Query = 无副作用的信息查询。**

**正确链：**

```text
Intent
→ World Query
→ Query Result
→ Decision
→ Action
```

**示例：**

```text
Intent: "我想带用户去医院。"
World Query:
  - 哪些医院存在？
  - 哪些开放？
  - 距离？
  - 是否可以到达？
Query Result: 提供候选。
Decision: 选择医院。
Action: 调用现有 ext_* 执行。
```

**C-0 只定义接口边界，不实现 World Query。**

---

## 10. Activity 与 Goal / Commitment / Intent（B 类）

### 10.1 示例链

```text
Goal:       "陪用户度过周末"
Commitment: "答应陪用户过周末"
Intent:     "继续留在住所"
Decision:   "留在住所"
Activity:   "周末陪伴活动 ACTIVE"
Action:     "保持当前位置 / 互动"
```

### 10.2 关系

| 概念 | 关系 |
|------|------|
| Goal → Activity | Goal 可以关联 Activity |
| Commitment → Activity | Commitment 可以关联 Activity |
| Intent → Activity | Intent 可以建议 Activity 类型 |
| Decision → Activity | Decision 可以启动 / 更新 Activity |
| Activity → Goal | Activity 完成可以反馈 Goal |
| Activity → Commitment | Activity 完成可以反馈 Commitment |

### 10.3 关键约束

> **Activity 是连续生命周期，Intent 是当前倾向，Decision 是当前选择。三者不能混在一起。**

---

## 11. 案例验证

### 11.1 案例 A：AI 周六答应陪用户过周末

**场景：**

> AI 周六答应陪用户过周末。第二天早上，不能因为随机机制突然移动到另一个地图。

**各层：**

| 概念 | 内容 |
|------|------|
| **Goal** | "陪用户度过周末" |
| **Commitment** | "答应陪用户过周末"（`hard`，用户 → AI） |
| **Motivation** | 上午："用户还在住所，我想继续陪伴。" 下午："天气很好，我想和用户出去走走。" |
| **Intent** | 留在住所 / 准备早餐 / 提议出门 |
| **Decision** | 留在住所 |
| **Activity** | 周末陪伴活动 ACTIVE |
| **Action** | 保持当前位置 / 互动 |
| **Location** | 保持在同一住所 |

**关键结论：**

- 随机机制**不能**覆盖 `hard` Commitment。
- Goal / Commitment 必须跨 Event 持续。
- Motivation 可以随时间和状态变化。

### 11.2 案例 B：用户说"我受伤了"

**未来链：**

```text
Event（用户消息）
→ Context
→ Motivation（用户受伤，AI 关心，需要帮助）
→ Intent（倾向陪用户去医院）
→ World Query（查询可用医院）
→ Query Result
→ Decision（选择某家医院 + 前往方式）
→ Action（调用现有 ext_* 执行）
→ Activity（医疗陪伴 ACTIVE）
→ World Change（AI 与用户位置变化）
→ Event（location_changed）
```

**C-0 只验证架构是否能够支持它，不实现。**

### 11.3 案例 C：AI 自己想见另一个 AI

**场景：**

> AI 自己想见另一个 AI。不是用户要求。

**分析：**

| 问题 | 回答 |
|------|------|
| Goal 从哪里来？ | 从 AI 自身长期偏好 / 愿望推导（允许来源之一） |
| Motivation 从哪里来？ | 从 Goal + State + Relationship + World Conditions 计算 |
| Intent 是什么？ | "想去找 AI B" / "想约 AI B 见面" |
| 是否需要 Commitment？ | 不一定；若是 AI A 对 AI B 的承诺，则需要 |
| 如何通过 Event / World 实现 AI↔AI？ | AI A → Decision → Action → Event → AI B RECEIVE → PERCEIVE |
| 是否允许 AI A 直接调用 AI B Brain？ | **不允许** |

**正确链：**

```text
AI A
→ Decision
→ Action
→ Event
→ AI B RECEIVE
→ PERCEIVE
```

**错误链：**

```text
AI A Brain
→ AI B Brain
```

**关键结论：**

- AI 可以有"不是用户要求"的 Goal。
- AI↔AI 必须通过 World / Event。
- AI A 不能直接调用 AI B Brain。

---

## 12. 随机性边界（A + B 类）

### 12.1 允许随机

- 非关键生活细节。
- 候选生成。
- 非关键偏好。
- 偶发记忆唤醒。

### 12.2 禁止随机

- 核心 Goal。
- 核心 Motivation。
- Commitment。
- Commitment 是否兑现。
- 核心 Decision。
- AI 为什么现在做某件重要事情。

### 12.3 关键分析

**"AI 想用户了，所以主动约用户"**

**不能简单写成：**

```python
if random() < 0.08:
    invite()
```

**未来必须能够解释：**

- 为什么想？
- 为什么现在？
- 为什么邀请这个人？
- 为什么选择这个地点？
- 为什么不是其他行为？

**C-0 结论：**

- 随机性只能用于**非关键细节**。
- 核心因果必须来自 Goal / Commitment / Motivation。

---

## 13. 持久化 / Source of Truth

### 13.1 各概念的持久性分类（B 类）

| 概念 | 性质 | 建议持久化 |
|------|------|-----------|
| **Goal** | 持久事实 | 待 C-1 冻结 |
| **Commitment** | 持久事实 | 待 C-1 冻结 |
| **Intent** | 临时推理结果 | 不持久化 |
| **Motivation** | 动态计算结果 | 不持久化 |
| **Event** | 事实 | 现有 Event 模型 |
| **State** | Projection | 不持久化（只读投影） |

### 13.2 与 main.data / AgentState / Memory 的关系

| 概念 | main.data | AgentState | Memory |
|------|-----------|------------|--------|
| Goal | ❌ 不写入 | ❌ 不是字段 | ⚠️ 可从 Memory 推导 |
| Commitment | ❌ 不写入 | ❌ 不是字段 | ⚠️ 可从 Memory 推导 |
| Intent | ❌ 不写入 | ❌ 不是字段 | ❌ 不相关 |
| Motivation | ❌ 不写入 | ⚠️ State 是输入 | ⚠️ 可从 Memory Recall 推导 |

### 13.3 【当前可以冻结的架构事实】（A 类）

1. `main.data` 仍是唯一 Source of Truth。
2. Goal / Commitment 必须跨 Event 持续存在。
3. Goal / Commitment 不写入 `main.data`。
4. Intent / Motivation 不持久化。
5. Intent 不产生副作用。
6. THINK → Intent candidates → Decision → Action 严格分离。
7. World Query 是无副作用信息查询。
8. `hard` Commitment 不可被随机性覆盖。
9. 随机性不能作为核心 Goal / Motivation / Decision 因果。
10. AI↔AI 必须通过 World / Event。
11. AI A 不能直接调用 AI B Brain。
12. AI 必须未来能够存在自己的生活目标。
13. Goal / Commitment 状态转换必须单向、可审计、不直接修改 `main.data`。

### 13.4 【必须留到后续 Contract Change 决定的问题】（D 类）

1. Goal 最终持久化位置。
2. Commitment 最终持久化位置。
3. Goal 优先级算法。
4. Goal 冲突解决规则。
5. Commitment 强度分级的最终定义。
6. Intent 最终数据结构。
7. Motivation 计算输入范围。
8. Decision 最终接口。
9. Goal / Commitment 是否需要独立数据库。
10. Goal / Commitment 是否需要独立文件。
11. Goal / Commitment 是否复用 `main.data`。
12. Goal / Commitment 是否使用 SQLite / JSON / 内存。
13. Goal / Commitment 与 Relationship 的接口。
14. Goal / Commitment 与 Memory 的接口。
15. Goal / Commitment 与 Activity Lifecycle 的接口。

---

## 14. 禁止提前解决的问题（E 类）

C-0 不要偷偷解决：

- Memory。
- Relationship 数据库。
- Scheduler。
- World Query 实现。
- Activity Runtime。
- AI↔AI autonomous loop。
- Prompt Adapter。
- LLM。
- TTS。
- VoiceStudio。
- SNS。
- Local Chat Archive。
- 多 World / Multi-tenant。

这些只讨论接口关系，**不实现**。

---

## 15. A/B/C/D/E 五类总结

### A. 已冻结架构事实

- §1.2 全部 20 条。
- §1.3 B6 已冻结的定义。
- §1.4 B6 已冻结的边界。
- §3.4 Goal 跨 Event 持续要求。
- §3.6 Goal 禁止随机生成。
- §4.6 Commitment 与 Goal 的关系（部分）。
- §6.6 Motivation 核心因果不能随机。
- §7.10 THINK → Intent → Decision → Action 链。
- §9 World Query 无副作用。
- §12.2 禁止随机清单。
- §13.3 全部 13 条。

### B. C-0 新提出的设计候选

- §3.1 Goal 数据结构草案。
- §3.2 Goal 生命周期。
- §3.3 Goal 多并存、优先级、冲突。
- §3.5 Goal 来源七类。
- §4.1 Commitment 数据结构草案。
- §4.2 四类承诺。
- §4.3 Commitment 生命周期。
- §4.4 创建 / 完成 / 取消 / 过期 / 冲突。
- §4.5 强度三级。
- §4.7 Commitment 与 Activity。
- §5 Goal 与 Commitment 关系。
- §6 Motivation 动态计算结果。
- §7 Intent 数据结构草案。
- §8 Decision 边界。
- §10 Activity 与 Goal / Commitment / Intent。
- §11 三个案例。
- §13.1 持久性分类。

### C. 推荐方案

- §3.3 允许 Goal 多并存（推荐）。
- §3.5 Goal 来源七类（推荐）。
- §4.5 强度三级（推荐）。
- §6.1 Motivation 动态计算结果（推荐）。
- §6.2 Motivation 不需要 ID（推荐）。
- §6.3 Motivation 不需要保存（推荐）。
- §7.7 Intent 不持久化（推荐）。
- §7.8 Intent 不跨 Event 存活（推荐）。
- §13.3 可冻结架构事实（推荐）。

### D. 尚未冻结的问题

- §13.4 全部 15 条。

### E. 禁止本阶段实现的内容

- §14 全部。
- §16 全部。

---

## 16. C-0 禁止事项

### 修改类

- ❌ 修改任何 `.py`。
- ❌ 修改 `docs/V3.1_ARCHITECTURE_CONTRACT.md`。
- ❌ 修改 `main.py`。
- ❌ 修改任何 `ext_*.py`。
- ❌ 修改前端。
- ❌ 修改 Memory。

### 实现类

- ❌ 实现 Goal。
- ❌ 实现 Commitment。
- ❌ 实现 Motivation。
- ❌ 实现 Intent。
- ❌ 实现 THINK。
- ❌ 实现 Decision。
- ❌ 实现 Action。
- ❌ 实现 World Query。
- ❌ 实现 Activity。
- ❌ 实现 Scheduler。
- ❌ 实现 AI↔AI。
- ❌ 接 LLM。
- ❌ 写 Prompt。
- ❌ 启用 Memory Runtime。
- ❌ 创建 Goal / Commitment 持久化文件 / 数据库。
- ❌ 修改 `main.data`。

### 阶段纪律类

- ❌ 进入 C-1 / C-2 编码。
- ❌ 冻结最终数据结构（本阶段）。
- ❌ 冻结 Goal / Commitment 持久化位置（本阶段）。
- ❌ 跳过架构审核。
- ❌ 删除 / 改名 / 别名化 `ContextLayers`。

---

## 17. 下一阶段建议

### 17.1 不建议直接进入 C-1 编码

理由：

1. Goal 持久化位置尚未冻结。
2. Commitment 持久化位置尚未冻结。
3. Intent 最终结构尚未冻结。
4. Goal 优先级 / 冲突规则尚未冻结。
5. Commitment 强度分级尚未最终确认。
6. Motivation 计算输入范围尚未冻结。
7. Decision 最终接口尚未冻结。

### 17.2 建议的下一步

**C-1 Contract Change。**

内容：

1. 把 C-0 的 A 类事实写入 `docs/V3.1_ARCHITECTURE_CONTRACT.md`。
2. 把 C-0 的 C 类推荐方案中、经架构审核通过的，写入 Contract。
3. 明确 D 类问题的解决顺序。
4. 不修改任何 `.py`。

### 17.3 不建议的顺序

- ❌ 先实现 THINK。
- ❌ 先接 LLM。
- ❌ 先实现 Decision。
- ❌ 先实现 Action。
- ❌ 先启用 Memory。

---

## 18. C-0 完成确认

> **C-0 只完成 Goal / Motivation / Commitment / Intent 架构预检。**
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
> **C-0 没有实现 Goal / Motivation / Commitment / Intent / THINK / Decision / Action / Brain / Activity / World Query / Scheduler / AI↔AI。**
> **C-0 没有接 LLM / 网络。**
> **C-0 没有启用 Memory Runtime。**
> **C-0 没有创建 Goal / Commitment 持久化文件 / 数据库。**
> **C-0 没有冻结最终数据结构。**
> **C-0 没有冻结 Goal / Commitment 持久化位置。**
>
> **C-0 只输出设计决策文档，不进入 C-1 编码。**

---

## 19. 输出物

### 19.1 新增文件

- `docs/C0_GOAL_MOTIVATION_COMMITMENT_INTENT_PREFLIGHT.md`（本文件）

### 19.2 可选更新

- `PROJECT_V3.1_MASTER.md`
  - 只记录 C-0 Preflight 状态
  - 不改动其他内容
  - 不修改任何代码

### 19.3 Commit SHA

- `docs/C0_GOAL_MOTIVATION_COMMITMENT_INTENT_PREFLIGHT.md` Commit SHA：**待提交后填写**
- `PROJECT_V3.1_MASTER.md` Commit SHA（如更新）：**待提交后填写**

### 19.4 PROJECT 修改说明

如更新 PROJECT，仅在以下位置追加：

- 第 0 节：C-0 状态（已完成，待审核）
- 第 20.4 节：Phase C 子阶段状态表（C-0 已完成，C-1 待启动）
- 第 22 节：§22.12 C-0 阶段事实

**不修改其他内容。**

---

**C-0 完成后停止，等待架构审核。不进入 C-1，不进入 B7。**