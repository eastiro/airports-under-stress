# Airports Under Stress — 交接说明

最后更新：2026-07-28

## 冻结的开发优先级：桌面优先

用户已明确决定：本项目主要面向简历展示、面试讲解和电脑端浏览。从 V1-B 起，不在每个版本反复投入完整手机适配。

- 每个阶段必须重点验收 1366×768 桌面端；
- 手机端阶段性只做最低保障：能打开、核心流程不崩、无完全阻断使用的问题；
- 手机端字号、卡片重排、触控细节、长页面密度和小屏视觉统一记录，暂不阻塞阶段 GO；
- 等桌面端功能、数据和叙事基本冻结后，单独开一个 Mobile Polish / Responsive QA 任务集中修复；
- 只有同时影响数据正确性、桌面端或导致手机页面完全不可用的问题，才允许提前处理。

后续给 External Agent 的任务书必须沿用这一规则，不再默认要求每个 V1 子版本完成 390×844 全量视觉验收。

外部执行已统一改为 Codex 通过本机 Claude Code CLI 下发：正式任务显式使用 `gpt-5.6-luna` 和 `--effort xhigh`，小型只读诊断最低使用 `high`；`low` 仅限无工具连通性探针。完整规则见 `tasks/external-agent/CLAUDE_CODE_EXECUTION_PROTOCOL.md`。

## 接手目标

V0/V0.5、V1-P0.1、V1-A、V1-B 第一版和 V1-B 第二版均已在当前工作区完成。P0.1 已把传播 episode 收紧为“同一机尾号上的连续晚点运营状态”：计划停场超过 180 分钟或总时长达到 18 小时即截断，且截断不记作恢复。当前不要回退这一边界；先让用户审阅修正后的 V1-B，再决定是否进入 V2 天气控制或做一次提交/私有发布。

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
15. `tasks/external-agent/CLAUDE_CODE_EXECUTION_PROTOCOL.md`：Codex 调用 Claude Code / GPT-5.6 Luna 的模型、effort、权限、任务书和验收协议。

## 当前稳定状态

工作区最新状态为 **V1-P0.1 连续性边界修正 + V1-B 第二版验收通过，未提交、未发布**：

- 计划停场上限 180 分钟、单个 episode 总时长上限 18 小时；越界统一记作 censored/观察中断，不伪装成 recovered；
- 15/30/60 分钟三档均使用同一连续运营边界并做真实阈值重分类；
- 全国 episode 数分别为 50,526 / 31,162 / 14,777，深度 ≥3 分别为 5,833 / 2,991 / 1,099；主分析最大深度为 9；
- 主分析中 15,876 个 episode 因计划长停场截断，292 个因 18 小时时长上限截断；最长正式 episode 不超过 18 小时；
- 12 个精选案例均保存三档视图；更严格门槛只会提前终止、缩短传播或使案例不再构成 episode，不会伪造新航段；
- 页面明确解释 30 分钟下排序仍较稳定，而 60 分钟下 Top 20 仅重合 3/20；
- 桌面字号、阈值实验区、无资格状态、时间轴播放和中英双语已完成；手机端仍按冻结策略只做最低保障；
- 当前自动验收：Python 共 68 项（基础/V0/V1-B 36 项 + 机制 32 项）、lint 0 warning、build 通过、SSR 7/7；两次完整 P0.1 运行的 7 个科学产物 SHA-256 全部一致；浏览器实测三档阈值、N985AT 长停场截断和 console 均通过。

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

用户确认 P0.1 修正后的机制区和连续延误案例表达后，再决定整理干净提交、更新私有部署，或进入 V2 天气控制。
