# 恋与临空 / Linkong — PROJECT V3.1 MASTER ARCHITECTURE ANCHOR

> 本文件是 V3.1 以后所有窗口的第一设计锚点。
> 它融合旧版 PROJECT.md 的现有功能地图 + V3.0 Agent Architecture + V3.1 新架构。
> 目标：换窗口、换 DS、换开发阶段，都不丢失“整个系统正在做什么”。

## 0. 当前状态

- 正式仓库：`bluekiki610/linkong`
- 当前 V3.0/V3.1 开发与验收：`bluekiki610/TEST`
- V3.0 P0-1 ~ P0-3B 已完成/接受。
- V3.1 当前处于：**Architecture Freeze 前的总整理阶段**。
- V3.1 Phase A（Global Architecture Inventory）已完成。
- 当前系统事实见 §22（不改变目标架构，只是真实起点）。
- Architecture Contract 见 `docs/V3.1_ARCHITECTURE_CONTRACT.md`（FROZEN）。
- 现在不要直接继续堆 autonomous behavior；先冻结架构与全局影响边界。

## 1. 产品定义

Linkong 不是“多个 AI 聊天机器人”。

最终产品是一个共享世界中的 AI Life Community：

- 最多约 5 个真人用户；
- 每个真人拥有自己的 AI；
- AI 有独立人格、关系、记忆、时间、活动、目标、承诺；
- AI 可以与真人、其他 AI、NPC、公共世界发生真实事件；
- AI 的行为应有原因，并且行为产生后果；
- 过去经历可能影响未来行为；
- 世界可以在用户不操作时继续产生有限的自然变化；
- 但系统不能因为无限历史而无限增加单次加载/LLM 成本。

核心循环：

World → Event → Perception → State/Context → Memory/Relationship Recall → Goal/Motivation → Commitment → Intent → Planning → Decision → Policy → Action → World Change → Event

## 2. 旧系统真实功能地图

旧 PROJECT.md 是当前系统的“器官清单”，不得因为 V3.1 而丢失。

### 后端基础

- `main.py`
  - 数据层
  - 基础工具
  - 路由基础
  - 插件加载器
  - 启动
  - 现阶段是重要兼容基础，不做无理由大重写。

- `index.html`
  - 前端主页面，现有稳定能力保持。

- `ext-loader.js`
  - 前端插件加载器，通过 `/api/ext_js/load` 加载扩展；
  - 单文件错误不应阻塞其他插件。

### 核心插件

- `ext_core.py`
  - 通知中心
  - 图片同步
  - 插件列表
  - ext JS 加载
  - ext 静态目录

- `ext_room.py`
  - 房间 / 地图 / 建筑 / NPC / 权限
  - 召唤
  - 轨迹
  - 会客厅补齐
  - presence 保护
  - restore 防线
  - 建筑房间缓存污染防护
  - 批量清空建筑

- `ext_notes.py`
  - 便签 / 日记 / 剧情

- `ext_econ.py`
  - 经济 / 工作 / 常驻 / 工资
  - AI 初始钱包
  - 真人/AI 钱包
  - 站长发钱

- `ext_sms.py`
  - 短信 / 通讯录

- `ext_ai.py`
  - AI 集成
  - 时间注入
  - 主人实时/非主人冷却
  - 自主生活
  - AI 唤醒
  - 移动
  - 群聊
  - 故事/日记/活动等旧行为入口
  - 未来应逐步从“总控制器”退化为兼容/编排层，而不是一次性删除。

- `ext_mem.py`
  - 原设计中的记忆库/画像/提示词注入/世界观/TTS 等能力入口。
  - **重要：当前生产系统实际上没有成功运行记忆文本生成链。**
  - 不得把旧 ext_mem 的设计描述误认为当前已经有有效用户记忆。

- `ext_admin.py`
  - 登记 / 名字清理 / 配色 / 铃铛 / 开发者权限 / 站长总览 / 数据诊断
  - 改名迁移
  - 记忆宽松拉取
  - 清除数据

- `ext_mcp.py`
  - MCP 工具

- `ext_mapimg.py`
  - 地图图片管理 / 上传

### 前端扩展

- `app2.js`
  - 记忆库按月
  - 通知中心
  - 地图 AI 配色

- `ext_admin_ui.js`
  - 站长总览
  - 开发者登录

- `ext_memfix.js`
  - memories_all 宽松拉取
  - saveName 改名迁移

- `ext_econui.js`
  - 「我的」页 AI 钱包

- `ext_hallfix.js`
  - 会客厅不恢复本地缓存
  - 建筑对话补会客厅

- `ext_mapimg.js`
  - 地图上传按钮

## 3. 现有重要约束 / 已修复问题

