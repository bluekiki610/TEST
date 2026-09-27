# C-2 GOAL / COMMITMENT IMPLEMENTATION PREFLIGHT

> 本阶段只做架构预检 / 设计文档。
> **未修改任何 `.py`、前端、数据、Memory、Provider、Assembler、Runtime、main、ext_\*、Contract。**
> 完成后停止，等待架构审核。
> **不进入 C-2 implementation，不实现任何逻辑，不接 LLM。**

---

## 0. 文档性质

| 项 | 内容 |
|----|------|
| 阶段 | C-2 Preflight |
| 性质 | Architecture Design（设计阶段，**不是编码**） |
| 依据 | C-0 Preflight（ACCEPTED）+ C-1 Contract Change CC-20260927-01（ACCEPTED） |
| 目标 | 在实现 Goal / Commitment / Motivation / Intent / THINK 前，冻结最小数据结构、生命周期、SOT 关系、边界、实现范围 |
| 禁止 | 不修改 `.py`，不修改 Contract，不实现任何逻辑，不接 LLM，不启用 Memory，不创建数据库 / 持久化文件 |
| 输出 | 本文档 `docs/C2_GOAL_COMMITMENT_IMPLEMENTATION_PREFLIGHT.md` + PROJECT 状态记录（可选） |

**分类约定（与 C-0 一致）：**

- **A. 已冻结架构事实**（不可推翻）
- **B. C-2 Preflight 新提出的设计候选**（未冻结）
- **C. 推荐方案**（仍未冻结）
- **D. 尚未冻结的问题**（留给后续 Contract Change）
- **E. 禁止本阶段实现的内容**

---

## 1. Goal 最小数据结构（B 类）

### 1.1 分析目标

Goal 数据结构必须满足：

- 能表达"我想完成什么"。
- 能表达来源（七类之一）。
- 能跨 Event 持续（见 §3）。
- 能被 Motivation 消费（见 §9）。
- 能关联 Commitment（见 §8）。
- 能被状态机管理（见 §6）。
- **不写入 `main.data`**（SOT-1 / AS-5）。

### 1.2 最小字段候选（B 类）

| 字段 | 是否必需 | 说明 |
|------|---------|------|
| `goal_id` | 必需 | 唯一标识，未来持久化主键候选 |
| `actor` | 必需 | AI 名（一个 AI 一个 Goal 集合） |
| `type` | 必需 | `companionship` / `medical` / `work` / `social` / `personal` / ... |
| `description` | 必需 | 人类可读描述（审计 / 调试用） |
| `source` | 必需 | 七类来源之一（见 §5） |
| `status` | 必需 | `CREATED` / `ACTIVE` / `COMPLETED` / `CANCELLED` / `EXPIRED` |
| `created_at` | 必需 | 创建时间 |
| `updated_at` | 必需 | 最近状态变更时间 |
| `reason` | 必需 | 为什么创建（审计） |
| `target` / `desired_state` | 必需 | 期望达成的状态 |
| `completion_condition` | 必需 | 何时视为完成 |
| `priority` | 可选 | 优先级（算法未冻结，见 §13） |
| `deadline` | 可选 | 截止时间（可为空） |
| `related_commitments` | 可选 | 关联 Commitment IDs |
| `related_activity` | 可选 | 关联 Activity IDs |

### 1.3 明确不包含（E 类）

- ❌ 不包含 `owner` / `data` 引用（SOT-1）。
- ❌ 不包含 Prompt / LLM 输出字段。
- ❌ 不包含 `persisted_at` / `storage_path` 等持久化元字段。
- ❌ 不包含 `mood` / `energy` 等 placeholder。

### 1.4 推荐方案（C 类）

**采纳 §1.2 中标记为"必需"的字段作为最小数据结构。**

`priority` / `deadline` / `related_*` 作为可选字段，允许未来扩展。

---

## 2. Commitment 最小数据结构（B 类）

### 2.1 分析目标

Commitment 数据结构必须满足：

