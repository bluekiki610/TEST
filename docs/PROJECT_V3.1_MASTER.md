# 恋与临空 / Linkong — PROJECT V3.1 MASTER ARCHITECTURE ANCHOR

> 本文件是 V3.1 以后所有窗口的第一设计锚点。
> 它融合旧版 PROJECT.md 的现有功能地图 + V3.0 Agent Architecture + V3.1 新架构。
> 目标：换窗口、换 DS、换开发阶段，都不丢失“整个系统正在做什么”。

## 0. 当前状态

- 正式仓库：`bluekiki610/linkong`
- 当前 V3.0/V3.1 开发与验收：`bluekiki610/TEST`
- V3.0 P0-1 ~ P0-3B 已完成/接受。
- V3.1 当前处于：**Phase C 已完成（Goal / Motivation / Commitment / Intent 归档）**。
- V3.1 Phase A（Global Architecture Inventory）已完成。
- V3.1 Phase B1（Context Data Contract）已完成。
- V3.1 Phase B2-1（StableCoreProvider）已完成。
- V3.1 Phase B2-2（DynamicWorldProvider）已完成。
- V3.1 Phase B2-3（RecentProvider）已完成。
- ✅ V3.1 Phase B2-4（LongTermProvider Stub）已 ACCEPTED。
- ✅ V3.1 Phase B3（ContextAssembler）已 ACCEPTED。
- ✅ V3.1 Phase B4（Runtime Connection Pre-Flight）已 ACCEPTED。
- ✅ V3.1 Phase B5-0（Context Contract Decision）已 ACCEPTED。
- ✅ V3.1 Phase B5-1（Contract Change CC-20260926-01）已 ACCEPTED。
- ✅ V3.1 Phase B5-2（Runtime Connection）已 ACCEPTED。
  - `agent/runtime.py` Commit SHA：`525973ae6ee00c02bbc43a608c6c27cb15b62ebb`
  - 该 commit 属于 B5-2 阶段；B5-3 未修改 `agent/runtime.py`。
- ✅ V3.1 Phase B5-3（Runtime Context Connection Tests）已 ACCEPTED。
  - 新增 `docs/test_b5_runtime_context.py`
  - 覆盖 T1-T12 + 附加测试
  - B5-3 未修改任何架构 `.py`
- ✅ V3.1 Phase B5-4（PROJECT Update）已完成。
  - 封板 commit：`a97293d7a312463748cb52029246fb27989e9873`
- ✅ V3.1 Phase B6（THINK / Decision 架构预检，修订版）已 ACCEPTED。
  - 明确 `think(context) -> Optional[str]` 是 B5 临时占位，不代表最终 Intent Contract
  - 修正 Goal / Motivation / Intent / Decision / Action 定义
  - 明确 World Query 为无副作用信息查询，不是决策层
  - Goal 最终持久化位置暂不冻结
- ✅ V3.1 Phase C-0（Goal / Motivation / Commitment / Intent Contract Preflight）已完成。
  - 新增 `docs/C0_GOAL_MOTIVATION_COMMITMENT_INTENT_PREFLIGHT.md`
  - 冻结 Goal / Commitment 生命周期与状态机
  - 冻结 Goal 来源（Relationship / Memory / Commitment）
  - 冻结 Goal 允许多个并存（优先级待 C-1）
  - 冻结 Commitment 数据结构草案与强度分级（hard / soft / implicit）
  - 冻结 Commitment 与 Goal 的关系
  - 明确 Motivation 是计算结果，不需持久化
  - 冻结 Intent 结构化原则（可审计、可多候选、携带 reason）
  - 冻结 Intent → Decision → Action 三层分离
  - 冻结 Goal / Commitment 必须跨 Event 存在，但**最终持久化位置暂不冻结**
  - 冻结与 main.data 的兼容边界（不写入、不新增字段）
  - 冻结 AI↔AI Commitment / Goal 只能由 AI B 自行形成
  - 冻结取消 / 冲突 / 过期 / 完成后的行为
  - 本阶段只做设计，**未修改任何 `.py`**
- ✅ V3.1 Phase C-1（Goal / Motivation / Commitment / Intent Contract Change，CC-20260927-01）已 ACCEPTED。
  - 新增 Contract §5A
  - 冻结 Goal / Commitment 生命周期、来源、reason 语义
  - 冻结 `hard` Commitment 正式定义（不等于"永远不可违背"）
  - 冻结 Intent 结构化、不持久化，跨 Event 连续性由 Activity / Commitment / Goal 承担
  - 明确 Memory Runtime 未启用，不得假设 Memory 已可产生 Goal
  - 明确 Goal / Commitment 不得产生第二套平行数据库
- ✅ V3.1 Phase C-2 Preflight（Goal / Commitment Implementation）已 ACCEPTED。
  - 新增 `docs/C2_GOAL_COMMITMENT_IMPLEMENTATION_PREFLIGHT.md`
- ✅ V3.1 Phase C-2 Contract Change（CC-20260927-02）已 ACCEPTED。
  - 新增 Contract §5B
  - 冻结 Goal / Commitment 最小结构
  - 冻结 Runtime-only working state 身份（非 SOT）
  - 冻结 Goal source 与 creation mechanism 分离（只提供 explicit programmatic create API）
  - 冻结 Goal.reason / Intent.reason 语义分离
  - 冻结 Motivation 纯函数 + 最小输入集合（Goal / Commitment / AgentState snapshot / now_ts）
  - 冻结 Intent / IntentSet 最小结构
  - 冻结 `think(context: AgentContext) -> IntentSet`
  - 冻结 Stub 阶段 `IntentSet(candidates=[])` 合法性
- ✅ V3.1 Phase C-2 Implementation 已 ACCEPTED。
  - 新增 `agent/goal.py` / `agent/commitment.py` / `agent/motivation.py` / `agent/intent.py`
  - 修改 `agent/runtime.py`：`think()` 迁移为 `-> IntentSet`
  - 新增 `docs/test_c2_goal_commitment.py`
  - Commit SHA：`033ecccfcb3efd90351b5baec6c87cde31a6e737`
  - Commit SHA：`6e0963765983c7bfcff734505279b481edc99faf`
- ✅ V3.1 Phase C-3 Tests Preflight 已 ACCEPTED。
  - 输出 C-3 Tests Preflight Report
  - 识别 12 项测试缺口（G1 ～ G12）
- ✅ V3.1 Phase C-2 Runtime Working-State Contract Patch（CC-20260928-03）已 ACCEPTED。
  - 新增 Contract §5B.5 补丁 / §5B.15 补丁 / §5B.16
  - 明确 Goal / Commitment = AgentRuntime-owned Runtime working state
  - 允许 `AgentRuntime` 持有 `_goals: Dict[str, Goal]` / `_commitments: Dict[str, Commitment]`
  - 允许最小 holder API：add / get / list / replace
  - 禁止自动 transition / 自动过期 / 冲突解决 / 优先级
- ✅ V3.1 Phase C-2 Implementation Patch（Runtime Holder + Hardening）已完成。
  - `agent/runtime.py` 新增 Runtime holder + 8 个 holder 方法
  - Hardening：所有 get / list 返回 `deepcopy`，add / replace 存储 `deepcopy`
  - 新增 `docs/test_c2_runtime_holder.py`（H1 ～ H17）
  - Runtime Holder Commit SHA：`c76391e7fb0406c1aba5d50989363dd583877565`
  - Runtime Holder Self-Test Commit SHA：`54d510250c91ef56fa267ae099c7826609e2cca0`
- ✅ V3.1 Phase C-3 Tests Implementation 已完成，等待架构审核。
  - 新增 `docs/test_c3_contract_structure.py`（A1 ～ A10 + B11 + C9 + C11 + D4 + D11 + F7）
  - 新增 `docs/test_c3_boundary.py`（E1 ～ E11）
  - 6 组测试全部通过
