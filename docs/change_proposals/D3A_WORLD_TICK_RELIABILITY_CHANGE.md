# D-3A · World Tick Reliability — Contract Change Proposal

**Document Type:** Contract Change Proposal（提案，尚未生效）
**Phase:** D-3A（D-3 Movement Continuity 的前置条件）
**Status:** PROPOSED — 等待架构侧审核
**Implementation Status:** **NOT AUTHORIZED**
**Date:** 2026-09-30

**上游：**
- D-0 **SEALED**（§5C，CC-20260930-04）
- D-1 **SEALED**（§5D，CC-20260930-05）
- D-2 **SEALED**（§5E，CC-20260930-06）
- **D-3 Preflight 事实盘点报告**（本次提案的事实依据）

**本文件不改动任何代码、不修改 Contract、不新增测试。**
它只提出 Contract Change 提案 + 实现设计 + 测试设计，供架构侧裁决。

---

# 1. Change Motivation

## 1.1 为什么现有设计无法支撑 D-3 Movement Continuity

D-3 的目标是 **Movement Continuity**：

```text
Goal / Commitment / Activity / Decision
        ↓
Movement Capability
        ↓
Location Change
        ↓
Event
        ↓
Agent Perception（下一轮）
```

这条链的**输入端**是 **World Tick 产出的「到达」世界事实**。
若 Tick 不能可靠地产生并提交「到达」，D-3 的每一环都失去可靠输入。

**当前 Tick 存在两个已由代码证实的缺陷**（见 D-3 Preflight 报告）：

### `D0-030` — World → Memory 调用异常截断 World Tick

```text
ext/ext_world.py:310   threading.Thread(target=ai_spot_tick, daemon=True).start()
                       → 裸线程，**无 asyncio 事件循环**

ext/ext_world.py:129 / 157 / 222 / 251 / 269
                       asyncio.create_task(enqueue_event(...))
                       → RuntimeError: no running event loop

ext/ext_world.py:306-307
                       except Exception: pass
                       → 吞掉异常；但 `for u, ais` 循环**已被整体跳出**
```

**关键事实（已确认）：**

| 事实 | 证据 |
|------|------|
| 5 处 Memory 调用全部在**无事件循环的裸线程**中调用 `create_task` | L310 + L129/157/222/251/269 |
| `enqueue_event` 内部的「无 loop 兜底」**永远不可达** | 兜底位于**协程体内**（`ext_memory.py:104-114`）；`create_task` 在**进入协程体之前**就抛错 |
| 4 处 Memory 调用位于对应 `save_data()` **之前** | `_try_story` L129→L140；`_arrive` L222→L232、L251→L261、L269→L279 |
| 异常**跳过** `save_data()` | 同上 |
| 异常**跳出整轮剩余 AI** | `except` 在 `for` 循环**外**（L286 内、L306 外） |
| 异常被**静默吞掉**（无日志 / 无计数） | L306-307 `except Exception: pass` |

### `D0-031` — 到达状态提交顺序错误

```text
ext/ext_world.py:301-305
    if st.get('last_bid') != bid:
        prev = st.get('last_bid')
        st['last_bid'] = bid                     ← 【提交】早于【处理】
        if prev and bid:
            _arrive(ai, bid, ...)                ← 【处理】

ext/ext_world.py:144-157（_arrive 内）
    st = _state(ai)                  ← 同一 ai → 同一 dict
    prev_bid = st.get('last_bid')    ← 已被上面设为 bid
    if prev_bid != bid and bid:      ← 恒为 False → **死代码**
        asyncio.create_task(enqueue_event(action="初访建筑"/"到达建筑" ...))
```

**四种位置情形的实际结果（已确认）：**

| 情形 | `prev` | `bid` | `_arrive` 是否调用 |
|------|--------|-------|------------------|
| 本进程内**首次进入建筑** | `None` | 有效 | ❌ **不调用** |
| **建筑 → 建筑** | 有效 | 有效 | ✅ 调用 |
| **离开建筑** | 有效 | `None` | ❌ 不调用（`last_bid` 重置为 `None`） |
| **无效位置** | `None` | `None` | ❌ 不调用 |

**并存在双重永久丢失：**

```text
last_bid 在 _arrive 之前提交（L303）
last_ts  在 _arrive 开头、Memory 调用之前提交（L148）

→ 一次失败 = 该次到达永久漏处理
  （除非 AI 离开建筑再重新移动，且 600 秒节流已过）
```

## 1.2 风险（为什么必须在 D-3 之前修）

