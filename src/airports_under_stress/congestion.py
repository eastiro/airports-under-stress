"""Leakage-safe scheduled airport congestion features."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

PLAN_COLUMNS = (
    "Origin",
    "Dest",
    "ScheduledDepartureUTC",
    "ScheduledArrivalUTC",
    "SourceRow",
)
WINDOW_HALF_MINUTES = {30: 15, 60: 30, 90: 45}


@dataclass(frozen=True)
class AirportSchedule:
    departures: np.ndarray
    arrivals: np.ndarray


def _utc_ns(values: Iterable[object]) -> np.ndarray:
    timestamps = pd.to_datetime(values, utc=True, errors="raise")
    if timestamps.isna().any():
        raise ValueError("scheduled timestamps must not be missing")
    return timestamps.astype("int64").to_numpy()


def validate_plan_columns(frame: pd.DataFrame) -> None:
    """Require the exact pre-operation schedule whitelist."""
    actual = set(frame.columns)
    expected = set(PLAN_COLUMNS)
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        raise ValueError(
            f"plan columns must equal the schedule whitelist; "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )


def _schedule_index(plan: pd.DataFrame) -> dict[str, AirportSchedule]:
    """Index departures by Origin and arrivals by Dest.

    A flight's scheduled arrival belongs only to its destination. Keeping the
    two groupings separate prevents origin-side arrival double counting.
    """
    departures = {
        str(airport): np.sort(_utc_ns(rows["ScheduledDepartureUTC"]))
        for airport, rows in plan.groupby("Origin", sort=True)
    }
    arrivals = {
        str(airport): np.sort(_utc_ns(rows["ScheduledArrivalUTC"]))
        for airport, rows in plan.groupby("Dest", sort=True)
    }
    empty = np.array([], dtype=np.int64)
    return {
        airport: AirportSchedule(
            departures=departures.get(airport, empty),
            arrivals=arrivals.get(airport, empty),
        )
        for airport in sorted(set(departures) | set(arrivals))
    }


def _window_count(sorted_values: np.ndarray, event_ns: np.ndarray, half_ns: int) -> np.ndarray:
    """Count values in the centered half-open interval [event-half, event+half)."""
    return np.searchsorted(sorted_values, event_ns + half_ns, side="left") - np.searchsorted(
        sorted_values, event_ns - half_ns, side="left"
    )


def _empirical_percentile(reference: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Average-tie empirical percentile: (below + 0.5 * ties) / N."""
    if not len(reference):
        return np.full(len(values), np.nan)
    reference = np.sort(reference)
    left = np.searchsorted(reference, values, side="left")
    right = np.searchsorted(reference, values, side="right")
    return (left + (right - left) / 2.0) / len(reference)


def build_congestion_features(plan: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Build centered schedule-only congestion features for event rows.

    Extra event columns are preserved but never used in feature construction.
    The reference population is every scheduled departure at the same airport.
    """
    validate_plan_columns(plan)
    required_events = {"Origin", "ScheduledDepartureUTC"}
    missing_events = required_events - set(events.columns)
    if missing_events:
        raise ValueError(f"missing event columns: {sorted(missing_events)}")

    plan = plan.copy()
    output = events.copy().reset_index(drop=True)
    plan["Origin"] = plan["Origin"].astype(str)
    plan["Dest"] = plan["Dest"].astype(str)
    output["Origin"] = output["Origin"].astype(str)
    event_ns = _utc_ns(output["ScheduledDepartureUTC"])
    schedule = _schedule_index(plan)

    event_positions = {
        str(airport): np.asarray(positions, dtype=np.int64)
        for airport, positions in output.groupby("Origin", sort=False).groups.items()
    }
    reference_times = {
        str(airport): np.sort(_utc_ns(rows["ScheduledDepartureUTC"]))
        for airport, rows in plan.groupby("Origin", sort=True)
    }

    focal_present = np.zeros(len(output), dtype=bool)
    for airport, positions in event_positions.items():
        airport_schedule = schedule.get(airport)
        if airport_schedule is None or not len(airport_schedule.departures):
            continue
        insertion = np.searchsorted(
            airport_schedule.departures, event_ns[positions], side="left"
        )
        in_bounds = insertion < len(airport_schedule.departures)
        focal_present[positions[in_bounds]] = (
            airport_schedule.departures[insertion[in_bounds]] == event_ns[positions[in_bounds]]
        )
    if not focal_present.all():
        raise ValueError(
            f"{int((~focal_present).sum())} focal event departures are absent from the schedule"
        )

    for window_minutes, half_minutes in WINDOW_HALF_MINUTES.items():
        half_ns = half_minutes * 60 * 1_000_000_000
        departures = np.zeros(len(output), dtype=np.int64)
        arrivals = np.zeros(len(output), dtype=np.int64)

        for airport, positions in event_positions.items():
            airport_schedule = schedule.get(airport)
            if airport_schedule is None:
                continue
            departures[positions] = _window_count(
                airport_schedule.departures, event_ns[positions], half_ns
            )
            arrivals[positions] = _window_count(
                airport_schedule.arrivals, event_ns[positions], half_ns
            )

        if np.any(departures < 1):
            missing_count = int(np.sum(departures < 1))
            raise ValueError(
                f"{missing_count} event departures are absent from the {window_minutes}m schedule window"
            )

        total = departures + arrivals
        output[f"planned_departures_{window_minutes}m"] = departures
        output[f"planned_arrivals_{window_minutes}m"] = arrivals
        output[f"planned_total_{window_minutes}m"] = total
        output[f"other_planned_departures_{window_minutes}m"] = departures - 1

        relative = np.full(len(output), np.nan)
        for airport, positions in event_positions.items():
            airport_schedule = schedule.get(airport)
            airport_departures = reference_times.get(airport)
            if airport_schedule is None or airport_departures is None:
                continue
            reference_total = _window_count(
                airport_schedule.departures, airport_departures, half_ns
            ) + _window_count(airport_schedule.arrivals, airport_departures, half_ns)
            relative[positions] = _empirical_percentile(reference_total, total[positions])
        output[f"relative_congestion_{window_minutes}m"] = relative

    return output