- ✅ V3.1 Phase C-4 PROJECT Update 已完成。
- ✅ **V3.1 Phase D-0（World / Activity / Capability Preflight）**

  | 子阶段 | 状态 |
  |--------|------|
  | D-0 Preflight（设计冻结准备） | ✅ 已完成（`docs/D0_WORLD_ACTIVITY_CAPABILITY_PREFLIGHT.md`） |
  | D-0 Conflict Audit | ✅ **ACCEPTED**（`docs/D0_CONFLICT_AUDIT.md`：45 项发现 / 36 YES / 6 UNCERTAIN / 3 NO / 5 OPEN QUESTION） |
  | D-0 Architecture Decisions | ✅ **ACCEPTED**（`docs/D0_ARCHITECTURE_DECISIONS.md`：D0-DEC-1 ～ D0-DEC-8，关闭全部 5 个 OPEN QUESTION，无新增） |
  | D-0 Contract Change | ✅ **ACCEPTED**（CC-20260930-04，`docs/V3.1_ARCHITECTURE_CONTRACT.md` 新增 §5C） |
  | D-0 Architecture Tests | ✅ **RAN / PASSED**（`docs/test_d0_world_activity_capability.py`：**Ran 54 tests … OK**，真实运行） |
  | **D-0 Seal** | ✅ **SEALED / APPROVED**（D-0 Architecture Review 结果：APPROVED） |
  | **D-1 Preflight** | ✅ **APPROVED**（`docs/D1_WORLD_QUERY_PREFLIGHT.md`：D1-DEC-1 ～ D1-DEC-15） |
  | **D-1 Contract §5D** | ✅ **APPROVED**（CC-20260930-05，`docs/V3.1_ARCHITECTURE_CONTRACT.md` §5D） |
  | **D-1 Architecture Tests** | ✅ **RAN / PASSED**（`docs/test_d1_world_query.py`：**Ran 51 tests … OK**，`GATE STATE: OPEN`，真实运行）<br>※ 门关闭阶段的历史运行记录为 **49 tests**（门开后 T-A 项数变化，故为 51） |
  | **D-1 Gate Correction** | ✅ **APPROVED**（T-A / T-B 生命周期分离 + 静态验证策略定位 + FORBIDDEN / 五态分离） |
  | **D-1 Implementation** | ✅ **ACCEPTED**（D1-H1 ～ H4 Hardening 已应用并验证）—— `agent/world_query.py` |
  | **D-1 Post-Implementation Gate（T-B）** | ✅ **RAN / PASSED**（静态边界，**Ran 51 tests … OK**） |
  | **D-1 Behavior Tests（D1-H4）** | ✅ **RAN / PASSED**（`docs/test_d1_world_query_behavior.py`：**Ran 70 tests … OK**，真实运行） |
  | **D-1 Implementation Review** | ✅ **APPROVED** |
  | **D-1 SEAL** | ✅ **SEALED**（见 §20.5.2 SEAL Record） |
  | **D-2 Preflight** | ✅ **APPROVED WITH ARCHITECTURAL CORRECTIONS** |
  | **D-2 Contract §5E** | ✅ **APPROVED**（CC-20260930-06，含 §5E.22 D-2 阶段门） |
  | **D-2 Architecture Tests** | ✅ **APPROVED**（架构审核 SHA `a622e537…`，Ran 53 tests … OK）<br>✅ **SEALED**（门控修正后 **Ran 64 tests … OK**，见 §20.5.3 Seal Record） |
  | **D-2 Gate** | 🔓 **OPEN**（`D2G-GATE-STATUS: OPEN` / `D2G-3-MARKER: true`；架构侧正式授权） |
  | **D-2 Implementation** | ✅ **VERIFIED / APPROVED** |
  | **D-2 Implementation Seal** | ✅ **SEALED**（见 §20.5.4 Seal Record） |
  | **D-2 Behavior Tests** | ✅ **RAN / PASSED**（`docs/test_d2_activity_behavior.py`：**Ran 74 tests … OK**）<br>→ 含 E 组 **15 项 immutable-boundary 行为证明** |

  **Immutable Boundary 修复（架构侧裁决 A / 只修隔离，不扩大 D-2）：**

  ```text
  缺陷（已由真实运行证实，现已修复）：
      frozen=True 只冻结属性重绑定，不冻结容器内容 → 三层穿透

  修复（仅隔离，未改生命周期 / ownership / SOT / 未加 persistence / Event /
        scheduler / Motivation / Capability / Movement / main.data）：

      输入侧 → _deep_freeze()：构造期递归冻结
               role_map / metadata 的嵌套 dict → MappingProxyType，list → tuple
               → 调用方事后修改自己传入的 dict **不再**影响 Activity

      输出侧 → _copy_for_read()：内部真相永远冻结，对外返回独立可变快照
               已接入**全部**返回 Activity 的路径：
                   create_activity / get / require / list_*（经 list_all）
                   / primary_activity / bound_activities / transition().activity

  行为证明（E 组 15 项，含架构侧指定的两条反向测试）：
      e1  frozen 阻止属性重绑定
      e2  转换不分叉真相
      e3  get() 不允许嵌套 metadata 穿透        ← 架构侧指定
      e4  get() 不允许 role_map 穿透            ← 架构侧指定
      e5  深层嵌套（dict→dict→list）不穿透
      e6  require() 路径不穿透
      e7  全部 list_* 路径不穿透
      e8  primary_activity() / bound_activities() 不穿透
      e9  transition().activity 不穿透
      e10 create_activity() 返回值不穿透
      e11 输入 metadata 不产生外部别名
      e12 输入 role_map 不产生外部别名
      e13 两次读取互相独立
      e14 绕过 Registry 直接构造也被构造期冻结
      e15 Activity 仍是 frozen dataclass

  测试计数（精确核对，EV-17）：
      总计 74 项
          A 11 · B 12 · C 9 · D 8 · E 15 · F 9 · G 6 · H 4 = 74

  ⚠️ 隔离修复同时暴露并修正了 2 处**测试自身**的错误：
      test_d1 —— 原用 `assertIs` 断言「三次读取返回同一对象」，
                 这**要求返回内部引用**，与裁决 A 的隔离要求直接冲突。
                 EC-4 的真义是「Registry 中只有一个**真相**」，
                 不是「对外必须返回同一对象」。
                 → 改为验证：identity 一致 + 对外是快照 + 改快照不影响真相
      test_d6 —— 误用 `self.aid`（该属性只属于 E 组）→ 改为自建夹具
  ```

  | D-3 | 🔴 **BLOCKED**（本轮禁止进入） |

  **D-2 Implementation Verification（架构侧要求）：**

  ```text
  架构审核结论：agent/activity.py 结构方向通过；
                但只有实现、缺乏实现级行为测试与真实运行证据 → 不得 Seal。

  本轮新增：docs/test_d2_activity_behavior.py（行为测试）
  ```

  **⚠️ 待架构侧裁决：immutable-boundary 问题**

  ```text
  现象（静态分析已确认，待真实运行确认）：
      Activity 是 @dataclass(frozen=True)，
      但 metadata / role_map / nested 结构仍是**可变 dict / list**。

      frozen=True 只冻结**属性重绑定**，不冻结**容器内容**。

      因此存在穿透路径：
          registry.get(id).metadata["k"] = v
          registry.get(id).role_map["x"] = "y"
          registry.get(id).metadata["nested"]["deep"].append(v)
              ↓
          Registry 内部 Activity 真相可能被静默改变

  证据链（静态）：
      activity.py:  role_map: Dict[str, str] = field(default_factory=dict)
                    metadata: Dict[str, Any] = field(default_factory=dict)
      create_activity(): metadata=copy.deepcopy(dict(metadata or {}))
      _store(): 直接存对象引用（未做不可变包装）

  本问题由 docs/test_d2_activity_behavior.py 的 E 组（test_e2 / e3 / e4）验证。
  **若穿透成立，E 组会 FAIL 并把观测结果写入失败信息。**

  架构侧需裁决（DS 不得自行选择）：
      A. 修改实现，使嵌套结构真正隔离（MappingProxyType / 深拷贝 / tuple）
      B. 明确 Contract 只要求属性级 frozen，接受该语义

  当前 DS 未修改实现（遵守「不允许 DS 自己选择」）。
  ```

  **D-2 进展：**

  ```text
  D-2 Preflight                ✅ APPROVED WITH ARCHITECTURAL CORRECTIONS
  D-2 Contract §5E             ✅ APPROVED（CC-20260930-06）
  D-2 Architecture Tests       ✅ SEALED（64/64 PASS）
  D-2 Gate                     🔓 OPEN（D2G-GATE-STATUS: OPEN / marker true）
  D-2 Implementation           ✅ VERIFIED / APPROVED
  D-2 Implementation Seal      ✅ SEALED（见 §20.5.4 Seal Record）
  D-2 五套回归                  ✅ 全绿
                                  D-0 54/54 · D-1 51/51 · D-1 behavior 70/70
                                  D-2 architecture 64/64 · D-2 behavior 74/74
  D-3                          🔴 BLOCKED
  ```

  **D-2 Immutable Boundary（架构侧裁决 A）—— 已闭合：**

  ```text
  input isolation        ✅ PASS（构造期 _deep_freeze）
  output isolation       ✅ PASS（全部读取路径 _copy_for_read）
  deep nested isolation  ✅ PASS（dict → dict → list 不穿透）

  Implementation SHA : b7a201979ab9ba26ac6b658e8ae85866702cb625
  Docs SHA           : ec40f53d619f68c8d4cb4d5aa83d0e4ce63dd38e
  ```

  **门开后首次真实运行结果（必须记录）：**

  ```text
  GATE STATE      : OPEN (implementation authorized)
  impl presence   : PRESENT -> agent/activity.py
  boundary scan   : 1 impl file(s) —— 实现存在，扫实现文件本身
  Ran 64 tests … FAILED (failures=2)

  失败项定性：
      test_ta2 → 硬编码 assertFalse(_gate_open())，门合法打开后必失败
                 （断言写成「门必须关闭」，与门可开合的设计矛盾）
      test_ta5 → 正则 `class\\s+\\w*ActivityRegistry` 误报：
                 `\\w*` 允许空匹配 → 同时命中 `class ActivityRegistryError`
                 → 把「1 个 Registry + 1 个异常类」误报成「2 个 ActivityRegistry」
  ```

  **修正（均为测试侧，未改实现）：**

  | 项 | 修正 |
  |----|------|
  | `ta2` | 改为**门态自洽**断言（CLOSED 或 OPEN 都验证一致），并新增 `D1G-16` 干扰文本反例验证 |
  | `ta5` | 类检测由**正则**改为 **AST 精确 class 计数**（`_count_exact_class`），并按 `D1G-17` 记录原因 |
  | `ta4` | 重命名为 `test_ta4_premature_implementation_guard`，门开后明确「不适用」 |
  | 附 | `ta5` 增加附带断言：门开时实现文件必须定义 `Activity` class（`EC-1`） |

  **门控 bug（`EV-20`）最终记录 —— 三轮才收敛：**

  ```text
  第 1 轮：GATE 误报 OPEN → test_ta2 / test_ta4 失败
      推断「裸标识符被逐行匹配」→ 加否定词表
      结果：无效（未打中根因）

  第 2 轮：GATE 仍误报 OPEN → test_ta3 / test_ta5 失败
      读 Contract 原文后定位真实根因：
          §5E.22「定义」段写了
              implementation authorized = …肯定式标记 D2G-3-SATISFIED: true
          这句**说明标记是什么**的文字被当成了**门已开**
      → 改为结构化键值 + 严格前缀匹配
      结果：GATE STATE = CLOSED ✅（实测）

  第 3 轮：test_ta2 失败（2 != 1）
      我的断言把「单一来源」误解为「只能出现一次」；
      而变更日志中另有一处**取值一致**的引用
      → 改为**一致性**语义（所有出现必须一致；分歧则 fail-closed）
      → Contract 变更日志改为非键值描述，真正实现单一来源
  ```

  **教训（比 bug 更重要）：**

  ```text
  ① 第一次修正是「基于推断」而非「读取原文」→ 未命中根因，浪费一轮运行
  ② 「单一来源」≠「只出现一次」；正确语义是「所有出现必须一致」
  ③ D1G-16（区分「状态构造」与「说明文本」）在 Contract 文档自身也会被违反，
     且比代码中的 docstring 误报更隐蔽
  ```

  **门控 bug（`EV-20`）—— 必须记录（两次尝试才对）：**

  ```text
  现象：Gate 误报为 OPEN，导致 test_ta3 / test_ta5 连锁失败

  第一次尝试（修正 ①）—— 未打中根因：
      推断「裸标识符 D2G-3-SATISFIED 被逐行匹配」
      改为要求带值形式 `D2G-3-SATISFIED: true`
      → 复跑仍然 OPEN

  真实根因（修正 ② 才定位）：
      Contract §5E.22 的「定义」段写了：

          implementation authorized = 架构侧在 Contract 中写入肯定式标记 D2G-3-SATISFIED: true

      **这句「说明标记是什么」的文字，本身被当成了「门已开」。**

  定性：这是 `D1G-16`（静态边界断言必须区分「代码构造」与「说明文本」）
        的**教科书级复现** —— 而且发生在 Contract 文档自身，
        比 D-1 的 docstring 误报更隐蔽。

  最终修正：
      ① 门状态改为**结构化、可机读、单一来源**：
             D2G-GATE-STATUS: CLOSED
             D2G-3-MARKER: null
      ② `_gate_open()` 改为**严格前缀匹配**（行首即键名 + 紧跟冒号），
         因此 blockquote 示例 / 行内代码 / 粗体强调**一律不构成开门**
      ③ 说明文本**不再使用标记的字面赋值形式**（改用 `STATUS = OPEN` 等非解析形式）
      ④ 回归断言 `test_ta2_gate_status_is_structured_and_parseable`：
         同时验证结构化、唯一性、自洽性，以及「说明文本不得影响判定」

  教训（比 bug 本身更重要）：
      第一次修正是**基于推断**而非**读取原文**，因此没打中根因。
      「先读事实、再下结论」在本次被违反了一次；
      第二次改为直接读 Contract 原文定位，一次命中。
  ```

  **D-2 Tests 首次真实运行结果（必须记录）：**

  ```text
  PHASE GATE : CLOSED (implementation not authorized)
  activity module : ABSENT
  Ran 53 tests … FAILED (failures=3)

  失败项：
      test_g4_forbidden_jumps_declared
      test_g7_recovery_does_not_create_new_identity
      test_h3_no_activity_event_production
  ```

  **3 处失败的定性（关键 —— 其中 2 处是 Contract/测试的真实缺口）：**

  | 失败项 | 定性 | 修正 |
  |--------|------|------|
  | `test_g4` | ✅ **测试正确抓到 Contract 真实缺口**：§5E.6 只有「禁止随意跳跃」一句，**未逐条列举**被禁止的具体跳跃（D-0 Preflight §12 有，但未搬入 §5E） | **修 Contract**：新增「禁止的跳跃（冻结，逐条列举）13 条」+ 新规则 `EF-11` ～ `EF-13` |
  | `test_g7` | 测试措辞未对齐（Contract 原文含 `**不得**` 粗体标记，子串不连续） | 改为兼容粗体标记的正则 |
  | `test_h3` | 测试范围过宽（在门关闭时扫描全部 `agent/`，命中 **B5/C-2 已存在的合法模块** `event_adapter.py` / `runtime.py` 对 `agent.event` 的依赖） | 补门控 + 收窄为「仅检查 Activity 实现文件」 |

  > **注：** `test_g4` 是本轮最有价值的发现 ——
  > 它证明**架构测试确实能反向发现 Contract 的遗漏**，而不是只做实现的单向检查。

  **D-2 Architecture Tests 覆盖（15 项重点验证 + T-A/T-B 双门）：**

  ```text
  T-A · Pre-Implementation Gate（按 Contract 标记 D2G-3-SATISFIED 判定）
      ta0 门状态可判定
      ta1 门控判据必须是 Contract 标记，不是文件存在
      ta2 门状态与实现存在性一致（CLOSED→不存在；OPEN→存在）
      ta3 门关闭时不得提前实现
      ta4 ActivityRegistry / ActivityRuntime 边界
      ta5 无隐式 persistence        ← 实现存在时同样执行
      ta6 无 scheduler / tick/timer ← 实现存在时同样执行
  T-B · Post-Implementation Boundary Gate（仅实现存在时生效）
      tb0 扫描目标必须覆盖实现文件（EG-16）
      tb1 实现内无 persistence
      tb2 实现内无 scheduler
      tb3 实现内不产生 Event
      tb4 实现内不反向写 Legacy
      tb5 实现内不接入 Motivation
      tb6 实现内不接入 Capability
      tb7 实现内不 import main / ext_*
  A  阶段门（Registry / persistence / scheduler 边界）
  B  Registry 唯一性 / 单一真相 / AgentRuntime 不拥有 / primary=binding
  C  World SOT（无 activities key / 无 persistence / 无隐式持久化）
  D  Motivation（Formal Activity 不进入）/ AgentState（Legacy Label）
  E  Scheduler 边界（无 tick/timer；expected_end_at 不自动完成）
  F  Legacy 单向关系（禁止 Activity → Legacy / 双向同步）
  G  生命周期与终态不可逆（含禁止跳跃逐条列举）
  H  未冻结项不得提前实现
  I  Contract / Preflight 文档边界
  J  D-0 / D-1 未被破坏
  K  环境能力（不伪造结果）
  ```

  **D-2 门控设计修正（架构侧 Review）：**

  | 问题 | 修正 |
  |------|------|
  | `_implementation_present()` 把「文件存在」当作 Gate OPEN/CLOSED，**混淆 presence 与 authorization** | 新增 Contract §5E.22 + 标记 `D2G-3-SATISFIED`；测试判据改为 `_gate_open()`（读 Contract），`_implementation_present()` 只回答「文件是否存在」 |
  | `test_a3` / `test_a4` / `test_a5` / `test_c3` / `test_e1` / `test_e2` / `test_f2` / `test_h3` 在实现存在时 **`return` 跳过** → 未来会漏检 persistence / scheduler | 移除全部跳过路径；新增 `_boundary_scan_targets()`（实现存在时扫**实现文件本身**）；新增 T-B 组 `test_tb0` ～ `test_tb7` **直接断言扫描目标必须覆盖实现文件** |
  | 新增规则 | `EG-12` ～ `EG-17` |

  **D-1 SEAL 结论：**

  ```text
  D-1 SEAL = SEALED
  三门全部真实通过：
      D-0 regression    Ran 54 tests … OK
      D-1 architecture  Ran 51 tests … OK（GATE STATE: OPEN）
      D-1 behavior      Ran 70 tests … OK
  D-2 = READY / NEXT（Preflight 尚未创建；本轮未提前设计）
  ```

  **D-1 Implementation 交付：**

  ```text
  agent/world_query.py        新增（World Query Foundation，只读）
  ```

  **实现严格遵守 Contract §5D：**

  - `QueryResult`：`status`（五态核心）与 `outcome`（ALLOWED / FORBIDDEN）**正交**
  - Dependency Injection：**不 import main / ext_***；不持有全局状态
  - **无任何写入模式**（D-1 静态验证策略：不使用就地修改 dict / list 的写法）
  - 不读 AgentState；不产生 / 不消费 Event；不实现 Activity / Capability / Movement / Command
  - 不触碰 Memory；不新增 `main.data` 顶层 key；不修改现有 HTTP 接口 / 前端
  - 反模式守卫：`is_decision_like_request()` + `not_capabilities` 自描述（WQ-90 ～ WQ-93）
  - `UNSUPPORTED` 清单冻结（`WQ-110` / `WQ-111`）：Map / NPC 位置 / purpose 检索 /
    relationship / route / available places / activity
  - `get_agents_in_building` 为 **`DERIVED` 有限支持**（`WQ-85` ～ `WQ-89`），
    无法解析者记入 notes（不假装不存在）

  **T-B Gate 真实运行结果（最终 —— 通过）：**

  ```text
  === D-0 ===
  python docs/test_d0_world_activity_capability.py
  Ran 54 tests … OK

  === D-1 ===
  python docs/test_d1_world_query.py
  GATE STATE      : OPEN (implementation authorized)
  d1 impl modules : 1
  Ran 51 tests … OK   (skipped=1 —— test_ta2 仅门关闭时适用)
  ```

  **过程中修正的 2 类问题（均属测试层，非架构层）：**

  ```text
  ① T-B 三条断言（tb4 / tb7 / tb8）误报
     根因：裸文本包含把 world_query.py 自身 docstring 中的「否定式说明」
           当成了违规（"不调用 save_data()" / "不得读取 AgentState" /
           "禁止返回 … PLANNED / TRAVELING"）
     修正：按 Contract §5D.16.2 / D1G-16 ～ D1G-20，
           移植 _effective_code()（tokenize 级掩掉注释与字符串字面量）

  ② D-0 test_t6_6 阶段冲突
     根因：断言 world_query.py「不存在」，D-1 落地后必然永久失败
           （与 T-A 死锁同构）
     修正：改为「门感知」——门关闭断言不存在；门打开断言存在
  ```

  **D-1 Implementation Review（架构侧）→ Hardening：**

  ```text
  D-1 Implementation Review = ❌ NOT SEALED（发现 4 项 Contract 实际违规）
        ↓
  D-1 Implementation Hardening（D1-H1 ～ D1-H4）
        ↓
  待重跑验证
  ```

  | 编号 | 问题（架构侧审核） | 修正 |
  |------|------------------|------|
  | **D1-H1** | `_owner_invites()` 未接收**目标 owner**，导致私人房间授权可被「任意认识的用户/AI」绕过 | 改为以**目标 owner** 为中心的授权族：`_requester_is_owner` / `_requester_owns_agent` / `_requester_is_agent` / `_requester_has_same_owner` / `_can_view_room` / `_can_view_building`；**fail-closed**（无法归属 → 按不公开） |
  | **D1-H2** | 暴露范围超出 `WQ-94` 白名单（钱包 / 好感 / 归属 / legacy 活动 / dating / working / following / owner 清单均未做权限限制） | 全部接入可见性检查：私人状态仅**本人 / 其 owner / 同一 owner 范围**；其余 → `FORBIDDEN`。缺省 `requester` **不得**视为上帝视角 |
  | **D1-H3** | `get_building()` / `get_room()` 为**浅复制**，nested dict / list 仍引用 `main.data` | 引入 `copy.deepcopy` 生成**真正安全副本**（唯一允许的例外，Contract `D1G-23` ～ `D1G-25`） |
  | **D1-H4** | 51 tests OK ≠ 实现满足 D-1（静态边界测试不验证行为） | 新增 [`docs/test_d1_world_query_behavior.py`](docs/test_d1_world_query_behavior.py)：**70 项行为级断言**（B1 私人房间授权 / B2-B3 公开性 / B4 私人状态不泄露 / B5 返回值不穿透 / B6 五态语义 / B7 反模式守卫 / B8 回归） |

  **新增 Contract 规则：** `D1G-23` ～ `D1G-32`（§5D.16.3 深拷贝例外 + §5D.16.4 白名单实现级要求）。

  **公开性判定（冻结，未新增 schema 字段）：**

  ```text
  建筑  ： type == "npc" / 无 owner / public == True
  房间  ： main / 以 ·会客厅 结尾 / 所属建筑公开
  AI 在场： 该 AI 当前位于公开房间
  AI 私人： 仅本人 / 其 owner / 同一 owner 范围
  其他  ： 默认不可见（fail-closed）
  ```

  **Phase D 当前门状态（必须最先读）：**

  ```text
  Pre-Implementation Gate          = OPEN（架构侧已授权 D-1 Implementation）
  Post-Implementation Gate（T-B）   = RAN / PASSED（51 tests OK）
  D-1 Implementation               = 已完成 Hardening（D1-H1 ～ H4）
  ```

  > 详细门控记录见 §20.5.1（含历史沿革）。
  > **本文件不得同时出现「门已开」与「门未开」两种状态描述。**

  **D-0 冻结基线（SEALED）：**

  ```text
  docs/D0_CONFLICT_AUDIT.md                  ACCEPTED
  docs/D0_ARCHITECTURE_DECISIONS.md          ACCEPTED
  docs/V3.1_ARCHITECTURE_CONTRACT.md §5C     ACCEPTED
  docs/test_d0_world_activity_capability.py  RAN / PASSED（54 tests OK）
  生产代码（D-0 阶段）                        0 修改
  ```

  **D-1 当前唯一任务：World Query Foundation。**

  > 目标：让 Agent Core 能通过统一、只读、无 LLM、无行为决策、无 World mutation 的接口询问当前世界事实。
  > **D-1 不实现 Activity / Capability / Movement / World Command；不改 `ext_ai.py` / `ext_world.py` / `ext_room.py` 旧行为；不修 Memory；不进入 D-2。**

  **D-1 阶段门（Contract §5D.16，`D1G-1` ～ `D1G-32`）：**

  ```text
  D-1 Preflight                ✅ APPROVED（含两轮修正）
  D-1 Contract Change（§5D）    ✅ APPROVED（含 TEST GATE CORRECTION）
  D-1 Architecture Tests       ✅ RAN / PASSED（51 tests OK，GATE STATE: OPEN）
  D-1 Pre-Implementation Gate  ✅ PASSED（架构侧已授权）
  D-1 Implementation           ✅ ACCEPTED（D1-H1 ～ H4 Hardening 完成）
  D-1 Behavior Tests           ✅ RAN / PASSED（70 tests OK）
  D-1 Post-Implementation Gate ✅ RAN / PASSED（51 tests OK）
  D-1 Implementation Review    ✅ APPROVED
  D-1 SEAL                     ✅ SEALED
  D-2                          🔓 READY / NEXT
  ```

  **阶段门生命周期（第二轮裁决，已落实）：**

  | 门 | 生效时机 | 断言 | 实现落地后 |
  |----|---------|------|-----------|
  | **T-A · Pre-Implementation Gate** | 实现之前 | 断言实现**不存在**（防提前偷做） | 转为断言实现**存在** → **自动通过** |
  | **T-B · Post-Implementation Boundary Gate** | 仅实现存在时 | 只读 / 无副作用 / 无 LLM / 无 Event / 无 Activity / 无 AgentState / 五态 / FORBIDDEN / UNSUPPORTED | 全部生效 |

  > **禁止把 T-A 实现为「永久断言不存在」；任何阶段门都不得形成「无法通过」的终态。**
  > 门状态由 Contract §5D.16 的显式标记（`D1G-3-SATISFIED`）决定，**不由 DS 自行判断**。

  **D-1 严格只读策略的定位（第二轮裁决）：**

  「禁止 **local** `append` / `sort` / `pop`」= **D-1 静态验证策略**，
  **不是永久 Python 架构原则**。理由：Python 无法语言级保证只读，D-1 用「禁止一切写入模式」换取「静态可验证的只读性」。
  未来若引入不可变视图 / 代理对象 / 类型系统，本策略可放宽，但必须仍满足「静态可验证」。

  **FORBIDDEN 与五态的关系（第二轮裁决）：**

  ```text
  五态核心（status）= FOUND / ABSENT / UNKNOWN / UNSUPPORTED / AMBIGUOUS   ← 认识论结论
  FORBIDDEN        = visibility / authorization outcome                    ← 授权结论
                     FORBIDDEN ≠ UNKNOWN ≠ ABSENT；FORBIDDEN ∉ 五态核心
  ```

  **D-1 的 5 项架构侧修正（第一轮，已落实）：**

  1. **World Fact 定义扩宽**（`D1-DEC-1`）：不再等同「必须躺在 `main.data` dict 里」；来源含 `main.data` 直接存储 / 明确定义的世界时钟 / 既定确定性规则的只读投影；强制区分 `FACT` / `DERIVED` / `CACHE` / `HISTORY`
  2. **删除「注入只读引用」措辞**（`D1-DEC-3`）：改为「Query 接收调用方注入的 **World 数据视图**」；追加「不得保存 `data` 引用」「返回值不得暴露内部可变引用」；并明确 **只读不是语言级保证**
  3. **新增高频限制硬条款**（`D1-DEC-5`）：O(buildings × rooms) 反查**禁止**接入任何 scheduler / tick / polling loop
  4. **`Q-U3` 改为有限支持**：`get_agents_in_building` 属 **`DERIVED`**，**不是** `UNSUPPORTED`；无法解析者单独返回 `UNKNOWN`，不得假装不存在
  5. **requester / visibility 最小边界**：D-1 只实现白名单 5 项，**禁止**建立完整 Visibility Matrix

  **另新增反模式条款**：**禁止把 World Query 做成「万能世界 API」**（route / planning / selection / ranking / recommendation 类接口一律拒绝）。

  **D-0 / D-1 架构测试真实结果（不再有 NOT RUN）：**

  ```text
  === D-0 ===
  python docs/test_d0_world_activity_capability.py
  Ran 54 tests … OK

  === D-1（门 OPEN 后的当前结果）===
  python docs/test_d1_world_query.py
  GATE STATE      : OPEN (implementation authorized)
  d1 impl modules : 1
  Ran 51 tests … OK   (skipped=1 —— test_ta2 仅门关闭时适用)

  === D-1（门 CLOSED 阶段的历史结果）===
  GATE STATE      : CLOSED (implementation not authorized)
  Ran 49 tests … OK

  ※ 49 → 51 的原因：门打开后 T-A 由「断言实现不存在」切换为
     「断言实现确实存在」，入口组由 6 项变为 7 项（新增 test_ta0），
     且 test_ta2 转为 skipped。属**预期变化**，非测试被弱化。
  ```

  **执行环境：** 用户本机（Windows，`python` 直接可运行；测试**只依赖标准库**，无需 pip 安装任何依赖）。

  **执行能力说明（重要）：** DS 侧 Shell **无法执行任何子进程**
  （`pwsh` / `cmd` 均以 `exit 3221225794` / `0xC0000142, STATUS_DLL_INIT_FAILED` 失败，
  连 `cmd /c ver` 与 `Write-Output` 都失败 —— 与 Python 是否存在无关）。
  **因此 DS 不能自行运行测试**，测试执行由用户完成、结果回贴。

  **首次真实运行的价值（必须记录）：** 两轮真实运行共暴露 **6 处缺陷**，
  **全部位于测试/文档层，无一在生产架构中**。其中一处为**关键缺陷**：
  门状态判定把「`D1G-3-SATISFIED` 当前不存在」这句**否定说明**误读为开门标记，
  导致 `GATE STATE: OPEN` 误报。**若未真实运行，该缺陷会潜伏到实现阶段才爆发。**

  **由该经验固化的 Contract 规则：** `D1G-16` ～ `D1G-20`（见 Contract §5D.16.2）。

  > 职责划分（已冻结）：**DS 不负责修环境**；测试执行由用户提供。
  > 在获得真实测试结果之前，DS **不得声称「代码看起来正确」**。

  **D-1 涉及文件：** `docs/D1_WORLD_QUERY_PREFLIGHT.md`、`docs/V3.1_ARCHITECTURE_CONTRACT.md`（§5D）、`docs/test_d1_world_query.py`、`docs/PROJECT_V3.1_MASTER.md`（本文件）。

  **D-0 / D-1 Preflight 阶段生产代码修改：0。** 只产出文档与边界测试，不实现任何功能。

  **D-0 裁决要点（详见 `docs/D0_ARCHITECTURE_DECISIONS.md` 与 Contract §5C）：**

  - `main.data` 仍是唯一 World **存储位置**；但明确「唯一存储位置 ≠ 事实治理」（D0G-2）
  - Activity = 未来唯一正式「持续世界过程」抽象；现有 18 类旧活动字段正式定义为 **Legacy Activity State / Legacy Projection**（只登记，不修改）
  - **只有 `agent.Event` 是正式 Domain Event**；`enqueue_event` = Legacy Memory ingestion；SSE = Presentation / Transport Notification
  - **不删除 `execute_action`**；但**禁止 Agent Core 继续新增对它的直接依赖**；它暂时作为 **Legacy Execution Adapter** 存活
  - Memory Runtime = **业务功能关闭状态**（非「模块不存在」），不进入 D 阶段任何依赖
  - World Tick 可靠性缺陷（`D0-030` / `D0-031`）登记为 **D-3 前置 Blocker**，D-0 不修
  - 45 项发现按 **A/B/C/D/E 类**分层，**禁止一次性全部修复**
  - 事实基线 = **当前代码 + `D0_CONFLICT_AUDIT.md`**；`V3.1_GLOBAL_ARCHITECTURE_INVENTORY.md` 不再作为当前事实依据
  - A/B/C 已冻结 Contract **不需要重写**

  **D-0 涉及文件：** `docs/D0_CONFLICT_AUDIT.md`（新增）、`docs/D0_ARCHITECTURE_DECISIONS.md`（新增）、`docs/V3.1_ARCHITECTURE_CONTRACT.md`（§5C 增补）、`docs/test_d0_world_activity_capability.py`（新增）、`docs/PROJECT_V3.1_MASTER.md`（本文件）。

  **D-1 涉及文件：** `docs/D1_WORLD_QUERY_PREFLIGHT.md`、`docs/V3.1_ARCHITECTURE_CONTRACT.md`（§5D 增补）、`docs/test_d1_world_query.py`、`docs/PROJECT_V3.1_MASTER.md`（本文件）。

  **目录整理说明（DS 已适配）：** `PROJECT_V3.1_MASTER.md` 与 `V3.1_PRODUCT_GUIDE.md` 已迁入 `docs/`。
  `docs/test_d0_world_activity_capability.py` 原以 `parent.parent` 推导仓库根，会因搬移而误判为 `docs/`。
  **已修复为「标记探测」**（向上寻找同时含 `main.py` + `agent/` + `ext/` 的目录），并新增 `T11.3` / `T11.4` 两项断言防止再次发生。
  D-1 测试（`docs/test_d1_world_query.py`）同样采用标记探测。上述修复**未改动任何生产代码**。

  **下一步：** 等待架构侧审核 **D-1 Contract Change（§5D）** 与 **D-1 Architecture Tests**。
  **D-1 Implementation 在架构测试实际通过前禁止开始。**

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