| # | 风险 | 影响 |
|---|------|------|
| **R-1** | **到达事件可能丢失** | D-3 的 Movement Continuity **无可靠输入**；Agent 感知不到「我到了」 |
| **R-2** | **世界状态可能无法保存** | `save_data()` 被跳过 → `ai_spot_state` / `story_rhythm` / `trails` / `timeline` / `messages` 的修改可能不落盘 |
| **R-3** | **Tick 可靠性不足会污染后续全部阶段** | Movement / Activity / Goal / Commitment 都建立在「世界事实可靠推进」之上 |
| **R-4** | **非核心副作用成为核心路径的必要条件** | 违反「世界核心状态推进不能依赖非核心副作用成功」这一原则 |
| **R-5** | **失败不可观测** | `except Exception: pass` 使任何异常在运行期完全不可见，无法诊断 |
| **R-6** | **单点失败扩散为全局失败** | 一个 AI 的异常使**同轮其余 AI** 全部不被处理（30 秒空窗） |

**架构原则（本提案的核心命题）：**

> **世界核心状态推进不能依赖非核心副作用成功。**

其中：

| 类别 | 归属 |
|------|------|
| **World SOT 更新** | **核心行为** |
| **Event 记录** | 世界行为的一部分，但**必须明确失败策略** |
| **Memory** | **非阻塞副作用**，不得成为 World Tick 的运行条件 |

---

# 2. Contract Changes

> **以下为提案内容，尚未写入 `docs/V3.1_ARCHITECTURE_CONTRACT.md`。**
> 生效须经架构侧批准 + 独立 Contract Change 流程。

## 2.0 变更总览

| 规则 | 现状 | 提案后 |
|------|------|--------|
| **WT-4** | 「只做最小可靠性修复：`Memory failure → 不能杀死 World Tick`」 | 升格为**强制规则**：Memory 必须被完全隔离 |
| **WT-5** | 「**禁止**借该修复顺手修 Memory」 | 追加：**Event enqueue 失败不得破坏 World 状态，且必须可观察** |
| **WT-6** | 「若必须修，走独立 Contract Change」 | **重新定义**为 **Arrival Transaction Ordering** |
| **WT-7** | 「`D0-031` 的到达语义问题必须在 D-3 之前处理」 | **扩展**为 **Arrival Failure Recovery** |

> ⚠️ **编号冲突提示：** 现行 `WT-6` 是「流程规则（走独立 Contract Change）」，`WT-7` 是「时点规则」。
> 本提案要把它们**重新定义为行为规则**，属于**语义改写**，须架构侧明确确认是否允许复用编号。
> 若架构侧倾向保留原编号语义，建议改为 **新增 `WT-8` ～ `WT-11`**（见 §2.5 备选方案）。

---

## 2.1 WT-4 Change — Memory Failure Isolation

### 旧

```text
WT-4：只做最小可靠性修复：Memory failure → 不能杀死 World Tick；
      禁止顺便重写 ext_world。

→ 定性为「修复目标」，未给出强制规则。
```

### 新

```text
Memory failure MUST NOT stop World Tick execution.
```

### 强制要求

| 编号 | 要求 |
|------|------|
| **WT-4.1** | Memory 异常**必须被隔离** —— 不得传播出 Memory 调用点 |
| **WT-4.2** | World 状态推进（`_arrive` 主干、`save_data()` 安排）**必须继续** |
| **WT-4.3** | **不允许**因为 Memory unavailable 导致 Tick abort |
| **WT-4.4** | Memory 调用**不得**位于任何核心状态提交语句之前而阻断它 |
| **WT-4.5** | 本规则**不启用** Memory（`ME-21` 仍生效）；只保证「Memory 坏了也不影响世界」 |

---

## 2.2 WT-5 Change — Event Enqueue Failure Must Not Corrupt World State

### 旧

```text
WT-5：禁止借该修复顺手修 Memory。

→ 这是「范围限制」，不是「失败语义」规则。
```

### 新

```text
Event enqueue 失败不得破坏 World 状态，且必须可观察。
```

### 强制要求

| 编号 | 要求 |
|------|------|
| **WT-5.1** | Event enqueue 失败**必须可观察**（日志 / 计数 / 结构化记录），**不得**再次 `except: pass` |
| **WT-5.2** | Event 失败**不能阻止** `save_data()` |
| **WT-5.3** | **不允许 silent failure** —— 至少一次可检索的记录 |
| **WT-5.4** | Event 失败**不得**改变 World 事实（不得因记录失败而回滚 / 篡改世界状态） |
| **WT-5.5** | 本规则**不修改 Event 架构**（`EV-9` ～ `EV-14` 不变）；`enqueue_event` 仍属 **Legacy Memory ingestion**，**不是** Domain Event |

> **说明：** 现行 `WT-5`（禁止顺手修 Memory）**继续有效**，作为附加约束保留。

---

## 2.3 WT-6 Change — Arrival Transaction Ordering（**新增语义**）

### 旧

```text
WT-6：若必须修，走独立 Contract Change，不夹带在 D-0 / D-1 中。

→ 流程规则；非行为规则。
```

