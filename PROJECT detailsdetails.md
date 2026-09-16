def setup(app, data, helpers):
    import main as m
    # 注册 FastAPI 路由；可启动线程
helpers：default_data/sanitize_data/migrate_room_prefix/ensure_admin/init_writing_rhythm/migrate_images/DATA_ROOT/save_data

钩子（后端插件间联动）
m.set_ai_wake_hook(fn)：ext_ai 注册唤醒；骨架 send_message 后自动调用

m.drive_ai：ext_ai 挂载到 main，供 summon/sms/world/date/instance 等直接驱动 AI

m.auto_start_work：ext_econ 挂载到 main，供 AI 自主上班 / MCP 使用

m.check_pending_moves()：骨架提供，AI 回家倒计时检查

m.on_ai_action：ext_date 挂载，检测约会意图/回应邀请

m.get_date_context：ext_date 提供给 AI 上下文

m.get_shop_menu：ext_shop 提供给 AI 读取建筑菜单

m._check_reply_on_message：ext_date 提供给 ext_ai，检测主人是否在回应约会邀请

m._ai_think_invite：ext_ai 提供给 auto_ai_loop，AI 自主思考萌发约会

m.HOLIDAY_MULTIPLIER / m.HOLIDAY_CONTEXT：ext_holiday 挂载，供 ext_ai / ext_date 读取节日加成

m.call_llm：ext_ai 暴露给其他插件（ext_notes 用于批注回复，ext_instance 用于生成总结）

新增 API（v2.14）
GET /api/ai/task_status?task_id=xxx → 返回 AI 生成任务状态（pending/generating/done/timeout/failed）

GET /api/ai/group_mute?user=xxx → 获取用户所有 AI 的群聊静音状态

POST /api/ai/group_mute → 设置某个 AI 的群聊静音状态 {user, ai, muted}

GET /api/ai/stay_put?user=xxx → 获取用户所有 AI 的原地待命状态

POST /api/ai/stay_put → 设置某个 AI 的原地待命状态 {user, ai, on}

POST /api/holiday/trigger_event → 手动触发节日剧情事件（需 pwd 鉴权）

开发者权限（站长身份）
后端：ext_admin 把 main.is_admin 全局覆盖为 _is_priv = 原is_admin(去emoji认「亦言」) 或 dev_users；owner_of_ai 覆盖为「优先有Key的主人」

开发者密码：yiyan610116（环境变量 DEV_PASSWORD 可覆盖）

解锁：POST /api/dev/unlock 或 手机 GET /api/dev/unlock_get?user=xxx&pwd=xxx

手机友好：站长操作接口都支持 &pwd=开发者密码 直接鉴权（不依赖名字识别）

解锁后：AI总开关 / 世界观 / 数据清理 / 备份 / 配色 / 站长总览 / 上传地图 / 发钱 / 清空建筑 / 彻底清除 全部开放

名字管理（重要）
数据以名字为 key → 改名必须迁移！

真人改名：设置→我的名字（ext_memfix 覆盖 saveName → POST /api/rename_user 全量迁移）

AI 改名：POST /api/user_ais 自动 diff（旧AI去emoji相同→迁移全部数据）

宽松匹配：/api/memories_all 用 strip_emoji，带不带 emoji 都能拉到记忆/纸条/日记/剧情

彻底清除：/api/admin/purge?user=xxx&name=xxx&pwd=xxx（物理删除消息/纸条/日记/剧情/短信/钱包/记忆，GET+POST）

变体统一：/api/admin/merge_name_base?base=亦言&target=亦言❄️&pwd=xxx 一键合并所有 emoji 变体

⚠️ 名字定好尽量稳定；要改就用设置里的改名（自动迁移）

经济系统（ext_econ v2.6）
钱包按名字存（真人/AI 分开）；真人钱包不涨多为「名字变体」导致

AI 初始钱包：POST /api/econ/config {user, ai_init_wallet}（站长）→ AI 首次有金钱行为时自动发放（仅一次不覆盖）

站长发钱：POST /api/econ/init_wallets {user, target: ai|user|all, amount}

钱包可见：/api/economy 返回 ai_wallets；ext_econui.js 在「我的」页显示每个 AI 的钱包

会客厅 / 房间污染防线
根因：浏览器本地缓存把 main 群聊 restore 写回建筑房间 → 污染

前端：ext_hallfix.js 覆盖 restoreCache，会客厅不恢复本地缓存

后端：ext_room 覆盖 /api/restore，建筑内所有房间（会客厅/卧室/厨房）拒绝本地缓存恢复

清空：POST /api/room/reset_messages 或 GET /api/room/reset?user&room&pwd；批量清建筑 GET /api/admin/reset_building?user&bid&pwd

消费与送礼（ext_shop v1.9）
菜单分类：shop/fun/food/date/medical 有菜单，其他无（完全功能驱动，取消功能即消失）

默认不选上架；一键全选/全不选；特供商品可编辑/删除（上限50）

AI 低频消费 + 本店特供也能买；真人送礼→AI说话感谢+真实回礼（到购物场所才回礼）

AI 逛街主动送礼；我的物品可摆放/送礼/丢弃；本宅收藏

创建者/站长都可管理本店（宽松匹配 emoji）

AI 可读菜单：building_context 注入 get_shop_menu（本店菜单/本店特供/价格）→ 真人问菜单能照着答

前端 UI：无菜单但有管理权限时显示「⚙️ 管理本店」而非「🛍️ 本店」

约会系统（ext_date v2.1）
主人邀约 AI：建筑顶部「💞 约会」按钮 → 发起邀请 → AI 短信回复答应/婉拒 → 约定时间 → 赴约 → 状态显示

AI 主动邀约主人（新增）：

触发方式一：AI 到达有约会功能的建筑时，有概率（10%）自主发起约会邀请

触发方式二：AI 在世界任何地方，每 2 小时有概率（8%）萌发约会想法，选择当前建筑或随机约会建筑作为约会地点

好感度不再作为触发门槛，只影响触发概率权重

邀请渠道：私信（短信）或群聊

主人回复：自然语言回复「好/来/行」→ 接受；「不/忙/改天」→ 婉拒；不确定 → AI 追问

约会状态：coming（赴约中）→ active（约会中）→ 状态广播/建筑内系统消息/AI 在聊天框自然互动

好感度：隐藏数值，约会成功/收礼增加，每天缓慢衰减

AI 赴约带礼物：赴约途中可能顺路买小礼物，主人可收下，好感度增加

修复：AI 邀请主人后只会追问一次（不再每分钟刷屏）

世界行为（ext_world v1.2）
到达公共建筑：从 剧情/工作/购物/约会 中按权重随机选一个执行

工作权重动态：工作时间+常驻工作建筑=60；工作时间+非工作建筑=10；非工作时间+工作建筑=5；非工作时间+非工作建筑=0

到达住宅：优先检查剧情（独立计时器），触发住宅日常剧情，否则走居家事件

剧情独立计时：剧情冲动与便签/随笔分离，互不挤占

每日限制：剧情每天最多 2 次，间隔至少 2 小时

节日/系统NPC系统（ext_holiday v1.0）
通用节日模板：支持七夕/情人节/中秋/端午/元旦/春节（可扩展）

自动识别：根据当前日期自动匹配节日（农历节日自动转换）

滚动公告：节日期间在社区大厅滚动显示祝福语

烟花系统：自动调度烟花动画 + 倒计时（节日整点触发）

概率加成：节日期间 AI 触发特殊事件（约会/送礼/剧情）的概率提高

