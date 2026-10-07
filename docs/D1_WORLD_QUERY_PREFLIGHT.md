# V3.1 Phase D-1 Preflight

# World Query Foundation

**Status:** PRE-FLIGHT
**Phase:** V3.1 Phase D-1
**Document Type:** Architecture Preflight / Decision Freeze Preparation
**Implementation Status:** **NO CODE IMPLEMENTATION AUTHORIZED**
**上游状态：** D-0 = **SEALED**（Audit / Decisions / Contract §5C / Tests 全部 ACCEPTED）
**Last Updated:** 2026-09-30

---

## 0. 文档目的

本文件是 V3.1 Phase D-1 的前置架构确认文件。

D-0 已冻结：

- World Fact 定义
- `main.data` 的 SOT 治理原则（`D0G-1` ～ `D0G-5`）
- Activity 归属（`AC-5` ～ `AC-10`）
- Event 权威（`EV-9` ～ `EV-14`）
- Capability 与 Legacy Execution Adapter（`CP-1` ～ `CP-8`）
- Memory "OFF"（`ME-21` ～ `ME-26`）
- World Tick Blocker（`WT-1` ～ `WT-7`）

D-1 不允许直接进入代码实现。

必须**先明确**：

> **World Query 是什么、能被谁用、能读什么、不能读什么、返回什么、以及它与 Context / Event / Activity / Command 的边界。**

否则后续极易出现：

```text
Agent 自己到处读 main.data / ext_*
        ↓
每个模块各自解释世界
        ↓
世界事实出现多个解释版本
        ↓
D-0 刚刚冻结的「唯一事实来源」被绕过
```

---

## 1. D-1 的唯一目标

> **让 Agent Core 能够通过统一、只读、无 LLM、无行为决策、无 World mutation 的接口，询问当前世界事实。**

一句话：

```text
Agent
 ↓
World Query
 ↓
「我在哪里？」「这个地方是什么？」「谁在这里？」
「现在几点？」「这里有什么？」「我正在做什么？」
```

### 1.1 D-1 明确不做

| 不做 | 归属 |
|------|------|
| ❌ Activity | **D-2** |
| ❌ Capability | **D-4** |
| ❌ Movement / Location Continuity | **D-3** |
| ❌ Agent Decision → Capability | **D-5** |
| ❌ Legacy Migration | **D-6** |
| ❌ 修改 `ext_ai.py` / `ext_world.py` / `ext_room.py` 的旧行为 | **D-6** |
| ❌ 修 Memory（`ext_memory.py` / `ext_mem.py`） | **Phase E** |
| ❌ 前端改动 | D-4 / D-6 |
| ❌ 新 Event Bus | 禁止（`EV-14`） |
| ❌ 第二个 World / World Store | 禁止（`D0G-4`） |

### 1.2 D-1 的验收形态

> **新增一个只读查询层。它不改变任何现有行为。**
>
> 因此 D-1 结束时的正确状态是：**所有旧功能行为与 D-0 结束时完全一致，只是世界上多了一个未被强制使用的只读入口。**

---

## 2. 当前读取能力与真实 schema（事实基线，必须作为 D-1 起点）

> 依据：D-0 Audit（**ACCEPTED**）+ 本轮对 `main.py` / `ext_room.py` 的核对。
> 本节记录的是**当前真实状态**，不是目标。

### 2.1 现有读取函数（`main.py`，全部已存在并被使用）

| 函数 | 行号 | 语义 | 复杂度 |
|------|------|------|--------|
| `canonical_ai_name(name)` | 336 | 名字规范化（AI） | O(ais) |
| `canonical_contact_name(name)` | 343 | 名字规范化（联系人） | O(ais+buildings) |
| `canonical_name(name)` | 359 | 上两者合并 | —— |
| `is_ai_name(name)` | 364 | 是否 AI | O(ais) |
| `owner_of_ai(ai)` | 371 | AI → owner（**运行时被 `ext_admin.py:38` 猴补丁替换**） | O(users) |
| `is_ai_of(owner, name)` | 378 | 归属判断（不做 emoji 规范化） | O(1) |
| `is_admin(user)` | 388 | 权限（**运行时被 `ext_admin.py:19` 替换**） | O(1) |
| `room_exists(name)` | 494 | 房间是否存在 | O(1) |
| `now_str()` | 496 | **UTC+8** 时间字符串 | O(1) |
| `room_time(room)` | 498 | 按房间时钟（`time_settings[room].mode == "fixed"` 时用 `fixed_time`） | O(1) |
| `find_building_of_room(room)` | 518 | 房间 → 建筑（**线性扫描**） | **O(buildings × rooms)** |
| `building_owner_of_room(room)` | 523 | 房间 → 建筑 owner | O(buildings × rooms) |
| `can_access_room(room, user)` | 531 | 可访问性 | O(buildings × rooms) |
| `can_view_room(room, user)` | 551 | **`can_access_room` 的别名**（无独立 view 策略） | 同上 |
| `resolve_building(key)` | 553 | 建筑模糊查找：id → 精确 name → name 子串 | O(buildings) |
| `full_room_name(room)` | 575 | 裸房间名 → 持久化全名 | O(buildings × rooms) |
| `online_room_count(room)` | 587 | 45 秒窗口内在该房间的在线人数 | O(online) |
| `append_timeline` / `append_visited` / `add_trail` | 416 / 425 / 612 | **写入函数**（非 Query，D-1 不得调用） | O(1) |
| `check_pending_moves()` | 592 | **写入函数**（`ai_location` mutation） | O(pending) |
| `ai_integration_enabled()` | 618 | AI 集成开关 | O(1) |

### 2.2 现有 `AgentState` 投影（`agent/state.py`）

`get_agent_state(ai_name, data)` → `AgentState`，字段：

```text
name / owner / location / wallet / affection
is_following / is_dating / is_working
current_activity（_derive_activity 推导）
current_goal（固定 None）
mood / energy / social_need / stress（placeholder，AS-2 禁作决策输入）
_meta（字段来源标记）
```

**事实确认（D-0 `D0-014`）：** `agent/state.py:15` **直接 `from main import ...`**，是 Agent 包内唯一与 `main` 直接耦合的模块。当前**无生产调用者**。

### 2.3 现有读取的 schema（真实结构）