- 能表达"我已经答应什么"。
- 能表达四类承诺（见 §7）。
- 能跨 Event 持续（见 §3）。
- 能约束 Motivation / Decision（见 §9、§10）。
- 能被状态机管理（见 §7）。
- **不写入 `main.data`**（SOT-1 / AS-5）。

### 2.2 最小字段候选（B 类）

| 字段 | 是否必需 | 说明 |
|------|---------|------|
| `commitment_id` | 必需 | 唯一标识 |
| `type` | 必需 | `user_promise` / `ai_promise` / `meeting` / `date` / `implicit` |
| `actor` | 必需 | 承诺方（AI 名 / 用户 / 自己） |
| `counterparty` | 必需 | 被承诺方 |
| `content` | 必需 | 承诺内容 |
| `strength` | 必需 | `hard` / `soft` / `implicit` |
| `status` | 必需 | `CREATED` / `ACTIVE` / `FULFILLED` / `CANCELLED` / `EXPIRED` |
| `created_at` | 必需 | 创建时间 |
| `updated_at` | 必需 | 最近状态变更时间 |
| `reason` | 必需 | 为什么形成（审计） |
| `expires_at` | 可选 | 过期时间（可为空） |
| `linked_goal` | 可选 | 关联 Goal ID |
| `linked_activity` | 可选 | 关联 Activity ID |
| `source` | 可选 | 来源（event / chat / date / meeting） |

### 2.3 明确不包含（E 类）

- ❌ 不包含 `data` 引用。
- ❌ 不包含 Prompt / LLM 输出字段。
- ❌ 不包含持久化元字段。
- ❌ 不包含 `date_invites` / `ai_meeting` 的直接引用（只读语义，见 §17）。

### 2.4 推荐方案（C 类）

**采纳 §2.2 中标记为"必需"的字段作为最小数据结构。**

`expires_at` / `linked_*` / `source` 作为可选字段。

---

## 3. Goal / Commitment 跨 Event 生命周期（B 类）

### 3.1 需求

**已冻结（A 类）：**

- Goal / Commitment **必须能够跨 Event 持续存在**（GO-11、CO-16）。
- 单个 Event **不得**让 Goal / Commitment 无故消失。
- Goal / Commitment **不写入 `main.data`**（SOT-8）。
- 不得产生第二套平行数据库（SOT-10）。

### 3.2 C-2 Preflight 必须回答

- Goal / Commitment 如何在 Event 之间存活？
- 谁持有它们？
- 谁负责状态转换？
- 重启后如何恢复？
- 与 Runtime 的关系？

### 3.3 候选方案（B 类）

| 方案 | 说明 | 优点 | 缺点 |
|------|------|------|------|
| **A. Runtime 内存 + 未来持久化** | 每个 Runtime 内存持有 Goal / Commitment；未来加持久化层 | 简单；不引入新数据源 | 重启丢失；需未来补持久化 |
| **B. 独立 GoalStore / CommitmentStore（未实现）** | 独立存储，未来从 `main.data` 或独立介质加载 | 结构化 | 引入新数据源；需 Contract 变更 |
| **C. 未来从 `main.data` 派生 + 只读投影** | Goal / Commitment 从 `main.data` 现有字段派生 | 单一 SOT | 现有字段不足；需扩展 `main.data` schema |
| **D. 混合方案** | 内存 + 未来 Contract 决定持久化 | 平衡 | 复杂度高 |

### 3.4 推荐方案（C 类）

**C-2 Preflight 建议：**

- **短期（C-2 最小实现）**：Runtime 内存持有，不持久化。
- **长期（后续 Contract Change）**：在 SOT-10 约束下，选择方案 A / B / C / D 之一。
- **C-2 阶段不冻结持久化方案。**

### 3.5 明确不做（E 类）

- ❌ 不创建数据库。
- ❌ 不创建持久化文件。
- ❌ 不修改 `main.data`。
- ❌ 不建立第二套 Source of Truth。

---

## 4. Goal / Commitment 与 `main.data` 的 SOT 关系（A 类）

### 4.1 已冻结（A 类）

