import pandas as pd

from airports_under_stress.audit import build_rotation_links


def leg(
    row: int,
    origin: str,
    destination: str,
    scheduled_departure: str,
    scheduled_arrival: str,
    actual_departure: str,
    actual_arrival: str,
    dep_delay: float,
    arr_delay: float,
) -> dict[str, object]:
    return {
        "SourceRow": row,
        "Tail_Number": "N123AB",
        "FlightDate": pd.Timestamp("2026-05-01"),
        "Reporting_Airline": "ZZ",
        "Flight_Number_Reporting_Airline": row + 1,
        "Origin": origin,
        "Dest": destination,
        "Cancelled": 0.0,
        "Diverted": 0.0,
        "ScheduledDepartureUTC": pd.Timestamp(scheduled_departure, tz="UTC"),
        "ScheduledArrivalUTC": pd.Timestamp(scheduled_arrival, tz="UTC"),
        "ActualDepartureUTC": pd.Timestamp(actual_departure, tz="UTC"),
        "ActualArrivalUTC": pd.Timestamp(actual_arrival, tz="UTC"),
        "NaiveScheduledDeparture": pd.Timestamp(scheduled_departure).tz_localize(None),
        "DepDelay": dep_delay,
        "ArrDelay": arr_delay,
        "LateAircraftDelay": 0.0,
    }


def test_valid_airport_continuous_rotation_is_linked() -> None:
    frame = pd.DataFrame(
        [
            leg(0, "AAA", "BBB", "2026-05-01 10:00", "2026-05-01 11:00", "2026-05-01 10:10", "2026-05-01 11:10", 10, 10),
            leg(1, "BBB", "CCC", "2026-05-01 12:00", "2026-05-01 13:00", "2026-05-01 12:10", "2026-05-01 13:10", 10, 10),
        ]
    )
    links, metrics = build_rotation_links(frame)
    assert len(links) == 1
    assert metrics["airport_continuity_rate"] == 1.0


def test_negative_actual_turn_candidate_is_excluded() -> None:
    frame = pd.DataFrame(
        [
            leg(0, "AAA", "BBB", "2026-05-01 10:00", "2026-05-01 11:00", "2026-05-01 10:00", "2026-05-01 12:20", 0, 80),
            leg(1, "BBB", "CCC", "2026-05-01 12:00", "2026-05-01 13:00", "2026-05-01 12:10", "2026-05-01 13:10", 10, 10),
        ]
    )
    links, metrics = build_rotation_links(frame)
    assert links.empty
    assert metrics["negative_actual_turn_candidates_excluded"] == 1

