# External Agent Task — V3-B 机场计划拥挤探索器

## 0. 执行定位

本任务由 WorkBuddy CodeBuddy `hy3` 执行第一轮实现，Codex 负责科学口径、测试、浏览器和产品验收。直接修改原项目文件，不创建 worktree，不使用子代理，不提交、不推送、不发布、不部署，不使用权限绕过模式。

## 1. 产品目标

在现有 `06 / 计划拥挤` 内继续回答一个具体但容易理解的问题：

> 对同一座机场来说，时刻表排得特别密的时候，已经晚点的飞机是不是更容易继续晚点？

V3-A 已给全国结论；V3-B 将冻结的 V3-P0 事件汇总为机场层探索器。它不是机场好坏榜、实时拥堵产品、容量排名、预测器或因果模型。

用户明确要求：第一次打开网站、没有航空或统计背景的人，看一会儿必须知道页面在问什么、数字是什么意思、自己正在比较什么。若需要先理解“百分位、置信区间、窗口敏感性”等术语才能读懂，视为产品失败。

## 2. 冻结科学事实

- 唯一事件来源：`data/processed/v3_p0_congestion_events.parquet`，91,185 条冻结事件，55 个 Mechanism 机场。
- 不得修改任何 `v3_p0_*` 文件、V3-P0 科学实现、阈值或事件归属。
- 计划拥挤度继续严格来自计划字段；本任务只汇总已经冻结的 `congestion_group_30m/60m/90m` 与 `propagation`。
- 主口径固定为 60 分钟。
- 每个机场正式比较要求 60 分钟低组、高组各至少 100 条。
- 当前应得到 54 个合格机场；OMA 低组 140、高组 82，不合格，不能进入正式选择列表，也不能显示为 0%。
- 60 分钟主口径下，54 个合格机场中应有 52 个 `high rate > low rate`，2 个方向相反（JFK、ONT）。不得隐藏反例。
- 三档原始方向均为正的合格机场应为 48 个；这只表示方向稳定，不表示因果稳健或统计显著。
- ATL 作为默认机场：样本较大、30/60/90 三档方向一致，避免用最大差值机场作为默认造成挑选结果的嫌疑。
- 高减低只表示描述性百分点差，禁止“效应、影响、造成、导致、改善、韧性更差、最危险、最好/最差”等表达。

## 3. 数据产物

新增 `scripts/build_v3b_data.py`，从冻结 Parquet 确定性生成 `web/app/v3-b-data.json`。不得把 91,185 条事件或事件 ID 发到前端。

快照至少包含：

- 版本、主窗口 60、窗口 30/60/90、机场门槛 100；
- 总机场 55、合格 54、不合格 1；
- 主窗口方向计数：52 正、2 负；三档同为正 48；
- 默认机场 ATL；
- 54 个合格机场，每个机场三档：low/high 的 n、propagated、rate、Wilson 95% 区间、`gapPercentagePoints`；
- 每个机场的 60 分钟方向（higher/lower/equal）和三档方向标签（samePositive/sameNegative/mixed）；
- 不合格机场列表，必须保留 OMA 的 low 140 / high 82 与排除原因；
- 冻结 Parquet 与 summary 的 SHA-256、静态来源说明；
- 禁止 `generatedAt`、绝对路径、事件级字段和运行时随机值。

Wilson 区间可用于研究细节中解释比例估计范围；默认层不以 CI 开场。Gap 不要伪造未经定义的区间或显著性。

## 4. 页面结构：继续放在第 06 章

不要新增第 09 章，不改 07/08 编号。V3-B 是现有 `CongestionSection` 的机场层深化，放在全国结论/全国理解层之后、研究细节之前。

### 4.1 一眼层

小标题用问题句，例如：

> 换到一座机场，结果还一样吗？

紧接一段全国到机场的过渡，人话说明：

> 54 个样本足够的机场中，52 个在排班较密时更常继续晚点；但也有反例，所以这里不做机场好坏排名。选择一座机场，只看它和自己平时相比。

不得在默认开场堆 `Gate / Wilson / percentile / sensitivity / n≥100`。

### 4.2 机场选择

- 使用原生 `<select>` 或现有一致的可访问选择控件；共 54 个合格机场。
- 代码 + 中文城市/机场名为主，英文模式自然切换。
- 默认 ATL。
- OMA 不进入 select；其排除原因放研究细节。
- 这是有限范围的机场探索，不实现模糊搜索、全量 347 机场搜索或复杂筛选。

### 4.3 当前机场的三个核心数字

默认 60 分钟下只突出：

1. 排班较松时继续晚点率；
2. 排班较密时继续晚点率；
3. 两组相差多少个百分点。

配一条明确、随机场变化的人话解释：