- 数据以 AI/真人名字作为 key，改名必须全量迁移。
- AI 时间需要注入北京时间。
- AI 回复有冷却机制。
- AI Key 回退 + owner 优先有 Key。
- 公共建筑缺房间时自动补会客厅。
- 地图同步有 presence 防线。
- 会客厅/建筑房间不能被浏览器本地缓存污染。
- 服务器有定期快照和 `.bak`。
- 现有手机 `worldSnapshot` 只存世界核心，不含聊天/短信/记忆轨迹，因此不会随聊天历史线性膨胀。

## 4. V3.0 已接受基础

### P0-1 AgentState
AgentState 是 `main.data` 的只读 Projection，不是 Source of Truth。
不得把 placeholder mood/energy/social_need/stress 当作真实决策输入。

### P0-2A Event
统一 Event 模型。

### P0-2B Message Event Adapter
用户消息 → 一个 `message_received` Event。
多目标 AI 仍是一个 Event，`target_ais` 放 payload。

### P0-2C / P0-2D
完成 Event taxonomy、边界与语义冻结。

### P0-3A
Agent Runtime Contract：
RECEIVE → PERCEIVE → WAKE_DECISION → CONTEXT → THINK → DECISION → ACTION → WORLD_CHANGE → EVENT

### P0-3B
已实现第一条真实 Perception 链：
receive_event → perceive → should_wake
当前仍不 THINK，不调用 LLM。

## 5. V3.1 核心架构

### Agent

每个 AI 是独立 AgentRuntime 实例，共享同一个 World。

AI A 不允许直接调用 AI B Brain。

正确方式：

AI A Action → World Change → Event → AI B Perception → Wake → Think → Action

### Agent State

描述“现在是什么状态”：
- identity
- location
- current_activity
- current_goal
- relationship snapshot
- 可逐步加入真实 energy/mood 等，但必须有可靠来源。

### Event

描述“刚刚发生什么”。

Event 不是函数调用，不是 Timer，不是 LLM 调用。

### Memory

描述“记住了什么”。

### Commitment

描述“已经答应/约定/承诺什么”。

这是解决“AI 为什么现在还应该去那里”的关键层。

### Goal / Motivation

描述“我现在/近期想完成什么，以及为什么”。

### Intent

描述“现在准备做什么”。

### Planning

在已有 Goal/Commitment/World 条件下形成行动计划。

### Policy

检查：
- 目标地点是否存在
- 是否开放
- 是否有资格进入
- 是否与当前活动冲突
- 是否有更高优先级 Commitment
- 是否满足经济/世界规则

### Action

只负责执行，不负责解释动机。

## 6. Time / Schedule

AI 必须知道当前时间，但不是死脚本。

分成：
- Hard Constraints：工作、营业、预约、约会
- Soft Preferences：生活偏好
- Time Trigger：纪念日、截止时间
- Decision Point：到达、活动结束、消息到达、状态变化

长期 Scheduler 替代散落 Timer，但不能直接代替 Brain。

## 7. Activity Lifecycle

统一：

PLANNED → TRAVELING → ARRIVED → ACTIVE → PAUSED → COMPLETED/CANCELLED

活动应逐步具有：
- activity_id
- type
- actor
- participants
- place
- started_at
- expected_end_at
- status
- reason/goal
- linked_commitments

先兼容旧活动，不做一次性重构。

## 8. World Query

地图不只是前端图片。

Brain/Policy 将来需要查询：

- 医疗地点
- 咖啡馆
- 餐厅
- 商店
- 工作地点
- 娱乐
- 可进入房间
- 当前开放状态
- 距离
- 参与者可达性

例如：

`query_places(purpose="medical", urgency="high", open_now=True)`

用户说受伤时，AI 应能：
识别医疗需求 → 查询真实世界 → 选择可用医疗地点 → 规划前往 → 执行 → 产生事件。

## 9. Autonomous Life

旧系统的随机生活逻辑必须保留为 fallback/生活细节来源，但不能继续作为核心因果。

未来：

Time + State + Relationship + Memory + Goal + Commitment + World Condition
→ Motivation
→ Intent
→ Plan
→ Action

随机性可以用于：
- 非关键生活细节
- 候选生成
- 记忆偶发唤醒
- 不影响核心关系/承诺的选择

不能用随机概率解释：
- 为什么突然离开约会
- 为什么突然去一个地点
- 为什么主动邀请主人
- 为什么忽略已经做出的承诺

## 10. Date

约会必须有连续状态，而不是几个 Timer 拼起来。

至少考虑：
INVITED_BY_USER
→ ACCEPTED
→ TRAVELING
→ WAITING
→ USER_ARRIVED
→ ACTIVE
→ ENDING
→ ENDED