| 规则 | 内容 |
|------|------|
| **SOT-1** | `main.data` 是唯一 Source of Truth |
| **SOT-8** | Goal / Commitment 不是 `main.data` 子结构，也不是第二 SOT |
| **SOT-9** | Goal / Commitment 不得与 `main.data` 双向同步 |
| **SOT-10** | 持久化机制**不得**产生第二个与 `main.data` 平行、同等权威的事实源；介质必须在权威性上从属于 `main.data`，或可从 `main.data` 重建 |
| **SOT-11** | 具体实现方案未冻结；最终权威性、重建关系、一致性边界留待后续 Contract Change |

### 4.2 C-2 Preflight 立场

- **C-2 阶段不引入任何持久化。**
- Goal / Commitment 在 C-2 阶段只存在于内存。
- 内存持有不违反 SOT-1（不写入 `main.data`，不建立持久化数据源）。
- 未来持久化必须走 Contract Change。

---

## 5. Goal 创建来源与权限（B 类）

### 5.1 已冻结来源（A 类）

Goal 来源仅限七类（GO-6）：

1. 用户要求。
2. Commitment。
3. Relationship。
4. Memory。
5. 未完成 Activity。
6. 工作 / 日程 / 世界约束。
7. AI 自身长期偏好 / 愿望。

### 5.2 创建权限（B 类）

| 来源 | 谁创建 | 权限 |
|------|--------|------|
| 用户要求 | AI 自己解析用户输入 | AI 自主决定是否形成 Goal |
| Commitment | AI 自己从 Commitment 推导 | Commitment → Goal 是单向 |
| Relationship | AI 自己 | 未来依赖 Relationship 层 |
| Memory | AI 自己 | **当前 Memory 未启用**，不可依赖 |
| 未完成 Activity | AI 自己 | 未来依赖 Activity 层 |
| 工作 / 日程 / 世界约束 | AI 自己从 Context 读取 | 只读 |
| AI 自身长期偏好 / 愿望 | **AI 自己** | 不来自用户 |

### 5.3 关键约束

- **AI 必须未来能够拥有不来自用户要求的生活目标**（GO-10）。
- Goal 创建**必须可审计**（携带 `reason`）。
- Goal 创建**禁止随机**（GO-8）。
- Goal 创建**禁止凭空**（GO-7）。
- Goal 创建**禁止未经验证的 LLM 输出直接生成**（GO-9）。

### 5.4 推荐方案（C 类）

- C-2 最小实现只支持**程序化创建**（由调用方显式调用创建 API）。
- 不引入 LLM 驱动创建。
- 不引入自动创建规则。
- 未来 LLM 驱动创建必须走 Contract Change。

---

## 6. Goal 完成 / 取消 / 过期（B 类）

### 6.1 已冻结状态机（A 类）

```text
CREATED → ACTIVE → COMPLETED
              │
              ├──→ CANCELLED
              │
              └──→ EXPIRED
```

### 6.2 转换触发（B 类）

| 转换 | 触发条件 | 权限 |
|------|---------|------|
| `CREATED → ACTIVE` | 显式激活 | 调用方 |
| `ACTIVE → COMPLETED` | `completion_condition` 满足 | 调用方显式调用 |
| `ACTIVE → CANCELLED` | 显式取消（带 `reason`） | 调用方 |
| `ACTIVE → EXPIRED` | 超过 `deadline` | 显式调用（不自动） |
| `CREATED → CANCELLED` | 显式取消 | 调用方 |

### 6.3 约束

- 状态转换**单向**（GO-2）。
- 状态转换**可审计**（GO-3）。
- 状态转换**不直接修改 `main.data`**（GO-4）。
- **不自动过期**（C-2 阶段），过期由调用方显式触发。

### 6.4 推荐方案（C 类）

- C-2 最小实现提供**显式状态转换 API**。
- 不实现自动过期。
- 不实现自动完成检测。
- 未来可引入 Scheduler 触发（Phase D / F）。

---

## 7. Commitment 创建 / 履行 / 取消 / 过期（B 类）

