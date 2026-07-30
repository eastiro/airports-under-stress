from __future__ import annotations

import hashlib
import io
import math
from pathlib import Path
from typing import Iterable

import pandas as pd


IEM_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
REQUIRED_RAW_COLUMNS = [
    "station",
    "valid",
    "lon",
    "lat",
    "elevation",
    "tmpf",
    "dwpf",
    "relh",
    "drct",
    "sknt",
    "vsby",
    "gust",
    "skyc1",
    "skyc2",
    "skyc3",
    "skyc4",
    "skyl1",
    "skyl2",
    "skyl3",
    "skyl4",
    "wxcodes",
    "metar",
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_iem_csv(data: bytes) -> pd.DataFrame:
    text = data.decode("utf-8", errors="replace")
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    if not lines:
        return pd.DataFrame(columns=REQUIRED_RAW_COLUMNS)
    frame = pd.read_csv(io.StringIO("\n".join(lines)), na_values=["M", ""])
    for column in REQUIRED_RAW_COLUMNS:
        if column not in frame:
            frame[column] = pd.NA
    return frame


def standardize_observations(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize IEM ASOS rows without treating five-minute feeds as METARs."""
    out = frame.copy()
    out["station"] = out["station"].astype("string").str.strip().str.upper()
    out["valid_utc"] = pd.to_datetime(out["valid"], utc=True, errors="coerce")
    numeric = [
        "lon",
        "lat",
        "elevation",
        "tmpf",
        "dwpf",
        "relh",
        "drct",
        "sknt",
        "vsby",
        "gust",
        *[f"skyl{i}" for i in range(1, 5)],
    ]
    for column in numeric:
        out[column] = pd.to_numeric(out[column], errors="coerce")

    out["temperature_c"] = (out["tmpf"] - 32.0) * 5.0 / 9.0
    out["dew_point_c"] = (out["dwpf"] - 32.0) * 5.0 / 9.0
    out["wind_speed_mps"] = out["sknt"] * 0.514444
    out["wind_gust_mps"] = out["gust"] * 0.514444
    out["visibility_km"] = out["vsby"] * 1.609344
    # IEM's `elevation` field is already metres.
    out["elevation_m"] = out["elevation"]

    ceiling_layers: list[pd.Series] = []
    for index in range(1, 5):
        cover = out[f"skyc{index}"].astype("string").str.upper()
        base = out[f"skyl{index}"]
        ceiling_layers.append(base.where(cover.isin(["BKN", "OVC", "VV"])))
    out["ceiling_ft"] = pd.concat(ceiling_layers, axis=1).min(axis=1, skipna=True)

    metar = out["metar"].astype("string")
    out["is_five_minute_partial"] = metar.str.contains("MADISHF", case=False, na=False)
    out["is_complete_metar"] = metar.notna() & ~out["is_five_minute_partial"]
    out["report_type"] = "FIVE_MINUTE"
    # IEM does not reliably expose a separate METAR/SPECI flag in this export.
    out.loc[out["is_complete_metar"], "report_type"] = "METAR_OR_SPECI"
    out.loc[metar.str.contains(r"\bSPECI\b", case=False, na=False), "report_type"] = "SPECI"
    out["present_weather"] = out["wxcodes"].astype("string")

    out = out[out["valid_utc"].notna() & out["station"].notna()].copy()
    out = out.sort_values(
        ["station", "valid_utc", "is_complete_metar", "metar"], kind="mergesort"
    )
    out["is_duplicate_report"] = out.duplicated(["station", "valid_utc"], keep=False)
    out = out.drop_duplicates(["station", "valid_utc"], keep="last").reset_index(drop=True)

    out["low_visibility"] = out["vsby"].lt(3).fillna(False)
    out["low_ceiling"] = out["ceiling_ft"].lt(1000).fillna(False)
    out["strong_wind"] = (out["sknt"].ge(20) | out["gust"].ge(30)).fillna(False)
    out["precipitation"] = out["present_weather"].str.contains(
        r"[-+]?(?:RA|SN|DZ|SG|PL|GR|GS)", case=False, regex=True, na=False
    )
    out["thunderstorm"] = out["present_weather"].str.contains(
        "TS", case=False, regex=False, na=False
    )
    out["fog"] = out["present_weather"].str.contains(
        r"FG|BR", case=False, regex=True, na=False
    )
    out["adverse_weather"] = out[
        [
            "low_visibility",
            "low_ceiling",
            "strong_wind",
            "precipitation",
            "thunderstorm",
            "fog",
        ]
    ].any(axis=1)
    has_sky = out[[f"skyc{i}" for i in range(1, 5)]].notna().any(axis=1)
    out["usable_for_exposure"] = (
        out["is_complete_metar"]
        & out["vsby"].notna()
        & out["sknt"].notna()
        & has_sky
    )
    return out.sort_values(["station", "valid_utc"], kind="mergesort").reset_index(drop=True)


def backward_join_by_station(
    events: pd.DataFrame,
    observations: pd.DataFrame,
    *,
    station_col: str,
    time_col: str,
    tolerance_minutes: int = 90,
) -> pd.DataFrame:
    """Attach only observations at or before each event, never future weather."""
    left = events.copy()
    left[station_col] = left[station_col].astype("string")
    left[time_col] = pd.to_datetime(left[time_col], utc=True, errors="coerce")
    left = left[left[time_col].notna()].copy()
    right = observations.copy()
    right["airport_code"] = right["airport_code"].astype("string")
    right["valid_utc"] = pd.to_datetime(right["valid_utc"], utc=True, errors="coerce")
    weather_columns = [
        "valid_utc",
        "adverse_weather",
        "low_visibility",
        "low_ceiling",
        "strong_wind",
        "precipitation",
        "thunderstorm",
        "fog",
        "report_type",
    ]
    parts: list[pd.DataFrame] = []
    for station, station_events in left.groupby(station_col, sort=True):
        station_weather = right[right["airport_code"] == station][weather_columns]
        if station_weather.empty:
            missing = station_events.copy()
            missing["valid_utc"] = pd.Series(
                pd.NaT, index=missing.index, dtype="datetime64[ns, UTC]"
            )
            for column in weather_columns:
                if column == "valid_utc":
                    continue
                if column == "report_type":
                    missing[column] = pd.Series(pd.NA, index=missing.index, dtype="string")
                else:
                    missing[column] = False
            parts.append(missing)
            continue
        parts.append(
            pd.merge_asof(
                station_events.sort_values(time_col),
                station_weather.sort_values("valid_utc"),
                left_on=time_col,
                right_on="valid_utc",
                direction="backward",
                tolerance=pd.Timedelta(minutes=tolerance_minutes),
            )
        )
    if not parts:
        return left.assign(valid_utc=pd.NaT, weather_age_minutes=pd.NA)
    joined = pd.concat(parts, ignore_index=True)
    joined[time_col] = pd.to_datetime(joined[time_col], utc=True, errors="coerce")
    joined["valid_utc"] = pd.to_datetime(joined["valid_utc"], utc=True, errors="coerce")
    joined["weather_age_minutes"] = (
        joined[time_col] - joined["valid_utc"]
    ).dt.total_seconds().div(60)
    return joined


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    value = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(value))


def station_query(
    stations: Iterable[str], start: str = "2026-05-01", end: str = "2026-06-01"
) -> dict[str, str]:
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    return {
        "station": ",".join(sorted({str(value).upper() for value in stations})),
        "data": "all",
        "year1": str(start_ts.year),
        "month1": str(start_ts.month),
        "day1": str(start_ts.day),
        "year2": str(end_ts.year),
        "month2": str(end_ts.month),
        "day2": str(end_ts.day),
        "tz": "UTC",
        "format": "comma",
        "latlon": "yes",
        "elev": "yes",
        "missing": "M",
    }
