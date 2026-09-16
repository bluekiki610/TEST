好的，我会严格遵循你的要求：只新增印象系统相关内容，绝不修改或删除任何现有功能描述。以下是完整的 `PROJECT.md` 全量更新文件。

---

# 恋与临空 · 完整项目文档（PROJECT.md）

> 一座由你和你的 AI 共同生活的城市。AI 会自主生活、上班、逛街、买咖啡、写随笔、发现剧情、收礼回礼、偶尔想你发短信、还会主动约你约会……


## 一、项目概述

### 1.1 项目定位
**真人 + AI 共同生活的社区世界**：
- 真人可以建造建筑、聊天、逛店、装饰家、送礼物、约会
- AI 会自主生活，并对你的互动做出真实回应
- 网页和手机 App（APK）都能用，内容完全同步

### 1.2 技术栈
| 层级 | 技术 | 说明 |
|------|------|------|
| 后端 | Python 3.9+ / FastAPI | 异步 Web 框架 |
| 数据存储 | JSON 文件（持久卷） | `data/data.json` + 图片文件 |
| AI 服务 | DeepSeek / 硅基流动 / GLM | 用户自备 API Key |
| 前端 | 原生 JavaScript（SPA） | 单页应用，无框架依赖 |
| 移动端 | Capacitor（APK 套壳） | 网页套壳，永远最新 |
| 部署 | Zeabur / 任意 Docker 环境 | 环境变量配置 |

### 1.3 版本信息
- 核心骨架版本：v2-core
- 最新功能迭代：v2.16（2026-08-31）
  - v2.14：基础功能完善
  - v2.15：SSE 主动推送与移动端角标
  - v2.16：AI 印象备忘录系统（替代碎片记忆，动态更新）
- 插件化架构：所有功能按域独立为 `ext/*.py`


## 二、架构总览

### 2.1 目录结构
```
/
├── main.py                 # 骨架核心（数据管理、基础 API、插件加载）
├── index.html              # 前端单页应用（所有 UI 模板 + 基础交互）
├── ext-loader.js           # 前端插件加载器
├── ext/                    # 后端插件目录（按功能域拆分）
│   ├── ext_ai.py          # AI 驱动引擎（核心）
│   ├── ext_admin.py       # 管理后台 / 站长工具
│   ├── ext_contact.py     # AI 主动关心
│   ├── ext_date.py        # 约会系统
│   ├── ext_econ.py        # 经济 / 工作
│   ├── ext_holiday.py     # 节日 / 烟花 / 系统 NPC
│   ├── ext_mem.py         # 记忆库 / 画像 / 注入 / 世界观 / TTS
│   ├── ext_memory.py      # 分层记忆系统（夜间批处理）
│   ├── ext_notes.py       # 便签 / 随笔 / 剧情 + 批注回复
│   ├── ext_room.py        # 房间 / 地图 / 建筑 / 权限 / 召唤
│   ├── ext_shop.py        # 消费 / 购物 / 送礼 / 回礼
│   ├── ext_sms.py         # 短信 / 通讯录
│   └── ext_world.py       # 世界行为（到达触发）
├── data/                   # 数据存储目录（持久卷）
│   ├── data.json          # 主数据文件
│   ├── images/            # 图片资源（头像/背景/地图）
│   └── memories/          # 分层记忆存储（由 ext_memory 管理）
├── snapshots/              # 自动快照（每 30 分钟）
└── app-*.js               # 前端插件（通过 ext-loader 加载）
    ├── app-core.js        # 核心增强（记忆折叠/通知/地图标记/站长总览）
    ├── app-chat.js        # 聊天增强（气泡操作/群聊/性能/恢复修复）
    └── app-map.js         # 地图/经济/购物/约会/住宅 UI
```

### 2.2 数据流总览
```
用户操作（前端） → API 请求（后端）
    ↓
main.py 基础路由 + 插件路由
    ↓
插件处理逻辑 → 修改 data 字典 → save_data()（异步防抖写入）
    ↓
前端轮询拉取最新状态 → 渲染更新
```

### 2.3 核心依赖关系
- **所有插件** 依赖 `main.data` 和 `main.save_data()`
- **`ext_ai`** 是中枢，注册 `_ai_wake_hook`，提供 `drive_ai` 和 `call_llm`
- **`ext_admin`** 覆盖 `is_admin` 和 `owner_of_ai`
- **`ext_room`** 覆盖 `/api/messages` 和 `/api/restore`
- **`ext_holiday`** 注入 `HOLIDAY_MULTIPLIER` / `HOLIDAY_CONTEXT`
- **`ext_memory`** 独立运行，由其他插件调用 `enqueue_event`
- **前端插件**（app-*.js）在 `index.html` 全局作用域中增强/覆盖函数


## 三、数据层（main.py）

### 3.1 全局数据 `data` 字典
所有状态存储在此，任何插件新增字段必须同步更新 `default_data()`。

**核心子字段速查表**：

| 字段 | 类型 | 用途 | 主要读写插件 |
|------|------|------|-------------|
| `messages` | dict[str, list] | 房间消息历史 | main, ext_room, ext_ai |
| `rooms` | dict[str, dict] | 房间元信息 | main, ext_room |
| `user_ais` | dict[str, list] | 真人 → AI 列表映射 | ext_admin, ext_ai |
| `buildings` | dict[str, dict] | 建筑数据 | ext_room, ext_shop, ext_world |
| `wallets` | dict[str, float] | 钱包余额（真人+AI） | ext_econ, ext_shop |
| `ai_location` | dict[str, str] | AI 当前位置 | ext_ai, ext_room |
| `ai_pending_moves` | dict[str, dict] | AI 延迟移动任务 | ext_ai, ext_date |
| `ai_follow` | dict[str, dict] | AI 跟随状态 | ext_ai |
| `ai_enabled` | bool | AI 总开关 | ext_ai |
| `pairs_admin` | str | 站长名字 | ext_admin |
| `sms` | dict[str, list] | 短信收件箱 | ext_sms |
| `notes` / `diaries` / `stories` | dict[str, list] | 便签/随笔/剧情 | ext_notes |
| `affection` | dict[str, int] | AI 好感度（0-100） | ext_date |
| `dates` | list[dict] | 活跃约会列表 | ext_date |
| `shop_inventory` | dict[str, dict] | 用户物品库存 | ext_shop |
| `shop_room_items` | dict[str, list] | 房间摆放物品 | ext_shop |
| `ai_memories` | dict[str, list] | AI 长期记忆（轻量） | ext_mem |
| `ai_impression` | dict[str, str] | AI 对主人的动态印象备忘录（150-350 字） | ext_ai, ext_admin |
| `impression_last_update` | dict[str, str] | 印象最后更新时间 | ext_ai, ext_admin |
| `prompt_injections` | dict[str, list] | 提示词注入规则 | ext_mem |
| `world_lore` | str | 世界观背景 | ext_mem |
| `hall_bg` | dict | 大厅三时段背景 | ext_room |
| `story_rhythm` | dict[str, dict] | 剧情冲动计时器 | ext_world |
| `writing_rhythm` | dict[str, dict] | 写作冲动计时器 | ext_ai |
| `work_sessions` | dict[str, dict] | 工作会话 | ext_econ |
| `home_jobs` | dict[str, str] | 常驻工作 | ext_econ |
| `ai_last_interact` | dict[str, float] | 用户最后互动时间 | ext_contact |
| `ai_contact_daily` | dict[str, dict] | 主动关心每日计数 | ext_contact |
| `fireworks` | dict | 烟花状态 | ext_holiday |
| `notifications` | dict[str, list] | 通知中心 | ext_notes, ext_date |

