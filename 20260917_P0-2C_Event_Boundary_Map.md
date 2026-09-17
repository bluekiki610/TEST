# Linkong V3.0 — P0-2C Event Boundary Map

> 版本：2026-09-17（v2 修正版）
> 校对依据：ext_ai.py / ext_world.py / ext_date.py / ext_econ.py / ext_shop.py / ext_instance.py
> 原则：只定位，不实现；Event ≠ 函数调用；Event = 世界真实发生的事实

---

## 0. 核心边界定义

| 概念 | 定义 | 本阶段状态 |
|------|------|-----------|
| **AgentState** | 现在的状态（Read-only Projection） | ✅ P0-1 已建立 |
| **Event** | 刚刚发生的事实 | ✅ P0-2A 模型 / 🟡 部分接入 |
| **Memory** | 过去发生、以后可回忆的内容 | 🟡 旧系统独立运行 |
| **Function Call** | 函数执行（不是 Event） | ❌ 永远不是 Event |
| **save_data()** | 持久化（不是 Event） | ❌ 永远不是 Event |
| **旧 `enqueue_event`** | 写入记忆系统的旧机制 | 🟡 保留，不重构 |

**P0-2C 唯一任务**：基于真实代码，绘制 Event Boundary Map。
**P0-2C 明确不做**：EventBus / Scheduler / Wake / Brain / Decision / Action / Memory 重构 / TTS / ai_id 迁移。

---

## 1. SOCIAL / COMMUNICATION

### 1.1 message_received ✅ P0-2B 已完成

| 字段 | 内容 |
|------|------|
| **世界事实** | 用户在某房间发送了一条消息 |
| **候选 Event** | `message_received` |
| **实际发生位置** | `ext_ai.wake_ais_for_room()` 内，群聊分支 `return` 之后、建筑分支 `print` 之前 |
| **Adapter** | `agent/event_adapter.py::observe_message()` |
| **当前数据变化** | 原流程写入 `data.messages[room]`（由原聊天流程负责，Adapter 不写） |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ✅ 已完成（P0-2B） |
| **备注** | 一条用户消息 = 一个 Event。`target_ais` 只读快照。`ai_name=None` |

### 1.2 message_sent 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | AI 在某房间说出了一句话（chat 或 group） |
| **候选 Event** | `message_sent` |
| **实际发生位置（候选 1：单聊）** | `ext_ai.execute_action()` 的 `act == "speak"` 分支<br>· follow 同建筑子分支：`data.setdefault("messages", {}).setdefault(cur0, []).append(...)`<br>· 普通子分支：`data["messages"].setdefault(r, []).append({...})` |
| **实际发生位置（候选 2：群聊）** | `ext_ai.drive_ai()` 的 `trigger == "group"` 分支<br>`data.setdefault("messages", {}).setdefault("main", []).append({...})`<br>（**注**：`_group_talk` 只是派发器，不写入消息） |
| **实际发生位置（候选 3：邀约消息）** | `ext_date.handle_invite_date()` 中 `channel == "chat"` 时写入 `data.messages` |
| **当前数据变化** | `data.messages[room]` 追加一条 `{sender: ai, content, role: "assistant", time}` |
| **Agent 是否应感知** | ✅ 是（其他 AI / SNS / 关系系统可能需要） |
| **P0-2C 是否接入** | ❌ 否（只定位） |
| **待决问题** | ① 单聊 speak / 群聊 group / 邀约 chat 是否共用一个 `message_sent`，还是细分？<br>② Event 的 `source` 是 `"ai"` 还是具体 AI 名？ |
| **备注** | 系统广播（`_broadcast` / `_hall_msg` / `_broadcast_to_owner`）不算 AI 主动发言 |

### 1.3 message_sms_sent 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | AI 发出一条短信 |
| **候选 Event** | `sms_sent` |
| **实际发生位置** | `ext_ai.execute_action()` 的 `act == "sms"` 分支<br>`data["sms"].setdefault(to, []).append(...)`（多处循环） |
| **当前数据变化** | `data.sms[recipient]` 追加 |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **备注** | 与 `message_sent` 语义不同，不应合并 |

