# 恋与临空 / Linkong — PROJECT V3.1 MASTER ARCHITECTURE ANCHOR

> 本文件是 V3.1 以后所有窗口的第一设计锚点。
> 它融合旧版 PROJECT.md 的现有功能地图 + V3.0 Agent Architecture + V3.1 新架构。
> 目标：换窗口、换 DS、换开发阶段，都不丢失“整个系统正在做什么”。

## 0. 当前状态

- 正式仓库：`bluekiki610/linkong`
- 当前 V3.0/V3.1 开发与验收：`bluekiki610/TEST`
- V3.0 P0-1 ~ P0-3B 已完成/接受。
- V3.1 当前处于：**Context Foundation / Phase B 阶段**。
- V3.1 Phase A（Global Architecture Inventory）已完成。
- V3.1 Phase B1（Context Data Contract）已完成。
- V3.1 Phase B2-1（StableCoreProvider）已完成。
- V3.1 Phase B2-2（DynamicWorldProvider）已完成。
- V3.1 Phase B2-3（RecentProvider）已完成。
  - 新增 `agent/recent_provider.py`
  - 测试 `docs/test_b2_3_recent.py`（可从仓库根目录直接运行：`python docs/test_b2_3_recent.py`）
  - **实际数据源**：
    - `ai_timeline[ai]` → `recent_timeline`（上限 5 条）
    - `trails[ai]` → `recent_trail`（24h 窗口 + 上限 5 条）
    - `ai_visited[ai]` → `recent_visited_place`（上限 3 个）
  - **明确不生成**：recent_map / recent_building / recent_region / recent_place / recent_decision / recent_goal / recent_memory / recent_full_chat / recent_full_sms
  - **限制**：输出条数 ≤ 13，单条 ≤ 120 字符，输入 3000 条 → 输出 ≤ 13 条（非线性）
- V3.1 Phase B2-4（LongTermProvider Stub）已完成。
  - 新增 `agent/long_term_provider.py`（Stub，无业务逻辑）
  - 测试 `docs/test_b2_4_long_term.py`（可从仓库根目录直接运行）
  - 当前状态：**stub**
  - 当前无真实 Long-term 数据源，返回 `[]` 是正确行为
  - Memory Runtime 仍未启用
  - ext_memory 不修改、不修复
  - Recall 仅预留接口（`recall_query` 参数），未实现
  - ContextAssembler 尚未开始
  - Runtime 尚未接入
- V3.1 Phase B2-4（LongTermProvider Stub）已 ACCEPTED。
- V3.1 Phase B3（ContextAssembler）已完成。
  - 新增 `agent/context_assembler.py`
  - 测试 `docs/test_b3_context_assembler.py`（从仓库根目录运行：`python docs/test_b3_context_assembler.py`）
  - 四层组装：Stable Core / Recent / Long-term / Dynamic World
  - Budget enforcement：四层独立预算 + 总预算
  - deterministic truncation：保持 Provider 原顺序，超预算时拒绝当前 item，标记 truncated=True
  - LongTermProvider 当前仍为 Stub，返回 `[]`
  - Runtime 尚未接入，`agent/runtime.build_context()` 保持 P0-3A Stub
  - 未修改 `agent/runtime.py`、`main.py`、`ext_*.py`

---

## 2. `PROJECT_V3.1_MASTER.md` 阶段状态追加

- ✅ V3.1 Phase B3（ContextAssembler）已 ACCEPTED。
- ✅ V3.1 Phase B4（Runtime Connection Pre-Flight）已 ACCEPTED。
- ✅ V3.1 Phase B5-0（Context Contract Decision）已 ACCEPTED。
  - V3.1 正式 Context 标准 = `AgentContext`
  - `ContextLayers` = deprecated compatibility stub（保留、不删除、不改名、不别名化）
  - Runtime 最终接口冻结（待 B5-2 实现）：
    - `build_context(event: Event, now_ts: Optional[float] = None) -> AgentContext`
    - `think(context: AgentContext) -> Optional[str]`
  - 数据来源冻结：
    - `owner` = `get_state().owner`
    - `agent_state_dict` = `get_state().to_dict()`
    - `data` = `self._data`
    - `now_ts` = 调用方注入
    - `recall_query` = 当前固定 `None`
  - Contract Change：CC-20260926-01
- ⏳ V3.1 Phase B5-1（Contract Change）进行中。
- ⏳ V3.1 Phase B5-2（Runtime Connection）待启动。
现在不要直接继续堆 autonomous behavior；
先完成 Context Foundation，再进入 Agent Decision / Motivation 层。

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

### 1.1 首页产品形态：AI Life Home
Linkong 的默认 App 入口不应长期停留在“上一次聊天页面”。