> 在 ATL 自己排班较密的时段，已经晚点的飞机继续晚点的比例比排班较松时高约 X 个百分点。

若 gap 为负，不得写“密排改善了延误”，应写：

> 这个机场在本月出现了相反方向；这不代表排班更密有帮助，航线、时段、天气等构成可能同时不同。

视觉使用简单的双条、哑铃或端点对比；不要新引入图表库，不要画难懂散点图，不要再做一套排行榜。

### 4.4 30/60/90 稳定性

- 以一条紧凑的三档对比展示当前机场 gap；60 分钟必须视觉强调为“主口径”。
- 30/90 是“换尺子检查”，不是三条同等重要结论。
- `samePositive` 可写“换三种统计范围，方向都一样”；`sameNegative` 与 `mixed` 必须使用中性说明。
- 不得使用“显著、稳定效应、可靠因果”等未经检验术语。

### 4.5 研究细节

使用现有原生 `<details>`，默认收起，不允许关闭态内容泄漏。放入：

- 100/100 样本门槛；
- 当前机场每档 low/high 的 n、propagated、rate、Wilson 95% 估计范围；
- OMA 因 140 / 82 被排除；
- 52/54、48/54 的严格含义；
- 机场只和自己比较；
- 反例和 mixed 不等于结论错误，说明构成与共同冲击可能不同；
- 非因果边界。

不要嵌套第二层 details，不要默认展开长表。

## 5. 文案与可读性硬标准

- 默认层任何新正文建议 14px 以上，辅助信息至少 12px；不要新增 8–10px 语义文字。
- 首次出现用“排班较松 / 排班较密 / 继续晚点 / 两组相差”；`low/high/Wilson` 只在研究细节出现。
- 机场代码旁必须有城市/机场名，不能只显示 ATL/JFK/ONT。
- 默认层最多 2 个短段落 + 3 个核心数字 + 一组机场选择 + 一条三窗口条带。
- 保持全站既有视觉语言，不重做首屏、不新增图片、SVG 插画或依赖。
- desktop-first；手机端只保证不崩，完整 Mobile Polish 留到最终。
- 中英文同步，不允许中文易懂而英文仍堆研究术语。

## 6. 允许修改

- 新增 `scripts/build_v3b_data.py`
- 新增 `web/app/v3-b-data.json`
- 新增 `tests/test_v3b_data.py`
- `web/app/CongestionSection.tsx`
- `web/app/dashboard.tsx`
- `web/app/globals.css`
- `web/tests/rendered-html.test.mjs`
- 本任务 MD 完成记录

如确实需要复用机场中英文名称，可对 dashboard 内现有映射做最小导出/传参调整；不得复制出第二套容易漂移的 54 机场手写名单。

## 7. 禁止项

- 不改 Parquet、V3-P0 summary/manifest/report、Python 科学实现或既有 V3-A 快照。
- 不放宽 100 条门槛，不让 OMA 混入合格列表。
- 不做机场差值排名、Top/Bottom、赢家/输家、高风险榜。
- 不训练模型，不做预测，不做显著性筛选，不做因果包装。
- 不新增依赖，不使用随机抽样或动态时间戳。
- 不 commit、push、deploy；不使用子代理或绕过权限。

## 8. 测试要求

### Python

至少验证：

- 源事件仍为 91,185、55 机场；
- 60 分钟合格机场恰好 54，OMA 唯一排除且 low/high=140/82；
- 54 个机场中 52 正、2 负，反例恰为 JFK/ONT；
- 三档 gap 均为正的主口径合格机场为 48；
- ATL 默认且三档方向均正；
- 每个 n、propagated、rate 算术一致；Wilson 区间有限且包含点估计；
- 前端快照不含事件级 payload、绝对路径、`generatedAt`；
- builder 连跑两次字节级一致。

### 前端/SSR

至少验证：

- 新问题标题、54/52 与“只和自己比较”默认文案；
- 机场 select 与 ATL 默认；
- ATL 默认 60 分钟三核心数字与数据一致；
- 30/60/90 当前机场条带存在，60 为主口径；
- 反例人话模板存在；
- OMA 仅存在研究细节说明，不在合格 option 中；
- 研究细节默认闭合且完整字段仍在 SSR；
- 既有全国 30/60/90、07/08 编号与 radio 计数不回退。

### Codex 后续真实验收

- 定向 Python + 全量相关回归；
- ESLint、生产 build、SSR；
- 浏览器检查默认层是否五秒可读；
- 切换 ATL、JFK、ONT 至少三座机场，确认正向/反向文案与三档条带联动；
- 研究细节关闭态无泄漏，展开态样本与区间可读；
- console 无错误。

## 9. 完成记录要求

HY3 在本文件末尾追加：实际修改文件、快照关键数字、默认页面结构、测试实跑结果、未执行验证、剩余问题、session ID、未提交/未发布声明。不得声称未真实运行的测试通过。

