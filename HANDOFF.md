# Airports Under Stress — 交接说明

最后更新：2026-07-30

## 冻结的开发优先级：桌面优先

用户已明确决定：本项目主要面向简历展示、面试讲解和电脑端浏览。从 V1-B 起，不在每个版本反复投入完整手机适配。

- 每个阶段必须重点验收 1366×768 桌面端；
- 手机端阶段性只做最低保障：能打开、核心流程不崩、无完全阻断使用的问题；
- 手机端字号、卡片重排、触控细节、长页面密度和小屏视觉统一记录，暂不阻塞阶段 GO；
- 等桌面端功能、数据和叙事基本冻结后，单独开一个 Mobile Polish / Responsive QA 任务集中修复；
- 只有同时影响数据正确性、桌面端或导致手机页面完全不可用的问题，才允许提前处理。

后续给 External Agent 的任务书必须沿用这一规则，不再默认要求每个 V1 子版本完成 390×844 全量视觉验收。

当前外部执行只使用 WorkBuddy HY3，免费期截至 2026-08-06；HY3 不可用、不适合或多轮返工失败时由 Codex 直接接管，不自动切换中转站 Luna。Luna 只保留历史备用信息，恢复使用必须由用户另行讨论并更新规则。外部执行必须先写 `tasks/external-agent/` 任务书，由 Codex 独立验收，不得自动提交或发布。

## 接手目标

V0/V0.5、V1-P0.1、V1-A、V1-B 第一版和第二版、V2-P0 与 V2-A 均已由 Codex 最终验收 GO。P0.1 的 180 分钟计划停场/18 小时总时长边界不得回退；V2-A 只在 97 Core / 55 Mechanism 范围做描述性天气分层，不得写成因果归因。

V1-B 第二版由 Codex 亲自实现，不经过 External Agent。它不是装饰性切换：15/30/60 分钟会重新分类同一条冻结的真实轮转路径，并同步展示全国敏感性结果。

## 开始前先看

按顺序阅读：

1. `PROJECT_STATUS.md`：当前总体状态和未完成项。
2. `reports/P0_DATA_AUDIT.md`：数据可行性结论和核心数字。
3. `docs/P0_PROTOCOL.md`：预先冻结的审计规则。
4. `docs/DATA_DICTIONARY.md`：字段和派生指标定义。
5. `web/app/dashboard.tsx`：已经发布的双语交互页面。
6. `web/app/globals.css`：全站视觉系统和语言切换器样式。
7. `tasks/external-agent/EXTERNAL_AGENT_TASK_01.md`：V0.5 网络首屏的实现、返工与最终验收记录。
8. `web/app/airport-coordinates.ts`：首屏使用的可复核机场经纬度子集及来源信息。
9. `tasks/external-agent/EXTERNAL_AGENT_TASK_02.md`：用户首屏反馈后的连接网络、地图轮廓、标签与日期反馈重构任务。
10. `tasks/external-agent/EXTERNAL_AGENT_TASK_03.md`：轮转故事的时间语义、名称、字号和叙事时间线重构任务。
11. `tasks/external-agent/EXTERNAL_AGENT_TASK_02_03_MASTER.md`：本轮联合返工的唯一执行入口；实际交给 External Agent 的文件。
12. `tasks/external-agent/EXTERNAL_AGENT_TASK_04.md`：V0.5 冻结前最后一轮产品修整；当前应交给 External Agent 的唯一入口。
13. `reports/V1_P01_CONTINUITY_AUDIT.md`：P0.1 的 3×3 连续性边界敏感性审计与 180 分钟/18 小时选择理由。
14. `reports/V1_P0_MECHANISM_AUDIT.md`：按 P0.1 边界重建后的正式机制产物、硬门槛与可复现性结果。
15. `tasks/external-agent/CLAUDE_CODE_EXECUTION_PROTOCOL.md`：当前 HY3 外部执行、Codex 接管和额度控制规则；其中 Luna 内容仅为历史备用，当前不得自动使用。
16. `tasks/external-agent/EXTERNAL_AGENT_TASK_V2_P0.md`：V2 天气数据可行性审计的唯一执行入口；当前禁止修改前端和 V0/V1 冻结产物。
17. `tasks/external-agent/EXTERNAL_AGENT_TASK_V2_A.md`：V2-A 天气分层与 episode 注释的唯一执行入口；Gate 0、样本门槛、UI 边界和禁止项均已冻结。
18. `tasks/external-agent/EXTERNAL_AGENT_TASK_V2_B.md`：V2-B 多因素调整天气关联的完整任务、外部执行记录与 Codex 最终验收记录。
19. `POLISH_BACKLOG.md`：不阻塞下一版本的统计概念解释、视觉和手机端统一收尾清单。
20. `tasks/external-agent/EXTERNAL_AGENT_TASK_V3_P0.md`：V3-P0 计划拥挤度审计边界、外部初稿和 Codex 最终验收记录。
21. `tasks/external-agent/EXTERNAL_AGENT_TASK_V3_P0_HY3_REVIEW.md`：WorkBuddy/CodeBuddy CLI 直接调用 HY3 的首次独立复核、session、模型用量和 Codex 复验记录。
22. `reports/V3_P0_CONGESTION_AUDIT.md`：修正口径后的 30/60/90 分钟计划拥挤度结果、Gate 和非因果边界。
23. `tasks/external-agent/EXTERNAL_AGENT_TASK_V3_A.md`：V3-A 全国层前端章节边界、HY3 实现、三轮返工与 Codex 最终验收记录。