## 13. Chat History Infrastructure / 聊天历史基础设施

13.1 职责边界
13.2 Server Chat Store
13.3 History Pagination
13.4 Device Local Cache
13.5 Search
13.6 Chat History 与 Memory 的边界
13.7 Multi-world 数据边界
13.8 当前实现状态

### 13.6 chat History 与 Memory不同
Chat History
= 用户可查看的完整历史

Memory
= AI 从历史中形成的少量长期记忆

Context
= AI 当前一次思考需要的相关信息

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
Chat History 是外部历史资源，
不是 Context 的直接输入。

Chat History
    ↓
History Retrieval
    ↓
Memory / Relevant Recall
    ↓
Long-term Provider
    ↓
AgentContext

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

**B5 阶段状态**：
- ✅ B5-0 Context Contract Decision（ACCEPTED）
- ✅ B5-1 Contract Change（CC-20260926-01，ACCEPTED）
- ✅ B5-2 Runtime Connection（ACCEPTED）
- ✅ B5-3 Tests（ACCEPTED）
- ✅ B5-4 PROJECT Update（ACCEPTED）

**V3.1 唯一正式 Context 数据链（B5-1 冻结，B5-2 落地，B5-3 验证）**：

```text
Event
  ↓
RECEIVE
  ↓
PERCEIVE
  ↓
WAKE_DECISION
  ↓
build_context(event, now_ts=None)
  ↓
ContextAssembler.assemble(...)
  ↓
AgentContext
  ↓
THINK（仍为 Stub）
```
**B5-1 / B5-2 冻结的关键契约**：

