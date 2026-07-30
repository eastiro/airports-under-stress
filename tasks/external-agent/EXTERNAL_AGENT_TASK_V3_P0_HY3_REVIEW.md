# External Agent Task — V3-P0 HY3 独立复核

日期：2026-07-28  
状态：已完成并经 Codex 复核  
执行者：WorkBuddy / CodeBuddy CLI / `hy3` / `high`  
验收者：Codex

## 目标

对当前 V3-P0 计划拥挤度审计做一次独立、只读的科学与代码复核，同时检查它与 P0、V1、V2 冻结口径之间是否存在明显冲突或回归。

本轮用于测试 HY3 作为外部执行者的能力。优先发现会改变 Gate、核心数字、研究结论或后续 V3-A 边界的问题，不做泛泛的风格点评。

## 必读文件

- `PROJECT_STATUS.md`
- `HANDOFF.md`
- `docs/P0_PROTOCOL.md`
- `tasks/external-agent/EXTERNAL_AGENT_TASK_V3_P0.md`
- `src/airports_under_stress/congestion.py`
- `scripts/run_v3_p0_congestion_audit.py`
- `tests/test_v3_congestion.py`
- `reports/V3_P0_CONGESTION_AUDIT.md`
- `data/processed/v3_p0_congestion_summary.json`
- `data/processed/v3_p0_manifest.json`

必要时可只读核对 V0/V1/V2 的构建器、报告和测试，但不要扩展成全项目代码风格审查。

## 审查重点

1. 计划拥挤特征是否严格只使用事前计划字段，有无结果泄漏。
2. 到达归属、事件机场、事件时刻、半开窗口、自身航班扣除是否正确。
3. 机场内经验百分位的 reference population、ties、30/60/90 分钟可比性是否正确。
4. 全国高低组样本、传播率、集中度、窗口敏感性和逐机场门槛是否由最终产物真实支持。
5. `CONDITIONAL GO` 是否是按冻结 Gate 得出的唯一合理判断，有无被遗漏的 NO-GO/GO 条件。
6. 测试是否真正覆盖上述高风险逻辑，而非只验证输出存在。
7. 报告、summary、manifest、项目状态之间是否存在陈旧数字或口径冲突。
8. 若进入 V3-A，哪些结论可以展示，哪些必须禁止；避免因果包装。

## 允许操作

- 读取和搜索项目文件。
- 运行只读诊断与现有测试；测试命令必须关闭 pytest cache。
- 查看 git diff/status，但不得改写 git 状态。

## 禁止操作

- 不得修改、创建或删除任何项目文件。
- 不得 commit、push、deploy、安装依赖或访问凭据。
- 不得调用子代理或 Agent Teams。
- 不得为了让测试通过而放宽冻结阈值。

## 输出格式

直接在最终回答中提供：

1. 总判定：`NO-GO / CONDITIONAL GO / GO`。
2. Findings：按 `P0 / P1 / P2` 排序；每项必须给出文件路径、尽量精确的行号或字段、证据、影响和建议。
3. 若没有阻塞问题，明确写“未发现会改变当前 Gate 的问题”，并列出仍存在的研究边界。
4. 实际运行的测试及结果。
5. 建议 Codex 亲自核查的最多 5 个点。

不要用长篇项目复述代替审查结论，不要声称已经修改任何内容。

## 完成记录

执行会话：`7c7fd089-ffa0-4ac2-8952-b4b7a7da7c45`  
实际模型：`hy3` / `high`  
外部调用费用记录：`credit: 0`  
外部执行者未修改项目文件。

HY3 总判定为 **CONDITIONAL GO**，未发现会改变当前 Gate 的 P0 阻塞项。它确认唯一未通过的冻结门槛仍是逐机场样本量：最小高拥挤组为 OMA 的 82 条，低于每组 100 条要求；全国层 coverage、有限非负、计划字段契约、动态性、全国样本、集中度和窗口敏感性均与最终产物一致。

HY3 提出的非阻塞关注点：

- 30 分钟与 60 分钟的四分位一致率为 `0.509941`，仅略高于 `0.50` 门槛；V3-A 不应把 30 分钟档包装成稳定的机场排名。
- `congestion_group` 与 `fixed_quartile` 在恰好等于 0.25/0.75 时使用不同的闭区间语义。
- 现有测试验证 ties 的确定性与 `[0, 1]` 范围，但没有对 `(below + 0.5 * ties) / N` 做精确数值断言。
- `PrevArrDelay` 随事件帧保留但未参与特征；`DownstreamDepDelayed15` 只在计划特征完成后作为描述性结果加入，未发现泄漏。

Codex 复核：

- 实跑 `tests/test_v3_congestion.py`：`5 passed`。
- 核对三个窗口的最终事件产物：恰好等于 `0.25` 或 `0.75` 的相对拥挤度记录均为 `0`，因此两套边界写法对当前结果、Gate 和窗口一致率没有影响；30/90 分钟一致率仍分别为 `0.5099413281` / `0.6015024401`。
- 平均 ties 百分位实现与冻结公式一致，位于 `src/airports_under_stress/congestion.py` 的 `_empirical_percentile`。
- 本轮不修改冻结科学实现与产物。精确百分位 fixture 记为后续低风险测试增强；30 分钟展示边界带入 V3-A 规划。