## 当前稳定状态

工作区最新状态为 **V3 已于 2026-07-30 正式冻结；V1-P0.1 + V1-B 第二版 + V2-P0 + V2-A + V2-B + V3-A + V3-B 均验收通过，V3-P0 科学 Gate 为 CONDITIONAL GO；Sites version 3 以 owner-only 保留，临时 Cloudflare 公网预览已下线**：

- 计划停场上限 180 分钟、单个 episode 总时长上限 18 小时；越界统一记作 censored/观察中断，不伪装成 recovered；
- 15/30/60 分钟三档均使用同一连续运营边界并做真实阈值重分类；
- 全国 episode 数分别为 50,526 / 31,162 / 14,777，深度 ≥3 分别为 5,833 / 2,991 / 1,099；主分析最大深度为 9；
- 主分析中 15,876 个 episode 因计划长停场截断，292 个因 18 小时时长上限截断；最长正式 episode 不超过 18 小时；
- 12 个精选案例均保存三档视图；更严格门槛只会提前终止、缩短传播或使案例不再构成 episode，不会伪造新航段；
- 页面明确解释 30 分钟下排序仍较稳定，而 60 分钟下 Top 20 仅重合 3/20；
- 桌面字号、阈值实验区、无资格状态、时间轴播放和中英双语已完成；手机端仍按冻结策略只做最低保障；
- V2-P0 映射 96/97 Core 与 55/55 Mechanism；Mechanism 航班 90 分钟天气覆盖 99.91%，逐机场最差 99.23%，完整报告小时覆盖最差 98.25%；PBI 保持明确缺失，不用邻站替代；
- V2-A 默认 90 分钟并提供 60 分钟敏感性；全国 Gate 0 为 91,055 / 90,964 条匹配，48 个机场可比较、7 个明确样本不足，12 个 episode 有两档严格 backward 天气注释；
- 当前验收：V2-A/V2-P0 数据测试 9/9、Python 全量回归 77/77、lint、build、SSR 7/7；浏览器实测机场不足状态、案例天气切换与 console 均通过。
- 2026-07-28 用户复阅后已做概念可读性收口：第五、六部分优先用“连续延误段、接到晚点飞机的比例、连续晚点次数、两组传播率相差、天气报告匹配范围”等人话标签，并在页面解释 60/90、样本数、百分点和 95% 估计范围；科学字段和数据口径未改。
- V3-P0 只用五个计划字段完成 55 机场、91,185 事件的三档计划拥挤度审计；60 分钟低/高组传播率为 42.27% / 66.15%，窗口敏感性与集中度通过，但最小机场高组只有 82 条，低于 100 条门槛，因此不得直接承诺 55 机场全量比较页。
- V3-A 已新增 `06 / 计划拥挤` 双语章节，默认 60 分钟，可切换 30/60/90 分钟并真实联动低/中/高组样本、传播率、高减低差、计划总架次和窗口敏感性；案例/方法已顺延为 07/08。页面只做全国层描述，不做机场排行、搜索或因果解释。
- V3-A 最终验收：专项数据测试 8/8、Python 全量回归通过、ESLint 通过、生产构建通过、SSR 8/8；V3-P0 三个冻结科学产物 SHA-256 与 manifest 3/3 一致。HY3 session 为 `v3a-hy3-20260729`，共经历 60 分钟取数、集中度字段契约和 SSR 注释分隔三轮准确返工。

已部署源码提交：

```text
b02076d feat: add Chinese-first bilingual V0
```

当前线上版本：

```text
site: https://airports-under-stress.fizzy-elm-9171.chatgpt.site
Sites version: 2
visibility: owner-only
```

线上仍是 Sites version 2；V0.5 至 V1-B 第二版的工作区修改尚未提交或发布。

双语版本已经实现：

