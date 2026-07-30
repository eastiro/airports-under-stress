#!/usr/bin/env python
"""Build the deterministic V3-B airport scheduled-congestion explorer snapshot.

The ONLY data source is the frozen
``data/processed/v3_p0_congestion_events.parquet`` (91,185 events, 55 Mechanism
airports). This script never re-derives congestion, never touches any ``v3_p0_*``
file, and never re-runs the V3-P0 scientific implementation, thresholds, or event
attribution.

It aggregates the already-frozen ``congestion_group_30m/60m/90m`` and
``propagation`` columns into per-airport, per-window, per-group summaries
(``n``, ``propagated``, ``rate``, Wilson 95% interval, ``gapPercentagePoints``).

All science numbers are *computed* from the frozen Parquet — none are hand
written. The builder is deterministic and reproduces byte-for-byte identical
output across runs (no timestamps, no randomness, sorted keys).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
WEB = ROOT / "web" / "app"
PARQUET = DATA / "v3_p0_congestion_events.parquet"
SUMMARY = DATA / "v3_p0_congestion_summary.json"
OUT = WEB / "v3-b-data.json"

WINDOWS = ("30", "60", "90")
PRIMARY_WINDOW = "60"
AIRPORT_GATE_THRESHOLD = 100
DEFAULT_AIRPORT = "ATL"
EXCLUDED_AIRPORT = "OMA"

Z = 1.959963984540054  # 95% two-sided normal quantile


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wilson(x: int, n: int) -> dict[str, float]:
    """Wilson score 95% interval for a binomial proportion.

    Returns finite bounds that always contain the point estimate p_hat.
    """
    if n <= 0:
        return {"lower": 0.0, "upper": 0.0}
    p_hat = x / n
    z2 = Z * Z
    denom = 1 + z2 / n
    center = (p_hat + z2 / (2 * n)) / denom
    half = Z * np.sqrt(max(0.0, p_hat * (1 - p_hat) / n + z2 / (4 * n * n))) / denom
    lower = max(0.0, center - half)
    upper = min(1.0, center + half)
    return {"lower": lower, "upper": upper}


def build() -> dict:
    events = pd.read_parquet(PARQUET)

    # Frozen-fact guardrails: the parquet is the single source of truth.
    assert len(events) == 91185, len(events)
    assert events["Origin"].nunique() == 55, events["Origin"].nunique()

    # Per-airport aggregation of frozen low/high groups across the three windows.
    airports: dict[str, dict[str, object]] = {}
    for airport, group in events.groupby("Origin", sort=True):
        code = str(airport)
        windows: dict[str, dict[str, dict[str, float]]] = {}
        for w in WINDOWS:
            col = f"congestion_group_{w}m"
            window_block: dict[str, dict[str, float]] = {}
            for tier in ("low", "high"):
                sub = group.loc[group[col].eq(tier), "propagation"]
                n = int(len(sub))
                propagated = int(sub.sum())
                rate = float(propagated / n) if n else 0.0
                interval = wilson(propagated, n)
                window_block[tier] = {
                    "n": n,
                    "propagated": propagated,
                    "rate": rate,
                    "wilsonLower": interval["lower"],
                    "wilsonUpper": interval["upper"],
                }
            gap = round((window_block["high"]["rate"] - window_block["low"]["rate"]) * 100, 8)
            windows[w] = {
                "low": window_block["low"],
                "high": window_block["high"],
                "gapPercentagePoints": gap,
            }
        airports[code] = windows  # type: ignore[assignment]

    # Airport-level gate: both low and high groups >= 100 in the primary 60m window.
    eligible: list[str] = []
    excluded: list[dict[str, object]] = []
    for code, windows in airports.items():
        primary = windows[PRIMARY_WINDOW]
        low_n = primary["low"]["n"]
        high_n = primary["high"]["n"]
        if low_n >= AIRPORT_GATE_THRESHOLD and high_n >= AIRPORT_GATE_THRESHOLD:
            eligible.append(code)
        else:
            excluded.append(
                {
                    "airport": code,
                    "lowN": low_n,
                    "highN": high_n,
                    "reason": (
                        f"60 分钟窗口下低组 {low_n} / 高组 {high_n} 条；"
                        f"低于每机场每组至少 {AIRPORT_GATE_THRESHOLD} 条的门槛，故不进入合格列表。"
                    ),
                }
            )
    assert len(eligible) == 54, len(eligible)
    assert [e["airport"] for e in excluded] == [EXCLUDED_AIRPORT], excluded
    assert excluded[0]["lowN"] == 140 and excluded[0]["highN"] == 82, excluded[0]

    # Direction of the high-minus-low gap at each window for each eligible airport.
    for code in eligible:
        windows = airports[code]
        gaps = {w: windows[w]["gapPercentagePoints"] for w in WINDOWS}
        primary_dir = (
            "higher"
            if gaps[PRIMARY_WINDOW] > 0
            else ("lower" if gaps[PRIMARY_WINDOW] < 0 else "equal")
        )
        all_pos = all(gaps[w] > 0 for w in WINDOWS)
        all_neg = all(gaps[w] < 0 for w in WINDOWS)
        if all_pos:
            direction_label = "samePositive"
        elif all_neg:
            direction_label = "sameNegative"
        else:
            direction_label = "mixed"
        airports[code]["direction60"] = primary_dir
        airports[code]["directionLabel"] = direction_label

    # Snapshot-level direction counts over the 54 eligible airports.
    positive_60 = sum(1 for c in eligible if airports[c]["direction60"] == "higher")
    negative_60 = sum(1 for c in eligible if airports[c]["direction60"] == "lower")
    same_positive = sum(1 for c in eligible if airports[c]["directionLabel"] == "samePositive")
    assert positive_60 == 52, positive_60
    assert negative_60 == 2, negative_60
    assert same_positive == 48, same_positive
    counterexamples = sorted(
        c for c in eligible if airports[c]["direction60"] == "lower"
    )
    assert counterexamples == ["JFK", "ONT"], counterexamples

    # Pack the per-airport payload for the front end. Each airport keeps only the
    # aggregates (no event-level payload, no event ids, no absolute paths).
    airport_payload: dict[str, dict] = {}
    for code in eligible:
        windows = airports[code]
        airport_payload[code] = {
            "windows": {
                w: {
                    "low": {
                        "n": windows[w]["low"]["n"],
                        "propagated": windows[w]["low"]["propagated"],
                        "rate": windows[w]["low"]["rate"],
                        "wilsonLower": windows[w]["low"]["wilsonLower"],
                        "wilsonUpper": windows[w]["low"]["wilsonUpper"],
                    },
                    "high": {
                        "n": windows[w]["high"]["n"],
                        "propagated": windows[w]["high"]["propagated"],
                        "rate": windows[w]["high"]["rate"],
                        "wilsonLower": windows[w]["high"]["wilsonLower"],
                        "wilsonUpper": windows[w]["high"]["wilsonUpper"],
                    },
                    "gapPercentagePoints": windows[w]["gapPercentagePoints"],
                }
                for w in WINDOWS
            },
            "direction60": airports[code]["direction60"],
            "directionLabel": airports[code]["directionLabel"],
        }

    # Verify the default airport (ATL) is eligible and directionally positive on all
    # three windows.
    assert DEFAULT_AIRPORT in airport_payload, DEFAULT_AIRPORT
    assert airport_payload[DEFAULT_AIRPORT]["directionLabel"] == "samePositive", (
        DEFAULT_AIRPORT,
        airport_payload[DEFAULT_AIRPORT]["directionLabel"],
    )

    summary = json.loads(SUMMARY.read_text(encoding="utf-8")) if SUMMARY.exists() else {}

    output = {
        "version": "v3-b-1",
        "primaryWindowMinutes": int(PRIMARY_WINDOW),
        "windows": list(WINDOWS),
        "airportThreshold": AIRPORT_GATE_THRESHOLD,
        "scope": {
            "totalAirports": 55,
            "eligibleAirports": len(eligible),
            "excludedAirports": len(excluded),
            "eventCount": 91185,
        },
        "directionCounts60": {
            "positive": positive_60,
            "negative": negative_60,
            "equal": sum(1 for c in eligible if airports[c]["direction60"] == "equal"),
        },
        "samePositiveAirports": same_positive,
        "counterexamples60": counterexamples,
        "defaultAirport": DEFAULT_AIRPORT,
        "excluded": excluded,
        "airports": airport_payload,
        "sources": {
            "parquet": {
                "file": "data/processed/v3_p0_congestion_events.parquet",
                "sha256": sha256(PARQUET),
            },
            "summarySha256": sha256(SUMMARY) if SUMMARY.exists() else None,
            "note": (
                "All rates, n, propagated counts, Wilson intervals and gaps are "
                "computed deterministically from the frozen V3-P0 events parquet. "
                "No values are hand-written."
            ),
        },
    }
    if summary:
        output["sources"]["gateDecision"] = summary.get("gate_decision")
    return output


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build the V3-B airport explorer snapshot.")
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT,
        help="output JSON path (default: %(default)s)",
    )
    args = parser.parse_args()

    output = build()
    args.out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "output": str(args.out),
            "scope": output["scope"],
            "directionCounts60": output["directionCounts60"],
            "samePositiveAirports": output["samePositiveAirports"],
            "counterexamples60": output["counterexamples60"],
            "defaultAirport": output["defaultAirport"],
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
