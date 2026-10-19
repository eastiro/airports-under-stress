from __future__ import annotations

import json
import math
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import airportsdata
import pandas as pd

from .timeutils import parse_hhmm, scheduled_departure_utc

USE_COLUMNS = [
    "FlightDate",
    "Reporting_Airline",
    "DOT_ID_Reporting_Airline",
    "Tail_Number",
    "Flight_Number_Reporting_Airline",
    "OriginAirportID",
    "Origin",
    "DestAirportID",
    "Dest",
    "CRSDepTime",
    "DepTime",
    "DepDelay",
    "TaxiOut",
    "WheelsOff",
    "WheelsOn",
    "TaxiIn",
    "CRSArrTime",
    "ArrTime",
    "ArrDelay",
    "Cancelled",
    "CancellationCode",
    "Diverted",
    "CRSElapsedTime",
    "ActualElapsedTime",
    "AirTime",
    "Distance",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
]

PRIMARY_KEY = [
    "FlightDate",
    "DOT_ID_Reporting_Airline",
    "Flight_Number_Reporting_Airline",
    "OriginAirportID",
    "DestAirportID",
    "CRSDepTime",
]

CHAIN_COLUMNS = [
    "Tail_Number",
    "PrevFlightDate",
    "FlightDate",
    "PrevReportingAirline",
    "Reporting_Airline",
    "PrevFlightNumber",
    "Flight_Number_Reporting_Airline",
    "PrevOrigin",
    "PrevDest",
    "Origin",
    "Dest",
    "PrevScheduledDepartureUTC",
    "ScheduledDepartureUTC",
    "PrevScheduledArrivalUTC",
    "ScheduledArrivalUTC",
    "PrevActualArrivalUTC",
    "ActualDepartureUTC",
    "ScheduledTurnMinutes",
    "ActualTurnMinutes",
    "PrevArrDelay",
    "DepDelay",
    "ArrDelay",
    "LateAircraftDelay",
    "UpstreamArrDelayed15",
    "DownstreamDepDelayed15",
    "OfficialLateAircraft",
    "PropagationSignal",
    "RecoverySignal",
]


def _safe_ratio(numerator: float | int, denominator: float | int) -> float | None:
    if denominator == 0:
        return None
    return float(numerator / denominator)