### 新

```text
Arrival processing 必须满足：

    detect
      ↓
    process
      ↓
    commit state
```

### 禁止

```text
detect
  ↓
commit state        ← 禁止：先提交后处理
  ↓
process
```

### 强制要求

| 编号 | 要求 |
|------|------|
| **WT-6.1** | **状态提交必须在处理成功之后** —— `last_bid` / `last_ts` 不得在 `_arrive` 之前提交 |
| **WT-6.2** | 处理失败时**不得提交**状态（保留重试机会） |
| **WT-6.3** | 处理成功时**必须提交**状态（防止重复触发） |
| **WT-6.4** | `_arrive` 内部**不得**再依赖「已被外部改写的检测变量」判断是否首次到达；首次 / 再次到达的判定必须基于**处理前捕获的快照** |
| **WT-6.5** | 到达判定必须覆盖**全部四种情形**（首次进入 / 建筑→建筑 / 离开 / 无效），语义须显式定义，不得依赖隐式 diff |

---

## 2.4 WT-7 Change — Arrival Failure Recovery（**新增语义**）

### 旧

```text
WT-7：D0-031 的到达语义问题必须在 D-3 之前处理，否则 D-3 无可靠输入。

→ 时点规则；未定义失败恢复语义。
```

### 新

```text
如果 _arrive() 失败，
则下一次 Tick 必须仍然能够重新处理。
```

### 禁止的终态

```text
failed once
    +
state already committed
    =
permanent loss          ← 必须被消除
```

### 强制要求

| 编号 | 要求 |
|------|------|
| **WT-7.1** | 一次到达处理失败后，**后续 Tick 必须仍能重新处理同一次到达** |
| **WT-7.2** | **禁止**出现「失败一次 + 状态已提交 = 永久丢失」 |
| **WT-7.3** | 重试**必须有界**：不得无限重试；必须有节流 / 退避 / 次数上限 |
| **WT-7.4** | 重试**不得**重复产生副作用（幂等要求；见 `WT-6.3`） |
| **WT-7.5** | 重试耗尽后，**必须可观察**（与 `WT-5.1` 同一可观测性要求），且**不得**阻断后续到达处理 |

---

## 2.5 备选方案（编号策略）

若架构侧认为 **不应复用 `WT-6` / `WT-7` 编号**（因其原有语义是流程 / 时点规则），则本提案可改为：

```text
保留：WT-1 ～ WT-7 原文不动
新增：WT-8   Memory Failure Isolation            （= 本文 §2.1）
      WT-9   Event Failure Observability         （= 本文 §2.2）
      WT-10  Arrival Transaction Ordering        （= 本文 §2.3）
      WT-11  Arrival Failure Recovery            （= 本文 §2.4）
```

> **本项为 OPEN QUESTION，由架构侧裁决。** 见 §5 `OPEN-3A-1`。

---

# 3. Implementation Design Review

> **本节只设计，不实现。**
> 以下所有方案都**不修改** `ext_memory.py` 的数据结构、不引入新的 Memory 架构、**不重写 `ext_world.py`**。

## A. Memory Failure Isolation

### A.1 现状问题（精确复述）

```text
调用方写法（5 处）：
    asyncio.create_task(enqueue_event(...))

执行顺序：
    ① 构造协程对象 enqueue_event(...)        ← 不执行协程体
    ② asyncio.create_task(coro)              ← 要求当前线程有**运行中**的 loop
       └→ 裸线程 → RuntimeError: no running event loop
    ③ 【永不到达】协程体内部（含无-loop 兜底）
```

**关键洞察：** `ext_memory.enqueue_event` **本身已经具备**「无 loop 时自建 loop」的兜底（`ext_memory.py:104-114`）。**它当前失效，纯粹是因为调用方用 `create_task` 绕过了协程体的执行。**

### A.2 设计选项

| 选项 | 做法 | 是否需要同步 wrapper | 是否需要 background queue | 是否修改 Memory |
|------|------|------------------|------------------------|----------------|
| **O-1（最小）** | 把 `create_task(coro)` 改为**直接调用并驱动协程**，整段包在 `try/except` 中 | ✅ 需要（局部 helper） | ❌ 不需要 | ❌ 不修改 |
| **O-2** | 引入 Tick 侧「非阻塞副作用队列」，由持有 loop 的一方消费 | ✅ 需要 | ✅ 需要 | ❌ 不修改 |
| **O-3** | 不改调用方，改由 Memory 提供**同步入口** | ✅ 需要 | ❌ 不需要 | ⚠️ **会修改 Memory** → **本阶段禁止** |

### A.3 推荐：**O-1（最小隔离）**

**设计要点：**