### 1.4 relationship_changed 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | 某 AI 与主人的关系状态发生变化 |
| **候选 Event** | `relationship_changed` / `affection_changed` |
| **实际发生位置** | ① `ext_date._finish_date()`：`_set_aff(ai, aff)`（约会结束 +5~9）<br>② `ext_date.date_accept_gift()`：`_set_aff(d['ai'], _aff(d['ai']) + 3)`（收礼物 +3） |
| **当前数据变化** | `data.affection[ai]` 变化 |
| **Agent 是否应感知** | ⚠️ 待评估——内部数值变化 vs 真正的关系跃迁 |
| **P0-2C 是否接入** | ❌ 否 |
| **待决问题** | +3 / +5 只是内部计算，什么阈值才算"关系变化"值得 Event？ |

---

## 2. MOVEMENT / WORLD

### 2.1 location_changed 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | AI 的 `ai_location` 从 A 变为 B |
| **候选 Event** | `location_changed` |
| **实际发生位置（15 处）** | 1. `ext_ai.execute_action()` speak+follow **同建筑**分支：`data.setdefault("ai_location", {})[ai] = got`<br>2. `ext_ai.execute_action()` speak **普通**分支：`data.setdefault("ai_location", {})[ai] = r`<br>3. `ext_ai.execute_action()` **note** 分支：同上<br>4. `ext_ai.execute_action()` **diary** 分支：同上<br>5. `ext_ai.execute_action()` **move** 分支：同上<br>6. `ext_ai.wake_ais_for_room()` 大喊分支 `arrive_and_reply()`：同上<br>7. `ext_ai._follow_arrive()`：`data.setdefault("ai_location", {})[ai] = go`<br>8. `ext_ai.drive_ai()` summon 分支 `_s()`：`data.setdefault("ai_location", {})[ai] = tgt`<br>9. `ext_ai._check_meetings()`：`data.setdefault('ai_location', {})[ai] = mt.get('room')`<br>10. `ext_date._arrive_date()`：`data['ai_location'][ai] = hall`<br>11. `ext_econ.auto_start_work()`：`data.setdefault('ai_location', {})[name] = 会客厅`<br>12. `ext_instance.enter_instance()`：`data.setdefault("ai_location", {})[ai_name] = "_instance_" + iid`<br>13. `ext_instance.pause_instance()`：传回住宅会客厅<br>14. `ext_instance.end_instance()`：传回住宅会客厅<br>15. `main.check_pending_moves()`（**未提供，需核对**）：执行 `ai_pending_moves` 到期 |
| **当前数据变化** | `data.ai_location[ai]` |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **待决问题** | 15 处修改，是否应统一到一个 Adapter？还是每个语义独立触发？ |

### 2.2 entered_location 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | AI **进入了一个新建筑**（进入本身值得感知） |
| **候选 Event** | `entered_location` |
| **实际发生位置** | `ext_world._arrive()` 内部：`ai_spot_tick` 检测到 `st['last_bid'] != bid` 时触发<br>（**这是目前唯一把"进入新地点"当独立事实处理的地方**） |
| **当前数据变化** | `ai_spot_state[ai]['last_bid']` 更新；随后可能触发 `_broadcast` / `add_trail` / `enqueue_event` |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **备注** | `ext_world._arrive` 已经在消费者角色上使用了"进入"这个事实 |

### 2.3 left_location 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | AI 离开了某个房间 |
| **候选 Event** | `left_location` |
| **实际发生位置** | 无独立事实。仅在消息层面有 `"🚶 {ai} 离开了 {cur}"` 系统消息<br>· `execute_action` speak+follow 同建筑分支<br>· `execute_action` move 分支<br>· `_follow_arrive()` |
| **当前数据变化** | 无（只有 system message 写入） |
| **Agent 是否应感知** | ⚠️ 待评估 |
| **P0-2C 是否接入** | ❌ 否 |
| **备注** | 当前无 `left_location` 独立事实，需要先决定是否需要 |

---

## 3. LIFE / WORK

### 3.1 work_started 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | AI 开始了一份工作 |
| **候选 Event** | `work_started` |
| **实际发生位置** | ① `ext_econ.auto_start_work()`（AI 自主 / 自动触发）<br>② `ext_econ.work_start()` API 端点（用户手动触发） |
| **当前数据变化** | `data.work_sessions[name] = {...}`，`data.ai_location[name]` 更新到工作建筑会客厅 |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **备注** | **ext_econ 完全没有调用 `enqueue_event`**——这是旧 Memory 的真空区 |