### 7.1 已冻结状态机（A 类）

```text
CREATED → ACTIVE → FULFILLED
              │
              ├──→ CANCELLED
              │
              └──→ EXPIRED
```

### 7.2 转换触发（B 类）

| 转换 | 触发条件 | 权限 |
|------|---------|------|
| `CREATED → ACTIVE` | 显式激活 | 调用方 |
| `ACTIVE → FULFILLED` | 承诺条件满足 | 调用方显式调用 |
| `ACTIVE → CANCELLED` | 显式取消（带 `reason`） | 调用方 |
| `ACTIVE → EXPIRED` | 超过 `expires_at` | 显式调用（不自动） |
| `CREATED → CANCELLED` | 显式取消 | 调用方 |

### 7.3 强度与约束（A 类）

- 四类承诺：AI→用户 / 用户→AI / AI→AI / AI→自己。
- 强度：`hard` / `soft` / `implicit`。
- `hard` 在正常 Decision 中不可被普通随机性 / 低优先级偏好覆盖。
- `hard` **可以**被世界硬约束 / 更高强度用户承诺覆盖；覆盖必须可审计（CO-10、CO-11）。

### 7.4 约束

- 状态转换**单向**（CO-4）。
- 状态转换**可审计**（CO-5）。
- 状态转换**不直接修改 `main.data`**（CO-6）。
- 用户承诺**不得**被 AI↔AI 承诺覆盖（CO-7）。
- AI↔AI 承诺**不得**被随机性覆盖（CO-8）。
- AI 对自己的承诺**不得**被随机性覆盖（CO-9）。

### 7.5 推荐方案（C 类）

- C-2 最小实现提供**显式状态转换 API**。
- 不实现自动过期。
- 不实现自动履行检测。
- 不实现跨 AI 承诺协商。

---

## 8. Goal 与 Commitment 的关系（B 类）

### 8.1 已冻结（A 类）

| 规则 | 内容 |
|------|------|
| **CO-12** | Commitment 可以产生 Goal |
| **CO-13** | Commitment 可以约束 Motivation / Decision |
| **CO-14** | Goal **不能**反向修改 Commitment |

### 8.2 C-2 Preflight 必须回答

- Commitment → Goal 是自动还是显式？
- Goal 与 Commitment 冲突时怎么办？
- 多个 Commitment 关联同一 Goal 时怎么办？

### 8.3 候选方案（B 类）

| 方案 | Commitment → Goal | 冲突处理 |
|------|-------------------|---------|
| **A. 自动** | Commitment 创建时自动生成 Goal | Commitment 优先 |
| **B. 显式** | 调用方显式创建 Goal | Commitment 优先 |
| **C. 半自动** | Commitment 创建时提供候选 Goal，调用方确认 | Commitment 优先 |

### 8.4 推荐方案（C 类）

- C-2 最小实现采用**方案 B（显式）**。
- Commitment 创建**不自动**生成 Goal。
- 冲突处理：**Commitment 优先**（CO-14 延伸）。
- 多个 Commitment 关联同一 Goal：允许多对一。

---

## 9. Goal / Commitment 如何进入 Motivation（B 类）

### 9.1 已冻结（A 类）

| 规则 | 内容 |
|------|------|
| **MO-8** | Motivation 计算输入包括：Goal / Commitment / State / Relationship / Recent Experience / World Conditions |
| **MO-1** | Motivation 是动态计算结果，不是持久状态 |
| **MO-3** | Motivation 不持久化 |
| **MO-6** | Motivation 核心因果不允许由随机概率产生 |

### 9.2 C-2 Preflight 必须回答

- Motivation 是函数还是对象？
- Motivation 在哪里被调用？
- Motivation 的输出是什么？
- Motivation 如何被 THINK 消费？

### 9.3 候选方案（B 类）