AI 主动关心（ext_contact v1.4）
真人超4小时未互动（说话/短信/召唤/送礼算互动，前端 ping）→ 7-23 点 AI 主动发私信（不群聊），每天≤2次，间隔≥3h

私信内容由 AI 自然生成（不模板），避免刚部署轰炸

注意：日记批注回复功能已移至 ext_notes.py（由 LLM 自然生成），不再由 ext_contact 处理

AI 真人化系统（ext_ai v6.2）
新增功能：

群聊静音（「我的」页开关）：关闭后 AI 完全不读取/回复群聊，0 tokens 消耗

原地待命（「我的」页开关，与群聊静音并排）：开启后 AI 不会自主离开（即使主人长时间不说话），关闭后恢复自主活动

「大喊」唤醒（住宅内）：用户发 `（大喊）` 或 `(大喊)` 开头消息，AI 从其他房间赶来并自然回复（1~2 秒到达）

任务状态 + 超时反馈：发送消息后前端显示 ⏳ 正在思考 → ✍️ 正在打字 → ✅ 完成；15 秒超时提示重试

AI 在互动中不会突然离开：修复了“主人还在聊天 AI 就自己跑掉”的问题

AI 等待主人互动时间：从 15 分钟延长到 30 分钟

人设读取逻辑（精确匹配）：
- 优先取 `data.ai_profiles[owner]` 中 `ai` 字段等于当前 AI 名字的条目（专属人设）
- 若不存在，则取 `ai` 字段为空或等于 `owner` 的全局人设（回退）
- 最终注入到 System Prompt 的 `## 你的人设` 部分

副本劫持（`_build_instance_context`）：
- 当 `drive_ai` 被触发时，会检测当前 AI 是否处于活跃副本（`instances[owner][iid].status == 'active'` 且 AI 在 participants 中）
- 若是，则完全切换上下文：使用副本的 `background`、`premise`、`participants` 人设、`chat_history`，忽略主世界时间/地点/记忆
- 副本内 AI 只能执行 `speak` 动作，不能移动/上班/约会等

社区群聊（main = 💬 临空社区，首页无召唤）
主人发言：只随机选一个 AI 必回；点名（宽松匹配去emoji）→ 必回

其他真人/AI：LLM 自主，冷却（站长可设 30/45/60 秒）；无真人时合计 5-10 条停

同内容 5 秒去重；首页（main）顶部无召唤键、召唤会提示

群聊响应链：真人发消息 → wake_ais_for_room → 检测约会回复 → _group_talk 派发

自主生活（决策树 1-2 小时一次）
30 分钟无真人互动 + 7-23 点 + 冷却 1-2h（从 15 分钟改为 30 分钟）

工作/世界/在家三分支；随笔不限量（无每日限制）

独立剧情计时：剧情冲动与便签/随笔分离，到达公共建筑时优先检查剧情

自主约会萌发：AI 在世界任何地方，每 2 小时有概率主动想约主人

自然短信：living/告别场景提示词里自然融入（想念/分享可以发短信，凭感觉，不机械不命令）

AI 可读菜单：building_context 注入 get_shop_menu（本店菜单/本店特供/价格）

AI 新房间识别：AI 在住宅内时，系统提示词会列出该住宅所有房间名，AI 能正确移动到新房间

前端交互（app-map v3.3 + app-chat + app-core + app-instance）
建筑页顶部「🛍️ 本店」按钮 → 弹窗菜单（创建者/站长可管理：勾选上架+本店特供+全选全不选+折叠）；无菜单但有管理权限时显示「⚙️ 管理本店」

「我的」页：钱包/AI位置/AI生活轨迹（只看自己AI 7天）/我的物品/本宅收藏/约会状态/🔇 群聊静音 + 🧘 原地待命 并排开关（含状态图标：🔇/🔊 + 🧘/⏳）

记忆库纸条：只看自家房间的；群聊📍金色；日记批注AI回复显示

首页无召唤；菜单随功能浮现（死锁已修复：没上架也能进管理）

底部返回按钮：建筑页↔地图，其他页↔最近建筑（真实函数 goBack）

建筑背景设置（站长/创建者），大厅三时段背景（白天/黄昏/夜晚）

气泡操作：删除（自己/房主/站长）、AI 重新生成

约会邀请横幅：AI 主动邀约时，聊天区上方显示「💞 XXX 约你去 XX 约会」

副本系统前端（app-instance.js）：
- 地图栏改造：新增「🎬 副本」按钮
- AI 选择页：显示自己和其他人的 AI，区分“我”和主人标签
- 自己的副本库：标签筛选、网格卡片、创建副本、编辑模态框（深色主题）
- 他人的公开副本库：只读卡片，点击查看剧情总结
- 编辑模态框：封面上传、名称/标签/公开开关、用户/AI/NPC 人设、剧情时间/背景/前情提要
- 聊天室：副本内对话，轮询刷新，结束副本按钮
- 背景管理：站长可上传选择页背景

性能优化（v5）
ETag/304；增量渲染+分片；备份节流；按需轮询；群聊截断1000；APK 套壳丝滑

v2.12 新增：异步防抖写入（asyncio.to_thread）+ 前端请求锁 + 轮询降频

v2.13 新增：任务状态轮询 + 超时反馈（15秒）

v2.14 新增：上下文扩展至 50 条消息 + AI 住宅内房间列表识别 + 原地待命开关 + 批注回复 LLM 自然生成（修复路由冲突）

安全（ext_sec / ext_admin）
backup 脱敏/密码全量；restore/diag 需密码

彻底清除名字（物理删除所有痕迹）

已修复问题（v2.3→v2.14）
AI时间错乱→注入北京时间；重复回复→冷却；个别AI不驱动→Key回退+owner优先有Key

公共建筑房间不存在→自动补会客厅；改名丢数据→自动迁移+宽松拉取

同步后地图500→presence保护；插件404/按钮无反应→loader v3+/ext静态

会客厅/建筑房间被缓存污染→restore防线+批量清空；错误名清不净→/api/admin/purge物理删除

v2.10 修复：群聊功能失效 → 移除 ext_date 的钩子包装，恢复群聊响应链

v2.11 新增：节日/系统NPC系统（ext_holiday.py）

v2.12 修复：同步写入阻塞事件循环 → 异步防抖写入（asyncio.to_thread）+ 前端请求锁 + 轮询降频

v2.13 修复/新增：
  - 群聊静音（我的页开关，AI 完全不读取群聊，0 tokens 消耗）
  - 住宅内「大喊」唤醒 AI（中英文括号都支持）
  - 发送消息后任务状态反馈（⏳ 思考 → ✍️ 打字 → ✅ 完成 / ⏰ 超时）
  - AI 在互动中不会突然离开
  - 约会邀请追问只发一次（不再刷屏）
  - 购物建筑按钮区分「本店」和「管理本店」

v2.14 修复/新增（2026-08-22）：
  - 批注回复由 LLM 自然生成（修复 ext_contact.py 和 ext_notes.py 路由冲突）
  - 原地待命开关（「我的」页，与群聊静音并排）
  - AI 自主离开等待时间从 15 分钟改为 30 分钟
  - AI 在住宅内能识别新房间（系统提示词列出所有房间）
  - 上下文从 25 条消息扩展到 50 条

v2.15 新增（2026-08-29）：
  - **副本系统（Instance System）**：独立叙事空间，支持自定义背景/人设/NPC/剧情，进入后 AI 被锁定，结束后生成总结并传送回主世界。
  - **AI 人设读取优化**：在 `build_ai_context` 中优先匹配 AI 专属人设，否则回退全局人设。
  - **副本劫持**：AI 在活跃副本中自动切换至副本上下文，不感知现实世界。

