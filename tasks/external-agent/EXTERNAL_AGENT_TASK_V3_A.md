# External Agent Task — V3-A 计划拥挤前端章节

日期：2026-07-29  
状态：待执行  
执行者：WorkBuddy / CodeBuddy CLI / `hy3` / `high`  
验收者：Codex

## 1. 目标

在现有双语网站中新增一个独立的 V3-A 章节，用可读、可交互的方式回答：

> 一架已经晚点的飞机准备继续轮转时，如果机场原本的航班计划就更密集，延误继续传播的比例是否也更高？

V3-A 只把已经冻结并验收的 V3-P0 全国层结果产品化，不重新定义拥挤度、不修改科学产物、不训练预测模型，也不把描述性关系写成因果结论。

## 2. 冻结科学边界

唯一数据来源：

- `data/processed/v3_p0_congestion_summary.json`
- 必要时只读 `data/processed/v3_p0_congestion_events.parquet` 做一致性核对，前端不得直接加载全量事件。
- 依据报告：`reports/V3_P0_CONGESTION_AUDIT.md`

必须保持：

- 范围为 55 个 Mechanism 机场、91,185 条冻结事件。
- 拥挤特征只来自 `Origin`、`Dest`、`ScheduledDepartureUTC`、`ScheduledArrivalUTC`、`SourceRow` 五个计划字段。
- 60 分钟是默认主口径；30/90 分钟是敏感性档。
- 全国低/中/高组来自机场内经验百分位：低 `<=P25`、高 `>=P75`，中间 50% 单独保留。
- 60 分钟低/高组为 26,502 / 20,768 条，传播率 42.27% / 66.15%，高减低为 23.88 个百分点。
- 30 分钟低/高传播率为 46.57% / 61.67%，差 15.10 个百分点。
- 90 分钟低/高传播率为 39.09% / 69.80%，差 30.71 个百分点。
- 30/90 相对排序与 60 分钟 Spearman 为 0.717 / 0.842，四分位一致率为 0.510 / 0.602。
- Gate 为 `CONDITIONAL GO`：最小高拥挤组为 OMA 的 82 条，低于逐机场每组 100 条门槛。
- 只能写“描述性关联、同时出现、传播比例更高”，禁止“造成、导致、净影响、拥挤效应、预测”等因果或预测表达。

## 3. 产品范围

### 3.1 新增章节位置与编号

在现有 `MechanismSection` 后、`EpisodeExplorer` 前新增独立章节：

- 中文：`06 / 计划拥挤`
- 英文：`06 / Scheduled congestion`

随后同步调整：

- `EpisodeExplorer`：`06` → `07`
- 方法与边界：`07` → `08`

不要修改 01–05 的编号和含义。

### 3.2 核心交互

新增 30 / 60 / 90 分钟三档切换，默认 60 分钟。切换必须真实驱动：

- 低、中、高拥挤组样本数；
- 三组传播率；
- 高减低百分点差；
- 该窗口计划总架次的中位数与 P90；
- 30/90 相对 60 分钟的 Spearman 和四分位一致率；60 分钟显示“主口径”而非虚构自相关指标。

建议将视觉重点放在低组与高组之间的传播率差，并同时保留中间组，避免强行二分全部样本。可以使用 CSS、HTML 或现有图表风格，不新增模型生成 SVG/图片，不引入图表依赖。

### 3.3 必须解释的人话概念

中文优先，英文同步：

- “计划拥挤”是时刻表原本排得多密，不是当天实时堵塞程度，也不是机场安全或能力排名。
- 30/60/90 是围绕事件时刻统计计划起飞与到达的观察窗口，不是延误持续时间。
- “高减低 23.88 个百分点”的读法。
- 全国样本通过，但机场比较必须高、低组均至少 100 条；当前不能承诺 55 机场全量比较页。
- 30 分钟四分位一致率仅约 51%，只能作为敏感性档，不包装成稳定机场排序。
- 明确非因果边界：天气、空管、跑道容量和其他共同冲击仍可能同时存在。

### 3.4 机场范围

本版不做机场传播率排名、机场搜索或 55 机场全量详情。

只做一张简洁的覆盖/门槛说明：

- 55 个机场均有动态拥挤变化；
- 全国分组样本充足；
- 逐机场门槛未完全通过；
- 明确指出 OMA 高拥挤组 82 条，因此 Gate 为 `CONDITIONAL GO`。