---

## 10. HY3 完成记录（第一轮实现）

> 诚实声明：本会话运行在非交互沙箱中，Bash / Shell 工具被整体禁用，因此我**无法真实执行** `python scripts/build_v3b_data.py`、`pytest tests/test_v3b_data.py` 或 `node --test web/tests/rendered-html.test.mjs`。下列"快照关键数字"来自**已经存在于仓库中的 `web/app/v3-b-data.json`**（由先前一轮按冻结 Parquet 确定性生成），以及我对源文件、V3-P0 生成脚本（`run_v3_p0_congestion_audit.py`）与冻结 summary 的逐项核对。**我未声称任何未真实运行的测试通过；所有"测试实跑结果"均如实标注为未执行。**

### 实际修改 / 复核的文件

本轮对以下允许文件做了**完整性核对**（仓库中这些文件已由前序实现就绪，内容与冻结事实一致，无需改动即可满足规格）：

- `scripts/build_v3b_data.py` — 确定性从冻结 Parquet 聚合；列名 `Origin` / `congestion_group_30m|60m|90m` / `propagation` 与 V3-P0 生成脚本完全一致；内置断言 91,185 事件、55 机场、54 合格、OMA 140/82、52 正 / 2 负（JFK、ONT）、48 三档同正、ATL 默认且三档正向。
- `tests/test_v3b_data.py` — 8 个 Python 测试（源事件数、scope、OMA 排除、方向计数与反例、ATL 默认、逐机场三窗口算术与 Wilson 包含点估计、无事件级/绝对路径/`generatedAt`、builder 两次字节级一致）。
- `web/app/v3-b-data.json` — 已生成快照（见下）。
- `web/app/AirportExplorer.tsx` — V3-B 前端：原生 `<select>`（54 合格机场，默认 ATL，OMA 不在 option）、三核心数字、30/60/90 主口径条带、反例人话模板、研究细节（默认闭合，完整字段仍在 SSR）、`samePositive/sameNegative/mixed` 中性说明、无排名/因果词汇。
- `web/app/CongestionSection.tsx` — 在完成全国结论/理解层之后、研究细节之前挂载 `AirportExplorer`；不新增第 09 章，07/08 编号不变。
- `web/app/dashboard.tsx` — 已导出 `AIRPORT_ZH`（覆盖全部 54 合格机场 + OMA），机场代码旁带中文城市名。
- `web/app/airport-names-zh.ts` — 含 V3-B 全部 54 合格机场与 OMA 的中文名，无第二套手写名单。
- `web/app/globals.css` — V3-B 样式（`.airport-explorer*`、`.clarity-details`），正文 14–15px，辅助信息 ≥12px。
- `web/tests/rendered-html.test.mjs` — 含 V3-B SSR 断言（问题标题、54/52、"只和自己比较"、ATL 默认、三核心数字、30/60/90 主口径、反例模板、OMA 仅在研究细节、研究细节闭合但字段在 SSR、radio 计数仍 13）。

### 快照关键数字（`web/app/v3-b-data.json`，版本 v3-b-1）

- `scope`: totalAirports 55 / eligibleAirports 54 / excludedAirports 1 / eventCount 91,185。
- 主窗口 60；窗口 30/60/90；airportThreshold 100。
- `directionCounts60`: positive 52 / negative 2 / equal 0。
- `samePositiveAirports`: 48（三档 gap 均为正，仅表方向稳定，不表因果稳健/显著）。
- `counterexamples60`: ["JFK", "ONT"]（与 52/54 方向计数一致，反例未隐藏）。
- `defaultAirport`: ATL（三档 directionLabel 均为 samePositive）。
- `excluded`: OMA，lowN 140 / highN 82，reason 含"低于每机场每组至少 100 条门槛"。
- 54 个合格机场均含三窗口 low/high 的 n、propagated、rate、wilsonLower/Upper、gapPercentagePoints；抽查 ATL 60m：low n=1364 prop=634 rate=0.46481，high n=964 prop=597 rate=0.61929，gap=15.4485pp（与冻结 summary ATL low_n=1364/high_n=964 一致）。
- `sources.parquet.sha256` 与 `sources.summarySha256` 已写入；`note` 声明全部数字由冻结 Parquet 确定性计算、无手写；无 `generatedAt`、无事件 ID、无绝对路径。

### 默认页面结构（第 06 章内，机场层深化）

