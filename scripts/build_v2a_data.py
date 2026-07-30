#!/usr/bin/env python
"""Build the deterministic V2-A weather-stratification snapshot."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
WEB = ROOT / "web" / "app"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from airports_under_stress.weather import backward_join_by_station

OUT = WEB / "v2-a-data.json"
TOLERANCES = (60, 90)
CATEGORIES = (
    "low_visibility", "low_ceiling", "strong_wind", "precipitation",
    "thunderstorm", "fog",
)
EXPECTED_INSUFFICIENT = {"MKE", "ONT", "PDX", "PHX", "SJC", "SJU", "SNA"}
ANNOTATION_COLUMNS = [
    "valid_utc", "report_type", "adverse_weather", *CATEGORIES,
    "visibility_km", "ceiling_ft", "wind_speed_mps", "wind_gust_mps",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean(item) for item in value]
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return clean(value.item())
    return value


def wilson(success: int, n: int) -> list[float] | None:
    if not n:
        return None
    p, z = success / n, 1.959963984540054
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denominator
    return [round(max(0.0, centre - half), 8), round(min(1.0, centre + half), 8)]


def summarize(group: pd.DataFrame) -> dict[str, Any]:
    n = len(group)
    propagated = int(group["DownstreamDepDelayed15"].sum())
    return {
        "n": n,
        "propagated": propagated,
        "recovered": n - propagated,
        "propagationRate": propagated / n if n else None,
        "recoveryRate": (n - propagated) / n if n else None,
        "wilson95": wilson(propagated, n),
    }


def main() -> None:
    links = pd.read_parquet(DATA / "p0_chain_links.parquet")
    roles = pd.read_parquet(DATA / "v1_p0_airport_roles.parquet")
    observations = pd.read_parquet(DATA / "v2_p0_weather_observations.parquet")
    weather_summary = json.loads((DATA / "v2_p0_weather_summary.json").read_text(encoding="utf-8"))
    v1b = json.loads((WEB / "v1-b-data.json").read_text(encoding="utf-8"))

    mechanism = sorted(set(roles.loc[roles["nExposed"] >= 500, "code"]))
    usable = observations[
        observations["usable_for_exposure"].eq(True) & observations["airport_code"].notna()
    ].copy()
    usable["valid_utc"] = pd.to_datetime(usable["valid_utc"], utc=True, errors="coerce")
    usable_airports = set(usable["airport_code"].dropna().astype(str))
    base = links[
        links["UpstreamArrDelayed15"].eq(True) & links["Origin"].isin(mechanism)
    ].copy()
    events = base[["Origin", "ScheduledDepartureUTC", "DownstreamDepDelayed15"]].rename(
        columns={"Origin": "airport_code", "ScheduledDepartureUTC": "event_utc"}
    )

    comparisons: dict[str, Any] = {}
    airport_comparisons: dict[str, Any] = {}
    category_comparisons: dict[str, Any] = {}
    insufficient_by_tolerance: dict[str, list[str]] = {}
    for tolerance in TOLERANCES:
        joined = backward_join_by_station(
            events, usable, station_col="airport_code", time_col="event_utc",
            tolerance_minutes=tolerance,
        )
        joined = joined[joined["weather_age_minutes"].notna()].copy()
        assert joined["weather_age_minutes"].ge(0).all(), "future weather leaked into V2-A"
        joined["adverse_weather"] = joined["adverse_weather"].astype(bool)
        adverse = summarize(joined[joined["adverse_weather"]])
        non_adverse = summarize(joined[~joined["adverse_weather"]])
        comparisons[str(tolerance)] = {
            "toleranceMinutes": tolerance,
            "matched": len(joined),
            "matchRate": len(joined) / len(events),
            "maxWeatherAgeMinutes": float(joined["weather_age_minutes"].max()),
            "adverse": adverse,
            "nonAdverse": non_adverse,
            "differencePercentagePoints": (
                adverse["propagationRate"] - non_adverse["propagationRate"]
            ) * 100,
        }
        airport_rows = []
        for airport in mechanism:
            airport_group = joined[joined["airport_code"] == airport]
            airport_adverse = summarize(airport_group[airport_group["adverse_weather"]])
            airport_non_adverse = summarize(airport_group[~airport_group["adverse_weather"]])
            comparable = airport_adverse["n"] >= 50 and airport_non_adverse["n"] >= 50
            airport_rows.append({
                "airport": airport,
                "adverse": airport_adverse,
                "nonAdverse": airport_non_adverse,
                "comparable": comparable,
                "differencePercentagePoints": (
                    airport_adverse["propagationRate"] - airport_non_adverse["propagationRate"]
                ) * 100 if comparable else None,
                "status": "comparable" if comparable else "insufficient_sample",
            })
        airport_comparisons[str(tolerance)] = airport_rows
        derived_insufficient = sorted(row["airport"] for row in airport_rows if not row["comparable"])
        assert set(derived_insufficient) == EXPECTED_INSUFFICIENT
        insufficient_by_tolerance[str(tolerance)] = derived_insufficient
        category_comparisons[str(tolerance)] = [
            {"category": category, **summarize(joined[joined[category].astype(bool)])}
            for category in CATEGORIES
        ]

    def weather_annotation(airport: str | None, event: Any, tolerance: int) -> dict[str, Any]:
        base_result = {"airport": airport, "toleranceMinutes": tolerance}
        if not airport:
            return {**base_result, "available": False, "reason": "unmapped_station"}
        event_utc = pd.to_datetime(event, utc=True, errors="coerce")
        if pd.isna(event_utc):
            return {**base_result, "available": False, "reason": "missing_event_time"}
        base_result["eventUTC"] = event_utc.isoformat().replace("+00:00", "Z")
        if airport not in usable_airports:
            return {**base_result, "available": False, "reason": "unmapped_station"}
        station_weather = usable.loc[usable["airport_code"].eq(airport), ANNOTATION_COLUMNS].sort_values("valid_utc")
        matched = pd.merge_asof(
            pd.DataFrame({"event_utc": [event_utc]}), station_weather,
            left_on="event_utc", right_on="valid_utc", direction="backward",
            tolerance=pd.Timedelta(minutes=tolerance),
        ).iloc[0]
        if pd.isna(matched["valid_utc"]):
            return {**base_result, "available": False, "reason": "no_complete_report_within_tolerance"}
        age = (event_utc - matched["valid_utc"]).total_seconds() / 60
        assert age >= 0, "episode annotation used a future weather report"
        return {
            **base_result,
            "available": True,
            "observedUTC": matched["valid_utc"].isoformat().replace("+00:00", "Z"),
            "ageMinutes": round(float(age), 2),
            "reportType": str(matched["report_type"]),
            "statusKey": "candidate_adverse" if bool(matched["adverse_weather"]) else "non_adverse",
            "adverse": bool(matched["adverse_weather"]),
            "flags": [category for category in CATEGORIES if bool(matched[category])],
            "values": {
                "visibilityKm": matched["visibility_km"],
                "ceilingFt": matched["ceiling_ft"],
                "windSpeedMps": matched["wind_speed_mps"],
                "windGustMps": matched["wind_gust_mps"],
            },
        }

    episode_annotations = []
    for episode in v1b["episodes"]:
        steps = []
        for source in episode["steps"]:
            expected_match = (
                "prior_delayed_flight" if source.get("stepType") == "recovered_en_route"
                else "six_key_exact"
            )
            assert source.get("sourceLinkMatch") == expected_match
            turn = source.get("turnAirport", {}).get("code")
            next_airport = (source.get("nextAirport") or {}).get("code")
            steps.append({
                "stepIndex": source["stepIndex"],
                "weatherAtScheduledDeparture": {
                    str(tolerance): weather_annotation(
                        turn, source.get("nextScheduledDepartureUTC"), tolerance
                    ) for tolerance in TOLERANCES
                },
                "weatherAtActualArrival": {
                    str(tolerance): weather_annotation(
                        next_airport, source.get("nextActualArrivalUTC"), tolerance
                    ) for tolerance in TOLERANCES
                },
            })
        episode_annotations.append({"episodeId": episode["episodeId"], "steps": steps})

    core_total = int(weather_summary["core_airports"])
    core_mapped = int(weather_summary["core_airports_mapped"])
    mechanism_total = len(mechanism)
    mechanism_mapped = int(weather_summary["mechanism_airports_mapped"])
    assert (core_mapped, core_total, mechanism_mapped, mechanism_total) == (96, 97, 55, 55)
    assert len(v1b["episodes"]) == 12

    sources = [
        DATA / "p0_chain_links.parquet", DATA / "v1_p0_airport_roles.parquet",
        DATA / "v2_p0_weather_observations.parquet", DATA / "v2_p0_station_mapping.json",
        DATA / "v2_p0_weather_summary.json", WEB / "v1-a-data.json", WEB / "v1-b-data.json",
    ]
    output = {
        "version": "v2-a-2",
        "defaultToleranceMinutes": 90,
        "tolerances": list(TOLERANCES),
        "scope": {
            "coreMappedAirports": core_mapped,
            "coreTotalAirports": core_total,
            "mechanismMappedAirports": mechanism_mapped,
            "mechanismTotalAirports": mechanism_total,
            "mechanismAirportCodes": mechanism,
            "episodes": len(v1b["episodes"]),
            "pbi": "unavailable",
        },
        "national": comparisons,
        "weatherCategories": category_comparisons,
        "airportComparisons": airport_comparisons,
        "insufficientSampleAirportsByTolerance": insufficient_by_tolerance,
        "episodeWeather": episode_annotations,
        "sources": {
            "sha256": {
                str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path) for path in sources
            },
            "thresholds": {
                "upstreamDelayMinutes": 15,
                "downstreamDelayMinutes": 15,
                "airportExposure": 500,
                "airportStratumMinimum": 50,
                "weatherMaxAgeMinutes": 90,
            },
            "missingReasons": [
                "unmapped_station", "missing_event_time", "no_complete_report_within_tolerance",
            ],
        },
    }
    OUT.write_text(
        json.dumps(clean(output), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(OUT), "sha256": sha256(OUT), "national": comparisons}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
