from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import airportsdata
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "web" / "app" / "v0-data.json"
COORDINATES = ROOT / "web" / "app" / "airport-coordinates.ts"

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

# Contiguous U.S. bounding box used both for route filtering and the canvas
# projection, so the boundary outline and the airport nodes share one frame.
US_BOUNDS = {"west": -125.0, "east": -66.0, "south": 24.0, "north": 50.0}

ROUTE_TARGET = 48
ROUTE_MIN_FLIGHTS = 200
TIGHT_TURN_MIN = 15
TIGHT_TURN_MAX = 40


def ratio(mask: pd.Series, denominator: int | None = None) -> float:
    total = len(mask) if denominator is None else denominator
    return 0.0 if total == 0 else float(mask.sum() / total)


def round_or_zero(value: float, digits: int = 4) -> float:
    return round(0.0 if pd.isna(value) else float(value), digits)


def fmt_z(ts: pd.Timestamp) -> str:
    return ts.strftime("%H:%MZ")


def day_tag(ts: pd.Timestamp, ref: date) -> str:
    """Chinese day-shift suffix when a UTC timestamp leaves the flight date."""
    delta = (ts.date() - ref).days
    if delta == 0:
        return ""
    if delta == 1:
        return " · 次日"
    if delta == -1:
        return " · 前日"
    return f" · {delta:+d}天"


def utc_field(ts: object, ref: date) -> str:
    if ts is None or pd.isna(ts):
        return "未报告"
    ts = pd.Timestamp(ts)
    return f"{fmt_z(ts)}{day_tag(ts, ref)}"


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

    # Ordinal ranks within the 97 eligible airports (1 = worst / highest value).
    eligible["rankPressure"] = eligible["pressureScore"].rank(ascending=False, method="min").astype(int)
    eligible["rankDelay"] = eligible["delayRate"].rank(ascending=False, method="min").astype(int)
    eligible["rankCancel"] = eligible["cancelRate"].rank(ascending=False, method="min").astype(int)
    eligible["rankPropagation"] = eligible["propagationRate"].rank(ascending=False, method="min").astype(int)
    eligible["rankFlights"] = eligible["flights"].rank(ascending=False, method="min").astype(int)

    eligible = eligible.sort_values("pressureScore", ascending=False)
    columns = list(records[0].keys()) + [
        "pressureScore", "rankPressure", "rankDelay", "rankCancel", "rankPropagation", "rankFlights"
    ]
    return eligible[columns].to_dict(orient="records")


def build_airlines(flights: pd.DataFrame, links: pd.DataFrame) -> list[dict[str, object]]:
    link_groups = links.groupby("Reporting_Airline")
    records: list[dict[str, object]] = []
    for code, group in flights.groupby("Reporting_Airline"):
        if len(group) < 10_000:
            continue
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