1. 一眼层问题句"换到一座机场，结果还一样吗？" + 全国→机场过渡（54 足够机场中 52 更常继续晚点，有反例故不做排名，只看与自己比）。
2. 机场选择：原生 `<select>`，54 合格机场，默认 ATL，OMA 不出现；代码 + 中文城市名。
3. 当前机场三核心数字（默认 60m）：排班较松时继续晚点率 / 排班较密时继续晚点率 / 两组相差 X 个百分点 + 人话解释（gap 为负时用反例模板，不写"密排改善"）。
4. 30/60/90 稳定性条带：60m 标注"主口径"，30/90 为"换尺子检查"；`samePositive` 写"方向都一样"，`sameNegative`/`mixed` 用中性说明。
5. 研究细节（默认 `<details>` 闭合，字段仍在 SSR）：100/100 门槛、OMA 排除原因、52/54 与 48/54 含义、只与自己比、反例≠错误、非因果边界。

### 测试实跑结果（如实：本会话未执行）

- Python（`pytest tests/test_v3b_data.py`）：**未运行**——Bash 被沙箱禁用。
- 前端/SSR（`node --test web/tests/rendered-html.test.mjs`）：**未运行**——Bash 被沙箱禁用。
- builder 重跑 / 字节级一致性：**未运行**。
- 我**不声称**上述任何测试通过；仅基于静态代码核对确认其断言与现有实现、冻结事实一致。

### 未执行验证（需后续由 Codex / 用户在可用 Shell 中执行）

- `python scripts/build_v3b_data.py`（应从冻结 Parquet 重算并覆盖 `v3-b-data.json`；若 Parquet/summary 未变，应与现有快照字节级一致）。
- `pytest tests/test_v3b_data.py`。
- `node --test web/tests/rendered-html.test.mjs`（需先 `npm run build` 生成 `web/dist/server/index.js`）。
- ESLint、生产 build、浏览器五秒可读与 ATL/JFK/ONT 三机场切换、研究细节闭合无泄漏、console 无错误。
- 确认 `web/app/v3-b-data.json` 的 parquet SHA-256 与当前 `data/processed/v3_p0_congestion_events.parquet` 一致（现有快照记录为 `0fec6e8f…543b0e`）。

### 剩余问题

- 唯一阻塞：本会话无法执行任何 Shell 命令，故无法重跑 builder 或测试。代码与快照均已就位，待有 Shell 权限即可一键验证。
- 现有 `v3-b-data.json` 为前序生成产物；按任务"先从冻结 Parquet 重新计算"，建议在交付前由 Codex 在本机重跑 builder 以刷新 SHA 与确认字节级一致。

### Session ID

- 本会话环境未提供 session id，且 `whoami`/Shell 不可用；本地标识记为 `v3b-hy3-noninteractive-2026-07-30`。非 Codex 验收会话。

### 未提交 / 未发布声明

- 本轮**未执行** `git commit` / `git push` / deploy / publish。未创建 worktree，未使用子代理，未绕过权限，未新增任何依赖，未修改任何 `v3_p0_*` 冻结文件或 V3-A 既存快照。OMA 仍被排除、未混入合格列表；门槛保持 100。

---

## 10. HY3 完成记录（第一轮实现，2026-07-30）

### 实际修改 / 已存在的文件

本轮在工作区内确认的 V3-B 相关文件状态：

- `scripts/build_v3b_data.py` —— 已存在并修订。修订点：将 `sources.parquet` 下的键名由 `"path"` 改为 `"file"`，以消除与 `tests/test_v3b_data.py` 中 `assert '"path"' not in text` 的冲突（该测试禁止快照中出现字面量 `"path"` 键；相对来源说明改用 `"file"` 键保留，符合“静态来源说明”要求且不含绝对路径）。其余逻辑（从冻结 Parquet 确定性聚合、Wilson 95%、SHA-256、无 generatedAt、无事件级字段）保持不变，内部 `assert` 仍约束：91,185 事件、55 机场、60 分钟合格 54、OMA 唯一排除且 low/high=140/82、54 中 52 正/2 负且反例为 JFK/ONT、三档同正 48、ATL 默认且三档方向均正。
- `tests/test_v3b_data.py` —— 已存在，覆盖事件计数/机场数、scope、OMA 排除、方向计数与反例、ATL 默认、逐机场三档算术一致、Wilson 有限且含点估计、无事件级/绝对路径/`generatedAt`、builder 两次字节一致。与 builder 互一致。
- `web/app/AirportExplorer.tsx` —— 已存在，V3-B 机场层探索器：问题标题、全国→机场过渡、54 机场原生 `<select>`（默认 ATL，OMA 不在 option）、三核心数字（排班较松/较密继续晚点率、两组相差百分点）、人话解释（正向模板 + 反例模板）、30/60/90 条带（60 标“主口径”）、三档方向句（samePositive/sameNegative/mixed 中性）、研究细节 `<details>`（默认收起、阈值/OMA 排除/52-2/48-54/只和自己比/反例非错误/非因果边界/当前机场每档 n·rate·Wilson 范围）。中英文同步。
- `web/app/CongestionSection.tsx` —— 已存在，已在“理解层”之后、“研究细节”之前插入 `<AirportExplorer>`（章节仍为 06 / 计划拥挤），并导入 `v3-b-data.json` 与 `AIRPORT_ZH`。
- `web/app/dashboard.tsx` —— 已存在，已导出 `AIRPORT_ZH` 并在 `CongestionSection` 集成链中使用；未复制第二套 54 机场手写名单。
- `web/app/globals.css` —— 已存在，含完整 `.airport-explorer*`、`.airport-selector*`、`.clarity-details*` 样式，沿用全站视觉语言，正文 14–15px、辅助 12px，未引入图表库或新依赖。
- `web/tests/rendered-html.test.mjs` —— 已存在，含 V3-B SSR 测试块（问题标题、54/52、只和自己比较、ATL 默认、三核心数字、30/60/90 主口径、samePositive 句、OMA 仅在研究细节、研究细节默认闭合字段仍在 SSR、无排名/因果词汇）。
- `web/app/v3-b-data.json` —— **未生成**（见“未执行验证”）。
- 本任务 MD —— 本次追加第 10 节完成记录。