- 新增 `zh` / `en` 语言状态，默认 `zh`。
- 新增主要界面、排序项、轮转类型和航段状态的双语文案。
- 新增页头 `中文 / EN` 切换按钮。
- 中文化机场榜、航司对比、轮转故事、方法边界和页脚。
- 根据语言切换数字格式、延误单位和无障碍标签。
- 浏览器端切换时更新 `document.documentElement.lang`。
- 中文优先的页面标题、描述和分享元数据。
- 语言切换器的桌面、平板和手机布局。

## 下一步执行顺序

V3 已冻结。默认不再执行功能开发、结构改版、科学产物重建或公开部署，只处理用户明确指出的缺陷。不要重新执行已完成的 V2-B/V3-P0，也不要默认扩张 347 机场。任何机场级比较仍需高、低组均至少 100 条，传播率差不得包装成因果影响。若启动 V4，先建立单独 Roadmap、范围、数据 Gate 与任务书；不得直接在 V3 上继续堆功能。

### 1. 收集用户反馈

优先让用户直接查看当前本地中文版，并记录具体修改意见。建议按以下顺序确认：

- 首页标题与项目副标题。
- “压力指数”“传播”“吸收”等术语。
- 机场榜和机场详情的信息密度。
- 4 个轮转故事是否足够直观。
- 是否需要给机场、城市和航司增加中文译名。

### 2. 修改时保持双语同步

大部分界面文案集中在 `web/app/dashboard.tsx` 的 `ui.zh` 与 `ui.en`。修改中文时检查英文含义是否仍一致；不要复制出第二套页面。

继续保持现有颜色系统：墨黑背景、薄边框、薄荷绿色激活态。不要为了局部意见重做整套视觉方向。

### 3. 每轮修改后验证

数据逻辑：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

网页：

```powershell
npm.cmd test
```

2026-07-27 Task 04 最终验收已通过。第三轮后 Codex 浏览器实测发现键盘机场选择会触发 `pinnedCluster` 初始化顺序错误，已直接修复，并补齐样本外节点英文信息、聚合焦点转移、按钮组语义和 MYR 中文乱码。最终结果：数据测试 `24 passed`，生产构建通过，SSR `5 passed`，ESLint `0 error / 0 warning`；三指标可点击联动，DEC 样本外中英文信息正确且无假 `0.0%`，JFK 四机场聚合可从键盘入口打开并由 Escape 关闭。Task 04 / V0.5 可以冻结；当前仍未提交或发布。

2026-07-27 已创建 V1 的第一阶段唯一入口：`tasks/external-agent/EXTERNAL_AGENT_TASK_V1_P0.md`。该阶段只在冻结 P0 链边上审计多航段 Shockwave episode、有向传播链路、机场机制维度、15/30/60 分钟敏感性和 UI 数据契约；禁止修改前端、接入天气、训练预测模型、提交或发布。External Agent 完成后必须先由 Codex 验收 GO / CONDITIONAL GO / NO-GO，再决定 V1-A / V1-B 的实现范围。

2026-07-27 V1-P0 第一轮 Codex 验收不通过。External Agent 声称 GO，但独立核对发现 4,798 个 episode 带 `airport_discontinuity` 却被计为 recovered，10,906 个 en-route recovery 被误计为 censored，恢复 terminal step 未写入 steps，路径字段和累计分钟语义有误；CI gate 被 1,854 条 n<5 的默认零宽区间污染，报告声称的 Spearman / Top20 overlap 没有实现，集中度对象和角色样本边界也不正确。报告最大深度 11 与真实产物 15 冲突。精确返工清单已追加至 V1-P0 任务文件；当前 V1-A / V1-B 禁止开始，未修改前端、未提交、未发布。

2026-07-27 V1-P0 第二轮 Codex 验收仍不通过，当前按冻结规则判定 `NO-GO`。第二轮已经修复 gap outcome、terminal recovery step、路径字段、累计放大量、CI、conditional lift 和角色样本边界，但最终产物仍有 6 对同机尾号 episode 重叠，重叠 50–859 分钟；External Agent 将任务书要求的 100% 不重叠擅自放宽为 `<=10` 并称作边界噪声。报告仍是第一轮旧数字，manifest 未保存科学产物 hash，UI contract 仍有动态时间戳，所谓复现测试只检查临时 hash 长度。完整第三轮返工清单已追加至 `tasks/external-agent/EXTERNAL_AGENT_TASK_V1_P0.md`；在 overlap=0、真实 validator、报告一致与双跑 hash 一致之前，禁止进入 V1-A / V1-B、修改前端、提交或发布。