| 数据 | 结构 | 关键事实 |
|------|------|---------|
| `ai_location` | `{ai: room_full_name}` | **存的是 room 全名（如 `咖啡馆·会客厅`），不是 building_id**；`"main"` 是通信频道不是物理地点 |
| `rooms` | `{room_full_name: {creator, has_password, password, created, description}}` | **`rooms` 中没有 `building_id` 字段** |
| `buildings` | `{bid: {name, emoji, type, region, x, y, owner, description, features[], salary, rooms[], notice, ...}}` | `rooms` 是**房间名列表**；`region` 是**标签字符串**（非 region_id） |
| `regions` | `{label: {x, y, image}}` | 无 id 体系，label 即 key |
| `npcs` | `{building_id: [{name, emoji, desc}]}` | **NPC 归属建筑，不归属房间；无位置、无状态** |
| `presence` | `{user: {page, room, ts}}` | **只记录真人**；25 秒过期 |
| `online` | `{name: {room, time}}` | 45 秒过期 |
| `affection` | `{ai: int}` | 默认 50 |
| `wallets` | `{name: float}` | —— |
| `work_sessions` | `{ai: {building_id, start_ts, hours, started_at}}` | Legacy Activity State |
| `ai_follow` | `{ai: {owner, go_to, at_ts}}` | Legacy Activity State |
| `ai_pending_moves` | `{ai: {room, at_ts}}` | Legacy Activity State |
| `ai_meeting` | `{ai: {room, at_ts}}` | Legacy Activity State |
| `dates` | `[{id, user, ai, building_id, room, start_ts, status, arrive_min, arrive_at, bring_gift, gift_item, gift_accepted, aff, invited_by_ai, end_ts}]` | Legacy Activity State |
| `ai_shop_state` | `{ai: {last_ts, day, day_count, reply_day, pending_reply, active_gift_day, next_shop_ts}}` | Legacy Activity State |
| `instances` | `{user: {iid: {..., status, participants[], chat_history[]}}}` | Legacy Activity State |
| `time_settings` | `{room: {mode, fixed_time}}` | 房间虚拟时钟 |
| `user_ais` | `{user: [ai, ...]}` | 归属关系 SOT |

### 2.4 已确认的结构性缺口（D-1 必须显式面对，不得猜）

| # | 缺口 | 影响 |
|---|------|------|
| **G-1** | **Room → Building 无索引**，`find_building_of_room` 是 **O(buildings × rooms)** 线性扫描 | World Query 若被每 tick 调用会放大成本 |
| **G-2** | **没有 World → Map 关系**：`buildings.region` 是**标签字符串**，不是 `map_id` | 「这个建筑在哪张地图上」**当前无法回答** |
| **G-3** | **NPC 没有位置/状态**，只按 `building_id` 分组 | 「某 NPC 现在在哪里」「谁在这里」对 NPC **当前无法回答** |
| **G-4** | **`presence` 只含真人**，不含 AI / NPC | 「谁在这里」必须**分别**回答 真人 / AI / NPC 三类 |
| **G-5** | **`ai_location` 与 `rooms` 的关系只有字符串**，没有 `building_id` ↔ `room` 外键 | 位置事实是「字符串匹配」而非「关系引用」 |
| **G-6** | **`current_activity` 是推导值**（`_derive_activity` 读 18 个 Legacy 字段） | 「我正在做什么」在 D-1 **只能返回 Legacy 推导结果**，不是正式 Activity |
| **G-7** | **`ai_location` 可能持有建筑名而非房间名**（`ext_econ.py:64` fallback，D-0 `D0-027`） | 「我在哪里」必须能表达**不可解析的位置** |
| **G-8** | **`agent/state.py` 直接 import main** | Agent 包内已存在与 `main` 的直接耦合（`D0-014`） |

> **G-1 / G-2 / G-3 决定了 D-1 的诚实上限：**
> D-1 **不能**凭空实现「按用途查询地点」「地图→建筑→房间层级查询」，
> 因为**当前 schema 里不存在这些关系**。
> 若需要，必须先在 Contract 中裁定「是否新增关系 / 是否允许新增索引」——**这属于 D-1 Contract Change 的范围，不属于本 Preflight 的自行决定。**

---

## 3. 决策清单（Preflight 必须冻结的 14 项）

以下 14 项是本 Preflight 的核心。每项给出**候选方案**与**建议**，等待架构侧裁决。

---

## D1-DEC-1 · World Fact 的定义

### 问题

World Query 返回的「World Fact」到底是什么？

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| A | **`main.data` 中当前值的只读投影**（本 Preflight 建议） | 与 D-0 §4 一致；但会把「推导值」（如 `current_activity`）排除在外 |
| B | 包含推导值（`_derive_activity` 结果也算 Fact） | 推导逻辑变化会导致「事实」变化，违背 Fact 稳定性 |
| C | 包含派生缓存（如 `presence` 过期裁剪后的结果） | 引入新的时间语义 |

### 建议：**A**

**理由：**

- D-0 Preflight §4 已定义 World Fact 为「当前世界中可以被系统视为真实状态的数据事实」
- D-0 `D0G-1` 冻结 `main.data` 为唯一 World 存储位置
- 若把推导值也算 Fact，则 Fact 会随推导算法变化，破坏「事实」的可审计性

**因此建议冻结：**

```text
World Fact
  = main.data 中「直接存储的当前值」
  ≠ 推导结果
  ≠ 缓存
  ≠ 事件历史
```

**并且：** 若 Query 返回推导值（例如「我正在做什么」），必须**显式标注为 derived**，不得与 Fact 混同。

---

## D1-DEC-2 · World Query 的职责与绝对边界

### 问题

World Query 负责什么、绝对不负责什么？

### 建议：冻结如下

**World Query 负责：**

```text
向 Agent / Application 提供读取世界事实的统一入口
返回结构化事实
对「不存在 / 未知 / 不可解析」给出明确语义
```

**World Query 绝对不做（继承 D-0 Preflight §7）：**

```text
❌ 调用 LLM
❌ 进行 AI 行为判断
❌ 产生 Intent
❌ 产生 Decision
❌ 修改 main.data
❌ 直接移动 AI
❌ 直接发送 SMS
❌ 直接开始约会
❌ 直接调用 VoiceStudio
❌ 直接执行 Capability
❌ 创建 Goal
❌ 创建 Commitment
❌ 处理 Memory
❌ 触发写入函数（append_timeline / append_visited / add_trail / check_pending_moves / save_data）
❌ 裁剪 / 归一化 / 修复数据（即 Query 不得有副作用）
```

### 关键：**Query 不得有副作用，包括「顺手清理」**

**当前已知的反例（D-0 `D0-019`）：**

```text
GET /api/messages → _ensure_hall(room) → 写 rooms / messages / save_data()
GET /api/map      → 裁剪 presence
GET /api/economy  → _ensure_wallet() 写 wallets
GET /api/presence → 裁剪 presence
```