- V3.1 正式 Context 标准 = `AgentContext`（`agent/context.py`）。
- `ContextLayers` = deprecated compatibility stub：
  - 保留、不删除、不改名、不别名化；
  - 新 V3.1 链不再引用。
- Runtime 正式接口：
  - `build_context(event: Event, now_ts: Optional[float] = None) -> AgentContext`
  - `think(context: AgentContext) -> Optional[str]`
- 数据来源冻结：
  - `ai_name` = `self.ai_name`
  - `owner` = `self.get_state().owner`
  - `data` = `self._data`
  - `now_ts` = 调用方注入，缺省由 `ContextAssembler` 使用当前时间
  - `agent_state_dict` = `self.get_state().to_dict()`
  - `recall_query` = 当前固定 `None`

**B5 之后仍然保持不变的边界**：

- `LongTermProvider` = stub，返回 `[]`。
- Memory Runtime 未启用；`ext_memory` / `ext_mem` 未修复、未修改。
- `decision_constraints` = `None`。
- `think()` 仍为 Stub，未调用 LLM。
- 未实现 Goal / Motivation / Commitment / Activity / World Query / Scheduler / Brain / Prompt Adapter。
- 未接 LLM / Decision / Action。
- `ext_ai.build_ai_context()` 未接入 V3.1 正式链；旧路径保持独立。
- 未产生"双 Context"。

**B5 阶段涉及文件**（不含本阶段修改的 PROJECT）：