```text
在 ext_world 内新增一个**局部** helper（不进 Memory、不进 main）：

    def _safe_enqueue(**kwargs) -> bool:
        """
        尽力记录一条 Legacy Memory 事件。
        返回是否成功；**任何失败都不得传播**。
        """
        try:
            coro = enqueue_event(**kwargs)
            # 在裸线程中安全驱动一次协程（不依赖 create_task）
            ...驱动...
            return True
        except Exception as exc:
            # 可观察：记录（WT-5.1）
            record_failure("memory_enqueue", exc)
            return False
```

**必须回答的边界问题：**

| # | 问题 | 设计回答 |
|---|------|---------|
| A-1 | **exception 如何处理** | 在 `_safe_enqueue` 内**全部捕获**；返回 `bool`；**绝不传播**（`WT-4.1`） |
| A-2 | **asyncio / thread 边界如何处理** | Tick 是**裸线程无 loop**。因此**不得**使用 `create_task`。驱动方式二选一（**OPEN**，见 §5 `OPEN-3A-2`）：<br>**(a)** 调用 `enqueue_event()` 得到协程后，用一个**新建的临时 loop** `run_until_complete` 驱动（与 Memory 内部兜底同构，但不修改 Memory）<br>**(b)** 直接依赖 Memory 自身的兜底：把 `create_task(coro)` 改为「构造协程 → 交给一个**调用 Memory**的同步驱动」<br>**两方案都需要 Tick 侧的驱动逻辑** |
| A-3 | **是否需要同步 wrapper** | **需要** —— 因为 Tick 是同步裸线程，必须有一个同步入口负责「驱动协程 + 捕获异常」。该 wrapper **放在 `ext_world` 内部**，不改 Memory |
| A-4 | **是否需要 background queue** | **本阶段不需要**（`WT-4` 最小化原则）。若采用 O-2 队列，属**结构性改动**，必须独立 Contract Change |
| A-5 | **是否允许 Tick 阻塞** | ⚠️ **必须由架构侧裁决**（见 §5 `OPEN-3A-3`）：<br>当前 Tick 周期 30 秒；每个 AI 每次到达至多 1 次 Memory 调用；同步驱动会引入**有界的文件 I/O 阻塞**。<br>「非阻塞副作用」在架构上指**因果非必需**（失败不影响世界），<br>**不一定**指「零阻塞耗时」。**此语义必须显式冻结，否则实现无法判定合规** |
| A-6 | **失败是否重试** | **Tick 内部不重试**。Memory 的**批量提炼**（`ext_memory` 夜间批处理）是它自己的补偿路径；Tick 只负责「尽力投递 + 记录失败」 |

### A.4 明确不做（禁止项）

```text
❌ 重写 Memory 系统
❌ 修改 Memory 数据结构（pending / summary / events 文件格式）
❌ 引入新的 Memory 架构（新 DB / 新队列服务 / 新 Provider）
❌ 把 Memory 变成 Tick 的必要依赖
❌ 启用 Memory Runtime（ME-21 仍生效）
❌ 修改 agent.Event / Event Bus 架构
```

---

## B. Arrival Transaction Ordering

### B.1 现状问题

```text
detect（L301 last_bid != bid）
   ↓
commit state（L303 st['last_bid'] = bid）      ← 提前提交
   ↓
process（L305 _arrive(...)）
   └ 内部再 L148 提前提交 last_ts               ← 第二处提前提交
   └ 失败 → 状态已提交 → 永久丢失
```

### B.2 目标语义

```text
arrival detected
      ↓
arrival effects processed      ← 全部副作用在此完成（含副作用失败处理）
      ↓
state committed                ← 只有成功才提交
```

### B.3 设计要点

**B-1 检测阶段（read-only）**

```text
只做检测，不写状态：

    detected = (st['last_bid'] != bid)
    prev_bid = st['last_bid']        ← 捕获**处理前快照**
```

**B-2 处理阶段**

把**处理前快照**传入 `_arrive`，让它自己决定「初访 / 到达」：

```text
_arrive(ai, bid, building, prev_bid=prev_bid)
    # 内部不再读取已被改写的 st['last_bid']
    if prev_bid != bid and bid:
        → 初访 / 到达记录（WT-6.4）
```

**B-3 提交阶段（仅在成功后）**

```text
result = process(...)          # 返回成功 / 失败
if result.ok:
    st['last_bid'] = bid       # 提交
    st['last_ts']  = now       # 提交
else:
    # 不提交 → 下一轮自然重试（WT-7.1）
```

### B.4 如何避免「重复触发」

| 机制 | 设计 |
|------|------|
| **成功即提交** | `WT-6.3`：成功后立即提交 `last_bid` / `last_ts` → 下一轮检测不成立 |
| **保留 `last_ts` 节流** | 现有 600 秒节流**保留**，作为第二道防线（防止 `last_bid` 因其他原因回退时重复触发） |
| **保留 `story_rhythm` / `story_count` 日限** | 剧情分支的重复保护**不变** |

