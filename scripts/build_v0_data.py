from __future__ import annotations

import json
from pathlib import Path

import airportsdata
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "web" / "app" / "v0-data.json"

AIRLINE_NAMES = {
    "9E": "Endeavor Air",
    "AA": "American Airlines",
    "AS": "Alaska Airlines",
    "B6": "JetBlue Airways",
    "DL": "Delta Air Lines",
    "F9": "Frontier Airlines",
    "G4": "Allegiant Air",
    "HA": "Hawaiian Airlines",
    "MQ": "Envoy Air",
    "NK": "Spirit Airlines",
    "OH": "PSA Airlines",
    "OO": "SkyWest Airlines",
    "UA": "United Airlines",
    "WN": "Southwest Airlines",
    "YX": "Republic Airways",
}


def ratio(mask: pd.Series, denominator: int | None = None) -> float:
    total = len(mask) if denominator is None else denominator
    return 0.0 if total == 0 else float(mask.sum() / total)


def round_or_zero(value: float, digits: int = 4) -> float:
    return round(0.0 if pd.isna(value) else float(value), digits)


def build_daily(flights: pd.DataFrame, links: pd.DataFrame) -> list[dict[str, object]]:
    link_days = links.groupby(links["FlightDate"].dt.date)
    output: list[dict[str, object]] = []
    for day, group in flights.groupby(flights["FlightDate"].dt.date):
        operated = group[group["Cancelled"] == 0]
        day_links = link_days.get_group(day) if day in link_days.groups else links.iloc[0:0]
        upstream = day_links[day_links["UpstreamArrDelayed15"]]
        output.append(
            {
                "date": day.isoformat(),
                "day": day.day,
                "flights": int(len(group)),
                "delayRate": round_or_zero(ratio(operated["DepDelay"] >= 15)),
                "cancelRate": round_or_zero(ratio(group["Cancelled"] == 1)),
                "avgDelay": round_or_zero(operated["DepDelay"].mean(), 1),
                "propagationRate": round_or_zero(
                    ratio(upstream["DownstreamDepDelayed15"])
                ),
            }
        )
    return output


def build_airports(flights: pd.DataFrame, links: pd.DataFrame) -> list[dict[str, object]]:
    airport_reference = airportsdata.load("IATA")
    link_groups = links.groupby("Origin")
    records: list[dict[str, object]] = []

    for code, group in flights.groupby("Origin"):
        operated = group[group["Cancelled"] == 0]
        airport_links = (
            link_groups.get_group(code) if code in link_groups.groups else links.iloc[0:0]
        )
        upstream = airport_links[airport_links["UpstreamArrDelayed15"]]
        reference = airport_reference.get(str(code), {})
        records.append(
            {
                "code": str(code),
                "city": reference.get("city") or str(code),
                "region": reference.get("subd") or "United States",
                "name": reference.get("name") or str(code),
                "flights": int(len(group)),
                "delayRate": round_or_zero(ratio(operated["DepDelay"] >= 15)),
                "cancelRate": round_or_zero(ratio(group["Cancelled"] == 1)),
                "avgDelay": round_or_zero(operated["DepDelay"].mean(), 1),
                "p90Delay": round_or_zero(operated["DepDelay"].quantile(0.9), 1),
                "propagationRate": round_or_zero(
                    ratio(upstream["DownstreamDepDelayed15"])
                ),
                "recoveryRate": round_or_zero(
                    ratio(~upstream["DownstreamDepDelayed15"])
                ),
                "chainLinks": int(len(airport_links)),
            }
        )

    frame = pd.DataFrame(records)
    eligible = frame[(frame["flights"] >= 1_000) & (frame["chainLinks"] >= 500)].copy()
    eligible["delayRank"] = eligible["delayRate"].rank(pct=True)
    eligible["cancelRank"] = eligible["cancelRate"].rank(pct=True)
    eligible["propagationRank"] = eligible["propagationRate"].rank(pct=True)
    eligible["pressureScore"] = (
        100
        * (
            0.45 * eligible["delayRank"]
            + 0.20 * eligible["cancelRank"]
            + 0.35 * eligible["propagationRank"]
        )
    ).round(1)

    chosen_codes = set(eligible.nlargest(30, "pressureScore")["code"]) | set(
        eligible.nlargest(30, "flights")["code"]
    )
    chosen = eligible[eligible["code"].isin(chosen_codes)].copy()
    chosen = chosen.sort_values("pressureScore", ascending=False)
    columns = list(records[0].keys()) + ["pressureScore"]
    return chosen[columns].to_dict(orient="records")