2026-07-27 V1-P0 第三轮验收仍不通过，且本轮核心处理无效。最终 Parquet 仍有原来的 6 对 50–859 分钟重叠；代码只是让 validator 跳过 `airport_discontinuity` 边界，从而表面返回 overlap=0。`recovery_not_continuing` 仍硬编码为 0，测试、报告和完成记录未更新。已确认 UI contract 移除动态时间戳，manifest 保存的 6 个 SHA-256 与现场重算 6/6 匹配。当前继续 `NO-GO`，详见 V1-P0 任务末尾第三轮验收记录。

2026-07-27 Codex 已直接完成 V1-P0 最终修复，正式判定 **GO**。状态机现在用 `PrevOrigin + Origin + PrevActualArrivalUTC` 精确验证真实航段连续性；所有发布 episode 统一执行同机尾号不重叠检查，不再跳过 gap。11 个 BTS 机尾分配/极端延误造成的并发替代时间线候选单独写入 `data/processed/v1_p0_episode_rejections.parquet`，不进入正式统计。最终产物：66,538 episodes、125,350 steps；负周转、UTC 倒序、重叠、路径断裂、gap-as-recovered、恢复后继续计数均为 0。两次完整管线的 7 个科学产物 SHA-256 全部一致，manifest 已记录 `scientificOutputsMatchPreviousRun=true`；针对硬门槛、哈希和报告一致性的自动验收 7/7 通过。`reports/V1_P0_MECHANISM_AUDIT.md` 已自动重建并与 summary 一致。可以开始 V1-A，但当前未提交、未发布、未修改 V1 前端。

2026-07-27 已下发 `tasks/external-agent/EXTERNAL_AGENT_TASK_V1_A.md`，它是当前 External Agent 的唯一入口。开工必须先完成 Gate 0：轮转故事 IATA 代码增加中英文小号名称；压力榜保持真实排名但说明“单机场、不合并都会区”，并允许选择全部 97 个 eligible 机场；底网从单纯 Top 48 改为 coverage-first + high-volume 的真实航线选取，保证所有显示节点至少一条真实连接。已独立核实 LGA/JFK/EWR 压力排名为 22/83/92；当前 52 个地图节点中有 25 个底网 degree=0，确属选线 UI 缺陷。Gate 0 后才实现 V1-A 机制总览；V1-B 不得提前开始。

2026-07-27 V1-A 最终验收通过。External Agent 完成了 Gate 0 与机制总览主体；Codex 独立检查后直接修复英文模式城市名、机制图实际数据轴域/中位线/键盘操作、SVG hydration mismatch、版本徽标与 SSR 脚本，并把可靠链路从 20 行密集小字重排为桌面双列/手机单列卡片，默认 8 条、可展开 20 条。最终数据测试 21 passed，ESLint 0 warning，生产 build 通过，SSR 6/6；浏览器确认地图全部展示节点有真实连接，97 机场入口和纽约单机场排名说明正确，轮转故事机场名称可读，机制页中英双语与桌面/手机布局可用。工作区仍未提交、未发布。下一阶段应先写 V1-B 边界与任务书，不要直接堆功能。

2026-07-27 已下发 `tasks/external-agent/EXTERNAL_AGENT_TASK_V1_B.md`。V1-B 第一版只做约 12 个按规则选择的真实 episode 与桌面端冲击波播放器：精确富化航班/时间/周转字段，支持案例切换、播放暂停、步进、状态解释和结局摘要。全量 episode 搜索、15/30/60 阈值切换、天气、预测、反事实和全美飞行动画全部排除。Codex 同步在 `globals.css` 增加 ≥900px 桌面可读性底线，将原有大量 8–10px 语义文字提升到 11–12px；后续实现不得撤销或重新引入必须依靠 175% 浏览器缩放才能阅读的小字。

2026-07-27 V1-B 第一轮 Codex 验收不通过。数据侧 12 个精选 episode、精确链路富化和静态产物基本可用，但页面直接暴露 `deepest/caught_up/amplified/recovered` 等内部 key，删失长警告被塞进选择按钮；案例与步骤各有一条亮白原生横向滚动条，播放到后半段 active step 会跑出视口；航班号、中英文城市名和状态解释虽已生成却未展示；摘要存在无标签数字、`recovered (recovered)` 和“深度15/共16步”未解释等问题，详情下方大片空白。完整返工门槛已追加到 V1-B 任务文件。Codex 同时修正了旧机制测试中数学上不成立的累计放大上限断言，未修改冻结科学定义。当前 V1-B 不得标记完成，未提交、未发布。