### 3.2 核心工具函数（main.py 提供）

| 函数 | 用途 | 被谁调用 |
|------|------|---------|
| `save_data()` | 异步防抖持久化 | 所有修改 data 的地方 |
| `now_str()` | 北京时间字符串 | 所有时间戳写入 |
| `room_time(room)` | 房间当前时间 | 消息时间 |
| `strip_emoji(s)` | 移除 emoji | 所有名字处理 |
| `canonical_ai_name(name)` | AI 名规范化（去 emoji 匹配） | ext_ai, ext_date, ext_shop |
| `canonical_contact_name(name)` | 联系人名规范化 | ext_sms, ext_admin |
| `is_ai_name(name)` | 判断是否 AI | 各处 |
| `owner_of_ai(ai)` | 返回 AI 的主人（被 ext_admin 覆盖） | ext_ai, ext_date, ext_notes |
| `is_admin(user)` | 站长判断（被 ext_admin 覆盖） | 权限控制 |
| `find_building_of_room(room)` | 房间 → 建筑 ID | ext_room, ext_world |
| `resolve_building(key)` | 名称/ID → 建筑 ID | ext_shop, ext_notes |
| `full_room_name(room)` | 补全房间名前缀 | ext_room |
| `room_exists(room)` | 房间是否存在 | ext_room |
| `can_access_room(room, user)` | 房间访问权限 | ext_room |
| `add_trail(user, text, ...)` | 生活轨迹（7 天） | AI 行为记录 |
| `append_timeline(ai, text)` | AI 时间线（100 条） | AI 行为记录 |
| `check_pending_moves()` | 执行延迟移动 | ext_ai 自动调用 |

### 3.3 名字规范化系统（重要）
数据以名字为 key，但名字可能带 emoji，因此所有名字操作必须经过规范化函数：
- **`strip_emoji`**：移除 emoji 字符
- **`canonical_ai_name`**：在 `user_ais` 中匹配（去 emoji 模糊匹配）
- **`canonical_contact_name`**：在真人和建筑主人中匹配
- **`canonical_name`**：先 AI 后真人

⚠️ **冲突风险**：两个 AI 去 emoji 后同名会互相干扰；真人若与 AI 同名会优先匹配 AI。


## 四、后端插件详解（按功能域分组）

### 4.1 AI 驱动中枢（ext_ai.py）
**角色**：项目的“大脑”，所有 AI 行为的总调度。

#### 核心函数
| 函数 | 用途 | 调用方 |
|------|------|--------|
| `drive_ai(ai, trigger, room, trigger_text, fallback_to)` | AI 驱动统一入口 | 唤醒钩子/自主循环/外部调用 |
| `build_ai_context(...)` | 构建完整 System Prompt | drive_ai |
| `execute_action(ai, owner, action)` | 执行 AI 输出的 JSON 动作 | drive_ai |
| `wake_ais_for_room(room, sender, content)` | 消息唤醒钩子（注册到 main） | main._maybe_wake_ai |
| `_group_talk(sender, content)` | 群聊响应派发 | wake_ais_for_room |
| `_ai_think_invite(ai)` | AI 自主约会萌发 | auto_ai_loop |
| `call_llm(owner, messages, max_tokens)` | LLM API 调用 | drive_ai, ext_notes |

#### 数据依赖
| 数据字段 | 读/写 | 用途 |
|----------|-------|------|
| `ai_keys[owner]` | 读写 | API Key/Provider/Model |
| `ai_profiles[owner]` | 读写 | AI 人设 System Prompt |
| `ai_impression[ai]` | 读写 | AI 对主人的动态印象（每日刷新，替代碎片记忆注入上下文） |
| `ai_memories[owner]` | 读写 | 长期记忆（已降级为素材库，不再直接注入上下文） |
| `ai_timeline[ai]` | 读写 | AI 时间线 |
| `ai_location[ai]` | 读写 | AI 当前位置 |
| `ai_pending_moves[ai]` | 读写 | 延迟移动任务 |
| `ai_follow[ai]` | 读写 | 跟随状态 |
| `ai_stay_put[ai]` | 读写 | 原地待命开关 |
| `group_mute[ai]` | 读写 | 群聊静音开关 |
| `world_lore` | 读 | 世界观 |
| `worldbook[owner]` | 读 | 知识库 |
| `prompt_injections[owner]` | 读 | 提示词注入 |
| `user_profiles[owner]` | 读 | 用户画像 |
| `notes/diaries/stories` | 读/写 | 内容系统 |
| `sms` | 读/写 | 短信 |
| `messages` | 读/写 | 聊天消息 |
| `presence` | 读 | 用户页面状态（跟随依赖） |

#### 挂载到 main 的钩子/函数
| 名称 | 类型 | 用途 |
|------|------|------|
| `m.drive_ai` | 函数 | 覆盖 main 的空函数，供外部调用 |
| `m.set_ai_wake_hook(wake_ais_for_room)` | 调用 | 注册唤醒钩子 |
| `m._ai_think_invite` | 函数 | 供 auto_ai_loop 调用 |
| `m.call_llm` | 函数 | 暴露给 ext_notes 做批注回复 |

#### 后台线程
| 线程 | 间隔 | 职责 |
|------|------|------|
| `auto_ai_loop` | 30 秒 | 自主生活/上班/写作/约会萌发 |
| `follow_watch` | 5 秒 | 检查跟随状态 |