def build_network_routes(
    flights: pd.DataFrame,
    target_codes: set[str] | None = None,
    max_routes: int = 72,
) -> tuple[list[dict[str, object]], set[str]]:
    """Aggregate real monthly domestic airport pairs into a base network.

    Coverage-first selection: every target node gets at least one real route.
    Then high-volume pairs fill up to max_routes. All pairs must exist in
    real operated flight data; no fabricated edges.
    """
    reference = airportsdata.load("IATA")
    coords: dict[str, tuple[float, float]] = {}
    for code, record in reference.items():
        lat = record.get("lat")
        lon = record.get("lon")
        if lat is None or lon is None:
            continue
        if not (US_BOUNDS["south"] <= lat <= US_BOUNDS["north"]):
            continue
        if not (US_BOUNDS["west"] <= lon <= US_BOUNDS["east"]):
            continue
        coords[str(code)] = (float(lat), float(lon))

    operated = flights[(flights["Cancelled"] != 1) & (flights["Diverted"] != 1)].copy()
    operated = operated[operated["Origin"].isin(coords) & operated["Dest"].isin(coords)]
    pair_key = operated.apply(
        lambda row: tuple(sorted((str(row["Origin"]), str(row["Dest"])))),
        axis=1,
    )
    operated = operated.assign(_pair=pair_key)

    grouped = operated.groupby("_pair")
    all_routes: list[dict[str, object]] = []
    for (origin, dest), group in grouped:
        if origin == dest:
            continue
        flights_count = int(len(group))
        if flights_count < ROUTE_MIN_FLIGHTS:
            continue
        delay_rate = round_or_zero(ratio(group["DepDelay"] >= 15))
        all_routes.append(
            {
                "origin": origin,
                "dest": dest,
                "flights": flights_count,
                "delayRate": delay_rate,
            }
        )

    all_routes.sort(key=lambda row: row["flights"], reverse=True)

    # Coverage-first: for each target code, pick its highest-volume real pair
    selected: list[dict[str, object]] = []
    selected_pairs: set[tuple[str, str]] = set()
    covered: set[str] = set()

    if target_codes:
        for code in sorted(target_codes):
            if code in covered:
                continue
            # Find the highest-volume route involving this code
            best: dict[str, object] | None = None
            for route in all_routes:
                pair_key_r = tuple(sorted((str(route["origin"]), str(route["dest"]))))
                if pair_key_r in selected_pairs:
                    continue
                if code in (route["origin"], route["dest"]):
                    best = route
                    break
            if best is not None:
                selected.append(best)
                selected_pairs.add(tuple(sorted((str(best["origin"]), str(best["dest"])))))
                covered.add(str(best["origin"]))
                covered.add(str(best["dest"]))

    # Fill remaining slots with highest-volume pairs
    for route in all_routes:
        if len(selected) >= max_routes:
            break
        pair_key_r = tuple(sorted((str(route["origin"]), str(route["dest"]))))
        if pair_key_r in selected_pairs:
            continue
        selected.append(route)
        selected_pairs.add(pair_key_r)
        covered.add(str(route["origin"]))
        covered.add(str(route["dest"]))

    endpoint_codes: set[str] = set()
    for route in selected:
        endpoint_codes.add(str(route["origin"]))
        endpoint_codes.add(str(route["dest"]))
    return selected, endpoint_codes


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


def classify_relation(prev_arr: float, next_dep: float) -> str:
    """Descriptive continuity between an arrival and the next departure.

    These are descriptive states, not causal claims:
    - propagated: both late and not improving (next >= prev)
    - caught_up: both late but the next departure improved (next < prev)
    - recovered_full: upstream late, next departure back under 15 min
    - delayed: next departure late without an upstream late arrival
    - on-time: neither side late
    """
    if prev_arr >= 15 and next_dep >= 15:
        return "caught_up" if next_dep < prev_arr else "propagated"
    if prev_arr >= 15 and next_dep < 15:
        return "recovered_full"
    if prev_arr < 15 and next_dep >= 15:
        return "delayed"
    return "on-time"


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
        actual_turns = ordered["ActualTurnMinutes"].to_numpy(dtype="float64")
        planned_turns = ordered["ScheduledTurnMinutes"].to_numpy(dtype="float64")
        delays = np.maximum(
            ordered["PrevArrDelay"].to_numpy(dtype="float64"),
            ordered["DepDelay"].to_numpy(dtype="float64"),
        )
        local_best: dict[str, tuple[tuple[float, ...], int]] = {}
        for start in range(len(ordered) - window_size + 1):
            end = start + window_size
            propagated_count = int(propagated[start:end].sum())
            recovered_count = int(recovered[start:end].sum())
            window_actual_turn = float(actual_turns[start:end].min())
            window_planned_ok = bool((planned_turns[start:end] > 0).all())
            max_delay = float(delays[start:end].max())
            if max_delay > 240:
                continue

            scores: dict[str, tuple[float, ...]] = {}
            if propagated_count >= 3:
                scores["cascade"] = (float(propagated_count), max_delay, -window_actual_turn)
            if recovered_count >= 2 and max_delay >= 30:
                scores["recovery"] = (float(recovered_count), max_delay, -window_actual_turn)
            if (
                window_planned_ok
                and TIGHT_TURN_MIN <= window_actual_turn <= TIGHT_TURN_MAX
                and propagated_count >= 1
                and max_delay >= 30
            ):
                scores["tight-turn"] = (-window_actual_turn, float(propagated_count), max_delay)
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
            key = str(sequence.iloc[0]["Tail_Number"])
            if key not in used:
                chosen.append((label, sequence))
                used.add(key)
                break
    return chosen