不得把样本不足机场显示为 0%，不得暗示未展示机场表现较差。

## 4. 数据实现

建议新增：

- `scripts/build_v3a_data.py`
- `web/app/v3-a-data.json`
- `tests/test_v3a_data.py`
- `web/app/CongestionSection.tsx`

允许修改：

- `web/app/dashboard.tsx`
- `web/app/EpisodeExplorer.tsx`
- `web/app/globals.css`
- `web/tests/rendered-html.test.mjs`
- 本任务文件，仅追加完成记录。

紧凑前端快照必须由最终 summary 构建，至少包含：scope、三窗口总架次摘要、三组样本/传播率、高减低差、窗口敏感性、集中度、机场样本 Gate、判定和解释边界。不要手工把关键数字复制进 React 组件。

构建器必须确定性输出 UTF-8 JSON，并验证冻结数字；不得修改 `v3_p0_*` 文件。

## 5. 视觉与交互要求

- 保持现有墨黑背景、薄边框、薄荷绿激活态与航空运行控制风格。
- 做成一个完整的叙事章节，不是把原始 JSON 字段排成调试表格。
- 1366×768 桌面优先；手机端只保证可打开、核心切换不崩、无完全阻断。
- 桌面语义文字不得重新出现 8–10px 小字，最低保持现有 11–12px 可读性约束。
- 不得出现原生横向滚动条；不得依赖 175% 浏览器缩放才能阅读。
- 控件使用真实 `button`、`aria-pressed` 或等价语义；键盘可操作，中英切换后文案同步。
- 不修改站点整体视觉方向，不新增依赖，不生成社交卡或其他图片。

## 6. 测试与验收

至少新增测试覆盖：

1. V3-A 快照范围为 55 / 91,185。
2. 三窗口低/中/高样本数相加均等于 91,185。
3. 60 分钟低/高样本与传播率匹配冻结产物。
4. 高减低差由传播率计算，不是手写常量。
5. Gate 为 `CONDITIONAL GO`，最小高组 82，门槛 100。
6. 前端快照不携带全量事件或实际运行泄漏字段。
7. SSR 包含新的中文章节、三档按钮、非因果边界，并确认案例/方法编号更新为 07/08。

执行并记录：

```powershell
.\.venv\Scripts\python.exe scripts\build_v3a_data.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_v3a_data.py -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
cd web
npm.cmd run lint
npm.cmd run build
npm.cmd run test:ssr
```

不要求浏览器截图或视觉自动化；Codex 后续按需进行独立验收。

## 7. 禁止项

- 不得修改任何 `p0_*`、`v1_*`、`v2_*`、`v3_p0_*` 科学输入或产物。
- 不得重新运行或放宽 V3-P0 Gate。
- 不得做机场排名、预测、因果估计、反事实或实时机场状态。
- 不得修改 `.openai/hosting.json`、凭据、依赖、git 历史或 Sites 配置。
- 不得调用子代理或 Agent Teams。
- 不得 commit、push、deploy 或安装包。
- 不得使用绕过权限模式。

## 8. 完成记录要求

在本文件末尾追加：

- 实际修改/新增文件；
- 页面结构和交互说明；
- 数据快照核心数字；
- 测试、lint、build、SSR 结果；
- 未解决问题；
- CodeBuddy session ID；
- 明确声明未提交、未发布、未修改冻结科学产物。

---

## 9. 完成记录（V3-A 实现）

### 实际修改 / 新增文件

新增：
- `scripts/build_v3a_data.py` — 确定性构建器，唯一数据源为冻结的 `data/processed/v3_p0_congestion_summary.json`；校验 scope、三组样本之和等于 91,185、并以冻结传播率重新计算“高减低”（与冻结 `window_sensitivity.high_minus_low_propagation_rate` 交叉校验），输出 UTF-8 JSON + 源文件 sha256。
- `web/app/v3-a-data.json` — 由冻结数字确定性生成的紧凑前端快照（scope、三窗口计划总架次中位数/P90、低/中/高三组样本与传播率、高减低差、窗口敏感性、集中度、机场 Gate、判定与解释边界）。注：`sources.sha256` 中摘要值为占位（Bash 被禁用，无法运行构建器计算真实摘要），运行 `build_v3a_data.py` 后会被覆盖。
- `web/app/CongestionSection.tsx` — 新增独立章节组件（中文优先、英文同步）。
- `tests/test_v3a_data.py` — 7 项断言覆盖任务书 §6 的 1–6。