> **World Query 必须与这些行为彻底分开。** Query 只读，不修。

### 建议冻结

| 规则 | 内容 |
|------|------|
| **WQ-5** | World Query 是 **READ ONLY**；不得有任何副作用（含清理、裁剪、修复、归一化） |
| **WQ-6** | World Query 不调用 LLM、不产生 Decision、不执行 Capability |
| **WQ-7** | World Query 不修改 `main.data`（直接或间接） |
| **WQ-8** | World Query 不调用 `save_data()` |
| **WQ-9** | World Query 不调用任何写入型 helper（`append_*` / `add_trail` / `check_pending_moves` 等） |

---

## D1-DEC-3 · Query 是否允许读取 `main.data`

### 问题

World Query 是否可以（直接或间接）读 `main.data`？

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| A | Query 直接读 `main.data`（拿到 dict 引用） | 与现状一致；但 Query 与 main 直接耦合，且容易顺手写 |
| B | Query 通过**调用方注入数据**（Dependency Injection，不 import main）（**建议**） | 需要调用方提供 data；但边界干净、可测试、不可写 |
| C | Query 通过一个未来的 `WorldStore` 抽象访问 | **D-1 不允许新建 World 对象**（`D0G-4`） |

### 建议：**B**

**理由：**

1. `D0G-4` 禁止创建第二个 World / World Store —— 因此 C 不可选
2. A 会让 Query 持有可变引用，**在结构上无法保证只读**
3. B 与 `agent/*_provider.py` 现有风格**完全一致**：

   现有 Provider 全部采用 `fetch(ai_name, owner, data, ...)` 形式，且明确声明「不 import main / ext_*」。

**因此建议冻结：**

```text
World Query 采用 Dependency Injection：
    - 由调用方传入 data（不透明只读引用）
    - Query 模块不 import main
    - Query 模块不 import ext_*
    - Query 模块不持有全局状态
```

**必须明确的残余风险（如实记录）：**

Python 的 `dict` 无法在语言层面强制只读。因此「Query 不修改 data」只能靠：

- 代码约定与 code review
- D-1 Architecture Tests（静态断言 Query 模块中无写入模式）
- **架构测试是唯一可自动化的防线**

> 这一点必须在 Contract 中写明：**只读是约定 + 测试约束，不是语言级保证。**

参考实现风格（与现有 `agent/stable_core_provider.py` 一致）：

```python
def fetch_agent_location(ai_name: str, data: Dict[str, Any]) -> Optional[str]:
    """只读返回 AI 当前房间全名；未知返回 None。"""
    ...
```

---

## D1-DEC-4 · Query 是否允许读取 `AgentState` projection

### 问题

World Query 是否可以读 `AgentState`（`agent/state.py`）？

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| A | 允许 Query 读 AgentState | 会形成 `data → WorldQuery → AgentState → data` 的绕行；且 AgentState 含推导值与 placeholder |
| B | **禁止**：Query 只读原始 Fact；AgentState 是**消费方**，不是数据源（**建议**） | 需要在 D-1 明确方向 |
| C | 允许，但只允许读其中的「direct_map」字段 | 复杂，且仍需排除 placeholder |

### 建议：**B**

**理由：**

1. D-0 §2 冻结：`AgentState = 当前事实投影`（**输出**，不是输入源）
2. `AgentState` 含 **placeholder**（`mood` / `energy` / `social_need` / `stress`），Contract **AS-2** 禁止其作为决策输入
3. `AgentState.current_activity` 是**推导值**，`current_goal` 固定 `None`
4. 若 Query 读 AgentState，则出现 **`data → Query → AgentState → Query`** 的循环，违背 `D0G-2`

**因此建议冻结：**

```text
方向必须是单向：

    main.data  →  World Query  →  Agent / Context / Decision

而不是：

    main.data  →  World Query  →  AgentState  →  World Query
```

**并且建议：** D-1 建立 Query 后，`AgentState` 的**读取入口归属**必须在 D-1 Contract 中一并裁定（对应 D-0 `D0-014` 待处理项）。

---

## D1-DEC-5 · Query 是否允许 Map / Building / Room 反查

### 问题

Query 是否可以做 `room → building`、`building → region`、`building → rooms` 这类反查？

### 事实（来自 §2.4）

```text
room → building : 只能 O(buildings × rooms) 线性扫描
building → rooms: 直接存在（buildings[bid].rooms 是列表）
building → region: region 只是「标签字符串」，不是 map_id
map 层级: 当前 schema 中不存在 World → Map 关系
```

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| A | 允许反查，**复用现有 `find_building_of_room` 语义**，不新增索引（**建议**） | 保留 O(n)；但符合 Contract `WQ-4`「不引入新索引」 |
| B | 在 Query 内部建立 room→building 索引缓存 | **违反 `WQ-4`**，且引入缓存一致性问题（`SOT-6` 要求缓存只读或可重建） |
| C | 修改 `rooms` schema 增加 `building_id` | **违反 `WQ-3` / `AC-3`**（不修改 schema） |

### 建议：**A**

**理由：**

- Contract **`WQ-3`**：不修改 `buildings` / `rooms` / `npcs` schema
- Contract **`WQ-4`**：未来 World Query 必须基于现有数据结构，**不引入新索引**（除非单独设计）
- B / C 都需要 Contract Change，**不属于 D-1 Preflight 可自行决定的范围**

**因此建议冻结：**

| 规则 | 内容 |
|------|------|
| **WQ-10** | 反查**允许**，但必须复用现有语义，**不得新增索引 / 缓存 / schema 字段** |
| **WQ-11** | Query **必须如实返回当前 schema 能回答的内容**；对 schema 无法回答的内容（如 Map 层级、NPC 位置）返回 `UNSUPPORTED`，**不得猜测** |
| **WQ-12** | 若 D-1 之后确需 Map / 关系索引，必须走**独立 Contract Change** |

**并且：** 由于 `find_building_of_room` 是 O(buildings × rooms)，建议 Query **不在高频路径上自动调用反查**，由调用方显式请求。

---

## D1-DEC-6 · Query 返回值的数据结构

### 问题

Query 返回什么形式的数据？

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| A | 直接返回裸值 / 裸 dict（`main.data` 的引用） | **调用方可能修改它 → Query 事实上不是只读** |
| B | 返回**不可变结构 + 来源标注**（本 Preflight 建议） | 需要额外包装 |
| C | 返回值 + 状态码二元组 `(value, status)` | 与 D-1 的「显式 absent 语义」重复 |
| D | 统一返回 `QueryResult` 对象 | 结构较重，但语义最完整 |