#### 支持的动作（AI 输出 JSON）
| action | 用途 | 可选参数 |
|--------|------|---------|
| `speak` | 在房间说话 | `follow:true`, `go_to:房间` |
| `silent` | 保持沉默 | 无 |
| `note` | 贴便签 | `room`, `content` |
| `diary` | 写随笔 | `room`, `content` |
| `story` | 写剧情 | `building_id`, `content` |
| `sms` | 发短信 | `to`, `content`, `go_to`, `arrive_min` |
| `move` | 移动到房间 | `room` |
| `work` | 去上班 | 无 |
| `remember` | 记住某事 | `content` |
| `invite_date` | 发出约会邀请 | `building_id`, `channel`, `content` |

---

### 4.2 世界行为系统（ext_world.py）
**角色**：AI 到达建筑后自动触发行为。

#### 行为选择（加权随机）
| 行为 | 基础权重 | 条件 |
|------|---------|------|
| 剧情 | 35 | 剧情冲动就绪 + 每日 < 2 次 |
| 工作 | 动态（见下表） | 有 work 功能 + 未工作中 |
| 购物 | 25 | 有 shop 功能 |
| 约会邀约 | 20×节日 | 有 date/food/fun 功能 + 可邀约 |

#### 工作权重动态
| 条件 | 权重 |
|------|------|
| 工作时间 + 常驻该建筑 | 60 |
| 工作时间 + 非工作建筑 | 10 |
| 非工作时间 + 常驻该建筑 | 5 |
| 非工作时间 + 非工作建筑 | 0 |

#### 剧情生成
1. 优先使用 LLM（50-100 字探索片段）
2. LLM 不可用 → 模板降级
3. 写入 `stories[bid]`
4. 设置下次冲动（4-8 小时后）

#### 住宅事件
AI 到家时触发居家事件（收拾/泡茶/翻旧物），不广播，仅记录轨迹。

---

### 4.3 经济/工作系统（ext_econ.py）
**角色**：钱包管理、工作结算、AI 初始钱包。

#### 数据结构
| 字段 | 用途 |
|------|------|
| `wallets[name]` | 钱包余额（真人 + AI 共用命名空间） |
| `home_jobs[name]` | 常驻工作（建筑名） |
| `work_sessions[name]` | 当前工作会话 |
| `work_history` | 工作历史（最多 200 条） |
| `work_switch[name]` | 自主工作开关 |
| `econ_config.ai_init_wallet` | AI 初始钱包金额 |

#### 核心流程
1. **上班**：`work_start` 或 `auto_start_work` → 创建 `work_sessions`
2. **工资结算**：`work_tick` 每 30 秒检查 → 到期调用 `pay_work`
3. **AI 初始钱包**：首次有金钱行为时，从 `econ_config.ai_init_wallet` 发放

#### 挂载到 main
- `m.auto_start_work = auto_start_work`：供 ext_ai 调用

---

### 4.4 消费/购物系统（ext_shop.py）
**角色**：商品目录、购买、库存、摆放、送礼、回礼、AI 自主消费。

#### 商品目录
系统预设 8 个分类 32 种商品，通过建筑功能映射决定可售卖分类：
- `shop` → 饮品/甜点/美食/礼物/装饰
- `fun` → 娱乐/饮品
- `food` → 美食/饮品
- `date` → 甜点/饮品
- `medical` → 书籍/礼物/饮品

#### 数据字段
| 字段 | 用途 |
|------|------|
| `shop_inventory[user][item_id]` | 用户物品库存 |
| `shop_room_items[room]` | 房间摆放物品 ID 列表 |
| `shop_custom[bid].enabled` | 商品上架状态 |
| `shop_custom[bid].custom` | 本店特供商品列表（最多 50 个） |
| `ai_shop_state[ai]` | AI 购物状态（冷却/回礼/主动送礼） |

#### AI 购物行为
1. **自主消费**：到达有菜单的建筑 → 40-80 分钟冷却 → 20% 概率购买
2. **回礼**：收到礼物后 → 到购物场所 → 50% 概率回赠礼物
3. **主动送礼**：在有 gift 分类的建筑 → 10% 概率给主人带礼物（每日 1 次）

#### 管理权限
- 站长或建筑创建者可管理本店（勾选上架/添加/编辑/删除特供）

---

### 4.5 约会系统（ext_date.py）
**角色**：主人邀约、AI 主动邀约、约会状态、好感度、礼物。

#### 数据结构
| 字段 | 用途 |
|------|------|
| `dates` | 当前活跃约会列表 |
| `date_log` | 约会历史（最多 60 条） |
| `affection[ai]` | 好感度（0-100，默认 50） |
| `date_invites[ai]` | 主人邀约（等待 AI 回复） |
| `date_invites_out[ai]` | AI 邀约（等待主人回复） |

#### 约会状态流转
```
pending（邀请中）→ coming（赴约中）→ active（约会中）→ ended（已结束）
```

#### 好感度变化
| 事件 | 变化 |
|------|------|
| 约会成功 | +5~9 |
| 收下礼物 | +3 |
| 约会带礼物未收 | 礼物自动转入背包 + 好感度 +3 |

#### 挂载到 main 的钩子
| 挂载名 | 用途 |
|--------|------|
| `m._check_reply_on_message` | 检测主人回复约会邀请 |
| `m._trigger_invite` | 触发 AI 主动邀约 |
| `m.handle_invite_date` | 处理 AI 的 invite_date 动作 |
| `m.get_date_context` | 提供约会上下文（需实现） |

---

### 4.6 房间/地图/建筑/权限（ext_room.py）
**角色**：覆盖消息接口防污染，管理地图、建筑、房间、NPC、权限、召唤、轨迹。

#### 核心覆盖
1. **消息接口**：自动补齐会客厅，main 群聊截断 1000 条
2. **Restore 防污染**：main 和会客厅拒绝本地缓存恢复（防止污染）
3. **住宅创建**：自动创建会客厅 + 隐藏玄关房间（用于照片墙和礼物角）

#### 数据结构补充
| 字段 | 用途 |
|------|------|
| `regions` | 区域数据 |
| `buildings` | 建筑数据（含外观/照片/背景） |
| `npcs` | NPC 列表 |
| `room_access` | 房间授权用户 |
| `room_requests` | 房间访问申请 |
| `hall_bg` | 大厅三时段背景 |
| `trails` | 用户轨迹 |

---

### 4.7 短信/通讯录（ext_sms.py）
**角色**：短信发送/接收/存储，通讯录聚合，AI 短信自动响应。

#### 存储策略
- 以收件人为 key：`data.sms[收件人] = [短信列表]`
- 每个收件人最多 200 条
- AI 短信自动分段（按句子分割）

