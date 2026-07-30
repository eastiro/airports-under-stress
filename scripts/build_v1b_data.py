#!/usr/bin/env python
"""Build the curated, static V1-B Shockwave Episode Explorer payload.

Only frozen V1-P0 products and the existing V0 naming/daily snapshot are read.
The selection and all joins are deterministic; failure to find one exact source link
for a displayed step stops the build rather than silently picking an arbitrary row.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.airports_under_stress.v1_mechanism import sha256, write_json_safe

DATA = ROOT / "data" / "processed"
WEB = ROOT / "web" / "app"
OUT = WEB / "v1-b-data.json"
THRESHOLDS = (15, 30, 60)
# Frozen outputs from the final V1-P0 sensitivity audit. The values are also
# rendered in reports/V1_P0_MECHANISM_AUDIT.md and tested against that report.
AUDITED_SENSITIVITY = [
    {"threshold": 15, "nEpisodes": 50526, "nDeep2": 14811, "nDeep3": 5833, "maxDepth": 9, "nAirportsExposed500": 55},
    {"threshold": 30, "nEpisodes": 31162, "nDeep2": 8309, "nDeep3": 2991, "maxDepth": 8, "nAirportsExposed500": 39},
    {"threshold": 60, "nEpisodes": 14777, "nDeep2": 3335, "nDeep3": 1099, "maxDepth": 7, "nAirportsExposed500": 19},
]
TARGETS = {
    "deepest": 3,
    "high_delay_recovered": 2,
    "high_pressure_day": 2,
    "normal_day": 2,
    "crosses_midnight": 1,
    "censored": 2,
}
CATEGORY_ORDER = list(TARGETS)
EPISODE_COLUMNS = {
    "episodeId", "tailNumber", "depth", "airportsTouched", "uniqueAirportsTouched",
    "initialArrivalDelay", "maxDepartureDelay", "cumulativeAmplificationMinutes",
    "outcome", "terminationReason", "observedStartUTC", "endUTC", "crossesMidnightUTC",
}
STEP_COLUMNS = {
    "episodeId", "stepIndex", "depthAfterStep", "stepType", "prevAirport", "turnAirport",
    "nextAirport", "prevArrivalDelay", "nextDepartureDelay", "delayDelta",
    "plannedTurnMinutes", "actualTurnMinutes", "relation", "prevArrUTC", "nextDepUTC", "tailNumber",
}
LINK_COLUMNS = {
    "Tail_Number", "PrevReportingAirline", "Reporting_Airline", "PrevFlightNumber",
    "Flight_Number_Reporting_Airline", "PrevOrigin", "Origin", "Dest",
    "PrevScheduledArrivalUTC", "ScheduledDepartureUTC", "ScheduledArrivalUTC",
    "PrevActualArrivalUTC", "ActualDepartureUTC", "ScheduledTurnMinutes", "ActualTurnMinutes",
    "ArrDelay",
}


def require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{label} missing required columns: {', '.join(missing)}")


def utc(value: Any) -> pd.Timestamp:
    parsed = pd.to_datetime(value, utc=True, errors="raise")
    if pd.isna(parsed):
        raise ValueError(f"Invalid UTC value: {value!r}")
    return parsed


def iso(value: Any) -> str:
    return utc(value).isoformat().replace("+00:00", "Z")


def number(value: Any) -> float | int | None:
    if value is None or pd.isna(value):
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Non-finite number: {value!r}")
    return int(result) if result.is_integer() else round(result, 1)


def load_names(v0: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    airport_cities = {row["code"]: row["city"] for row in v0["airports"]}
    airlines = {row["code"]: row["name"] for row in v0["airlines"]}
    return airport_cities, airlines


def pressure_days(v0: dict[str, Any]) -> tuple[str, str]:
    daily = sorted(v0["daily"], key=lambda row: row["date"])
    high = min(daily, key=lambda row: (-row["delayRate"], row["date"]))["date"]
    median_rate = pd.Series([row["delayRate"] for row in daily]).median()
    normal = min(daily, key=lambda row: (abs(row["delayRate"] - median_rate), row["date"]))["date"]
    return high, normal


def episode_sort(frame: pd.DataFrame, fields: list[str], ascending: list[bool]) -> pd.DataFrame:
    return frame.sort_values(fields + ["observedStartUTC", "episodeId"], ascending=ascending + [True, True], kind="mergesort")


def pick_candidates(
    episodes: pd.DataFrame, high_day: str, normal_day: str,
) -> list[tuple[str, pd.DataFrame]]:
    recovered = episodes[episodes["outcome"].eq("recovered")]
    return [
        ("deepest", episode_sort(episodes, ["depth", "maxDepartureDelay"], [False, False])),
        ("high_delay_recovered", episode_sort(recovered, ["initialArrivalDelay", "depth"], [False, False])),
        ("high_pressure_day", episode_sort(episodes[episodes["startDate"].eq(high_day)], ["depth", "initialArrivalDelay"], [False, False])),
        ("normal_day", episode_sort(episodes[episodes["startDate"].eq(normal_day)], ["depth", "initialArrivalDelay"], [False, False])),
        ("crosses_midnight", episode_sort(episodes[episodes["crossesMidnightUTC"].astype(bool)], ["depth"], [False])),
        ("censored", episode_sort(episodes[episodes["outcome"].eq("censored")], ["depth", "initialArrivalDelay"], [False, False])),
    ]


def select_episodes(episodes: pd.DataFrame, high_day: str, normal_day: str) -> list[tuple[str, pd.Series]]:
    """Select exactly the category targets with stable, auditable de-duplication.

    One tail, at most two reporting carriers, and at most two start airports are
    preferred. If a category cannot meet its target under caps, the category is
    filled in the same stable sort order and carries an explicit fallback reason.
    """
    selected: list[tuple[str, pd.Series]] = []
    selected_ids: set[str] = set()
    tail_counts: dict[str, int] = {}
    carrier_counts: dict[str, int] = {}
    airport_counts: dict[str, int] = {}

    for category, candidates in pick_candidates(episodes, high_day, normal_day):
        wanted = TARGETS[category]
        chosen = 0
        for relaxed in (False, True):
            for _, row in candidates.iterrows():
                if chosen == wanted or row.episodeId in selected_ids:
                    continue
                tail_ok = tail_counts.get(row.tailNumber, 0) < 1
                carrier_ok = carrier_counts.get(row.carrier, 0) < 2
                airport_ok = airport_counts.get(row.observedStartAirport, 0) < 2
                if not relaxed and not (tail_ok and carrier_ok and airport_ok):
                    continue
                item = row.copy()
                item["selectionFallback"] = relaxed
                selected.append((category, item))
                selected_ids.add(row.episodeId)
                tail_counts[row.tailNumber] = tail_counts.get(row.tailNumber, 0) + 1
                carrier_counts[row.carrier] = carrier_counts.get(row.carrier, 0) + 1
                airport_counts[row.observedStartAirport] = airport_counts.get(row.observedStartAirport, 0) + 1
                chosen += 1
            if chosen == wanted:
                break
        if chosen != wanted:
            raise ValueError(f"Unable to select {wanted} eligible {category} episodes")
    return selected


def build_link_index(links: pd.DataFrame) -> dict[tuple[str, str, str, str, pd.Timestamp, pd.Timestamp], pd.Series]:
    indexed: dict[tuple[str, str, str, str, pd.Timestamp, pd.Timestamp], pd.Series] = {}
    for _, row in links.iterrows():
        key = (str(row.Tail_Number), str(row.PrevOrigin), str(row.Origin), str(row.Dest), utc(row.PrevActualArrivalUTC), utc(row.ActualDepartureUTC))
        if key in indexed:
            raise ValueError(f"p0_chain_links contains duplicate six-key source link: {key}")
        indexed[key] = row
    return indexed


def source_link_for_step(step: pd.Series, links: dict, prior: pd.Series | None) -> pd.Series:
    """Return the uniquely matching P0 link for a step.

    `recovered_en_route` describes the arrival of the immediately previous delayed
    flight, so its six physical fields are not a turnover link. It is verified
    against that prior delayed step's already exact-matched source edge; this is a
    strict flight-identity association, not a fuzzy lookup.
    """
    if step.stepType == "recovered_en_route":
        if prior is None or prior.stepType != "delayed":
            raise ValueError(f"{step.episodeId} has terminal en-route recovery without prior delayed step")
        key_step = prior
    else:
        key_step = step
    key = (str(key_step.tailNumber), str(key_step.prevAirport), str(key_step.turnAirport), str(key_step.nextAirport), utc(key_step.prevArrUTC), utc(key_step.nextDepUTC))
    try:
        return links[key]
    except KeyError as exc:
        raise ValueError(f"No exact P0 chain link for {step.episodeId} step {step.stepIndex}: {key}") from exc


def state_key(step: pd.Series) -> str:
    if step.stepType in {"recovered", "recovered_en_route"}:
        return step.stepType
    return "caught_up" if step.relation == "caught_up" else ("amplified" if step.delayDelta > 0 else "propagated")


def flight(link: pd.Series, prefix: str, carrier_names: dict[str, str]) -> dict[str, Any]:
    carrier = str(link["PrevReportingAirline"] if prefix == "previous" else link["Reporting_Airline"])
    flight_number = link["PrevFlightNumber"] if prefix == "previous" else link["Flight_Number_Reporting_Airline"]
    return {"carrierCode": carrier, "carrierNameEn": carrier_names.get(carrier, carrier), "flightNumber": str(int(flight_number)) if pd.notna(flight_number) else None}


def airport(code: Any, airport_cities: dict[str, str]) -> dict[str, Any] | None:
    code = str(code)
    if not code:
        return None
    return {"code": code, "cityEn": airport_cities.get(code, code)}


def enrich_step(step: pd.Series, link: pd.Series, airport_cities: dict[str, str], carrier_names: dict[str, str]) -> dict[str, Any]:
    en_route = step.stepType == "recovered_en_route"
    return {
        "stepIndex": int(step.stepIndex),
        "depthAfterStep": int(step.depthAfterStep),
        "stepType": step.stepType,
        "relation": step.relation,
        "stateKey": state_key(step),
        "prevAirport": airport(step.prevAirport, airport_cities),
        "turnAirport": airport(step.turnAirport, airport_cities),
        "nextAirport": airport(step.nextAirport, airport_cities),
        "previousFlight": flight(link, "previous", carrier_names) if not en_route else flight(link, "next", carrier_names),
        "nextFlight": flight(link, "next", carrier_names) if not en_route else None,
        "prevArrivalDelay": number(step.prevArrivalDelay),
        "nextDepartureDelay": number(step.nextDepartureDelay),
        "nextArrivalDelay": number(link.ArrDelay),
        "delayDelta": number(step.delayDelta),
        "plannedTurnMinutes": number(step.plannedTurnMinutes),
        "actualTurnMinutes": number(step.actualTurnMinutes),
        "prevActualArrivalUTC": iso(step.prevArrUTC),
        "nextActualDepartureUTC": iso(step.nextDepUTC),
        "nextActualArrivalUTC": iso(utc(link.ScheduledArrivalUTC) + pd.to_timedelta(float(link.ArrDelay), unit="m")),
        "previousScheduledArrivalUTC": iso(link.PrevScheduledArrivalUTC) if not en_route else iso(link.ScheduledArrivalUTC),
        "nextScheduledDepartureUTC": iso(link.ScheduledDepartureUTC) if not en_route else None,
        "sourceLinkMatch": "prior_delayed_flight" if en_route else "six_key_exact",
    }


def build_threshold_view(episode: pd.Series, rendered_steps: list[dict[str, Any]], threshold: int) -> dict[str, Any]:
    """Reclassify one frozen T15 physical path under a stricter threshold.

    Because 30/60 are stricter than the frozen 15-minute definition, a case can
    only terminate earlier or fail to qualify; it can never require links beyond
    the already published T15 path.
    """
    initial_delay = float(episode.initialArrivalDelay)
    if initial_delay < threshold:
        return {
            "threshold": threshold,
            "qualifies": False,
            "depth": 0,
            "observationCount": 0,
            "maxDepartureDelay": None,
            "cumulativeAmplificationMinutes": 0,
            "durationMinutes": 0,
            "uniqueAirportsTouched": 0,
            "outcome": "not_qualified",
            "terminationReason": "initial_delay_below_threshold",
            "endUTC": iso(episode.observedStartUTC),
            "steps": [],
        }

    view_steps: list[dict[str, Any]] = []
    depth = 0
    max_departure = 0.0
    amplification = 0.0
    outcome = "censored"
    termination = str(episode.terminationReason)
    end_utc = utc(episode.endUTC)
    touched: list[str] = []

    for rendered in rendered_steps:
        # The en-route terminal row duplicates the prior physical flight. It is
        # recreated below when that flight's arrival crosses the active threshold.
        if rendered["stepType"] == "recovered_en_route":
            continue

        departure_delay = float(rendered["nextDepartureDelay"])
        arrival_delay = float(rendered["nextArrivalDelay"])
        source_index = int(rendered["stepIndex"])
        touched.extend([
            rendered["prevAirport"]["code"],
            rendered["turnAirport"]["code"],
            rendered["nextAirport"]["code"] if rendered["nextAirport"] else "",
        ])

        if departure_delay < threshold:
            view_steps.append({
                "sourceStepIndex": source_index,
                "phase": "departure",
                "stateKey": "recovered",
                "depthAfterStep": depth,
            })
            outcome = "recovered"
            termination = "recovered"
            end_utc = utc(rendered["nextActualDepartureUTC"])
            break

        depth += 1
        delta = departure_delay - float(rendered["prevArrivalDelay"])
        max_departure = max(max_departure, departure_delay)
        amplification += max(0.0, delta)
        state = "caught_up" if delta < 0 else ("amplified" if delta > 0 else "propagated")
        view_steps.append({
            "sourceStepIndex": source_index,
            "phase": "departure",
            "stateKey": state,
            "depthAfterStep": depth,
        })

        if arrival_delay < threshold:
            view_steps.append({
                "sourceStepIndex": source_index,
                "phase": "arrival",
                "stateKey": "recovered_en_route",
                "depthAfterStep": depth,
            })
            outcome = "recovered"
            termination = "recovered_en_route"
            end_utc = utc(rendered["nextActualArrivalUTC"])
            break
    else:
        outcome = "censored"

    duration = max(0.0, (end_utc - utc(episode.observedStartUTC)).total_seconds() / 60)
    return {
        "threshold": threshold,
        "qualifies": True,
        "depth": depth,
        "observationCount": len(view_steps),
        "maxDepartureDelay": number(max_departure),
        "cumulativeAmplificationMinutes": number(amplification),
        "durationMinutes": number(duration),
        "uniqueAirportsTouched": len({code for code in touched if code}),
        "outcome": outcome,
        "terminationReason": termination,
        "endUTC": iso(end_utc),
        "steps": view_steps,
    }


def finite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(finite(v) for v in value.values())
    if isinstance(value, list):
        return all(finite(v) for v in value)
    return True


def build_payload() -> dict[str, Any]:
    episodes = pd.read_parquet(DATA / "v1_p0_episodes.parquet")
    steps = pd.read_parquet(DATA / "v1_p0_steps.parquet")
    links = pd.read_parquet(DATA / "p0_chain_links.parquet")
    require_columns(episodes, EPISODE_COLUMNS, "episodes")
    require_columns(steps, STEP_COLUMNS, "steps")
    require_columns(links, LINK_COLUMNS, "chain links")
    v0 = json.loads((WEB / "v0-data.json").read_text(encoding="utf-8"))
    p0_summary = json.loads((DATA / "v1_p0_summary.json").read_text(encoding="utf-8"))
    summary_sensitivity = [
        {key: row[key] for key in AUDITED_SENSITIVITY[0]}
        for row in p0_summary["thresholdSensitivity"]
    ]
    if summary_sensitivity != AUDITED_SENSITIVITY:
        raise ValueError("V1-B sensitivity constants drift from final V1-P0 summary")
    airport_cities, carrier_names = load_names(v0)
    high_day, normal_day = pressure_days(v0)

    episodes = episodes.copy()
    episodes["observedStartUTC"] = pd.to_datetime(episodes["observedStartUTC"], utc=True)
    episodes["endUTC"] = pd.to_datetime(episodes["endUTC"], utc=True)
    episodes["startDate"] = episodes["observedStartUTC"].dt.date.astype(str)
    # Carrier is derived only by an exact first normal step match below.  Populate
    # it provisionally for deterministic diversity after validating one first link.
    index = build_link_index(links)
    first_steps = steps[steps.stepType == "delayed"].sort_values(["episodeId", "stepIndex"], kind="mergesort").groupby("episodeId", as_index=False).first()
    carriers: dict[str, str] = {}
    for _, step in first_steps.iterrows():
        carriers[step.episodeId] = str(source_link_for_step(step, index, None).Reporting_Airline)
    episodes["carrier"] = episodes.episodeId.map(carriers)
    eligible = episodes[
        episodes["carrier"].notna()
        & episodes["observedStartUTC"].notna()
        & episodes["endUTC"].notna()
        & (episodes["endUTC"] >= episodes["observedStartUTC"])
    ].copy()
    selected = select_episodes(eligible, high_day, normal_day)

    cases: list[dict[str, Any]] = []
    for category, episode in selected:
        episode_steps = steps[steps.episodeId.eq(episode.episodeId)].sort_values("stepIndex", kind="mergesort")
        if episode_steps.empty:
            raise ValueError(f"Selected episode without steps: {episode.episodeId}")
        rendered_steps = []
        prior = None
        for _, step in episode_steps.iterrows():
            link = source_link_for_step(step, index, prior)
            rendered_steps.append(enrich_step(step, link, airport_cities, carrier_names))
            prior = step
        if episode.outcome == "recovered" and rendered_steps[-1]["stepType"] not in {"recovered", "recovered_en_route"}:
            raise ValueError(f"Recovered episode lacks terminal recovery step: {episode.episodeId}")
        if episode.outcome == "censored" and rendered_steps[-1]["stateKey"] in {"recovered", "recovered_en_route"}:
            raise ValueError(f"Censored episode falsely ends recovered: {episode.episodeId}")
        duration = (episode.endUTC - episode.observedStartUTC).total_seconds() / 60
        reason_key = {
            "deepest": "highest_depth",
            "high_delay_recovered": "largest_initial_delay_recovered",
            "high_pressure_day": "starts_on_high_pressure_day",
            "normal_day": "starts_on_typical_pressure_day",
            "crosses_midnight": "crosses_utc_midnight",
            "censored": "observation_censored",
        }[category]
        cases.append({
            "episodeId": episode.episodeId,
            "selectionCategory": category,
            "selectionReasonKey": reason_key,
            "selectionReasonParams": {"depth": int(episode.depth), "startDate": str(episode.startDate)},
            "tailNumber": episode.tailNumber,
            "carrier": episode.carrier,
            "depth": int(episode.depth),
            "initialArrivalDelay": number(episode.initialArrivalDelay),
            "maxDepartureDelay": number(episode.maxDepartureDelay),
            "cumulativeAmplificationMinutes": number(episode.cumulativeAmplificationMinutes),
            "durationMinutes": number(duration),
            "airportsTouched": [str(code) for code in episode.airportsTouched],
            "uniqueAirportsTouched": int(episode.uniqueAirportsTouched),
            "outcome": episode.outcome,
            "terminationReason": episode.terminationReason,
            "observedStartUTC": iso(episode.observedStartUTC),
            "endUTC": iso(episode.endUTC),
            "crossesMidnightUTC": bool(episode.crossesMidnightUTC),
            "steps": rendered_steps,
            "thresholdViews": {
                str(threshold): build_threshold_view(episode, rendered_steps, threshold)
                for threshold in THRESHOLDS
            },
        })

    payload = {
        "version": "v1_b_threshold_lab",
        "thresholdMinutes": 15,
        "availableThresholds": list(THRESHOLDS),
        "thresholdSensitivity": AUDITED_SENSITIVITY,
        "episodeContinuity": p0_summary["episodeContinuity"],
        "thresholdStability": {
            "15vs30Spearman": 0.8962,
            "15vs30Top20Overlap": 20,
            "15vs60Spearman": None,
            "15vs60Top20Overlap": 3,
        },
        "sourceSummary": {"nEpisodes": int(len(episodes)), "nSteps": int(len(steps))},
        "selectionMethod": {
            "targetCount": sum(TARGETS.values()), "categoryRequirements": TARGETS,
            "priorityOrder": CATEGORY_ORDER, "highPressureDate": high_day, "normalPressureDate": normal_day,
            "diversityCaps": {"maxPerTail": 1, "maxPerCarrier": 2, "maxPerStartAirport": 2},
        },
        "inputHashes": {name: sha256(DATA / name) for name in ["v1_p0_episodes.parquet", "v1_p0_steps.parquet", "p0_chain_links.parquet"]},
        "episodes": cases,
        "disclaimerKey": "descriptive_not_causal",
    }
    if len(cases) != sum(TARGETS.values()) or len({case["episodeId"] for case in cases}) != len(cases):
        raise ValueError("Curated episode count or uniqueness check failed")
    if not finite(payload):
        raise ValueError("Payload contains non-finite values")
    return payload


def main() -> None:
    payload = build_payload()
    write_json_safe(payload, OUT)
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes; {len(payload['episodes'])} curated episodes)")


if __name__ == "__main__":
    main()