def story_from_sequence(label: str, sequence: pd.DataFrame, index: int) -> dict[str, object]:
    sequence = sequence.sort_values("ScheduledDepartureUTC").reset_index(drop=True)
    first = sequence.iloc[0]
    ref_date = pd.Timestamp(first["FlightDate"]).date()

    legs: list[dict[str, object]] = []
    for row in sequence.itertuples():
        arr_delay = round_or_zero(row.ArrDelay, 0)
        dep_delay = None if pd.isna(row.DepDelay) else round_or_zero(row.DepDelay, 0)
        sched_dep = pd.Timestamp(row.ScheduledDepartureUTC)
        sched_arr = pd.Timestamp(row.ScheduledArrivalUTC)
        actual_dep = (
            None
            if pd.isna(row.DepDelay)
            else sched_dep + timedelta(minutes=float(row.DepDelay))
        )
        actual_arr = (
            None
            if pd.isna(row.ArrDelay)
            else sched_arr + timedelta(minutes=float(row.ArrDelay))
        )
        legs.append(
            {
                "flight": f"{row.Reporting_Airline} {int(row.Flight_Number_Reporting_Airline)}",
                "origin": str(row.Origin),
                "dest": str(row.Dest),
                "status": "late" if arr_delay >= 15 else "on-time",
                "depDelay": dep_delay,
                "arrDelay": arr_delay,
                "scheduledDepUTC": utc_field(sched_dep, ref_date),
                "actualDepUTC": utc_field(actual_dep, ref_date),
                "scheduledArrUTC": utc_field(sched_arr, ref_date),
                "actualArrUTC": utc_field(actual_arr, ref_date),
            }
        )

    connectors: list[dict[str, object]] = []
    for i in range(len(sequence) - 1):
        current = sequence.iloc[i]
        nxt = sequence.iloc[i + 1]
        prev_arr = round_or_zero(current["ArrDelay"], 0)
        next_dep = round_or_zero(nxt["DepDelay"], 0)
        connectors.append(
            {
                "hub": str(current["Dest"]),
                "planGap": round_or_zero(nxt["ScheduledTurnMinutes"], 0),
                "actualTurn": round_or_zero(nxt["ActualTurnMinutes"], 0),
                "prevArrDelay": prev_arr,
                "nextDepDelay": next_dep,
                "delayDelta": round_or_zero(next_dep - prev_arr, 0),
                "relation": classify_relation(prev_arr, next_dep),
            }
        )

    propagated = sum(
        1 for c in connectors if c["relation"] in ("propagated", "caught_up")
    )
    recovered = sum(1 for c in connectors if c["relation"] == "recovered_full")
    min_actual_turn = float(sequence["ActualTurnMinutes"].min())
    max_arr = int(max(round_or_zero(row.ArrDelay, 0) for row in sequence.itertuples()))

    titles = {
        "cascade": ("Delay continued across the rotation", f"连续 {propagated} 班仍在晚点"),
        "recovery": ("The next flight recovered", "晚到后被下一班追回"),
        "tight-turn": (
            f"Only {int(min_actual_turn)} minutes on the ground",
            f"实际地面只停了 {int(min_actual_turn)} 分钟",
        ),
        "mixed": ("Delay spread, then recovered", "先传递，后来追回"),
    }
    summaries = {
        "cascade": (
            f"{propagated} downstream departures stayed past the 15-minute threshold.",
            f"有 {propagated} 个后续航段的起飞延误仍超过 15 分钟。",
        ),
        "recovery": (
            f"{recovered} late arrivals were absorbed before the next departure.",
            f"有 {recovered} 次晚到在下一次起飞前被吸收。",
        ),
        "tight-turn": (
            f"The tightest real ground turn was only {int(min_actual_turn)} minutes.",
            f"这条轮转链最短的实际地面周转只有 {int(min_actual_turn)} 分钟。",
        ),
        "mixed": (
            "The same aircraft shows why network stress is not a one-way cascade.",
            "同一架飞机的轮转说明，网络压力并不是单向级联：延误可以传播，也可能在后续航段恢复。",
        ),
    }
    title_en, title_zh = titles[label]
    summary_en, summary_zh = summaries[label]

    return {
        "id": f"story-{index + 1}",
        "type": label,
        "title": title_en,
        "titleZh": title_zh,
        "summary": summary_en,
        "summaryZh": summary_zh,
        "tail": str(first["Tail_Number"]),
        "date": pd.Timestamp(first["FlightDate"]).strftime("%Y-%m-%d"),
        "edges": len(sequence) - 1,
        "legCount": len(sequence),
        "propagated": propagated,
        "recovered": recovered,
        "maxDelay": max_arr,
        "legs": legs,
        "connectors": connectors,
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
    chosen = choose_story_sequences(sequences)
    stories = [
        story_from_sequence(label, sequence, index)
        for index, (label, sequence) in enumerate(chosen)
    ]

    # Compute target node set first, so route selection can guarantee coverage.
    airports_all = build_airports(flights, links)
    eligible_frame = pd.DataFrame(airports_all)
    top30_pressure: set[str] = set(eligible_frame.nlargest(30, "pressureScore")["code"])
    top30_flights: set[str] = set(eligible_frame.nlargest(30, "flights")["code"])
    target_codes: set[str] = top30_pressure | top30_flights
    for story in stories:
        for leg in story["legs"]:
            target_codes.add(str(leg["origin"]))
            target_codes.add(str(leg["dest"]))
    target_codes.discard("")

    # Coverage-first route selection: every target node gets ≥1 real route.
    routes, route_endpoints = build_network_routes(flights, target_codes=target_codes)

    map_codes: set[str] = target_codes | route_endpoints
    map_codes.discard("")
    needed_codes = map_codes.copy()
    for airport in airports_all:
        needed_codes.add(str(airport["code"]))
    augment_coordinates(needed_codes)

    airlines_filtered = build_airlines(flights, links)
    raw_airport_count = int(pd.concat([flights["Origin"], flights["Dest"]]).nunique())
    raw_airline_count = int(flights["Reporting_Airline"].nunique())

    payload = {
        "meta": {
            "period": "May 2026",
            "records": int(len(flights)),
            "rawAirports": raw_airport_count,
            "eligibleAirports": len(airports_all),
            "mapAirports": len(map_codes),
            "rankedAirportsShown": 12,
            "rawAirlines": raw_airline_count,
            "comparableAirlines": len(airlines_filtered),
            "tails": int(flights["Tail_Number"].nunique()),
            "chainLinks": int(len(links)),
            "source": "U.S. DOT Bureau of Transportation Statistics",
            "coverage": "Reporting carriers' scheduled domestic passenger flights",
            "airlineThreshold": "Monthly flights ≥ 10,000",
        },
        "national": {
            "delayRate": round_or_zero(ratio(operated["DepDelay"] >= 15)),
            "cancelRate": round_or_zero(ratio(flights["Cancelled"] == 1)),
            "propagationRate": round_or_zero(ratio(upstream["DownstreamDepDelayed15"])),
            "recoveryRate": round_or_zero(ratio(~upstream["DownstreamDepDelayed15"])),
            "peakDay": max(daily, key=lambda row: row["delayRate"])["date"],
        },
        "daily": daily,
        "network": {
            "selection": (
                f"Coverage-first selection: every target map node has ≥1 real operated pair, "
                f"then highest-volume pairs fill to {len(routes)} total. "
                f"All pairs exist in real operated contiguous-U.S. flights with ≥{ROUTE_MIN_FLIGHTS} monthly flights."
            ),
            "routes": routes,
        },
        "mapAirportCodes": sorted(map_codes),
        "airports": airports_all,
        "airlines": airlines_filtered,
        "stories": stories,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"wrote {OUTPUT} with {len(payload['airports'])} airports, "
        f"{len(payload['airlines'])} airlines, {len(stories)} stories, "
        f"{len(routes)} routes and {len(map_codes)} map nodes"
    )


def augment_coordinates(needed: set[str]) -> None:
    """Add any missing airport coordinates from the same OurAirports/IATA source.

    Existing entries are preserved verbatim; only new codes are appended.
    """
    reference = airportsdata.load("IATA")
    merged: dict[str, dict[str, float]] = {}
    if COORDINATES.exists():
        raw = COORDINATES.read_text(encoding="utf-8")
        marker = "AIRPORT_COORDINATES: Record<string, AirportCoordinate> = {"
        idx = raw.find(marker)
        current: dict[str, dict[str, float]] = {}
        if idx != -1:
            start = raw.find("{", idx)
            depth = 0
            end = None
            for j in range(start, len(raw)):
                if raw[j] == "{":
                    depth += 1
                elif raw[j] == "}":
                    depth -= 1
                    if depth == 0:
                        end = j + 1
                        break
            if end:
                try:
                    import re

                    cleaned = re.sub(r",\s*}", "}", raw[start:end])
                    current = json.loads(cleaned)
                except json.JSONDecodeError:
                    current = {}
            for code, value in current.items():
                merged[code] = {
                    "ident": value.get("ident", f"K{code}"),
                    "latitude": value["latitude"],
                    "longitude": value["longitude"],
                }
    added = 0
    for code in sorted(needed):
        if code in merged:
            continue
        record = reference.get(code)
        if not record:
            continue
        lat = record.get("lat")
        lon = record.get("lon")
        if lat is None or lon is None:
            continue
        merged[code] = {
            "ident": record.get("ident", f"K{code}"),
            "latitude": float(lat),
            "longitude": float(lon),
        }
        added += 1

    lines = [
        'export type AirportCoordinate = {',
        '  ident: string;',
        '  latitude: number;',
        '  longitude: number;',
        '};',
        '',
        'export const AIRPORT_COORDINATE_SOURCE = {',
        '  name: "OurAirports airports.csv",',
        '  url: "https://ourairports.com/data/airports.csv",',
        '  dictionary: "https://ourairports.com/help/data-dictionary.html",',
        '  retrieved: "2026-07-26",',
        '  license: "Public Domain; accuracy is not guaranteed by the source",',
        '} as const;',
        '',
        '// Checked-in subset used by the V0 hero. Values preserve the source decimal',
        '// latitude/longitude so canvas placement can be reproduced by one projection.',
        'export const AIRPORT_COORDINATES: Record<string, AirportCoordinate> = {',
    ]
    for code in sorted(merged):
        value = merged[code]
        lines.append(
            f'  {code}: {{ ident: "{value["ident"]}", latitude: {value["latitude"]}, longitude: {value["longitude"]} }},'
        )
    lines.append('};')
    lines.append('')
    COORDINATES.write_text("\n".join(lines), encoding="utf-8")
    print(f"airport-coordinates.ts: {len(merged)} airports ({added} added)")


if __name__ == "__main__":
    main()
