# C-3 Tests Preflight Report

> 本阶段只做测试架构预审（Preflight）。
> **未修改任何 `.py`、Contract、PROJECT、前端、Memory、ext_\*。**
> **未新增任何测试代码。**
> 完成后停止，等待架构审核。

---

## 1. C-3 目标

C-3 的定位：

> **C-3 = 对 C-2 已封板实现进行契约一致性、边界隔离、回归安全、行为可验证性的测试架构设计。**

**C-3 Preflight 只设计测试矩阵，不写测试代码。**

C-3 要证明：

- C-2 已冻结的 Contract 是否准确、可测试、无越界、无回归。
- Runtime Holder 是否真正 Runtime-owned。
- 边界（SOT / LLM / Persistence / ext_* / Memory）是否守住。

C-3 不证明：

- AI 已经会真正思考。
- AI 已能自动产生 Goal / Commitment / Motivation / Intent。
- Decision / Action / Activity / World Query / Scheduler / AI↔AI 已存在。
- Memory 已恢复。
- Goal / Commitment 已持久化。
- LLM 已接入 THINK。

---

## 2. 当前测试对象清单

| 对象 | 文件 | 类型 | 冻结依据 |
|------|------|------|---------|
| `Goal` / `create_goal` / `transition_goal` | `agent/goal.py` | dataclass + 函数 | §5B.1 / §5B.3 |
| `Commitment` / `create_commitment` / `transition_commitment` | `agent/commitment.py` | dataclass + 函数 | §5B.2 / §5B.3 |
| `MotivationSummary` / `compute_motivation` | `agent/motivation.py` | dataclass + 纯函数 | §5B.8 |
| `Intent` / `IntentSet` / `make_intent` / `make_empty_intent_set` | `agent/intent.py` | dataclass + 函数 | §5B.9 / §5B.10 |
| `AgentRuntime` holder（`_goals` / `_commitments`） | `agent/runtime.py` | 私有状态 + 8 方法 | §5B.5 / §5B.15 / §5B.16 |
| `AgentRuntime.think()` | `agent/runtime.py` | 方法（Stub） | §5B.11 |
| `AgentRuntime.build_context()` | `agent/runtime.py` | 方法（B5-2 已连接） | CC-20260926-01 |

---

## 3. T-A Contract Structure（测试设计）

**目的**：验证 C-2 冻结的结构在代码中真实存在且可被测试明确表达。

| ID | 测试内容 | 依据 |
|----|---------|------|
| A1 | `agent/goal.py` / `commitment.py` / `motivation.py` / `intent.py` / `runtime.py` 存在 | §5B.1 ～ §5B.16 |
| A2 | `Goal` 必需字段与 §5B.1 一致 | §5B.1 GO-14 |
| A3 | `Commitment` 必需字段与 §5B.2 一致 | §5B.2 CO-18 |
| A4 | Goal 生命周期 = `CREATED → ACTIVE → {COMPLETED, CANCELLED, EXPIRED}` | §5B.3 |
| A5 | Commitment 生命周期 = `CREATED → ACTIVE → {FULFILLED, CANCELLED, EXPIRED}` | §5B.3 |
| A6 | 4 个新文件不 `import main` / `ext_*` / `random` / LLM 库 | §5B.13 |
| A7 | `runtime.py` 的 `think()` 签名为 `-> IntentSet` | §5B.11 IN-29 |
| A8 | `runtime.py` 无 `call_llm` / `drive_ai` / `build_ai_context` | §5B.15 |
| A9 | `ContextLayers` 保留为 deprecated stub，未删除 / 改名 / 别名化 | CC-20260926-01 CA-7 |
| A10 | `context.py` / `context_assembler.py` / `state.py` / `event.py` / 任何 Provider / `main.py` / `ext_*` 未被 C-2 修改 | §5B.13 |

---

## 4. T-B Goal（测试设计）