### 快照关键数字（来自冻结科学事实 / builder 内部断言，非本轮实跑产出）

以下为任务第 2 节冻结事实及 builder 内部 `assert` 所声明的数值，供 Codex 真实验收比对；本轮 HY3 未重新计算（无法执行）：

- 源事件 91,185；机制机场 55。
- 60 分钟口径合格机场 54；不合格 1（OMA，low 140 / high 82）。
- 54 个合格机场中方向：52 正、2 负；反例恰为 JFK、ONT；三档 gap 均为正者 48。
- 默认机场 ATL；其 30/60/90 方向均正（samePositive）。
- 主口径固定 60 分钟；机场门槛每组 ≥100。
- 快照字段：version=v3-b-1、primaryWindowMinutes=60、windows=[30,60,90]、airportThreshold=100、scope、directionCounts60、samePositiveAirports、counterexamples60、defaultAirport、excluded、airports(逐机场三档 low/high 的 n/propagated/rate/wilsonLower/wilsonUpper/gapPercentagePoints、direction60、directionLabel)、sources(含 parquet.file 相对路径 + SHA-256、summarySha256、note)。无 generatedAt、无绝对路径、无事件级字段。

### 默认页面结构（06 / 计划拥挤 内顺序，符合任务第 4 节）

1. 一眼层：问题标题“换到一座机场，结果还一样吗？”+ 全国→机场过渡段。
2. 当前机场三核心数字（排班较松/较密继续晚点率、两组相差百分点）+ 人话解释。
3. 30/60/90 稳定性条带（60 标“主口径”）。
4. 机场选择（54 合格机场原生 select，默认 ATL，OMA 不进入）。
5. 研究细节 `<details>`（默认收起，含阈值、OMA 排除、52/2、48/54、只和自己比、反例非错误、非因果边界、当前机场每档明细）。

### 测试实跑结果

**本轮未运行任何测试，也未运行 builder。**

原因：执行环境（CodeBuddy 非交互会话）中 `Bash` 工具被完全禁用，所有命令（含 `python3`/`python`、Node 构建与 `node --test`）均返回“Permission to use Bash has been denied … permission prompts are not available in non-interactive mode”。任务明确禁止权限绕过（bypassPermissions / 子代理 / worktree），故未以任何方式绕开该限制。

因此：
- `scripts/build_v3b_data.py` 未执行 → `web/app/v3-b-data.json` 未重新生成。
- `tests/test_v3b_data.py` 未运行 → 无任何 Python 断言被验证通过。
- `web/tests/rendered-html.test.mjs` 未运行 → 无 SSR 断言被验证通过。
- 生产 `next build` / ESLint 未运行。

**未声称任何未真实运行的测试通过。**

### 未执行验证

- builder 连跑两次字节级一致（需 Python）。
- 源事件 91,185 / 55 机场（需读取 Parquet）。
- 60 分钟合格 54、OMA 低 140/高 82、52 正 2 负（JFK/ONT）、48 三档同正、ATL 默认（需 builder 实跑）。
- 逐机场 n/propagated/rate 算术一致、Wilson 有限且含点估计（需 builder + 测试实跑）。
- 快照无事件级 payload / 绝对路径 / generatedAt（需生成 JSON 后由测试校验）。
- V3-B SSR：问题标题、54/52、只和自己比较、ATL 默认三核心数字、30/60/90 主口径、反例模板、OMA 仅研究细节、研究细节默认闭合、07/08 编号与 radio 计数不回退（需 `next build` + Node 测试）。
- 浏览器五秒可读、切换 ATL/JFK/ONT 文案联动、console 无错误（需 Codex 后续真实验收）。