| 方案 | Motivation 形式 | 调用位置 |
|------|-----------------|---------|
| **A. 纯函数** | `compute_motivation(goal, commitment, state, ...)` → 摘要字符串 / 结构化对象 | THINK 内部 |
| **B. 独立对象** | `Motivation` dataclass | THINK 内部 |
| **C. 由 Provider 计算** | Provider 输出 Motivation 摘要 | Context Assembly |

### 9.4 推荐方案（C 类）

- C-2 最小实现采用**方案 A（纯函数）**。
- Motivation **不进入 Context**（MO-3：不持久化）。
- Motivation 在 THINK 内部计算。
- Motivation 输出结构化摘要（不是原始 `str`）。

### 9.5 明确不做（E 类）

- ❌ 不实现 Motivation 计算。
- ❌ 不实现 Motivation 持久化。
- ❌ 不把 Motivation 注入 Context。

---

## 10. Motivation 如何进入 THINK（B 类）

### 10.1 已冻结（A 类）

- THINK 输入：`AgentContext`。
- THINK 输出：Intent candidates。
- `think(context) -> Optional[str]` 是 B5 临时占位，**不代表最终 Intent Contract**（IN-14）。

### 10.2 C-2 Preflight 必须回答

- Motivation 在 THINK 内部如何生成？
- Motivation 如何转换为 Intent candidates？
- THINK 的输出结构是什么？

### 10.3 候选方案（B 类）

| 方案 | THINK 输出 |
|------|-----------|
| **A. 保留 `Optional[str]`** | 不满足 IN-1（结构化） |
| **B. 引入 `IntentSet`** | 满足 IN-1 ～ IN-3 |
| **C. 引入 `ThinkResult`** | 包含 IntentSet + 审计信息 |

### 10.4 推荐方案（C 类）

- C-2 最小实现采用**方案 B（`IntentSet`）**。
- THINK 签名更新为 `think(context: AgentContext) -> IntentSet`。
- 签名更新需要 Contract Change（见 §12）。

### 10.5 明确不做（E 类）

- ❌ 不实现 THINK 内部逻辑。
- ❌ 不调用 LLM。
- ❌ 不实现 Prompt Adapter。

---

## 11. Intent 最终结构（B 类）

### 11.1 已冻结（A 类）

| 规则 | 内容 |
|------|------|
| **IN-1** | Intent 是结构化对象 |
| **IN-2** | Intent 必须可审计 |
| **IN-3** | Intent 必须携带 Motivation / reason |
| **IN-7** | Intent 不持久化 |
| **IN-8** | Intent 不跨 Event 存活 |
| **IN-13** | Intent 最终数据结构未冻结 |

### 11.2 最小字段候选（B 类）

| 字段 | 是否必需 | 说明 |
|------|---------|------|
| `intent_id` | 必需 | 唯一标识 |
| `actor` | 必需 | AI 名 |
| `action_type` | 必需 | 倾向的动作类型 |
| `target` | 可选 | 目标（人 / 地点 / 物体） |
| `reason` | 必需 | Motivation 摘要 |
| `source_goal` | 可选 | 关联 Goal ID |
| `source_commitment` | 可选 | 关联 Commitment ID |
| `constraints` | 可选 | 约束列表 |
| `confidence` | 可选 | 置信度 |
| `candidate_rank` | 可选 | 候选排序 |
| `created_at` | 必需 | 创建时间 |

### 11.3 `IntentSet` 结构（B 类）

```text
IntentSet
├── actor
├── created_at
├── candidates: List[Intent]
└── reason_summary
```

### 11.4 推荐方案（C 类）

- 采纳 §11.2 必需字段 + §11.3 `IntentSet`。
- `IntentSet.candidates` 至少一个。
- 不引入 `Decision` 字段（IN-11）。

### 11.5 明确不做（E 类）

- ❌ 不实现 Intent 数据结构。
- ❌ 不实现 IntentSet。
- ❌ 不冻结最终 schema（IN-13）。

---

## 12. THINK 从 `Optional[str]` 到结构化 Intent 的迁移方案（B 类）

### 12.1 当前状态（A 类）

```python
def think(self, context: AgentContext) -> Optional[str]:
    ...
```