| ID | 测试内容 | 依据 |
|----|---------|------|
| B1 | `create_goal()` 正常创建；返回 `Goal` | §5B.1 |
| B2 | 必需字段完整：`goal_id` / `actor` / `type` / `description` / `source` / `status` / `created_at` / `updated_at` / `reason` / `target` / `completion_condition` | §5B.1 |
| B3 | 初始状态 `CREATED` | §5B.3 |
| B4 | 空 `actor` / `source` / `reason` / `completion_condition` 被拒绝 | §5B.1 |
| B5 | 合法转换 `CREATED → ACTIVE` / `ACTIVE → COMPLETED` / `ACTIVE → CANCELLED` / `ACTIVE → EXPIRED` | §5B.3 LC-9 |
| B6 | 非法转换 `COMPLETED → ACTIVE` / `CANCELLED → ACTIVE` / `EXPIRED → ACTIVE` / `CREATED → COMPLETED` 被拒绝 | §5B.3 |
| B7 | 状态转换**单向**且**不修改原对象** | §5B.3 LC-12 |
| B8 | `updated_at` 随转换更新；`created_at` 不变 | §5B.1 |
| B9 | `goal_id` 由系统生成（`uuid`），唯一 | §5B.1 |
| B10 | `source` 字段只记录调用方声明，不做自动检测 | §5B.4 GO-29 ～ GO-31 |
| B11 | 无自动创建：`goal.py` 不监听事件 / 不扫描 data / 不调用其他模块 | §5B.4 GO-22 ～ GO-28 |
| B12 | Runtime `add_goal` / `get_goal` / `list_goals` / `replace_goal` | §5B.16 |
| B13 | `add_goal` 重复 ID → `GoalAlreadyExists` | §5B.16 RS-33 |
| B14 | `replace_goal` 不存在 ID → `GoalNotFound` | §5B.16 RS-34 |
| B15 | `get_goal` / `list_goals` 返回副本；外部改字段不穿透 holder | §5B.16 RS-18（hardening 版） |
| B16 | 唯一允许的状态变化路径：`transition_goal() → replace_goal()`；Runtime 不自动 transition | §5B.16 RS-32 |

---

## 5. T-C Commitment（测试设计）

| ID | 测试内容 | 依据 |
|----|---------|------|
| C1 | `create_commitment()` 正常创建；返回 `Commitment` | §5B.2 |
| C2 | 必需字段完整：`commitment_id` / `type` / `actor` / `counterparty` / `content` / `strength` / `status` / `created_at` / `updated_at` / `reason` | §5B.2 |
| C3 | 初始状态 `CREATED` | §5B.3 |
| C4 | 合法 `type` / 非法 `type` | §5B.2 |
| C5 | 合法 `strength`（`hard` / `soft` / `implicit`） / 非法 `strength` | §5B.2 |
| C6 | `is_hard()` 正确 | §5A.2 |
| C7 | 合法转换 `CREATED → ACTIVE` / `ACTIVE → FULFILLED` / `ACTIVE → CANCELLED` / `ACTIVE → EXPIRED` | §5B.3 |
| C8 | 非法转换被拒绝 | §5B.3 |
| C9 | **`hard` Commitment 从 `ACTIVE` → `CANCELLED` 应当被允许**（不是"永远不可违背"） | §5A.2 CO-11 |
| C10 | 状态转换**单向**且**不修改原对象** | §5B.3 LC-12 |
| C11 | 无 AI↔AI negotiation：`commitment.py` 无 `negotiate` / `peer` 相关代码 | §5A.2 / §5B.14 |
| C12 | Runtime `add_commitment` / `get_commitment` / `list_commitments` / `replace_commitment` | §5B.16 |
| C13 | `add_commitment` 重复 ID → `CommitmentAlreadyExists` | §5B.16 RS-33 |
| C14 | `replace_commitment` 不存在 ID → `CommitmentNotFound` | §5B.16 RS-34 |
| C15 | `get_commitment` / `list_commitments` 返回副本；外部改字段不穿透 holder | §5B.16 RS-18（hardening 版） |
| C16 | 唯一允许的状态变化路径：`transition_commitment() → replace_commitment()`；Runtime 不自动 transition | §5B.16 RS-32 |

