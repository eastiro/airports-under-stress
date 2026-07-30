from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import airportsdata
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from airports_under_stress.weather import (
    backward_join_by_station,
    haversine_km,
    parse_iem_csv,
    sha256_file,
    standardize_observations,
)


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "weather"
PROCESSED = ROOT / "data" / "processed"


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8"
    )


def _core_airports(flights: pd.DataFrame, links: pd.DataFrame) -> set[str]:
    flight_counts = flights.groupby("Origin", sort=True).size()
    link_counts = links.groupby("Origin", sort=True).size()
    return set(flight_counts[flight_counts >= 1_000].index) & set(
        link_counts[link_counts >= 500].index
    )


def _build_station_mapping(
    airport_codes: set[str], observations: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, str]]:
    reference = airportsdata.load("IATA")
    observed = set(observations["station"].dropna().astype(str))
    station_locations = observations.groupby("station", sort=True)[["lat", "lon"]].median()
    records: list[dict[str, Any]] = []
    reverse: dict[str, str] = {}
    for airport in sorted(airport_codes):
        info = reference.get(airport, {})
        icao = str(info.get("icao") or "").upper()
        if airport in observed:
            station, method = airport, "same_iata_code"
        elif icao and icao in observed:
            station, method = icao, "official_icao_code"
        else:
            station, method = None, "unmapped"
        distance = None
        station_lat = station_lon = None
        if station is not None:
            reverse[station] = airport
            station_lat = float(station_locations.loc[station, "lat"])
            station_lon = float(station_locations.loc[station, "lon"])
            airport_lat = info.get("lat")
            airport_lon = info.get("lon")
            if airport_lat is not None and airport_lon is not None:
                distance = haversine_km(
                    float(airport_lat), float(airport_lon), station_lat, station_lon
                )
        records.append(
            {
                "airport": airport,
                "airport_name": info.get("name"),
                "icao": icao or None,
                "station": station,
                "mapping_method": method,
                "station_latitude": station_lat,
                "station_longitude": station_lon,
                "distance_km": distance,
            }
        )
    return pd.DataFrame(records), reverse


def _coverage(joined: pd.DataFrame, minutes: int) -> float:
    if joined.empty:
        return 0.0
    return float(joined["weather_age_minutes"].le(minutes).fillna(False).mean())