### 3.2 work_finished 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | AI 完成了工作，工资入账 |
| **候选 Event** | `work_finished` |
| **实际发生位置** | ① `ext_econ.pay_work()`（由 `work_tick` 定时结算）<br>② `ext_econ.work_stop()` API 端点（用户主动下班） |
| **当前数据变化** | `data.wallets[name] += earn`，`work_sessions` 中移除，`work_history` 追加 |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **备注** | 同样未调用 `enqueue_event` |

### 3.3 activity_started / activity_finished ❌ 不存在

| 字段 | 内容 |
|------|------|
| **世界事实** | —— |
| **候选 Event** | ❌ **暂不作为 Event** |
| **原因** | 代码验证：不存在统一的活动生命周期。真实存在的只有：<br>· `story_rhythm` / `writing_rhythm`：**冲动计时器**（冲动 ≠ 活动开始）<br>· `_plan_auto` / `_home_activity`：**决策/触发函数**（不是事实）<br>· `ai_spot_state`：到达建筑后的行为状态（不是活动） |
| **P0-2C 结论** | 删除该候选。若未来需要"活动"概念，应先设计 Activity 模型 |

---

## 4. DATING

### 4.1 date_invited 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | 某方向另一方发出了约会邀请 |
| **候选 Event** | `date_invited` |
| **实际发生位置（两个方向）** | ① **用户 → AI**：`ext_date.date_invite()` API（`POST /api/date/invite`）<br>② **AI → 用户**：`ext_date._trigger_invite()`（由 `ext_world._arrive` 或 `ext_ai._ai_think_invite` 触发） |
| **当前数据变化** | ① `data.date_invites[ai] = {...}`<br>② `data.date_invites_out[ai] = {...}` |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **旧 Memory 对应** | ② 已通过 `enqueue_event(action="AI主动邀约")` 记录<br>① **未记录** |

### 4.2 date_agreed 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | 约会邀请被接受 |
| **候选 Event** | `date_agreed` |
| **实际发生位置** | ① `ext_date._accept_invite()`（用户邀约场景）<br>② `ext_date._process_reply()` 中 `result == 'accept'`（AI 邀约场景） |
| **当前数据变化** | `data.dates.append({...status: 'coming'...})`，`ai_pending_moves` 设置 |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **旧 Memory 对应** | 已记录 `action="约会约定"`（两处都有） |

### 4.3 date_started 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | 双方到达约会地点，约会正式激活 |
| **候选 Event** | `date_started` |
| **实际发生位置** | `ext_date._arrive_date()`：`d['status'] = 'active'` |
| **当前数据变化** | `ai_location[ai]` 更新到约会房间，`ai_pending_moves` 清理 |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **旧 Memory 对应** | 已记录 `action="约会开始"` |

### 4.4 date_finished 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | 约会结束 |
| **候选 Event** | `date_finished` |
| **实际发生位置** | `ext_date._finish_date()`（用户主动结束 / 60 分钟自然结束 / 取消赴约） |
| **当前数据变化** | `affection[ai] += 5~9`（+3 如果带礼物未收），`date_log` 追加，`dates` 中移除 |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **旧 Memory 对应** | 已记录 `action="约会结束"` |

### 4.5 gift_received 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | 约会中主人收下 AI 送的礼物 |
| **候选 Event** | `gift_received` |
| **实际发生位置** | `ext_date.date_accept_gift()` API（`POST /api/date/accept_gift`） |
| **当前数据变化** | `shop_inventory[user]` 追加，`affection += 3` |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **旧 Memory 对应** | 已记录 `action="收礼物"` |

### 4.6 ⚠️ 旧 Memory Event 与 agent.Event 的关系

| 维度 | 旧 `ext_memory.enqueue_event()` | 新 `agent.Event` |
|------|-------------------------------|-----------------|
| **语义** | "这个发生过的事，以后可能用于夜间 LLM 总结" | "世界刚刚发生了什么" |
| **触发者** | 各插件内部 | Adapter（event_adapter.py） |
| **存储** | 写入 `memories/{owner}/{ai}/pending_events.json` | 运行时内存，**不持久化** |
| **消费者** | 夜间批处理（凌晨 2:05） | 无（P0-2C 阶段） |
| **生命周期** | 保留到夜间总结 | 创建后即返回，无存储 |
| **覆盖面** | **16 处调用**（见附录 A） | 1 处（`message_received`） |