AI 主动邀请：
INVITED_BY_AI
→ WAITING_FOR_USER
→ USER_ACCEPTED
→ AI_WAITING
→ USER_ARRIVED
→ ACTIVE

约会原因来自 Goal/Relationship/Memory/Commitment，而不是单纯 8% probability。

## 11. Communication Layer

统一：
- Chat
- SMS
- Group Chat
- SNS
- Comment
- Notification
- Date Invitation
- AI ↔ AI

Brain 决定：
是否沟通、对象、原因、渠道、时机。

底层插件负责执行。

## 12. Memory V3.1

### 当前真实状态

**当前用户聊天尚未成功生成记忆文本。**
历史聊天不能被描述为“已经完成记忆化”。

过去尝试的记忆插件导致系统明显变慢，并且记忆文本没有成功稳定产生。

因此：
**暂不把旧记忆插件重新接入在线主链。**

### 未来目标

Experience
→ Emotional Encoding
→ Association
→ Dormant Memory
→ Cue
→ Recall

普通聊天：
Recall 0 为常态。

特殊情境：
Recall 1~2。

真正重要：
少量高价值记忆。

Memory 不等于完整聊天历史。

## 13. Chat History 与本地归档

建议未来采用“服务器当前窗口 + 本地完整归档”的混合模式。

### Server
负责：
- 当前聊天
- 最近消息
- 实时同步
- 必要的世界事件
- 多设备/多用户一致性

### Device Local Archive
手机端可以把用户自己的历史聊天异步归档到 IndexedDB/SQLite 等本地持久存储，并建立本地搜索索引。

服务器不需要每次把所有历史聊天重新下发。

用户搜索旧聊天时：
优先本地搜索；
如果本地没有，再向服务器请求缺失片段。

### 重要限制

本地归档不能替代服务器数据源。

如果用户清除 App 数据、换手机、卸载应用，本地历史可能丢失，所以服务器仍应保留可靠归档/备份策略。

另外不要把完整聊天塞进 localStorage；应使用 IndexedDB 或等价本地数据库。

## 14. Context Budget

不要简单把现有约 7000~10000 tokens 粗暴砍掉。

使用：

Stable Core
+ Current
+ Recent
+ Long-term Recall
+ Dynamic World

目标：
历史增长不导致单次 Context 线性增长。

LLM Cost ≈ LLM Call Count × Context Size

## 15. Wake / Relevance

先判断“有没有必要思考”，再调用 LLM。

普通无关事件：
IGNORE / OBSERVE

重要事件：
THINK

五个 AI 不应该因为一个普通世界事件全部完整 Think。

## 16. 未来 Voice / TTS

未来 VoiceStudio 接入只通过稳定 Agent identity / voice identity 关联。

Voice 不进入当前 V3.1 核心架构改造。

## 17. Instance / Multi-world

未来预留：
world_id
instance_id
region_id
building_id
room_id

现在不开发副本/多元宇宙。

## 18. 开发规则：每轮必须更新 PROJECT

每一个 V3.1 开发轮次：

1. 先读取本 PROJECT MASTER。
2. 再检查相关代码及依赖。
3. 修改前列出影响面。
4. 实施一个小阶段。
5. 回归测试。
6. 更新 PROJECT MASTER：
   - 当前状态
   - 已完成
   - 新增接口
   - 数据变化
   - 影响文件
   - 已知风险
   - 下一步
7. 再进入下一轮。

PROJECT 是“架构地图”，不是代码实现说明书。

## 19. DS 全局修改铁律

如果 DS 看不到相关文件：
**停止修改，不猜。**

每次修改前必须回答：

1. 谁 import 它？
2. 谁调用它？
3. 它读/写哪些 data 字段？
4. 哪些插件依赖这些字段？
5. 是否存在 Timer/callback/background loop？
6. 是否产生 Event？
7. 是否影响 AgentState？
8. 是否影响 Activity/Commitment/Memory？
9. 是否影响 SSE/前端？
10. 哪些旧功能需要回归？

## 20. 当前下一阶段

**现在不是继续写 P0-3C 的时候。**

下一步：

### Phase A — Global Architecture Inventory
先建立整个 TEST 仓库的：
- 文件地图
- import/call 关系
- data 字段读写关系
- Timer/background loop
- API 路由
- Event/Memory/SSE 链
- 前端依赖
- 核心功能回归矩阵

### Phase B — V3.1 Context Foundation
然后才实现：
- Context Assembly
- Stable Core / Current / Recent / Dynamic World
- Long-term Memory Recall 接口预留
- 不接入失败的旧在线记忆插件
- 不改变现有聊天行为

### Phase C — Motivation / Goal / Commitment
再让自主生活、移动、约会开始具有连续原因。

