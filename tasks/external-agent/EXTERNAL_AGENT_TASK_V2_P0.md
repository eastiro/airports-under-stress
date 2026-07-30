# External Agent Task — V2-P0 天气数据可行性审计

日期：2026-07-28
状态：Codex 最终验收 GO（97 Core / 55 Mechanism 限定范围）
执行者：Claude Code / `gpt-5.6-luna` / `xhigh`
验收者：Codex

## 1. 任务目标

只判断 2026 年 5 月机场小时级天气能否可靠接入 Airports Under Stress，并建立可复现的天气下载、标准化和覆盖率审计管线。

本阶段不做前端、不修改 V0/V1 科学产物、不做天气控制模型、不训练预测模型，也不声称因果关系。V2-P0 的最终输出只能是 `GO`、`CONDITIONAL GO` 或 `NO-GO`。

## 2. 已知现场事实（必须复核，不得改写）

1. BTS 航班范围为 2026-05-01 至 2026-05-31，共 611,735 条记录、347 个机场。
2. V0 机场榜有 97 个合格机场；V1 机制图有 55 个上游暴露数不少于 500 的机场。
3. BTS `WeatherDelay` 仅在延误原因记录中非空：当前 611,735 条中 129,511 条非空，7,010 条大于 0。它不能作为所有航班的外部天气暴露来源，只能用于弱一致性检查。
4. 2026-07-28 现场查询时：
   - NOAA NCEI ISD 产品页与 `isd-history.csv` 可访问；
   - `global-hourly/access/2026/` 返回 404；
   - NCEI `global-hourly` 与 `local-climatological-data` 对 LGA/JFK 的 2026-05-01 查询均为空；
   - 同一 LGA 站点的 2024-05-01 Global Hourly 查询能返回记录；
   - Iowa Environmental Mesonet ASOS/METAR 档案能返回 LGA 2026-05-01 的观测。
5. 因此候选执行源为 Iowa State IEM ASOS/METAR 档案；报告必须明确它是大学维护的航空气象档案，而不是把它写成 NOAA NCEI 已归档数据。

## 3. 数据源与来源边界

候选入口：

```text
https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py
```

必须保存：

- 请求参数和数据字典/来源说明链接；
- 下载时间、HTTP 状态、响应字节数与 SHA-256；
- 站点、日期和字段清单；
- 原始响应写入 `data/raw/weather/`（该目录继续由 Git 忽略）；
- 标准化产物写入 `data/processed/v2_p0_*`（继续由 Git 忽略）；
- 不把动态下载时间写入科学产物哈希。

不得使用需要 API Key 的天气服务，不得把未知来源的商业聚合数据作为主源。

## 4. 目标机场与执行顺序

按三层审计，不能只挑容易成功的机场：

1. **Pilot**：至少 12 个机场，覆盖东北、东南、中西部、山地、西海岸、夏威夷、阿拉斯加及小型机场。
2. **Core**：V0 的全部 97 个合格机场，必须逐个报告覆盖率。
3. **Mechanism**：V1 的 55 个机制机场必须单独汇总，因为它们是 V2-A 的最低产品范围。

347 个 BTS 机场的全量覆盖作为扩展审计；不能为了追求 347/347 而阻塞 97/55 的核心判断。

机场到气象站的映射必须可复核：优先使用同机场 IATA/ICAO 的 ASOS/METAR 站；若使用邻近站，必须记录距离、理由和映射方式，不能静默替代。

## 5. 最小字段

至少请求并标准化：

- station / valid UTC / latitude / longitude / elevation；
- temperature / dew point / relative humidity；
- wind direction / sustained wind / gust；
- visibility；
- sky cover 与 cloud base（尽可能保留多层）；
- present weather codes；
- report type（METAR / SPECI 等）。

单位必须明确。原始华氏度、节、英里、英尺可以保留，但标准化层需同时提供摄氏度、米每秒、米/公里等明确单位字段；禁止只靠列名猜单位。

## 6. 时间与去重规则

- 所有标准化时间必须是 timezone-aware UTC。
- 不能按本地日期直接连接 BTS。
- 同一站点同一时刻若有重复报告，必须制定确定性去重规则并报告重复数。
- 5 分钟部分观测与整点/51 分钟完整 METAR 不得混为“完整小时天气”；分别审计字段覆盖。
- 评估至少三种 join tolerance：30 / 60 / 90 分钟。
- 为避免用结果发生后的信息解释结果，优先审计“计划起飞 UTC 之前最近一次有效观测”；可另报最近观测，但不能替代主口径。

## 7. 候选天气定义（P0 只审计，不最终冻结）

至少评估以下可计算性和样本规模：

- 低能见度：visibility < 3 statute miles；
- 低云底：ceiling < 1,000 ft；
- 强风：持续风 ≥20 kt 或阵风 ≥30 kt；
- 降水、雷暴、雾：来自 present weather code；
- `adverse_weather`：上述任一条件成立。

报告各条件的机场小时数、航班暴露数和缺失率。不得为了得到显著差异事后调整阈值。

## 8. 必做审计

1. 每机场观测数、完整 METAR 数、首末 UTC、重复数、最大时间缺口。
2. 每字段非空率，区分全部报告与完整 METAR。
3. 97 个核心机场、55 个机制机场的机场小时覆盖率。
4. BTS 航班按计划起飞 UTC 连接天气后的 30/60/90 分钟覆盖率。
5. V1 episode step 在上游到达、周转机场和下一计划起飞时刻的天气覆盖率。
6. 候选恶劣天气条件的样本量与机场集中度。
7. 与 BTS `WeatherDelay > 0` 做弱一致性检查：只报告描述性关联，不把一致或不一致当成天气真值。
8. 下载重跑的内容哈希与标准化产物确定性；同一原始文件重复构建必须一致。