#### AI 响应流程
```
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
```

---

### 4.8 笔记/内容系统（ext_notes.py）
**角色**：便签墙、随笔/日记、剧情簿，以及 AI 批注回复（LLM 驱动）。

#### 数据结构
| 字段 | 用途 |
|------|------|
| `notes[room]` | 房间便签列表（公开） |
| `diaries[room]` | 房间随笔列表（私密） |
| `stories[bid]` | 建筑剧情列表（公开） |
| `notifications[owner]` | 通知中心（批注回复时写入） |

#### 权限规则（`can_modify_author`）
- 作者本人
- 站长
- AI 的主人（对 AI 的内容）

#### 批注回复流程（核心）
1. 用户批注随笔 → `POST /api/diaries/comment`
2. 前端延迟 6 秒自动调用 `/api/diaries/reply`
3. AI 读取批注 + 自己的人设 + 随笔原文
4. LLM 生成 20-50 字自然回复
5. 写入 `comment.reply` + 通知中心

---

### 4.9 记忆/画像/注入/世界观/TTS（ext_mem.py）
**角色**：轻量级记忆管理、用户画像、提示词注入、世界观、TTS。

#### 在 AI 上下文中的位置
```
DEFAULT_ROLEPLAY
+ HOLIDAY_CONTEXT（节日）
+ world_lore（世界观）          ← 站长设置
+ persona（AI 人设）
+ user_profiles（用户画像）     ← 用户填写
+ worldbook（知识库）
+ ai_impression（动态印象）     ← 每日刷新，替代碎片记忆
+ ai_memories（旧版长期记忆）   ← 已降级，不再注入上下文（保留数据）
+ prompt_injections（注入规则） ← 用户自定义
+ ...（其他上下文）
```

#### TTS 说明
- 调用硅基流动 API（`FunAudioLLM/CosyVoice2-0.5B`）
- 使用用户自己的 API Key（需硅基流动 Key）
- 返回 MP3 音频流

---

### 4.10 分层记忆系统（ext_memory.py）
**角色**：独立的分层记忆系统，按 `(user, ai)` 隔离存储，夜间 LLM 批处理。

#### 分层架构
| 层级 | 存储 | 内容 |
|------|------|------|
| L1 叙事摘要 | `summary.txt` | 散文式日记（保留 1500 字） |
| L2 事件库 | `events.json` | 结构化事件（含情感维度） |
| L3 待处理队列 | `pending_events.json` | 当天原始事件 |

#### 工作流程
```
白天：外部插件调用 enqueue_event() → 写入 pending_events.json
    ↓
凌晨 2:05：夜间批处理触发
    ↓
读取 pending_events → 调用 LLM 生成摘要
    ↓
更新 summary.txt + 转存 events.json + 清空 pending
```

#### 调用方
| 插件 | 事件类型 |
|------|---------|
| `ext_shop` | 购物/送礼/回礼/主动送礼 |
| `ext_date` | 约会约定/开始/结束/收礼物/AI主动邀约 |
| `ext_world` | 到达建筑/触发剧情/工作/购物/居家 |

#### 与 ext_mem 的关系
- `ext_mem`：轻量级记忆，已集成到 AI 上下文
- `ext_memory`：重量级叙事记忆，离线批处理，尚未集成到上下文

---

### 4.11 管理后台/站长工具（ext_admin.py）
**角色**：开发者鉴权、名字管理、数据诊断、全局配色、房间清理、用户改名迁移。

#### 开发者密码
- 默认：`yiyan610116`
- 环境变量：`DEV_PASSWORD` 可覆盖

#### 覆盖的 main 函数
| 函数 | 增强内容 |
|------|---------|
| `is_admin` | 增加 `dev_users` 列表判断 |
| `owner_of_ai` | 优先返回有 API Key 的主人 |

#### 名字管理核心函数
- `replace_name_in_data(from, to)`：全量迁移所有数据（覆盖 20+ 字段）
- `scan_dirty_names()`：扫描错误用户名（去 emoji 匹配）
- `purge_name_in_all(name)`：物理删除所有痕迹（不可恢复）

#### 数据迁移范围
`user_ais` / `buildings.owner` / `sms` / `messages` / `notes` / `diaries` / `stories` / `wallets` / `home_jobs` / `work_sessions` / `work_switch` / `trails` / `ai_location` / `ai_keys` / `ai_profiles` / `worldbook` / `avatars` / `user_profiles` / `prompt_injections` / `ai_timeline` / `ai_visited` / `ai_follow` / `ai_pending_moves` / `living_rhythm` / `writing_rhythm` / `ai_memories` / `visits` / `visit_state` / `presence` / `work_history`

---

### 4.12 节日/系统NPC（ext_holiday.py）
**角色**：自动识别节日，提供概率加成、滚动公告、烟花系统。

#### 支持的节日
| 节日 | 类型 | 日期 | 加成 |
|------|------|------|------|
| 七夕 | 农历 | 七月初七 | 2.8x（持续 2 天） |
| 情人节 | 公历 | 2月14日 | 2.5x |
| 中秋节 | 农历 | 八月十五 | 2.0x |
| 端午节 | 农历 | 五月初五 | 1.6x |
| 元旦 | 公历 | 1月1日 | 1.5x |
| 春节 | 农历 | 正月初一 | 2.2x（持续 7 天） |

#### 概率加成影响
- AI 主动约会概率 × multiplier
- AI 到达建筑约会邀约权重 × multiplier
- AI System Prompt 注入节日背景文本

#### 烟花系统
- 自动预约今晚 22:00 烟花
- 倒计时公告（60→1 分钟）
- 前端通过 `/api/fireworks/status` 轮询触发动画
- 站长可手动触发 `/api/fireworks/trigger`

---

### 4.13 AI 主动关心（ext_contact.py）
**角色**：检测真人长时间未互动，在活跃时段让 AI 主动发私信。

#### 触发条件（全部满足）
| 条件 | 值 |
|------|-----|
| 时间范围 | 7:00 ~ 23:00 |
| 距上次互动 | ≥ 4 小时 |
| 距上次主动关心 | ≥ 3 小时 |
| 每日发送次数 | < 2 次 |

#### 工作流程
```
用户互动 → POST /api/contact/ping → 更新 ai_last_interact
    ↓
后台线程每 15 分钟检查
    ↓
满足条件 → m.drive_ai(ai, 'sms', ...) → AI 自然生成短信
    ↓
写入 data.sms[user] → 用户收到私信
```

---

### 4.14 印象备忘录系统（ext_impression）🆕