**C-3 特别声明**：`hard` Commitment 目前只是**约束语义**，C-3 **不实现** Decision / 冲突解决。C9 只测试"允许被 CANCELLED"，**不测试**"谁在什么条件下 CANCELLED"。

---

## 6. T-D Motivation / Intent / THINK（测试设计）

### 6.1 Motivation

| ID | 测试内容 | 依据 |
|----|---------|------|
| D1 | `compute_motivation(actor, goal, commitment, agent_state_snapshot, now_ts)` 接受最小输入集合 | §5B.8 MO-16 |
| D2 | 所有输入可为 `None` | §5B.8 |
| D3 | 输出为 `MotivationSummary`（结构化） | §5B.8 MO-13 |
| D4 | 相同输入 → 相同输出（纯函数） | §5B.8 MO-11 |
| D5 | 传入固定 `now_ts` → `created_at == now_ts`；**不自行重新读取当前时间** | §5B.8 |
| D6 | 不修改输入 `goal` / `commitment` / `agent_state_snapshot` | §5B.8 |
| D7 | 不写 `main.data` | §5A.3 MO-3 |
| D8 | 不产生持久化 | §5A.3 MO-3 |
| D9 | 不调用 LLM / `ext_*` / 网络 | §5B.8 MO-17 |
| D10 | 不使用随机数 | §5B.8 MO-19 |
| D11 | 不消费 Relationship / Memory / Recent / World Query | §5B.8 MO-17 |

### 6.2 Intent / IntentSet

| ID | 测试内容 | 依据 |
|----|---------|------|
| D12 | `Intent` 最小结构：`intent_id` / `actor` / `action_type` / `reason` / `created_at` + 可选字段 | §5B.9 IN-16 |
| D13 | `make_intent()` 参数校验 | §5B.9 |
| D14 | `IntentSet` 最小结构：`actor` / `created_at` / `candidates` / `reason_summary` | §5B.9 IN-17 |
| D15 | `IntentSet(candidates=[])` 合法；`is_empty()` 正确 | §5B.9 IN-18 / §5B.10 |
| D16 | `Intent.reason` ≠ `Goal.reason`（语义分离） | §5B.7 RS-27 ～ RS-30 |
| D17 | `IntentSet` 不含 `Decision` 字段 | §5B.9 IN-23 |

### 6.3 THINK

| ID | 测试内容 | 依据 |
|----|---------|------|
| D18 | `think(context: AgentContext) -> IntentSet` | §5B.11 IN-29 |
| D19 | `isinstance(result, IntentSet)` | §5B.11 |
| D20 | `result.candidates == []`（Stub 阶段） | §5B.10 IN-24 ～ IN-25 |
| D21 | 多次调用均返回空集合（Stub 稳定，不制造假 Intent） | §5B.10 IN-27 |
| D22 | `think()` 不调用 LLM / `ext_*` / 网络 | §5B.11 IN-31 |

**C-3 明确禁止**：

- ❌ 测试 `Goal → Motivation → Intent` 真实链（THINK 未实现）。
- ❌ 要求 `think()` 产生非空 `candidates`。
- ❌ 为让测试"更完整"而给 Motivation 增加新输入。

---

## 7. T-E Runtime / SOT / Boundary（测试设计）