## 9. GO / CONDITIONAL GO / NO-GO

### GO

- 55 个机制机场全部有可复核站点映射；
- 97 个核心机场至少 95 个有可用映射；
- 55 个机制机场中，至少 90% 的机场其小时覆盖率 ≥95%；
- 计划起飞前最近观测在 90 分钟内的航班覆盖率 ≥95%；
- visibility、wind、ceiling、weather code 足以构造候选天气标记，且无单一机场/单日支配全国恶劣天气样本；
- 原始下载有哈希，标准化重建确定性通过。

### CONDITIONAL GO

- 核心机制机场可用，但部分机场或字段不足；
- 必须明确将 V2-A 范围缩小到可审计机场/天气维度，并列出不能展示的内容。

### NO-GO

- 55 个机制机场无法形成稳定覆盖；
- 时间连接大量依赖未来观测或超过 90 分钟；
- 关键字段缺失使候选天气状态不可计算；
- 数据源无法稳定重跑或来源说明不足。

任何门槛不得在看到结果后擅自放宽。若认为门槛不合理，只能在报告中提出，不得直接修改任务书标准。

## 10. 允许修改/新增

- `scripts/download_weather_v2_p0.py`
- `scripts/run_v2_p0_weather_audit.py`
- `src/airports_under_stress/weather.py`
- `tests/test_v2_weather.py`
- `reports/V2_P0_WEATHER_AUDIT.md`
- `docs/WEATHER_DATA_DICTIONARY.md`
- `data/raw/weather/*` 与 `data/processed/v2_p0_*`（均保持 Git 忽略）
- 本任务文件的执行记录区

如确有必要，可小范围更新 `requirements.txt` / `pyproject.toml`，但优先使用现有依赖。

## 11. 禁止修改

- `web/` 下全部文件；
- V0/V1 脚本、测试、报告、JSON、Parquet 和已冻结定义；
- `.gitignore` 中现有数据忽略策略；
- `HANDOFF.md` 与 `PROJECT_STATUS.md`（由 Codex 验收后更新）；
- Git 提交、推送、发布、Sites 配置和可见性；
- 全局 Claude/Codex 配置及任何凭据。

## 12. 验证要求

至少运行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_v2_weather.py
```

若代码触及公共模块，还需运行相关既有测试。下载与审计命令必须写入报告和执行记录，不能只报告“成功”。

## 13. 完成记录与 Codex 最终验收

### 实际修改文件

- `scripts/download_weather_v2_p0.py`
- `scripts/run_v2_p0_weather_audit.py`
- `src/airports_under_stress/weather.py`
- `tests/test_v2_weather.py`
- `reports/V2_P0_WEATHER_AUDIT.md`
- `docs/WEATHER_DATA_DICTIONARY.md`
- `data/raw/weather/*`（下载原始响应及元数据）
- `data/processed/v2_p0_*`（标准化观测、机场审计和摘要）

### 下载与构建命令

```powershell
python scripts/download_weather_v2_p0.py --stations <core IATA list> --start 2026-05-01 --end 2026-06-01
python scripts/download_weather_v2_p0.py --stations <core IATA list> --start 2026-06-01 --end 2026-06-02
python scripts/download_weather_v2_p0.py --stations PANC,PHNL,PHKO,PHLI,PHOG,KPBI,TJSJ --start 2026-05-01 --end 2026-06-02
python scripts/run_v2_p0_weather_audit.py --raw <三份固定原始 CSV>
.\.venv\Scripts\python.exe -m pytest -q tests/test_v2_weather.py
.\.venv\Scripts\python.exe -m pytest -q
```

三份固定响应合计 1,264,389 行；HTTP 200、请求参数和 SHA-256 已保存在 `download_metadata.json` / 同名 `.metadata.json` 与最终 summary 中。

### 审计结果

- Codex 纠正执行器初版的 Core 定义：按 V0 冻结的 `flights >= 1,000` 且 `chainLinks >= 500`，Core 为 97，不是 133。
- 确定性去重后 1,260,300 条观测，其中 1,143,305 条 5 分钟部分观测、116,995 条完整 METAR/SPECI、116,715 条可用于主暴露连接。
- 映射 96/97 Core 与 55/55 Mechanism；PBI 保持明确缺失，未用邻站替代。最大同机场站点距离 3.48km。
- 完整报告口径的计划起飞前 90 分钟覆盖：Core 99.42%，Mechanism 99.91%；55/55 个 Mechanism 机场逐机场覆盖均 >=95%，最差 99.23%。
- 55/55 个 Mechanism 机场完整报告小时覆盖均 >=95%，最差 98.25%。
- 79,339 个真实周转 step 与冻结 P0 链边 100% 匹配；Mechanism 周转机场在到达/计划起飞/实际起飞时点的 90 分钟覆盖均约 99.8%。
- `WeatherDelay > 0` 航班的候选恶劣天气率为 43.85%，其余匹配航班为 11.39%；仅作弱一致性描述。
- 连续两次完整重建的 6 个科学产物 SHA-256 全部一致，manifest 为 `scientificOutputsMatchPreviousRun=true`。

### 测试结果

天气专项 **5/5**，全量 Python 回归 **73/73**。覆盖 UTC、单位、5 分钟/完整报告区分、正确 ceiling、确定性去重和 no-future backward join。

### 未解决问题与建议判定

External Agent 初版建议 `CONDITIONAL GO`，但其 Core 定义、报告类型、海拔单位、ceiling 和逐机场覆盖均有问题。Codex 接管修正、补齐数据与独立复验后，最终判定为 **GO**，仅适用于 97 Core / 55 Mechanism 范围。347 机场全量、预测、反事实和因果表述继续不在 V2-A 范围；PBI 必须明确显示天气不可用。