**P0-2C 结论**：
- 旧 `enqueue_event` 继续保留，**不重构**
- 新 `agent.Event` 独立运行，**不接入旧 Memory**
- 未来 P1 阶段再考虑二者关系

---

## 5. ECONOMY

### 5.1 item_bought 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | 花金币买东西 |
| **候选 Event** | `item_bought` |
| **实际发生位置（2 处）** | ① `ext_shop.shop_buy()` API（**真人**购买，`POST /api/shop/buy`）<br>② `ext_shop._buy_ai_item()`（**AI** 自主购买，由 `ai_shop_tick` 触发） |
| **当前数据变化** | `wallets[buyer] -= price`，`shop_inventory[buyer][item_id] += qty`，`_broadcast` |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **旧 Memory 对应** | ① `action="真人消费"`<br>② `action="AI消费"` |
| **备注** | 代码已区分 AI / 真人两个 `action` 名，说明事件语义天然分两个 `source` |

### 5.2 gift_sent 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | 送礼 |
| **候选 Event** | `gift_sent` |
| **实际发生位置（3 处）** | ① `ext_shop.shop_gift()` API（**真人送礼**，`POST /api/shop/gift`）<br>② `ext_shop._do_reply_gift()`（**AI 回礼**，由 `ai_shop_tick` 中 `pending_reply` 触发）<br>③ `ext_shop._do_active_gift()`（**AI 主动送礼**，由 `ai_shop_tick` 触发） |
| **当前数据变化** | `wallets[sender] -= price`（AI 送礼时），`shop_inventory[recipient] += 1`，系统消息广播 |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **旧 Memory 对应** | ① `action="送礼"`<br>② `action="回礼"`<br>③ `action="主动送礼"` |
| **备注** | "送礼"从**送礼方**触发，"收礼"是副作用，不应独立成 Event |

### 5.3 money_changed ❌ 不作为独立 Event

| 字段 | 内容 |
|------|------|
| **世界事实** | 钱包余额变化 |
| **候选 Event** | ❌ **不独立成 Event** |
| **原因** | 钱包变化都是 `item_bought` / `gift_sent` / `work_finished` / 发钱的**副作用**，不是独立事实 |
| **例外** | 站长 `econ_init_wallets` 发钱（`POST /api/econ/init_wallets`）—— 这是独立事实，但**暂无 Memory Event** |
| **P0-2C 结论** | 见 `admin_issued_money` 候选（待评估） |

---

## 6. MEMORY（旧系统，不重构）

| 旧机制 | 位置 | 与 agent.Event 的关系 |
|--------|------|---------------------|
| `enqueue_event()` | ext_memory | 旧"事件式"调用。**保留**。共 16 处调用（附录 A） |
| `append_timeline(ai, text)` | main.py | 旧记录机制。**不是 Event** |
| `append_visited(ai, room)` | main.py | 旧记录机制。**不是 Event** |
| `add_trail(user, text)` | main.py | 旧记录机制。**不是 Event** |
| `ai_memories` | ext_mem | 碎片记忆（已降级） |
| `ai_impression` | ext_ai | 动态印象（每日/手动刷新） |
| `ai_timeline` | main | AI 时间线（最近 20 条注入 Prompt） |

**P0-2C 结论**：旧 Memory 保持原样。

---

## 7. INSTANCE / 副本

### 7.1 instance_created 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | 副本被创建（草稿） |
| **候选 Event** | `instance_created` |
| **实际发生位置** | `ext_instance.create_instance()` API（`POST /api/instance`） |
| **当前数据变化** | `data.instances[user][iid] = {... status: "draft" ...}` |
| **Agent 是否应感知** | ⚠️ 待评估（创建时 AI 未进入） |
| **P0-2C 是否接入** | ❌ 否 |

### 7.2 instance_entered 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | 副本被激活，AI 被锁定进入 |
| **候选 Event** | `instance_entered` |
| **实际发生位置** | `ext_instance.enter_instance()` API（`POST /api/instance/{iid}/enter`） |
| **当前数据变化** | `inst["status"] = "active"`，`ai_stay_put[ai_name] = True`，`ai_location[ai_name] = "_instance_" + iid` |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |

### 7.3 instance_paused 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | AI 暂离副本 |
| **候选 Event** | `instance_paused` |
| **实际发生位置** | `ext_instance.pause_instance()` API（`POST /api/instance/{iid}/pause`） |
| **当前数据变化** | `inst["status"] = "paused"`，`ai_stay_put` 清理，`ai_location` 传回住宅会客厅，系统消息 |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |
| **备注** | 命名应反映"暂停"而非"离开" |