### B.5 如何避免「无限重试」

| 机制 | 设计 |
|------|------|
| **有界重试计数** | `ai_spot_state[ai]` 增加 `arrive_attempts` 计数（**OPEN**：是否允许新增属该 Legacy state 的字段，见 §5 `OPEN-3A-4`） |
| **退避** | 第 N 次失败后延迟（如指数退避，上限若干分钟） |
| **上限后放弃 + 记录** | 超过上限 → 提交状态避免永久卡住 + **记录可观察失败**（`WT-7.5`） |

> ⚠️ **注意：** 新增 `arrive_attempts` 字段属于**修改 Legacy Activity State 的 schema**。
> `AC-2` / `AC-3` 保护的是 `work_sessions` / `dates` / `ai_shop_state` / `instances` 等；
> `ai_spot_state` 是 `ext_world` 自有状态。
> **本项是否允许，必须由架构侧裁决**（`OPEN-3A-4`）。
> 若不允许新增字段，备选：用**内存字典**记录重试（跨重启丢失，但可接受，因 Tick 本就跨重启重置）。

### B.6 如何避免「状态污染」

| 风险 | 设计 |
|------|------|
| 失败后 `last_ts` 已被改写（现值行为） | **不提交** → 无污染 |
| 提交了 `last_bid` 但处理失败 | **不提交** → 无污染 |
| 部分副作用已生效（如 `add_trail` 成功、Memory 失败） | **副作用必须各自幂等或可容忍**；核心提交语义只针对**检测状态**（`last_bid` / `last_ts`），不针对已产生的副作用 |

> ⚠️ **诚实的限制：** 本设计**不能**做到「副作用的全有全无」（无事务机制，且不得引入）。
> 它只保证 **检测状态不被错误提交**，从而**允许重试**。
> 重试可能导致**部分副作用重复**（如 `add_trail` 重复）。
> **这属于 OPEN QUESTION**（`OPEN-3A-5`）：是否接受「至多一次语义退化为至少一次」。

---

## C. save_data Guarantee

### C.1 前置事实（必须精确）

`main.save_data()`（`main.py:245-279`）**不是落盘函数**，而是**防抖调度器**：

```text
save_data()
  ├ _save_pending = True
  ├ 取消上一个 timer
  └ 安排 threading.Timer(0.5, _schedule)
        └ _schedule → asyncio.to_thread(_sync_write)   ← 真正落盘（main.py:231-243）
```

**因此本节的「保存 World 状态」= 「安排落盘」，不是「已落盘」。**

### C.2 三种失败的保证矩阵

| # | 失败类型 | 1. 是否保存 World 状态 | 2. 是否继续处理其他 Agent | 3. 是否记录失败信息 |
|---|---------|---------------------|------------------------|-------------------|
| 1 | **Memory 失败** | ✅ **必须**（`WT-4.2` / `WT-5.2`）<br>Memory 调用**不得**位于 `save_data()` 之前阻断它 | ✅ **必须**（`WT-4.2`）<br>异常必须在**单 AI 粒度**被隔离 | ✅ **必须**（`WT-5.1`）<br>不得 silent |
| 2 | **Event 失败** | ✅ **必须**（`WT-5.2`） | ✅ **必须** | ✅ **必须**（`WT-5.3`） |
| 3 | **Arrival 失败** | ✅ **必须**<br>⚠️ 但**检测状态不提交**（`WT-6.2`）<br>→ 世界状态照常保存，只是该次到达待重试 | ✅ **必须**<br>一个 AI 的到达失败不得影响其余 AI（`WT-7.5` / `WT-5.1`） | ✅ **必须**（`WT-7.5`） |

### C.3 关键设计约束

| 编号 | 约束 |
|------|------|
| **C-1** | `save_data()` 调用**必须**位于所有可能抛错的 Memory / Event 调用**之后不会被执行到**的地方 —— 即：**要么放前面，要么把抛错源包进 `try`** |
| **C-2** | 异常处理的**粒度必须是单 AI**（把 `try` 从「整轮」下移到「单 AI」），否则一个 AI 失败会吃掉整轮（`R-6`） |
| **C-3** | 整轮的**最外层** `try/except` 仍应保留（防止单 AI 异常逃逸导致线程死亡），但**必须记录**，不得 `pass` |
| **C-4** | 「记录失败」在本阶段的最简可行形态：**标准输出日志**（与项目既有 `[WARN]` / `[ERROR]` 风格一致）。是否引入结构化计数 / 指标属后续阶段 |

### C.4 与 Contract 既有规则的相容性