### 建议：**D（`QueryResult`）**，并同时满足 **B** 的约束

**理由：**

1. D-0 §25 / §26 要求 Query「返回结构化事实」
2. §2.3 显示当前数据**非常不规则**（有的存全名、有的存 id、有的存标签、有反例 G-7）
3. 必须能表达「未知 / 不存在 / 不可解析」，因此 A 不够

**建议返回结构（候选，具体字段在 D-1 Contract 冻结）：**

```text
QueryResult
├── value              # 事实值（None 表示无值）
├── status             # FOUND / ABSENT / UNKNOWN / UNSUPPORTED / AMBIGUOUS
├── source             # 事实来源，例如 "main.data.ai_location"
├── derived            # bool：该值是否为推导值（D1-DEC-1）
├── as_of              # 该事实的观测时间（若数据本身无时间戳则为 Query 执行时间）
└── notes              # 可选：解释（例如「位置无法解析为建筑」）
```

**冻结建议：**

| 规则 | 内容 |
|------|------|
| **WQ-13** | Query 返回**结构化结果对象**，不返回裸引用 |
| **WQ-14** | 结果必须携带 **`source`**（哪个 `main.data` key 或哪个已有 helper） |
| **WQ-15** | 结果必须携带 **`derived`** 标记（区分 Fact 与推导值） |
| **WQ-16** | 结果必须是**调用方可安全持有**的副本（不得让调用方改到 `main.data`） |
| **WQ-17** | `QueryResult` 的具体字段名与类型在 **D-1 Contract** 冻结；Preflight 只冻结语义 |

> **注意：** `QueryResult` **不是** `agent.Event`、**不是** `CapabilityResult`（后者属 D-4）、**不是** Context Section。

---

## D1-DEC-7 · 空值 / unknown / absent 语义

### 问题

「没有」「不知道」「不支持」「有多个」如何区分？

### 建议：冻结五态

| 状态 | 语义 | 典型例子 |
|------|------|---------|
| **`FOUND`** | 事实存在且有值 | `ai_location` 有值且可解析 |
| **`ABSENT`** | **该事实在当前世界确实不存在** | 该 AI 不在任何约会中（`dates` 中无记录） |
| **`UNKNOWN`** | **事实存在，但当前无法确定** | `ai_location` 指向一个已不存在的房间（G-7） |
| **`UNSUPPORTED`** | **该问题当前 schema 无法回答** | 查询「这个建筑在哪张地图上」（G-2）；「某 NPC 现在在哪里」（G-3） |
| **`AMBIGUOUS`** | **匹配到多个候选，无法唯一确定** | `resolve_building("咖啡")` 命中多个建筑 |

### 关键区分（必须冻结）

```text
ABSENT      ≠ UNKNOWN
    没这回事      有这回事但我不知道

UNKNOWN     ≠ UNSUPPORTED
    数据坏了      这个问题我根本答不了

UNSUPPORTED ≠ ABSENT
    schema 限制   世界事实
```

### 建议冻结

| 规则 | 内容 |
|------|------|
| **WQ-18** | Query 必须区分 `FOUND` / `ABSENT` / `UNKNOWN` / `UNSUPPORTED` / `AMBIGUOUS` |
| **WQ-19** | **禁止**用 `None` 同时表达这五种情况 |
| **WQ-20** | **禁止**为了「让调用方好过」而把 `ABSENT` 伪装成空值或默认值 |
| **WQ-21** | `UNSUPPORTED` 必须显式返回，**不得**用猜测值代替（与 `WQ-11` 一致） |
| **WQ-22** | Query **不得抛异常作为正常控制流**；数据缺失不是异常 |

---

## D1-DEC-8 · Query 是否允许时间参数

### 问题

Query 是否接受时间参数（例如「昨天 19 点他在哪」）？

### 事实

```text
main.data 中只有「当前值」，没有历史版本
历史存在于：ai_timeline / trails / ai_visited / dates / work_history / date_log
（均为「事件记录」，不是「世界快照」）
```

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| A | Query 接受 `now_ts`（仅用于**当前时刻的判定**） | 小、明确 |
| B | Query 支持任意历史时刻查询 | **当前 schema 无法支持**；会把 Event History 误当 World Snapshot |
| C | 完全不接受时间 | 无法处理 `presence` 过期、`room_time` 房间时钟 |

### 建议：**A**（限制为「观测时刻」，不是「历史回溯」）

**理由：**

- `presence` / `online` 有 25s / 45s 过期窗口 → 必须能注入「现在」
- `room_time(room)` 有**房间虚拟时钟**（`time_settings`）→ 必须能注入
- 但**历史时刻**无法回答：`main.data` 不保存历史快照

**因此建议冻结：**

| 规则 | 内容 |
|------|------|
| **WQ-23** | Query **可以**接受 `now_ts`（用于过期判定与房间时钟），缺省为当前时间 |
| **WQ-24** | `now_ts` 的语义是「观测时刻」，**不是「历史回溯」** |
| **WQ-25** | Query **不支持**任意历史时刻查询；该能力若需要，属 Event History / Memory 范畴（**Phase E**） |
| **WQ-26** | Query 涉及时间的返回必须标明是「世界时间」还是「房间时间」（`room_time` vs `now_str`） |

> **必须注意：** 当前世界时间存在**两套语义**——`now_str()`（UTC+8 真实时间）与 `room_time(room)`（可被 `time_settings` 固定）。Query 不得把两者混同。

---

## D1-DEC-9 · Query 是否允许读取其他 AI / NPC / User

### 问题

AI A 能否通过 World Query 知道 AI B / NPC / User 的事实？

### 事实（产品要求，来自 `V3.1_PRODUCT_GUIDE.md` §13）

> 用户拥有「上帝视角」，**AI 不拥有全知视角**。

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| A | Query 无差别返回所有事实 | **违反产品原则**：AI 变成全知 |
| B | Query **在数据层不限制**，可见性由调用方（Agent / Application）决定 | 责任后移，D-1 无法验证 |
| C | Query **接受 requester 身份**，在数据层返回「该身份可见的事实」（**建议**） | 需要定义可见性规则 |

### 建议：**C**，但 **D-1 只建立机制，不实现复杂策略**

**理由：**

- 产品明确要求 AI 不是全知（`V3.1_PRODUCT_GUIDE.md` §13）
- 但 D-1 是「Foundation」，**不应在此冻结完整可见性矩阵**（那需要 Relationship / Presence 语义，属后续阶段）