### 7.4 instance_finished 🟡 已定位（未接入）

| 字段 | 内容 |
|------|------|
| **世界事实** | 副本结束，AI 解冻回住宅 |
| **候选 Event** | `instance_finished` |
| **实际发生位置** | `ext_instance.end_instance()` API（`POST /api/instance/{iid}/end`） |
| **当前数据变化** | `inst["status"] = "ended"`，LLM 生成 `summary`，AI 解冻并传回会客厅 |
| **Agent 是否应感知** | ✅ 是 |
| **P0-2C 是否接入** | ❌ 否 |

### 7.5 instance_message 🟡 已定位（未接入，主世界不感知）

| 字段 | 内容 |
|------|------|
| **世界事实** | 副本内发送了一条消息 |
| **候选 Event** | ⚠️ 副本内部事件，**主世界 Event 不覆盖** |
| **实际发生位置** | `ext_instance.instance_message()` API：`inst["chat_history"].append(...)` |
| **当前数据变化** | `chat_history` 追加（**与主世界 messages 隔离**） |
| **P0-2C 结论** | 副本内部消息**不应成为主世界 Event**（副本有自己的 context / world rules） |

### 7.6 其他副本相关 API（非 Event）

| API | 语义 | 是否 Event |
|-----|------|-----------|
| `PUT /api/instance/{iid}` | 编辑副本信息 | ❌ 配置操作 |
| `DELETE /api/instance/{iid}` | 删除副本 | ⚠️ 待评估（可能值得） |
| `POST /api/instance/tags` | 更新标签 | ❌ 配置操作 |
| `GET /api/instance/public/*` | 查询公开副本 | ❌ 查询操作 |
| `GET/POST /api/instance/bg` | 背景管理 | ❌ 配置操作 |

---

## 8. 方向性总结

| 方向 | 示例 | 已覆盖 | 未覆盖 |
|------|------|-------|--------|
| **用户 → AI** | 用户发消息 / 用户邀约 | 🟡 `message_received` (P0-2B) | `date_invited` (用户侧) |
| **AI → 用户** | AI 发消息 / AI 短信 / AI 邀约 | ❌ | `message_sent` / `sms_sent` / `date_invited` (AI 侧) |
| **AI → 世界** | AI 移动 / AI 工作 / AI 购物 | ❌ | `location_changed` / `work_started` / `item_bought` |
| **世界 → AI** | 节日 / 天气 / NPC 活动 | ❌ | 目前无 |
| **AI → AI** | AI 之间直接互动 | ❌ | 目前系统无此机制 |

---

## 9. 最终候选 Event 清单（20 个，1 已完成）
SOCIAL (4)
├── message_received ✅ P0-2B 已完成
├── message_sent 🟡 identified（execute_action + drive_ai/group）
├── sms_sent 🟡 identified（execute_action/sms）
└── relationship_changed 🟡 identified（_finish_date / accept_gift）

WORLD (2)
├── location_changed 🟡 identified（15 处）
└── entered_location 🟡 identified（ext_world._arrive）
（left_location 暂不作为 Event）

LIFE (2)
├── work_started 🟡 identified（auto_start_work / work_start）
└── work_finished 🟡 identified（pay_work / work_stop）
（activity_started/finished 已删除）

DATE (5)
├── date_invited 🟡 identified（date_invite / _trigger_invite）
├── date_agreed 🟡 identified（_accept_invite / _process_reply）
├── date_started 🟡 identified（_arrive_date）
├── date_finished 🟡 identified（_finish_date）
└── gift_received 🟡 identified（date_accept_gift）

ECON (2)
├── item_bought 🟡 identified（shop_buy / _buy_ai_item）
└── gift_sent 🟡 identified（shop_gift / _do_reply_gift / _do_active_gift）
（money_changed 不作为独立 Event）

INSTANCE (4)
├── instance_created 🟡 identified（create_instance）
├── instance_entered 🟡 identified（enter_instance）
├── instance_paused 🟡 identified（pause_instance）
└── instance_finished 🟡 identified（end_instance）
（instance_message 不纳入主世界）

---

## 10. 旧 Event / Memory 机制盘点

### 10.1 旧 `enqueue_event` 调用清单（16 处）