| 既有规则 | 本设计是否冲突 |
|---------|--------------|
| `EV-3`（Event 不修改 `main.data`） | ✅ 不冲突 —— 本设计不改 Event 语义 |
| `EV-10`（`enqueue_event` 是 Legacy Memory ingestion，**不是** Event Bus） | ✅ 不冲突，且本设计**强化**该定性 |
| `ME-21`（Memory = 业务功能关闭状态） | ✅ 不冲突 —— 本设计**不启用** Memory |
| `ME-25`（D 阶段不修 `enqueue_event`） | ⚠️ **需架构侧确认**：本设计**不修改** `ext_memory.py`，只在**调用方**加隔离。若架构侧认为「调用方改变调用方式」也属 `ME-25` 禁止范围，则需调整（见 `OPEN-3A-6`） |
| `AC-2` / `AC-3`（不修改现有活动状态字段） | ⚠️ **需架构侧确认**：本设计可能需要 `ai_spot_state` 新增重试字段（`OPEN-3A-4`） |
| `WT-2`（D-0 不修） | ✅ 不冲突 —— 本提案属 D-3A |
| `WT-4`（禁止顺便重写 `ext_world`） | ✅ 不冲突 —— 本设计是**最小定点修改**，非重写 |

---

# 4. Test Design

> **本节只定义测试，不实现测试。**
> 所有测试都是**行为测试**，必须**真实运行**（`EV-16` / `EV-18` / `EV-19` 的同一原则）。

## 4.0 测试前置条件

| 项 | 说明 |
|----|------|
| 运行环境 | 必须能构造**无事件循环的裸线程**（模拟 `ai_spot_tick` 的真实上下文） |
| 夹具 | 最小 `data`：`user_ais`（≥2 个 AI，用于隔离测试）、`ai_location`、`buildings`（≥2 个）、`ai_spot_state`、`rooms`、`messages` |
| 依赖 | **不得**依赖真实 `ext_memory`（会做文件 I/O）；使用**可控的替身**注入失败 |
| 注意 | 现有 tick 由 `setup()` 启动**真实 daemon 线程**。测试必须能**在不启动真实线程**的情况下调用单轮逻辑 → 需要把「单轮」抽出为可调用单元（见 §5 `OPEN-3A-7`） |

---

## Test WT-R-001 — Memory unavailable does not break Tick

**验证：** Memory 异常时，Tick 继续、`save_data` 执行、其他 Agent 继续。

| 步骤 | 动作 | 断言 |
|------|------|------|
| 1 | 注入 Memory 替身，使其**必然抛错** | — |
| 2 | 构造触发 Memory 调用的场景（如某 AI 到达一个 `shop` 建筑） | — |
| 3 | 执行**一轮** Tick | Tick **未抛错**（`WT-4.1`） |
| 4 | 观察 `save_data` | **被调用**（`WT-4.2` / `WT-5.2`） |
| 5 | 构造**另一个** AI 的独立场景，排在同轮之后 | 该 AI **仍被处理**（`WT-4.2`） |
| 6 | 观察失败记录 | **存在可检索记录**（`WT-5.1` / `WT-5.3`） |

**对应清单项：** D-3 Preflight §5.7 第 1、2、3 项。

---

## Test WT-R-002 — Arrival failure retry

**验证：** Arrival 第一次失败后，下一 Tick 可以重新处理。

| 步骤 | 动作 | 断言 |
|------|------|------|
| 1 | 令 `_arrive` 的**处理阶段**第 1 次必然失败 | — |
| 2 | 执行第 1 轮 Tick | 到达**被检测**；处理**失败** |
| 3 | 检查检测状态 | `last_bid` **未被提交**（`WT-6.2`）<br>`last_ts` **未被提交** |
| 4 | 令第 2 次处理**成功** | — |
| 5 | 执行第 2 轮 Tick | 到达**被重新处理**（`WT-7.1`） |
| 6 | 检查副作用 | 到达效果**已生效**；`last_bid` / `last_ts` **已提交** |

**反例断言（必须同时验证）：**

```text
assert not (failed_once and state_committed)      # WT-7.2
```

**对应清单项：** D-3 Preflight §5.7 第 6 项。

---

## Test WT-R-003 — Arrival success commits once

**验证：** 成功 Arrival 不会重复触发。

| 步骤 | 动作 | 断言 |
|------|------|------|
| 1 | 构造一次成功到达（处理成功） | — |
| 2 | 执行第 1 轮 Tick | 到达**被处理一次** |
| 3 | 检查提交 | `last_bid` / `last_ts` **已提交**（`WT-6.3`） |
| 4 | 位置**不变**，执行第 2、3 轮 Tick | 到达行为**不再触发**（`WT-6.3`） |
| 5 | 位置变为**另一个**建筑，执行 Tick | 到达**重新触发**（语义正确） |

**同时验证节流：**

```text
600 秒内重复移动 → 到达副作用受 last_ts 节流约束
```

**对应清单项：** D-3 Preflight §5.7 第 7 项。

---

## Test WT-R-004 — One Agent failure isolation