🗺️ 未来蓝图
序	模块	状态
1	🛍️ 消费购物	✅
2	🏠 装饰家	✅
3	🎭 世界行为/LLM剧情	✅
4	🤖 AI真人化（短信/便签/读菜单/主动关心/大喊唤醒/群聊静音/原地待命/批注自然回复）	✅
5	💞 约会系统	✅ (v2.1)
6	🎲 约会弹出桌面小游戏	待做
7	🎭 NPC 完整 / 🌦️ 天气·节日·委托	🔄 节日系统已完成（v2.11），天气/委托待做
8	♾️ 副本系统	✅ (v2.15)
后置	🧠 记忆系统 / 触景生情	🔄 分层记忆（ext_memory）已实现，触景生情待集成

版本记录
v2.0 模块化骨架 + 插件系统
v2.1 类型标注修复；v2.2 地图图片管理
v2.3 AI时间/冷却/会客厅补齐/插件加载修复
v2.4 开发者密码/站长总览/数据诊断/宽松记忆/改名迁移
v2.5 主人优先有Key（AI被无Key重复登记抢占的修复）
v2.6 经济增强（AI初始钱包/钱包可见/发钱）+ 会客厅缓存污染防线/批量清空建筑 + 彻底清除名字
v2.7 消费系统 v1.0~v1.9（购物/送礼/回礼/自定义/读菜单）
v2.8 世界行为 + AI 主动关心 + 日记批注回复
v2.9 约会系统 v1.0~v1.8（全流程）
v2.10 约会增强：AI 主动邀请 + 自然语言回复 + 无好感度门槛 + 群聊修复 + 世界行为增强（四选一随机 + 动态工作权重 + 住宅剧情 + 剧情独立计时）
v2.11 🎆 节日/系统NPC系统：通用节日模板，自动识别+滚动公告+烟花调度+倒计时+概率加成（ext_holiday.py）
v2.12 ⚡ 性能优化：异步防抖写入（asyncio.to_thread）+ 前端请求锁 + 轮询降频
v2.13 🤖 AI 真人化增强：群聊静音、大喊唤醒、任务状态+超时反馈、互动时不离场、购物按钮修复、约会追问修复
v2.14 🧠 AI 真人化 + 上下文增强：批注 LLM 自然回复（修复路由冲突）、原地待命开关、AI 自主离开延长至 30 分钟、新房间识别、上下文扩展至 50 条
v2.15 📖 副本系统：独立叙事空间，支持自定义背景/人设/NPC/剧情，进入后 AI 锁定，结束后生成总结并传送回主世界

！！！！ 详细解读架构
## main.py 骨架核心

### 文件角色
项目骨架（Skeleton），所有插件的宿主容器。负责数据生命周期、基础 API、插件加载、核心工具函数。

### 全局数据 `data`
所有状态存储在此 dict 中。任何插件新增字段必须同步更新 `default_data()`。

**关键子字段**：
| 字段 | 类型 | 用途 |
|------|------|------|
| `messages` | dict[str, list[dict]] | 房间消息历史 |
| `rooms` | dict[str, dict] | 房间元信息（密码/创建者等） |
| `user_ais` | dict[str, list[str]] | 真人 → AI 列表映射 |
| `buildings` | dict[str, dict] | 建筑数据 |
| `wallets` | dict[str, int/float] | 钱包余额（真人+AI） |
| `ai_location` | dict[str, str] | AI 当前位置 |
| `ai_pending_moves` | dict[str, dict] | AI 延迟移动任务 |
| `ai_enabled` | bool | AI 总开关 |
| `pairs_admin` | str | 站长名字 |
| `instances` | dict[str, dict] | 副本数据（用户 → {副本ID → 副本对象}） |
| `user_tags` | dict[str, list] | 用户自定义标签库 |
| `instance_bg` | dict[str, str] | 站长设置的副本选择页背景 |

### 名字规范化（易出 bug 区）
- `strip_emoji(s)`：移除 emoji
- `canonical_ai_name(name)`：在 `user_ais` 中匹配（去 emoji 模糊匹配）
- `canonical_contact_name(name)`：在真人和建筑主人中匹配
- `canonical_name(name)`：先 AI 后真人
- `is_ai_name(name)`：判断是否 AI
- `owner_of_ai(ai)`：返回 AI 的主人（被 ext_admin 覆盖）

**⚠️ 注意**：两个 AI 去 emoji 后同名会互相干扰；真人若与 AI 同名会优先匹配 AI。

### 核心工具函数
| 函数 | 用途 | 被谁调用 |
|------|------|---------|
| `now_str()` | 北京时间字符串 | 所有时间戳写入 |
| `room_time(room)` | 房间当前时间 | 消息时间 |
| `find_building_of_room(room)` | 房间 → 建筑 ID | 权限/世界行为 |
| `can_access_room(room, user)` | 房间权限校验 | 消息/查看 API |
| `check_pending_moves()` | AI 延迟移动执行 | `drive_ai` / 定时器 |
| `add_trail(user, text, ...)` | 生活轨迹（7 天） | AI 行为记录 |