def _finite(value: object) -> float | int | str | bool | None:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def load_month(archive_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(archive_path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise RuntimeError(f"Expected one CSV in {archive_path}, found {csv_names}")
        with archive.open(csv_names[0]) as source:
            frame = pd.read_csv(
                source,
                usecols=USE_COLUMNS,
                dtype={
                    "Reporting_Airline": "string",
                    "Tail_Number": "string",
                    "Origin": "string",
                    "Dest": "string",
                    "CancellationCode": "string",
                },
                low_memory=False,
            )

    frame.insert(0, "SourceRow", range(len(frame)))
    frame["FlightDate"] = pd.to_datetime(frame["FlightDate"], errors="raise")
    frame["Tail_Number"] = frame["Tail_Number"].str.strip().replace("", pd.NA)
    return frame


def airport_timezone_map() -> dict[str, str]:
    records = airportsdata.load("IATA")
    return {
        code: record["tz"]
        for code, record in records.items()
        if record.get("tz")
    }


def _build_scheduled_departures(
    frame: pd.DataFrame,
    origin_timezones: pd.Series,
) -> tuple[pd.Series, int]:
    values: list[object] = []
    invalid = 0
    for flight_date, hhmm, timezone_name in zip(
        frame["FlightDate"].dt.date,
        frame["CRSDepTime"],
        origin_timezones,
    ):
        if pd.isna(hhmm) or pd.isna(timezone_name):
            values.append(pd.NaT)
            continue
        try:
            values.append(scheduled_departure_utc(flight_date, hhmm, str(timezone_name)))
        except (ValueError, KeyError):
            invalid += 1
            values.append(pd.NaT)
    return pd.Series(pd.to_datetime(values, utc=True), index=frame.index), invalid


def _clock_minutes(value: object) -> float:
    if value is None or pd.isna(value):
        return float("nan")
    try:
        minutes, _ = parse_hhmm(value)
        return float(minutes)
    except ValueError:
        return float("nan")


def _local_arrival_parts(
    utc_times: pd.Series,
    destination_timezones: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    local_dates: list[object] = []
    local_minutes: list[float] = []
    for utc_time, timezone_name in zip(utc_times, destination_timezones):
        if pd.isna(utc_time) or pd.isna(timezone_name):
            local_dates.append(pd.NaT)
            local_minutes.append(float("nan"))
            continue
        local = utc_time.to_pydatetime().astimezone(ZoneInfo(str(timezone_name)))
        local_dates.append(pd.Timestamp(local.date()))
        local_minutes.append(float(local.hour * 60 + local.minute))
    return (
        pd.Series(pd.to_datetime(local_dates), index=utc_times.index),
        pd.Series(local_minutes, index=utc_times.index, dtype="float64"),
    )


def _circular_clock_difference(left: pd.Series, right: pd.Series) -> pd.Series:
    raw = (left - right).abs()
    return pd.concat([raw, 1440 - raw], axis=1).min(axis=1)


def _naive_schedule(frame: pd.DataFrame) -> pd.Series:
    numeric = pd.to_numeric(frame["CRSDepTime"], errors="coerce")
    hhmm = numeric.fillna(-1).astype("int64")
    minutes = (hhmm // 100) * 60 + (hhmm % 100)
    minutes = minutes.where(hhmm != 2400, 1440)
    minutes = minutes.where(numeric.notna())
    return frame["FlightDate"] + pd.to_timedelta(minutes, unit="m")


def build_rotation_links(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    chain = frame.loc[
        (frame["Cancelled"] == 0)
        & (frame["Diverted"] == 0)
        & frame["Tail_Number"].notna()
        & frame["ScheduledDepartureUTC"].notna()
        & frame["ScheduledArrivalUTC"].notna()
    ].copy()
    chain = chain.sort_values(
        ["Tail_Number", "ScheduledDepartureUTC", "SourceRow"],
        kind="stable",
    )
    grouped = chain.groupby("Tail_Number", sort=False)

    previous_fields = {
        "FlightDate": "PrevFlightDate",
        "Reporting_Airline": "PrevReportingAirline",
        "Flight_Number_Reporting_Airline": "PrevFlightNumber",
        "Origin": "PrevOrigin",
        "Dest": "PrevDest",
        "ScheduledDepartureUTC": "PrevScheduledDepartureUTC",
        "ScheduledArrivalUTC": "PrevScheduledArrivalUTC",
        "ActualArrivalUTC": "PrevActualArrivalUTC",
        "ArrDelay": "PrevArrDelay",
    }
    for source, target in previous_fields.items():
        chain[target] = grouped[source].shift()

    chain["MinutesSincePreviousDeparture"] = (
        chain["ScheduledDepartureUTC"] - chain["PrevScheduledDepartureUTC"]
    ).dt.total_seconds() / 60
    chain["ScheduledTurnMinutes"] = (
        chain["ScheduledDepartureUTC"] - chain["PrevScheduledArrivalUTC"]
    ).dt.total_seconds() / 60
    chain["ActualTurnMinutes"] = (
        chain["ActualDepartureUTC"] - chain["PrevActualArrivalUTC"]
    ).dt.total_seconds() / 60

    has_previous = chain["PrevScheduledDepartureUTC"].notna()
    adjacent_window = has_previous & chain["MinutesSincePreviousDeparture"].between(0, 18 * 60)
    airport_continuity = chain["PrevDest"].eq(chain["Origin"])
    schedule_valid_link = (
        airport_continuity
        & chain["ScheduledTurnMinutes"].between(0, 12 * 60)
        & chain["ActualDepartureUTC"].notna()
        & chain["PrevActualArrivalUTC"].notna()
    )
    negative_actual_turn = schedule_valid_link & (chain["ActualTurnMinutes"] < 0)
    valid_link = schedule_valid_link & (chain["ActualTurnMinutes"] >= 0)

    links = chain.loc[valid_link].copy()
    links["UpstreamArrDelayed15"] = links["PrevArrDelay"] >= 15
    links["DownstreamDepDelayed15"] = links["DepDelay"] >= 15
    links["OfficialLateAircraft"] = links["LateAircraftDelay"].fillna(0) > 0
    links["PropagationSignal"] = (
        links["UpstreamArrDelayed15"] & links["DownstreamDepDelayed15"]
    )
    links["RecoverySignal"] = (
        links["UpstreamArrDelayed15"] & ~links["DownstreamDepDelayed15"]
    )

    candidate_count = int(adjacent_window.sum())
    continuity_count = int((adjacent_window & airport_continuity).sum())

    utc_rank = chain.groupby("Tail_Number", sort=False).cumcount()
    naive_order = chain.sort_values(
        ["Tail_Number", "NaiveScheduledDeparture", "SourceRow"],
        kind="stable",
    )
    naive_rank = naive_order.groupby("Tail_Number", sort=False).cumcount()
    naive_rank = pd.Series(naive_rank.to_numpy(), index=naive_order.index).reindex(chain.index)
    order_disagreement = utc_rank.ne(naive_rank)

    link_metrics = {
        "rotation_eligible_flights": len(chain),
        "same_tail_adjacent_within_18h": candidate_count,
        "airport_continuous_adjacencies": continuity_count,
        "airport_continuity_rate": _safe_ratio(continuity_count, candidate_count),
        "valid_chain_links": len(links),
        "flights_with_valid_predecessor_rate": _safe_ratio(len(links), len(chain)),
        "naive_vs_utc_order_disagreement_rows": int(order_disagreement.sum()),
        "naive_vs_utc_order_disagreement_rate": _safe_ratio(
            int(order_disagreement.sum()), len(chain)
        ),
        "negative_actual_turn_candidates_excluded": int(negative_actual_turn.sum()),
    }
    return links[CHAIN_COLUMNS], link_metrics


def propagation_metrics(links: pd.DataFrame) -> dict[str, object]:
    upstream = links["UpstreamArrDelayed15"]
    inferred = links["PropagationSignal"]
    official = links["OfficialLateAircraft"]
    propagated = int((upstream & links["DownstreamDepDelayed15"]).sum())
    recovered = int((upstream & ~links["DownstreamDepDelayed15"]).sum())
    tp = int((inferred & official).sum())
    fp = int((inferred & ~official).sum())
    fn = int((~inferred & official).sum())
    tn = int((~inferred & ~official).sum())

    return {
        "upstream_arrival_delayed_15_links": int(upstream.sum()),
        "propagated_links": propagated,
        "recovered_links": recovered,
        "propagation_rate_given_upstream_delay": _safe_ratio(propagated, int(upstream.sum())),
        "recovery_rate_given_upstream_delay": _safe_ratio(recovered, int(upstream.sum())),
        "official_late_aircraft_positive_links": int(official.sum()),
        "inferred_vs_official_confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "inferred_precision_against_official": _safe_ratio(tp, tp + fp),
        "inferred_recall_against_official": _safe_ratio(tp, tp + fn),
        "previous_arrival_vs_current_departure_delay_pearson": _finite(
            links["PrevArrDelay"].corr(links["DepDelay"])
        ),
    }


def choose_chain_samples(links: pd.DataFrame, per_type: int = 8) -> pd.DataFrame:
    categories = {
        "propagated_official": links["PropagationSignal"] & links["OfficialLateAircraft"],
        "recovered": links["RecoverySignal"],
        "inferred_not_official": links["PropagationSignal"] & ~links["OfficialLateAircraft"],
        "official_without_inferred": ~links["PropagationSignal"] & links["OfficialLateAircraft"],
    }
    samples: list[pd.DataFrame] = []
    for label, mask in categories.items():
        subset = links.loc[mask].sort_values(
            ["PrevArrDelay", "DepDelay"], ascending=False
        ).head(per_type).copy()
        subset.insert(0, "SampleType", label)
        samples.append(subset)
    return pd.concat(samples, ignore_index=True) if samples else pd.DataFrame()


def run_audit(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    timezones = airport_timezone_map()
    frame["OriginTimezone"] = frame["Origin"].map(timezones)
    frame["DestTimezone"] = frame["Dest"].map(timezones)
    frame["ScheduledDepartureUTC"], invalid_hhmm = _build_scheduled_departures(
        frame, frame["OriginTimezone"]
    )
    frame["ScheduledArrivalUTC"] = frame["ScheduledDepartureUTC"] + pd.to_timedelta(
        frame["CRSElapsedTime"], unit="m"
    )
    frame["ActualDepartureUTC"] = frame["ScheduledDepartureUTC"] + pd.to_timedelta(
        frame["DepDelay"], unit="m"
    )
    frame["ActualArrivalUTC"] = frame["ActualDepartureUTC"] + pd.to_timedelta(
        frame["ActualElapsedTime"], unit="m"
    )
    frame["NaiveScheduledDeparture"] = _naive_schedule(frame)

    scheduled_local_date, scheduled_local_minutes = _local_arrival_parts(
        frame["ScheduledArrivalUTC"], frame["DestTimezone"]
    )
    _, actual_local_minutes = _local_arrival_parts(
        frame["ActualArrivalUTC"], frame["DestTimezone"]
    )
    reported_scheduled_minutes = frame["CRSArrTime"].map(_clock_minutes)
    reported_actual_minutes = frame["ArrTime"].map(_clock_minutes)
    scheduled_clock_diff = _circular_clock_difference(
        scheduled_local_minutes, reported_scheduled_minutes
    )
    actual_clock_diff = _circular_clock_difference(
        actual_local_minutes, reported_actual_minutes
    )

    operated = frame["Cancelled"] == 0
    normal = operated & (frame["Diverted"] == 0)
    endpoint_tz_covered = frame["OriginTimezone"].notna() & frame["DestTimezone"].notna()
    tail_present = frame["Tail_Number"].notna()
    scheduled_clock_comparable = normal & scheduled_clock_diff.notna()
    actual_clock_comparable = normal & actual_clock_diff.notna()
    duplicate_rows = int(frame.duplicated(PRIMARY_KEY, keep=False).sum())

    links, link_metrics = build_rotation_links(frame)
    propagation = propagation_metrics(links)
    cross_midnight = normal & scheduled_local_date.notna() & (
        scheduled_local_date != frame["FlightDate"].dt.normalize()
    )

    quality = {
        "rows": len(frame),
        "date_min": frame["FlightDate"].min().date().isoformat(),
        "date_max": frame["FlightDate"].max().date().isoformat(),
        "reporting_airlines": int(frame["Reporting_Airline"].nunique()),
        "airports": int(pd.concat([frame["Origin"], frame["Dest"]]).nunique()),
        "unique_tail_numbers": int(frame["Tail_Number"].nunique()),
        "cancelled_flights": int((frame["Cancelled"] == 1).sum()),
        "cancelled_rate": _safe_ratio(int((frame["Cancelled"] == 1).sum()), len(frame)),
        "diverted_flights": int((frame["Diverted"] == 1).sum()),
        "diverted_rate": _safe_ratio(int((frame["Diverted"] == 1).sum()), len(frame)),
        "tail_number_coverage_all": _safe_ratio(int(tail_present.sum()), len(frame)),
        "tail_number_coverage_operated": _safe_ratio(
            int((operated & tail_present).sum()), int(operated.sum())
        ),
        "tail_number_coverage_cancelled": _safe_ratio(
            int(((frame["Cancelled"] == 1) & tail_present).sum()),
            int((frame["Cancelled"] == 1).sum()),
        ),
        "endpoint_timezone_coverage_normal": _safe_ratio(
            int((normal & endpoint_tz_covered).sum()), int(normal.sum())
        ),
        "missing_timezone_airports": sorted(
            set(frame.loc[frame["OriginTimezone"].isna(), "Origin"].dropna())
            | set(frame.loc[frame["DestTimezone"].isna(), "Dest"].dropna())
        ),
        "invalid_scheduled_departure_hhmm": invalid_hhmm,
        "candidate_primary_key_duplicate_rows": duplicate_rows,
        "candidate_primary_key_duplicate_rate": _safe_ratio(duplicate_rows, len(frame)),
        "scheduled_arrival_clock_match_within_2m": _safe_ratio(
            int((scheduled_clock_comparable & (scheduled_clock_diff <= 2)).sum()),
            int(scheduled_clock_comparable.sum()),
        ),
        "actual_arrival_clock_match_within_2m": _safe_ratio(
            int((actual_clock_comparable & (actual_clock_diff <= 2)).sum()),
            int(actual_clock_comparable.sum()),
        ),
        "scheduled_cross_midnight_flights": int(cross_midnight.sum()),
        "scheduled_cross_midnight_rate": _safe_ratio(int(cross_midnight.sum()), int(normal.sum())),
    }

    gates = {
        "operated_tail_coverage_at_least_98pct": quality["tail_number_coverage_operated"] >= 0.98,
        "timezone_coverage_at_least_99_5pct": quality["endpoint_timezone_coverage_normal"] >= 0.995,
        "scheduled_clock_match_at_least_99_5pct": quality[
            "scheduled_arrival_clock_match_within_2m"
        ]
        >= 0.995,
        "duplicate_rate_at_most_0_1pct": quality["candidate_primary_key_duplicate_rate"] <= 0.001,
        "airport_continuity_at_least_95pct": link_metrics["airport_continuity_rate"] >= 0.95,
        "at_least_100k_valid_chain_links": link_metrics["valid_chain_links"] >= 100_000,
    }

    metrics = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "quality": quality,
        "chains": link_metrics,
        "propagation_diagnostic": propagation,
        "gates": gates,
        "decision": "GO" if all(gates.values()) else "NO-GO",
    }
    return links, metrics


def write_metrics(metrics: dict[str, object], path: Path) -> None:
    path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, default=_finite),
        encoding="utf-8",
    )
