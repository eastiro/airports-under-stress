from __future__ import annotations

import pandas as pd

from airports_under_stress.weather import (
    backward_join_by_station,
    parse_iem_csv,
    standardize_observations,
)


def test_standardize_units_and_utc() -> None:
    raw = b"station,valid,lon,lat,elevation,tmpf,dwpf,relh,drct,sknt,vsby,gust,skyc1,skyl1,wxcodes,metar\nLGA,2026-05-01 12:00,-73.8,40.7,10,68,50,50,180,20,2.5,31,BKN,800,+TSRA,METAR LGA\n"
    out = standardize_observations(parse_iem_csv(raw))
    row = out.iloc[0]
    assert str(row.valid_utc.tz) == "UTC"
    assert abs(row.temperature_c - 20) < 1e-9
    assert abs(row.wind_speed_mps - 10.28888) < 1e-4
    assert abs(row.visibility_km - 4.02336) < 1e-4
    assert bool(row.low_visibility)
    assert bool(row.low_ceiling)
    assert bool(row.strong_wind)
    assert bool(row.thunderstorm)
    assert bool(row.adverse_weather)
    assert row.elevation_m == 10


def test_duplicate_reports_are_deterministic() -> None:
    raw = b"station,valid,lon,lat,elevation,tmpf,dwpf,relh,drct,sknt,vsby,gust,skyc1,skyl1,wxcodes,metar\nLGA,2026-05-01 12:00,-73.8,40.7,10,68,50,50,180,10,10,,CLR,, ,AUTO LGA\nLGA,2026-05-01 12:00,-73.8,40.7,10,68,50,50,180,10,10,,CLR,, ,METAR LGA\n"
    out = standardize_observations(parse_iem_csv(raw))
    assert len(out) == 1
    assert bool(out.iloc[0].is_duplicate_report)
    assert out.iloc[0].metar == "METAR LGA"


def test_five_minute_feed_is_not_complete_metar() -> None:
    raw = b"station,valid,lon,lat,elevation,tmpf,dwpf,relh,drct,sknt,vsby,gust,skyc1,skyl1,wxcodes,metar\nLGA,2026-05-01 12:00,-73.8,40.7,9,M,M,M,180,10,10,M,FEW,500,M,KLGA 011200Z AUTO 18010KT 10SM FEW005 MADISHF\n"
    row = standardize_observations(parse_iem_csv(raw)).iloc[0]
    assert bool(row.is_five_minute_partial)
    assert not bool(row.is_complete_metar)
    assert not bool(row.usable_for_exposure)


def test_ceiling_ignores_few_and_scattered_layers() -> None:
    raw = b"station,valid,lon,lat,elevation,tmpf,dwpf,relh,drct,sknt,vsby,gust,skyc1,skyc2,skyl1,skyl2,wxcodes,metar\nLGA,2026-05-01 12:51,-73.8,40.7,9,68,50,50,180,10,10,M,FEW,BKN,500,2500,M,KLGA 011251Z 18010KT 10SM FEW005 BKN025\n"
    row = standardize_observations(parse_iem_csv(raw)).iloc[0]
    assert row.ceiling_ft == 2500
    assert not bool(row.low_ceiling)


def test_backward_join_never_uses_future_weather() -> None:
    observations = pd.DataFrame(
        {
            "airport_code": ["LGA", "LGA"],
            "valid_utc": pd.to_datetime(
                ["2026-05-01T11:00:00Z", "2026-05-01T12:05:00Z"], utc=True
            ),
            "adverse_weather": [False, True],
            "low_visibility": [False, True],
            "low_ceiling": [False, False],
            "strong_wind": [False, False],
            "precipitation": [False, False],
            "thunderstorm": [False, False],
            "fog": [False, False],
            "report_type": ["METAR", "METAR"],
        }
    )
    events = pd.DataFrame(
        {"airport": ["LGA"], "event": pd.to_datetime(["2026-05-01T12:00:00Z"], utc=True)}
    )
    joined = backward_join_by_station(
        events,
        observations,
        station_col="airport",
        time_col="event",
        tolerance_minutes=90,
    )
    assert joined.iloc[0].valid_utc == pd.Timestamp("2026-05-01T11:00:00Z")
    assert joined.iloc[0].weather_age_minutes == 60
    assert not bool(joined.iloc[0].adverse_weather)
