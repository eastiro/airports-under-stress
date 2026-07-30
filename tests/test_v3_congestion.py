import json
from pathlib import Path

import pandas as pd
import pytest

from src.airports_under_stress.congestion import (
    build_congestion_features,
    validate_plan_columns,
)

ROOT = Path(__file__).resolve().parents[1]


def fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Origin": ["AAA", "AAA", "AAA", "BBB", "BBB"],
            "Dest": ["BBB", "CCC", "BBB", "AAA", "AAA"],
            "ScheduledDepartureUTC": pd.to_datetime(
                [
                    "2026-05-01 00:00Z",
                    "2026-05-01 00:15Z",
                    "2026-05-01 00:30Z",
                    "2026-05-01 00:00Z",
                    "2026-05-01 01:00Z",
                ]
            ),
            "ScheduledArrivalUTC": pd.to_datetime(
                [
                    "2026-05-01 00:10Z",
                    "2026-05-01 00:45Z",
                    "2026-05-01 01:00Z",
                    "2026-05-01 00:15Z",
                    "2026-05-01 01:15Z",
                ]
            ),
            "SourceRow": [1, 2, 3, 4, 5],
        }
    )


def test_half_open_boundary_arrival_direction_and_self_deduction():
    plan = fixture()
    events = pd.DataFrame(
        {
            "Origin": ["AAA", "BBB"],
            "ScheduledDepartureUTC": pd.to_datetime(
                ["2026-05-01 00:15Z", "2026-05-01 00:00Z"]
            ),
        }
    )
    out = build_congestion_features(plan, events)

    # AAA window is [00:00, 00:30): departure at +15m is excluded.
    assert out.loc[0, "planned_departures_30m"] == 2
    # BBB->AAA arrives at AAA at 00:15; AAA->BBB does not count as an AAA arrival.
    assert out.loc[0, "planned_arrivals_30m"] == 1
    assert out.loc[0, "planned_total_30m"] == 3
    assert out.loc[0, "other_planned_departures_30m"] == 1
    # AAA->BBB arrival is counted at BBB, proving destination-side assignment.
    assert out.loc[1, "planned_arrivals_30m"] == 1


def test_duplicate_events_ties_are_deterministic_and_windows_monotonic():
    plan = fixture()
    events = plan.iloc[[0, 0, 1]][["Origin", "ScheduledDepartureUTC"]]
    first = build_congestion_features(plan, events)
    second = build_congestion_features(plan, events)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 3
    assert first.loc[0, "relative_congestion_60m"] == first.loc[1, "relative_congestion_60m"]
    assert (first.planned_total_30m <= first.planned_total_60m).all()
    assert (first.planned_total_60m <= first.planned_total_90m).all()
    for window in (30, 60, 90):
        assert first[f"relative_congestion_{window}m"].between(0, 1).all()


def test_plan_column_contract_rejects_missing_and_runtime_fields():
    plan = fixture()
    with pytest.raises(ValueError):
        validate_plan_columns(plan.drop(columns=["Dest"]))
    with pytest.raises(ValueError):
        validate_plan_columns(plan.assign(DepDelay=10))


def test_missing_focal_departure_is_not_silently_clipped():
    events = pd.DataFrame(
        {
            "Origin": ["AAA"],
            "ScheduledDepartureUTC": pd.to_datetime(["2026-05-02 00:00Z"]),
        }
    )
    with pytest.raises(ValueError, match="absent"):
        build_congestion_features(fixture(), events)


def test_full_audit_outputs_cover_frozen_scope_when_present():
    summary_path = ROOT / "data/processed/v3_p0_congestion_summary.json"
    if not summary_path.exists():
        pytest.skip("run the V3-P0 audit before checking full outputs")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["scope"] == {"mechanism_airports": 55, "event_count": 91185}
    assert summary["gate_checks"]["coverage"]["passed"]
    assert summary["gate_checks"]["finite_nonnegative"]["passed"]
    assert summary["gate_checks"]["schedule_only_contract"]["passed"]