| ID | 测试内容 | 依据 |
|----|---------|------|
| E1 | 创建 Goal / Commitment 前后 `main.data` 深比较相等 | §5B.5 RS-4 |
| E2 | `main.data` 中无 `_goals` / `_commitments` 相关字段 | §5B.5 RS-4 |
| E3 | 无独立 DB / 文件 / 持久化（静态：无 `open('w')` / `json.dump` / `sqlite`） | §5B.5 RS-5 / §5B.6 |
| E4 | **无 persistence mechanism**（静态）；不把 "restart-loss" 写成正式 API 行为 | §5B.6 RS-24 ～ RS-26 |
| E5 | 4 个新文件 + `runtime.py` 不调用 LLM / 网络 | §5B.15 |
| E6 | 4 个新文件 + `runtime.py` 不调用 `ext_*` | §5B.13 |
| E7 | 创建 Goal / Commitment 不触发 World Change（不修改 `location` / `wallets` / `dates` 等） | §5B.13 |
| E8 | `_goals` / `_commitments` 是 Runtime 私有状态 | §5B.16 RS-35 |
| E9 | 外部直接 `runtime._goals[...] = ...` / `runtime._commitments[...] = ...` 不被允许（测试通过"不存在官方 API"间接验证 + 静态无 `setattr`/`__dict__` 滥用） | §5B.16 RS-35 |
| E10 | Holder API 只有 `add` / `get` / `list` / `replace`，无其他官方入口 | §5B.16 RS-31 |
| E11 | `runtime.py` 无 `auto_` / `scheduler` / `priority` / `conflict` 相关逻辑 | §5B.16 RS-36 |

**E9 特别检查（由顾问指令 §8 强调）**：

> 检查 Runtime Holder 是否真正 Runtime-owned，而不是"表面上有 `_goals` / `_commitments`，实际调用者仍可绕过 Runtime 直接控制"。

**C-3 将通过以下方式验证**：

- **静态检查**：`runtime.py` 中 `_goals` / `_commitments` 只出现在 `self._goals` / `self._commitments` 上下文。
- **动态检查**：测试 `add_goal` / `get_goal` / `list_goals` / `replace_goal` 四个官方 API 的行为覆盖。
- **行为隔离**：`get_goal` / `list_goals` 返回 deepcopy 副本，外部改字段不穿透 holder（已在 C-2 hardening 完成，C-3 补充为正式回归测试）。
- **无绕过路径**：`AgentRuntime` 不暴露任何"直接把 `_goals` 暴露给外部"的 API。

---

## 8. T-F Regression（测试设计）

| ID | 测试内容 | 来源 |
|----|---------|------|
| F1 | `docs/test_b3_context_assembler.py` 全部通过 | B3 回归 |
| F2 | `docs/test_b5_runtime_context.py` 全部通过 | B5 回归 |
| F3 | `docs/test_c2_goal_commitment.py` 全部通过 | C-2 自测回归 |
| F4 | `docs/test_c2_runtime_holder.py` 全部通过（含 H1-H17） | C-2 Holder 回归 |
| F5 | `build_context()` 仍返回 `AgentContext` | CC-20260926-01 |
| F6 | `think()` 仍返回 `IntentSet(candidates=[])` | §5B.10 / §5B.11 |
| F7 | `ContextLayers` 保留为 deprecated stub，未删除 / 未改名 / 未别名化 | CC-20260926-01 CA-7 |

---

## 9. 当前已有测试覆盖情况

| 测试文件 | 覆盖范围 | 状态 |
|---------|---------|------|
| `docs/test_b3_context_assembler.py` | ContextAssembler T1-T30 + 附加 | ✅ 已存在 |
| `docs/test_b5_runtime_context.py` | Runtime Context Connection T1-T12 + 附加 | ✅ 已存在 |
| `docs/test_c2_goal_commitment.py` | Goal / Commitment / Motivation / Intent T1-T15 + 附加 | ✅ 已存在 |
| `docs/test_c2_runtime_holder.py` | Runtime Holder H1-H17（含 hardening H14-H17） | ✅ 已存在 |

**当前覆盖状态**：

- T-A（Contract Structure）：**部分覆盖**（分散在现有测试的静态检查中）。
- T-B（Goal）：**大部分覆盖**（`test_c2_goal_commitment.py` 的 T1-T3 + `test_c2_runtime_holder.py` 的 H2-H5 / H14-H15）。
- T-C（Commitment）：**大部分覆盖**（T4-T6 + H6-H9 / H16-H17）。
- T-D（Motivation / Intent / THINK）：**部分覆盖**（T7-T13 + H12）。
- T-E（Runtime / SOT / Boundary）：**部分覆盖**（分散在多个测试的静态检查）。
- T-F（Regression）：**完全覆盖**（4 个测试文件本身即回归）。