2026-07-27 V1-B 第二轮最终验收通过。External Agent 完成主要返工后，其 Claude Code 模型通道连续 10 次重试并以 `ConnectionRefused` 结束；Codex 接管补齐条件删失警告、离开视口自动停播、桌面 6×2 案例区、缺失机场中文名、中文航司名和测试性能。最终 12 个精选 episode 均以双语产品标签呈现；最长 15 深度/16 观察步骤案例可完整播放并自动跟随，航班号、机场城市、周转、延误变化、恢复和删失边界均可读。自动验证 V1-B 4、V0 21、机制 29 项全过，lint/build/SSR 7/7 全过；浏览器无应用错误。V1-B 第一版可冻结，仍未提交、未发布。

2026-07-28 Codex 亲自完成 V1-B 第二版并最终验收通过。`build_v1b_data.py` 现在把同一条冻结的 T15 物理路径按 15/30/60 分钟重新分类：若起始延误不足则明确标记 `not_qualified`，否则可提前在起飞前或途中恢复，严格门槛不会补造 T15 路径之外的新链路。前端新增双语“定义敏感性实验室”、全国敏感性指标、三档阈值控制、案例级动态深度/结局/时间轴和无资格解释，并统一提高 V1-B 桌面小字。浏览器实测 N985AT 从 16 个观察点缩为 6、3；N8825Q 在 60 分钟下正确不构成 episode；播放和控制台正常。最终 V1-B 6/6、V0 21/21、机制 29/29、lint/build/SSR 7/7 全过。当前仍未提交、未发布；下一步先交给用户审阅，不默认扩展全量搜索、天气或预测。

2026-07-28 用户指出旧 episode 横跨两天，不能合理代表同一轮连续冲击。Codex 亲自完成 P0.1 连续性修正：用 120/180/240 分钟计划停场 × 12/18/24 小时总时长做 3×3 审计，冻结主口径为 180 分钟/18 小时；触界均记作 `scheduled_turn_break` 或 `duration_limit` 的观察中断，不记作恢复。重建后的 15/30/60 分钟 episode 为 50,526 / 31,162 / 14,777，深度 ≥3 为 5,833 / 2,991 / 1,099，主分析最大深度 9；15,876 个因长停场截断、292 个因时长上限截断。完整管线连续两跑的 7 个科学产物 SHA-256 全部一致，`scientificOutputsMatchPreviousRun=true`。Python 68 项、SSR 7/7、lint、生产 build 全过；浏览器实测 N985AT 为 14.9 小时并因计划停场超过 180 分钟停止，30/60 分钟全国指标联动正确，console 无错误。当前未提交、未发布。

### 4. 发布

重点检查：

- 页头在桌面与手机宽度下是否拥挤。
- 中文长标题和机场详情指标是否自然换行。
- 切换到英文后所有主要区域是否同步变化。
- 图表悬停提示、按钮、ARIA 标签和轮转状态是否随语言变化。
- 中英切换不改变当前机场排序、选中机场和选中轮转故事。

每次通过验证后更新已有 Sites 项目，不要创建新项目：

```text
project_id: appgprj_6a64f2917a94819181201cc9f2e1d54a
site: https://airports-under-stress.fizzy-elm-9171.chatgpt.site
visibility: owner-only
```

## 文件地图

| 路径 | 用途 |
|---|---|
| `scripts/download_bts.py` | 下载并校验 BTS 原始月度数据 |
| `scripts/run_p0.py` | 执行 P0 数据审计与链路重建 |
| `scripts/build_v0_data.py` | 生成网页使用的 V0 聚合数据 |
| `src/airports_under_stress/` | 时间处理、下载和审计核心逻辑 |
| `tests/` | Python 数据逻辑测试 |
| `reports/P0_DATA_AUDIT.md` | P0 最终审计报告 |
| `web/app/v0-data.json` | 网页的固定 V0 数据快照 |
| `web/app/dashboard.tsx` | 已发布的中英双语主交互页面（轮转故事在此重构） |
| `web/app/NetworkHero.tsx` | 首屏航空网络画布（两层网络、真实边界、标签碰撞、日期强度、迷你趋势） |
| `web/app/EpisodeExplorer.tsx` | V1-B 双语案例播放器与 15/30/60 定义敏感性实验室 |
| `scripts/build_v1b_data.py` | 生成 12 个精选案例及三档阈值重分类静态数据 |
| `scripts/audit_episode_continuity.py` | 独立运行 3×3 连续性边界敏感性审计，不覆盖正式 P0 产物 |
| `scripts/run_v1_p0.py` | 按冻结的 180 分钟/18 小时边界重建 V1-P0.1 正式科学产物与审计报告 |
| `web/app/v1-b-data.json` | V1-B 固定、可复现的前端数据快照 |
| `web/app/us-boundary.ts` | 美国本土边界坐标（Public Domain，与机场用同一投影） |
| `web/app/globals.css` | 全站视觉与响应式样式 |
| `web/app/layout.tsx` | 页面语言和 SEO/分享元数据 |
| `web/tests/rendered-html.test.mjs` | 服务端渲染验收测试 |
| `web/.openai/hosting.json` | 已有 Sites 项目配置 |