- B5-1：`docs/V3.1_ARCHITECTURE_CONTRACT.md`（+ `PROJECT_V3.1_MASTER.md`）
- B5-2：`agent/runtime.py`（Commit `525973ae6ee00c02bbc43a608c6c27cb15b62ebb`）
- B5-3：`docs/test_b5_runtime_context.py`（新增）
- B5-4：`PROJECT_V3.1_MASTER.md`（本阶段）

**C-2 阶段状态**：
- ✅ C-0 Goal / Motivation / Commitment / Intent Contract Preflight 通过
- ✅ C-1 Contract Change（CC-20260927-01）通过
- ✅ C-2 Preflight 通过
- ✅ C-2 Contract Change（CC-20260927-02）通过
- ✅ C-2 Implementation 通过
- ✅ C-2 Runtime Working-State Contract Patch Preflight 通过
- ✅ C-2 Runtime Working-State Contract Patch（CC-20260928-03）通过
- ✅ C-2 Implementation Patch（Runtime Holder + Hardening）通过

**C-2 Implementation 交付物**：

| 文件 | 类型 | 内容 |
|------|------|------|
| `agent/goal.py` | 新增 | Goal dataclass + `create_goal()` + `transition_goal()` |
| `agent/commitment.py` | 新增 | Commitment dataclass + `create_commitment()` + `transition_commitment()` |
| `agent/motivation.py` | 新增 | `MotivationSummary` + `compute_motivation()` 纯函数 |
| `agent/intent.py` | 新增 | `Intent` / `IntentSet` + `make_intent()` + `make_empty_intent_set()` |
| `agent/runtime.py` | 修改 | `think() -> IntentSet`；Runtime holder（`_goals` / `_commitments`）+ 8 个 holder 方法（hardening） |
| `docs/test_c2_goal_commitment.py` | 新增 | T1 ～ T15 + 附加 |
| `docs/test_c2_runtime_holder.py` | 新增 | H1 ～ H17（含 hardening H14 ～ H17） |

**C-3 阶段状态**：
- ✅ C-3 Tests Preflight 通过
- ✅ C-3 Tests Implementation 完成（等待架构审核）

**C-3 Tests Implementation 交付物**：

| 文件 | 类型 | 内容 |
|------|------|------|
| `docs/test_c3_contract_structure.py` | 新增 | T-A Contract Structure + B11 + C9 + C11 + D4 + D11 + F7 |
| `docs/test_c3_boundary.py` | 新增 | T-E Runtime / SOT / Boundary（E1 ～ E11） |

**C-3 覆盖缺口**：C-3 Preflight 报告的 12 项缺口（G1 ～ G12）**全部闭合**。

**6 组测试结果**：

| 测试文件 | 结果 |
|---------|------|
| `docs/test_c3_contract_structure.py` | ✅ 全部通过 |
| `docs/test_c3_boundary.py` | ✅ 全部通过 |
| `docs/test_c2_runtime_holder.py` | ✅ 全部通过（H1 ～ H17） |
| `docs/test_c2_goal_commitment.py` | ✅ 全部通过 |
| `docs/test_b3_context_assembler.py` | ✅ 全部通过 |
| `docs/test_b5_runtime_context.py` | ✅ 全部通过 |

**C-2 / C-3 完成后仍保持的边界**：

- `think()` 仍为 Stub，返回 `IntentSet(candidates=[])`。
- 未实现 THINK 内部逻辑。
- 未接 LLM / Decision / Action。
- 未启用 Memory Runtime。
- 未创建数据库 / 持久化文件。
- `LongTermProvider` 仍为 stub，返回 `[]`。
- `decision_constraints` = `None`。
- Goal / Commitment 是 Runtime-only working state，**非 Source of Truth**。
- `main.data` 仍是唯一 World / Application SOT。
- 重启会丢失 Goal / Commitment，是 C-2 已知限制。
- 未实现自动 Goal / Commitment 创建。
- 未实现自动 transition / 优先级 / 冲突解决。
- 未实现 AI↔AI Commitment negotiation。
- 未产生"双 Context"。
- `ContextLayers` 保留为 deprecated compatibility stub。

**C-2 / C-3 未冻结项**（必须留待后续 Contract Change）：

- Goal / Commitment 持久化方案（JSON / SQLite / 内存 + 快照 / 其他）。
- Goal priority / conflict algorithm。
- Decision 数据结构与接口。
- Activity 生命周期。
- World Query 接口。
- Scheduler 接口。
- AI↔AI Commitment negotiation。
- 用户 Goal vs AI Goal 自动权衡。
- 真实 THINK 的 candidate 数量要求。
- Goal source 自动检测。
- Goal creation 自动机制。
- Motivation 最终算法。
- Motivation 完整输入范围。

下一阶段方向：

不直接进入 Brain / THINK 实现。

下一阶段必须先进行 Phase C 架构设计 / Preflight（Goal / Motivation / Commitment / Activity / World Query / Scheduler 的边界定义），等待架构审核通过后再考虑代码。

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

Chat History 必须具备 world_id / room_id 隔离边界。

未来消息资源至少逻辑上属于：

universe_id
→ world_id
→ instance_id（可选）
→ region_id
→ building_id
→ room_id
→ message_id

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

### 20.1 当前所处阶段

- Phase A（Global Architecture Inventory）：✅ 已完成
- Phase B（V3.1 Context Foundation）：✅ 已完成（含 B5-4 归档）
- Phase C（Motivation / Goal / Commitment / Intent）：✅ 已完成（含 C-4 归档）
- Phase D（World Query / Activity / Capability）：🟢 **D-0 SEALED；D-1 SEALED（54 + 51 + 70 三项真实通过）；D-2 READY / NEXT**
- Phase E（Memory Recall）：⏳ 未开始
- Phase F（Brain / Decision）：⏳ 未开始

---

### 20.2 Phase A — Global Architecture Inventory（已完成）

建立整个 TEST 仓库的：

- 文件地图
- import / call 关系
- data 字段读写关系
- Timer / background loop
- API 路由
- Event / Memory / SSE 链
- 前端依赖
- 核心功能回归矩阵

产出：`docs/V3.1_GLOBAL_ARCHITECTURE_INVENTORY.md`

---

### 20.3 Phase B — V3.1 Context Foundation（已完成）

**B1 ～ B4 阶段总览：**

| 阶段 | 内容 | 状态 |
|------|------|------|
| B1 | Context Data Contract | ✅ |
| B2-1 | StableCoreProvider | ✅ |
| B2-2 | DynamicWorldProvider | ✅ |
| B2-3 | RecentProvider | ✅ |
| B2-4 | LongTermProvider Stub | ✅ |
| B3 | ContextAssembler | ✅ |
| B4 | Runtime Connection Preflight | ✅ |

**B5 阶段总览：**

| 阶段 | 内容 | 状态 |
|------|------|------|
| B5-0 | Context Contract Decision | ✅ |
| B5-1 | Contract Change（CC-20260926-01） | ✅ |
| B5-2 | Runtime Connection | ✅ |
| B5-3 | Runtime Context Connection Tests | ✅ |
| B5-4 | PROJECT Update | ✅ |

**Phase B 已完成内容：**

1. Context Data Contract ✅
2. StableCoreProvider ✅
3. DynamicWorldProvider ✅
4. RecentProvider ✅
5. LongTermProvider（Stub）✅
6. ContextAssembler ✅
7. 接入 `agent/runtime.build_context()` ✅（B5-2）
8. Context Connection 测试 ✅（B5-3）
9. PROJECT 归档 ✅（B5-4）

**Phase B 冻结的正式 Context 链：**

```text
Event
  ↓
RECEIVE
  ↓
PERCEIVE
  ↓
WAKE_DECISION
  ↓
build_context(event, now_ts=None)
  ↓
ContextAssembler.assemble(...)
  ↓
AgentContext
  ↓
THINK（仍为 Stub）
```

**Phase B 完成后仍保持的边界：**

- `LongTermProvider` = stub，返回 `[]`
- Memory Runtime 未启用
- `decision_constraints` = `None`
- THINK 未实现
- 未接 LLM / Decision / Action
- `ext_ai.build_ai_context()` 未接入正式链
- 未产生"双 Context"
- `ContextLayers` 保留为 deprecated compatibility stub

**Home / Frontend Interaction Layer：**

- 属于产品表现层建设方向。
- 不应提前打断 Phase B。
- 在 Agent Core 语义冻结后，再进行 Home Shell 的前端架构设计与实现。

---

### 20.4 Phase C — Motivation / Goal / Commitment / Intent（已完成）

**目标：**
让自主生活、移动、约会开始具有连续原因。

**涉及边界（必须先做 Preflight）：**

- Goal
- Motivation
- Commitment
- Activity Lifecycle
- World Query
- Scheduler

**约束：**

- Phase C Preflight 审核通过前，**禁止任何代码修改**。
- 不允许直接进入 Brain / THINK 实现。
- 不允许绕过 Contract 变更流程。
- 不允许在 Preflight 阶段接入 LLM。

**Preflight 必须回答：**

1. Goal 的数据结构、来源、生命周期。
2. Motivation 如何从 Goal + State + Relationship + Memory 推导。
3. Commitment 如何从 date / meeting / promise 语义中提取。
4. Activity Lifecycle 如何从现有 `work_sessions` / `dates` / `ai_shop_state` / `instances` 兼容。
5. World Query 如何基于现有 `buildings` / `rooms` / `npcs` 提供查询接口。
6. Scheduler 如何逐步替代散落 `threading.Timer` 与后台循环。
7. 每一项的 Contract 边界与冻结时机。

**Phase C 子阶段状态**：

| 阶段 | 内容 | 状态 |
|------|------|------|
| C-0 | Goal / Motivation / Commitment / Intent Contract Preflight | ✅ |
| C-1 | Contract Change（CC-20260927-01） | ✅ |
| C-2 | Preflight | ✅ |
| C-2 | Contract Change（CC-20260927-02） | ✅ |
| C-2 | Implementation | ✅ |
| C-2 | Runtime Working-State Contract Patch Preflight | ✅ |
| C-2 | Runtime Working-State Contract Patch（CC-20260928-03） | ✅ |
| C-2 | Implementation Patch（Runtime Holder + Hardening） | ✅ |
| C-3 | Tests Preflight | ✅ |
| C-3 | Tests Implementation | ✅ |
| C-4 | PROJECT Update | ✅ |

**Phase C 涉及的正式 Commit**：

- C-2 Contract Change（CC-20260927-02）：`docs/V3.1_ARCHITECTURE_CONTRACT.md` 更新
- C-2 Implementation：
  - `033ecccfcb3efd90351b5baec6c87cde31a6e737`
  - `6e0963765983c7bfcff734505279b481edc99faf`
- C-2 Runtime Working-State Contract Patch（CC-20260928-03）：`docs/V3.1_ARCHITECTURE_CONTRACT.md` 更新
- C-2 Runtime Holder：`c76391e7fb0406c1aba5d50989363dd583877565`
- C-2 Runtime Holder Self-Test：`54d510250c91ef56fa267ae099c7826609e2cca0`
- C-3 Tests Implementation：**待提交后填写**

**Phase C 完成后进入下一阶段的前置条件**：

- 必须先进行下一阶段的 Preflight。
- 未通过 Preflight 前，禁止修改任何 `.py`。
- 不允许跳过 Contract Change 直接编码。

---