def build_airlines(flights: pd.DataFrame, links: pd.DataFrame) -> list[dict[str, object]]:
    link_groups = links.groupby("Reporting_Airline")
    records: list[dict[str, object]] = []
    for code, group in flights.groupby("Reporting_Airline"):
        operated = group[group["Cancelled"] == 0]
        airline_links = (
            link_groups.get_group(code) if code in link_groups.groups else links.iloc[0:0]
        )
        upstream = airline_links[airline_links["UpstreamArrDelayed15"]]
        records.append(
            {
                "code": str(code),
                "name": AIRLINE_NAMES.get(str(code), str(code)),
                "flights": int(len(group)),
                "delayRate": round_or_zero(ratio(operated["DepDelay"] >= 15)),
                "cancelRate": round_or_zero(ratio(group["Cancelled"] == 1)),
                "avgDelay": round_or_zero(operated["DepDelay"].mean(), 1),
                "propagationRate": round_or_zero(
                    ratio(upstream["DownstreamDepDelayed15"])
                ),
                "recoveryRate": round_or_zero(
                    ratio(~upstream["DownstreamDepDelayed15"])
                ),
                "chainLinks": int(len(airline_links)),
            }
        )
    return sorted(records, key=lambda row: row["flights"], reverse=True)


def split_sequences(links: pd.DataFrame) -> list[pd.DataFrame]:
    sequences: list[pd.DataFrame] = []
    for _, tail_group in links.groupby("Tail_Number"):
        ordered = tail_group.sort_values("ScheduledDepartureUTC")
        current_indices: list[int] = []
        previous_current_departure = None
        for row in ordered.itertuples():
            is_continuation = (
                previous_current_departure is not None
                and row.PrevScheduledDepartureUTC == previous_current_departure
            )
            if not is_continuation and current_indices:
                if len(current_indices) >= 3:
                    sequences.append(ordered.loc[current_indices].copy())
                current_indices = []
            current_indices.append(row.Index)
            previous_current_departure = row.ScheduledDepartureUTC
        if len(current_indices) >= 3:
            sequences.append(ordered.loc[current_indices].copy())
    return sequences


def sequence_profile(sequence: pd.DataFrame) -> dict[str, object]:
    return {
        "edges": len(sequence),
        "propagated": int(sequence["PropagationSignal"].sum()),
        "recovered": int(sequence["RecoverySignal"].sum()),
        "tightest": float(sequence["ScheduledTurnMinutes"].min()),
        "maxDelay": float(sequence[["PrevArrDelay", "DepDelay"]].max().max()),
    }


def choose_story_sequences(sequences: list[pd.DataFrame]) -> list[tuple[str, pd.DataFrame]]:
    candidates: dict[str, list[tuple[tuple[float, ...], pd.DataFrame]]] = {
        "cascade": [],
        "recovery": [],
        "tight-turn": [],
        "mixed": [],
    }
    window_size = 4
    for sequence in sequences:
        if len(sequence) < window_size:
            continue
        ordered = sequence.sort_values("ScheduledDepartureUTC").reset_index(drop=True)
        propagated = ordered["PropagationSignal"].to_numpy(dtype="int8")
        recovered = ordered["RecoverySignal"].to_numpy(dtype="int8")
        turns = ordered["ScheduledTurnMinutes"].to_numpy(dtype="float64")
        delays = np.maximum(
            ordered["PrevArrDelay"].to_numpy(dtype="float64"),
            ordered["DepDelay"].to_numpy(dtype="float64"),
        )
        local_best: dict[str, tuple[tuple[float, ...], int]] = {}
        for start in range(len(ordered) - window_size + 1):
            end = start + window_size
            propagated_count = int(propagated[start:end].sum())
            recovered_count = int(recovered[start:end].sum())
            tightest_turn = float(turns[start:end].min())
            max_delay = float(delays[start:end].max())
            if max_delay > 240:
                continue

            scores: dict[str, tuple[float, ...]] = {}
            if propagated_count >= 3:
                scores["cascade"] = (
                    float(propagated_count),
                    max_delay,
                    -tightest_turn,
                )
            if recovered_count >= 2 and max_delay >= 30:
                scores["recovery"] = (
                    float(recovered_count),
                    max_delay,
                    -tightest_turn,
                )
            if tightest_turn <= 40 and propagated_count >= 2:
                scores["tight-turn"] = (
                    -tightest_turn,
                    float(propagated_count),
                    max_delay,
                )
            if propagated_count >= 1 and recovered_count >= 1:
                scores["mixed"] = (
                    float(propagated_count + recovered_count),
                    float(propagated_count),
                    max_delay,
                )

            for label, score in scores.items():
                if label not in local_best or score > local_best[label][0]:
                    local_best[label] = (score, start)

        for label, (score, start) in local_best.items():
            candidates[label].append(
                (score, ordered.iloc[start : start + window_size].copy())
            )

    chosen: list[tuple[str, pd.DataFrame]] = []
    used: set[str] = set()
    for label in ["cascade", "recovery", "tight-turn", "mixed"]:
        for _, sequence in sorted(candidates[label], key=lambda item: item[0], reverse=True):
            key = (
                str(sequence.iloc[0]["Tail_Number"]),
            )
            if key[0] not in used:
                chosen.append((label, sequence))
                used.add(key[0])
                break
    return chosen