**ext_shop.py（5 处）**：
| 位置 | action |
|------|--------|
| `_do_reply_gift()` | `回礼` |
| `_do_active_gift()` | `主动送礼` |
| `_buy_ai_item()` | `AI消费` |
| `shop_buy()` | `真人消费` |
| `shop_gift()` | `送礼` |

**ext_date.py（5 处）**：
| 位置 | action |
|------|--------|
| `_trigger_invite()` | `AI主动邀约` |
| `_accept_invite()` | `约会约定` |
| `_arrive_date()` | `约会开始` |
| `date_accept_gift()` | `收礼物` |
| `_finish_date()` | `约会结束` |

**ext_world.py（6 处）**：
| 位置 | action |
|------|--------|
| `_arrive()` 内部 | `初访建筑` / `到达建筑` |
| `_try_story()` | `触发剧情` |
| `_arrive()` 居家分支 | `居家` |
| `_arrive()` work_event 分支 | `工作` |
| `_arrive()` shop_event 分支 | `购物` |

**ext_econ.py（0 处）**：完全没有 `enqueue_event`——`work_started` / `work_finished` 是旧 Memory 的**真空区**。

### 10.2 不是 Event 的机制

| 机制 | 位置 | 说明 |
|------|------|------|
| `drive_ai` | ext_ai | 函数入口 |
| `execute_action` | ext_ai | 函数入口 |
| `_group_talk` | ext_ai | 派发器（真正写入在 drive_ai/group 分支） |
| `_plan_auto` / `_home_activity` | ext_ai | 决策函数 |
| `auto_ai_loop` | ext_ai | 30 秒循环 |
| `ai_shop_tick` / `ai_spot_tick` / `work_tick` / `date_tick` | 各 ext | 轮询循环 |
| `save_data` | main | 持久化 |
| `_broadcast` / `_hall_msg` / `_broadcast_to_owner` | 各 ext | 系统广播（不是 AI 主动发言） |

---

## 11. 存在的不确定项

| # | 不确定项 | 为什么重要 | 验证位置 |
|---|---------|-----------|---------|
| U1 | `main.check_pending_moves()` 的具体实现 | `ai_pending_moves` 到期后如何更新 `ai_location` | main.py |
| U2 | `main.add_trail()` / `append_timeline()` 的调用是否应作为 Event 上游 | 决定 Event 与旧 Memory 的边界 | main.py |
| U3 | `_broadcast` 等系统广播是否应作为 Event | 决定是否引入 `system_broadcast` | 全局 |
| U4 | 用户手动 `POST /api/work/start` 与 AI 自主 `auto_start_work` 是否共享 `work_started` | 决定 `source` 字段设计 | ext_econ |
| U5 | `POST /api/instance` 创建副本时是否值得感知 | 副本的生命周期边界 | ext_instance |
| U6 | `econ_init_wallets`（站长发钱）是否独立成 `admin_issued_money` | 是否引入新 Event 类型 | ext_econ |
| U7 | 是否存在 AI → AI 直接互动代码 | SOCIAL 类是否需要扩展 | 全局搜索 |

---

## 12. P0-2C 完成后的状态

- ✅ Event Boundary Map 建立
- ✅ 20 个候选 Event 已定位（1 已完成，19 已识别）
- ✅ 旧 Memory / Event 机制盘点完成（16 处 `enqueue_event`）
- ✅ 7 个不确定项标记待验证
- ❌ 未接入任何新的 Event Adapter
- ❌ 未修改任何现有业务代码
- ❌ 未建立 EventBus / Scheduler / Wake / Brain

**下一步（由架构顾问决定）**：
- 可能选择 1-2 个高价值 Event 接入
- 或先验证不确定项
- 或进入 P0-2D

---

## 附录 A：旧 `enqueue_event` 完整清单（16 处）

见 Section 10.1。

## 附录 B：`ai_location` 修改位置完整清单（15 处）

见 Section 2.1。

## 附录 C：P0-2C 严格遵守的边界

- ❌ 未创建 EventBus
- ❌ 未创建 EventStore
- ❌ 未创建 Scheduler
- ❌ 未创建 Wake
- ❌ 未创建 Brain
- ❌ 未重构 Memory
- ❌ 未接入 TTS
- ❌ 未迁移 ai_id
- ❌ 未修改任何 ext_*.py（除 P0-2B 已完成的 `wake_ais_for_room` 旁路）
