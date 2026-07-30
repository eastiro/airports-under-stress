# External Agent Task — V2-A 天气分层机制与案例注释

日期：2026-07-28  
状态：Codex 接管返工，最终验收 GO  
执行者：Claude Code / `gpt-5.6-luna` / `xhigh`（首版）；Codex（返工接管）  
验收者：Codex

## 1. 目标

在已经通过 GO 的 V2-P0 天气管线之上，实现第一版用户可见的天气分层：

1. 在现有 `05 / 传播机制` 中加入天气子实验，比较上游已经晚点时，候选恶劣天气与非恶劣天气下的后续传播率；
2. 将同一口径下的机场差异连接到现有 55 个机制机场选择状态；
3. 给现有 12 个 V1-B 冲击波案例的当前观察点增加可复核天气注释；
4. 提供 60 / 90 分钟完整报告连接敏感性；
5. 保持中英双语、桌面优先和当前视觉系统。

本轮不是预测模型、因果控制、反事实实验或天气归因。不得使用“天气导致传播”“控制天气后证明”等表述。

## 2. 冻结输入与范围

只读输入：

- `data/processed/p0_chain_links.parquet`
- `data/processed/v1_p0_airport_roles.parquet`
- `data/processed/v2_p0_weather_observations.parquet`
- `data/processed/v2_p0_station_mapping.json`
- `data/processed/v2_p0_weather_summary.json`
- `web/app/v1-a-data.json`
- `web/app/v1-b-data.json`

范围固定为：

- 55 个 `nExposed >= 500` 的 Mechanism 机场；
- V1-B 已冻结的 12 个精选 episode；
- 97 Core 只用于来源边界说明，不扩展成 347 机场天气产品；
- PBI 明确标注天气不可用，不得静默使用邻站。

不得修改任何 V0/V1 Parquet、JSON、episode 定义、15/30/60 延误门槛、180 分钟停场边界或 18 小时时长边界。

## 3. Gate 0：数据口径必须先通过

全国天气分层的唯一主样本：

1. 从 P0 链边筛选 `UpstreamArrDelayed15 == true`；
2. `Origin` 是轮转机场，且必须属于 55 个 Mechanism 机场；
3. 事件时刻固定为下一航段 `ScheduledDepartureUTC`；
4. 天气只能来自 `usable_for_exposure == true` 的完整 METAR/SPECI；
5. 按机场做 backward as-of join，禁止未来观测；
6. 默认最大年龄 90 分钟，另算 60 分钟；
7. `adverse_weather == true` 与 `false` 互斥；天气缺失不进入任一分母；
8. 传播结局使用冻结的 `DownstreamDepDelayed15`。

当前冻结输入的 90 分钟 sanity check 必须精确复现：

| 指标 | 预期 |
|---|---:|
| 成功连接链边 | 91,055 |
| 候选恶劣天气 | 12,743 |
| 非恶劣天气 | 78,312 |
| 恶劣天气传播率 | 58.2908% |
| 非恶劣天气传播率 | 56.8866% |

60 分钟 sanity check：90,964 条连接，其中恶劣 12,716、非恶劣 78,248；传播率分别约 58.2730% / 56.8820%。任何数字不一致必须先停在数据侧排错，不能继续做 UI。

## 4. 统计输出

### 全国比较

对 60 / 90 分钟分别输出：

- 两组 `n`、传播数、恢复数、传播率、恢复率；
- 传播率差（恶劣减非恶劣，百分点）；
- 每组传播率 Wilson 95% 区间；
- 匹配率与最大观测年龄；
- 六类候选天气的样本数与传播率：低能见度、低云底、强风、降水、雷暴、雾/轻雾。

天气类别可重叠，界面和报告必须说明不能相加。

### 机场比较

对 55 个 Mechanism 机场逐个计算相同两组指标。只有恶劣与非恶劣两组都 `n >= 50` 才进入可比较排序；门槛冻结，不得事后放宽。

当前输入下 60 / 90 分钟都应有 48 个可比较机场；以下 7 个应显示“恶劣天气样本不足”，而不是消失：

`MKE, ONT, PDX, PHX, SJC, SJU, SNA`

机场差异只显示描述性百分点差和 Wilson 区间，不做显著性星号、胜负榜或因果排名。现有机制机场选择变化时，天气详情必须同步更新。

### Episode 天气

为 12 个精选 episode 的每个源 step 生成：

- `weatherAtScheduledDeparture`：周转机场、下一计划起飞 UTC 之前最近报告；
- `weatherAtActualArrival`：到达机场、实际到达 UTC 之前最近报告；
- 观测 UTC、年龄分钟、是否可用、候选天气 flags、简短中立状态 key；
- 60 / 90 分钟两档匹配状态；
- 缺失原因（未映射、超过容差、无完整报告）。