### Phase D — World Query / Activity Lifecycle
让 AI 能查询真实世界并保持活动连续性。

### Phase E — Memory Recall
在已有历史基础上一次性整理/生成历史记忆，再启用召回。

### Phase F — Brain / Decision
最后把 LLM Think/Decision 接到统一 Runtime。

---
## 21. 设计总原则

> 不要让 AI 记得更少，而要让 AI 在需要的时候想起正确的东西。

> 数据可以无限增长，但单次 Context 不应随历史线性增长。

> AI 不是随机执行器；随机性只是生活细节之一。

> World 负责事实和执行，Agent 负责动机与决策。

> Event 是世界共同语言。

> 先统一语义，再拆文件；先接管决策，再迁移执行。
>

## 22. 当前系统事实（Phase A Inventory 结果 · 2026-09-19）

> 本节记录的是**当前 TEST 仓库真实状态**，不是 V3.1 目标架构。
> 未来所有改造必须以此为起点，不能假设现状与设计一致。
> 完整清单见：`docs/V3.1_GLOBAL_ARCHITECTURE_INVENTORY.md`

### 22.1 后台运行结构

**10 个常驻后台循环**：

| 文件 | 名称 | 间隔 | 职责 |
|------|------|------|------|
| main | snapshot_loop | 1800s | 自动快照 |
| ext_ai | auto_ai_loop | 30s | AI 自主生活/剧情/写作/上班/约会萌发 |
| ext_ai | follow_watch | 5s | 跟随状态检查 |
| ext_world | ai_spot_tick | 30s | 跨建筑到达检测 |
| ext_econ | work_tick | 30s | 工资结算 |
| ext_shop | ai_shop_tick | 60s | AI 自主购物 |
| ext_date | date_tick | 5s | 约会状态机 |
| ext_contact | contact_tick | 900s | 主动关心 |
| ext_holiday | announcement_worker | 1800-3600s | 节日公告 |
| ext_memory | _nightly_scheduler_loop | 每天 2:05 | 夜间记忆批处理 |

**数十个单次 `threading.Timer`**：全部未持久化，服务器重启后丢失。

**关键事实**：
- **无统一 Scheduler**
- **无 Wake Score**
- **无冷却机制**（除 `ai_drive_log` 30s + `ai_group_cooldown` 之外）

### 22.2 ext_ai 是当前 AI Orchestration Hub

`ext_ai.py` 通过 `m.drive_ai` / `m.call_llm` / `m.set_ai_wake_hook` 挂载为全系统 AI 中枢。

**被 8+ 模块调用**：ext_world / ext_date / ext_econ / ext_shop / ext_sms / ext_room / ext_instance / ext_contact / ext_admin。

**调用形式**：`m.drive_ai(ai, trigger, room, trigger_text, fallback_to)`

**关键事实**：`ext_ai` 不是"一个 AI 的 Runtime"，而是**全系统 AI 行为的唯一调度器**。这是 V3.1 AgentRuntime 必须逐步接管的核心边界。

### 22.3 AgentState / Event / AgentRuntime 当前状态

| 模块 | 状态 | 是否被调用 |
|------|------|-----------|
| `agent/state.py` | P0-1 完成 | ❌ 无调用者 |
| `agent/event.py` | P0-2A 完成 | ✅ 被 event_adapter / runtime |
| `agent/event_adapter.py` | P0-2B 完成 | ✅ 被 ext_ai.wake_ais_for_room（room != main）|
| `agent/runtime.py` | P0-3A/3B 完成 | ❌ 无调用者 |

**注意**：AgentRuntime 目前是**旁路观察**，不影响任何现有行为。

### 22.4 ai_location 写入点（15 处）

| # | 位置 | 原因 |
|---|------|------|
| 1-2 | ext_ai.execute_action (speak+follow / speak普通) | AI 发言时更新位置 |
| 3-4 | ext_ai.execute_action (note / diary) | AI 写字时更新位置 |
| 5 | ext_ai.execute_action (move) | AI 主动移动 |
| 6 | ext_ai.wake_ais_for_room 大喊分支 | 大喊召唤到达 |
| 7 | ext_ai._follow_arrive | 跟随到达 |
| 8 | ext_ai.drive_ai summon | 召唤同建筑 |
| 9 | ext_ai._check_meetings | 约定到达 |
| 10 | ext_date._arrive_date | 约会到达 |
| 11 | ext_econ.auto_start_work | 上班位置 |
| 12 | ext_instance.enter_instance | 进入副本 |
| 13 | ext_instance.pause_instance | 副本暂停传回 |
| 14 | ext_instance.end_instance | 副本结束传回 |
| 15 | main.check_pending_moves | 延迟移动到期 |