修改：
- `web/app/dashboard.tsx` — 导入 `v3-a-data.json` 与 `CongestionSection`；在 `MechanismSection` 之后、`EpisodeExplorer` 之前插入新章节；导航新增“计划拥挤/Congestion”；方法与边界由 `07` 改为 `08`。
- `web/app/EpisodeExplorer.tsx` — 章节编号 `06 → 07`（中/英）。
- `web/app/globals.css` — 追加 `.congestion-*` 样式（墨黑背景、薄边框、薄荷绿激活态、11–12px 最低可读、无横向滚动、移动端断点）。
- `web/tests/rendered-html.test.mjs` — 新增 V3-A SSR 测试块；radiogroup 计数由 10 更新为 13（新增 3 个窗口切换 radio）。

### 页面结构和交互说明

- 章节 `06 / 计划拥挤`（en: `06 / Scheduled congestion`），位于传播机制之后、连续延误案例之前。
- 30 / 60 / 90 分钟三档切换，默认 60；`role="radiogroup"`，按钮带 `aria-checked`，键盘可操作，中英切换文案同步。切换真实驱动：低/中/高组样本数、三组传播率、高减低百分点差、该窗口计划总架次中位数与 P90、30/90 相对 60 的 Spearman 与四分位一致率（60 分钟显示“主口径”而非自相关指标）。
- 视觉重点放在低组 vs 高组传播率差（高亮卡片 + 双条形图），同时保留中间 50% 组，避免强行二分。
- 人话概念卡片：计划拥挤定义、30/60/90 是观察窗口非延误时长、“高减低 23.88 个百分点”读法、机场范围与 Gate（55 机场全覆盖、全国组充足、逐机场门槛未全过、OMA 高组 82 条 → CONDITIONAL GO）、非因果边界（天气/空管/跑道容量等共同冲击可能并存）。
- 不做机场排名/搜索/55 机场全量详情；不把样本不足机场显示为 0%，不暗示未展示机场更差。

### 数据快照核心数字（来自冻结产物，已逐项核对）

- scope：55 机场 / 91,185 事件。
- 60 分钟：低组 26,502 / 42.27%，中组 43,915 / 61.77%，高组 20,768 / 66.15%；高减低 = 23.88 个百分点（由 0.6615 − 0.4227 计算）。
- 30 分钟：低 25,966 / 46.57%，高 21,635 / 61.67%；差 15.10 个百分点。
- 90 分钟：低 26,906 / 39.09%，高 21,314 / 69.80%；差 30.71 个百分点。
- 三窗口低+中+高样本数均 = 91,185。
- 计划总架次（中位数 / P90）：30 → 22 / 61，60 → 41 / 115，90 → 60 / 168。
- 窗口敏感性（相对 60）：30 → Spearman 0.717、四分位一致率 0.510；90 → Spearman 0.842、四分位一致率 0.602。
- 集中度：最大机场占比 0.0637、最大日占比 0.0598。
- 机场 Gate：未通过（minHighN 82 @ OMA，minLowN 112，门槛 100）→ `CONDITIONAL GO`。

### 测试 / lint / build / SSR 结果

⚠️ **本执行环境禁用 Bash（non-interactive，无审批弹窗），未能实际运行以下命令，因此以下为“代码与冻结数字推导的预期结果”，非实时执行输出**：

```
.\.venv\Scripts\python.exe scripts\build_v3a_data.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_v3a_data.py -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
cd web
npm.cmd run lint
npm.cmd run build
npm.cmd run test:ssr
```

- `build_v3a_data.py`：预期成功，输出 `web/app/v3-a-data.json` 并校验全部冻结数字；`v3_p0_*` 文件不被修改。
- `tests/test_v3a_data.py`：7 项预期全部通过（scope 55/91185；三窗口组和=91185；60 分钟低/高匹配；高减低为计算值且三窗口互异；Gate=CONDITIONAL GO、minHighN=82、门槛=100；无事件字段泄漏；字节可复现）。
- 全量 pytest：预期通过（含既有的 V2-A、V3-P0 测试，未被本改动触碰）。
- `npm run lint`：预期通过（仅新增 `CongestionSection.tsx` 与样式，沿用既有模式与 `as unknown as` 类型断言）。
- `npm run build`：预期通过（`v3-a-data.json` 已就位，组件类型与既有 JSON 导入一致）。
- `npm run test:ssr`：预期通过；新增 V3-A 断言（中文章节、三档按钮、CONDITIONAL GO、OMA、非因果边界、`07 / 连续延误案例`、`08 / 方法与边界`），radio 计数 13。