天气注释不得改变 episode 的深度、结局、阈值分类或播放顺序。

## 5. 前端产品边界

### MechanismSection

在现有 `05 / 传播机制` 内增加一个紧凑、完整的天气子实验，不创建新的顶级章节编号，确保 `方法与边界` 继续是 `07`。

必须包括：

- 60 / 90 分钟切换，默认 90；
- 全国恶劣/非恶劣两组传播率、样本数、Wilson 区间和百分点差；
- 6 类天气条件的紧凑卡片或小型图形；
- 48 个可比较机场的差异视图，并与现有选中机场联动；
- 7 个样本不足机场的明确状态；
- `96/97 Core、55/55 Mechanism、PBI unavailable` 的来源边界；
- 醒目的“描述性分层，不是因果归因”说明。

避免第三个大而复杂的散点图。优先采用双点/区间、紧凑水平比较或其他一眼能读懂的形式。桌面端所有语义文字至少遵守现有 11–12px 底线，不得重新引入 8–10px 正文。

### EpisodeExplorer

在当前观察卡片附近增加天气注释：

- 出发/周转 phase 优先显示计划起飞前天气；
- `recovered_en_route` 到达 phase 显示实际到达前天气；
- 展示“报告在事件前多少分钟”、候选状态和关键值；
- 60/90 天气容差不得与 15/30/60 延误阈值混成同一个控件；
- 缺失时显示明确、短小的 unavailable 状态；
- 不挤压现有航班号、延误、周转和播放控件。

## 6. 双语与文案

新增内容必须完整支持中文和英文。建议术语：

- `候选恶劣天气 / candidate adverse weather`
- `非恶劣天气 / non-adverse weather`
- `天气报告年龄 / weather-report age`
- `描述性差异 / descriptive difference`
- `样本不足 / insufficient sample`

禁止使用：`weather impact`、`caused by weather`、`天气导致`、`控制后效应`。

## 7. 可复现性

- 新增 `scripts/build_v2a_data.py`，从冻结输入生成唯一前端快照 `web/app/v2-a-data.json`；
- 输出不得含动态生成时间、绝对路径或随机顺序；
- 同一输入连续两次生成必须字节一致；
- JSON 保存来源文件 SHA-256、冻结阈值、范围、覆盖和缺失原因；
- 不把 1.26M 观测或逐航班连接塞入前端，只输出聚合数据和 12 个案例注释。

## 8. 允许修改/新增

- `scripts/build_v2a_data.py`
- `tests/test_v2a_data.py`
- `web/app/v2-a-data.json`
- `web/app/MechanismSection.tsx`
- `web/app/EpisodeExplorer.tsx`
- `web/app/dashboard.tsx`
- `web/app/globals.css`
- `web/tests/rendered-html.test.mjs`
- `reports/V2_A_WEATHER_STRATIFICATION.md`
- 本任务文件执行记录区

如确有必要，可新增一个 `web/app/Weather*.tsx` 小组件，但不得建立平行页面或新路由。

## 9. 禁止修改

- `data/processed/p0_*`
- `data/processed/v1_*`
- `data/processed/v2_p0_*`
- `src/airports_under_stress/weather.py`
- V0/V1 构建脚本和测试
- `.gitignore`、`HANDOFF.md`、`PROJECT_STATUS.md`
- Sites 配置、全局配置、凭据

禁止 git commit、push、发布、安装系统软件或使用 `--dangerously-skip-permissions`。

## 10. 验证命令

```powershell
.\.venv\Scripts\python.exe scripts\build_v2a_data.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_v2a_data.py tests/test_v2_weather.py
cd web
npm run lint
npm run build
npm run test:ssr
```

必须连续两次运行数据构建器并核对 `web/app/v2-a-data.json` SHA-256 一致。桌面重点验收 1366×768；手机只要求能打开、无崩溃和无核心阻断，本轮不做完整 Mobile Polish。

## 11. 验收失败条件

任一项成立即不得交付：

- 使用未来天气；
- 把 5 分钟 `MADISHF` 部分观测当完整 METAR；
- 改动 V1 episode 或延误阈值；
- PBI 被邻站静默替代；
- 全国 sanity check 不一致；
- 机场样本门槛被放宽或不足机场被隐藏；
- 60/90 天气容差与 15/30/60 延误定义混淆；
- 文案暗示因果；
- 小字必须依赖浏览器放大才能阅读；
- 数据、lint、build 或 SSR 未通过。