**风险**：无统一入口；多处并发可能竞态。

### 22.5 当前 Context 规模

**每次完整 AI 对话约 7,000-10,000 tokens**（`ext_ai.build_ai_context`）。

**组成**：DEFAULT_ROLEPLAY + world_lore + persona + user_profiles + worldbook + ai_impression + ai_timeline + ai_visited + room_notes/diary/story + date_ctx + chat_hist + prompt_injections + bctx + scene_hint + 输出规范。

**V3.1 边界**：不粗暴砍掉；目标是通过 Context Budget + Memory Recall 让"历史增长不导致单次 Context 线性增长"。

### 22.6 Memory Runtime 当前未运行

**关键事实**：`ext_memory.py` 的 `enqueue_event()` 有致命 Bug：

```python
async def enqueue_event(...):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        result = await loop.run_until_complete(_enqueue_event_impl(...))  # ❌ 语法非法
        return result
    return await _enqueue_event_impl(...)  # ❌ 函数未定义
    # ↓ 真实写文件逻辑永远不执行 ↓
影响：

16 处调用（ext_shop × 5 + ext_date × 5 + ext_world × 6）全部静默失败

pending_events.json 从未被写入

夜间批处理扫描到的是空目录

用户聊天历史未被记忆化

22.7 已知不一致 / 未挂载
#	位置	问题
1	ext_ai.build_ai_context	调用 m.get_date_context，但未找到任何挂载 → 恒返回 ""
2	ext_ai.drive_ai	调用 m.on_ai_action，但未找到定义 → 死代码
3	ext_admin.generate_impression	存 key 用 normalize_name(ai_name)，ext_ai 读 key 优先原始名 → key 不一致
22.8 SNS 当前不存在
当前系统：无朋友圈 / 无评论 / 无点赞 / 无动态。

唯一接近：sms（短信）+ messages（房间/群聊）+ notifications（通知中心）。

SNS 属于未来产品能力，Communication Layer（§11）已为它预留语义位置。

22.9 Event 真空区
模块	状态
ext_econ	完全未调用 enqueue_event（工作/工资）
ext_instance	完全未调用 enqueue_event（副本进出）
ext_memory	调用失败（见 §22.6）
22.10 事实与目标分离原则
以上所有事实不改变 V3.1 目标架构，只是当前系统的真实起点。

未来改造规则：

任何改造必须以此节为基准，不能假设现状与设计一致

任何"修 Bug"必须先评估是否影响 V3.1 边界

任何"顺手重构"必须停，报告给架构审核

text

---

## 文件 2：新建 `docs/V3.1_ARCHITECTURE_CONTRACT.md`

```markdown
# V3.1 Architecture Contract

> 版本：2026-09-19
> 状态：**FROZEN**
> 依据：PROJECT V3.1 MASTER + Phase A Global Inventory
> 目的：冻结 V3.1 边界，防止 Context / Motivation / Memory / Activity / Scheduler 相互侵入
> 原则：只定义 Contract，不实现功能

---

## 0. 总原则
V3.1 = orchestration / control layer over existing Linkong capabilities

≠ 重写 Linkong
≠ 建立第二套 World
≠ 建立第二套 Source of Truth

text

**改造策略**：
- 先统一语义，再拆文件
- 先接管决策，再迁移执行
- 先并行观察，再逐步切换
- 旧功能不能坏

---

## 1. Source of Truth

### 冻结规则

| 规则 | 内容 |
|------|------|
| **SOT-1** | `main.data` 是当前唯一 Source of Truth |
| **SOT-2** | AgentState 是 Projection，**不是** Source of Truth |
| **SOT-3** | Event 是"事实描述"，**不是** Source of Truth |
| **SOT-4** | 不允许任何 V3.1 模块创建第二数据源 |
| **SOT-5** | 不允许任何 V3.1 模块双向同步 main.data |
| **SOT-6** | 任何"缓存"必须是只读投影或可重建 |

---

## 2. AgentState

### 定义
`main.data` 的只读投影，描述"现在是什么状态"。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **AS-1** | P0-1 实现保持不变，直到 P0-4 才考虑接入 |
| **AS-2** | `mood` / `energy` / `social_need` / `stress` 是 placeholder，**不得**作为决策输入 |
| **AS-3** | AgentState 不反向写入 main.data |
| **AS-4** | `current_activity` 的推导优先级是 P0-1 临时规则，不代表最终行为模型 |
| **AS-5** | 未来若需持久化 AgentState，必须单独设计，不得写入 main.data |

---

## 3. Event

