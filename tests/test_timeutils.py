from datetime import date, datetime, timezone

import pytest

from airports_under_stress.timeutils import (
    actual_departure_utc,
    parse_hhmm,
    scheduled_departure_utc,
)


def test_parse_hhmm_regular_value() -> None:
    assert parse_hhmm(735) == (7 * 60 + 35, 0)


def test_parse_hhmm_midnight_rollover() -> None:
    assert parse_hhmm(2400) == (0, 1)


@pytest.mark.parametrize("value", [2360, 2500, -1])
def test_parse_hhmm_rejects_invalid_values(value: int) -> None:
    with pytest.raises(ValueError):
        parse_hhmm(value)


def test_scheduled_departure_uses_airport_timezone() -> None:
    result = scheduled_departure_utc(date(2026, 5, 1), 800, "America/New_York")
    assert result == datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)


def test_actual_departure_uses_reported_delay_for_day_rollover() -> None:
    scheduled = datetime(2026, 5, 2, 3, 50, tzinfo=timezone.utc)
    result = actual_departure_utc(scheduled, 25)
    assert result == datetime(2026, 5, 2, 4, 15, tzinfo=timezone.utc)