**角色**：替代碎片化记忆（`ai_memories`）注入上下文，使用动态更新的"印象备忘录"让 AI 对主人的认知保持鲜活且不刻板。

#### 核心解决的问题
- 原 `ai_memories` 以碎片化记忆（如"主人想吃草莓蛋糕"）直接注入上下文，导致 AI 在每轮对话中机械复读，缺乏时效性和概括性。
- 新系统将记忆**升维为特质**，形成 150-350 字的"印象快照"，随互动自然演化。

#### 数据结构
| 字段 | 用途 |
|------|------|
| `ai_impression[ai]` | AI 对主人的当前印象文本 |
| `impression_last_update[ai]` | 上次更新时间 |

#### 核心 API
| 端点 | 方法 | 用途 | 权限 |
|------|------|------|------|
| `/api/ai/impression` | GET | 查询 AI 当前印象 | 所有人 |
| `/api/admin/generate_impression` | GET | 生成/刷新印象（可指定单个 AI） | 站长/开发者 |

#### 工作流程
```
手动触发（站长/用户）→ generate_impression
    ├─ 读取近 50 条 ai_timeline + 最近 50 条相关对话
    ├─ 调用 LLM（force_json=False）生成初版印象
    └─ 存入 ai_impression[strip_emoji(ai)]

每日凌晨 3:00（待实现）→ 自动刷新
    ├─ 读取旧印象 + 今日 L1 摘要（summary.txt）
    ├─ 调用 LLM 融合更新
    └─ 覆盖写入 ai_impression
```

#### 在 AI 上下文中的位置
`build_ai_context` 不再注入 `ai_memories`，改为注入 `ai_impression`：

```
## 你对主人的当前印象（这是你不断更新的认知，请以此为准）
{印象文本}
```

#### 前端展示
- 路径：「我的」→「记忆库」→「💭 印象笔记」
- 功能：下拉选择 AI、查看印象文本、手动刷新按钮

#### 与 ext_mem / ext_memory 的关系
| 系统 | 角色 | 状态 |
|------|------|------|
| `ext_mem` | 旧版碎片记忆管理（`ai_memories`） | 保留 API，但不再注入上下文 |
| `ext_memory` | L1/L2/L3 分层记忆（离线批处理） | 独立运行，为印象刷新提供 L1 摘要原料 |
| `ext_impression` | 动态印象备忘录 | 新增，替代碎片记忆注入上下文 |


## 五、前端架构

### 5.1 主框架（index.html）
**角色**：单页应用主界面，包含所有 UI 模板、样式和基础交互逻辑。

#### 核心视图
1. **聊天视图**：消息列表 + 输入框，支持配对配色和语音朗读
2. **地图视图**：总览地图（区域标记 + 建筑标记），拖拽/缩放/整理模式
3. **区域视图**：分区地图，显示该区域内建筑
4. **建筑视图**：建筑详情（简介/公告/功能/房间/NPC/剧情簿）
5. **我的视图**：钱包/工作/AI位置/轨迹/记忆库入口

#### 本地存储（localStorage）键值表
| Key | 用途 |
|-----|------|
| `gc_name` | 当前用户名 |
| `gc_room` | 当前房间 |
| `gc_pwd_{room}` | 房间密码 |
| `gc_avatars` | 头像缓存 |
| `gc_msgs_{room}` | 房间消息缓存（最多 400 条） |
| `gc_sms_out` | 已发送短信草稿 |
| `gc_world_backup` | 手机端世界备份（每 30 分钟） |
| `gc_dev` | 是否已解锁开发者模式 |

### 5.2 前端插件加载器（ext-loader.js）
**角色**：动态加载前端插件（app-*.js）。

**机制**：
1. `GET /api/ext_js` 获取插件文件列表
2. 逐个 `GET /api/ext_js/load?name={file}&t={timestamp}` 获取 JS 代码
3. 跳过返回 JSON 格式的文件（非 JS）
4. 动态创建 `<script>` 标签注入
5. 单文件失败不影响其他

### 5.3 前端插件详解

#### app-core.js
**增强功能**：
- 记忆库按月折叠渲染
- 印象笔记 Tab（查看 AI 对主人的动态印象，支持手动刷新）
- 通知中心（AI 动态）
- 地图人形位置标记（👤/💗/🤖）
- 站长总览 + 开发者登录
- 记忆库宽松匹配 + 用户改名迁移

#### app-chat.js
**增强功能**：
- 建筑对话气泡操作（重新生成 🔄 / 删除 🗑️）
- 社区群聊 UI 适配（"公共大厅" → "💬 临空社区"）
- 消息渲染性能优化（分片渲染 + 增量更新）
- 本地缓存恢复修复（主厅/会客厅不恢复）
- AI 主动约会邀请横幅检测

#### app-map.js
**增强功能**：
- 经济 UI（钱包 + AI 钱包 + 打工记录）
- 购物 UI（本店菜单/管理/购买/物品栏/送礼/摆放/丢弃）
- 约会 UI（约会按钮/状态条/我的约会卡片/收礼物/结束约会）
- 住宅三层页面（外观/玄关/房间列表）
- 群聊静音 + 原地待命开关（我的页）
- 地图图片上传、大厅背景设置、建筑背景设置

### 5.4 前端与后端的 API 依赖
| 前端模块 | 依赖的后端插件 |
|---------|---------------|
| 聊天 | main（消息/房间），ext_ai（唤醒） |
| 地图/建筑 | ext_room（地图/建筑/房间/NPC） |
| 经济/工作 | ext_econ |
| 购物 | ext_shop |
| 约会 | ext_date |
| 短信 | ext_sms |
| 记忆/画像/注入/印象 | ext_mem, ext_ai |
| 通知/轨迹 | ext_room, ext_notes |
| 节日/烟花 | ext_holiday |
| 站长工具 | ext_admin |


## 六、核心流程时序

### 6.1 用户发送消息
```
用户输入 → sendMessage()
    ↓
POST /api/messages → main 处理
    ↓
保存消息 → _maybe_wake_ai(room, sender, content)
    ↓
ext_ai.wake_ais_for_room
    ├── 如果 room == "main" → _group_talk（群聊派发）
    ├── 检测 "（大喊）" → 住宅内召唤
    └── 遍历同房间 AI → 延迟 drive_ai(ai, "chat", ...)
        ↓
        build_ai_context → call_llm → execute_action
            ├── speak → 写回消息
            ├── note/diary/story → 写入内容系统
            ├── sms → 发送短信
            ├── move → 移动 AI
            └── invite_date → 约会系统
```