### 定义
世界刚刚发生了什么（Fact）。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **EV-1** | Event ≠ 函数调用（`drive_ai` / `call_llm` / `execute_action` / `save_data` 都不是 Event） |
| **EV-2** | Event 不进入 LLM |
| **EV-3** | Event 不修改 main.data |
| **EV-4** | Event 不触发行为（不自动聊天 / 移动 / 约会 / 工作 / 购物 / TTS） |
| **EV-5** | 一条用户消息 = 一个 Event（不是每个 AI 一个） |
| **EV-6** | Event 语义冻结见 `20260918_P0-2D_Event_Semantics_Freeze.md` |
| **EV-7** | `location_changed` 吸收规则已冻结（见 P0-2D §3） |
| **EV-8** | 旧 `enqueue_event` 与新 `agent.Event` **不是同一系统**，不得混用 |

---

## 4. AgentRuntime

### 定义
单个 AI 的 orchestration 生命周期。

### 生命周期
RECEIVE → PERCEIVE → WAKE_DECISION → CONTEXT
→ THINK → DECISION → ACTION → WORLD_CHANGE → EVENT

text

### 冻结规则

| 规则 | 内容 |
|------|------|
| **AR-1** | 一个 AI 一个 Runtime 实例（不是"超级 Runtime 管理所有 AI"） |
| **AR-2** | Runtime 不直接访问 main.data（只通过 Contract 方法） |
| **AR-3** | Runtime 不直接修改 World（只通过 Decision → Action 让现有 ext_* 修改） |
| **AR-4** | Runtime 不替代 ext_ai（**旁路观察**） |
| **AR-5** | P0-3B 感知链保持不变 |
| **AR-6** | P0-3B **不返回 THINK**（留给未来 Wake Score） |
| **AR-7** | Runtime 不成为 main.data 第二个数据库 |

---

## 5. Context Assembly

### 定义
独立于旧 `build_ai_context` 的 Context 构造层。

### 分层
| 层 | 内容 | 是否增长 |
|----|------|---------|
| **A. Stable Core** | 世界观 / 人设 / 核心用户信息 / 长期身份 | ❌ 稳定 |
| **B. Recent** | 当前对话 / 最近 Event / 当前活动 | ❌ 有界 |
| **C. Long-term** | Memory / Relationship / 历史事件 | ✅ 按需检索 |
| **D. Dynamic World** | AgentState / 当前地点 / 当前世界状态 | ❌ 瞬时 |

### 冻结规则

| 规则 | 内容 |
|------|------|
| **CA-1** | Context Assembly 与旧 `build_ai_context` **并行运行** |
| **CA-2** | 不修改旧 `build_ai_context` |
| **CA-3** | 目标：历史增长**不**导致单次 Context 线性增长 |
| **CA-4** | 不粗暴砍掉现有 7k-10k tokens（保护世界观 / 人设 / 关系 / Memory 连续性） |
| **CA-5** | Long-term 层必须**按需检索**，不默认全量注入 |

---

## 6. Memory

### 定义
人类式记忆：Experience → Emotional Encoding → Association → Dormant → Cue → Recall。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **ME-1** | **当前 `ext_memory` Runtime 不修复** |
| **ME-2** | **当前 `ext_memory` Runtime 不启用** |
| **ME-3** | **不假设旧记忆链有效** |
| **ME-4** | Memory ≠ Chat History |
| **ME-5** | Memory Recall 不是搜索，是"被想起"（Cue-driven） |
| **ME-6** | 普通聊天 Recall 0 是常态 |
| **ME-7** | 特殊情境 Recall 1-2 |
| **ME-8** | 真正重要：少量高价值记忆 |
| **ME-9** | 不做 ai_impression key migration（暂缓） |
| **ME-10** | 未来 Memory Recall 接口预留，但本阶段不实现 |

---

## 7. Goal

### 定义
AI 现在/近期想完成什么，以及为什么。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **GO-1** | 本阶段**不实现** |
| **GO-2** | 不引入随机目标 |
| **GO-3** | 不修改 `_plan_auto` |
| **GO-4** | 未来必须从 Relationship / Memory / Commitment 推导，不凭空生成 |

---

## 8. Motivation

### 定义
Goal + State + Relationship + Memory → 行动动机。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **MO-1** | 本阶段**不实现** |
| **MO-2** | 不替代当前 `_plan_auto` 的随机概率 |
| **MO-3** | 未来随机性只用于生活细节 / 候选生成，不解释核心关系/承诺 |

---

## 9. Commitment

### 定义
AI 已经答应 / 约定 / 承诺什么。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **CO-1** | 本阶段**不实现** |
| **CO-2** | 不修改现有 `date_invites` / `date_invites_out` / `ai_meeting` 状态 |
| **CO-3** | 不修改现有 date/meeting 状态机 |
| **CO-4** | 未来 Commitment 是解决"AI 为什么现在应该去那里"的关键层 |