## 数据复现

如需从头复现 2026 年 5 月数据：

```powershell
python scripts/download_bts.py --year 2026 --month 5
python scripts/run_p0.py --year 2026 --month 5
python scripts/build_v0_data.py
```

不要为了前端文案修改重新下载数据。`web/app/v0-data.json` 已经是 V0 使用的数据快照。

## 产品与叙事边界

项目最有价值的不是“做一个延误排行榜”，而是把逐航班记录还原成同一架飞机的轮转链，再观察压力如何传播或被吸收。简历和文书应强调：

- 处理跨时区、跨午夜、取消、备降和物理连续性。
- 用 611,735 条记录重建 549,388 条有效轮转关系。
- 主动区分描述性传播信号与因果结论。
- 从数据审计、可复现管线到交互式数据产品的完整闭环。

## 等用户确认的内容

接下来优先让用户对已发布的中文版提出意见：

1. 项目中文副标题是否准确、是否够有记忆点。
2. “压力指数”“传播”“吸收”等术语是否自然。
3. 首页信息密度是否过高。
4. 机场、航司等专有名词是否需要中文译名，还是保留官方英文。
5. 轮转故事是否足够直观，能不能让非航空背景的人快速理解。

V3-P0 已 CONDITIONAL GO。下一步冻结 V3-A 的全国展示与机场纳入规则；提交、私有部署和手机端集中修整仍需单独决定。

## 2026-07-28 V2-B 最终交接

- 外部 Claude Code 会话 `88fee937-001e-4227-8b55-674c3472cbdd` 实际 modelUsage 只有 `gpt-5.6-luna`，未调用 Sol。
- Codex 拒绝了外部代理最初的测试结论：其 `test_v2b_model.py` 没有 pytest 测试函数，所谓 9 passed 全来自旧测试。现已补成 6 条 V2-B 科学测试，连同 V2-A/天气回归共 15/15。
- 模型使用 55 个 Mechanism 机场、严格 backward weather join、60/90 分钟两档；主规格考虑机场、UTC 计划时段、星期、航司、计划周转分箱和上一航段延误严重度，不含实际起飞、实际周转或下一航段结果派生字段。
- 日期聚类区间采用明确的 CR1 有限样本校正，并有独立小矩阵逐元素复核。构建器同时生成科学 JSON 与前端快照，避免两者漂移。
- 90 分钟主展示：原始差 `1.40` 个百分点；基础调整 `4.92`（95% `2.79–7.06`）；运营条件调整 `3.17`（`2.07–4.27`）。结果只表示调整后的描述性关联。
- 页面已经接入现有天气区；lint、build、SSR 7/7、Python 定向回归 15/15 全过，1440×1100 浏览器验收通过。
- 未 commit、push、deploy；Mobile Polish 按用户约定留到最终阶段。

## 2026-07-28 V3-P0 最终交接

- 外部 Claude Code 会话 `ddce983d-7af6-4bf6-bb1c-b80f675440b6` 使用 `gpt-5.6-luna` 完成初稿；Codex 因到达机场归属、相对百分位口径、窗口比较和会话记录错误拒绝首轮验收并重写核心实现。
- 最终特征函数严格只接受 `Origin`、`Dest`、`ScheduledDepartureUTC`、`ScheduledArrivalUTC`、`SourceRow`；取消、备降和任何实际延误字段都不参与计划拥挤度构造。
- 55 个机场、91,185 条事件三档全覆盖；60 分钟计划总架次中位数 40、P90 115。低组 26,502 条、传播率 42.27%；高组 20,768 条、传播率 66.15%。这只是描述性关系。
- 30/90 分钟相对排序与 60 分钟 Spearman 为 0.717 / 0.842，四分位一致率 0.510 / 0.602，传播率方向一致；最大机场和最大单日占高组 6.37% / 5.98%。
- 55/55 机场有动态变化，但最小机场高组 82 条，未达冻结的 100 条门槛，因此为 `CONDITIONAL GO`。V3-A 可做全国层面，机场页必须按样本门槛筛选。
- V3 专项 5/5、Python 全量 88/88；事件、summary、报告连续构建 SHA-256 一致。未修改前端、未提交、未发布。

## 2026-07-28 HY3 直连与 V3-P0 二次复核交接