未来首页采用“AI Life Home”作为用户进入社区后的第一视觉入口：
- AI 人物作为首页主要视觉主体；
- 人物可以通过循环视频 / 动画 / Live2D / 3D 等表现层呈现；
- 用户可以直接与人物进行轻量互动；
- 人物身体不同区域可以配置 Interaction Hotspot；
- 点击脸、头、手、肩、身体等区域，可触发对应互动；
- 高频、低延迟互动优先使用预录语音 / 预制动画；
- 需要理解用户自然语言或复杂上下文时，再进入 LLM；
- LLM 生成的内容可通过 Voice / TTS 层输出 AI 专属声音；
- 首页同时作为 Chat / Community / Map / Date / Home / Shop / Schedule / Activity 等功能入口。

首页不是新的 AI Runtime，也不是新的数据源。

它只是现有 Agent / World / Activity / Communication / Action 能力的用户视觉入口。

产品关系：
AI Agent State / Activity / Goal / Relationship
↓
Home Presentation
↓
Character / Status / Interaction
↓
User Interaction
↓
Event / Agent Perception
↓
Response / Voice / Animation / Navigation

首页必须读取真实 Agent / World 状态，而不是自行维护第二套 AI 状态。

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
  - 当前前端主页面；  
  - 现有稳定能力保持；  
  - V3.1 不要求整体推倒重写；  
  - 未来新增 Home Shell / AI Life Home 作为新的默认入口；  
  - Chat / Map / Room / Date / SMS / Shop 等现有功能继续作为功能页面或功能模块存在。

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

### V3.1 Frontend Direction

未来前端采用：

App Shell
├── Home / AI Life Home
├── Chat
├── Map / World
├── Date
├── Home / Room
├── SMS / Communication
├── Shop
├── Schedule
├── Activity
└── Settings

Home 是默认入口，但不是新的业务数据层。
不采用“第二套独立前端覆盖旧前端”的方式。

原则：
- 保留现有业务页面；
- 新增 Home Shell；
- 统一导航；
- Home 负责人物展示、互动与功能入口；
- 原有页面继续负责具体业务功能。

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

### 5.x User Interaction Layer

未来前端增加独立的 User Interaction Layer，用于连接用户在首页上的直接互动与 Agent Runtime。

第一阶段支持：
- Character Touch
- Character Hotspot
- Face / Head / Hand / Shoulder / Body 等互动区域
- Character Voice
- Character Animation / Video Feedback
- Home Navigation
- Status Feedback

互动链：

User Touch / UI Interaction
→ Interaction Event
→ Agent Perception / Relevance
→ Response Decision
→ Action
→ Voice / Animation / UI Feedback

重要边界：

- Interaction Layer 不是 Agent Brain；
- Interaction Layer 不维护独立 AI State；
- Interaction Layer 不直接修改 main.data；
- 高频简单互动可以由前端/Interaction Layer 使用预定义响应；
- 复杂、上下文相关互动再进入 Agent Runtime / LLM；
- Interaction Layer 必须能够逐步从视频 Hotspot 升级到 Live2D / 3D，而不改变上层 Agent 语义。

第一阶段允许采用：循环角色视频 + 透明 Hotspot + 预录语音。

后续可以替换为：Live2D / 动画角色 / 3D 角色。

表现层变化不应导致 Agent 核心架构变化。

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

### World Presentation Hierarchy

未来 World Query 应支持至少以下层级：

World
→ Map
→ Building / Place / NaturalFeature
→ Activity

Map 是可查询的 World Knowledge，而不是单纯图片。

Map 可以具有：
- map_id
- map_name
- map_type
- map_description
- map_owner / ownership
- map_purpose
- map_tags
- map_environment
- suitable_activities
- availability

Building / Place / NaturalFeature 可以具有：
- place_id
- map_id
- name
- type
- description
- ownership
- tags
- suitable_activities
- availability

AI 应先根据 Goal / Motivation / Relationship / Time / World Condition 查询候选 Map，再在 Map 内查询 Building / Place / NaturalFeature。

不要通过随机建筑选择代替 World Query。

当前只记录架构，不实现 Map Query / Place Query。

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

### Voice / Speech Output

Voice 是 Communication / Interaction 的表现层能力之一。

- 高频固定互动可以直接播放预录语音；
- LLM 动态回复可以经过 TTS；
- 每个 AI 可以通过稳定 Agent identity / voice identity 关联自己的声音；
- Voice 不决定 AI 说什么，只负责将已经决定的文本/语义转换为声音表现；
- VoiceStudio 属于未来 Voice Layer，不改变 Agent Runtime / Brain / Decision 架构。

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