**因此建议冻结：**

| 规则 | 内容 |
|------|------|
| **WQ-27** | Query **必须接受 requester 身份**（`requester`），不得设计为「任何人问什么都答」 |
| **WQ-28** | D-1 阶段可见性策略**只实现最小规则**：自己的事实 + 公开事实；其余返回 `UNSUPPORTED` 或 `FORBIDDEN`（状态名在 D-1 Contract 冻结） |
| **WQ-29** | **禁止** D-1 把 Query 实现为「全知接口」，即使实现更简单 |
| **WQ-30** | 完整可见性矩阵（AI↔AI / AI↔User / AI↔NPC / 上帝视角 / 私聊可见性）留待后续 Contract，**不在 D-1 冻结** |
| **WQ-31** | Query 对 NPC 只能回答 **schema 能支持的内容**（NPC 归属建筑、name/emoji/desc）；「NPC 位置」「NPC 状态」返回 `UNSUPPORTED`（G-3） |

> **若架构侧选择 B（数据层不限制）：** 必须在本 Preflight 中明确记录，并同时记录「可见性由调用方保证」这一**未被测试覆盖的风险**。

---

## D1-DEC-10 · Query 与 Context Provider 的边界

### 问题

World Query 与 `agent/*_provider.py`（StableCore / Recent / LongTerm / DynamicWorld）是什么关系？

### 事实

```text
Provider 现状：
  - fetch(ai_name, owner, data, now_ts=None, agent_state_dict=None, recall_query=None)
  - 全部「不 import main / ext_*」
  - 只负责「从已有系统事实中，取出一小块结构化数据」
  - 输出 List[Dict]，供 ContextAssembler 组装
  - ContextAssembler 只被 AgentRuntime.build_context() 调用（CA-9）
```

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| A | Provider 改为调用 World Query | **D-1 不得改动 Provider**（属 CA / B2 已冻结边界） |
| B | World Query 与 Provider **并列**，Provider 内部逐步替换（后续阶段）（**建议短期**） | 短期存在两条读取路径 |
| C | World Query 取代 Provider | 需重写 Context 链，**必须 Contract Change**，不属 D-1 |

### 建议：**B（并列），并在 D-1 Contract 中冻结「谁是最终读取入口」的方向**

**理由：**

- Contract **CA-6 / CA-7 / CA-9** 已冻结 Context 链，D-1 不得改动
- `DynamicWorldProvider` 已经在读「当前地点」等事实 → 与 World Query **职责重叠**
- 但 B2 阶段的 Provider 是**已验收产物**，D-1 不应直接改它

**因此建议冻结：**

| 规则 | 内容 |
|------|------|
| **WQ-32** | D-1 **不修改** 任何 Provider 与 `ContextAssembler` |
| **WQ-33** | World Query 与 Provider **短期并列**；两者职责重叠部分（当前地点 / 世界状态）在 D-1 Contract 中记录，迁移属后续阶段 |
| **WQ-34** | **长期方向**：Provider 的**世界事实读取**应经由 World Query；**但该迁移不在 D-1 实施** |
| **WQ-35** | World Query **不得**被 `ContextAssembler` 直接调用（`CA-9` 限制 ContextAssembler 只被 `build_context` 调用） |
| **WQ-36** | Provider 与 Query 都**不得**写出 `main.data` |

---

## D1-DEC-11 · Query 与 Event 的边界

### 问题

World Query 与 `agent.Event` 是什么关系？

### 事实（D0-DEC-3 / Contract `EV-9` ～ `EV-14`）

```text
agent.Event        = 正式 Domain Event（世界「刚刚发生了什么」）
World Query        = 世界「现在是什么样」
两者语义不同：Event 是「发生」，Query 是「状态」
```

### 建议冻结

| 规则 | 内容 |
|------|------|
| **WQ-37** | World Query **不是** Event，**不产生** Event，**不消费** Event |
| **WQ-38** | Query **不得**被实现为「读 Event 日志后推导状态」（那会让 Event 变成隐蔽的 World SOT，违反 `D0G-4`） |
| **WQ-39** | `EV-12`（`World Change → agent.Event → Memory Runtime`）**不经过 World Query** |
| **WQ-40** | `EV-13`（main channel 必须能产生正式 `agent.Event`）属 **D-1 / D-5 Event Coverage**，但**与 World Query 是两件事**，不得混在一个实现里 |
| **WQ-41** | Query 的结果**不得**被当作 Event 使用（例如「Query 说他在咖啡馆」不等于「发生了到达事件」） |

> **重要：** D-1 的任务名是「World Query Foundation」，**不包含 Event Coverage**。
> `EV-13` 的 main channel 覆盖**必须单独定义**，不得夹带在 Query 实现中。

---

## D1-DEC-12 · Query 与 Activity 的边界

### 问题

World Query 能否返回「当前 Activity」？

### 事实（D0-DEC-2 / Contract `AC-5` ～ `AC-10`）

```text
Activity 正式实现 = D-2
当前只有 18 类 Legacy Activity State + _derive_activity() 推导值
```

### 建议冻结

| 规则 | 内容 |
|------|------|
| **WQ-42** | D-1 **不实现** Activity，World Query **不返回正式 Activity 对象** |
| **WQ-43** | D-1 阶段若需要回答「我正在做什么」，**只能返回 Legacy 推导结果**，且必须标记 `derived = True` 并注明来源为 `_derive_activity` |
| **WQ-44** | D-1 **禁止**把 Legacy Activity State 聚合包装成「Activity」，否则违反 `AC-7`（禁止多个 Activity 真相并存） |
| **WQ-45** | D-2 建立正式 Activity 后，**由 D-2 决定**该查询是否改由 Activity SOT 回答；D-1 不得预先设计该接口 |
| **WQ-46** | Query **不得**返回可被误认为「Activity 生命周期」的字段（如 `PLANNED` / `TRAVELING` / `ACTIVE`） |

---

## D1-DEC-13 · Query 与未来 World Command 的边界

### 问题

World Query 与未来的写入入口（World Command）是什么关系？

### 依据（D0-DEC-6 / `D0G-3`）

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

### 建议冻结

| 规则 | 内容 |
|------|------|
| **WQ-47** | World Query = **读取入口**；World Command = **写入入口**；两者**职责分离** |
| **WQ-48** | D-1 **不实现** World Command（写入治理属 **D-4**） |
| **WQ-49** | Query **不得**为了「顺带修一下」而执行任何写入（与 `WQ-5` 一致） |
| **WQ-50** | Query 与 Command **不得共用一个「万能 World 接口」**（否则会重演 D-0 §53 的「万能 action 分发器」问题） |
| **WQ-51** | 未来若引入 Command，**不得**把 Query 改造为「Query + Command 混合体」 |