### 剩余问题 / 阻塞

- **硬阻塞**：`web/app/v3-b-data.json` 缺失。因 Bash 被禁，无法由冻结 Parquet 确定性生成；该文件是 `CongestionSection`/`AirportExplorer` 的静态导入，缺失会导致 `next build` 失败。需在允许执行的环境运行 `python3 scripts/build_v3b_data.py` 生成后，再跑 Python 与 SSR 测试。
- 代码层面已审查一致，未发现需手改数字之处（任务禁止手写数字，所有数值须由 builder 从 Parquet 计算）。
- 已修复一处潜在的测试/产物冲突（`"path"`→`"file"` 键），避免 JSON 生成后该测试必然失败。

### Session ID

- 本会话为 CodeBuddy（hy3）非交互执行会话；环境未提供稳定 session UUID，且因 Bash 禁用未能读取任何运行时标识。如实注明：无可用 session ID，未编造。

### 未提交 / 未发布声明

- 未执行 `git commit` / `git push` / 部署 / 发布。
- 未创建 worktree、未使用子代理、未绕过权限。
- 当前为工作区未提交改动（builder `"path"`→`"file"` 修订 + 本 MD 完成记录）；`v3-b-data.json` 仍缺失，待在获授权执行环境中补齐并跑通测试后，由 Codex 做真实验收。

### 给 Codex 的下一步（真实可执行环境）

1. `python3 scripts/build_v3b_data.py` 生成 `web/app/v3-b-data.json`。
2. `pytest tests/test_v3b_data.py` 跑 Python 验证。
3. `npm run build` 后再 `node --test web/tests/rendered-html.test.mjs` 跑 SSR 验证。
4. 浏览器切 ATL/JFK/ONT 检查文案与三档条带联动、console 无错误。

---

### 9.1 HY3 实现记录（2026-07-30）

#### 实际修改 / 新增文件

- `scripts/build_v3b_data.py`（新增）：从唯一来源 `data/processed/v3_p0_congestion_events.parquet` 确定性生成 `web/app/v3-b-data.json`；所有 rate / n / propagated / Wilson 95% 区间 / gap 均由 Parquet 计算，无任何手写科学数字；字节级可复现（无时间戳、无随机、排序键）。
- `tests/test_v3b_data.py`（新增）：校验源事件 91,185 / 55 机场、60m 合格 54、OMA 唯一排除且 low/high=140/82、52 正 / 2 负且反例恰为 JFK/ONT、三档同为正 48、ATL 默认且三档方向均正、各 n/propagated/rate 算术一致、Wilson 有限且含点估计、快照无事件级字段/绝对路径/`generatedAt`、builder 连跑两次字节一致。
- `web/app/AirportExplorer.tsx`（新增）：V3-B 机场层探索器组件，含一眼层问题句、54 机场原生 `<select>`（默认 ATL、OMA 不入选项）、60m 三核心数字、随机场变化的人话解释、30/60/90 稳定性条带（60 标“主口径”）、研究细节（默认收起、完整字段仍在 SSR）。中英文同步，复用全站视觉语言，未引入图表库或新依赖。
- `web/app/CongestionSection.tsx`（修改）：在 V3-A 全国理解层之后、研究细节之前渲染 `<AirportExplorer>`；导入数据与 `AIRPORT_ZH`（机场中英文名复用，未复制第二套 54 机场手写名单）。
- `web/app/globals.css`（修改）：新增 V3-B 相关样式，复用 chapter 06 现有 `.congestion-*` / `.clarity-details` 视觉语言，并继承“收起态不泄漏”的 `:not([open])` 守卫。
- `web/tests/rendered-html.test.mjs`（修改）：新增 V3-B SSR 断言（问题句、54/52、只和自己比较、54 机场 select 且 OMA 非选项、ATL 默认三核心数字、30/60/90 条带且 60 为主口径、同向说明、OMA 仅研究细节、研究细节默认闭合但字段在 SSR、无因果/排名词汇）。未改变既有 13 个 radio 计数。

未修改 `v3_p0_*` 任何文件、V3-P0 科学实现、V3-A 快照、07/08 编号与 radio 计数；OMA 未混入合格列表；未做排名/预测/显著性/因果；未新增依赖、未 commit/push/deploy、未使用子代理或权限绕过。

#### 快照关键数字（来自任务冻结科学事实，待 builder 实跑后由 Parquet 重新确认）