**验证：** 一个 Agent 失败，其他 Agent Tick 正常。

| 步骤 | 动作 | 断言 |
|------|------|------|
| 1 | 构造 3 个 AI：A1（**必然失败**）、A2 / A3（正常） | — |
| 2 | 执行一轮 Tick | **A1 失败被隔离**（`WT-4.1`） |
| 3 | 检查 A2 / A3 | **均被正常处理**（`WT-4.2` / `C-2`） |
| 4 | 检查 `save_data` | **被调用** |
| 5 | 检查失败记录 | **仅 A1 的记录**（可定位到具体 AI） |
| 6 | 执行第 2 轮 Tick | Tick 正常；A1 可重试（若属到达类失败） |

**对应清单项：** D-3 Preflight §5.7 第 3 项（并从「整轮跳过」修正为「单 AI 隔离」）。

---

## 4.5 补充测试（本提案建议，非架构侧原始清单）

| 编号 | 名称 | 验证 |
|------|------|------|
| **WT-R-005** | No bare create_task | 静态（AST）：`ext_world.py` 中不存在裸 `asyncio.create_task(...)` 调用 |
| **WT-R-006** | No silent swallow | 静态：不存在 `except Exception: pass`（或等价无记录吞错） |
| **WT-R-007** | Arrival matrix | 「首次进入 / 建筑→建筑 / 离开 / 无效位置」四种情形的 `_arrive` 调用矩阵符合 §2.3 `WT-6.5` |
| **WT-R-008** | save_data not skipped | 对**每一个**会调用 Memory 的分支，断言 `save_data` 仍被调用 |
| **WT-R-009** | Bounded retry | 连续失败 N 次后：重试**有上限**、**不无限循环**、**记录可观察**（`WT-7.3` / `WT-7.5`） |
| **WT-R-010** | Legacy state untouched | [`docs/test_d0_world_activity_capability.py`](../test_d0_world_activity_capability.py) 的 `test_t10_4`（断言 `ai_spot_tick` 结构仍在）**已同步更新**，且 D-0 其余断言无回归 |

---

## 4.6 现有测试的影响（必须处理）

| 现有测试 | 位置 | 影响 |
|---------|------|------|
| `test_t10_2_random_decisions_still_present` | [`test_d0_world_activity_capability.py`](../test_d0_world_activity_capability.py) L1512 | 断言 `random.choices(` 仍在 → 修复**不涉及**该点，**应无影响** |
| `test_t10_4_world_tick_blocker_still_registered` | 同上 L1532–1548 | 断言 `ai_spot_tick` **函数名存在** → 修复后**仍存在**，**应无影响**；但其注释明示「若已做最小可靠性修复，必须走独立 Contract Change 并更新本测试」（L1543–1544）→ **须同步更新注释/断言** |
| `test_j3_d0_legacy_baseline_still_present` | [`test_d2_activity_contract.py`](../test_d2_activity_contract.py) L1721–1728 | 断言 `def ai_spot_tick` 仍在 → **应无影响** |
| `test_f*`（D-2 behavior，`ext_world` 无关） | `test_d2_activity_behavior.py` | **无影响** |

---

# 5. OPEN QUESTIONS

> 按 D-0 接手说明 §34：**不擅自决定，先记录歧义，等待架构侧确认。**

## `OPEN-3A-1` — Contract 规则编号策略

**问题：** 是否允许把 `WT-6` / `WT-7` 从「流程 / 时点规则」**改写**为「行为规则」？

**为什么存在歧义：** 现行 `WT-6`（走独立 Contract Change）与 `WT-7`（D-3 之前处理）**语义与新内容不同**。复用编号会造成**历史规则语义漂移**。

**需要架构侧回答：**
1. 采用 §2.1 ～ §2.4 的**改写**，还是 §2.5 的**新增 `WT-8` ～ `WT-11`**？
2. 若改写，是否需要保留原 `WT-6` / `WT-7` 语义为附加条款？

---

## `OPEN-3A-2` — Memory 调用的同步驱动方式

**问题：** Tick 侧如何安全驱动一个协程，而不修改 Memory？

**候选：**
- **(a)** 自建临时 event loop 并 `run_until_complete`（与 Memory 内部兜底同构，但在调用方）
- **(b)** 其他不引入新架构的方式

**为什么存在歧义：** 两种方式都**不修改** `ext_memory.py`，但对 asyncio 的用法不同，且可能影响未来迁移到统一 Event 通道（`EV-12`）的成本。

**需要架构侧回答：** 选择哪种？是否有偏好以避免与未来 `EV-12`（`World Change → agent.Event → Memory Runtime`）冲突？

---

## `OPEN-3A-3` — 「非阻塞副作用」是否允许**有界阻塞耗时**

**问题：** `WT-4` 说 Memory 是「非阻塞副作用」。这是指**因果非必需**，还是**零阻塞耗时**？