- 是 B5 临时占位（IN-14）。
- 不代表最终 Intent Contract。
- 行为仍为 Stub。

### 12.2 迁移目标（B 类）

```python
def think(self, context: AgentContext) -> IntentSet:
    ...
```

### 12.3 迁移步骤（B 类）

1. **C-2 Preflight**：设计 `IntentSet`（本文件）。
2. **C-2 Contract Change**：把 `IntentSet` 写入 Contract。
3. **C-2 Implementation**：更新 `think()` 签名 + 返回 `IntentSet`（仍不调用 LLM）。
4. **C-2 Tests**：验证签名 + 返回类型。
5. **C-2 PROJECT Update**。

### 12.4 兼容性

- `think()` 目前**无调用者**（PROJECT §22.3）。
- 签名变更**不影响**现有代码。
- 保留 `Optional[str]` 到结构化 Intent 的**单向迁移**。
- 不允许双向兼容。

### 12.5 推荐方案（C 类）

- 采用**直接替换**（无兼容层）。
- `think()` 返回 `IntentSet`。
- 空 `IntentSet` 表示"无候选"。
- 不引入 `None` 返回值（避免歧义）。

---

## 13. Goal / Commitment 的并发与冲突问题（B 类）

### 13.1 并发场景

| 场景 | 说明 |
|------|------|
| 多个 Goal 同时 `ACTIVE` | 允许（GO-5） |
| 多个 Commitment 同时 `ACTIVE` | 允许 |
| 多个 Event 同时触发 | Runtime 每次独立处理 |
| AI↔AI 同时形成 Commitment | 需 Event 隔离 |

### 13.2 冲突场景

| 冲突 | 处理 |
|------|------|
| Goal vs Goal | 优先级（未冻结，GO-12） |
| Commitment vs Commitment | 用户承诺优先；强度优先 |
| Goal vs Commitment | Commitment 优先（CO-14） |
| Commitment vs World | 世界硬约束优先（CO-11） |
| AI Goal vs 用户 Goal | 用户要求不自动覆盖 AI 核心 Goal（GO-10） |

### 13.3 并发控制（B 类）

| 方案 | 说明 |
|------|------|
| **A. 单线程 Runtime** | 每个 AI 一个 Runtime，内部串行 |
| **B. 锁** | 未来多线程时加锁 |
| **C. 事件队列** | 未来 Scheduler 层保证顺序 |

### 13.4 推荐方案（C 类）

- C-2 最小实现采用**方案 A（单线程 Runtime）**。
- 不引入锁。
- 不引入事件队列。
- 未来多线程由 Scheduler 层处理（Phase D / F）。

---

## 14. AI 自主 Goal 与用户 Goal 的边界（B 类）

### 14.1 已冻结（A 类）

- AI 必须未来能够拥有**不来自用户要求**的生活目标（GO-10）。
- 用户要求是 Goal 来源之一，但不是唯一来源。
- 用户要求**不自动覆盖** AI 核心 Goal。

### 14.2 边界（B 类）

| 维度 | AI 自主 Goal | 用户 Goal |
|------|-------------|-----------|
| 来源 | AI 自身长期偏好 / 愿望 | 用户明确表达 |
| 权限 | AI 自己 | AI 自己解析用户输入 |
| 冲突处理 | 用户要求不自动覆盖 AI 核心 Goal | 显式权衡 |
| 审计 | 必须携带 `reason` | 必须携带 `reason` |

### 14.3 推荐方案（C 类）

- C-2 最小实现**不实现自动推导**。
- Goal 由调用方显式创建。
- 未来自动推导必须走 Contract Change。

---

## 15. 与 Activity 的关系（B 类）

### 15.1 已冻结（A 类）

| 规则 | 内容 |
|------|------|
| **CO-15** | Commitment 可以关联 Activity，但 Commitment ≠ Activity |
| **AC-1** | Activity 本阶段不实现 |
| **AC-2** | 不修改现有 `work_sessions` / `dates` / `ai_shop_state` / `instances` |