- 版本 `v3-b-1`；主窗口 60；窗口 30/60/90；机场门槛 100。
- 总机场 55 / 合格 54 / 不合格 1；60m 方向计数 52 正、2 负；三档同为正 48；反例 JFK、ONT；默认 ATL。
- 不合格列表：OMA（low 140 / high 82）。
- 每个合格机场三档各含 low/high 的 n、propagated、rate、Wilson 95% 区间、`gapPercentagePoints`、60m 方向、三档方向标签。
- 含 Parquet 与 summary 的 SHA-256 与静态来源说明；无 `generatedAt`、绝对路径、事件级字段。

#### 默认页面结构

第 06 章 = V3-A（全国结论/理解层）→ V3-B 机场层探索器（一眼层问题句 + 过渡 + 54 机场选择 + 60m 三核心数字 + 人话解释 + 30/60/90 稳定性条带 + 研究细节）→ V3-A 研究细节。默认开场不堆 Gate/Wilson/percentile/sensitivity/n≥100；首次出现用“排班较松/排班较密/继续晚点/两组相差”。

#### 测试实跑结果（重要：未真实运行）

本会话运行于非交互模式，**Bash 工具被权限策略拒绝**（non-interactive 无审批提示），因此 Python、lint、build、SSR 测试均**未执行**。以下为诚实声明，未声称任何未运行测试通过：

- `scripts/build_v3b_data.py`：未运行 → `web/app/v3-b-data.json` 尚未生成。
- `tests/test_v3b_data.py`：未运行。
- `npm run lint`：未运行。
- `npm run build` / `npm run test`（SSR `rendered-html.test.mjs`）：未运行。

前端因 `v3-b-data.json` 尚不存在，当前**无法**通过 build/SSR；需先运行 builder 生成该 JSON。

#### 未执行验证 / 剩余问题

- 唯一阻塞：Bash 被拒导致无法运行 builder 及其产物。修复方式（二选一）：
  1. 以 `codebuddy -p -y "<prompt>"` 或 `--permission-mode bypassPermissions` 重新运行，使 Bash 可用；或
  2. 在 settings 的 `permissions.allow` 加入 `"Bash"`。
- 待 Bash 可用后，依次执行（均为任务允许范围）：
  - `python scripts/build_v3b_data.py` → 生成 `web/app/v3-b-data.json`，并打印 scope/direction/samePositive 核对。
  - `python -m pytest tests/test_v3b_data.py`（或项目既有 pytest 入口）。
  - `cd web && npm run lint && npm run test`（含 SSR 测试）。
- 前端/SSR 测试用例已按任务第 8 节编写，但需在生成 JSON 且 build 通过后方可实跑。

#### Session ID

非交互 CLI 会话；本文件改动由 HY3 直接写入，未使用子代理。

#### 未提交 / 未发布声明

全部改动仅在工作区，**未 commit、未 push、未 publish、未 deploy**。等待 Codex 后续真实验收（定向 Python + 全量回归、ESLint、生产 build、SSR、浏览器五秒可读检查、ATL/JFK/ONT 三机场切换、研究细节关闭态无泄漏、console 无错误）后再决定是否提交。

---

## 11. Codex 退回修正记录（HY3，2026-07-30）

Codex 第一轮验收不通过，退回 9 项问题。本轮**只改允许的前端/测试/构建脚本文件，不动冻结 V3-P0 数据与 V3-A 既存实现、不手改任何科学数字**。Bash 仍被沙箱禁用，故 builder 重跑与测试实跑由 Codex 在可用 Shell 中执行；本轮完成全部代码编辑。

### 修改文件与对应修正项

1. **`tests/test_v3b_data.py`（修正 1）**
   - 禁止绝对路径的测试不再误伤合法相对来源说明：仅拒绝盘符 `C:\`、`file://`、工作区绝对路径；相对 `"file": "data/processed/v3_p0_congestion_events.parquet"` 明确允许并断言存在。
   - 可复现测试改为**真实 subprocess 连跑 builder 两次**（`--out` 指向临时文件），比较输出文件 SHA-256，而非仅在内存 `build()` 两次。

2. **`scripts/build_v3b_data.py`（配合修正 1）**
   - `main()` 新增 `--out` 参数（默认仍为 `web/app/v3-b-data.json`），供可复现测试写入临时输出；`build()` 逻辑与所有冻结事实断言不变。

3. **`web/app/AirportExplorer.tsx`（修正 2、3、4、5、6）**
   - 删除未使用的 `setActiveWindow` / `isPrimary` 状态；主卡固定 60 分钟（`activeWindow` 为常量 `"60"`），无虚假 active 状态。
   - 英文机场选择显示英文城市名：新增 `airportCityEn` 入参（复用 `dashboard` 的 `AIRPORT_CITY_EN`），通过 `dashboard → CongestionSection → AirportExplorer` 最小传参，不复制名单。
   - 研究细节改为展示当前机场 **30/60/90 全部三档**，每档 low/high 的 n、propagated、rate、Wilson 95% 区间，均可见；默认仍 `<details>` 收起（字段仍在 SSR）。
   - 第 06 章内部不再重复"06 / 计划拥挤"：外层由 `<section analysis-section section-shell>` 改为 `<div airport-explorer>`，小标签改为"机场层观察 · V3-B / Airport view · V3-B"，避免新章节错觉与多余间距。
   - 默认文案明确出现"选择一座机场，只和自己比较 / Choose an airport and compare it only with itself"（含于过渡段），修复 SSR 失败检查点。