---

## 10. Activity

### 定义
PLANNED → TRAVELING → ARRIVED → ACTIVE → PAUSED → COMPLETED / CANCELLED。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **AC-1** | 本阶段**不实现** |
| **AC-2** | 不修改现有 `work_sessions` / `dates` / `ai_shop_state` / `instances` |
| **AC-3** | 不修改现有 date/world/shop/instance 的状态字段 |
| **AC-4** | 未来 Activity 应有 `activity_id` / `type` / `actor` / `participants` / `place` / `started_at` / `expected_end_at` / `status` / `reason` / `linked_commitments` |

---

## 11. World Query

### 定义
Brain / Policy 查询世界的方法（`query_places(purpose, urgency, open_now)` 等）。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **WQ-1** | 本阶段**不实现** |
| **WQ-2** | 不替代现有 `find_building_of_room` / `resolve_building` / `can_access_room` |
| **WQ-3** | 不修改 `buildings` / `rooms` / `npcs` schema |
| **WQ-4** | 未来 World Query 必须基于现有数据结构，不引入新索引（除非单独设计） |

---

## 12. Communication

### 定义
Chat / SMS / Group Chat / SNS / Comment / Notification / Date Invitation / AI↔AI。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **CM-1** | Brain 决定"是否沟通 / 对象 / 原因 / 渠道 / 时机" |
| **CM-2** | 底层插件负责执行（ext_sms / ext_ai / ext_notes / ext_core） |
| **CM-3** | **SNS 本阶段不实现** |
| **CM-4** | **AI↔AI autonomous loop 本阶段不实现** |
| **CM-5** | 不修改现有 `ext_sms` / `ext_ai.wake_ais_for_room` / `ext_ai._group_talk` |
| **CM-6** | SNS 属于未来产品能力，Communication Layer 已预留语义位置 |

---

## 13. Action

### 定义
执行层，只执行不解释动机。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **AX-1** | Action 不直接修改 main.data |
| **AX-2** | Action 只调用现有 ext_* 能力 |
| **AX-3** | 当前 `ext_ai.execute_action` **保持不变** |
| **AX-4** | 未来迁移时必须"旧功能不能坏" |
| **AX-5** | Action 与 Decision 分离（不在 Action 中做决策） |

---

## 14. Scheduler

### 定义
统一调度，替代散落的 `threading.Timer` 和后台循环。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **SC-1** | 本阶段**不实现** |
| **SC-2** | **不替代**任何现有 `threading.Timer` |
| **SC-3** | **不替代**任何现有后台循环（`auto_ai_loop` / `ai_spot_tick` / `work_tick` / `ai_shop_tick` / `date_tick` / `contact_tick`） |
| **SC-4** | 未来迁移必须是"只读观察 → 并行 → 切换"三步走 |
| **SC-5** | 未来 Scheduler 必须解决"重启丢失 Timer"问题（持久化） |

---

## 15. ext_ai migration boundary

### 当前事实
`ext_ai` 是全系统 AI orchestration hub，被 8+ 模块调用。

### 冻结规则

| 规则 | 内容 |
|------|------|
| **AI-1** | **不重写** `ext_ai.py` |
| **AI-2** | **不删除** `ext_ai.py` |
| **AI-3** | 先迁移**接口**（`m.drive_ai` / `m.call_llm` / `m.set_ai_wake_hook`） |
| **AI-4** | 后迁移**实现** |
| **AI-5** | 迁移过程必须"旧功能不能坏" |
| **AI-6** | 迁移必须**分阶段**，不一次性重构 |
| **AI-7** | 未来 `ext_ai` 从"总控制器"退化为兼容/编排层 |

---

## 16. Legacy compatibility rules

### 冻结规则

| 规则 | 内容 |
|------|------|
| **LC-1** | `main.data` 是 Source of Truth，**不迁移** |
| **LC-2** | `main.py` **不重写** |
| **LC-3** | 现有 API **不删除**（可以新增） |
| **LC-4** | 现有插件 **不删除**（可以新增） |
| **LC-5** | 前端 **不重写**（可以增强） |
| **LC-6** | 现有 `ext_*` 业务逻辑**不修改**（除非单独 PR 说明） |
| **LC-7** | 改名迁移路径**继续有效**（ext_admin.replace_name_in_data） |
| **LC-8** | 名字规范化系统（`canonical_ai_name` / `owner_of_ai`）**继续有效** |

---

## 17. 不现在做（完整清单）

以下全部**本阶段不做**：

### 修复 / 迁移类
- ❌ 修复 `ext_memory`
- ❌ 重新启用 `ext_memory`
- ❌ ai_impression key migration
- ❌ 处理 15 处 `ai_location`
- ❌ 修复 `get_date_context` 未挂载
- ❌ 修复 `on_ai_action` 未定义