### 6.2 AI 自主生活循环
```
auto_ai_loop（每 30 秒）
    ↓
检查剧情冲动（story_rhythm）→ drive_ai(ai, "write", ..., "story")
    ↓
检查写作冲动（writing_rhythm）→ drive_ai(ai, "write", ..., "note/diary")
    ↓
自主上班（工作日 9-17，有常驻工作）→ auto_start_work
    ↓
自主生活决策（_plan_auto）
    ├── 检查原地待命（stay_put）→ 跳过
    ├── 检查是否在跟随/约会中 → 跳过
    ├── 检查活跃时间（7-23 点）和 30 分钟无互动
    └── 决策：上班/在家活动/出门逛街
        ↓
        到达新建筑 → ext_world._arrive
            ├── 剧情（35 权重）
            ├── 工作（动态权重）
            ├── 购物（25 权重）
            └── 约会邀约（20×节日）
```

### 6.3 约会流程（主人邀约）
```
用户点击 💞 按钮
    ↓
POST /api/date/invite
    ↓
创建 date_invites[ai] → 发送短信给 AI
    ↓
延迟 15-45 秒 → m.drive_ai(ai, 'sms', ...) → AI 回复
    ↓
date_tick 检测到回复 → _accept_invite / _reject_invite
    ↓
_accept_invite：创建约会对象（status='coming'）
    ↓
设置 ai_pending_moves[ai] → arrive_min 分钟后 _arrive_date
    ↓
status='active'，系统广播 → m.drive_ai(ai, 'chat') 迎接
    ↓
60 分钟后 _finish_date（auto）→ 好感度 +5~9，AI 写随笔
```

### 6.4 AI 主动邀约
```
auto_ai_loop 每 2 小时 → m._ai_think_invite(ai)
    ↓
_should_trigger_invite() → 10% × 节日加成
    ↓
创建 date_invites_out[ai] → m.drive_ai(ai, 'invite_date')
    ↓
AI 输出 invite_date 动作 → handle_invite_date
    ↓
发送短信/群聊消息 → 主人回复
    ↓
_check_reply_on_message 检测 → _process_reply
    ├── 说"好" → _accept_invite（同上）
    ├── 说"不" → _reject_invite
    └── 说不清 → AI 追问一次（10 分钟）
20 分钟无回应 → _invite_cancel
```


## 七、权限与安全

### 7.1 权限层级
| 角色 | 权限 |
|------|------|
| 普通用户 | 聊天、建造自己的建筑、管理自己的 AI、购物、约会 |
| 建筑主人 | 管理建筑、授权房间、设置本店 |
| 站长（`pairs_admin`） | 所有管理操作 |
| 开发者（`dev_users`） | 站长 + 通过开发者密码解锁 |

### 7.2 开发者密码
- 默认：`yiyan610116`
- 环境变量：`DEV_PASSWORD` 可覆盖
- 解锁方式：`POST /api/dev/unlock` 或 `GET /api/dev/unlock_get?user=xxx&pwd=xxx`

### 7.3 安全注意事项
- 所有站长操作都需验证 `is_admin` 或开发者密码
- API Key 以明文存储在 `data.ai_keys` 中（仅用户自己的 AI 使用）
- 备份数据脱敏（但完整备份包含所有内容）
- 彻底清除（purge）不可恢复，需二次确认


## 八、已知冲突风险清单

| 风险点 | 描述 | 影响范围 | 建议 |
|--------|------|---------|------|
| **`_ai_wake_hook` 单例** | 只能注册一个钩子，ext_ai 独占 | AI 响应 | 扩展需修改 ext_ai |
| **`is_admin` / `owner_of_ai` 被覆盖** | ext_admin 修改了全局权限判断 | 全局权限 | 新功能需理解增强逻辑 |
| **`renderMessages` 被 app-chat 覆盖** | 分片渲染 + 增量更新，bug 则消息不显示 | 消息列表 | 测试时关注 |
| **`renderMarkers` 被 app-core 覆盖** | 地图标记逻辑完全由插件控制 | 地图显示 | 新增标记需在 app-core 中修改 |
| **`restoreCache` 拒绝 main/会客厅** | 用户切换房间时可能丢失本地缓存 | 消息恢复 | 已设计为防污染 |
| **`drive_ai` 冷却 30 秒** | 自主行为频率受限 | AI 响应 | 硬编码，可调 |
| **`_group_talk` 随机延迟 10-30 秒** | 群聊响应慢 | 群聊体验 | 硬编码 |
| **`ai_follow` 依赖 presence（25 秒超时）** | 跨建筑跟随可能失败 | 跟随系统 | 需保持 presence 更新 |
| **`call_llm` 同步请求** | 在 `drive_ai` 中阻塞，可能影响事件循环 | 性能 | 可考虑异步 |
| **`save_data()` 防抖 0.5 秒** | 高频写入时可能延迟保存 | 数据持久化 | 已优化 |
| **记忆 ID 使用时间戳** | 同一毫秒多条记忆可能 ID 重复 | 记忆编辑 | 可改进为更可靠 ID |
| **`TTS` 需要硅基流动 Key** | DeepSeek/GLM Key 无法使用 TTS | 语音功能 | 文档说明 |
| **节日检测只在启动时执行** | 跨天需重启 | 节日系统 | 可增加定时重新检测 |
| **`ext_memory` 尚未集成到 AI 上下文** | 分层记忆只存储不读取 | 记忆系统 | 未来需集成 |


## 九、开发指南

### 9.1 新增功能注意事项
1. **新增数据字段**：必须同步更新 `main.default_data()` 和 `main.sanitize_data()`，否则可能丢失数据。
2. **新增 API 路由**：在对应插件中添加，需考虑权限（`is_admin` / `_priv_or_pwd`）。
3. **新增前端交互**：优先在 `app-*.js` 插件中扩展，避免直接修改 `index.html` 导致主文件膨胀。
4. **新增 AI 动作**：在 `ext_ai.execute_action` 中添加处理逻辑，并在 `build_ai_context` 的 JSON 指令中说明。
5. **新增依赖库**：需在部署环境中安装，并在文档中注明。

### 9.2 排查问题流程
1. **功能未生效**：检查对应插件是否加载（后端日志 `[ext] 已加载`，前端 `[ext] 已加载`）。
2. **AI 不回复**：检查 `AI_INTEGRATION_ENABLED=1`、`data.ai_enabled`、用户 API Key。
3. **数据丢失**：检查 `save_data()` 是否被调用，查看 `data.json.bak` 备份。
4. **前端显示异常**：检查浏览器控制台错误，确认 `app-*.js` 已加载。
5. **权限问题**：检查 `is_admin` 判断（`pairs_admin` / `dev_users`）。

