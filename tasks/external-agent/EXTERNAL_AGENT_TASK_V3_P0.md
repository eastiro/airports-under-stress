# External Agent Task — V3-P0 计划拥挤度可行性审计

日期：2026-07-28  
状态：待执行  
执行者：Claude Code / `gpt-5.6-luna` / `xhigh`  
验收者：Codex

## 1. 目标

只做数据与科学可行性审计，回答：

> 能否仅使用事前可知的航班计划，在每条晚到轮转衔接发生时构造稳定、可解释的机场计划拥挤度，从而为后续 V3-A 提供新的网络压力层？

V3-P0 不实现前端、不拟合新的结果模型、不声称拥挤造成传播，也不使用实际运行结果构造拥挤特征。

## 2. 冻结输入

只读：

- `data/processed/p0_flights.parquet`
- `data/processed/p0_chain_links.parquet`
- `data/processed/v1_p0_airport_roles.parquet`
- V0/V1/V2 的现有科学产物与构建脚本仅供核对，不得修改。

事件范围固定为：

- `v1_p0_airport_roles.parquet` 中 `nExposed >= 500` 的 55 个 Mechanism 机场；
- `p0_chain_links.parquet` 中 `UpstreamArrDelayed15 == True` 的轮转衔接；
- 事件机场为 `Origin`，事件时刻为 `ScheduledDepartureUTC`；
- 不扩张到 347 机场，不替换或修改 P0.1、V2 的定义。

## 3. 计划拥挤度定义

只从 `p0_flights.parquet` 的以下计划字段构造特征：

- `Origin`、`Dest`；
- `ScheduledDepartureUTC`、`ScheduledArrivalUTC`；
- `SourceRow` 仅用于稳定行标识或核对。

不得读取或使用以下字段构造拥挤度：

- `DepTime`、`ArrTime`、`DepDelay`、`ArrDelay`；
- `ActualDepartureUTC`、`ActualArrivalUTC`；
- `TaxiOut`、`TaxiIn`、`WheelsOff`、`WheelsOn`；
- `Cancelled`、`Diverted` 作为筛选条件；
- `CarrierDelay`、`WeatherDelay`、`NASDelay`、`LateAircraftDelay` 等事后原因字段；
- `DownstreamDepDelayed15`、`PropagationSignal` 或任何结果派生字段。

注意：所有报表中的计划航班都进入计划需求底表，不因其事后取消或备降而删除。程序不需要读取取消/备降字段。

对每条事件计算三个居中窗口：

- 30 分钟窗口：`[event - 15m, event + 15m)`；
- 60 分钟窗口：`[event - 30m, event + 30m)`，主口径；
- 90 分钟窗口：`[event - 45m, event + 45m)`。

每档至少输出：

- 同机场窗口内计划出发数；
- 同机场窗口内计划到达数；
- 计划总架次 = 出发 + 到达；
- 其他计划出发数 = 出发数减去事件自身，必须 `>= 0`；
- 同机场相对拥挤度：以该机场全部计划出发事件的计划总架次分布为参考，生成确定性的经验百分位或数学上等价的相对位置；必须在报告中写清 reference population 和 tie 处理。

实现应使用按机场排序后的时间数组与 `searchsorted` 或同等级向量化方法；禁止对 60 万航班 × 9 万事件做笛卡尔连接。

## 4. 审计内容

至少审计：

1. 事件数与 55 机场范围是否与冻结 V2-B 基础事件一致；
2. 三档窗口的覆盖、缺失、最小值、中位数、IQR、P90、P99、最大值；
3. 逐机场样本量、distinct count、IQR、相对拥挤度四分位样本；
4. 至少 90% 的 55 机场是否存在 `IQR > 0` 的主窗口动态变化；
5. 高拥挤（机场内 >=P75）与低拥挤（<=P25）组的样本数和描述性传播率；中间 50% 单独保留，不强行二分全部样本；
6. 主窗口与 30/90 分钟窗口的 Spearman 相关、四分位一致率和结论方向；
7. 最大机场/最大单日对高拥挤样本的占比，避免全国结果由单一机场或单日支配；
8. 特征构造只依赖计划字段的自动测试；目标结果只允许在完成特征后用于描述性分组审计。

高/低组传播率仍只描述同时出现的现象，不是因果估计。不得用“拥挤效应”“净影响”“造成”等表述。

## 5. Gate

### GO

必须同时满足：

- 55/55 机场、冻结事件 100% 得到三档有限非负特征；
- 事件自身扣除后其他出发数无负数；
- 计划字段契约测试通过，无实际运行字段进入特征函数；
- 主窗口至少 50/55 机场 `IQR > 0`；
- 全国高/低四分位各至少 15,000 条事件，且每个进入后续机场比较的机场每组至少 100 条；
- 高拥挤样本中任一机场占比 <15%，任一单日占比 <10%；
- 30/60/90 分钟结果可复现、方向不因窗口轻微变化而完全翻转；
- 连续两次完整构建的所有科学产物 SHA-256 字节一致。