**为什么存在歧义：**
- 若指**因果非必需** → 同步驱动（含文件 I/O）**可接受**
- 若指**零阻塞耗时** → 需要**队列 / 异步投递**，属结构性改动，**超出最小修复**

**需要架构侧回答：** 明确 `WT-4` 中「非阻塞」的语义边界。

---

## `OPEN-3A-4` — 是否允许 `ai_spot_state` 新增重试字段

**问题：** `WT-7.3`（有界重试）需要记录「已重试次数」或「下次可重试时间」。是否可以新增 `ai_spot_state[ai]` 的字段？

**为什么存在歧义：**
- `ai_spot_state` 属 `ext_world` 自有 Legacy 状态，**不在** `AC-2` / `AC-3` 明确保护清单中
- 但它属 **Legacy Activity State**（`D0-026` 登记的 18 类之一）→ `AC-6` 只登记不修改
- 新增字段会**改变 Legacy 状态 schema**

**备选：** 用**进程内内存字典**记录重试（跨重启丢失；但 Tick 本就跨重启重置，影响有限）。

**需要架构侧回答：** 允许持久化重试字段，还是必须用内存方案？

---

## `OPEN-3A-5` — 是否接受「至多一次」退化为「至少一次」

**问题：** 采用 §B.3 的「失败不提交」后，重试可能导致**部分副作用重复**（如 `add_trail` / `append_timeline` / `_broadcast` 重复）。

**为什么存在歧义：** 无事务机制（且不得引入），因此**无法保证**副作用恰好一次。

**需要架构侧回答：**
1. 是否接受「**至少一次**」语义（可能有重复副作用）？
2. 若不可接受，需要**幂等键**（如以 `(ai, bid, 到达序号)` 去重）—— 这属于额外设计。

---

## `OPEN-3A-6` — 在调用方加隔离是否触碰 `ME-25`

**问题：** `ME-25` 规定「D 阶段**不做**：修 `enqueue_event`」。本设计**不修改** `ext_memory.py`，但**改变调用方的调用方式**（`create_task` → 同步驱动）。

**为什么存在歧义：** 「修 `enqueue_event`」是否包含「改变调用方式使其真正被执行」？

**需要架构侧回答：** 本设计是否在 `ME-25` 允许范围内？

---

## `OPEN-3A-7` — 单轮 Tick 是否可抽出为可测试单元

**问题：** 现有 `ai_spot_tick` 是 `while True` + `time.sleep(30)` + `setup()` 内**直接启动线程**（L310）。**无法在不启动真实线程的情况下调用单轮逻辑**，因此 §4 的四个测试**无法实现**。

**候选：**
- **(a)** 把单轮逻辑抽为 `_tick_once()`（`ai_spot_tick` 调用它），测试直接调用 `_tick_once()`
- **(b)** 测试启动真实线程 + 用事件/等待观察（慢、脆弱）
- **(c)** 用 `unittest.mock` 打补丁替换 `threading.Thread`（可行但更绕）

**为什么这是关键：** **不解决本项，`WT-R-001` ～ `WT-R-004` 全部无法真实运行** —— 而本阶段明确要求「不允许只做静态检查」。

**需要架构侧回答：** 是否允许 `ext_world.py` 做**最小可测性重构**（抽出 `_tick_once()`，不改变行为）？

---

# 6. 交付声明

```text
Production code changes:   0

Contract changes:          proposal only
                           （本文档；docs/V3.1_ARCHITECTURE_CONTRACT.md 未修改）

Tests added:               0

Test design:               4 项（架构侧指定 WT-R-001 ～ WT-R-004）
                         + 6 项（本提案建议 WT-R-005 ～ WT-R-010）

Implementation design:     3 项（A Memory Failure Isolation /
                                B Arrival Transaction Ordering /
                                C save_data Guarantee）

OPEN QUESTIONS:            7 项（OPEN-3A-1 ～ OPEN-3A-7）

Waiting for architecture approval.
```

**本次未修改：**

```text
❌ ext_world.py            ❌ main.py
❌ ext_memory.py           ❌ ext_mem.py
❌ V3.1_ARCHITECTURE_CONTRACT.md
❌ PROJECT_V3.1_MASTER.md
❌ 任何测试文件
❌ 任何前端 / API / World SOT / Event 架构 / Scheduler
❌ 未实现 Movement Continuity
❌ 未修改 Activity
❌ 未接入 Goal / Commitment / Recall
```

**本次唯一新增：** `docs/change_proposals/D3A_WORLD_TICK_RELIABILITY_CHANGE.md`（本文件）

---

**D-3A Proposal 完成，现在停止，等待架构审核。**

**未进入 Contract Change 生效阶段。未进入编码阶段。未进入 D-3 Movement Continuity。**
