from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.airports_under_stress.congestion import PLAN_COLUMNS, build_congestion_features

OUT_EVENTS = ROOT / "data/processed/v3_p0_congestion_events.parquet"
OUT_SUMMARY = ROOT / "data/processed/v3_p0_congestion_summary.json"
OUT_MANIFEST = ROOT / "data/processed/v3_p0_manifest.json"
REPORT = ROOT / "reports/V3_P0_CONGESTION_AUDIT.md"
WINDOWS = (30, 60, 90)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def describe(series: pd.Series) -> dict[str, int | float]:
    values = pd.to_numeric(series, errors="coerce")
    return {
        "finite": int(np.isfinite(values).sum()),
        "missing": int(values.isna().sum()),
        "min": float(values.min()),
        "median": float(values.median()),
        "iqr": float(values.quantile(0.75) - values.quantile(0.25)),
        "p90": float(values.quantile(0.90)),
        "p99": float(values.quantile(0.99)),
        "max": float(values.max()),
    }


def congestion_group(relative: pd.Series) -> pd.Series:
    return pd.Series(
        np.where(relative <= 0.25, "low", np.where(relative >= 0.75, "high", "middle")),
        index=relative.index,
        dtype="string",
    )


def group_summary(frame: pd.DataFrame, window: int) -> dict[str, dict[str, int | float]]:
    grouped = frame.groupby(f"congestion_group_{window}m", sort=True).agg(
        n=("propagation", "size"),
        propagation_rate=("propagation", "mean"),
    )
    return {
        str(group): {"n": int(row.n), "propagation_rate": float(row.propagation_rate)}
        for group, row in grouped.iterrows()
    }


def fixed_quartile(relative: pd.Series) -> np.ndarray:
    values = relative.to_numpy()
    return np.select(
        [values < 0.25, values < 0.50, values < 0.75],
        [0, 1, 2],
        default=3,
    )


def gate_entry(passed: bool, value: object, criterion: str) -> dict[str, object]:
    return {"passed": bool(passed), "value": value, "criterion": criterion}