### 15.2 C-2 Preflight 立场

- C-2 不实现 Activity。
- Goal / Commitment 可以有 `related_activity` 字段（未来使用）。
- 不修改现有 Activity 相关字段。

### 15.3 推荐方案（C 类）

- C-2 最小实现中 `related_activity` 字段**保留为空**。
- 未来 Activity 实现后再填充。

---

## 16. 与 Memory 的未来关系（B 类）

### 16.1 已冻结（A 类）

| 规则 | 内容 |
|------|------|
| **ME-12** | Memory Runtime 当前未启用 |
| **ME-13** | `LongTermProvider` 当前返回 `[]` |
| **ME-14** | Goal 不得假设当前可以从 Memory 产生 |
| **ME-15** | 只定义未来接口关系 |

### 16.2 C-2 Preflight 立场

- C-2 不实现 Memory。
- C-2 不假设 Memory 已可产生 Goal。
- Goal 来源中的"Memory"类**当前不可用**。
- 未来 Memory → Recall → LongTermProvider → ContextAssembler → AgentContext → THINK 链路保持。

### 16.3 推荐方案（C 类）

- C-2 最小实现中 Goal 来源**只支持**：用户要求 / Commitment / 工作日程世界约束 / AI 自身长期偏好。
- 其他来源（Relationship / Memory / Activity）留待后续阶段。

---

## 17. 与现有 `ext_*` 的边界（A 类）

### 17.1 已冻结（A 类）

- 不修改任何 `ext_*.py`。
- 不修改 `main.py`。
- 不修改 `date_invites` / `date_invites_out` / `ai_meeting`。
- 不修改 `work_sessions` / `dates` / `ai_shop_state` / `instances`。
- `ext_ai` 不重写、不删除。
- `ext_ai.build_ai_context` 不接入 V3.1 正式链。

### 17.2 C-2 Preflight 立场

- C-2 最小实现**不调用** `ext_*`。
- Goal / Commitment 是 Agent 层概念，与 `ext_*` 无直接交互。
- 未来交互通过 Action 层（Phase F）。

### 17.3 推荐方案（C 类）

- C-2 最小实现完全独立于 `ext_*`。

---

## 18. 最小实现范围（B 类）

### 18.1 C-2 Implementation 候选范围

| 项 | 是否实现 | 说明 |
|----|---------|------|
| Goal 数据结构 | ✅ | 最小字段 |
| Commitment 数据结构 | ✅ | 最小字段 |
| Goal 状态机 | ✅ | 显式转换 |
| Commitment 状态机 | ✅ | 显式转换 |
| Goal / Commitment 内存持有 | ✅ | Runtime 内存 |
| Motivation 纯函数 | ✅ | 结构化摘要 |
| IntentSet 结构 | ✅ | 最小字段 |
| THINK 签名更新 | ✅ | `-> IntentSet` |
| THINK 内部逻辑 | ❌ | 仍 Stub |
| LLM 调用 | ❌ | 禁止 |
| Prompt Adapter | ❌ | 禁止 |
| Memory | ❌ | 禁止 |
| Activity | ❌ | 禁止 |
| World Query | ❌ | 禁止 |
| Decision | ❌ | 禁止 |
| Action | ❌ | 禁止 |
| Scheduler | ❌ | 禁止 |
| AI↔AI | ❌ | 禁止 |
| 持久化 | ❌ | 禁止 |
| 数据库 | ❌ | 禁止 |

### 18.2 推荐方案（C 类）

- C-2 最小实现只做**数据结构 + 状态机 + 纯函数**。
- 不接 Runtime 之外的系统。
- 不接 LLM / Memory / Activity / World Query / Decision / Action。
- 不修改 `main.data`。

### 18.3 C-2 Implementation 禁止事项（E 类）

- ❌ 创建数据库。
- ❌ 创建持久化文件。
- ❌ 修改 `main.py`。
- ❌ 修改任何 `ext_*`。
- ❌ 修改 Runtime（除非 Contract Change 通过）。
- ❌ 实现 Goal / Commitment / Motivation / Intent / THINK 内部逻辑。
- ❌ 接 LLM / Memory / Activity / World Query / Decision / Action / Scheduler / AI↔AI。