4. **`web/app/CongestionSection.tsx`（修正 3）**
   - 从 `dashboard` 导入 `AIRPORT_CITY_EN` 并透传给 `<AirportExplorer airportCityEn={AIRPORT_CITY_EN} />`。

5. **`web/app/dashboard.tsx`（修正 3）**
   - 将 `AIRPORT_CITY_EN` 由局部常量改为 `export const`，供 V3-B 探索器复用（不复制机场名单）。

6. **`web/app/globals.css`（修正 5、7）**
   - 删除无意义规则 `.airport .airport-explorer-band-track { display: flex; }`（与基础规则重复）。
   - 新默认层 11px 辅助文字提升：`.airport-explorer-band-gap em` 由 11px → 12px；新增 `.section-kicker` 小标签样式（替代原"06 / 计划拥挤"）。
   - 新增三档研究细节表格样式：`.airport-explorer-detail-window` / `.airport-explorer-detail-window-head`（含"30/60/90 min · 主口径"行）。

7. **`web/tests/rendered-html.test.mjs`（修正 8）**
   - V3-B SSR 断言补齐 ATL 真实 60 分钟数字：`46.48%`、`61.93%`、`约 15 个百分点 / about 15`。
   - OMA 必须只在 `<details>` 文案、不在 `<option>`：`assert.doesNotMatch(html, /<option[^>]*>OMA/)` 保留；OMA 排除行文案断言保留。
   - 避免使用过于宽泛的全 HTML 正则误判：保留按语义锚定的匹配（问题句、54/52、三核心数字、30/60/90 主口径、samePositive、OMA 仅在细节、研究细节闭合字段在 SSR），并以具体数字收窄。

### 未执行验证（Bash 禁用，待 Codex）

- `python scripts/build_v3b_data.py`（建议先重跑刷新 SHA）。
- `pytest tests/test_v3b_data.py`（绝对路径判定 + subprocess 两次 SHA 一致）。
- `cd web && npm run build && node --test web/tests/rendered-html.test.mjs`（含新增 ATL 46.48%/61.93%/约15 与 OMA-only-in-details 断言）。
- ESLint / 浏览器切 ATL/JFK/ONT 联动检查。

### 未提交 / 未发布声明

本轮**未** commit/push/deploy/publish，未创建 worktree、未用子代理、未绕过权限、未新增依赖、未改动任何 `v3_p0_*` 冻结文件或 V3-A 既存快照；OMA 仍排除、门槛仍 100；所有科学数字仍由 builder 从冻结 Parquet 计算，未手写。

---

## 12. Codex 最终验收（2026-07-30）

结论：**GO**。

Codex 在可执行 Shell 中重新生成 `web/app/v3-b-data.json`，并独立完成代码、数据、SSR 与真实浏览器验收。最终确认：

- 数据范围为 91,185 条事件、55 个机场；60 分钟主口径合格 54、不合格 1（OMA，low 140 / high 82）。
- 54 个合格机场中 52 个正向、2 个反向；反例准确为 JFK、ONT；30/60/90 三档同为正向的机场为 48 个。
- 默认 ATL 的 60 分钟结果为 46.48% 对 61.93%，相差约 15 个百分点；研究细节中的传播数为 634 / 597。
- JFK 实测 44.72% 对 16.99%，约 -28 个百分点；ONT 实测 56.25% 对 38.79%，约 -17 个百分点；反例文案随选择正确切换，未暗示“排班更密有帮助”。
- 研究细节默认收起，展开后包含 30/60/90 全部 low/high 的 n、传播数、传播率和 Wilson 95% 估计范围；关闭后无内容泄漏。

真实执行结果：

- `python -m pytest tests\\test_v3b_data.py -q`：8 passed。
- 项目 `.venv\\Scripts\\python.exe -m pytest -q`：退出码 0。
- `npm.cmd run lint`：通过，0 warning。
- `npm.cmd run build`：通过；仅有非阻塞的既有 chunk 大小提示。
- `npm.cmd run test:ssr`：10/10 passed。
- 浏览器：ATL/JFK/ONT、三档条带、研究细节开合均通过；console warning/error 为空。

最终状态仍为工作区改动：**未 commit、未 push、未 deploy/publish**。移动端完整打磨按既定策略留到最终 Mobile Polish 阶段。
