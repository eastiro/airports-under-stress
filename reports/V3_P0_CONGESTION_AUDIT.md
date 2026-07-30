# V3-P0 计划拥挤度可行性审计

审计范围：55 个 Mechanism 机场、91,185 条冻结事件。Gate：**CONDITIONAL GO**。

拥挤度完全来自计划时刻表：在事件计划起飞时刻周围，统计同机场计划出发与计划到达。相对拥挤度是在同一机场、同一窗口内，相对于该机场所有计划出发事件的计划总架次经验百分位；并列值取平均秩。

## 三档窗口

| 窗口 | 计划出发中位数 | 计划到达中位数 | 计划总架次 P90 |
|---|---:|---:|---:|
| 30 分钟 | 13.0 | 8.0 | 61.0 |
| 60 分钟 | 23.0 | 17.0 | 115.0 |
| 90 分钟 | 33.0 | 27.0 | 168.0 |

## 高低拥挤组（描述性）

| 窗口 | 低组样本 | 低组传播率 | 高组样本 | 高组传播率 | 高减低 |
|---|---:|---:|---:|---:|---:|
| 30 分钟 | 25,966 | 0.4657 | 21,635 | 0.6167 | +0.1510 |
| 60 分钟 | 26,502 | 0.4227 | 20,768 | 0.6615 | +0.2388 |
| 90 分钟 | 26,906 | 0.3909 | 21,314 | 0.6980 | +0.3071 |

## Gate

- **通过** `coverage`：55 airports and 91,185 frozen events；实际值 `{'airports': 55, 'events': 91185}`。
- **通过** `finite_nonnegative`：all three windows finite/nonnegative and focal flight present；实际值 `{'all_finite': True, 'all_nonnegative': True, 'focal_departure_covered': True, 'other_departures_nonnegative': True}`。
- **通过** `schedule_only_contract`：exact five-column schedule whitelist；实际值 `['Origin', 'Dest', 'ScheduledDepartureUTC', 'ScheduledArrivalUTC', 'SourceRow']`。
- **通过** `dynamic_airports`：at least 50 of 55 airports have 60m relative-congestion IQR > 0；实际值 `55`。
- **通过** `national_group_samples`：national high and low groups each contain at least 15,000 events；实际值 `{'high_n': 20768, 'low_n': 26502}`。
- **未通过** `airport_group_samples`：each of the 55 airports has at least 100 events in both groups；实际值 `{'min_high_n': 82, 'min_low_n': 112}`。
- **通过** `concentration`：largest airport <15% and largest day <10% of high group；实际值 `{'max_high_airport_share': 0.06365562403697997, 'max_high_day_share': 0.05975539291217257}`。
- **通过** `window_sensitivity`：30/90 vs 60m Spearman and quartile agreement >=0.50, contrast direction unchanged；实际值 `{'same_contrast_direction': True, '30': {'spearman_vs_60m': 0.7173530510902346, 'quartile_agreement_vs_60m': 0.5099413280693097, 'high_minus_low_propagation_rate': 0.1509615167412129}, '90': {'spearman_vs_60m': 0.8422553443623491, 'quartile_agreement_vs_60m': 0.6015024400943138, 'high_minus_low_propagation_rate': 0.307075405991385}}`。

30/90 分钟与 60 分钟的详细 Spearman、四分位一致率及传播率方向见 summary。连续构建的字节一致性由 manifest 单独记录。

高低组传播率只描述同时出现的现象，不代表计划拥挤造成延误传播。