---

## 10. 测试缺口

| # | 缺口 | 严重度 | 处理建议 |
|---|------|-------|---------|
| G1 | T-A 无独立的"Contract Structure"测试文件；当前分散在各测试的静态检查 | 中 | C-3 新增 `docs/test_c3_contract_structure.py` |
| G2 | T-B B11（Goal 无自动创建）：当前无显式测试 | 中 | C-3 新增静态检查 + 行为检查 |
| G3 | T-C C9（`hard` Commitment 从 `ACTIVE` → `CANCELLED` 允许）：当前无显式测试 | 中 | C-3 新增行为测试 |
| G4 | T-C C11（无 AI↔AI negotiation）：当前无显式测试 | 低 | C-3 新增静态检查 |
| G5 | T-D D4（纯函数重复调用结果一致）：当前 T8 部分覆盖，缺"未传 now_ts"的确定性 | 中 | C-3 补充 |
| G6 | T-D D11（Motivation 不消费 Relationship / Memory / Recent / World Query）：静态检查有，动态缺 | 中 | C-3 补充静态扫描 |
| G7 | T-E E3（无持久化）：当前分散，无集中测试 | 中 | C-3 新增集中静态检查 |
| G8 | T-E E4（无 persistence mechanism；不把 restart-loss 写成 API 行为）：当前无显式测试 | 中 | C-3 新增静态检查 |
| G9 | T-E E9（Holder 真正 private，无绕过路径）：当前 H 系列部分覆盖，但缺"无绕过路径"的显式断言 | 高 | C-3 新增"无绕过路径"测试 |
| G10 | T-E E10（Holder API 只有 add / get / list / replace）：当前无显式测试 | 中 | C-3 新增 API 白名单检查 |
| G11 | T-E E11（无 auto / scheduler / priority / conflict）：当前无显式测试 | 中 | C-3 新增静态检查 |
| G12 | T-F F7（`ContextLayers` deprecated stub 状态）：当前分散，无集中测试 | 低 | C-3 新增集中检查 |

---

## 11. C-3 允许在 Implementation 阶段新增的测试

**允许新增（不修改 `.py`）**：

- `docs/test_c3_contract_structure.py`：T-A 集中结构检查。
- `docs/test_c3_boundary.py`：T-E 集中边界检查（含 E9 无绕过路径）。
- 在现有测试中补充缺失的断言（**不修改业务代码**）。

**允许修改**：

- 仅允许修改 `docs/test_c3_*.py`（新增）。
- 可对现有测试**追加**断言，但**不得**修改现有测试的既有断言语义。

---

## 12. C-3 明确禁止新增的测试

**禁止**：

- ❌ 测试 `Goal → Motivation → Intent` 真实链（THINK 未实现）。
- ❌ 测试 THINK 产生非空 `candidates`。
- ❌ 测试 Goal priority / conflict resolution（未冻结）。
- ❌ 测试 Commitment AI↔AI negotiation（未冻结）。
- ❌ 测试持久化 / restart-recovery（未冻结）。
- ❌ 测试 Decision / Action / Activity / World Query / Scheduler（未实现）。
- ❌ 测试 LLM / Prompt Adapter（未实现）。
- ❌ 测试 Memory Recall（未启用）。
- ❌ 测试 `ext_*` 执行（C-2 不调用）。
- ❌ 为让测试通过而修改 Contract 或 `.py`。

---

## 13. C-3 与未来 C-4 的边界

| 阶段 | 范围 | 产出 |
|------|------|------|
| **C-3** | 测试架构设计 + 实施 | `docs/test_c3_*.py` |
| **C-4** | PROJECT Update | 更新 `PROJECT_V3.1_MASTER.md` |
| **C-3 → C-4 之间** | 不做任何业务代码修改 | — |