### CONDITIONAL GO

- 全国层面稳定，但逐机场变化或高/低样本不足；
- 后续只能做全国/分组审计，不得承诺机场级页面。

### NO-GO

- 需要实际运行结果才能构造所谓拥挤度；
- 大量机场计划密度几乎不变；
- 样本集中度、窗口敏感性或数值异常使特征不能稳定解释；
- 构建不可复现或需要修改冻结输入。

门槛不得在看到结果后放宽。失败也应如实交付审计报告。

## 6. 输出文件

允许新增：

- `src/airports_under_stress/congestion.py`
- `scripts/run_v3_p0_congestion_audit.py`
- `tests/test_v3_congestion.py`
- `data/processed/v3_p0_congestion_events.parquet`
- `data/processed/v3_p0_congestion_summary.json`
- `data/processed/v3_p0_manifest.json`
- `reports/V3_P0_CONGESTION_AUDIT.md`

允许修改：

- 本任务文件，仅追加完成记录。

## 7. 禁止修改

- `web/` 下任何文件；
- `HANDOFF.md`、`PROJECT_STATUS.md`、`POLISH_BACKLOG.md`；
- 任何现有 `p0_*`、`v1_*`、`v2_*` 输入或产物；
- V0/V1/V2 构建器、测试和报告；
- 全局配置、凭据、依赖、git 历史或 Sites 配置；
- 不得 commit、push、deploy、安装包或调用子代理。

## 8. 测试与复现

至少覆盖：

- 手工小型时刻表 fixture，精确核对半开窗口边界、到达/出发计数和自身扣除；
- 同时刻 ties 与经验百分位确定性；
- 三档窗口单调性：30 分钟计数 `<=` 60 分钟 `<=` 90 分钟；
- 特征函数输入列白名单或等价的无泄漏契约；
- 55 机场、全事件覆盖、非负有限值和 Gate 自动判定；
- 两次完整运行哈希一致。

执行：

```powershell
.\\.venv\\Scripts\\python.exe scripts\\run_v3_p0_congestion_audit.py
.\\.venv\\Scripts\\python.exe -m pytest -q tests\\test_v3_congestion.py -p no:cacheprovider
```

不得因本轮不改前端而运行或修改 npm；如脚本运行时间过长，应优化算法，不得抽样冒充全量。

## 9. 完成记录（执行者追加）

必须写明：

- 实际修改文件；
- 三档窗口全国与逐机场诊断；
- 高/低组样本、传播率和集中度；
- Gate 判定与理由；
- 两跑哈希和测试结果；
- 未解决问题；
- Claude Code session UUID。

## 10. 外部初稿记录（Codex 验收作废）

> 以下数值来自存在到达机场归属和相对百分位口径错误的外部初稿，仅保留为验收轨迹，不得作为项目结论。最终结果见第 11 节。

执行日期：2026-07-28

### 实际修改文件

新增：

- `src/airports_under_stress/congestion.py`
- `scripts/run_v3_p0_congestion_audit.py`
- `tests/test_v3_congestion.py`
- `data/processed/v3_p0_congestion_events.parquet`
- `data/processed/v3_p0_congestion_summary.json`
- `data/processed/v3_p0_manifest.json`
- `reports/V3_P0_CONGESTION_AUDIT.md`

本任务文件仅追加本完成记录。未修改 `web/`、`HANDOFF.md`、`PROJECT_STATUS.md`、冻结输入、既有 V0/V1/V2 构建器或配置；未安装依赖、未提交、未发布。

### 范围与三档全国诊断

冻结事件范围核对：55/55 个 `nExposed >= 500` Mechanism 机场，91,185 条 `UpstreamArrDelayed15 == True` 且 `Origin` 在该范围内的事件；事件机场为 `Origin`，事件时刻为 `ScheduledDepartureUTC`。计划底表使用 611,735 条 `p0_flights.parquet` 计划航班，未按取消/备降或任何实际运行结果筛选。

| 窗口 | 出发 min/median/IQR/P90/P99/max | 到达 min/median/IQR/P90/P99/max | 总架次 min/median/IQR/P90/P99/max |
|---|---|---|---|
| 30 分钟 | 1/13/14/34/58/88 | 0/17/23/52/83/108 | 1/30/33/86/123/154 |
| 60 分钟（主口径） | 1/23/23/61/89/109 | 0/35/44/107/149/174 | 1/58/61/166/221/264 |
| 90 分钟 | 1/33/30/87/114/132 | 0/55/64/162/211.16/253 | 1/86/90/246/314/366 |

三档各 91,185/91,185 事件得到有限值；`other_planned_departures` 全部非负。逐机场结果已完整写入 `v3_p0_congestion_summary.json`：55/55 机场主窗口 IQR > 0，逐机场样本量范围 501–5,937，distinct relative-congestion 值范围 10–108。

### 高低组与稳定性