---

## 19. 需要 Contract Change 的项（D 类）

C-2 Implementation 前必须走 Contract Change 的项：

| 项 | 说明 |
|----|------|
| `think()` 签名更新 | `-> Optional[str]` → `-> IntentSet` |
| `IntentSet` 结构 | 冻结最小字段 |
| `Intent` 结构 | 冻结最小字段 |
| Goal 数据结构 | 冻结最小字段 |
| Commitment 数据结构 | 冻结最小字段 |
| Motivation 纯函数签名 | 冻结输入 / 输出 |
| Goal / Commitment 内存持有 | 明确不违反 SOT-1 |
| Goal / Commitment 持久化 | 明确 C-2 不持久化 |

---

## 20. 未冻结的问题（D 类）

- Goal 最终持久化位置。
- Commitment 最终持久化位置。
- Goal 优先级算法。
- Goal 冲突解决规则。
- Motivation 计算输入范围。
- Decision 最终接口。
- Activity 生命周期细节。
- World Query 接口细节。
- Scheduler 接口细节。
- AI↔AI Commitment 协商机制。
- 用户 Goal vs AI Goal 自动权衡规则。

---

## 21. C-2 Preflight 禁止事项（E 类）

### 修改类

- ❌ 修改任何 `.py`。
- ❌ 修改 `docs/V3.1_ARCHITECTURE_CONTRACT.md`。
- ❌ 修改 `main.py`。
- ❌ 修改任何 `ext_*.py`。
- ❌ 修改前端。
- ❌ 修改 Memory。
- ❌ 修改 Runtime。

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
- ❌ 创建数据库 / 持久化文件。
- ❌ 修改 `main.data`。

### 阶段纪律类

- ❌ 进入 C-2 implementation。
- ❌ 跳过架构审核。
- ❌ 冻结最终数据结构（本阶段）。
- ❌ 冻结 Goal / Commitment 持久化位置（本阶段）。

---

## 22. 下一阶段建议

### 22.1 C-2 Preflight 完成后

**建议顺序：**

1. **C-2 Contract Change**：把 C-2 Preflight 中经架构审核通过的项写入 Contract。
2. **C-2 Implementation**：最小实现（数据结构 + 状态机 + 纯函数 + `think()` 签名）。
3. **C-2 Tests**。
4. **C-2 PROJECT Update**。

### 22.2 不建议的顺序

- ❌ 直接实现 THINK 内部逻辑。
- ❌ 直接接 LLM。
- ❌ 直接启用 Memory。
- ❌ 直接实现 Decision / Action。

### 22.3 前置条件

C-2 Implementation 前必须：

- C-2 Preflight 审核通过。
- C-2 Contract Change 审核通过。
- 明确 `think()` 签名更新。
- 明确 `IntentSet` / `Intent` 最小结构。
- 明确 Goal / Commitment 内存持有不违反 SOT-1。

---

## 23. C-2 Preflight 完成确认

> **C-2 Preflight 只完成 Goal / Commitment 实现架构预检。**
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
> **未实现 Goal / Commitment / Motivation / Intent / THINK / Decision / Action / Brain / Activity / World Query / Scheduler / AI↔AI。**
> **未接 LLM / 网络。**
> **未启用 Memory Runtime。**
> **未创建数据库 / 持久化文件。**
> **未进入 C-2 implementation。**

---

## 24. 输出物

### 24.1 新增文件

- `docs/C2_GOAL_COMMITMENT_IMPLEMENTATION_PREFLIGHT.md`（本文件）

### 24.2 可选更新

- `PROJECT_V3.1_MASTER.md`
  - 只记录 C-2 Preflight 状态
  - 不改动其他内容
  - 不修改任何代码

### 24.3 Commit SHA

- `docs/C2_GOAL_COMMITMENT_IMPLEMENTATION_PREFLIGHT.md` Commit SHA