---

## D1-DEC-14 · Query 是否可以被 AgentRuntime 使用

### 问题

`AgentRuntime` 是否可以直接调用 World Query？

### 事实

```text
当前 AgentRuntime：
  - receive_event / perceive / should_wake（已实现）
  - build_context → ContextAssembler → AgentContext（B5-2）
  - think → IntentSet Stub（C-2）
  - decide / execute → P0-3A Stub
  - Runtime 不直接访问 main.data（AR-2）
```

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| A | D-1 即让 `AgentRuntime` 调用 Query | 会改动 Runtime 行为 → **超出 D-1 Foundation 范围** |
| B | D-1 **只建立 Query**，`AgentRuntime` **暂不接入**（**建议**） | Query 暂时无生产调用者 |
| C | D-1 让 Runtime 通过 Query 替换部分 `build_context` 数据来源 | 需改动 Context 链，违反 `WQ-32` |

### 建议：**B**

**理由：**

1. D-1 目标是 **Foundation**（建立只读入口），不是接入
2. 接入 `AgentRuntime` 会同时触及 **Context 链（CA-6 ～ CA-9）** 与 **Runtime 生命周期（AR-1 ～ AR-10）**，必须走 Contract Change
3. 让 Query 先以「零调用者」状态存在，可先通过 Architecture Tests 验证其只读性，再考虑接入

**因此建议冻结：**

| 规则 | 内容 |
|------|------|
| **WQ-52** | D-1 建立 Query，但 **`AgentRuntime` 暂不调用它** |
| **WQ-53** | `AgentRuntime` 接入 Query 属**后续阶段**，必须走 Contract Change |
| **WQ-54** | D-1 **不修改** `agent/runtime.py`（与 `AR-8` / `AR-9` 一致） |
| **WQ-55** | Query 必须**可在无 Runtime 的情况下独立测试** |

> **若架构侧选择 A 或 C：** 必须在 D-1 Contract 中同时裁定对 `AR-2`（Runtime 不直接访问 main.data）与 `CA-6` ～ `CA-9` 的影响。

---

## D1-DEC-15 · Query 是否可以被 Frontend 直接使用

### 问题

现有 HTTP 读接口（`GET /api/map` 等）是否改用 World Query？前端能否直接调 Query？

### 事实

```text
现有前端读接口（部分）：
  GET /api/map        → ext_room.py:144（且写 presence）
  GET /api/messages   → ext_room.py:50（且写 rooms/messages）
  GET /api/economy    → ext_econ.py:103（且写 wallets）
  GET /api/presence   → main.py:719（且裁剪 presence）
  GET /api/ai/status  → ext_ai.py:1961
  GET /api/date/status→ ext_date.py:619
  GET /api/shop/menu  → ext_shop.py:429
  ...

前端缓存（D-0 D0-024 / D0-043）：
  mapData / worldSnapshot / restoreCache / localStorage
```

### 候选

| 方案 | 内容 | 风险 |
|------|------|------|
| A | 现有 HTTP 接口改调 Query | **修改旧行为** → 违反「不修改 ext_ai/ext_world/ext_room 旧行为」 |
| B | 前端直接新增调用 Query 端点 | **改前端** → D-1 不做前端 |
| C | **D-1 只为后端/Agent 提供 Query；HTTP 层与前端暂不变动**（**建议**） | Query 暂无 HTTP 出口 |

### 建议：**C**

**理由：**

1. 用户明确要求：**不要修改 `ext_ai.py` / `ext_world.py` / `ext_room.py` 的旧行为**
2. 现有读接口**带有写副作用**（`D0-019`），若改调只读 Query，会**静默改变现有行为**（副作用消失可能破坏依赖它的逻辑）
3. D-0 已把前端 World mutation 归入 **D 类（D-4 / D-6）**

**因此建议冻结：**

| 规则 | 内容 |
|------|------|
| **WQ-56** | D-1 **不修改** 任何现有 HTTP 读接口，**不修改** 前端 |
| **WQ-57** | D-1 的 Query 是**内部只读入口**，不强制对外暴露 |
| **WQ-58** | 若后续要暴露 HTTP 端点，必须**新增**端点（不得替换旧的），且需 Contract Change |
| **WQ-59** | Query **不得**被前端直接用于「回写 World」的任何路径（与 `INVARIANT-14` 一致） |
| **WQ-60** | 现有读接口的**写副作用**（`D0-019`）属 **D-4 / D-6** 处理，**D-1 不动** |

---

## 4. 边界关系总图（D-1 冻结候选）

```text
                        ┌──────────────────────────┐
                        │        main.data         │
                        │   （唯一 World 存储位置）  │
                        └────────────┬─────────────┘
                                     │
                  ┌──────────────────┼──────────────────┐
                  │                  │                  │
                  ▼                  ▼                  ▼
        ┌─────────────────┐  ┌──────────────┐  ┌────────────────┐
        │  WORLD QUERY    │  │  AgentState  │  │ Context        │
        │  （D-1 新增）    │  │  （只读投影）  │  │ Providers      │
        │  READ ONLY      │  │              │  │ （B2 已验收）   │
        └────────┬────────┘  └──────┬───────┘  └───────┬────────┘
                 │                  │                  │
      ┌──────────┴──────────┐       │                  │
      │                     │       │                  │
      ▼                     ▼       ▼                  ▼
   Agent Core          Application  ContextAssembler → AgentContext
   （D-1 暂不接入）      （未来）

      ✗ 不得反向：Query → AgentState → Query
      ✗ 不得反向：Query → main.data（写）
      ✗ 不得：Query 产生 / 消费 Event
      ✗ 不得：Query 返回正式 Activity
      ✗ 不得：Query 执行写入（含清理）
      ✗ 不得：Query 调用 LLM
```

---

## 5. D-1 建议的 Query 目录（候选清单，待 Contract 冻结）

> **本清单是候选，不是实现授权。** 具体接口形状在 **D-1 Contract** 冻结。
> 每条注明：**当前 schema 是否支持**。

### 5.1 可支持（schema 已具备）