def story_from_sequence(label: str, sequence: pd.DataFrame, index: int) -> dict[str, object]:
    sequence = sequence.sort_values("ScheduledDepartureUTC")
    first = sequence.iloc[0]
    profile = sequence_profile(sequence)
    titles = {
        "cascade": "Delay carried through the rotation",
        "recovery": "Schedule buffer broke the chain",
        "tight-turn": "A short turn left no room",
        "mixed": "Propagation, then recovery",
    }
    summaries = {
        "cascade": f"{profile['propagated']} downstream departures crossed the 15-minute threshold.",
        "recovery": f"{profile['recovered']} delayed arrivals were absorbed before the next departure.",
        "tight-turn": f"The tightest scheduled turn was only {int(profile['tightest'])} minutes.",
        "mixed": "The same aircraft shows why network stress is not a one-way cascade.",
    }

    legs: list[dict[str, object]] = [
        {
            "flight": f"{first['PrevReportingAirline']} {int(first['PrevFlightNumber'])}",
            "origin": str(first["PrevOrigin"]),
            "dest": str(first["PrevDest"]),
            "scheduled": first["PrevScheduledDepartureUTC"].strftime("%H:%MZ"),
            "depDelay": None,
            "arrDelay": round_or_zero(first["PrevArrDelay"], 0),
            "status": "delayed" if first["PrevArrDelay"] >= 15 else "on-time",
        }
    ]
    for _, row in sequence.iterrows():
        if row["PropagationSignal"]:
            status = "propagated"
        elif row["RecoverySignal"]:
            status = "recovered"
        elif row["DepDelay"] >= 15:
            status = "delayed"
        else:
            status = "on-time"
        legs.append(
            {
                "flight": f"{row['Reporting_Airline']} {int(row['Flight_Number_Reporting_Airline'])}",
                "origin": str(row["Origin"]),
                "dest": str(row["Dest"]),
                "scheduled": row["ScheduledDepartureUTC"].strftime("%H:%MZ"),
                "depDelay": round_or_zero(row["DepDelay"], 0),
                "arrDelay": round_or_zero(row["ArrDelay"], 0),
                "turn": round_or_zero(row["ScheduledTurnMinutes"], 0),
                "status": status,
            }
        )

    return {
        "id": f"story-{index + 1}",
        "type": label,
        "title": titles[label],
        "summary": summaries[label],
        "tail": str(first["Tail_Number"]),
        "date": first["PrevFlightDate"].strftime("%Y-%m-%d"),
        "edges": int(profile["edges"]),
        "propagated": int(profile["propagated"]),
        "recovered": int(profile["recovered"]),
        "legs": legs,
    }


def main() -> None:
    flights = pd.read_parquet(PROCESSED / "p0_flights.parquet")
    links = pd.read_parquet(PROCESSED / "p0_chain_links.parquet")
    flights["FlightDate"] = pd.to_datetime(flights["FlightDate"])
    links["FlightDate"] = pd.to_datetime(links["FlightDate"])

    operated = flights[flights["Cancelled"] == 0]
    upstream = links[links["UpstreamArrDelayed15"]]
    daily = build_daily(flights, links)
    sequences = split_sequences(links)
    stories = [
        story_from_sequence(label, sequence, index)
        for index, (label, sequence) in enumerate(choose_story_sequences(sequences))
    ]

    payload = {
        "meta": {
            "period": "May 2026",
            "records": int(len(flights)),
            "airports": int(pd.concat([flights["Origin"], flights["Dest"]]).nunique()),
            "airlines": int(flights["Reporting_Airline"].nunique()),
            "tails": int(flights["Tail_Number"].nunique()),
            "chainLinks": int(len(links)),
            "source": "U.S. DOT Bureau of Transportation Statistics",
            "coverage": "Reporting carriers' scheduled domestic passenger flights",
        },
        "national": {
            "delayRate": round_or_zero(ratio(operated["DepDelay"] >= 15)),
            "cancelRate": round_or_zero(ratio(flights["Cancelled"] == 1)),
            "propagationRate": round_or_zero(
                ratio(upstream["DownstreamDepDelayed15"])
            ),
            "recoveryRate": round_or_zero(
                ratio(~upstream["DownstreamDepDelayed15"])
            ),
            "peakDay": max(daily, key=lambda row: row["delayRate"])["date"],
        },
        "daily": daily,
        "airports": build_airports(flights, links),
        "airlines": build_airlines(flights, links),
        "stories": stories,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"wrote {OUTPUT} with {len(payload['airports'])} airports, "
        f"{len(payload['airlines'])} airlines and {len(stories)} stories"
    )


if __name__ == "__main__":
    main()
