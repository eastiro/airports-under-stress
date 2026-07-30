# V2-B 调整后天气关联审计

日期：2026-07-28

## Gate 0

复现 V2-A backward weather join，范围固定为 55 个 Mechanism 机场，PBI 保持 unavailable。90 分钟匹配 91,055 条（恶劣 12,743、非恶劣 78,312；传播率 58.2908% / 56.8866%）；60 分钟匹配 90,964 条（恶劣 12,716、非恶劣 78,248；传播率 58.2730% / 56.8820%）。最大天气年龄分别为 90/60 分钟，未发现未来天气。两档协变量完整，分析保留率均 100%。

## 模型

每档均拟合基础调整（机场、UTC 计划小时、星期）和运营条件调整（再加报告航司、计划周转分箱、上一航段到达延误分箱）。模型以 IRLS 实现，分类变量采用 reference dummy，输出标准化概率百分点差；区间使用按 FlightDate 的 31 日聚类 sandwich covariance，并采用 `G/(G-1) × (N-1)/(N-P)` 的 CR1 有限样本校正。未进入设计矩阵的泄漏字段包括 DepDelay、ArrDelay、ActualDepartureUTC、ActualTurnMinutes、LateAircraftDelay、OfficialLateAircraft、PropagationSignal、RecoverySignal。

|天气范围|规格|分析行|标准化差异|聚类稳健 95% 区间|预测范围|
|---|---|---:|---:|---:|---:|
|60 分钟|基础调整|90,964|4.9466 个百分点|2.8123–7.0809|0.0187–0.9485|
|60 分钟|运营条件调整|90,964|3.1912 个百分点|2.0954–4.2870|0.0010–0.9998|
|90 分钟|基础调整|91,055|4.9245 个百分点|2.7930–7.0560|0.0187–0.9484|
|90 分钟|运营条件调整|91,055|3.1678 个百分点|2.0684–4.2671|0.0010–0.9998|

结果表示在同一批分析行上替换天气分组后的模型平均预测差异，不是个体反事实，也不是因果效应或预测器。两档天气范围和两种规格方向一致，差异大小略有变化。

## Gate 1

**GO（数据产物与模型结果允许进入现有天气区域）**：Gate 0 一致；四个模型均收敛；保留率 100%；预测概率处于 (0,1)；设计矩阵无重复/空列；日期聚类区间通过独立测试复核。

## 复现

- `./.venv/Scripts/python.exe scripts/build_v2b_model.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/test_v2b_model.py tests/test_v2a_data.py tests/test_v2_weather.py -p no:cacheprovider`：15 passed，其中 V2-B 6 条测试覆盖 Gate、模型方向、reference coding、泄漏、前端快照和聚类协方差独立矩阵复核。
- `npm.cmd run lint`、`npm.cmd run build`、`npm.cmd run test:ssr`：通过，SSR 7/7。
- 连续两次构建字节一致：科学结果 SHA-256 `5dc1f8ecfaee052ce29c6a87a4d6483f1c44f892793d836819f5e19c972836b0`；前端快照 `3a170f47946526e82671e456be40a3754167995b57a21da247dddee5a5bdee29`。
- 未安装依赖，未修改冻结输入，未 commit/push/publish。

## 实际修改

- `scripts/build_v2b_model.py`
- `tests/test_v2b_model.py`
- `data/processed/v2_b_model_results.json`
- `web/app/v2-b-data.json`
- `web/app/MechanismSection.tsx`
- `web/app/dashboard.tsx`
- `web/app/globals.css`
- `web/tests/rendered-html.test.mjs`
- `reports/V2_B_ADJUSTED_WEATHER_ASSOCIATION.md`