### 20.5 Phase D — World Query / Activity / Capability（D-0 SEALED · **D-1 SEALED** · D-2 READY / NEXT）

让 AI 能查询真实世界、保持活动连续性，并建立 Capability 边界。

- 依赖 Phase C 完成的 Goal / Motivation / Commitment。
- 不引入新数据源；基于现有 `main.data` 结构。
- 必须先完成 Preflight。
- 当前状态：🟢 **D-0 SEALED；D-1 SEALED（54 + 51 + 70 三项真实通过）；D-2 READY / NEXT。**

**Phase D 子阶段状态：**

| 阶段 | 内容 | 状态 |
|------|------|------|
| D-0 | World / Activity / Capability Preflight | ✅ 已完成 |
| D-0 | Conflict Audit（45 项发现） | ✅ ACCEPTED |
| D-0 | Architecture Decisions（D0-DEC-1 ～ 8） | ✅ ACCEPTED |
| D-0 | Contract Change（CC-20260930-04，§5C） | ✅ ACCEPTED |
| D-0 | Architecture Tests | ✅ **RAN / PASSED**（**Ran 54 tests … OK**，真实运行） |
| D-0 | **Seal** | ✅ **SEALED** |
| **D-1** | **World Query Preflight** | ✅ **APPROVED**（`docs/D1_WORLD_QUERY_PREFLIGHT.md`） |
| **D-1** | **Contract §5D（CC-20260930-05）** | ✅ **APPROVED** |
  | **D-1** | **Architecture Tests** | ✅ **RAN / PASSED**（`docs/test_d1_world_query.py`：**Ran 51 tests … OK**，`GATE STATE: OPEN`，真实运行）<br>※ 门关闭阶段历史记录为 49 tests |
| **D-1** | **Gate Correction（T-A / T-B 生命周期 + 静态策略定位 + FORBIDDEN/五态分离）** | ✅ **APPROVED** |
| **D-1** | **Implementation** | 🔧 **HARDENING APPLIED**（D1-H1 ～ H4）—— `agent/world_query.py` |
| **D-1** | **Post-Implementation Gate（T-B）** | ✅ **RAN / PASSED**（静态边界，**Ran 51 tests … OK**） |
| **D-1** | **Behavior Tests（D1-H4）** | ✅ **RAN / PASSED**（`docs/test_d1_world_query_behavior.py`：**Ran 70 tests … OK**，真实运行） |
| **D-1** | **Implementation Review** | ✅ **APPROVED** |
| **D-1** | **SEAL** | ✅ **SEALED**（见 §20.5.2 SEAL Record） |
| **D-2** | **Preflight** | ✅ **APPROVED WITH ARCHITECTURAL CORRECTIONS** |
| **D-2** | **Contract §5E** | ✅ **APPROVED**（CC-20260930-06，含 §5E.22 D-2 阶段门） |
| **D-2** | **Architecture Tests** | ✅ **APPROVED**（SHA `a622e537…`，**Ran 53 tests … OK**）<br>门控修正后 **Ran 64 tests … OK** |
| **D-2** | **Architecture Tests SEAL** | ✅ **SEALED**（见 §20.5.3 SEAL Record） |
| **D-2** | **Gate** | 🔒 **CLOSED**（`D2G-GATE-STATUS: CLOSED` / marker `null`） |
| **D-2** | **Implementation** | 🔴 **NOT AUTHORIZED**（`agent/activity.py` 未创建） |
| D-3 | Location / Movement Continuity | ⛔ 未开始（前置 Blocker：World Tick 可靠性，见 Contract §5C.6） |
| D-4 | Capability / Action Port | ⛔ 未开始 |
| D-5 | Agent Decision → Capability | ⛔ 未开始 |
| D-6 | Legacy Behavior Migration | ⛔ 未开始 |

**Phase D 正式 Contract 依据：** `docs/V3.1_ARCHITECTURE_CONTRACT.md` **§5C**（CC-20260930-04）与 **§5D**（CC-20260930-05）。

---

#### 20.5.2 D-1 SEAL RECORD

```text
D-1 SEAL
================================================================
Date                      : 2026-09-30

World Query implementation: agent/world_query.py
                            （World Query Foundation，只读；
                              Dependency Injection，不 import main / ext_*）

Architecture test result  : docs/test_d1_world_query.py
                            Ran 51 tests — OK（GATE STATE: OPEN, skipped=1）

Behavior test result      : docs/test_d1_world_query_behavior.py
                            Ran 70 tests — OK

D-0 regression            : docs/test_d0_world_activity_capability.py
                            Ran 54 tests — OK

D1-H1 Private Room Auth   : PASS
                            owner / owner 的 AI → ALLOWED
                            其他 user / 其他 AI / 陌生 / 空 requester → FORBIDDEN
                            FORBIDDEN 时 value == None
                            无法归属到建筑的房间 → fail-closed（按不公开处理）

D1-H2 Visibility          : PASS
                            公开建筑 / 公开房间 → 可见
                            私人建筑 / 私人房间 → 仅授权范围可见
                            私人 AI 状态（wallet / affection / owner / dating /
                            working / following / legacy activity）→ 越权读取被拒绝

D1-H3 Deep Copy           : PASS
                            修改 QueryResult.value 后 main.data 完全不变
                            （dict / list / nested dict / nested list 全覆盖）
                            value 一律为深拷贝，不暴露 main.data 内部引用

D1-H4 Behavior Regression : PASS
                            UNKNOWN ≠ ABSENT
                            UNSUPPORTED 不猜测（7 项全部 value=None）
                            FORBIDDEN 无 value
                            反模式接口（route / choose / plan / suggest /
                            recommend / rank）继续被拒绝
                            五态核心恰好 5 项，与 outcome 正交

Product Guide review      : PASS（无产品漂移）
                            World Query 只回答「世界现在是什么」
                            AI 不是全知（requester / visibility 生效）
                            因果链未被跳过（motivation.py 将 world_query
                            列为 forbidden_inputs —— 动机层不依赖 Query）
                            无随机决策 / 随机目的地 / 随机推荐
                            Query ≠ Movement ≠ Route ≠ Destination Selection

Architecture Contract     : docs/V3.1_ARCHITECTURE_CONTRACT.md
                            §5D（CC-20260930-05）与实现一致
                            §5D.16.2 静态断言策略 / §5D.16.3 深拷贝例外 /
                            §5D.16.4 白名单实现级要求 —— 均已落实
                            规则 WQ-1 ～ WQ-118、D1G-1 ～ D1G-32 全部存在
                            未新增未冻结架构

PROJECT consistency       : PASS
                            已清除「门已开」与「门未开」并存的矛盾描述；
                            过时状态（BLOCKED / NOT RUN / 49 tests 快照）
                            已统一到当前真实状态；
                            49 → 51 的测试数量变化已解释（门开后 T-A 项数变化）

Product Guide 修改         : 无（Product Guide 未因 D-1 Seal 而修改）

生产代码变更（D-1 累计）    : 新增 agent/world_query.py（1 个新文件）
                            既有文件 0 修改
                            （main.py / ext_* / agent 其他模块 /
                              前端 / HTTP API 全部未改）

可拆卸性（Removability）    : PASS
                            world_query 在整个仓库中**零生产消费者**
                            （仅出现在模块自身、测试文件、
                              以及 motivation.py 的 forbidden_inputs 列表）
                            → 删除 world_query.py 不影响 Agent Core /
                              Context / Goal / Motivation / Intent / Activity

唯一 World SOT            : PASS
                            main.data 仍是唯一 World / Application SOT
                            world_query 不持有任何状态、缓存、索引或数据库

Remaining risks（非阻塞）  : ① DS 侧 Shell 无法执行子进程（0xC0000142）
                                → 测试执行由用户完成（流程事实，非架构风险）
                             ② 工作区不是 Git 仓库 → 无法提交 / 无法提供 SHA
                             ③ get_agent_location() 暂不受可见性限制
                                （位置属白名单 A；如需收紧须 Contract Change）
                             ④ ext_date / ext_world / ext_shop 仍直接
                                import ext_memory（D-0 已登记的 World→Memory
                                耦合，属 Phase E / D-6，非 D-1 引入）

Final decision            : D-1 SEALED
Next                      : D-2 Activity Contract（需先创建 Preflight）
================================================================
```

---

#### 20.5.3 D-2 ARCHITECTURE TESTS SEAL RECORD