def main() -> None:
    flights = pd.read_parquet(ROOT / "data/processed/p0_flights.parquet")
    links = pd.read_parquet(ROOT / "data/processed/p0_chain_links.parquet")
    roles = pd.read_parquet(ROOT / "data/processed/v1_p0_airport_roles.parquet")

    airports = sorted(roles.loc[roles["nExposed"] >= 500, "code"].astype(str))
    event_mask = links["UpstreamArrDelayed15"].eq(True) & links["Origin"].isin(airports)
    event_columns = [
        "Origin",
        "ScheduledDepartureUTC",
        "Dest",
        "PrevArrDelay",
        "DownstreamDepDelayed15",
    ]
    events = links.loc[event_mask, event_columns].copy().reset_index(drop=True)
    events.insert(0, "event_id", np.arange(len(events), dtype=np.int64))

    # This exact selection is the leakage boundary: no actual-operation field
    # reaches the schedule table accepted by the feature function.
    plan = flights.loc[:, list(PLAN_COLUMNS)].copy()
    result = build_congestion_features(plan, events)
    result["propagation"] = result["DownstreamDepDelayed15"].astype(bool)
    for window in WINDOWS:
        result[f"congestion_group_{window}m"] = congestion_group(
            result[f"relative_congestion_{window}m"]
        )

    result.to_parquet(OUT_EVENTS, index=False)

    window_stats = {
        str(window): {
            metric: describe(result[f"{metric}_{window}m"])
            for metric in (
                "planned_departures",
                "planned_arrivals",
                "planned_total",
                "other_planned_departures",
                "relative_congestion",
            )
        }
        for window in WINDOWS
    }

    airport_rows: list[dict[str, object]] = []
    for airport, group in result.groupby("Origin", sort=True):
        relative = group["relative_congestion_60m"]
        counts = group["congestion_group_60m"].value_counts()
        airport_rows.append(
            {
                "airport": str(airport),
                "n": int(len(group)),
                "distinct": int(relative.nunique()),
                "iqr": float(relative.quantile(0.75) - relative.quantile(0.25)),
                "q25": float(relative.quantile(0.25)),
                "q75": float(relative.quantile(0.75)),
                "low_n": int(counts.get("low", 0)),
                "high_n": int(counts.get("high", 0)),
            }
        )
    airport_df = pd.DataFrame(airport_rows)

    groups_by_window = {str(window): group_summary(result, window) for window in WINDOWS}
    sensitivity: dict[str, dict[str, float | bool]] = {}
    primary_quartile = fixed_quartile(result["relative_congestion_60m"])
    primary_contrast = (
        groups_by_window["60"]["high"]["propagation_rate"]
        - groups_by_window["60"]["low"]["propagation_rate"]
    )
    contrasts = [primary_contrast]
    for window in (30, 90):
        relative = result[f"relative_congestion_{window}m"]
        rho = float(spearmanr(result["relative_congestion_60m"], relative).statistic)
        agreement = float((primary_quartile == fixed_quartile(relative)).mean())
        contrast = (
            groups_by_window[str(window)]["high"]["propagation_rate"]
            - groups_by_window[str(window)]["low"]["propagation_rate"]
        )
        contrasts.append(contrast)
        sensitivity[str(window)] = {
            "spearman_vs_60m": rho,
            "quartile_agreement_vs_60m": agreement,
            "high_minus_low_propagation_rate": float(contrast),
        }
    same_direction = all(np.sign(value) == np.sign(primary_contrast) for value in contrasts)
    stable_windows = same_direction and all(
        details["spearman_vs_60m"] >= 0.50
        and details["quartile_agreement_vs_60m"] >= 0.50
        for details in sensitivity.values()
    )

    high = result[result["congestion_group_60m"].eq("high")]
    max_airport_share = float(high["Origin"].value_counts(normalize=True).max())
    high_dates = pd.to_datetime(high["ScheduledDepartureUTC"], utc=True).dt.date
    max_day_share = float(high_dates.value_counts(normalize=True).max())

    feature_columns = [
        f"{metric}_{window}m"
        for window in WINDOWS
        for metric in (
            "planned_departures",
            "planned_arrivals",
            "planned_total",
            "other_planned_departures",
            "relative_congestion",
        )
    ]
    all_finite = bool(np.isfinite(result[feature_columns].to_numpy(dtype=float)).all())
    all_nonnegative = bool((result[feature_columns].to_numpy(dtype=float) >= 0).all())
    focal_covered = bool(
        all((result[f"planned_departures_{window}m"] >= 1).all() for window in WINDOWS)
    )
    other_nonnegative = bool(
        all((result[f"other_planned_departures_{window}m"] >= 0).all() for window in WINDOWS)
    )

    primary_groups = groups_by_window["60"]
    min_low = int(airport_df["low_n"].min())
    min_high = int(airport_df["high_n"].min())
    gate_checks = {
        "coverage": gate_entry(
            len(airports) == 55 and result["Origin"].nunique() == 55 and len(result) == 91185,
            {"airports": int(result["Origin"].nunique()), "events": int(len(result))},
            "55 airports and 91,185 frozen events",
        ),
        "finite_nonnegative": gate_entry(
            all_finite and all_nonnegative and focal_covered and other_nonnegative,
            {
                "all_finite": all_finite,
                "all_nonnegative": all_nonnegative,
                "focal_departure_covered": focal_covered,
                "other_departures_nonnegative": other_nonnegative,
            },
            "all three windows finite/nonnegative and focal flight present",
        ),
        "schedule_only_contract": gate_entry(
            tuple(plan.columns) == PLAN_COLUMNS,
            list(plan.columns),
            "exact five-column schedule whitelist",
        ),
        "dynamic_airports": gate_entry(
            int((airport_df["iqr"] > 0).sum()) >= 50,
            int((airport_df["iqr"] > 0).sum()),
            "at least 50 of 55 airports have 60m relative-congestion IQR > 0",
        ),
        "national_group_samples": gate_entry(
            primary_groups["high"]["n"] >= 15000 and primary_groups["low"]["n"] >= 15000,
            {"high_n": primary_groups["high"]["n"], "low_n": primary_groups["low"]["n"]},
            "national high and low groups each contain at least 15,000 events",
        ),
        "airport_group_samples": gate_entry(
            min_low >= 100 and min_high >= 100,
            {"min_high_n": min_high, "min_low_n": min_low},
            "each of the 55 airports has at least 100 events in both groups",
        ),
        "concentration": gate_entry(
            max_airport_share < 0.15 and max_day_share < 0.10,
            {
                "max_high_airport_share": max_airport_share,
                "max_high_day_share": max_day_share,
            },
            "largest airport <15% and largest day <10% of high group",
        ),
        "window_sensitivity": gate_entry(
            stable_windows,
            {"same_contrast_direction": same_direction, **sensitivity},
            "30/90 vs 60m Spearman and quartile agreement >=0.50, contrast direction unchanged",
        ),
    }

    all_passed = all(check["passed"] for check in gate_checks.values())
    core_passed = all(
        gate_checks[name]["passed"]
        for name in (
            "coverage",
            "finite_nonnegative",
            "schedule_only_contract",
            "dynamic_airports",
            "national_group_samples",
            "window_sensitivity",
        )
    )
    gate_decision = "GO" if all_passed else ("CONDITIONAL GO" if core_passed else "NO-GO")

    summary = {
        "scope": {"mechanism_airports": len(airports), "event_count": len(result)},
        "reference_population": (
            "For each airport and window, every scheduled departure in p0_flights is ranked "
            "by scheduled departures plus scheduled arrivals around its departure time; "
            "event values use the identical total-movements metric and average-tie percentile."
        ),
        "windows": window_stats,
        "airports": airport_rows,
        "groups_by_window": groups_by_window,
        "window_sensitivity": sensitivity,
        "concentration": {
            "max_high_airport_share": max_airport_share,
            "max_high_day_share": max_day_share,
        },
        "gate_checks": gate_checks,
        "gate_decision": gate_decision,
        "interpretation_boundary": "Descriptive association only; not a causal congestion effect.",
    }
    OUT_SUMMARY.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    report_lines = [
        "# V3-P0 计划拥挤度可行性审计",
        "",
        f"审计范围：55 个 Mechanism 机场、{len(result):,} 条冻结事件。Gate：**{gate_decision}**。",
        "",
        "拥挤度完全来自计划时刻表：在事件计划起飞时刻周围，统计同机场计划出发与计划到达。相对拥挤度是在同一机场、同一窗口内，相对于该机场所有计划出发事件的计划总架次经验百分位；并列值取平均秩。",
        "",
        "## 三档窗口",
        "",
        "| 窗口 | 计划出发中位数 | 计划到达中位数 | 计划总架次 P90 |",
        "|---|---:|---:|---:|",
    ]
    for window in WINDOWS:
        stats = window_stats[str(window)]
        report_lines.append(
            f"| {window} 分钟 | {stats['planned_departures']['median']:.1f} | "
            f"{stats['planned_arrivals']['median']:.1f} | {stats['planned_total']['p90']:.1f} |"
        )
    report_lines.extend(
        [
            "",
            "## 高低拥挤组（描述性）",
            "",
            "| 窗口 | 低组样本 | 低组传播率 | 高组样本 | 高组传播率 | 高减低 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for window in WINDOWS:
        groups = groups_by_window[str(window)]
        contrast = groups["high"]["propagation_rate"] - groups["low"]["propagation_rate"]
        report_lines.append(
            f"| {window} 分钟 | {groups['low']['n']:,} | {groups['low']['propagation_rate']:.4f} | "
            f"{groups['high']['n']:,} | {groups['high']['propagation_rate']:.4f} | {contrast:+.4f} |"
        )
    report_lines.extend(["", "## Gate", ""])
    for name, check in gate_checks.items():
        marker = "通过" if check["passed"] else "未通过"
        report_lines.append(f"- **{marker}** `{name}`：{check['criterion']}；实际值 `{check['value']}`。")
    report_lines.extend(
        [
            "",
            "30/90 分钟与 60 分钟的详细 Spearman、四分位一致率及传播率方向见 summary。连续构建的字节一致性由 manifest 单独记录。",
            "",
            "高低组传播率只描述同时出现的现象，不代表计划拥挤造成延误传播。",
        ]
    )
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    scientific_outputs = (OUT_EVENTS, OUT_SUMMARY, REPORT)
    previous = json.loads(OUT_MANIFEST.read_text(encoding="utf-8")) if OUT_MANIFEST.exists() else {}
    hashes = {path.name: sha256(path) for path in scientific_outputs}
    manifest = {
        "outputs": hashes,
        "previous_outputs": previous.get("outputs", {}),
        "scientific_outputs_match_previous_run": hashes == previous.get("outputs", {}),
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
