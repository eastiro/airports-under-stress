# V1-P0 传播机制与 Shockwave 数据可行性审计

**判定：GO**

## 1. 执行摘要

在冻结的 549,388 条 P0 轮转链边上，发布 50,526 个通过完整性门槛的 episode 和 89,595 个 step。另有 2 个候选因同机尾号时间线冲突被排除并单独审计，不进入统计样本。

## 2. 数据边界

数据覆盖 2026 年 5 月 BTS 美国国内定期、不经停客运航班。所有结果均为观察性描述，不代表因果关系，也不代表全球航空网络。

## 3. Episode 定义

当上一航段到达延误达到 15 分钟时开始观察；后续起飞延误仍达到阈值则传播，起飞或到达恢复至阈值以下则恢复。正式 episode 只允许计划停场不超过 180 分钟，且总观察时长不超过 18 小时；长停场、时长到限、机场链断裂和序列末端均属于删失，不伪装成恢复。无法形成单一物理时间线的候选不发布为 episode。物理轮转链仍保留 P0 的 720 分钟上限，不与传播 episode 边界混用。

## 4. 完整性审计

| 硬门槛 | 结果 |
|---|---:|
| `chain_links_549388` | 通过 |
| `no_negative_turns` | 通过 |
| `no_utc_reversal` | 通过 |
| `no_invalid_episode_times` | 通过 |
| `no_overlapping_episodes_same_tail` | 通过 |
| `airport_path_continuity` | 通过 |
| `no_gaps_as_recovered` | 通过 |
| `recovery_not_continuing_old_episodes` | 通过 |
| `continuity_boundaries_not_recovered` | 通过 |
| `episode_duration_within_limit` | 通过 |
| `step_turn_within_limit` | 通过 |

发布产物中的同机尾号 episode 重叠数为 0；UTC 倒序 0；路径断裂 0；恢复后继续计数 0；超过 18 小时 0；步骤计划停场超过 180 分钟 0；连续性边界误记恢复 0。

## 5. Episode 规模与结局

- Episodes：50,526
- Recovered：28,983
- Censored：21,543
- 深度 ≥2：14,811
- 深度 ≥3：5,833
- 最大深度：9
- 时间线冲突排除：2
- 计划长停场截断：15,876
- 18 小时时长截断：292

## 6. 有向传播链路

L1 `turnAirport -> nextDestination` 共 5,999 条；其中上游晚到暴露 ≥100 的链路 117 条。推荐正式展示使用 `nUpstreamLate >= 100` 并同时显示 Wilson 95% 区间。

## 7. 样本门槛与区间

CI 门槛同时要求 `nUpstreamLate >= 100` 且区间宽度 ≤0.20；符合条件的链路为 117 条。小于 5 个样本的区间保留为空，不作为合格项。

## 8. 条件传播差异

仅纳入同时存在 upstream-late 与 upstream-not-late 的可比 `(turnAirport, 2-hour bin)` strata。可比 strata 2,076，排除 132，覆盖率 99.81%，加权观察性差异 0.4666。

## 9. 机场机制维度

共计算 346 个机场，其中 55 个满足 `nExposed >= 500`。只有这些机场获得描述性 role label；其余标记为 `insufficient_sample`。V1 应优先展示连续维度，而不是把角色标签写成因果结论。

## 10. 阈值敏感性

| 阈值（分钟） | Episodes | 深度≥2 | 深度≥3 | 最大深度 | 暴露≥500机场 |
|---:|---:|---:|---:|---:|---:|
| 15 | 50526 | 14811 | 5833 | 9 | 55 |
| 30 | 31162 | 8309 | 2991 | 8 | 39 |
| 60 | 14777 | 3335 | 1099 | 7 | 19 |

15↔30 的传播率 Spearman 为 0.8962，Top 20 链路交集 20/20；15↔60 的 Spearman 为 None，Top 20 交集 3/20。

独立 P0.1 连续性网格比较了计划停场 120/180/240 分钟与总时长 12/18/24 小时。18 与 24 小时在 180 分钟停场定义下的深度≥3数量仅相差约 0.1%；正式选择中心规格 180 分钟 + 18 小时，详见 `reports/V1_P01_CONTINUITY_AUDIT.md`。

## 11. 集中度

集中度严格按精确 `(turnAirport, nextDestination)` Top 20 链路计算，而不是扩展为这些机场的全部航班。完整机器可读结果由运行日志及派生表保留。

## 12. 案例候选

案例候选包含最深传播、高延误后恢复、跨 UTC 午夜、高压日、普通日和删失案例；每类数量为：deepest=5, high_delay_but_recovered=5, cross_midnight=5, high_pressure_day=5, normal_day=5, rejected_or_censored=5。

## 13. UI 数据契约

`v1_p0_ui_contract.json` 不含动态时间戳，控制在 30,761 bytes。它只包含全国摘要、有限链路、机场机制维度和案例候选，不嵌入全量 episode。

## 14. 可复现性与限制

科学产物 SHA-256 写入独立 manifest；本次是否与前次相同：True。运行时间和生成时间仅存在 manifest，不参与科学产物哈希。天气、机场拥堵及共同冲击尚未控制，所以传播率和 conditional lift 都不作因果解释。

## 15. 产品门槛与 V1 范围

| 产品门槛 | 结果 |
|---|---:|
| `n_episodes_gte_10000` | 通过 |
| `n_deep2_gte_1000` | 通过 |
| `n_deep3_gte_100` | 通过 |
| `airports_exposed500_gte_40` | 通过 |
| `links_qualified100_gte_50` | 通过 |
| `links_ci020_n100_gte_30` | 通过 |
| `thresholds_analyzed` | 通过 |
| `cases_each_5plus` | 通过 |

判定为 **GO**。仅当全部硬门槛通过时才允许进入 V1-A / V1-B；V1-A 可实现机制总览、机场连续维度和可靠链路，V1-B 再加入 episode explorer 与阈值切换。
