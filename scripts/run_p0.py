from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from airports_under_stress.audit import (
    choose_chain_samples,
    load_month,
    run_audit,
    write_metrics,
)
from airports_under_stress.config import PROCESSED_DIR, REPORT_DIR, archive_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Airports Under Stress P0 audit")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, choices=range(1, 13), required=True)
    return parser.parse_args()


def pct(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}%}"


def number(value: int | float | None) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.3f}"


def write_report(metrics: dict[str, object], source: dict[str, object]) -> Path:
    quality = metrics["quality"]
    chains = metrics["chains"]
    propagation = metrics["propagation_diagnostic"]
    gates = metrics["gates"]

    gate_labels = {
        "operated_tail_coverage_at_least_98pct": "已执行航班机尾号覆盖率 ≥ 98%",
        "timezone_coverage_at_least_99_5pct": "正常航班两端时区覆盖率 ≥ 99.5%",
        "scheduled_clock_match_at_least_99_5pct": "计划到达时钟复算一致率 ≥ 99.5%",
        "duplicate_rate_at_most_0_1pct": "候选主键重复率 ≤ 0.1%",
        "airport_continuity_at_least_95pct": "相邻航段机场连续率 ≥ 95%",
        "at_least_100k_valid_chain_links": "有效轮转链边 ≥ 100,000",
    }
    gate_rows = "\n".join(
        f"| {gate_labels[name]} | {'通过' if passed else '未通过'} |"
        for name, passed in gates.items()
    )
    decision_line = (
        "数据满足预先冻结的全部门槛，可以进入 V0。"
        if metrics["decision"] == "GO"
        else "至少一个硬门槛未通过，当前版本不进入 V0。"
    )

    report = f"""# P0 数据可行性审计

## 结论：{metrics['decision']}

{decision_line}

本报告使用 **{quality['date_min']} 至 {quality['date_max']}** 的 BTS Reporting Carrier On-Time Performance 逐航班数据。P0 的目标不是证明因果，而是验证能否可靠地重建飞机轮转，并量化“上一个航段晚到、下一个航段是否继续晚发”的结构性信号。

## 数据源完整性

| 项目 | 结果 |
|---|---|
| 官方下载地址 | {source.get('url', 'n/a')} |
| 文件字节数 | {number(source.get('bytes'))} |
| SHA-256 | `{source.get('sha256', 'n/a')}` |
| 服务器最后修改时间 | {source.get('last_modified', 'n/a')} |
| 航班记录数 | {number(quality['rows'])} |
| 报告航司数 | {number(quality['reporting_airlines'])} |
| 机场数 | {number(quality['airports'])} |
| 唯一机尾号数 | {number(quality['unique_tail_numbers'])} |

## 预先冻结的进入门槛

| 门槛 | 结果 |
|---|---|
{gate_rows}

## 数据质量

| 指标 | 结果 |
|---|---:|
| 已执行航班机尾号覆盖率 | {pct(quality['tail_number_coverage_operated'], 4)} |
| 取消航班机尾号覆盖率 | {pct(quality['tail_number_coverage_cancelled'], 4)} |
| 正常航班两端时区覆盖率 | {pct(quality['endpoint_timezone_coverage_normal'], 4)} |
| 计划到达时钟复算误差 ≤ 2 分钟 | {pct(quality['scheduled_arrival_clock_match_within_2m'], 4)} |
| 实际到达时钟复算误差 ≤ 2 分钟 | {pct(quality['actual_arrival_clock_match_within_2m'], 4)} |
| 候选主键重复率 | {pct(quality['candidate_primary_key_duplicate_rate'], 4)} |
| 取消航班 | {number(quality['cancelled_flights'])} ({pct(quality['cancelled_rate'])}) |
| 备降航班 | {number(quality['diverted_flights'])} ({pct(quality['diverted_rate'])}) |
| 计划跨午夜航班 | {number(quality['scheduled_cross_midnight_flights'])} ({pct(quality['scheduled_cross_midnight_rate'])}) |
| 缺失时区的机场代码 | {', '.join(quality['missing_timezone_airports']) or '无'} |

已执行航班与取消航班的机尾号覆盖率存在差距，这是预期现象：BTS 报告规范允许“在分配飞机前已取消”的航班不填机尾号。因此，取消航班保留在完整性统计中，但不会被伪装成飞机真正飞过的一条链边。

## 飞机轮转链重建

| 指标 | 结果 |
|---|---:|
| 可进入轮转审计的已执行航班 | {number(chains['rotation_eligible_flights'])} |
| 同机尾号且间隔不超过 18 小时的相邻航段 | {number(chains['same_tail_adjacent_within_18h'])} |
| 满足“上一站终点 = 下一站起点”的相邻航段 | {number(chains['airport_continuous_adjacencies'])} |
| 相邻航段机场连续率 | {pct(chains['airport_continuity_rate'])} |
| 通过全部物理检查的链边 | {number(chains['valid_chain_links'])} |
| 拥有有效上一航段的航班占比 | {pct(chains['flights_with_valid_predecessor_rate'])} |
| 本地时钟排序与 UTC 排序不同的记录 | {number(chains['naive_vs_utc_order_disagreement_rows'])} ({pct(chains['naive_vs_utc_order_disagreement_rate'])}) |
| 因实际周转时间为负而排除的候选链边 | {number(chains['negative_actual_turn_candidates_excluded'])} |

本地时间排序差异不是“无伤大雅的小误差”。同一架飞机一天可以多次跨时区，直接按 HHMM 排序会交换航段顺序，制造不可能存在的链。P0 因此先构造统一 UTC 时间轴，再连接航班。即使机场连续且计划周转合理，只要复算出的实际周转时间为负，也会从最终链路中排除。

## 延误传播诊断

本节是描述性验证，不是因果估计。

| 指标 | 结果 |
|---|---:|
| 上一航段到达延误至少 15 分钟的链边 | {number(propagation['upstream_arrival_delayed_15_links'])} |
| 下一航段起飞也延误至少 15 分钟 | {number(propagation['propagated_links'])} |
| 下一航段恢复到 15 分钟以内 | {number(propagation['recovered_links'])} |
| 给定上游延误后的传播率 | {pct(propagation['propagation_rate_given_upstream_delay'])} |
| 给定上游延误后的恢复率 | {pct(propagation['recovery_rate_given_upstream_delay'])} |
| BTS `LateAircraftDelay` 为正的链边 | {number(propagation['official_late_aircraft_positive_links'])} |
| 结构信号相对官方标签的精确率 | {pct(propagation['inferred_precision_against_official'])} |
| 结构信号相对官方标签的召回率 | {pct(propagation['inferred_recall_against_official'])} |
| 上一航段到达延误与当前起飞延误相关系数 | {number(propagation['previous_arrival_vs_current_departure_delay_pearson'])} |

结构信号与 `LateAircraftDelay` 应该明显重叠，但不应该完全相同。前者观察的是时间与物理连续性，后者是航司按 BTS 规则上报的延误原因分钟数。把其中任何一个当作完美因果真值，都会过度声称。

## P0 证明了什么、没有证明什么

P0 证明：这张原始表可以在足够大的样本上支持可复现的飞机轮转链重建，并且能够明确处理时区、午夜换日、取消和备降；同时可以给出第一版传播/恢复经验诊断。

P0 **没有**声称每一班晚到飞机都“导致”了下一班晚飞，也没有声称数据覆盖所有美国航司，更没有控制天气和机场拥堵。这些分别属于 V1 和 V2。

## 官方参考

- BTS table information and downloads: <https://www.transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ>
- BTS field definitions: <https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ>
- BTS Reporting Directive No. 39 (effective 2025): <https://www.bts.gov/explore-topics-and-geography/modes/aviation/number-39-technical-directive-reporting-time>
"""
    path = REPORT_DIR / "P0_DATA_AUDIT.md"
    path.write_text(report, encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    source_path = archive_path(args.year, args.month)
    if not source_path.exists():
        raise SystemExit(
            f"Missing {source_path}. Run scripts/download_bts.py first."
        )

    print("loading official BTS month...", flush=True)
    frame = load_month(source_path)
    print(f"loaded {len(frame):,} flights; building UTC timeline and chains...", flush=True)
    links, metrics = run_audit(frame)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(PROCESSED_DIR / "p0_flights.parquet", index=False)
    links.to_parquet(PROCESSED_DIR / "p0_chain_links.parquet", index=False)
    choose_chain_samples(links).to_csv(
        PROCESSED_DIR / "p0_chain_samples.csv", index=False, encoding="utf-8-sig"
    )
    write_metrics(metrics, PROCESSED_DIR / "p0_metrics.json")

    metadata_path = PROCESSED_DIR / "source_metadata.json"
    source_metadata = (
        json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata_path.exists()
        else {}
    )
    report_path = write_report(metrics, source_metadata)
    print(f"P0 decision: {metrics['decision']}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