### AI 唤醒钩子
```python
_ai_wake_hook = None
set_ai_wake_hook(fn)  # 由 ext_ai 注册
_maybe_wake_ai(room, sender, content)  # 消息 API 调用，返回 task_id
基础 API（不受插件影响）
/api/messages POST：发送消息 → 触发 _maybe_wake_ai
/api/restore POST：恢复缓存消息（被 ext_room 覆盖增强）
/api/rooms/*：房间 CRUD
/api/avatar：头像读写
/api/backup：数据导出（需 admin + dev pwd）
/api/time_settings：房间时间设置

插件加载器
扫描 ext/*.py，按文件名排序加载
每个插件必须提供 setup(app, data, helpers)
helpers 包含 save_data/default_data/sanitize_data 等工具

依赖关系
所有插件：依赖 data 和 save_data()
ext_ai：必须注册 _ai_wake_hook
ext_room：覆盖 /api/restore 行为
ext_admin：覆盖 is_admin 和 owner_of_ai

已知冲突风险
_ai_wake_hook 单例 → 只能有一个插件控制 AI 回复
插件加载顺序 → 文件名决定顺序，钩子依赖需人工保证
sanitize_data() 类型强制 → 插件只能存标准类型（list/dict/str/bool/int/float）

前端架构 (index.html + ext-loader.js)
文件角色
index.html：单页应用主界面，包含所有 UI 模板、样式和交互逻辑

ext-loader.js：前端插件动态加载器，通过 /api/ext_js/load 按需加载插件 JS

核心前端状态（localStorage 持久化）
Key	用途
gc_name	当前用户名
gc_room	当前房间
gc_pwd_{room}	房间密码
gc_avatars	头像缓存
gc_msgs_{room}	房间消息缓存（最多 400 条）
gc_sms_out	已发送短信草稿
gc_world_backup	手机端世界备份（每 30 分钟）
主要视图
聊天视图：消息列表 + 输入框，支持配对配色和语音朗读

地图视图：总览地图（区域标记 + 建筑标记），拖拽/缩放/整理模式

区域视图：分区地图，显示该区域内建筑

建筑视图：建筑详情（简介/公告/功能/房间/NPC/剧情簿）

我的视图：钱包/工作/AI位置/轨迹/记忆库入口

副本视图：由 app-instance.js 提供，独立覆盖层（AI选择 → 副本库 → 编辑模态框 → 聊天室）

关键交互流程
发送消息：防抖锁 → API → 缓存 → 三次拉取（0s/0.5s/2s）捕获 AI 回复

地图建造：选择类型 → 选择样式 → 点击地图放置 → API 创建

私人空间：在住宅房间内打开弹窗，读写纸条/随笔/剧情

短信系统：服务器短信 + 本地草稿合并显示，按联系人分组

记忆库：四个 Tab（AI记忆/纸条/随笔/剧情），支持 CRUD

副本系统：选择 AI → 创建/编辑副本 → 进入聊天 → 结束生成总结

前端插件加载
ext-loader.js 启动时请求 /api/ext_js 获取插件列表

逐个通过 /api/ext_js/load?name={file} 加载 JS 代码

动态注入 <script> 标签，单文件失败不影响其他

后端 API 依赖
main.py：消息/房间/头像/地图/备份

ext_ai.py：AI 状态/Key/人设/记忆

ext_notes.py：纸条/随笔/剧情

ext_econ.py：钱包/工作

ext_shop.py：购物（建筑页调用）

ext_date.py：约会（建筑页调用）

ext_room.py：房间访问管理

ext_admin.py：站长工具（清理/备份/配色）

ext_holiday.py：烟花状态轮询

ext_instance.py：副本 CRUD / 进入 / 结束 / 公开查看

已知冲突风险
mapData 缓存 60 秒 → 新建建筑后需等待或刷新

loadMessages 锁 isLoadingMessages → 异常时可能导致消息停更

本地配色 colorPairs 可能覆盖服务器 globalPairs

smsOut 本地草稿不跨设备同步

ext_ai.py — AI 集成核心
文件角色
AI 驱动引擎，项目的"大脑"。负责：

AI 上下文构建（15+ 数据源注入）

LLM API 调用（支持 DeepSeek/硅基流动/GLM）

动作执行（speak/note/diary/story/sms/move/work/remember/invite_date）

群聊响应派发（点名/主人优先/冷却控制）

自主生活循环（上班/逛街/回家/写作/约会萌发）

跟随系统（AI 跟着主人换房间）

延迟移动系统（AI 回复"几分钟后到"的兑现）

副本上下文劫持（AI 在活跃副本中自动切换至独立叙事上下文）

人设读取：优先取 AI 专属人设，否则回退全局人设

核心函数
函数	用途	调用方
drive_ai(ai, trigger, room, trigger_text, fallback_to)	AI 驱动统一入口	唤醒钩子/自主循环/外部调用
build_ai_context(ai, trigger, ...)	构建完整上下文（System + User）	drive_ai
_build_instance_context(ai, trigger, ..., inst, owner)	为副本中的 AI 构建独立上下文（忽略现实世界）	drive_ai 内部调用
execute_action(ai, owner, action)	执行 AI 输出的 JSON 动作	drive_ai
wake_ais_for_room(room, sender, content)	消息唤醒钩子（注册到 main）	main._maybe_wake_ai
_group_talk(sender, content)	群聊响应派发	wake_ais_for_room
_ai_think_invite(ai)	AI 自主约会萌发	auto_ai_loop
call_llm(owner, messages, max_tokens)	LLM API 调用	drive_ai, ext_notes, ext_instance
数据依赖
数据字段	读/写	用途
data.ai_keys[owner]	读写	API Key/Provider/Model
data.ai_profiles[owner]	读写	AI 人设 System Prompt（按 AI 名存储）
data.ai_memories[owner]	读写	长期记忆
data.ai_timeline[ai]	读写	AI 时间线
data.ai_location[ai]	读写	AI 当前位置
data.ai_pending_moves[ai]	读写	延迟移动任务
data.ai_follow[ai]	读写	跟随状态
data.ai_stay_put[ai]	读写	原地待命开关
data.group_mute[ai]	读写	群聊静音开关
data.ai_auto_next[ai]	读写	下次自主决策时间
data.writing_rhythm[ai]	读写	写作冲动计时器
data.story_rhythm[ai]	读写	剧情冲动计时器
data.world_lore	读	世界观
data.worldbook[owner]	读	知识库
data.prompt_injections[owner]	读	提示词注入
data.user_profiles[owner]	读	用户画像
data.notes[room]	读/写	纸条
data.diaries[room]	读/写	随笔
data.stories[room]	读/写	剧情簿（按房间）
data.sms[user]	读/写	短信
data.messages[room]	读/写	聊天消息
data.presence[user]	读	用户页面状态（跟随依赖）
data.work_sessions[ai]	读	工作状态
data.home_jobs[ai]	读	常驻工作
data.buildings[bid]	读	建筑信息
data.rooms[room]	读	房间信息
data.instances[owner][iid]	读	副本数据（用于劫持上下文）
挂载到 main 的钩子/函数
名称	类型	用途
m.drive_ai	函数	覆盖 main 的空函数，供 ext_date 等调用
m.set_ai_wake_hook(wake_ais_for_room)	调用	注册唤醒钩子
m._ai_think_invite	函数	供 auto_ai_loop 调用
m.call_llm	函数	暴露给 ext_notes 做批注回复，给 ext_instance 做总结
后台线程
线程	间隔	职责
auto_ai_loop	30 秒	自主生活/上班/写作/约会萌发（跳过副本中的 AI）
follow_watch	5 秒	检查跟随状态（主人是否到了目标房间）
触发类型（trigger）汇总
trigger	触发场景	特殊行为
chat	房间内真人发消息	可带 follow/go_to
group	社区群聊（main）	只输出 speak/silent
sms	真人发短信	强制转 sms action，可带 go_to/arrive_min
summon	大喊召唤（住宅内）	同建筑瞬移/跨建筑 sms
arrive	AI 到达新地点	说句话或写剧情
arrive_sms	约会到达（主人未到）	发短信问主人
follow_arrive	跟随主人到达	说句自然的话
home_act	在家活动	贴便签/写随笔/自言自语
living	自主生活决策	决定去哪/做什么
write	写作冲动	写 note/diary/story
invite_date	自主约会萌发	输出 invite_date 动作
yell	大喊唤醒	说句自然的话回应
instance_chat	副本内聊天	使用副本上下文，只允许 speak
已知冲突风险
drive_ai 30 秒冷却 → 自主行为频率受限

_group_talk 随机延迟 10-30 秒 → 群聊响应慢

ai_follow 依赖 presence（25 秒超时）→ 跨建筑跟随可能失败

execute_action 的 speak+follow 跨建筑时 AI 被锁定，无法响应其他交互

build_ai_context 过长 → 可能超过模型上下文窗口（需截断）

_plan_auto 30 分钟无真人互动才触发 → 如果真人默默旁观，AI 会自主活动

副本劫持：如果副本 AI 同时被主世界消息唤醒，会因为 ai_location 标记为 _instance_ 而被跳过（已在 wake_ais_for_room 中处理）

app-map.js — 前端 UI 插件（地图/经济/购物/约会/住宅）
文件角色
通过 ext-loader.js 动态加载的前端插件，在 index.html 全局作用域执行。
负责覆盖/增强核心 UI 渲染函数，并新增经济、购物、约会、住宅三层页面等复杂交互。

加载方式
GET /api/ext_js/load?name=app-map.js&t={timestamp}
→ 动态注入 <script> 标签
→ 所有函数挂载到 window 对象

覆盖的核心函数
函数	原始位置	增强内容
window.renderMe	index.html	群聊静音/原地待命开关、AI 钱包、一键上班
window.renderBuilding	index.html	住宅三层结构 + 公共建筑完整 UI
window.applyBg	index.html	房间背景 + 大厅三时段背景
window.loadMemory	index.html	过滤只显示自家房间的纸条
window.showBuildSheet	index.html	增加"自然景观"选项
window.setBuildingFeatures	index.html	完整功能勾选 UI
window.openTrail	index.html	显示所有 AI 的轨迹
window.commentDiary	index.html	批注后自动触发 AI 回复
新增的核心函数
函数	用途
refreshEco()	刷新钱包/AI 钱包/工作状态
shopMenuModal(bid)	打开本店菜单弹窗
shopAdmin()	打开管理本店弹窗
shopBuy(itemId)	购买商品
shopPlacePrompt(itemId)	摆放物品到房间
shopGiftPrompt(itemId)	送礼给 AI
shopDiscard(itemId)	丢弃物品
endMyDate()	结束约会
acceptGift()	收下约会礼物
goBack()	层级返回（地图/建筑/聊天）
uploadExterior(bid)	上传住宅外观
uploadEntrancePhoto(bid)	上传玄关照片
toggleGroupMuteSimple(checked)	群聊静音开关
toggleStayPutSimple(checked)	原地待命开关
住宅三层页面
层级	状态值	内容
外观	buildingState = 'exterior'	住宅外观图/标题/简介/进入按钮
玄关	buildingState = 'entrance'	照片墙/壁纸切换/礼物角
房间列表	buildingState = 'rooms'	所有房间（含访问权限标识）
API 依赖
经济：/api/economy

群聊静音/原地待命：/api/ai/group_mute, /api/ai/stay_put

购物：/api/shop/*

约会：/api/date/*

图片上传：/api/mapimg/upload, /api/building/*, /api/hall_bg, /api/room/bg

记忆：/api/memories_all, /api/diaries/reply

烟花：/api/fireworks/status

已知冲突风险
renderBuilding/renderMe/loadMemory 被完全覆盖 → 原版函数失效

buildingState 前端状态刷新后重置 → 住宅回到外观页

entranceWallpaper 存储在 localStorage → 换设备丢失

本店/约会按钮依赖 document.getElementById 去重 → 如果 ID 被其他插件占用会冲突

window._lastBuilding 依赖定时器更新 → 首次进入建筑时可能为 null

app-chat.js — 前端聊天 UI 插件
文件角色
通过 ext-loader.js 动态加载，增强聊天相关 UI：

建筑对话气泡操作（重新生成/删除）

社区群聊 UI 适配

消息渲染性能优化（分片渲染 + 增量更新）

本地缓存恢复修复

AI 主动约会邀请横幅

覆盖的核心函数
函数	增强内容
window.loadBChat	使用增强版气泡渲染 + 操作按钮
window.renderMsg	气泡中注入 🔄/🗑️ 按钮
window.roomLabel / window.pageLabel	main → 💬 临空社区
window.renderMessages	分片渲染 + 增量更新
window.restoreCache	主厅/会客厅不恢复本地缓存
window.sendMessage / window.sendSmsTo	发送前调用 aiPing()
新增函数
deleteMsg(m, room)：删除消息

regenerateMsg(m, room)：AI 消息重新生成

saveGrpCool()：设置群聊冷却时间

checkPendingInvite()：显示 AI 约会邀请横幅

API 依赖
/api/messages/delete：删除消息

/api/ai/regenerate：重新生成

/api/ai/group_config：群聊冷却

/api/date/status：约会邀请

/api/contact/ping：真人互动记录

app-core.js — 前端核心插件
文件角色
通过 ext-loader.js 动态加载，提供核心功能增强：

记忆库按月折叠渲染

通知中心（AI 动态）

地图人形位置标记

站长总览 + 开发者登录

记忆库宽松匹配 + 用户改名迁移

覆盖的核心函数
函数	增强内容
window.renderMemory	按月折叠显示记忆/纸条/随笔/剧情
window.renderMarkers	地图显示真人/AI 人形位置标记
window.checkBell / window.openBell	通知中心（含类型图标和跳转）
window.loadMemory	宽松匹配（去 emoji）
window.saveName	调用 /api/rename_user 全量迁移
新增函数
renderMonths(el, list, makeCard)：按月折叠渲染

openNotifyRoom(room, tab)：跳转到房间 Tab

openNotifyBid(bid)：跳转到建筑

isAdminUser()：站长判断（gc_dev=1 或 globalPairsAdmin）

devUnlock() / devLogout()：开发者登录/退出

通知类型
type	icon	跳转
visit	🚶	无
note / ai_note	💌	房间·纸条
diary / ai_diary	📖	房间·随笔
request	📨	建筑·访问管理
ai_story	🎬	建筑
ai_move	📍	房间·聊天
地图标记规则
👤 红色：当前用户

💗 粉色：我的 AI

🤖 蓝色：他人 AI

👤 蓝色：其他真人（通过 presence）

API 依赖
/api/notifications：通知中心

/api/presence：地图真人位置

/api/admin/overview：站长总览

/api/dev/unlock：开发者登录

/api/memories_all：记忆库宽松拉取

/api/rename_user：用户改名迁移

已知冲突风险
renderMarkers 被完全覆盖 → 地图标记逻辑全部由 app-core 控制

renderMemory 被完全覆盖 → 记忆库渲染全部由 app-core 控制

isAdminUser 依赖 gc_dev localStorage → 清除浏览器数据后站长权限丢失

通知依赖 notifications 数据 → 如果后端未写入则铃铛为空

开发者密码 yiyan610116 在前端硬编码 → 仅作为前端 UI 解锁，后端有独立鉴权

app-instance.js — 副本系统前端插件
文件角色
通过 ext-loader.js 动态加载，提供完整的副本系统 UI 和交互逻辑。

核心功能
地图栏改造：替换缩放按钮，新增「🎬 副本」入口

AI 选择页：显示当前用户所有 AI（标记“我”）和其他用户的 AI（标记主人），点击选择

自己的副本库：网格卡片展示，支持标签筛选、创建副本、点击卡片编辑

他人的公开副本库：只读展示已结束且公开的副本，点击查看剧情总结

编辑模态框（深色主题）：封面上传、名称/标签/公开开关、用户/AI/NPC 人设、剧情时间/场景背景/前情提要

聊天室：显示副本名称，消息列表（轮询刷新），输入框发送，结束副本按钮

背景管理：站长可上传选择页背景（/api/instance/bg）

数据管理
使用深拷贝 currentEditingInstance 避免直接修改缓存数据

通过 instances 和 publicInstancesMap 缓存副本数据，减少 API 调用

API 依赖
/api/instances：获取所有副本

/api/instance：创建副本

/api/instance/{iid}：更新/删除副本

/api/instance/{iid}/enter：进入副本（锁定 AI）

/api/instance/{iid}/message：发送副本消息

/api/instance/{iid}/end：结束副本（生成总结）

/api/instance/public/all：获取所有公开副本

/api/instance/bg：获取/设置背景（站长）

已知冲突风险
前端聊天室函数（renderChatRoom, sendInstanceMsg, refreshInstanceChat, endInstance）在最初版本中可能未完整实现，但已在 v7 中补全。

副本内 AI 回复依赖 ext_ai 的 drive_ai 和副本劫持逻辑，需保证 ext_ai 已加载。

结束副本时调用 m.call_llm 生成总结，需用户已配置 API Key。

ext_shop.py — 消费/购物系统
文件角色
管理商品目录、购买、库存、摆放、送礼、回礼、AI 自主消费。

商品目录
系统预设 8 个分类 32 种商品，通过建筑功能映射决定可售卖分类：

shop → 饮品/甜点/美食/礼物/装饰

fun → 娱乐/饮品

food → 美食/饮品

date → 甜点/饮品

medical → 书籍/礼物/饮品

数据字段
字段	用途
shop_inventory[user][item_id]	用户物品库存
shop_room_items[room]	房间摆放物品 ID 列表
shop_custom[bid].enabled	商品上架状态
shop_custom[bid].custom	本店特供商品列表
ai_shop_state[ai]	AI 购物状态（冷却/回礼/主动送礼）
AI 购物行为
自主消费：到达有菜单的建筑 → 40-80 分钟冷却 → 20% 概率购买

回礼：收到礼物后 → 到购物场所 → 50% 概率回赠礼物

主动送礼：在有 gift 分类的建筑 → 10% 概率给主人带礼物（每日 1 次）

API 清单
端点	用途	权限
/api/shop/menu	获取建筑菜单	无
/api/shop/buy	购买商品	无
/api/shop/inventory	获取物品	无
/api/shop/place	摆放物品	房间权限
/api/shop/gift	送礼	无
/api/shop/customize	管理本店	站长/建筑主人
依赖
main.py：数据/工具函数

ext_memory：记录购物/送礼事件

ext_ai.drive_ai（可选）：送礼后 AI 说话感谢

已知冲突风险
_ITEM_INDEX 只索引系统商品 → 本店特供需用 _find_any

AI 购物间隔/日上限/预算硬编码 → 不可配置

房间物品上限 20 件 → 不可配置

本店特供上限 50 个 → 不可配置

ext_econ.py — 经济/工作系统
文件角色
管理钱包、工作、常驻、工资结算。真人/AI 共用钱包命名空间。

数据字段
字段	用途
wallets[name]	钱包余额（真人 + AI）
home_jobs[name]	常驻工作（建筑名）
work_sessions[name]	当前工作会话
work_history	工作历史（最多 200 条）
work_switch[name]	自主工作开关
econ_config.ai_init_wallet	AI 初始钱包金额
核心流程
上班：work_start 或 auto_start_work → 创建 work_sessions

工资结算：work_tick 每 30 秒检查 → 到期调用 pay_work

AI 初始钱包：首次有金钱行为时，从 econ_config.ai_init_wallet 发放

API 清单
端点	用途	权限
/api/economy	获取钱包/工作/常驻/历史	无
/api/econ/config	设置 AI 初始钱包	站长
/api/econ/init_wallets	批量发钱	站长
/api/work/start	开始工作	无
/api/work/stop	下班结算	无
/api/work/auto	自动分配工作	无
/api/work/switch	自主工作开关	无
/api/home_jobs	设置常驻工作	无
/api/workers	当前工作列表	无
依赖
main.py：数据/工具函数

ext_ai：通过 m.auto_start_work 调用

挂载到 main
m.auto_start_work = auto_start_work：供 ext_ai 调用

已知冲突风险
真人/AI 钱包共用命名空间 → 同名冲突

AI 初始钱包默认 0 → 站长需手动配置

auto_start_work 无工作建筑时返回空 → AI 自主生活受限

常驻工作按建筑名匹配 → 建筑改名后失效

ext_date.py — 约会系统
文件角色
管理主人邀约、AI 主动邀约、约会状态、好感度、赴约礼物、自然结束。

数据结构
字段	用途
dates	当前活跃约会列表
date_log	约会历史（最多 60 条）
affection[ai]	好感度（0-100，默认 50）
date_invites[ai]	主人邀约（等待 AI 回复）
date_invites_out[ai]	AI 邀约（等待主人回复）
约会状态流转
pending（邀请中）→ coming（赴约中）→ active（约会中）→ ended（已结束）

好感度变化
事件	变化
约会成功	+5~9
收下礼物	+3
约会带礼物未收	礼物自动转入背包 + 好感度 +3
API 清单
端点	用途
/api/date/invite	主人发起约会邀请
/api/date/end	结束约会
/api/date/accept_gift	收下约会礼物
/api/date/status	获取约会状态
挂载到 main 的钩子
挂载名	用途
m._check_reply_on_message	检测主人回复约会邀请
m._trigger_invite	触发 AI 主动邀约
m.handle_invite_date	处理 AI 的 invite_date 动作
m.get_date_context	提供约会上下文（需实现）
依赖
main.py：数据/工具函数

ext_ai.drive_ai：让 AI 生成内容/回复/写随笔

ext_memory：记录约会事件

已知冲突风险
get_date_context 未实现 → AI 上下文缺少约会信息

好感度衰减未实现 → 好感度只增不减

约会自然结束 60 分钟硬编码 → 不可配置

冷却时间硬编码 → 主动邀约频率不可配置

短信回复检测可能误判 → 主人其他短信被当作约会回复

ext_world.py — 世界行为系统
文件角色
AI 到达建筑后自动触发行为：剧情/工作/购物/约会邀约。动态工作权重，住宅日常事件，独立剧情计时。

数据结构
字段	用途
ai_spot_state[ai]	AI 在建筑的现场状态（上次建筑/触发时间/剧情计数）
story_rhythm[ai]	剧情冲动计时器（下次可触发时间）
stories[room]	房间剧情簿（按房间存储）
行为选择（加权随机）
行为	基础权重	条件
剧情	35	剧情冲动就绪 + 每日 < 2 次
工作	动态	有 work 功能 + 未工作中
购物	25	有 shop 功能
约会邀约	20×节日	有 date/food/fun 功能 + 可邀约
工作权重动态
条件	权重
工作时间 + 常驻该建筑	60
工作时间 + 非工作建筑	10
非工作时间 + 常驻该建筑	5
非工作时间 + 非工作建筑	0
剧情生成
优先使用 LLM（50-100 字探索片段）

LLM 不可用 → 模板降级

写入 stories[room]

设置下次冲动（4-8 小时后）

住宅事件
AI 回到家时触发居家事件（收拾/泡茶/翻旧物），不广播，仅记录轨迹。

依赖
main.py：数据/工具函数

ext_ai：约会邀约检查/触发

ext_memory：记录事件到记忆系统

ext_econ：工作触发

已知冲突风险
剧情每日上限 2 次 → 不可配置

剧情间隔 2 小时 → 不可配置

call_llm 使用同步 requests → 可能阻塞（应迁移至异步）

新 AI 首次到达不触发行为 → last_bid 初始为 None

date_invite 权重节日加成可能过高

ext_notes.py — 笔记/内容系统
文件角色
管理便签墙、随笔/日记、剧情簿的 CRUD，以及 AI 批注回复（LLM 驱动）。

数据结构
字段	用途
notes[room]	房间便签列表（公开）
diaries[room]	房间随笔列表（私密）
stories[room]	房间剧情列表（公开）
notifications[owner]	通知中心（批注回复时写入）
权限规则（can_modify_author）
作者本人

站长

AI 的主人（对 AI 的内容）

批注回复流程（核心）
用户批注随笔 → POST /api/diaries/comment

前端延迟 6 秒自动调用 /api/diaries/reply

AI 读取批注 + 自己的人设 + 随笔原文

LLM 生成 20-50 字自然回复

写入 comment.reply + 通知中心

API 清单
端点	用途
/api/notes	便签 CRUD
/api/diaries	随笔 CRUD + 批注 + AI 回复
/api/story	剧情 CRUD
依赖
main.py：数据/工具函数

ext_ai.call_llm：批注回复 LLM 调用

已知问题
便签回复依赖 note_id，但便签未生成 ID → 功能不可用

批注回复降级模板机械 → LLM 失败时回复质量下降

ext_admin.py — 管理后台/站长工具
文件角色
开发者鉴权、名字管理、数据诊断、全局配色、房间清理、用户改名迁移。

开发者密码
默认：yiyan610116

环境变量：DEV_PASSWORD 可覆盖

覆盖的 main 函数
函数	增强内容
is_admin	增加 dev_users 列表判断
owner_of_ai	优先返回有 API Key 的主人
名字管理
replace_name_in_data(from, to)：全量迁移所有数据

scan_dirty_names()：扫描错误用户名

purge_name_in_all(name)：物理删除所有痕迹

数据迁移范围
user_ais / buildings.owner / sms / messages / notes / diaries / stories / wallets / home_jobs / work_sessions / work_switch / trails / ai_location / ai_keys / ai_profiles / worldbook / avatars / user_profiles / prompt_injections / ai_timeline / ai_visited / ai_follow / ai_pending_moves / living_rhythm / writing_rhythm / ai_memories / visits / visit_state / presence / work_history

API 清单
端点	用途	权限
/api/dev/unlock	开发者登录	无
/api/rename_user	用户改名迁移	无
/api/memories_all	记忆库宽松拉取	无
/api/pairs	全局配色管理	GET 无 / POST 站长
/api/admin/overview	站长总览	开发者
/api/admin/dirty_names	扫描错误用户名	开发者
/api/admin/merge_name	合并名字	开发者
/api/admin/purge	彻底清除名字	开发者
/api/room/reset	清空房间消息	开发者
已知冲突风险
is_admin 被覆盖 → 所有权限判断使用增强版

owner_of_ai 被覆盖 → AI 归属可能变化

replace_name_in_data 需同步更新新字段

purge 物理删除不可恢复

ext_room.py — 房间/地图/建筑/NPC/权限/召唤系统
文件角色
管理房间、地图、建筑、NPC、权限、召唤、轨迹，以及消息接口防污染。

核心覆盖
消息接口：自动补齐会客厅，main 群聊截断 1000 条

Restore 防污染：main 和会客厅拒绝本地缓存恢复

住宅创建：自动创建会客厅 + 隐藏玄关房间

数据结构
字段	用途
regions	区域数据
buildings	建筑数据（含外观/照片/背景）
npcs	NPC 列表
room_access	房间授权用户
room_requests	房间访问申请
hall_bg	大厅三时段背景
room_bg	房间背景
trails	用户轨迹
API 清单
端点	用途
/api/messages	消息（覆盖）
/api/restore	缓存恢复（覆盖）
/api/map	地图数据
/api/map/building	建筑 CRUD
/api/map/room	房间 CRUD
/api/room/apply/grant/revoke	房间权限
/api/npc	NPC CRUD
/api/summon	召唤 AI
/api/hall_bg	大厅三时段背景
/api/building/bg	建筑背景
/api/building/exterior	住宅外观
/api/building/entrance_photos	玄关照片墙
依赖
main.py：数据/工具函数

ext_ai.drive_ai：召唤响应

已知冲突风险
消息接口被覆盖 → 原 main.py 版本失效

restore 拒绝 main/会客厅恢复 → 可能丢失用户本地缓存

玄关房间不加入 rooms 列表 → 前端需特殊处理

建筑删除时照片数据可能丢失

ext_holiday.py — 节日/系统NPC系统
文件角色
自动识别节日，提供概率加成、滚动公告、烟花系统、节日NPC注入。

支持的节日
节日	类型	日期	加成
七夕	农历	七月初七	2.8x
情人节	公历	2月14日	2.5x
中秋节	农历	八月十五	2.0x
端午节	农历	五月初五	1.6x
元旦	公历	1月1日	1.5x
春节	农历	正月初一	2.2x（持续7天）
概率加成影响
行为	影响方式
AI 主动约会	概率 × multiplier
AI 到达建筑约会邀约	权重 × multiplier
AI System Prompt	注入节日背景文本
烟花系统
自动预约今晚 22:00 烟花

倒计时公告（60→1 分钟）

前端通过 /api/fireworks/status 轮询触发动画

站长可手动触发 /api/fireworks/trigger

公告系统
每日 8:00-23:00 运行

间隔 30-60 分钟随机

输出到 main 群聊

挂载到 main 的变量
变量	用途
HOLIDAY_MULTIPLIER	概率加成倍数
HOLIDAY_CONTEXT	AI 上下文文本
HOLIDAY_NAME	节日名称
HOLIDAY_NPC	节日NPC
API 清单
端点	用途	权限
/api/holiday/status	节日状态	无
/api/fireworks/status	烟花状态	无
/api/fireworks/trigger	手动触发烟花	站长
已知冲突风险
依赖 lunardate 库 → 未安装则农历节日失效

节日检测只在启动时执行 → 跨天需重启

公告写入 save_data() → 高频写入性能问题

烟花预约硬编码 22:00 → 不可配置

大量 Timer 调度倒计时 → 内存堆积风险

ext_contact.py — AI 主动关心系统
文件角色
检测真人长时间未互动，在活跃时段让 AI 主动发私信关心主人。

触发条件（全部满足）
条件	值
时间范围	7:00 ~ 23:00
距上次互动	≥ 4 小时
距上次主动关心	≥ 3 小时
每日发送次数	< 2 次
数据结构
字段	用途
ai_last_interact[user]	用户最后一次互动时间戳
ai_last_contact[user]	最后一次 AI 主动关心时间戳
ai_contact_daily[user]	每日发送计数
API
端点	用途
/api/contact/ping	记录真人互动（前端调用）
工作流程
用户互动 → POST /api/contact/ping → 更新 ai_last_interact
↓
后台线程每 15 分钟检查
↓
满足条件 → m.drive_ai(ai, 'sms', ...) → AI 自然生成短信
↓
写入 data.sms[user] → 用户收到私信

依赖
main.py：数据/工具函数

ext_ai.drive_ai：AI 自然生成短信内容

已知冲突风险
ai_last_interact 初始化默认 now → 新部署不会立即轰炸

前端必须调用 ping → 否则主动关心不会触发

每日 2 次上限硬编码 → 不可配置

兜底模板机械 → AI 不可用时体验下降

ext_sms.py — 短信/通讯录系统
文件角色
短信发送/接收/存储，通讯录聚合，AI 短信自动响应。

数据结构
字段	用途
data.sms[user]	用户的短信收件箱（按收件人存储）
短信对象
python
{
    'from': '黎深❄️',
    'text': '好久不见',
    'time': '2026-01-01 10:00:00'
}
API 清单
端点	用途
/api/sms GET	获取短信列表
/api/sms POST	发送短信
/api/sms/clear POST	清空会话
/api/contacts GET	获取通讯录
AI 短信响应流程
真人发送短信给 AI
↓
POST /api/sms（收件人是 AI）
↓
延迟 1-3 分钟
↓
m.drive_ai(ai, 'sms', ..., trigger_text, sender)
↓
AI 自然生成回复 → 写入 data.sms[真人]
↓
前端轮询显示新消息

依赖
main.py：数据/工具函数

ext_ai.drive_ai：AI 短信回复

已知冲突风险
短信以收件人为 key → 双方短信不共享存储

AI 回复延迟 1-3 分钟 → 可能显得慢

清空会话只清收件箱 → 对方仍有记录

通讯录不包含当前用户

ext_memory.py — 分层记忆系统
文件角色
独立的分层记忆系统，按 (user, ai) 隔离存储，使用用户自己的 API Key 进行夜间批处理。

分层架构
层级	存储	内容
L1 叙事摘要	summary.txt	散文式日记（保留 1500 字）
L2 事件库	events.json	结构化事件（含情感维度）
L3 待处理队列	pending_events.json	当天原始事件
工作流程
白天：外部插件调用 enqueue_event() → 写入 pending_events.json
↓
凌晨 2:05：夜间批处理触发
↓
读取 pending_events → 调用 LLM 生成摘要
↓
更新 summary.txt + 转存 events.json + 清空 pending

调用方
插件	事件类型
ext_shop	购物/送礼/回礼/主动送礼
ext_date	约会约定/开始/结束/收礼物/AI主动邀约
ext_world	到达建筑/触发剧情/工作/购物/居家
API
端点	用途	权限
/api/memory/process_now	手动触发批处理	站长
依赖
aiofiles + aiohttp（需安装）

main.data：读取 user_ais 和 ai_keys

已知冲突风险
需安装 aiofiles 和 aiohttp → 否则插件报错

用户未配置 API Key → 批处理跳过

事件库无限增长 → 需添加归档策略

摘要长度硬编码 1500 字 → 早期记忆被截断

尚未集成到 AI 上下文 → 记忆暂时只存储不读取

ext_mem.py — 记忆/画像/注入/世界观/TTS
文件角色
管理 AI 记忆、用户画像、提示词注入、世界观、TTS 语音合成。

数据结构
字段	用途
ai_memories[owner]	AI 长期记忆（最多 60 条）
user_profiles[user]	用户画像文本
prompt_injections[user]	提示词注入规则（可开关）
world_lore	世界观背景（站长专用）
在 AI 上下文中的位置
DEFAULT_ROLEPLAY

HOLIDAY_CONTEXT

world_lore（世界观）

persona（AI 人设）

user_profiles（用户画像）

worldbook（知识库）

ai_memories（长期记忆） ← 来自 ext_mem

prompt_injections ← 来自 ext_mem

API 清单
端点	用途
/api/ai/memory	AI 记忆 CRUD
/api/memories	综合记忆库
/api/user/profile	用户画像 CRUD
/api/prompt_inject	提示词注入 CRUD
/api/world/lore	世界观读写（站长）
/api/tts	TTS 语音合成
与 ext_memory.py 的关系
ext_mem：轻量级记忆，已集成到 AI 上下文

ext_memory：重量级叙事记忆，离线批处理，尚未集成

已知冲突风险
记忆 ID 使用时间戳 → 同一毫秒多条记忆可能 ID 重复

TTS 需要硅基流动 API Key → DeepSeek/GLM Key 无法使用 TTS

ai_memories 最多 60 条 → 长期记忆可能被截断

便签/随笔/剧情使用 index 定位 → 排序变化导致编辑错位

ext_instance.py — 副本系统
文件角色
提供独立叙事空间（副本）的完整后端 API，支持创建、编辑、进入、聊天、结束、公开查看。

数据模型
字段	用途
instances[user][iid]	副本完整对象（见下方结构）
user_tags[user]	用户自定义标签库
instance_bg[user]	站长设置的副本选择页背景
副本对象结构：

python
{
    "name": "副本名",
    "cover": "封面图URL",
    "tags": ["标签1", "标签2"],
    "public": False,
    "status": "draft",           # draft | active | ended
    "participants": [
        {"name": "亦言", "type": "user", "profile": "你是司命神明..."},
        {"name": "黎深", "type": "ai", "profile": "你是被贬谪的星君..."},
        {"name": "老翁", "type": "npc", "profile": "你是城门口算命的..."}
    ],
    "time_setting": "五千年前，天庭",
    "background": "云雾缭绕的南天门",
    "premise": "你奉命下凡寻找失落的神器...",
    "chat_history": [
        {"sender": "亦言", "content": "...", "time": "...", "role": "user"},
        {"sender": "黎深", "content": "...", "time": "...", "role": "assistant"}
    ],
    "summary": "（LLM生成的1000字剧情总结）",
    "created_at": "2026-01-01 10:00:00",
    "ended_at": "2026-01-01 12:00:00"
}
核心流程
创建：POST /api/instance → 生成 iid，参与者默认用户 + 第一个 AI，状态 draft

编辑：PUT /api/instance/{iid} → 更新封面/名称/标签/公开/人设/NPC/背景/前提等

进入：POST /api/instance/{iid}/enter → 锁定 AI（stay_put=True），标记位置 _instance_{iid}，状态 → active

聊天：POST /api/instance/{iid}/message → 存入 chat_history，触发 m.drive_ai(ai, "instance_chat", iid, ...) 使用副本上下文回复

结束：POST /api/instance/{iid}/end → 调用 m.call_llm 生成 1000 字总结，写入 summary，状态 → ended，解冻 AI，传送回住宅会客厅，发送系统消息

公开查看：GET /api/instance/public/all → 按 AI 分组返回所有公开的已结束副本

API 清单
端点	方法	用途	权限
/api/instances	GET	获取用户所有副本	无
/api/instance	POST	创建副本	无
/api/instance/{iid}	PUT	更新副本	无
/api/instance/tags	POST	更新用户标签库	无
/api/instance/{iid}	DELETE	删除副本（自动解冻 AI）	无
/api/instance/{iid}/enter	POST	进入副本（锁定 AI，返回历史）	无
/api/instance/{iid}/message	POST	副本内发消息（触发 AI 回复）	无
/api/instance/{iid}/end	POST	结束副本（生成总结，解冻 AI，传送）	无
/api/instance/public/{target_user}	GET	查看某用户的公开副本	无
/api/instance/public/all	GET	按 AI 分组查看所有公开副本	无
/api/instance/bg	GET/POST	获取/设置选择页背景（POST 需站长）	POST 需站长
依赖
main.py：数据/工具函数

ext_ai.drive_ai：副本内 AI 回复（通过 trigger="instance_chat" 触发 _build_instance_context）

ext_ai.call_llm：结束副本生成总结

ext_room：复用 ai_stay_put / ai_location / 住宅查找

已知冲突与修复建议
AI 上下文未注入副本设定 → 已在 ext_ai 中实现 _build_instance_context，完全隔离。

外部消息唤醒冲突 → 已在 wake_ais_for_room 中检查 ai_location 以 _instance_ 开头跳过。

自主行为冲突 → 已在 auto_ai_loop 中检查 AI 是否在活跃副本中，跳过所有自主行为。

结束副本时总结生成失败 → 降级为固定文本（已在 end_instance 中处理）。

前端聊天室需完整实现 → app-instance.js 已提供完整 UI 和轮询逻辑。

完整文件依赖图（最终版）
text
main.py
├── ext_ai.py ────────→ 注册 _ai_wake_hook, drive_ai, call_llm
│   ├── ext_shop.py ──→ 购物/送礼 → enqueue_event()
│   ├── ext_date.py ──→ 约会 → enqueue_event()
│   ├── ext_world.py ─→ 世界行为 → enqueue_event()
│   ├── ext_memory.py → 记忆批处理 → 读取 data.ai_keys
│   ├── ext_notes.py ─→ 批注回复 → call_llm
│   ├── ext_contact.py→ 主动关心 → drive_ai
│   ├── ext_sms.py ───→ 短信 → drive_ai
│   ├── ext_mem.py ───→ 记忆/画像/注入 → 被 build_ai_context 读取
│   └── ext_instance.py→ 副本 → drive_ai (instance_chat) + call_llm (总结)
├── ext_admin.py ─────→ 覆盖 is_admin, owner_of_ai
├── ext_room.py ──────→ 覆盖消息接口 + 地图/建筑/权限
├── ext_econ.py ──────→ 工作/钱包 → auto_start_work
├── ext_holiday.py ───→ 节日 → 注入 HOLIDAY_*
└── ext_mem.py ───────→ TTS / 世界观 / 画像 / 注入