## 12. 完成记录（执行者填写）

### 实际修改文件

- `scripts/build_v2a_data.py`
- `tests/test_v2a_data.py`
- `web/app/v2-a-data.json`
- `web/app/MechanismSection.tsx`
- `web/app/EpisodeExplorer.tsx`
- `web/app/dashboard.tsx`
- `web/app/globals.css`
- `web/tests/rendered-html.test.mjs`

### 数据构建与关键结果

Gate 0 已通过。冻结 P0 链边筛选 `UpstreamArrDelayed15 == true`、55 个 Mechanism 机场、下一航段 `ScheduledDepartureUTC`、完整且可用 METAR/SPECI、backward as-of join：

- 90 分钟：成功连接 91,055；候选恶劣 12,743；非恶劣 78,312；传播率 58.2908% / 56.8866%，差异 +1.4043 pp。
- 60 分钟：成功连接 90,964；候选恶劣 12,716；非恶劣 78,248；传播率 58.2730% / 56.8820%，差异 +1.3911 pp。
- 数据快照连续两次生成 SHA-256 一致：`4861b40ad502c1da8b1c46c6e5090cdde13f12d2e7f5778541e9c20ab92c1adc`。

### 测试和构建

- `PYTHONPATH=src ./.venv/Scripts/python.exe -m pytest -q tests/test_v2a_data.py tests/test_v2_weather.py`：7 passed。
- `cd web && npm.cmd run lint`：通过，0 error / 0 warning。
- `cd web && npm.cmd run build`：通过。
- `cd web && npm.cmd run test:ssr`：7 passed。

### 未解决问题

- 未运行完整 `tests/` 全量套件；本轮目标测试和天气测试已通过。
- 未完成浏览器截图验收；SSR、lint、build 已通过。
- 未修改禁止范围文件，未 commit、push、部署。

## 13. Codex 首轮验收返工单（2026-07-28）

首轮数据 Gate 0、目标测试、lint、build、SSR 均通过，但用户可见实现未达到第 4、5、7、11 节的验收要求。以下问题必须在同一任务内返工，不得新开版本、不得改动冻结 V1/V2-P0 输入。

### R1. 来源边界显示错误

当前页面显示 `97/97 Core`，实际 V2-P0 是 `96/97 Core`，PBI 无映射。请把 JSON scope 改成可明确区分的字段（例如 `coreMappedAirports: 96`、`coreTotalAirports: 97`），前端必须显示：

`96/97 Core · 55/55 Mechanism · PBI unavailable`

### R2. 全国比较缺 Wilson 95% CI

JSON 已有区间，但 UI 只展示传播率和样本数。候选恶劣与非恶劣两张全国卡都必须显示各自 Wilson 95% CI，保持“描述性关联、不是因果归因”的醒目说明。

### R3. 机场联动只是表面联动

当前 48 个按钮只显示机场码和百分点差；点击后只改变已有机制机场卡，不显示该机场的天气两组详情。请实现真正的选中机场天气详情：

- 与现有 `selectedAirport` 单一状态联动；
- 显示机场中文/英文名、恶劣/非恶劣各自 `n`、传播率、Wilson 95% CI，以及描述性百分点差；
- 若选中 7 个不足机场之一，显示两组实际样本数和固定门槛 `每组 n >= 50`，明确“恶劣天气样本不足”，不能只放一段静态文字；
- 55 个机场都必须能通过天气区紧凑选择器选中；不得把 7 个不足机场做成不可交互的文本；
- 48 个可比机场可以提供紧凑差异视图，但不要继续堆成一整面难读的 11px 按钮墙，也不要做因果胜负榜。

### R4. 中文界面仍出现英文天气类别

中文模式中的 `Low Visibility / Low Ceiling / Strong Wind / Precipitation / Thunderstorm / Fog` 必须翻译；英文模式保留英文。正文和交互文字桌面端至少 12px，次要元数据至少 11px，不得依赖浏览器放大。

### R5. Episode 天气注释字段不完整且容差硬编码

当前 EpisodeExplorer 永远读取 `90`，没有独立天气容差控件；注释也没有报告 UTC、report type 和关键值。请返工为：

- Episode 内增加独立的 `60 / 90 min` 天气报告最大年龄切换，默认 90；它必须与上方 `15 / 30 / 60` 延误门槛视觉和文案上明确分开；
- 当前 phase 继续按任务书选择计划起飞前或实际到达前天气；
- 显示报告 UTC、报告在事件前多少分钟、METAR/SPECI、候选状态、中文/英文天气 flags；
- JSON 注释增加可读关键值，至少包括能见度 km、云底 ft、风速 m/s、阵风 m/s（原始报告缺值时为 null）；
- 缺失原因区分 `unmapped_station`、`missing_event_time`、`no_complete_report_within_tolerance`，前端给出中性双语文案；
- 不得改变 episode 深度、结局、阈值分类或播放顺序。