| # | 候选查询 | 数据来源 | 备注 |
|---|---------|---------|------|
| Q-01 | `get_agent_location(ai)` | `ai_location[ai]` | 可能不可解析（G-7） |
| Q-02 | `get_agent_owner(ai)` | `user_ais` / `owner_of_ai` | 注意猴补丁覆盖（`D0-036`） |
| Q-03 | `get_agent_wallet(ai)` | `wallets[ai]` | —— |
| Q-04 | `get_agent_affection(ai)` | `affection[ai]` | —— |
| Q-05 | `get_room(room)` | `rooms[room]` | 需 `full_room_name` 归一 |
| Q-06 | `get_building(bid_or_name)` | `buildings` | 需 `resolve_building`（可能 AMBIGUOUS） |
| Q-07 | `get_building_rooms(bid)` | `buildings[bid].rooms` | 直接支持 |
| Q-08 | `get_npcs_in_building(bid)` | `npcs[bid]` | 直接支持 |
| Q-09 | `get_world_time()` | `now_str()` | UTC+8 |
| Q-10 | `get_room_time(room)` | `room_time(room)` | 房间虚拟时钟 |
| Q-11 | `get_users_present_in_room(room)` | `presence` | 仅真人（G-4） |
| Q-12 | `get_ais_in_room(room)` | `ai_location` 反查 | O(ais) |
| Q-13 | `get_user_ais(user)` | `user_ais[user]` | 直接支持 |
| Q-14 | `is_agent_dating(ai)` | `dates` | **Legacy 状态，非 Activity** |
| Q-15 | `is_agent_working(ai)` | `work_sessions` | **Legacy 状态，非 Activity** |
| Q-16 | `is_agent_following(ai)` | `ai_follow` | **Legacy 状态** |
| Q-17 | `get_agent_current_activity_legacy(ai)` | `_derive_activity` | **必须标 `derived=True`**（WQ-43） |

### 5.2 当前 schema **不支持**（必须返回 `UNSUPPORTED`）

| # | 候选查询 | 为什么不能回答 |
|---|---------|--------------|
| Q-U1 | `get_map_of_building(bid)` | 无 World→Map 关系（G-2）；`region` 只是标签 |
| Q-U2 | `get_npc_location(npc)` | NPC 无位置字段（G-3） |
| Q-U3 | `get_agents_in_building(bid)` | 只能经「建筑 → rooms → ai_location 反查」间接得到；是否属 `UNSUPPORTED` 或「有限支持」需裁决 |
| Q-U4 | `query_places(purpose=..., open_now=...)` | 无 `purpose` / 营业时间 / 用途字段（D-0 Preflight §66 的示例**当前无法实现**） |
| Q-U5 | `get_relationship(ai, user)` | 只有 `affection` 数值，无 relationship 结构 |
| Q-U6 | `find_route(origin, destination)` | 无路径 / 距离 / 连通性数据 |
| Q-U7 | `get_available_places(ai)` | 无「可达性」建模 |
| Q-U8 | `get_activity(activity_id)` | Activity 属 D-2（`WQ-42`） |

> **Q-U4 特别重要：** D-0 Preflight §66 把 `query_places(purpose="medical", urgency="high", open_now=True)` 当作 World Query 的目标示例，
> 但**当前 schema 完全没有这些字段**。这必须在 D-1 Contract 中**明确记录为「当前不支持」**，
> 不得为了让示例成立而临时发明字段（那会违反 `WQ-3` / `WQ-4`）。

---

## 6. 与 D-0 已冻结契约的一致性检查

| D-0 规则 | D-1 是否可满足 | 本 Preflight 落点 |
|---------|---------------|------------------|
| `D0G-1`（`main.data` 唯一存储） | ✅ | `WQ-13` / `WQ-16` 返回副本，不新建存储 |
| `D0G-2`（位置 ≠ 治理） | ✅ | D-1 是治理的**第一步（读取侧）** |
| `D0G-4`（禁止第二个 World） | ✅ | `WQ-13`；不建 WorldStore（D1-DEC-3 排除方案 C） |
| `D0G-5`（事实基线） | ✅ | §2 以当前代码 + Audit 为基线 |
| `AC-7`（禁止多 Activity 真相） | ✅ | `WQ-42` ～ `WQ-46` |
| `AC-9`（Activity 属 D-2） | ✅ | `WQ-42` |
| `EV-9`（`agent.Event` 唯一 Domain Event） | ✅ | `WQ-37` / `WQ-38` |
| `EV-14`（不实现新 Event Bus） | ✅ | `WQ-37` |
| `ME-22` / `ME-23`（Memory 不进 Context / 不作依赖） | ✅ | D-1 不触碰 Memory；`WQ-63`（见 §7） |
| `AS-2`（placeholder 禁作决策输入） | ✅ | D1-DEC-4 禁止 Query 读 AgentState |
| `AS-3`（AgentState 不反向写入） | ✅ | Query 不回写 |
| `AR-2`（Runtime 不直接访问 main.data） | ✅ | `WQ-52` ～ `WQ-55`（D-1 不接入 Runtime） |
| `CA-6` ～ `CA-9`（Context 链冻结） | ✅ | `WQ-32` / `WQ-35` |
| `WQ-1` ～ `WQ-4`（原 World Query 条款） | ✅ | 本 Preflight 完全承接并细化 |
| `WQ-3`（不修改 buildings/rooms/npcs schema） | ✅ | `WQ-10` / `WQ-12` |
| `WQ-4`（不引入新索引） | ✅ | `WQ-10` |
| `SC-1` ～ `SC-5`（不实现 Scheduler） | ✅ | D-1 不涉及 |
| `CP-1` ～ `CP-8`（Capability） | ✅ | D-1 不实现 Capability |
| `WT-1` ～ `WT-7`（World Tick Blocker） | ✅ | **D-1 不修**（`WQ-61`，见 §7） |

---

## 7. 本 Preflight 追加的边界条款（候选）

除以上 14 项决策外，建议追加：

| 规则 | 内容 |
|------|------|
| **WQ-61** | D-1 **不修** World Tick 可靠性缺陷（`D0-030` / `D0-031`）—— 那是 **D-3 前置 Blocker**（`WT-1`） |
| **WQ-62** | D-1 **不修改** `ext_ai.py` / `ext_world.py` / `ext_room.py` / `main.py` 的**任何现有行为** |
| **WQ-63** | D-1 **不触碰** Memory（不修 `ext_memory.py` / `ext_mem.py`，不接 Recall，不读 `ai_memories` 作为 Fact） |
| **WQ-64** | D-1 **不实现** Capability / Activity / Movement / World Command |
| **WQ-65** | D-1 **不新增** `main.data` 顶层 key（World Query 不得引入自己的存储） |
| **WQ-66** | D-1 **不新增** 持久化文件 / 数据库 / 缓存文件 |
| **WQ-67** | D-1 的产物必须**可独立测试**，且测试**只依赖标准库**（与 D-0 Tests 一致） |
| **WQ-68** | D-1 必须能被**删除而不影响任何现有功能**（对应 `INVARIANT-19`：Feature Removability） |