def _event_coverage(
    events: pd.DataFrame, observations: pd.DataFrame, time_column: str
) -> dict[str, Any]:
    work = events[["turnAirport", time_column]].rename(
        columns={"turnAirport": "airport_code", time_column: "event_utc"}
    )
    joined = backward_join_by_station(
        work,
        observations,
        station_col="airport_code",
        time_col="event_utc",
        tolerance_minutes=90,
    )
    return {
        "events": int(len(work)),
        "coverage_30min": _coverage(joined, 30),
        "coverage_60min": _coverage(joined, 60),
        "coverage_90min": _coverage(joined, 90),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw",
        nargs="*",
        default=[],
        help="one or more raw IEM CSV files; defaults to every archived CSV",
    )
    args = parser.parse_args()
    raw_paths = [Path(value) for value in args.raw] or sorted(RAW.glob("*.csv"))
    if not raw_paths:
        raise FileNotFoundError("No IEM CSV files found")

    raw_frames = [parse_iem_csv(path.read_bytes()) for path in raw_paths]
    observations = standardize_observations(pd.concat(raw_frames, ignore_index=True))
    flights = pd.read_parquet(PROCESSED / "p0_flights.parquet")
    links = pd.read_parquet(PROCESSED / "p0_chain_links.parquet")
    roles = pd.read_parquet(PROCESSED / "v1_p0_airport_roles.parquet")
    steps = pd.read_parquet(PROCESSED / "v1_p0_steps.parquet")

    all_airports = set(flights["Origin"]) | set(flights["Dest"])
    core = _core_airports(flights, links)
    mechanism = set(roles.loc[roles["nExposed"] >= 500, "code"])
    mapping, station_to_airport = _build_station_mapping(all_airports, observations)
    observations["airport_code"] = observations["station"].map(station_to_airport).astype("string")
    usable = observations[
        observations["usable_for_exposure"] & observations["airport_code"].notna()
    ].copy()

    flight_events = flights[
        ["SourceRow", "Origin", "ScheduledDepartureUTC", "WeatherDelay"]
    ].rename(columns={"Origin": "airport_code", "ScheduledDepartureUTC": "event_utc"})
    joined_flights = backward_join_by_station(
        flight_events,
        usable,
        station_col="airport_code",
        time_col="event_utc",
        tolerance_minutes=90,
    )

    mapping_records = mapping.set_index("airport").to_dict(orient="index")
    airport_rows: list[dict[str, Any]] = []
    for airport in sorted(core):
        airport_observations = observations[observations["airport_code"] == airport]
        airport_usable = usable[usable["airport_code"] == airport]
        airport_flights = flight_events[flight_events["airport_code"] == airport]
        airport_joined = joined_flights[joined_flights["airport_code"] == airport]
        if airport_flights.empty:
            expected_hours = 0
            start_hour = end_hour = None
        else:
            start_hour = airport_flights["event_utc"].min().floor("h")
            end_hour = airport_flights["event_utc"].max().ceil("h")
            expected_hours = int((end_hour - start_hour).total_seconds() // 3600) + 1
        in_window = airport_observations
        if start_hour is not None:
            in_window = in_window[
                in_window["valid_utc"].between(start_hour, end_hour, inclusive="both")
            ]
        complete = in_window[in_window["is_complete_metar"]]
        usable_window = in_window[in_window["usable_for_exposure"]]
        complete_gaps = complete["valid_utc"].sort_values().diff().dt.total_seconds().div(60)
        mapping_row = mapping_records[airport]
        record: dict[str, Any] = {
            "airport": airport,
            "tier": "mechanism" if airport in mechanism else "core",
            **{key: _json_value(value) for key, value in mapping_row.items()},
            "observations": int(len(airport_observations)),
            "five_minute_partial": int(airport_observations["is_five_minute_partial"].sum()),
            "complete_metar": int(airport_observations["is_complete_metar"].sum()),
            "usable_reports": int(len(airport_usable)),
            "first_utc": (
                airport_observations["valid_utc"].min().isoformat()
                if not airport_observations.empty
                else None
            ),
            "last_utc": (
                airport_observations["valid_utc"].max().isoformat()
                if not airport_observations.empty
                else None
            ),
            "duplicate_reports": int(airport_observations["is_duplicate_report"].sum()),
            "max_complete_gap_minutes": (
                float(complete_gaps.max()) if complete_gaps.notna().any() else None
            ),
            "expected_flight_window_hours": expected_hours,
            "hourly_coverage_any": (
                float(in_window["valid_utc"].dt.floor("h").nunique() / expected_hours)
                if expected_hours
                else 0.0
            ),
            "hourly_coverage_complete_metar": (
                float(complete["valid_utc"].dt.floor("h").nunique() / expected_hours)
                if expected_hours
                else 0.0
            ),
            "hourly_coverage_usable": (
                float(usable_window["valid_utc"].dt.floor("h").nunique() / expected_hours)
                if expected_hours
                else 0.0
            ),
            "scheduled_departures": int(len(airport_flights)),
            "flight_coverage_30min": _coverage(airport_joined, 30),
            "flight_coverage_60min": _coverage(airport_joined, 60),
            "flight_coverage_90min": _coverage(airport_joined, 90),
            "field_nonnull_complete_metar": {
                column: float(complete[column].notna().mean()) if not complete.empty else 0.0
                for column in [
                    "temperature_c",
                    "dew_point_c",
                    "relh",
                    "wind_speed_mps",
                    "wind_gust_mps",
                    "visibility_km",
                    "ceiling_ft",
                    "present_weather",
                ]
            },
        }
        airport_rows.append(record)
    airport_audit = pd.DataFrame(airport_rows).sort_values("airport")

    def tier_coverage(codes: set[str], minutes: int) -> float:
        return _coverage(joined_flights[joined_flights["airport_code"].isin(codes)], minutes)

    join_coverage = {
        str(minutes): {
            "all": _coverage(joined_flights, minutes),
            "core": tier_coverage(core, minutes),
            "mechanism": tier_coverage(mechanism, minutes),
        }
        for minutes in [30, 60, 90]
    }

    matched90 = joined_flights[joined_flights["weather_age_minutes"].le(90)].copy()
    matched90["weather_delay_positive"] = matched90["WeatherDelay"].fillna(0).gt(0)
    weak_groups: dict[str, Any] = {}
    for label, group in matched90.groupby("weather_delay_positive", sort=True):
        key = "weather_delay_positive" if label else "weather_delay_not_positive"
        weak_groups[key] = {
            "flights": int(len(group)),
            "adverse_weather_rate": float(group["adverse_weather"].eq(True).mean()),
            "low_visibility_rate": float(group["low_visibility"].eq(True).mean()),
            "low_ceiling_rate": float(group["low_ceiling"].eq(True).mean()),
            "strong_wind_rate": float(group["strong_wind"].eq(True).mean()),
        }
    weak_groups["coverage"] = {
        "weather_delay_positive_total": int(flights["WeatherDelay"].fillna(0).gt(0).sum()),
        "weather_delay_positive_matched_90min": int(
            matched90["weather_delay_positive"].sum()
        ),
        "weather_delay_positive_match_rate": float(
            matched90["weather_delay_positive"].sum()
            / flights["WeatherDelay"].fillna(0).gt(0).sum()
        ),
    }

    link_lookup = links[
        [
            "Tail_Number",
            "PrevDest",
            "PrevActualArrivalUTC",
            "ActualDepartureUTC",
            "ScheduledDepartureUTC",
        ]
    ].copy()
    for column in ["PrevActualArrivalUTC", "ActualDepartureUTC", "ScheduledDepartureUTC"]:
        link_lookup[column] = pd.to_datetime(link_lookup[column], utc=True, errors="coerce")
    episode_steps = steps.copy()
    episode_steps["prevArrUTC"] = pd.to_datetime(
        episode_steps["prevArrUTC"], utc=True, errors="coerce"
    )
    episode_steps["nextDepUTC"] = pd.to_datetime(
        episode_steps["nextDepUTC"], utc=True, errors="coerce"
    )
    turn_steps = episode_steps[episode_steps["stepType"] != "recovered_en_route"].copy()
    linked_steps = turn_steps.merge(
        link_lookup,
        left_on=["tailNumber", "turnAirport", "prevArrUTC", "nextDepUTC"],
        right_on=["Tail_Number", "PrevDest", "PrevActualArrivalUTC", "ActualDepartureUTC"],
        how="left",
        validate="many_to_one",
    )
    def coverage_by_tier(frame: pd.DataFrame, time_column: str) -> dict[str, Any]:
        return {
            "all_turn_steps": _event_coverage(frame, usable, time_column),
            "core_turn_airports": _event_coverage(
                frame[frame["turnAirport"].isin(core)], usable, time_column
            ),
            "mechanism_turn_airports": _event_coverage(
                frame[frame["turnAirport"].isin(mechanism)], usable, time_column
            ),
        }

    en_route_events = episode_steps[episode_steps["stepType"] == "recovered_en_route"]
    en_route_for_join = en_route_events[["turnAirport", "nextDepUTC"]]
    episode_coverage = {
        "all_steps": int(len(episode_steps)),
        "turn_steps": int(len(turn_steps)),
        "recovered_en_route_steps": int(len(en_route_events)),
        "scheduled_departure_link_match_rate": float(
            linked_steps["ScheduledDepartureUTC"].notna().mean()
        ),
        "upstream_actual_arrival": coverage_by_tier(
            linked_steps, "prevArrUTC"
        ),
        "next_scheduled_departure": coverage_by_tier(
            linked_steps[linked_steps["ScheduledDepartureUTC"].notna()],
            "ScheduledDepartureUTC",
        ),
        "next_actual_departure": coverage_by_tier(linked_steps, "nextDepUTC"),
        "recovered_en_route_actual_arrival": _event_coverage(
            en_route_for_join, usable, "nextDepUTC"
        ),
    }

    complete = observations[
        observations["is_complete_metar"] & observations["airport_code"].isin(core)
    ]
    adverse = complete[complete["adverse_weather"]].copy()
    airport_concentration = adverse.groupby("airport_code").size().sort_values(ascending=False)
    day_concentration = adverse.groupby(adverse["valid_utc"].dt.date).size().sort_values(
        ascending=False
    )
    concentration = {
        "adverse_complete_reports": int(len(adverse)),
        "top_airport": str(airport_concentration.index[0]) if len(airport_concentration) else None,
        "top_airport_share": (
            float(airport_concentration.iloc[0] / len(adverse)) if len(adverse) else 0.0
        ),
        "top_day": str(day_concentration.index[0]) if len(day_concentration) else None,
        "top_day_share": (
            float(day_concentration.iloc[0] / len(adverse)) if len(adverse) else 0.0
        ),
    }

    output_paths = {
        "observations": PROCESSED / "v2_p0_weather_observations.parquet",
        "station_mapping": PROCESSED / "v2_p0_station_mapping.json",
        "airport_audit": PROCESSED / "v2_p0_weather_airport_audit.json",
        "episode_coverage": PROCESSED / "v2_p0_episode_weather_coverage.json",
        "weak_consistency": PROCESSED / "v2_p0_weather_delay_consistency.json",
        "summary": PROCESSED / "v2_p0_weather_summary.json",
    }
    observations.sort_values(["station", "valid_utc"], kind="mergesort").to_parquet(
        output_paths["observations"], index=False
    )
    _write_json(
        output_paths["station_mapping"],
        mapping.sort_values("airport").where(pd.notna(mapping), None).to_dict(orient="records"),
    )
    _write_json(output_paths["airport_audit"], airport_rows)
    _write_json(output_paths["episode_coverage"], episode_coverage)
    _write_json(output_paths["weak_consistency"], weak_groups)

    core_mapping = mapping[mapping["airport"].isin(core)]
    mechanism_mapping = mapping[mapping["airport"].isin(mechanism)]
    mechanism_audit = airport_audit[airport_audit["airport"].isin(mechanism)]
    summary = {
        "source": "Iowa State University Environmental Mesonet ASOS/METAR archive",
        "raw_files": [str(path) for path in raw_paths],
        "raw_sha256": {path.name: sha256_file(path) for path in raw_paths},
        "raw_rows_before_deduplication": int(sum(len(frame) for frame in raw_frames)),
        "observations_after_deduplication": int(len(observations)),
        "five_minute_partial_reports": int(observations["is_five_minute_partial"].sum()),
        "complete_metar_reports": int(observations["is_complete_metar"].sum()),
        "usable_exposure_reports": int(observations["usable_for_exposure"].sum()),
        "core_airports": len(core),
        "mechanism_airports": len(mechanism),
        "core_airports_mapped": int(core_mapping["station"].notna().sum()),
        "mechanism_airports_mapped": int(mechanism_mapping["station"].notna().sum()),
        "core_unmapped": sorted(core - set(core_mapping.loc[core_mapping["station"].notna(), "airport"])),
        "mechanism_unmapped": sorted(
            mechanism
            - set(mechanism_mapping.loc[mechanism_mapping["station"].notna(), "airport"])
        ),
        "join_coverage": join_coverage,
        "mechanism_airports_hourly_any_ge95": int(
            mechanism_audit["hourly_coverage_any"].ge(0.95).sum()
        ),
        "mechanism_airports_hourly_complete_ge95": int(
            mechanism_audit["hourly_coverage_complete_metar"].ge(0.95).sum()
        ),
        "mechanism_airports_flight_90min_ge95": int(
            mechanism_audit["flight_coverage_90min"].ge(0.95).sum()
        ),
        "candidate_counts_complete_metar": {
            column: int(complete[column].sum())
            for column in [
                "low_visibility",
                "low_ceiling",
                "strong_wind",
                "precipitation",
                "thunderstorm",
                "fog",
                "adverse_weather",
            ]
        },
        "field_nonnull_complete_metar": {
            column: float(complete[column].notna().mean())
            for column in [
                "temperature_c",
                "dew_point_c",
                "relh",
                "wind_speed_mps",
                "wind_gust_mps",
                "visibility_km",
                "ceiling_ft",
                "present_weather",
            ]
        },
        "semantic_field_availability_complete_metar": {
            "sky_condition": float(
                complete[[f"skyc{i}" for i in range(1, 5)]].notna().any(axis=1).mean()
            ),
            "explicit_present_weather_code": float(complete["present_weather"].notna().mean()),
            "ceiling_reported_when_bkn_ovc_vv": float(complete["ceiling_ft"].notna().mean()),
            "gust_reported": float(complete["gust"].notna().mean()),
        },
        "concentration": concentration,
        "episode_coverage": episode_coverage,
        "weak_consistency": weak_groups,
    }
    _write_json(output_paths["summary"], summary)

    old_manifest_path = PROCESSED / "v2_p0_manifest.json"
    old_manifest = (
        json.loads(old_manifest_path.read_text(encoding="utf-8"))
        if old_manifest_path.exists()
        else {}
    )
    hashes = {path.name: sha256_file(path) for path in output_paths.values()}
    manifest = {
        "scientific_outputs": hashes,
        "scientificOutputsMatchPreviousRun": old_manifest.get("scientific_outputs") == hashes,
    }
    _write_json(old_manifest_path, manifest)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