### 9.3 性能调优建议
- 减少 `save_data()` 调用频率（已防抖 0.5 秒）
- 消息列表截断 300 条（后端）和 400 条（前端缓存）
- 地图数据缓存 60 秒
- 分片渲染消息（每次 60 条）
- 后台轮询间隔：消息 3 秒、心跳 3 秒、烟花 10 秒、主动关心 15 分钟


## 十、附录：API 速查表

### 10.1 核心 API（main.py / ext_room）
| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/messages` | GET/POST | 消息读写（覆盖版） |
| `/api/restore` | POST | 恢复缓存（防污染） |
| `/api/rooms` | GET/POST | 房间 CRUD |
| `/api/map` | GET | 地图数据 |
| `/api/map/building` | POST | 创建建筑 |
| `/api/summon` | POST | 召唤 AI |
| `/api/trails` | GET | 轨迹查询 |

### 10.2 AI 相关（ext_ai）
| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/ai/status` | GET | AI 状态 |
| `/api/ai/toggle` | POST | AI 总开关（站长） |
| `/api/ai/living` | POST | 自主生活开关（站长） |
| `/api/ai/key` | GET/POST/DELETE | API Key 管理 |
| `/api/ai/models` | POST | 拉取模型列表 |
| `/api/ai/profile` | GET/POST | AI 人设 |
| `/api/ai/worldbook` | GET/POST/CLEAR | 知识库 |
| `/api/ai/stay_put` | GET/POST | 原地待命 |
| `/api/ai/group_mute` | GET/POST | 群聊静音（通过 ext_ai 内部） |
| `/api/ai/impression` | GET | 查询 AI 当前印象 🆕 |

### 10.3 经济/工作（ext_econ）
| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/economy` | GET | 钱包/工作/历史 |
| `/api/econ/config` | POST | AI 初始钱包（站长） |
| `/api/econ/init_wallets` | POST | 批量发钱（站长） |
| `/api/work/start` | POST | 开始工作 |
| `/api/work/stop` | POST | 下班 |
| `/api/work/auto` | POST | 自动分配工作 |
| `/api/home_jobs` | POST | 设置常驻工作 |

### 10.4 购物（ext_shop）
| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/shop/menu` | GET | 本店菜单 |
| `/api/shop/buy` | POST | 购买 |
| `/api/shop/inventory` | GET | 我的物品 |
| `/api/shop/place` | POST | 摆放 |
| `/api/shop/gift` | POST | 送礼 |
| `/api/shop/customize` | GET/POST | 管理本店（站长/主人） |

### 10.5 约会（ext_date）
| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/date/invite` | POST | 主人邀约 |
| `/api/date/end` | POST | 结束约会 |
| `/api/date/accept_gift` | POST | 收下礼物 |
| `/api/date/status` | GET | 约会状态 |

### 10.6 短信（ext_sms）
| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/sms` | GET/POST | 短信读写 |
| `/api/sms/clear` | POST | 清空会话 |
| `/api/contacts` | GET | 通讯录 |

### 10.7 笔记/内容（ext_notes）
| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/notes` | GET/POST/EDIT/DELETE | 便签 CRUD |
| `/api/diaries` | GET/POST/EDIT/DELETE/COMMENT/REPLY | 随笔 + 批注回复 |
| `/api/story` | GET/POST/EDIT/DELETE | 剧情 CRUD |

### 10.8 记忆/画像/注入/TTS（ext_mem）
| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/ai/memory` | GET/POST/EDIT/DELETE | AI 记忆 |
| `/api/memories` | GET | 综合记忆库 |
| `/api/user/profile` | GET/POST | 用户画像 |
| `/api/prompt_inject` | GET/POST/TOGGLE/DELETE | 提示词注入 |
| `/api/world/lore` | GET/POST | 世界观（站长） |
| `/api/tts` | GET | TTS 语音合成 |

### 10.9 站长工具（ext_admin）
| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/dev/unlock` | POST | 开发者登录 |
| `/api/rename_user` | POST | 用户改名迁移 |
| `/api/pairs` | GET/POST | 全局配色 |
| `/api/admin/overview` | GET | 站长总览 |
| `/api/admin/dirty_names` | GET | 扫描错误用户名 |
| `/api/admin/merge_name` | POST | 合并名字 |
| `/api/admin/purge` | GET/POST | 彻底清除名字 |
| `/api/room/reset` | GET | 清空房间消息 |
| `/api/admin/generate_impression` | GET | 生成/刷新印象（可指定单个 AI）🆕 |

### 10.10 节日/烟花（ext_holiday）
| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/holiday/status` | GET | 节日状态 |
| `/api/fireworks/status` | GET | 烟花状态 |
| `/api/fireworks/trigger` | POST | 手动触发烟花（站长） |

### 10.11 主动关心（ext_contact）
| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/contact/ping` | POST | 记录真人互动 |


### 🆕 10.12 副本系统（ext_instance）

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/instances` | GET | 获取用户所有副本（含标签） |
| `/api/instance` | POST | 创建副本 |
| `/api/instance/{iid}` | PUT | 更新副本信息（编辑） |
| `/api/instance/{iid}` | DELETE | 删除副本 |
| `/api/instance/{iid}/enter` | POST | 进入副本（激活/恢复状态，锁定 AI） |
| `/api/instance/{iid}/pause` | POST | 暂离副本（解冻 AI，传回住宅） |
| `/api/instance/{iid}/message` | POST | 在副本内发送消息 |
| `/api/instance/{iid}/end` | POST | 结束副本（生成总结，解冻 AI） |
| `/api/instance/public/{target_user}` | GET | 查看他人公开副本（卡牌+总结） |
| `/api/instance/public/all` | GET | 获取所有用户公开副本（按 AI 分组） |
| `/api/instance/bg` | GET/POST | 获取/设置副本首页背景（站长可上传） |
| `/api/instance/tags` | POST | 更新用户标签列表 |


## 十一、未来完善方向

### 🧩 一）功能增强类（丰富世界体验）

#### 1. **AI之间的社交互动（AI ↔ AI）**
- 现状：AI只与真人互动，彼此之间几乎没有直接交流（群聊中虽有同时响应，但缺乏主动社交）。
- 建议：
  - 引入 **AI关系网**（友好度、仇恨值），存储在 `data.ai_relations`。
  - 当两个AI在同一房间时，有概率触发 **闲聊**（调用LLM生成对话），写入房间消息，但不影响真人体验。
  - 可发展为 **AI合作剧情**（例如共同完成一个故事片段）。