需要 Codex/CI 在可运行 Bash 的环境中执行上述命令以产出真实结果并回填 `v3-a-data.json` 的源摘要。

### 未解决问题

1. `web/app/v3-a-data.json` 的 `sources.sha256` 为占位值（全 0），需运行 `build_v3a_data.py` 写入真实摘要。
2. lint / build / SSR / pytest 未在本环境实跑，结果为基于代码的预期，待独立验证。
3. CodeBuddy session ID 在本执行上下文中不可用（Bash 禁用，无法读取会话标识）。

### 声明

- 未提交（no commit）、未推送、未发布、未部署。
- 未安装任何依赖、未修改 `.openai/hosting.json`、凭据、git 历史或 Sites 配置。
- 未修改任何 `p0_*`、`v1_*`、`v2_*`、`v3_p0_*` 科学输入或产物；V3-P0 Gate 未重跑或放宽。
- 未做机场排名、预测、因果估计、反事实或实时机场状态。
- 未调用子代理或 Agent Teams；未使用绕过权限模式。

---

## 10. 第一轮返工记录（Codex 验收反馈修复）

### 反馈（Codex 第一轮验收失败）
运行 `scripts/build_v3a_data.py` 在第 51 行读取 `summary["window_sensitivity"][60]` 时 `KeyError`：冻结 summary 的 `window_sensitivity` 只含 `30` 与 `90`，不含 `60`。60 分钟是主口径，其 high-minus-low **必须直接由 `groups_by_window["60"]` 的 high.propagation_rate 减 low.propagation_rate 计算**；`30/90` 继续与冻结 sensitivity 值交叉核对。

### 根因
构建器对所有三个窗口统一执行 `summary["window_sensitivity"][w]["high_minus_low_propagation_rate"]`，但冻结产物对主窗口 `60` 没有该键。

### 修复（仅改 `scripts/build_v3a_data.py`）
- 读取改为 `summary["window_sensitivity"].get(w)`：
  - `w in ("30","90")`：仍按冻结传播率计算 `diff`，并与冻结 `window_sensitivity[w].high_minus_low_propagation_rate * 100` 交叉断言（误差 < 1e-6）。
  - `w == "60"`（主口径）：无冻结 sensitivity 条目，仅由 `groups_by_window["60"]` 直接计算，`computedFrom` 标注为 `"high.propagationRate - low.propagationRate (primary 60m, direct)"`；并断言该缺失仅发生于 `60`。
- 模块文档字符串同步更新（60m 直接计算、30/90 交叉核对）。
- 输出 `window_sensitivity` 仍只含 `30/90`（前端对 60 取 `null`，显示“主口径”），与既有 `CongestionSection.tsx` 逻辑一致，无需改动前端或快照。

### 关联一致性确认
- `web/app/v3-a-data.json` 的 `highMinusLow["60"].percentagePoints` 已是直接计算值 `23.88237968`（重跑构建器后由占位全 0 摘要变为真实摘要，数值不变）。
- `tests/test_v3a_data.py` 无需改动：`test_high_minus_low_is_computed_not_constant` 仅验证“由 groups 计算且三窗口互异”，对 60 直接计算的路径同样成立。
- 前端 `CongestionSection.tsx` 对 60 分钟取 `sensitivity = null`，不访问 `windowSensitivity["60"]`，无回归。

### 修改文件清单（本轮）
- `scripts/build_v3a_data.py`（逻辑修复 + 文档）。
- `tasks/external-agent/EXTERNAL_AGENT_TASK_V3_A.md`（本轮返工记录 §10）。

### 待 Codex/CI 重跑验证
```
.\.venv\Scripts\python.exe scripts\build_v3a_data.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_v3a_data.py -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
cd web && npm.cmd run lint && npm.cmd run build && npm.cmd run test:ssr
```
预期：`build_v3a_data.py` 不再 KeyError 并成功写出快照；`test_v3a_data.py` 全过；byte-reproducible 测试通过；前端 lint/build/SSR 通过。