### 14.1 当前 Context Architecture（Phase B1 完成）

**已建立**：Context 数据结构 + 预算模型。

**四层**：

| 层 | 内容 | 预算上限 | 增长特性 |
|----|------|---------|---------|
| Stable Core | 世界观 / 人设 / 用户画像 / 长期身份 | 2000 tokens | 不增长 |
| Recent | 当前对话 / 最近事件 / 当前活动 | 3000 tokens | 有界 |
| Long-term | Memory / Relationship / 历史事件 | 2500 tokens | 按需检索（B2 实现） |
| Dynamic World | AgentState / 当前地点 / 当前世界状态 | 1000 tokens | 瞬时 |

**总预算**：8500 tokens（略低于当前真实基线 7k-10k）。

**核心数据结构**（`agent/context.py`）：
- `AgentContext`：结构化对象，不是 Prompt 字符串
- `ContextSection`：单层结构化内容（items 是 dict 列表）
- `ContextBudget`：四层预算模型

**关键原则**：
- Context 是结构化对象，不是已拼好的 Prompt
- 每层有独立预算上限
- `to_debug_dict()` 不包含 items 内容（防泄漏）
- 已预留 `decision_constraints` 字段（B1 不实现）

**B1 边界**：
- 不读取 `main.data`
- 不调用 LLM
- 不修改任何现有业务代码
- 不启用 `ext_memory`
- 不进入 `think()` / `decide()` / `execute()`

### 14.2 Context Providers（Phase B2 渐进）

**B2 总原则**：
- Provider ≠ Database
- Provider ≠ Memory
- Provider ≠ Decision
- Provider ≠ Prompt
- Provider 只负责：从已有系统事实中，取出一小块结构化数据

**B2 分阶段**：

| 阶段 | Provider | 状态 |
|------|----------|------|
| B2-1 | StableCoreProvider | ✅ 已完成 |
| B2-2 | DynamicWorldProvider | ✅ 已完成 |
| B2-3 | RecentProvider |  ✅ 已完成 |
| B2-4 | LongTermProvider（Stub） | ✅ 已完成 |

**B2-1 StableCoreProvider**：
- 位置：`agent/stable_core_provider.py`
- 输入：`fetch(ai_name, owner, data)`（data 由调用方传入，Provider 不 import main）
- 输出：`List[Dict[str, Any]]`（结构化 items，不是 Prompt）
- 提取内容：
  - `identity`（AI 名 + owner 名）
  - `world_lore`（世界观）
  - `persona`（AI 人设）
  - `user_profile`（用户画像）
- 明确排除：messages / sms / trails / ai_timeline / ai_memories / ai_keys / dev_users / pairs_admin / server_id / ai_impression
- 行为：只读、不缓存、不修改 data

**B2-2 DynamicWorldProvider**：
- 位置：`agent/dynamic_world_provider.py`
- 输入：`fetch(ai_name, owner, data, now_ts=None, agent_state_dict=None)`
- 输出：`List[Dict[str, Any]]`
- 提供字段：
  - `current_time`（北京时间，来自 provider.clock）
  - `current_location`（直接读 `ai_location`）
  - `current_activity` / `is_working` / `is_dating` / `is_following`（可选，从 AgentState 投影）
- 保守缺省：
  - **不提供** `current_building` / `current_map` / `current_region` / `current_place`
  - 需要反查或多步推断，违反"不猜测"原则
- Map Knowledge 预留（describe() 中声明，未实现）：
  - `map_id` / `map_name` / `map_type` / `map_region`
  - `map_owner` / `map_purpose` / `map_description`
  - `map_tags` / `map_environment` / `map_places`

**B2-3 RecentProvider**：
- 位置：`agent/recent_provider.py`
- 测试：`docs/test_b2_3_recent.py`（从仓库根目录运行）
- 输入：`fetch(ai_name, owner, data, now_ts=None, agent_state_dict=None)`
- 输出：`List[Dict[str, Any]]`（结构化 items）
- 数据源（全部有明确上限）：
  - `ai_timeline[ai]`   → `recent_timeline`      (≤ 5 条)
  - `trails[ai]`        → `recent_trail`         (≤ 5 条 + 24h 窗口)
  - `ai_visited[ai]`    → `recent_visited_place` (≤ 3 个)
- 边界：
  - **不读** messages / sms / notes / diaries / stories
  - **不读** ai_memories / ai_impression
  - **不读** AgentState（current_activity 属于 Dynamic World）
  - **不生成** map / building / region / place / decision / goal / memory