```text
D-2 ARCHITECTURE TESTS SEAL
================================================================
Date                      : 2026-09-30

D-2 Preflight             : APPROVED WITH ARCHITECTURAL CORRECTIONS
                            （docs/D2_ACTIVITY_CONTRACT_PREFLIGHT.md；
                              D2-DEC-1 ～ D2-DEC-19 + 4 个 OPEN QUESTION 已关闭）

Contract §5E              : APPROVED
                            （docs/V3.1_ARCHITECTURE_CONTRACT.md §5E，
                              CC-20260930-06；含 §5E.22 D-2 阶段门）

Architecture Tests        : APPROVED
                            文件：docs/test_d2_activity_contract.py

                            ┌─ 首次真实运行（门控修正前）
                            │     Ran 53 tests … FAILED (failures=3)
                            │     test_g4 / test_g7 / test_h3
                            │     → 其中 test_g4 抓到 Contract 真实缺口
                            │       （§5E.6 未逐条列举禁止跳跃）
                            │     → 修正后 Ran 53 tests … OK
                            │
                            ├─ 架构审核通过（APPROVED）
                            │     SHA a622e5371aa25605a165b708b171a1e4445ecb25
                            │     测试结果：Ran 53 tests … OK
                            │
                            └─ 门控修正后（最终版本）
                                  Ran 64 tests … OK   ← 真实运行 ✅
                                  门控修正后测试数变化已解释（EV-17）：
                                      原 A 组 5 项 → 移除/重构
                                      新增 T-A（ta0 ～ ta7）   +8
                                      新增 T-B（tb0 ～ tb7）   +8
                                      原有 B ～ K              48
                                      合计                     64

                            四套回归（最终版本，均真实运行）：
                                docs/test_d0_world_activity_capability.py   OK
                                docs/test_d1_world_query.py                 OK
                                docs/test_d1_world_query_behavior.py        OK
                                docs/test_d2_activity_contract.py           OK

Gate                      : CLOSED
                            Contract §5E.22 结构化门状态（唯一来源）：
                                D2G-GATE-STATUS: CLOSED
                                D2G-3-MARKER: null
                            → D-2 Pre-Implementation Gate = CLOSED
                            → 已由测试真实输出确认：
                              GATE STATE      : CLOSED (implementation not authorized)
                              impl presence   : ABSENT -> ...\agent\activity.py
                              boundary scan   : 16 agent file(s) —— 实现不存在，扫整个 agent/

Activity implementation   : NOT AUTHORIZED
                            agent/activity.py = 不存在（未创建）

本次最终 SHA（架构审核通过）: a622e5371aa25605a165b708b171a1e4445ecb25

（历史链条，避免后续误读）：
    Architecture Review SHA : a622e5371aa25605a165b708b171a1e4445ecb25
                              （架构审核通过的 **测试版本**）
    D-2 Seal Commit         : c676abd28f2ef28f595491d0fa6d227ab063c4a9
                              （把 Seal 结果正式写入 PROJECT / Contract 的提交）

D-2 Implementation 授权      : ✅ AUTHORIZED
                              （依据：Architecture Review SHA a622e537 /
                                D-2 Seal Commit c676abd… / 64-64 tests OK）
                              Contract §5E.22 门状态已置为：
                                  D2G-GATE-STATUS: OPEN
                                  D2G-3-MARKER: true

----------------------------------------------------------------
本轮门控修正（架构侧 D-2 Architecture Tests Review 要求）
----------------------------------------------------------------

① implementation presence ≠ implementation authorization
   - 文件存在只说明 presence（客观事实）
   - 唯一授权依据 = Contract §5E.22 的门状态 marker
   - 规则：EG-12 / EG-13（禁止把「文件存在」当作授权条件）

② Gate 由 Contract 显式 marker 决定
   - 门状态改为结构化、可机读、单一来源：
         D2G-GATE-STATUS: CLOSED
         D2G-3-MARKER: null
   - 判定采用严格前缀匹配，说明性文本不得影响判定
   - 规则：EG-14

③ 实现存在时不得因文件存在而跳过 boundary checks
   - 移除全部「实现存在即 return」的跳过路径
   - 新增 _boundary_scan_targets()：实现存在时扫**实现文件本身**
   - 规则：EG-15 / EG-16 / EG-17
   - 新增 T-B 组 test_tb0 ～ test_tb7，
     其中 tb0 直接断言「扫描目标必须覆盖实现文件」

④ Activity Event 检查只针对 Activity implementation 本身
   - 原 test_h3 在门关闭时扫描整个 agent/，
     误命中 B5 / C-2 已存在的合法模块
     （event_adapter.py / runtime.py 对 agent.event 的依赖）
   - 修正为：仅检查 Activity 实现文件；实现不存在时本项不适用
   - 依据：EB-13 约束的是「Activity 不产生 Event」，
     而非「任何 agent 模块都不得 import agent.event」

----------------------------------------------------------------
本轮修正过程中暴露并修复的**真实缺陷**（必须记录）
----------------------------------------------------------------

缺陷 1（Contract 真实缺口，由 test_g4 发现）
    §5E.6 仅写「禁止随意跳跃」，未逐条列举被禁止的具体跳跃。
    修正：新增「禁止的跳跃」逐条列举 13 条 + 规则 EF-11 ～ EF-13。

缺陷 2（门控判定 bug，三轮才收敛）
    现象：Gate 误报 OPEN。
    真实根因：Contract §5E.22 的「定义」段写了
        implementation authorized = …肯定式标记 <标记>: true
    这句**说明标记是什么**的文字被判定读成**门已开**。
    定性：D1G-16（区分「状态构造」与「说明文本」）的教科书级复现，
          且发生在 Contract 文档自身。
    修正：门状态结构化 + 严格前缀匹配 + 说明文本去键值化；
          并新增回归断言 test_ta2_gate_status_is_structured_and_parseable。
    过程教训：
        · 第 1 轮基于**推断**修正 → 未命中根因，浪费一轮验证
        · 第 2 轮改为**读原文** → 一次定位真因
        · 第 3 轮发现「单一来源」≠「只出现一次」，
          正确语义是「所有出现必须一致」（分歧则 fail-closed）

----------------------------------------------------------------
生产代码变更
----------------------------------------------------------------
新增  agent/activity.py                    ：无（未创建）
修改  agent/state.py / motivation.py /     ：无
      context.py / world_query.py
修改  main.py / 任何 ext_*                  ：无
修改  前端 / HTTP API / Memory              ：无
进入  D-3                                   ：未进入

Final decision            : D-2 Architecture Tests = APPROVED / SEALED
Next                      : 等待架构侧审核；D-2 Implementation 仍 NOT AUTHORIZED
================================================================
```

---

#### 20.5.4 D-2 IMPLEMENTATION SEAL RECORD

```text
D-2 IMPLEMENTATION SEAL
================================================================
Date                      : 2026-09-30

D-2 Implementation Verification : APPROVED
D-2 Implementation Seal         : AUTHORIZED → SEALED

Implementation SHA        : b7a201979ab9ba26ac6b658e8ae85866702cb625
Docs SHA                  : ec40f53d619f68c8d4cb4d5aa83d0e4ce63dd38e

----------------------------------------------------------------
Immutable Boundary（架构侧裁决 A 的闭合项）
----------------------------------------------------------------
    input isolation          : PASS
        调用方输入 → _deep_freeze()（构造期递归冻结）
        role_map / metadata 的嵌套 dict → MappingProxyType
        list → tuple
        → 调用方事后修改自己传入的 dict 不影响 Activity

    output isolation         : PASS
        内部真相 → _copy_for_read() → 独立快照
        已接入**全部**返回 Activity 的路径：
            create_activity / get / require / list_*（经 list_all）
            / primary_activity / bound_activities / transition().activity

    deep nested isolation    : PASS
        深层结构（dict → dict → list）同样不穿透

    修复前的缺陷（已闭合）：
        @dataclass(frozen=True) 只冻结属性重绑定，不冻结容器内容 →
        三层穿透（metadata / role_map / 嵌套 list）已由行为测试证实
        依赖：PEP 557（frozen dataclass 非真正不可变）

----------------------------------------------------------------
Regression（五套全部真实运行 —— EV-16 / EV-18 / EV-19）
----------------------------------------------------------------
    D-0 architecture          54/54  PASS
    D-1 architecture          51/51  PASS
    D-1 behavior              70/70  PASS
    D-2 architecture          64/64  PASS
    D-2 behavior              74/74  PASS

    注：五套均为**真实运行**结果，非静态声称。
        DS 侧 Shell 不可执行（0xC0000142），执行由架构侧完成。

----------------------------------------------------------------
Behavior Coverage（docs/test_d2_activity_behavior.py = 74 项）
----------------------------------------------------------------
    A  Activity 创建与字段校验              11
    B  lifecycle（合法转换/非法跳跃/终态/EP-5） 12
    C  primary / secondary binding             9
    D  Registry 唯一真相与容器隔离             8
    E  Immutable Boundary（行为证明）          15
    F  不产生 Event / 不写 World / 不持久化 /
       不依赖 scheduler / 不接 Motivation      9
    G  Activity Domain Object 语义             6
    H  环境能力                                4
    ----------------------------------------------
    TOTAL                                     74

    E 组 15 项（含架构侧指定的两条反向测试）：
        e1  frozen 阻止属性重绑定
        e2  转换不分叉真相
        e3  get() 不允许嵌套 metadata 穿透          ← 架构侧指定
        e4  get() 不允许 role_map 穿透              ← 架构侧指定
        e5  深层嵌套（dict→dict→list）不穿透
        e6  require() 路径不穿透
        e7  全部 list_* 路径不穿透
        e8  primary_activity() / bound_activities() 不穿透
        e9  transition().activity 不穿透
        e10 create_activity() 返回值不穿透
        e11 输入 metadata 不产生外部别名
        e12 输入 role_map 不产生外部别名
        e13 两次读取互相独立
        e14 绕过 Registry 直接构造也被构造期冻结
        e15 Activity 仍是 frozen dataclass

----------------------------------------------------------------
Gate
----------------------------------------------------------------
    Contract §5E.22 门状态块（唯一来源）：
        D2G-GATE-STATUS: OPEN
        D2G-3-MARKER: true

----------------------------------------------------------------
架构语义确认（架构侧明确认可）
----------------------------------------------------------------
    EC-4 的准确含义：
        「同一 activity_id 只有一个 **Registry truth**」
        ≠ 「所有调用方必须拿到同一个 Python object identity」

    因此把 `assertIs(a, b)` 改为
        「identity 一致 + 读取快照彼此隔离 + 快照不能修改 Registry truth」
    是正确的架构解释。
    否则会强迫实现暴露内部引用，重新制造刚修掉的 immutable-boundary 漏洞。

----------------------------------------------------------------
NON-BLOCKING IMPLEMENTATION NOTE（架构侧 Seal 审核记录）
----------------------------------------------------------------
    `_copy_for_read()` 使用 `replace()`，会再次触发
    `Activity.__post_init__()` → `_deep_freeze()`，
    因此对外快照的**实际**形态是：

        内部 truth       = frozen
        外部 snapshot    = frozen + 独立

    而早期注释曾写作「外部 snapshot = **mutable** + 独立」，与行为不符。

    结论：
        * **不构成 D-2 Seal 阻塞项**
          —— 架构真正要求的是「外部不能穿透修改内部 Truth」，
             74 项行为测试已证明。
        * **不需要 Contract Change**
        * 本次 Seal **已顺带修正文档**，使描述与行为一致：
              _deep_thaw()      补充「独立副本 / 可变只是中间态」
              _copy_for_read()  改为「frozen 独立快照」并记录该 note
              Activity 类文档   改为「内部 frozen；对外 frozen + 独立」
              to_dict()         明确「不经过 __post_init__，故为可变副本」
              测试 test_d6 文档 同步修正
        * 隔离的真正来源是「**新构造 + 零共享引用**」，
          与快照可变与否无关。

----------------------------------------------------------------
D-2 边界未扩张（确认）
----------------------------------------------------------------
    ❌ Event          ❌ World 写入     ❌ main.data
    ❌ persistence    ❌ scheduler      ❌ Motivation
    ❌ Capability     ❌ Movement       ❌ Legacy 反向写
    ❌ AgentState     ❌ Context        ❌ World Query
    ❌ D-3

    定性：本轮属于 **D-2 内部实现硬化**，不是架构范围扩张。

----------------------------------------------------------------
生产代码变更（D-2 累计）
----------------------------------------------------------------
    新增  agent/activity.py
          —— Activity Domain Object（frozen + 双向隔离）
          —— Runtime-scoped Activity Registry（唯一管理入口）
          —— lifecycle（7 状态 / 冻结转换表 / 终态不可逆）
          —— actor / participant / role
          —— primary / secondary binding（binding ≠ ownership）
          —— 基础查询 / 管理能力

    既有文件修改：0
        main.py / ext_* / agent 其他模块 /
        前端 / HTTP API / Memory 全部未改

----------------------------------------------------------------
Final decision            : D-2 IMPLEMENTATION SEALED
Next                      : 等待架构侧审核；D-3 仍 BLOCKED
================================================================
```


---

#### 20.5.1 D-1 阶段门记录（Pre-Implementation Gate → 已开放；T-B → 已通过）

**门状态标记（历史 → 现状）：**

```text
【过去 / D-1 实现前】
D1G-3-SATISFIED 不存在
→ Pre-Implementation Gate = CLOSED

【现在 / 架构侧已授权】
D1G-3-SATISFIED: true   （已写入 Contract §5D.16）
→ Pre-Implementation Gate = OPEN
→ D-1 Implementation 已完成
→ T-B Gate 已运行并通过
```

**测试现状：**

```text
D-0 Architecture Tests   ✅ Ran 54 tests … OK
D-1 Architecture Tests   ✅ Ran 51 tests … OK   (GATE STATE: OPEN, skipped=1 属预期)
```

> **两套架构测试均已真实通过。** 不存在「未运行」或「测试失败」的阻塞项。

**当前唯一剩余事项：**

```text
D-1 Seal —— 待架构侧审核批准
```

**当前仍然禁止：**

```text
禁止进入 D-2
```

**另需注意（环境限制，不影响本阶段）：**