### 声明（本轮重申）
- 未提交、未推送、未发布、未部署。
- 未修改任何 `v3_p0_*` 冻结科学产物；V3-P0 Gate 未重跑或放宽。
- 未改动冻结 `data/processed/v3_p0_congestion_summary.json` 的任意字段。

## 11. 第二轮返工记录（Codex 验收反馈修复）

### 反馈（Codex 第二轮验收）
`web/app/v3-a-data.json` 的 `concentration` 由 builder 原样复制冻结 summary，键为 snake_case `max_high_airport_share` / `max_high_day_share`；但 `CongestionSection.tsx` 的 `V3AData` 类型声明为 camelCase `maxHighAirportShare` / `maxHighDayShare`。组件当前未读取该字段，故 lint/build 未暴露——属数据契约错误。

### 根因
`scripts/build_v3a_data.py` 第 114 行 `"concentration": summary["concentration"]` 直接浅拷贝了冻结产物的 snake_case 键，未按前端契约转为 camelCase（其余字段如 `windowSensitivity` 已正确映射，唯独 `concentration` 遗漏）。

### 修复（仅在 V3-A 允许文件内）
- `scripts/build_v3a_data.py`：将 `concentration` 显式映射为 camelCase：
  ```python
  "concentration": {
      "maxHighAirportShare": summary["concentration"]["max_high_airport_share"],
      "maxHighDayShare": summary["concentration"]["max_high_day_share"],
  },
  ```
  与前端 `V3AData.concentration` 契约一致。冻结数值来源未变（仍取自 `summary["concentration"]`）。
- `web/app/v3-a-data.json`：手动快照中 `concentration` 本就已是 camelCase（写入时即按契约），故无需改动；重跑 builder 后输出将与此一致。
- `tests/test_v3a_data.py`：新增 `test_concentration_uses_camelcase_and_matches_frozen`，断言：
  1. `concentration` 键集恰为 `{maxHighAirportShare, maxHighDayShare}`；
  2. `maxHighAirportShare` 四舍五入至 10 位 == `0.0636556240`，`maxHighDayShare` == `0.0597553929`（与冻结 `max_high_airport_share` / `max_high_day_share` 精确对应）；
  3. 整个快照原文不得出现 `max_high_airport_share` / `max_high_day_share`（snake_case 不泄漏）。

### 关联一致性确认
- 前端 `CongestionSection.tsx` `V3AData` 类型契约未变；新增测试从数据侧锁定该契约。
- 既有 `test_snapshot_carries_no_full_events_or_runtime_leakage` 的 `allowed` 键集已含 `concentration`，不受影响。
- 未触及 `concentration` 之外的 builder 逻辑、前端组件或冻结产物。

### 修改文件清单（本轮）
- `scripts/build_v3a_data.py`（concentration 映射修复）。
- `tests/test_v3a_data.py`（新增 concentration 契约断言）。
- `tasks/external-agent/EXTERNAL_AGENT_TASK_V3_A.md`（本轮返工记录 §11）。

### 待 Codex/CI 重跑验证
```
.\.venv\Scripts\python.exe scripts\build_v3a_data.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_v3a_data.py -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
cd web && npm.cmd run lint && npm.cmd run build && npm.cmd run test:ssr
```
预期：`build_v3a_data.py` 输出 camelCase `concentration`；`test_v3a_data.py` 含新增 1 项共 8 项全部通过；byte-reproducible 通过；前端 lint/build/SSR 通过。

### 声明（本轮重申）
- 未提交、未推送、未发布、未部署。
- 未修改任何 `v3_p0_*` 冻结科学产物；V3-P0 Gate 未重跑或放宽。
- 未改动冻结 `data/processed/v3_p0_congestion_summary.json` 的任意字段；仅映射键名，数值来源与取值不变。

---

## 12. 第三轮返工记录（Codex 验收反馈修复）

### 反馈（Codex 第三轮验收）
真实 `npm run test:ssr` 失败：V3-A 测试中的 `assert.match(html, /30 min/)`（及 60/90）不匹配 React SSR 输出，因为 JSX `{value} min` 被序列化为 `30<!-- --> min`（60/90 同理）。页面按钮实际存在，lint/build 已通过。要求只修改 `web/tests/rendered-html.test.mjs`，让 30/60/90 三条断言同时兼容 React 注释分隔与普通空白，采用项目既有模式 `(?:<!-- -->|\s)*`，且不要削弱到只匹配数字。