- 本机 WorkBuddy `5.3.5` 自带 CodeBuddy CLI；Codex 已验证可使用非交互 `--print` 模式，从项目目录后台直接下发任务并取得 JSON/流式结果，无需打开 WorkBuddy 桌面窗口或由用户复制任务。
- 定向连通性测试使用 `--model hy3 --effort high`，返回元数据明确为 `model: hy3`、`requestModelName: Hy3`、`credit: 0`。后续可以保存 session ID 并通过 resume 继续返工。
- 首次正式任务是 V3-P0 独立只读审查，任务入口为 `tasks/external-agent/EXTERNAL_AGENT_TASK_V3_P0_HY3_REVIEW.md`，HY3 session 为 `7c7fd089-ffa0-4ac2-8952-b4b7a7da7c45`。外部执行未修改项目文件。
- HY3 判定仍为 `CONDITIONAL GO`，未发现新的阻塞项；确认唯一失败门槛是 OMA 高拥挤组 82 条。它识别出 30 分钟四分位一致率 `0.509941` 仅贴线，以及平均 ties 百分位缺少精确数值测试的非阻塞缺口。
- HY3 无法在该只读非交互权限下执行 Bash；Codex 已补跑 V3 专项测试，结果 `5 passed`。Codex 还核对 91,185 条最终事件：三个窗口均无相对拥挤度恰好等于 0.25/0.75 的记录，因此 HY3 提到的两处分箱边界差异对当前结果无影响，不为形式统一扰动冻结 P0。
- 后续协作模式：Codex 定义范围与任务书 → HY3 承担大量阅读、实现或第一轮审查 → Codex 检查 diff/科学口径/测试/浏览器 → 使用原 session 精确返工 → 多轮仍不正确时由 Codex 接管。HY3 免费不等于免验收，默认不得使用绕过权限、commit、push 或 deploy。
- 下一步仍是先规划 V3-A：全国层展示可继续，机场比较只纳入高低组均至少 100 条的机场；30 分钟档只作敏感性参考，不包装成稳定排名或因果影响。Mobile Polish 继续留到最终集中处理。

## 2026-07-29 全站易读性改版交接

- HY3 按 `tasks/external-agent/EXTERNAL_AGENT_TASK_SITE_CLARITY_FULL.md` 完成第一轮，Codex 两轮浏览器验收退回并在同一会话修正。
- 全站现在统一为三层：默认层直接说研究问题和结论；理解层保留必要图表/交互；样本、阈值、区间、模型和审计边界进入原生 `details`。
- 第 06 章默认明确：30/60/90 分钟分别是计划起飞前后 15/30/45 分钟的总窗口；排班松紧在每个机场内部比较，约按低 25% / 中 50% / 高 25% 分组，ties 会使实际比例不严格等于 25/50/25。
- Codex 真实浏览器发现 `.clarity-details-inner` 的作者 `display` 规则覆盖原生关闭态，导致折叠内容溢出；已增加关闭态高特异性守卫。最终页面 9 个 details 默认全部关闭且 `leakedChildren=[]`，展开天气研究细节后机场选择可见，收起后完全隐藏。
- 传播图标签由 10px 提升至 12px；天气默认层的重复非因果提醒合并为一句；传播章节末尾说明改为“描述性比较不等于因果控制”。
- 最终验收：ESLint 通过、生产构建通过、SSR 9/9；浏览器实测天气研究细节、单步天气、计划拥挤 30/60 切换正常，并已恢复默认 60 分钟与全部折叠关闭状态。
- 未修改 JSON、Python、冻结科学产物、阈值或数值；未 commit、push、deploy。下一步由用户浏览中文版提出内容/视觉意见，Mobile Polish 继续留到最终统一处理。

## 2026-07-30 V3-B 最终交接

- V3-B 已并入第 06 章，定位是机场层探索器，不新增章节、不做机场排名。默认问题是“换到一座机场，结果还一样吗？”，先用人话给结论，样本门槛、Wilson 区间和完整 n/传播数进入默认收起的研究细节。
- 唯一数据源为冻结的 `data/processed/v3_p0_congestion_events.parquet`：91,185 条事件、55 个机场；60 分钟主口径下 54 个机场满足松/密两组各至少 100 条，OMA 因 140/82 被排除。54 个机场中 52 个为正向、JFK 与 ONT 为反例；48 个机场在 30/60/90 三档均为正向。
- 默认机场为 ATL：60 分钟下排班较松组 46.48%，较密组 61.93%，相差约 15 个百分点。页面明确“选择一座机场，只和自己比较”，30/90 只作为换尺子检查，不包装成三条同等结论。
- HY3 按 `tasks/external-agent/EXTERNAL_AGENT_TASK_V3_B.md` 完成大批量实现；Codex 独立修正了测试可复现性、循环导入、英文机场名透传、三档研究明细、章节重复、字号、选择器定位及 SSR 作用域。
- 验收结果：V3-B Python 定向测试 8/8；项目 `.venv` 全量 pytest 退出码 0；ESLint 通过；生产 build 通过（仅既有 chunk 大小提示）；SSR 10/10。浏览器实测 ATL/JFK/ONT 联动、反例文案、研究细节开合与 30/60/90 明细均正确，console warning/error 为 0。
- 当前本地开发站点为 `http://localhost:3000/`；未 commit、push、deploy/publish。Mobile Polish 继续留到最后集中处理。