```text
DS 侧 Shell 无法执行任何子进程：
    exit code = 0xC0000142 (STATUS_DLL_INIT_FAILED)
    连 cmd /c ver 与 Write-Output 都失败 → 与 Python 是否存在无关

工作区不是 Git 仓库（无 .git）→ DS 无法提交 / 无法提供 commit SHA
```

**D-1 门状态（已完成使命）：**

```text
Pre-Implementation Gate = 已由架构侧打开（授权 D-1 Implementation）
Post-Implementation Gate（T-B） = 已运行并通过

D-1 Implementation 与 T-B Gate 均已完成。
```

**D-1 交付与验证：**

```text
交付：agent/world_query.py（只读 World Query Foundation）

验证（真实运行）：
    D-0 Architecture Tests   Ran 54 tests … OK
    D-1 Architecture Tests   Ran 51 tests … OK（GATE STATE: OPEN, skipped=1 属预期）
```

**当前仍然禁止：**

```text
禁止进入 D-2
```

**下一步（等待架构侧）：**

```text
① 架构侧审核 D-1 Implementation 与 T-B Gate 结果
② 决定是否 D-1 Seal
③ 只有 D-1 Seal 后，才讨论 D-2（Activity Contract）
```

> 职责划分：**DS 不负责修环境**；测试执行与门控授权由架构侧 / 用户负责。

---

**D-0 / D-1 Preflight 阶段生产代码修改：0**（D-0 / D-1 Preflight）。
**D-1 Implementation 生产代码修改：新增 `agent/world_query.py`（1 个新文件，未改动任何既有文件）。**

---

### 20.6 Phase E — Memory Recall（未开始）

在已有历史基础上一次性整理 / 生成历史记忆，再启用召回。

- 依赖 Phase B 的 Context 分层。
- 依赖 Phase C / D 的语义稳定。
- 不修复、不直接启用旧 `ext_memory`。
- 必须先完成 Preflight。
- 当前状态：⏳ 未开始（依赖 Phase C 完成）。

---

### 20.7 Phase F — Brain / Decision（最后一步）

最后把 LLM Think / Decision 接到统一 Runtime。

- 依赖 Phase B / C / D / E 全部完成。
- THINK 才从 Stub 变为真实实现。
- 必须先完成 Preflight。
- 当前状态：⏳ 未开始（依赖 Phase C 完成）。
- 在此之前 `think()` 一律保持 Stub。

---

### 20.8 通用阶段推进规则

1. 每个 Phase 开始前，必须先做 Preflight。
2. Preflight 通过后，才可进入 Contract Change。
3. Contract Change 通过后，才可进入编码。
4. 编码完成后必须回归测试。
5. 测试通过后更新 PROJECT。
6. 每个阶段完成后停止，等待架构审核。
7. 不允许跨阶段并行编码。
8. 不允许绕过 Contract 直接修改 Runtime / Provider / Assembler。
9. 每个子阶段（C-0 / C-1 / C-2 ...）都必须独立审核。
10. Preflight 阶段不允许写代码；Contract Change 阶段只允许改 Contract；编码阶段才允许改 `.py`。

---

## V3.1-INFRA 架构规划

Android 手机作为 Linkong 本地主服务器的长期方案
手机负责运行 Python Linkong、世界状态和后台 AI 调度
Zeabur 保留作为云端备用/灾备节点
GitHub 负责代码版本，不作为实时世界状态数据库
未来设计 Local Server / Cloud Backup / Health Check / Restore / Failover
Android Server Prototype
24 小时运行、自动启动、自动重启
Cloudflare Tunnel 公网访问
手机 → 云端增量备份
新手机恢复世界
最终目标：一部 Android 手机可以承载一个独立 Linkong 世界

当前状态：PLANNED / 未实施

不冻结具体硬件型号、Termux方案、备份协议、Cloudflare配置和故障切换实现。

这些留到 INFRA-0 设计阶段再正式确定。

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

### 22.7 已知不一致 / 未挂载
#	位置	问题
1	ext_ai.build_ai_context	调用 m.get_date_context，但未找到任何挂载 → 恒返回 ""
2	ext_ai.drive_ai	调用 m.on_ai_action，但未找到定义 → 死代码
3	ext_admin.generate_impression	存 key 用 normalize_name(ai_name)，ext_ai 读 key 优先原始名 → key 不一致
### 22.8 SNS 当前不存在
当前系统：无朋友圈 / 无评论 / 无点赞 / 无动态。

唯一接近：sms（短信）+ messages（房间/群聊）+ notifications（通知中心）。

SNS 属于未来产品能力，Communication Layer（§11）已为它预留语义位置。

### 22.9 Event 真空区
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

### 22.11 B5 阶段事实（2026-09-27）

- V3.1 正式 Context 链已从设计层进入 Runtime。
- `build_context()` 已返回 `AgentContext`，并由 `ContextAssembler` 组装。
- `think()` 签名已更新为 `think(context: AgentContext) -> Optional[str]`，行为仍为 Stub。
- `ContextLayers` 保留为 deprecated compatibility stub。
- `LongTermProvider` 仍为 stub，返回 `[]`。
- Memory Runtime 未启用。
- `decision_constraints` 仍为 `None`。
- 未接入 `ext_ai.build_ai_context()`。
- 未产生"双 Context"。
- 未调用 LLM / 网络。
- `main.data` 未被 Runtime 直接写。
- B5-2 的 `agent/runtime.py` 修改 Commit SHA：`525973ae6ee00c02bbc43a608c6c27cb15b62ebb`。

### 22.12 C-0 阶段事实（2026-09-27）

- C-0 Goal / Motivation / Commitment / Intent Contract Preflight 已完成。
- 新增 `docs/C0_GOAL_MOTIVATION_COMMITMENT_INTENT_PREFLIGHT.md`。
- Goal / Commitment 生命周期与状态机已冻结（草案）。
- Motivation 明确为计算结果，**不需持久化**。
- Intent 明确为结构化、可审计、可多候选。
- Goal / Commitment **最终持久化位置暂不冻结**（待 C-1）。
- Goal / Commitment **不写入 `main.data`**。
- 未修改任何 `.py`。
- 未修改 Architecture Contract。
- 未接 LLM。
- 未启用 Memory Runtime。
- 未进入 B7。
- 未进入 C-1 编码。

### 22.13 Chat History 当前真实状态
当前 /api/messages 只返回有限历史窗口
当前前端存在 localStorage 聊天缓存
当前缓存约保留最近 400 条
当前服务器 data["messages"][room] 保存聊天历史
当前世界数据仍集中在 data.json
当前没有真正的游标分页
当前没有完整历史搜索 API
当前没有 IndexedDB 聊天归档
当前没有“搜索结果 → 定位原消息”的完整链路

### 22.14 C-2 阶段事实（2026-09-30）

- C-2 Goal / Commitment / Motivation / Intent Implementation 已完成并 ACCEPTED。
- Runtime Working-State Contract Patch（CC-20260928-03）已 ACCEPTED。
- Runtime Holder + Hardening 已完成。
- `agent/goal.py` / `agent/commitment.py` / `agent/motivation.py` / `agent/intent.py` 已落地。
- `agent/runtime.py` 的 `think()` 迁移为 `-> IntentSet`。
- `agent/runtime.py` 新增 Runtime holder（`_goals` / `_commitments`）+ 8 个 holder 方法。
- Holder hardening：所有 get / list 返回 `deepcopy`，add / replace 存储 `deepcopy`。
- `docs/test_c2_goal_commitment.py` / `docs/test_c2_runtime_holder.py` 已落地，全部通过。
- C-2 涉及 Commit SHA：
  - `033ecccfcb3efd90351b5baec6c87cde31a6e737`
  - `6e0963765983c7bfcff734505279b481edc99faf`
  - `c76391e7fb0406c1aba5d50989363dd583877565`
  - `54d510250c91ef56fa267ae099c7826609e2cca0`
- 未实现 THINK / Decision / Action / Activity / World Query / Scheduler / AI↔AI。
- 未接 LLM / 网络。
- 未启用 Memory Runtime。
- 未创建数据库 / 持久化文件。
- 未修改 `main.data`。
- `LongTermProvider` 仍为 stub，返回 `[]`。
- `decision_constraints` = `None`。
- Goal / Commitment = Runtime-only working state，非 SOT。
- 重启会丢失 Goal / Commitment，是 C-2 已知限制。

### 22.15 C-3 阶段事实（2026-09-30）

- C-3 Tests Preflight 已 ACCEPTED。
- C-3 Tests Implementation 已完成，等待架构审核。
- C-3 只新增测试文件，未修改任何业务 `.py`。
- 新增测试：
  - `docs/test_c3_contract_structure.py`（T-A Contract Structure + B11 + C9 + C11 + D4 + D11 + F7）
  - `docs/test_c3_boundary.py`（T-E Runtime / SOT / Boundary，E1 ～ E11）
- C-3 Preflight 报告的 12 项缺口（G1 ～ G12）**全部闭合**。
- 6 组测试全部通过：
  - `test_c3_contract_structure.py`
  - `test_c3_boundary.py`
  - `test_c2_runtime_holder.py`
  - `test_c2_goal_commitment.py`
  - `test_b3_context_assembler.py`
  - `test_b5_runtime_context.py`
- C-3 未修改 Contract / PROJECT / `agent/*.py` / `main.py` / `ext_*` / 前端 / Memory。
- C-3 未实现 THINK / Decision / Action / Activity / World Query / Scheduler / AI↔AI。
- C-3 未接 LLM / 网络。
- C-3 未启用 Memory Runtime。
- C-3 未创建数据库 / 持久化文件。
- C-3 未修改 `main.data`。

### 22.16 Phase C 完成状态（2026-09-30）

- Phase C（Goal / Motivation / Commitment / Intent）**全部子阶段已完成**。
- C-0 ～ C-4 全部状态：✅。
- Phase C 冻结的 Contract：§5A（CC-20260927-01）+ §5B（CC-20260927-02）+ §5B.5 / §5B.15 / §5B.16 补丁（CC-20260928-03）。
- Phase C 完成后仍保持的边界：
  - `think()` 仍为 Stub，返回 `IntentSet(candidates=[])`。
  - `LongTermProvider` = stub，返回 `[]`。
  - Memory Runtime 未启用。
  - `decision_constraints` = `None`。
  - 未实现 THINK / Decision / Action / Activity / World Query / Scheduler / AI↔AI。
  - 未接 LLM / 网络。
  - 未创建数据库 / 持久化文件。
  - 未修改 `main.data`。
  - Goal / Commitment = Runtime-only working state。
  - 未产生"双 Context"。
  - `ContextLayers` 保留为 deprecated compatibility stub。
- Phase C 未冻结项（必须留待后续 Contract Change）：
  - Goal / Commitment 持久化方案。
  - Goal priority / conflict algorithm。
  - Decision 数据结构与接口。
  - Activity 生命周期。
  - World Query 接口。
  - Scheduler 接口。
  - AI↔AI Commitment negotiation。
  - 用户 Goal vs AI Goal 自动权衡。
  - 真实 THINK 的 candidate 数量要求。
  - Goal source 自动检测。
  - Goal creation 自动机制。
  - Motivation 最终算法。
  - Motivation 完整输入范围。

**下一阶段方向**：

- 不直接进入 Phase D 实现。
- 下一阶段（Phase D：World Query / Activity Lifecycle）必须先进行 Preflight。
- Preflight 通过后才可进入 Contract Change。
- Contract Change 通过后才可进入编码。

---