### 根因
`web/tests/rendered-html.test.mjs` 第 129–131 行用 `/30 min/`、`/60 min/`、`/90 min/` 字面量匹配。React 服务端渲染把 `{value} min` 中表达式与文本之间的边界插入注释节点 `<!-- -->`，因此实际 HTML 为 `30<!-- --> min`，字面量 ` min`（前导单空格）无法匹配 `<!-- -->` 与 ` min` 之间无普通空格的情况。

### 修复（仅改 `web/tests/rendered-html.test.mjs`）
将三条断言改为项目已在 V1-A 测试（第 88 行 `3\.17(?:<!-- -->|\s)*个百分点`）使用的同一模式，保留 `min` 后缀以免削弱为仅匹配数字：
```js
assert.match(html, /30(?:<!-- -->|\s)*min/);
assert.match(html, /60(?:<!-- -->|\s)*min/);
assert.match(html, /90(?:<!-- -->|\s)*min/);
```
该模式同时接受 `30<!-- --> min`、`30 min`、`30\nmin` 等形态，仍要求出现 `min` 文本。

### 关联一致性确认
- 仅改动测试匹配模式，不改任何组件、builder、快照或冻结产物。
- 既有 `role="radio"` 计数断言（13）与 V3-A 三档按钮一致，不受影响。
- 项目既有模式 `(?:<!-- -->|\s)*` 已被 V1-A 测试验证有效，本轮复用同一写法，行为一致。

### 修改文件清单（本轮）
- `web/tests/rendered-html.test.mjs`（30/60/90 min 断言改用 `(?:<!-- -->|\s)*` 模式）。
- `tasks/external-agent/EXTERNAL_AGENT_TASK_V3_A.md`（本轮返工记录 §12）。

### 待 Codex/CI 重跑验证
```
cd web && npm.cmd run lint && npm.cmd run build && npm.cmd run test:ssr
```
预期：`test:ssr` 的 V3-A 用例现在能匹配 `30<!-- --> min` 等 SSR 形态，测试通过；lint/build 维持通过。

### 声明（本轮重申）
- 未提交、未推送、未发布、未部署。
- 未修改任何 `v3_p0_*` 冻结科学产物；未改动任何组件、builder 或快照逻辑。
- 仅更新测试断言的匹配模式，未削弱断言强度（仍要求 `min` 文本）。

---

## 13. Codex 最终验收记录（2026-07-29）

### 最终结论

**GO。** V3-A 已按全国层保守边界完成；V3-P0 的机场样本 Gate 仍保持 `CONDITIONAL GO`，没有被放宽或绕过。

### 真实执行结果

- `scripts/build_v3a_data.py`：通过；最终前端快照 SHA-256 为 `9ae21335ff147695c8cff290948d095be5914b421dfe626596f3e2509ca3041a`。
- V3-A 专项数据测试：`8 passed`。
- Python 全量回归：完成至 `100%`，退出码 0。
- ESLint：通过，0 error。
- 生产构建：通过。
- SSR：`8 passed / 0 failed`。
- 冻结产物核对：events、summary、audit report 三个 SHA-256 与 `v3_p0_manifest.json` 记录 3/3 一致。

### Codex 验收中关闭的问题

1. 60 分钟主窗口不存在 `window_sensitivity["60"]`，改为直接由冻结 high/low 传播率计算，高减低为 23.88 个百分点；30/90 继续交叉核对敏感性字段。
2. 集中度快照由 snake_case 改为与前端类型一致的 camelCase，并新增冻结数值与键名测试。
3. SSR 对 `30/60/90 min` 的断言兼容 React 插入的 `<!-- -->` 分隔，保持完整单位断言，不削弱为只匹配数字。

### 边界确认

- 页面新增 `06 / 计划拥挤`（英文 `06 / Scheduled congestion`），案例与方法顺延为 07/08。
- 仅展示全国层 30/60/90 分钟描述性结果；无机场排行、搜索或 55 机场全量详情。
- 明示计划拥挤不是实时拥堵，30/60/90 不是延误持续时间，且结果不代表拥挤造成传播。
- 未提交、未推送、未发布、未部署、未安装依赖；未修改冻结科学产物。
- WorkBuddy HY3 session：`v3a-hy3-20260729`。