按机场内 60 分钟计划总架次的经验百分位（reference population：该机场全部计划出发事件；并列值采用 `(below + 0.5 * ties) / N`）构造相对拥挤度，再以全国 P25/P75 分组：

- 高组：22,821 条，描述性传播率 0.543754；
- 低组：22,810 条，描述性传播率 0.560763；
- 中间 50%：45,554 条，描述性传播率 0.589849。

窗口敏感性：30 vs 主窗口 Spearman `0.002016`，四分位一致率 `0.166025`；90 vs 主窗口 Spearman `-0.010234`，四分位一致率 `0.157713`。因此窗口切换时相对排序几乎不稳定，未满足“方向不因窗口轻微变化而完全翻转”的可解释性要求。

集中度：高组最大机场占比 `22.6064%`（超过 `<15%` 门槛），最大单日占比 `5.3065%`（满足 `<10%`）。逐机场高/低组最小样本数为 3（低于每组至少 100 条门槛）。

### Gate 判定

**CONDITIONAL GO**，不是 GO。

满足：55/55 机场与冻结事件三档有限非负覆盖；自身扣除后无负数；计划字段白名单实现；主窗口 55/55 机场 IQR > 0；全国高/低组各超过 15,000 条；两次完整构建输出哈希一致。

不满足：逐机场高/低比较的最小组样本仅 3；高组最大机场占比 22.6064% >= 15%；30/60/90 相对排序 Spearman 近 0 且四分位一致率约 16%，窗口敏感性不足。后续最多支持全国/分组审计，不得承诺机场级页面或机场级稳定拥挤层。

### 两跑哈希与测试

连续两次执行：

```powershell
.\\.venv\\Scripts\\python.exe scripts\\run_v3_p0_congestion_audit.py
.\\.venv\\Scripts\\python.exe scripts\\run_v3_p0_congestion_audit.py
.\\.venv\\Scripts\\python.exe -m pytest -q tests\\test_v3_congestion.py -p no:cacheprovider
```

测试结果：`3 passed`。

两跑科学产物 SHA-256（两次完全相同）：

- `v3_p0_congestion_events.parquet`: `8dab8674a0c90b7abb0ea9731d04388fb0ea0f9c66ee77bf02efdd7cf54a3a2d`
- `v3_p0_congestion_summary.json`: `c0c4dd8231e78d44ea7af10cf7bb619f1810e8b8d579e123abdd7ca0899bb0f0`

`v3_p0_manifest.json` 已记录 `scientificOutputsMatchPreviousRun: true`。

### 未解决问题

机场级样本门槛、机场集中度和窗口敏感性均未达到 GO；不能据此进入机场级 V3-A 页面实现，也不能把高低组差异写成拥挤造成传播的因果结论。计划密度特征本身不依赖实际运行字段，但当前相对百分位在该事件样本上的窗口间稳定性不足。

Claude Code session UUID：`ddce983d-7af6-4bf6-bb1c-b80f675440b6`。外部初稿将其误写为 N/A，Codex 验收时已纠正。

## 11. Codex 最终验收记录

最终判定：**CONDITIONAL GO**。

Codex 拒绝外部初稿并修复了四个关键问题：计划到达只归属 `Dest`，不再把同一航班的到达时刻计入 `Origin`；参考分布和事件值统一使用同一窗口的计划总架次；30/60/90 分钟分别生成机场内经验百分位并做同口径敏感性比较；事件自身必须在计划底表中精确存在，不再用 `max(departures - 1, 0)` 掩盖缺失。

最终覆盖 55 个机场、91,185 条事件，三档特征全部有限非负，55/55 机场主窗口 IQR 大于 0。60 分钟主口径：低拥挤组 26,502 条、传播率 42.27%；高拥挤组 20,768 条、传播率 66.15%。30/90 分钟相对排序与 60 分钟 Spearman 为 0.717 / 0.842，四分位一致率为 0.510 / 0.602，三档高减低传播率方向一致。高组最大机场占比 6.37%，最大单日占比 5.98%，均通过集中度门槛。

唯一未通过项是 55 个机场中最小高拥挤组只有 82 条，低于冻结的每组 100 条门槛；最小低组为 112 条。因此后续可做全国层面的 V3-A，机场比较必须先执行样本门槛，不得承诺 55 机场全量页面。

验证结果：V3 专项 `5/5`，Python 全量 `88/88`。连续构建三个科学产物 SHA-256 一致：

- `v3_p0_congestion_events.parquet`: `0fec6e8f052599adf8d968e90cb867060650714fa13bd2b4f5cfa5c441543b0e`
- `v3_p0_congestion_summary.json`: `6102c8326d57c99f491e834d201e4db181e6a5b639d7c67a9b66483e4ea2c08b`
- `V3_P0_CONGESTION_AUDIT.md`: `c04b424d15f32539dd02628e5da72bcddcfbe58fe41326ce1f27759f951d0daa`

未修改前端，未提交、未发布。