### 新增 / 实现类
- ❌ 创建 Scheduler
- ❌ 实现 Goal / Motivation / Commitment
- ❌ 实现 Activity Lifecycle
- ❌ 实现 World Query
- ❌ 实现 Brain / Decision
- ❌ 实现 AI↔AI autonomous loop
- ❌ 实现 SNS
- ❌ 实现 Chat Pagination
- ❌ 实现 local chat archive
- ❌ 实现 TTS / VoiceStudio
- ❌ 实现 World Clone / multi-tenant

### 修改类
- ❌ 修改 `main.py` 业务逻辑
- ❌ 修改 `ext_ai.py` 业务逻辑
- ❌ 修改 `ext_world.py` 业务逻辑
- ❌ 修改 `ext_date.py` 业务逻辑
- ❌ 修改 `ext_econ.py` 业务逻辑
- ❌ 修改 `ext_shop.py` 业务逻辑
- ❌ 修改 `ext_sms.py` 业务逻辑
- ❌ 修改 `ext_room.py` 业务逻辑

---

## 18. 允许修改的边界（本阶段）

**只允许修改**：

| 文件 | 内容 |
|------|------|
| `PROJECT_V3.1_MASTER.md` | 追加 §22 当前系统事实 |
| `docs/V3.1_ARCHITECTURE_CONTRACT.md` | 本文件 |

**不修改**：
- 任何 `.py`
- 任何 `.js`
- 任何 `.html`
- 任何 `data/*.json`
- `requirements.txt`

---

## 19. 进入 Phase B 的条件

**进入 Phase B（Context Foundation）必须满足**：

- [x] Phase A Global Inventory 已完成
- [x] Phase A-2 Architecture Contract 已冻结
- [x] PROJECT_V3.1_MASTER.md 已更新
- [x] 未修改任何业务代码
- [ ] 架构审核通过

**只有全部满足后，才能进入 Phase B。**

---

## 20. Contract 变更规则

| 规则 | 内容 |
|------|------|
| **CC-1** | 任何边界修改必须先更新本 Contract |
| **CC-2** | 不允许"顺手改" |
| **CC-3** | 修改必须经架构审核 |
| **CC-4** | 修改必须记录在本 Contract 的变更日志中 |
| **CC-5** | Contract 是 V3.1 所有阶段的设计锚点 |

---

## 21. 为什么下一步是 Context Foundation

### Phase B（V3.1 Context Foundation）的必要性

**1. Context 是当前最痛的瓶颈**
- 每次对话 7k-10k tokens
- 上下文包含 15+ 片段
- 无分层、无预算、无按需检索

**2. Context 是后续所有阶段的前置依赖**
- Memory Recall → 需要 Context 分层
- Goal / Motivation → 需要 Context 提供状态
- Activity Lifecycle → 需要 Context 提供当前活动
- World Query → 需要 Context 提供世界状态

**3. Context Foundation 完全独立于业务代码**
- 只新增 `agent/context.py` 之类的模块
- 不修改 `build_ai_context`
- 可并行运行、独立测试

**4. 不做 Context Foundation 就进入 Goal/Motivation 会失控**
- 会导致 Goal 层自己去拼 context
- 会导致 Motivation 层重复读取 main.data
- 会破坏 Contract 的"单一 Source of Truth"原则

**结论**：Context Foundation 是**低风险、高价值、被所有后续阶段依赖**的第一步。它是 V3.1 从"文档"走向"代码"的正确切入点。

---

## 22. 附录：Contract 与 P0-* 文档的关系

| 文档 | 定位 | 状态 |
|------|------|------|
| `PROJECT.md` | 旧版功能地图 | 保留，被 MASTER 引用 |
| `PROJECT_V3.1_MASTER.md` | V3.1 设计总纲 | 活跃更新 |
| `docs/V3.1_GLOBAL_ARCHITECTURE_INVENTORY.md` | Phase A 事实盘点 | FROZEN（事实） |
| `docs/V3.1_ARCHITECTURE_CONTRACT.md` | **本文件** | FROZEN（边界） |
| `20260918_P0-2D_Event_Semantics_Freeze.md` | Event 语义冻结 | FROZEN |
| `20260918_P0-3A_Agent_Runtime_Contract.md` | Runtime 生命周期 | FROZEN |

**冲突解决顺序**：Contract > MASTER > 阶段文档 > 旧文档。

---

**V3.1 Architecture Contract 已冻结。**

**下一步：等待架构审核，然后进入 Phase B（V3.1 Context Foundation）。**

> 世界越来越真实，而不是系统越来越复杂。