> `WQ-68` 是 D-1 最重要的验收性质：
> **因为 D-1 不接入 Runtime、不改旧接口，所以「删掉 Query」必须不改变任何现有行为。**
> 这同时是 D-1 「零风险」的证明。

---

## 8. 本 Preflight 发现的新风险（必须上报）

| # | 风险 | 说明 |
|---|------|------|
| **R-1** | **D-0 Tests 的 `ROOT` 解析因目录整理而失效** | `PROJECT_V3.1_MASTER.md` 与 `V3.1_PRODUCT_GUIDE.md` 已迁入 `docs/`。`docs/test_d0_world_activity_capability.py` 原用 `parent.parent` 推导 ROOT，会**误判 ROOT 为 `docs/`**，导致全部用例失效。**本轮已修复为「标记探测」**（向上寻找同时含 `main.py` + `agent/` + `ext/` 的目录），并新增 3 项断言（`T11.3` / `T11.4`）防止再次发生 |
| **R-2** | **`docs/` 内出现重复的 Inventory** | 同时存在 `V3.1_GLOBAL_ARCHITECTURE_INVENTORY.md`（根）与 `docs/V3.1_GLOBAL_ARCHITECTURE_INVENTORY.md`。按 `BL-2`，两者都**不再是当前事实依据**；但重复副本本身构成潜在的文档 SOT 问题，建议在 D-0 Closure 收尾时统一 |
| **R-3** | **`agent/state.py:15` 仍直接 import main** | `D0-014` 记录的待处理项。D-1 建立 Query 后，该模块的读取入口归属必须裁定 |
| **R-4** | **Contract `WQ-4`（不引入新索引）与 G-1（O(n) 反查）冲突** | 若 World Query 进入高频路径，线性反查成本会成为问题。本 Preflight 建议「不新增索引」，但需架构侧确认是否接受该性能边界 |
| **R-5** | **D-0 Tests 仍为 NOT RUN** | 工作区 Shell / Python / Git 均不可执行（`0xC0000142`）。**D-1 的测试同样会面临同一限制**，需提前规划在可执行环境中运行 |

> **R-1 已在本轮修复**（属既有 D-0 产物的适配性修复，未改动任何生产代码）。
> **R-2 ～ R-5 仅记录，等待架构侧裁决。**

---

## 9. D-1 完成后的正确顺序（不得跳步）

```text
D-1 Preflight（本文件）
    ↓
架构审核
    ↓
D-1 Contract Change（新增 Contract §5D，冻结 Query 边界与接口形状）
    ↓
D-1 Architecture Tests（docs/test_d1_world_query.py）
    ↓
D-1 Implementation（新增只读 Query 模块）
    ↓
D-1 Tests 运行（需可执行环境）
    ↓
D-1 验收
    ↓
D-2 Activity Contract
```

**禁止：**

```text
Preflight → 直接大量写代码
```

---

## 10. 本 Preflight 明确不做的事

```text
❌ 不实现 World Query
❌ 不实现 Activity（D-2）
❌ 不实现 Capability（D-4）
❌ 不实现 Movement / Location Continuity（D-3）
❌ 不实现 World Command（D-4）
❌ 不修改 ext_ai.py / ext_world.py / ext_room.py / main.py 的现有行为
❌ 不修改任何 Provider / ContextAssembler / AgentRuntime
❌ 不修改前端
❌ 不修 Memory
❌ 不修 World Tick 可靠性缺陷（D-3 前置）
❌ 不新增 main.data 顶层 key
❌ 不新增持久化文件 / 数据库 / 缓存
❌ 不建立第二个 World / WorldStore
❌ 不实现新 Event Bus
❌ 不进入 D-2
```

---

## 11. D-1 Preflight 检查清单

在宣布 D-1 Preflight 通过前，必须逐项确认：

### Query 定义

- [ ] World Fact 定义明确（D1-DEC-1）
- [ ] World Query 职责与绝对边界明确（D1-DEC-2）
- [ ] READ ONLY 与「无副作用」明确（`WQ-5` ～ `WQ-9`）

### 数据接入

- [ ] Query 是否读 `main.data` 已裁决（D1-DEC-3）
- [ ] Query 是否读 `AgentState` 已裁决（D1-DEC-4）
- [ ] Map / Building / Room 反查范围已裁决（D1-DEC-5）

### 返回语义

- [ ] 返回结构已裁决（D1-DEC-6）
- [ ] `FOUND` / `ABSENT` / `UNKNOWN` / `UNSUPPORTED` / `AMBIGUOUS` 已裁决（D1-DEC-7）
- [ ] 时间参数语义已裁决（D1-DEC-8）

### 访问范围

- [ ] 是否允许读其他 AI / NPC / User 已裁决（D1-DEC-9）
- [ ] 可见性最小规则已裁决（`WQ-27` ～ `WQ-31`）

### 边界

- [ ] Query ↔ Context Provider 边界已裁决（D1-DEC-10）
- [ ] Query ↔ Event 边界已裁决（D1-DEC-11）
- [ ] Query ↔ Activity 边界已裁决（D1-DEC-12）
- [ ] Query ↔ World Command 边界已裁决（D1-DEC-13）
- [ ] Query ↔ AgentRuntime 接入关系已裁决（D1-DEC-14）
- [ ] Query ↔ Frontend / HTTP 边界已裁决（D1-DEC-15）

### 一致性

- [ ] 与 D-0 `D0G-*` / `AC-*` / `EV-*` / `ME-*` / `AS-*` / `AR-*` / `CA-*` / `CP-*` / `WT-*` 全部一致（§6）
- [ ] 现有 schema 支持 / 不支持项已如实登记（§5.1 / §5.2）
- [ ] 新风险已上报（§8）
- [ ] 未新增 OPEN QUESTION（或已明确记录）

---

## 12. D-1 Preflight 状态

```text
Status:
    PRE-FLIGHT

Implementation:
    NOT AUTHORIZED

Next:
    Review / Resolve 14 Decisions + WQ-5 ～ WQ-68

After Approval:
    D-1 Contract Change（Contract §5D）

After Contract:
    D-1 Architecture Tests

After Tests:
    D-1 Implementation
```

**End of D-1 World Query Preflight**