**C-3 不得进入 C-4 的内容**：

- 不更新 `PROJECT_V3.1_MASTER.md`。
- 不修改 Contract。
- 不进入 Decision / Action / Activity / World Query / Scheduler。

---

## 14. 风险 / 架构问题

| # | 风险 / 问题 | 说明 | 处理 |
|---|------------|------|------|
| R1 | C-3 测试可能"越权设计未来" | 例如测试 Goal priority / Decision | 已在 §12 明确禁止 |
| R2 | 测试可能"偷偷让 THINK 产生 Intent" | 例如为让 D20 通过而修改 `think()` | 已在 §6.3 / §12 明确禁止 |
| R3 | Holder "无绕过路径"验证困难 | Python 无真正 private | 通过"官方 API 白名单 + 静态检查 + 行为隔离"组合验证 |
| R4 | Motivation "最小输入集合"测试可能被扩展 | 例如测试 Relationship 输入 | 已在 §6.1 D11 明确禁止 |
| R5 | `hard` Commitment 语义易被误读为"绝对不可违反" | 测试可能写成"拒绝所有 CANCELLED" | 已在 §5 C9 明确"允许被 CANCELLED" |
| R6 | 回归测试可能因 C-3 新增文件而互相影响 | 测试隔离 | C-3 新增文件不修改现有测试 |
| R7 | 发现 Contract 与代码矛盾 | 例如 Contract 允许但代码拒绝 | §15 说明：**停下报告**，不自行修改 |

---

## 15. 最终结论

### C-3 Tests Preflight：**ACCEPTED**

**理由**：

1. C-3 目标明确：只做测试架构设计，不写业务代码。
2. 六组测试（T-A ～ T-F）设计符合 C-2 冻结的 Contract。
3. 已识别现有测试的覆盖状态与 12 项缺口。
4. 明确区分"允许在 C-3 实施阶段新增"与"禁止新增"的测试。
5. 明确 C-3 与 C-4 的边界。
6. 已识别 7 项风险，均有对应处理。

**C-3 待实现**：

- 新增 `docs/test_c3_contract_structure.py`（T-A）。
- 新增 `docs/test_c3_boundary.py`（T-E 集中检查，含 E9 无绕过路径）。
- 在现有测试中**追加**（不修改）缺失的断言（T-B / T-C / T-D）。

**C-3 不允许**：

- 修改任何 `.py`。
- 修改 Contract。
- 修改 PROJECT。
- 修改现有测试的既有断言语义。
- 进入 C-4。

---

## 16. 特别声明（对应顾问指令 §10）

**若 C-3 实施阶段发现**：

- Contract 与代码矛盾。
- 测试要求与当前架构矛盾。
- 某个测试需要修改 Contract。

**DS 必须**：

1. **停下报告**。
2. 不自行进入 Contract Change。
3. 不自行修改 `.py`。

**本 Preflight 已按此原则设计所有测试**：所有测试只验证 C-2 已冻结的内容，不要求修改 Contract 或代码。

---

## 17. 完成确认

> **本阶段只做 C-3 Tests Preflight。**
>
> **未修改任何 `.py`。**
> **未新增任何测试代码。**
> **未修改 `PROJECT_V3.1_MASTER.md`。**
> **未修改 `docs/V3.1_ARCHITECTURE_CONTRACT.md`。**
> **未修改 `main.py` / `ext_*.py` / 前端 / Memory。**
> **未实现 THINK / Decision / Action / Activity / World Query / Scheduler / AI↔AI。**
> **未接 LLM / 网络。**
> **未启用 Memory Runtime。**
> **未创建数据库 / 持久化文件。**
>
> **未进入 C-3 Implementation。**
> **未进入 C-4。**

---

## 输出物

- **C-3 Tests Preflight Report**（本文件）
- 建议落地文件：`docs/C3_TESTS_PREFLIGHT.md`
- Commit SHA：**待提交后填写**

---

**C-3 Tests Preflight 完成，停止。等待架构审核。**