- 预算策略：
  - 条数上限：timeline 5 + trail 5 + visited 3 = 13
  - 时间窗口：trails 默认 24h
  - 内容长度：单条 ≤ 120 字符
  - 非线性验证：输入 3000 条 → 输出 ≤ 13 条
- 与 Event 的边界：
  - 当前直接从 ai_timeline / trails / ai_visited 读
  - 未来 Event 层就绪后可插入转换层
- 与 Memory 的边界：
  - Recent 只读最近事件，不做 Recall
  - Long-term 由 B2-4 负责
  - 旧 ext_memory 不修复、不启用

**B2-4 LongTermProvider Stub**：
- 位置：`agent/long_term_provider.py`
- 输入：
  `fetch(ai_name, owner, data, now_ts=None, agent_state_dict=None, recall_query=None)`
- 输出：`List[Dict[str, Any]]` —— **当前始终返回 `[]`**
- 状态：
  - `status = "stub"`
  - `data_source = "none"`
  - `memory_runtime_connected = False`
  - `recall_supported = False`
- 当前返回 `[]` 的原因：
  - Memory Runtime 未启用
  - 无可靠 Long-term 数据源
  - 不生成伪造的长期记忆
- 预算元数据（`describe()` 声明，即使当前为空）：
  - `max_items = 5`
  - `max_chars_per_item = 300`
  - `token_budget = 2500`（与 ContextBudget.long_term_max 一致）
- 明确禁止（本阶段）：
  - 不修复 ext_memory
  - 不启用 Memory Runtime
  - 不读 pending_events
  - 不生成新 Memory 文本
  - 不扫 chat / sms / notes / diaries / stories / timeline / trails / visited
  - 不创建第二套 Memory DB
  - 不创建持久化文件
- 明确不生成 item 类型：
  - `long_term_memory` / `long_term_recall` / `long_term_diary` /
    `long_term_note` / `long_term_chat` / `long_term_event` /
    `long_term_decision` / `long_term_goal`
- 与 Memory Runtime 的关系：
  - 未来流程：Memory Runtime → Recall → LongTermProvider → ContextAssembler
  - 本阶段仅建立接口，Memory Runtime 未启用
- 与其他 Provider 的一致性：
  - 接口签名与 B2-1 / B2-2 / B2-3 一致
  - Dependency Injection 风格
  - 不 import main / ext_*
  - 不调用 LLM / 网络
  - 不修改 main.data

**B2 全部完成前不接 Runtime**：`agent/runtime.build_context()` 保持P0-3A Stub。

**B2 当前状态**：
- StableCoreProvider：✅ 已完成
- DynamicWorldProvider：✅ 已完成
- RecentProvider：✅ 已完成
- LongTermProvider：✅ 已完成

**B2 全部完成前不接 Runtime**：
`agent/runtime.build_context()` 继续保持 P0-3A Stub。

**B3 已完成**：
- 新增 `agent/context_assembler.py`
- 测试 `docs/test_b3_context_assembler.py`
- 仅完成 Context Assembly
- 不接入 Runtime；`agent/runtime.build_context()` 保持 P0-3A Stub
- Runtime 接入属于后续阶段

**B4 Runtime Preflight**            ✅ ACCEPTE

**B5 阶段状态**：
- B5-0 Context Contract Decision：✅ 已 ACCEPTED
- B5-1 Contract Change（CC-20260926-01）：⏳ 进行中
- B5-2 Runtime Connection：⏳ 待启动
- Runtime 实现仍未修改；`agent/runtime.py` 保持 P0-3A/3B 原状
- `build_context` 尚未接入 `ContextAssembler`
- THINK 仍为 Stub

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

### Home Interaction Voice

首页人物互动允许存在两类声音：

1. Pre-recorded Voice   
 - 高频、低延迟、固定互动；   
 - 不调用 LLM；   
 - 不产生高额 Token 消耗。

2. Dynamic AI Voice  
 - 用户提出需要理解上下文的问题；  
 - Agent / LLM 生成动态回复； 
 - 再通过 TTS / VoiceStudio 输出。
 
两者最终都属于 Voice Presentation Layer。

因此：“戳脸 → 固定游戏语音”和“用户说话 → LLM → TTS”可以同时存在。

当前阶段只记录架构，不实现 VoiceStudio 接入。


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

当前正在进行 Context Foundation。

顺序：
1. Context Data Contract
2. StableCoreProvider
3. DynamicWorldProvider
4. RecentProvider
5. LongTermProvider
6. ContextAssembler
7. 接入 `agent/runtime.build_context()`

Home / Frontend Interaction Layer 属于产品表现层建设方向，不应提前打断当前 Context Foundation。

在 Agent Core 语义冻结后，再进行 Home Shell 的前端架构设计与实现。

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