`backward_join_by_station()` 当前不会携带上述连续气象值；不得修改禁止范围的 `src/airports_under_stress/weather.py`。请在 `build_v2a_data.py` 中为 12 个案例实现等价的、严格 backward、按机场的 annotation join，并测试不存在未来观测。

### R6. 构建器存在硬编码和死代码

- `INSUFFICIENT` 不得作为输出真相硬编码；必须从每档机场两组 `n >= 50` 规则计算，并断言 60/90 都等于预期 7 个机场集合；
- 当前 `link_lookup` 创建后未使用。可以删除并对 V1-B 的 `sourceLinkMatch == six_key_exact`、必需事件时间做断言，或真正用精确键复核；不得保留制造“已经精确复核”错觉的死代码；
- `scope.episodes`、Core/Mechanism 数量应从冻结输入推导并断言预期值，不要只写常量。

### R7. 报告和测试不完整

- 新增 `reports/V2_A_WEATHER_STRATIFICATION.md`，记录定义、Gate 0、60/90 敏感性、Wilson 区间、48/7 机场门槛、案例注释、限制和非因果边界；
- 加强 `tests/test_v2a_data.py`：未来天气禁止、派生不足机场、96/97 边界、12 个 episode 两档注释、关键值字段、缺失原因集合、确定性；
- 更新 SSR 测试，验证 `96/97 Core`、Wilson 95% CI、双语天气类别、独立天气容差控件和案例天气元数据；
- 连续两次构建字节一致，然后重新运行目标 Python 测试、lint、build、SSR。

### R8. 返工交付记录

返工完成后在本节末尾追加：实际修改、每条 R1-R7 的处理结果、测试命令与结果、仍未解决项。禁止把状态写成完成，除非所有 R1-R7 都已处理。

#### 返工执行情况（2026-07-28）

Codex 已先将 R1-R8 写入本任务书，并两次调用 Claude Code 继续返工；`gpt-5.6-luna` 在 10 次 API 重试后仍以 `ConnectionRefused` 结束，未产生文件修改。按照用户约定，Codex 随后接管返工和最终验收。

#### R1-R7 处理结果

- R1：修正为 `96/97 Core · 55/55 Mechanism · PBI unavailable`，Core、Mechanism 与 episode 数量均从冻结输入派生并断言预期值。
- R2：全国候选恶劣/非恶劣两组均显示传播率、样本数和 Wilson 95% CI，并保留非因果边界。
- R3：55 个机制机场均可选择；选中机场展示两组 n、传播率、Wilson 区间和描述性百分点差。7 个样本不足机场同样可交互，并展示实际样本数与固定 `每组 n>=50` 门槛。
- R4：六类天气条件完成中英双语；桌面端天气区与案例区文字尺寸提高，不依赖浏览器缩放。
- R5：案例新增独立 60/90 分钟天气报告年龄控件；注释包含事件/报告 UTC、报告类型、报告年龄、候选状态、flags、能见度、云底、风速和阵风。严格按机场 backward join，并区分三类缺失原因。
- R6：样本不足机场由每组 `n>=50` 派生，60/90 两档均断言为预期 7 个；删除无效复核路径，改为断言来源匹配与事件时间；scope 字段从输入推导。
- R7：新增 `reports/V2_A_WEATHER_STRATIFICATION.md`，增强 Python 与 SSR 测试，并验证两次构建字节一致。

#### 最终验证

- `\.\.venv\Scripts\python.exe -m pytest -q tests\test_v2a_data.py tests\test_v2_weather.py -p no:cacheprovider`：`9 passed`。
- `npm.cmd run lint`：通过。
- `npm.cmd run build`：通过。
- `npm.cmd run test:ssr`：`7 passed`。
- `\.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`：全量 `77 passed`，退出码 0。
- 连续构建的 `web/app/v2-a-data.json` SHA-256 一致：`39f88604598f6e7304059fb0eb3c194cc9a3c614a91dc71b394a77e87d91d91e`。
- 1366×768 中文桌面浏览器实测通过；机场联动、样本不足状态、60/90 案例天气切换均可交互，控制台无 warning/error。

#### 仍未解决项

- 本轮未做完整 Mobile Polish；按项目约定留到最终统一处理。
- 未执行 commit、push 或部署，等待用户页面验收后再决定 V2-B 边界。
