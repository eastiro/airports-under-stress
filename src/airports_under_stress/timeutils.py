from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd


def parse_hhmm(value: object) -> tuple[int, int]:
    """Return (minutes after midnight, day offset) for a BTS HHMM value."""
    if value is None or pd.isna(value):
        raise ValueError("HHMM value is missing")

    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if not text:
        raise ValueError("HHMM value is empty")

    number = int(text)
    if number == 2400:
        return 0, 1

    hours, minutes = divmod(number, 100)
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ValueError(f"Invalid HHMM value: {value!r}")
    return hours * 60 + minutes, 0


@lru_cache(maxsize=None)
def local_midnight_utc(day: date, timezone_name: str) -> datetime:
    local = datetime.combine(day, time.min, tzinfo=ZoneInfo(timezone_name))
    return local.astimezone(timezone.utc)


def scheduled_departure_utc(
    flight_date: date,
    crs_dep_time: object,
    timezone_name: str,
) -> datetime:
    minutes, day_offset = parse_hhmm(crs_dep_time)
    local_day = flight_date + timedelta(days=day_offset)
    return local_midnight_utc(local_day, timezone_name) + timedelta(minutes=minutes)


def actual_departure_utc(
    scheduled_departure: datetime,
    departure_delay_minutes: object,
) -> datetime:
    if departure_delay_minutes is None or pd.isna(departure_delay_minutes):
        raise ValueError("Departure delay is missing")
    return scheduled_departure + timedelta(minutes=float(departure_delay_minutes))