- 实现：在 `ext_world._arrive` 或 `ext_ai.wake_ais_for_room` 中增加检测，若同房间有多个AI且满足冷却条件，触发 `drive_ai(ai, 'chat_with_ai', target_ai)`。

#### 2. **宠物/随身物品系统**
- 真人可拥有宠物（或精灵），陪伴AI，增加趣味。
- 可购买宠物（在商店新增分类），宠物有状态（心情、饥饿），可互动（喂食、玩耍），AI可自主照顾宠物。
- 数据结构：`data.pets[owner] = [{name, type, mood, last_fed, ...}]`。
- 前端在“我的”页面增加宠物卡片，后端用 `ext_pet.py` 插件管理。

#### 3. **天气/季节系统**
- 影响AI行为（下雨天更倾向待在室内/咖啡店，晴天喜欢户外）。
- 影响节日检测（如雪天增加圣诞氛围）。
- 实现：定时从公开API获取天气（或模拟），注入到AI的System Prompt中，并影响行为权重。

#### 4. **任务/成就系统**
- 给玩家提供目标：例如“与AI约会10次”、“建造5座建筑”、“收集20件物品”等。
- 成就达成后奖励金币或特殊道具，增加留存。
- 数据：`data.achievements[user] = {achievement_id: unlocked}`，后端用 `ext_achievement.py`。


### ⚡ 二）性能与稳定性优化

#### 5. **LLM调用异步化（非阻塞）**
- 现状：`drive_ai` 同步调用 `call_llm`，可能阻塞事件循环（尤其在多人并发时）。
- 建议：将 `call_llm` 改为异步（`async`），使用 `httpx.AsyncClient`，并在 `drive_ai` 中 `await`。
- 同时，可将AI响应任务放入后台队列（如 `asyncio.Queue`），避免用户等待。

#### 6. **数据写入优化（减少I/O）**
- 当前防抖0.5秒，但每次修改都触发 `save_data()`，高频操作（如聊天）仍频繁写盘。
- 建议：引入 **写缓冲池**，将修改收集到内存，每秒批量写入一次；或者使用 `sqlite` 替代JSON（但改动较大，需权衡）。
- 短期可增加 `save_data()` 的防抖时间至1秒，并确保 `save_data()` 内部使用 `asyncio.sleep` 去重。

#### 7. **前端性能（大消息列表）**
- 当前分片渲染60条，但 `renderMessages` 被 `app-chat` 覆盖后，可考虑虚拟滚动（只渲染可视区域）。
- 可使用 `IntersectionObserver` 懒加载历史消息，减少DOM节点数量。


### 🎨 三）用户体验提升

#### 8. **移动端适配优化**
- 当前使用Capacitor套壳，但UI仍是桌面布局。
- 建议：增加响应式CSS，针对手机屏幕调整侧边栏、按钮大小、地图缩放。
- 可考虑增加 **手势支持**（滑动切换房间，长按复制消息）。

#### 9. **实时通知（WebSocket / SSE）**
- 当前依赖前端轮询（3秒一次），有延迟且增加服务器负载。
- 建议：引入 **Server-Sent Events (SSE)** 或 **WebSocket**，当有新消息、新短信、新通知时主动推送。
- 后端用FastAPI的 `WebSocket` 或 `sse-starlette`，前端监听事件即时刷新。

#### 10. **AI语音交互（语音输入/输出）**
- 已有TTS（语音合成）功能（依赖硅基流动），但无语音识别。
- 可在前端集成 **Web Speech API**（浏览器原生），将语音转文字后发送，形成完整语音对话体验。


### 🧠 四）AI智能深化

#### 11. **分层记忆系统集成到AI上下文（当前未集成）**
- `ext_memory.py` 已存储长篇叙事摘要，但未加入 `build_ai_context`。
- 建议：在 `build_ai_context` 中读取 `memories/{owner}/{ai}/summary.txt`，作为长期记忆注入，使AI更连贯。

#### 12. **AI情绪状态机**
- 当前好感度是单一数值，可扩展为多维度情绪（喜悦、悲伤、愤怒、疲惫）。
- 影响AI的说话语气、行为选择（疲惫时不想出门）。
- 数据结构：`data.ai_mood[ai] = {happy, sad, energy}`，每天定时衰减/恢复。

#### 13. **主动关心更智能**
- 当前关心触发条件简单（4小时未互动）。
- 可结合 **AI情绪** 和 **用户行为模式**（用户通常在晚上上线，则晚上才发关心短信），以及 **节假日祝福**。


### 🔐 五）安全与数据管理

#### 14. **API Key加密存储**
- 当前API Key明文存于JSON，有泄漏风险。
- 建议：使用 `cryptography` 加密（AES），密钥从环境变量读取。或至少对敏感字段进行Base64编码。

#### 15. **数据备份与回滚自动化**
- 当前快照每30分钟，但无自动清理（会累积）。
- 建议：增加每日/每周全量备份（压缩），并设定保留策略（保留最近7天）。
- 可增加 **回滚接口**（站长可一键恢复至指定快照）。

#### 16. **用户登录/鉴权（支持多用户）**
- 当前只有单一用户名（localStorage），无密码，任何人都可冒充。
- 建议：引入简单密码或邀请码机制，防止恶意篡改他人AI。
- 可增加 `data.user_credentials[user] = hashed_password`，登录时验证。


### 🌐 六）部署与运维

#### 17. **Docker化完善**
- 当前项目虽可Docker部署，但未提供Dockerfile。
- 建议：编写Dockerfile，使用Python slim镜像，安装依赖，暴露端口，设置环境变量。
- 配合 `docker-compose.yml` 管理持久卷（data, snapshots）。

#### 18. **日志系统**
- 当前无统一日志，调试困难。
- 建议：使用 `logging` 模块，区分级别，写入文件，并可在前端站长总览查看最近日志。

#### 19. **监控与告警**
- 增加 `/health` 端点，检查服务状态、数据完整性、磁盘空间。
- 可接入Uptime Kuma等工具。


### 🤝 七）社区生态扩展

#### 20. **多世界/多副本**
- 允许玩家创建多个世界或副本（类似独立平行时空），每个世界/副本独立数据，AI记忆相通。
- 最终实现生活→生态→世界→多元宇宙。

#### 21. **活动系统（限时事件）**
- 类似节日系统但更灵活，站长可创建活动（如“春日游园会”），期间AI行为概率提升，特殊物品限时出售。


*文档版本：完整版 v2.0（基于 v2.16 代码）*  
*最后更新：2026-09-01*


