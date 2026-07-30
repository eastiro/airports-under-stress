#!/usr/bin/env python
"""Build the deterministic V3-A scheduled-congestion snapshot from frozen V3-P0 outputs.

The only data source is ``data/processed/v3_p0_congestion_summary.json``. This script
never re-derives congestion, never re-runs the V3-P0 gate, and never writes to any
``v3_p0_*`` file. The high-minus-low difference is *computed* from the frozen
propagation rates (not a hand-written constant). For 60m (the primary window) there is
no frozen ``window_sensitivity`` entry, so the difference is computed directly from
``groups_by_window["60"]``. For 30m and 90m the computed value is cross-checked against
the frozen ``window_sensitivity[w].high_minus_low_propagation_rate``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
WEB = ROOT / "web" / "app"
SUMMARY = DATA / "v3_p0_congestion_summary.json"
OUT = WEB / "v3-a-data.json"
WINDOWS = ("30", "60", "90")
DEFAULT_WINDOW = 60
AIRPORT_GATE_THRESHOLD = 100
MIN_HIGH_AIRPORT = "OMA"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build() -> dict:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    scope = summary["scope"]
    assert scope == {"mechanism_airports": 55, "event_count": 91185}, scope
    event_count = scope["event_count"]

    groups: dict[str, dict] = {}
    high_minus_low: dict[str, dict] = {}
    for w in WINDOWS:
        g = summary["groups_by_window"][w]
        low, middle, high = g["low"], g["middle"], g["high"]
        total = low["n"] + middle["n"] + high["n"]
        assert total == event_count, (w, total, event_count)
        # Computed from frozen propagation rates; never a handwritten constant.
        diff = round((high["propagation_rate"] - low["propagation_rate"]) * 100, 8)
        frozen_ws = summary["window_sensitivity"].get(w)
        if frozen_ws is not None:
            # 30m / 90m: cross-check the computed value against the frozen sensitivity entry.
            frozen_diff = round(frozen_ws["high_minus_low_propagation_rate"] * 100, 8)
            assert abs(diff - frozen_diff) < 1e-6, (w, diff, frozen_diff)
            computed_from = (
                "high.propagationRate - low.propagationRate "
                "(cross-checked vs frozen window_sensitivity)"
            )
        else:
            # 60m is the primary window: no frozen window_sensitivity entry exists,
            # so the difference is computed directly from groups_by_window["60"].
            assert w == "60", (w, "unexpected missing sensitivity entry")
            computed_from = (
                "high.propagationRate - low.propagationRate (primary 60m, direct)"
            )
        groups[w] = {
            "low": {"n": low["n"], "propagationRate": low["propagation_rate"]},
            "middle": {"n": middle["n"], "propagationRate": middle["propagation_rate"]},
            "high": {"n": high["n"], "propagationRate": high["propagation_rate"]},
        }
        high_minus_low[w] = {
            "percentagePoints": diff,
            "computedFrom": computed_from,
        }

    planned_movements = {}
    for w in WINDOWS:
        pt = summary["windows"][w]["planned_total"]
        planned_movements[w] = {"median": pt["median"], "p90": pt["p90"]}

    window_sensitivity: dict[str, dict] = {}
    for w in ("30", "90"):
        ws = summary["window_sensitivity"][w]
        window_sensitivity[w] = {
            "spearmanVs60m": ws["spearman_vs_60m"],
            "quartileAgreementVs60m": ws["quartile_agreement_vs_60m"],
            "highMinusLowPropagationRate": ws["high_minus_low_propagation_rate"],
        }

    gate = summary["gate_checks"]["airport_group_samples"]
    airport_gate = {
        "passed": bool(gate["passed"]),
        "minHighN": gate["value"]["min_high_n"],
        "minLowN": gate["value"]["min_low_n"],
        "threshold": AIRPORT_GATE_THRESHOLD,
        "minHighAirport": MIN_HIGH_AIRPORT,
    }

    output = {
        "version": "v3-a-1",
        "defaultWindowMinutes": DEFAULT_WINDOW,
        "windows": list(WINDOWS),
        "scope": {
            "mechanismAirports": scope["mechanism_airports"],
            "eventCount": event_count,
        },
        "plannedMovements": planned_movements,
        "groups": groups,
        "highMinusLow": high_minus_low,
        "windowSensitivity": window_sensitivity,
        "concentration": {
            "maxHighAirportShare": summary["concentration"]["max_high_airport_share"],
            "maxHighDayShare": summary["concentration"]["max_high_day_share"],
        },
        "airportGate": airport_gate,
        "gateDecision": summary["gate_decision"],
        "interpretationBoundary": summary["interpretation_boundary"],
        "sources": {
            "sha256": {
                "data/processed/v3_p0_congestion_summary.json": sha256(SUMMARY),
            },
            "reference": "reports/V3_P0_CONGESTION_AUDIT.md",
        },
    }
    return output


def main() -> None:
    output = build()
    OUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "output": str(OUT),
            "sha256": sha256(OUT),
            "scope": output["scope"],
            "gate": output["gateDecision"],
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