## 2026-07-30 新对话与额度交接规则

- 当前长对话已经覆盖从 V0 到 V3 的大量历史。V3 验收结束后，下一阶段建议直接新开 Codex 对话，不再继续携带完整聊天历史。
- 新对话首先读取 `PROJECT_STATUS.md` 和 `HANDOFF.md`；若要启动新版本，再读取对应的 `tasks/external-agent/` 任务书。文档中的 GO/CONDITIONAL GO、冻结边界和未提交/未部署状态视为正式上下文，不重做已完成工作。
- 推荐开场语：`读取 PROJECT_STATUS.md 和 HANDOFF.md，了解当前项目状态；不要重做已标记 GO 的版本，不要提交或部署，先告诉我下一步边界。`
- 当前外部执行只使用 WorkBuddy HY3，免费期截至 2026-08-06。HY3 联系不上、明确不适合或多轮返工仍不正确时，由 Codex 直接接管；不得自动切换中转站 Luna。
- 中转站 GPT-5.6 Luna 当前停用，只保留历史记录。8 月 6 日后是否恢复，必须等用户主动讨论并重新写入规则，不能根据日期自动启用。
- 额度控制：小型修改由 Codex 直接完成；大型且边界明确的实现可交给 HY3；普通实现与验收优先 high，xhigh 留给复杂科学设计和疑难问题；浏览器验收禁止反复读取整页 DOM、整页文字和巨大截图，只检查目标组件。
- 这是一种阶段性交接，不是重新开始。代码、数据产物、测试与项目决策都保留在工作区和 MD 中，新对话只减少无关聊天上下文。

## 2026-07-30 Sites version 3 部署交接

- V0 至 V3-B 的最新本地版本已通过生产构建与 SSR 10/10，提交 `cf2e8bf` 已推送至原 Sites 项目。
- 原项目已成功部署 Sites version 3，网址仍为 <https://airports-under-stress.fizzy-elm-9171.chatgpt.site>。
- 用户明确要求公开访问，但 Sites 在切换 `public` 时返回“当前工作区未启用发布到互联网”；当前访问策略仍是仅 owner 可访问。
- 后续公开分享不得误判为已经完成：需要先启用当前工作区的 Sites 互联网发布能力，或选择另一家支持公开网址的托管平台。

## 2026-07-30 Cloudflare Workers 公开部署交接

- Cloudflare 登录与首次 Workers 子域初始化已经完成，账户子域为 `eastiro-lab`。
- `web/vite.config.ts` 已固定 Worker 名称 `airports-under-stress`；兼容日期后修正为本地运行时支持的 `2026-05-22`。
- 当前公开网址为 <https://airports-under-stress.eastiro-lab.workers.dev>，部署版本 ID 为 `2d158fe1-08ff-4927-a215-a074e57012da`。
- 已确认完整样式和脚本能够从公开地址加载；该地址不要求访客拥有或登录 ChatGPT 账号，也不依赖本地开发服务器持续运行。
- 原 Sites 项目和网址继续保留，但仍为 owner-only。
- 2026-07-30 用户看完临时公开版本后要求取消；Cloudflare Worker `airports-under-stress` 已成功删除，原 `workers.dev` 地址现为历史记录，不得继续作为有效公开链接。此操作未删除本地代码、Git 历史或 Sites 私有版本。

## 2026-07-30 V3 正式冻结交接

- 用户明确决定冻结 V3。后续默认只修复具体缺陷，不主动开启 V4、增加章节、扩充机场范围或重建科学口径。
- 冻结收口已统一页头/页脚 V3 标识，并修复第 06 章机场下拉框白底浅字问题；根因是 CSS 使用了不存在的 `--bg`，现改为深色 surface，并显式设置 dark color scheme 与 option 配色。
- 最终验证：Python `104 passed`；SSR `10/10`；ESLint、生产 build 通过。1280×721 浏览器检查无横向溢出、console warning/error 为 0，V3 标识和选择框样式正确。
- 完整 Mobile Polish 仍是已知非阻塞技术债，本轮不为冻结而扩张范围；如未来需要，单独建立维护任务。Cloudflare Worker 保持已删除，Sites version 3 保持 owner-only，本地冻结版本不重新发布。
