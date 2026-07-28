"""V1-P0: Propagation mechanism and shockwave episode reconstruction.

All analysis is derived from the frozen P0 chain links.
No P0 definitions are altered, no frontend is touched.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from scipy.stats import binom

EPISODE_MAX_SCHEDULED_TURN_MINUTES = 180
EPISODE_MAX_DURATION_HOURS = 18

# ── file hashing ──────────────────────────────────────────────────

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json_safe(data: dict | list, path: Path) -> None:
    """Write JSON ensuring no NaN/Inf values."""
    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    # Replace any NaN/Inf that might slip through
    for bad in ("NaN", "Infinity", "-Infinity"):
        text = text.replace(f": {bad}", ": null")
        text = text.replace(f": -{bad}", ": null")
        text = text.replace(f":{bad}", ":null")
    path.write_text(text, encoding="utf-8")


# ── episode reconstruction ────────────────────────────────────────

def _chain_invariants(links: pd.DataFrame) -> bool:
    """Verify that consecutive links for the same tail are physically consistent."""
    ok = True
    if (links["ActualTurnMinutes"] < 0).any():
        ok = False
    # Group by tail and check airport continuity
    # (prev dest == current origin is already guaranteed by P0 chain building)
    return ok


def build_shockwave_episodes(
    links: pd.DataFrame,
    threshold: int = 15,
    max_scheduled_turn_minutes: int | None = EPISODE_MAX_SCHEDULED_TURN_MINUTES,
    max_episode_hours: int | None = EPISODE_MAX_DURATION_HOURS,
) -> pd.DataFrame:
    """Reconstruct shockwave episodes from P0 chain links.

    An episode starts when PrevArrDelay >= threshold (inbound was late).
    Tracks each subsequent departure: >=T is a delayed step, <T is a recovery step.
    Records recovery steps (terminal departure recovery AND en-route arrival recovery).
    Chain gaps → censored (not recovered). Gap link picked up as potential new start.
    Optional continuity limits separate the physical aircraft chain from a tighter
    operational episode: planned long ground stops are not propagation edges, and
    an elapsed-time ceiling censors an episode instead of claiming an indefinitely
    persistent original shock.
    """
    if max_scheduled_turn_minutes is not None and max_scheduled_turn_minutes <= 0:
        raise ValueError("max_scheduled_turn_minutes must be positive or None")
    if max_episode_hours is not None and max_episode_hours <= 0:
        raise ValueError("max_episode_hours must be positive or None")

    links = links.sort_values(["Tail_Number", "ScheduledDepartureUTC"]).copy()
    links["_prev_arr_late"] = links["PrevArrDelay"] >= threshold
    links["_ActualArrivalUTC"] = links["ScheduledArrivalUTC"] + pd.to_timedelta(links["ArrDelay"].fillna(0), unit="m")

    episodes: list[dict] = []
    steps_list: list[dict] = []
    episode_counter = 0

    for tail, group in links.groupby("Tail_Number", sort=False):
        group = group.reset_index(drop=True)
        n = len(group)
        i = 0
        while i < n:
            row = group.iloc[i]
            if not row["_prev_arr_late"]:
                i += 1
                continue
            # The P0 physical chain deliberately permits planned ground stops up
            # to 12 hours.  Such a link remains useful for tail continuity, but a
            # long planned stop must not start a propagation episode.
            if (
                max_scheduled_turn_minutes is not None
                and float(row["ScheduledTurnMinutes"])
                > max_scheduled_turn_minutes
            ):
                i += 1
                continue

            episode_counter += 1
            episode_id = f"ep-{tail}-{episode_counter:06d}"
            start_utc = row["PrevActualArrivalUTC"]
            start_airport = row["Origin"]
            initial_arrival_delay = float(row["PrevArrDelay"])
            start_prev_origin = str(row.get("PrevOrigin", ""))

            depth = 0
            max_dep_delay = 0.0
            terminal_dep_delay = 0.0
            cumul_amplification = 0.0
            airports: list[str] = [start_airport]
            outcome = "recovered"
            termination_reason = "recovered"
            end_utc = row["ActualDepartureUTC"]
            end_airport = row["Origin"]
            last_observed_utc = pd.Timestamp(start_utc)
            last_observed_airport = str(start_airport)
            deadline_utc = (
                pd.Timestamp(start_utc) + pd.Timedelta(hours=max_episode_hours)
                if max_episode_hours is not None
                else None
            )
            quality_flags: list[str] = []

            j = i
            while j < n:
                r = group.iloc[j]

                # Airport continuity check (except first step of episode)
                if j > i:
                    prior = group.iloc[j - 1]
                    same_inbound_flight = (
                        prior["Origin"] == r.get("PrevOrigin")
                        and prior["Dest"] == r["Origin"]
                        and pd.Timestamp(prior["_ActualArrivalUTC"])
                        == pd.Timestamp(r["PrevActualArrivalUTC"])
                    )
                    if not same_inbound_flight:
                        quality_flags.append("airport_discontinuity")
                        outcome = "censored"
                        termination_reason = "airport_discontinuity"
                        end_utc = group.iloc[j - 1]["ActualDepartureUTC"]
                        end_airport = group.iloc[j - 1]["Dest"]
                        # Do NOT skip j; next iteration of outer loop starts at j
                        break

                # A planned long stop is an operational boundary, not evidence
                # that the original delay kept propagating.  Preserve the P0
                # physical link but censor this episode at the inbound arrival.
                if (
                    max_scheduled_turn_minutes is not None
                    and float(r["ScheduledTurnMinutes"])
                    > max_scheduled_turn_minutes
                ):
                    quality_flags.append("scheduled_turn_break")
                    outcome = "censored"
                    termination_reason = "scheduled_turn_break"
                    end_utc = last_observed_utc
                    end_airport = last_observed_airport
                    break

                departure_utc = pd.Timestamp(r["ActualDepartureUTC"])
                if deadline_utc is not None and departure_utc > deadline_utc:
                    quality_flags.append("duration_limit")
                    outcome = "censored"
                    termination_reason = "duration_limit"
                    end_utc = last_observed_utc
                    end_airport = last_observed_airport
                    break

                prev_delay: float
                if j == i:
                    prev_delay = initial_arrival_delay
                else:
                    prev_delay = float(group.iloc[j - 1]["ArrDelay"])

                dep_late = r["DepDelay"] >= threshold
                prev_airport = str(r.get("PrevOrigin", ""))
                turn_airport = str(r["Origin"])
                next_airport = str(r["Dest"])

                if dep_late:
                    # Delayed step
                    depth += 1
                    max_dep_delay = max(max_dep_delay, float(r["DepDelay"]))
                    cumul_amplification += max(0.0, float(r["DepDelay"]) - prev_delay)
                    terminal_dep_delay = float(r["DepDelay"])

                    relation = "caught_up" if float(r["DepDelay"]) < prev_delay else "persisted_or_amplified"
                    steps_list.append({
                        "episodeId": episode_id,
                        "stepIndex": len(airports) - 1,
                        "depthAfterStep": depth,
                        "stepType": "delayed",
                        "prevAirport": prev_airport,
                        "turnAirport": turn_airport,
                        "nextAirport": next_airport,
                        "prevArrivalDelay": round(prev_delay, 1),
                        "nextDepartureDelay": float(r["DepDelay"]),
                        "delayDelta": round(float(r["DepDelay"]) - prev_delay, 1),
                        "plannedTurnMinutes": float(r["ScheduledTurnMinutes"]),
                        "actualTurnMinutes": float(r["ActualTurnMinutes"]),
                        "relation": relation,
                        "prevArrUTC": str(r["PrevActualArrivalUTC"]),
                        "nextDepUTC": str(r["ActualDepartureUTC"]),
                        "tailNumber": tail,
                    })
                    airports.append(next_airport)
                    last_observed_utc = departure_utc
                    last_observed_airport = turn_airport

                    j += 1
                    arrival_utc = pd.Timestamp(r["_ActualArrivalUTC"])
                    if deadline_utc is not None and arrival_utc > deadline_utc:
                        quality_flags.append("duration_limit")
                        outcome = "censored"
                        termination_reason = "duration_limit"
                        end_utc = last_observed_utc
                        end_airport = last_observed_airport
                        break

                    # Check if the departing flight arrived on time
                    if float(r["ArrDelay"]) < threshold:
                        # En-route recovery: departed late but arrived on time
                        outcome = "recovered"
                        termination_reason = "recovered_en_route"
                        end_utc = r["_ActualArrivalUTC"]
                        end_airport = next_airport
                        # Record the en-route recovery step
                        steps_list.append({
                            "episodeId": episode_id,
                            "stepIndex": len(airports) - 1,
                            "depthAfterStep": depth,
                            "stepType": "recovered_en_route",
                            "prevAirport": turn_airport,
                            "turnAirport": next_airport,
                            "nextAirport": "",
                            "prevArrivalDelay": float(r["DepDelay"]),
                            "nextDepartureDelay": float(r["ArrDelay"]),
                            "delayDelta": float(r["ArrDelay"]) - float(r["DepDelay"]),
                            "plannedTurnMinutes": 0.0,
                            "actualTurnMinutes": 0.0,
                            "relation": "recovered",
                            "prevArrUTC": str(r["ActualDepartureUTC"]),
                            "nextDepUTC": str(r["_ActualArrivalUTC"]),
                            "tailNumber": tail,
                        })
                        break
                    last_observed_utc = arrival_utc
                    last_observed_airport = next_airport
                    if j >= n:
                        outcome = "censored"
                        termination_reason = "end_of_sequence"
                        quality_flags.append("end_of_sequence")
                        end_utc = arrival_utc
                        end_airport = next_airport
                        break
                    # Otherwise, arriving flight was late → continue via next link
                else:
                    # Terminal departure recovery
                    outcome = "recovered"
                    termination_reason = "recovered"
                    end_utc = r["ActualDepartureUTC"]
                    end_airport = turn_airport
                    terminal_dep_delay = float(r["DepDelay"])
                    # Record the recovery step
                    steps_list.append({
                        "episodeId": episode_id,
                        "stepIndex": len(airports) - 1,
                        "depthAfterStep": depth,
                        "stepType": "recovered",
                        "prevAirport": prev_airport,
                        "turnAirport": turn_airport,
                        "nextAirport": next_airport,
                        "prevArrivalDelay": round(prev_delay, 1),
                        "nextDepartureDelay": float(r["DepDelay"]),
                        "delayDelta": round(float(r["DepDelay"]) - prev_delay, 1),
                        "plannedTurnMinutes": float(r["ScheduledTurnMinutes"]),
                        "actualTurnMinutes": float(r["ActualTurnMinutes"]),
                        "relation": "recovered",
                        "prevArrUTC": str(r["PrevActualArrivalUTC"]),
                        "nextDepUTC": str(r["ActualDepartureUTC"]),
                        "tailNumber": tail,
                    })
                    j += 1
                    break

            crossed_midnight = False
            if pd.notna(start_utc) and pd.notna(end_utc):
                try:
                    if str(start_utc)[:10] != str(end_utc)[:10]:
                        crossed_midnight = True
                except Exception:
                    pass

            episodes.append({
                "episodeId": episode_id,
                "tailNumber": tail,
                "thresholdMinutes": threshold,
                "observedStartUTC": str(start_utc),
                "observedStartAirport": start_airport,
                "startPrevOrigin": start_prev_origin,
                "depth": depth,
                "legCount": depth + (1 if outcome == "recovered" else 1),
                "airportsTouched": airports,
                "uniqueAirportsTouched": len(set(airports)),
                "initialArrivalDelay": round(initial_arrival_delay, 1),
                "maxDepartureDelay": round(max_dep_delay, 1),
                "terminalDepartureDelay": round(terminal_dep_delay, 1),
                "cumulativeAmplificationMinutes": round(cumul_amplification, 1),
                "outcome": outcome,
                "terminationReason": termination_reason,
                "endUTC": str(end_utc),
                "endAirport": end_airport,
                "crossesMidnightUTC": crossed_midnight,
                "maxScheduledTurnMinutes": max_scheduled_turn_minutes,
                "maxEpisodeHours": max_episode_hours,
                "qualityFlags": quality_flags,
            })
            # Resume from the boundary.  A duration limit can theoretically fire
            # before the first departure; always advance at least one row.
            i = max(j, i + 1)

    episodes_df = pd.DataFrame(episodes)
    steps_df = pd.DataFrame(steps_list)

    # A small number of BTS tail assignments can form two airport-disconnected
    # chains whose observed times overlap (typically after an extreme delay).
    # Such candidates cannot be treated as physically valid episodes.  Reject
    # the earlier, gap-censored candidate and retain it in a separate audit
    # table instead of weakening the 100% non-overlap invariant.
    rejected_rows: list[dict] = []
    while len(episodes_df) > 1:
        timeline = episodes_df.copy()
        timeline["_start"] = pd.to_datetime(timeline["observedStartUTC"], utc=True)
        timeline["_end"] = pd.to_datetime(timeline["endUTC"], utc=True, errors="coerce")
        timeline = timeline.sort_values(["tailNumber", "_start", "episodeId"])
        timeline["_next_start"] = timeline.groupby("tailNumber")["_start"].shift(-1)
        conflicts = timeline[
            timeline["_end"].notna()
            & timeline["_next_start"].notna()
            & (timeline["_end"] > timeline["_next_start"])
        ]
        if conflicts.empty:
            break

        reject_ids: list[str] = []
        for _, conflict in conflicts.iterrows():
            rejected = conflict.drop(
                labels=["_start", "_end", "_next_start"]
            ).to_dict()
            rejected["rejectionReason"] = "tail_timeline_conflict"
            rejected["conflictingNextStartUTC"] = str(conflict["_next_start"])
            rejected["overlapMinutes"] = round(
                (conflict["_end"] - conflict["_next_start"]).total_seconds() / 60,
                1,
            )
            rejected_rows.append(rejected)
            reject_ids.append(conflict["episodeId"])

        episodes_df = episodes_df[~episodes_df["episodeId"].isin(reject_ids)].copy()
        steps_df = steps_df[~steps_df["episodeId"].isin(reject_ids)].copy()

    global _v1_steps
    global _v1_episode_rejections
    _v1_steps = steps_df.reset_index(drop=True)
    _v1_episode_rejections = pd.DataFrame(rejected_rows)
    return episodes_df


_v1_steps: pd.DataFrame | None = None
_v1_episode_rejections: pd.DataFrame | None = None


def build_shockwave_steps() -> pd.DataFrame:
    """Return the step-level data from the last `build_shockwave_episodes` call."""
    if _v1_steps is None:
        raise RuntimeError("Call build_shockwave_episodes first")
    return _v1_steps


def build_episode_rejections() -> pd.DataFrame:
    """Return candidates excluded by the hard timeline-integrity filter."""
    if _v1_episode_rejections is None:
        raise RuntimeError("Call build_shockwave_episodes first")
    return _v1_episode_rejections


def validate_episodes(
    episodes: pd.DataFrame,
    links: pd.DataFrame,
    steps: pd.DataFrame | None = None,
) -> dict:
    """Run hard integrity checks on episode output."""
    checks: dict[str, int] = {}

    checks["negative_actual_turn_steps"] = int((links["ActualTurnMinutes"] < 0).sum())
    gaps_mask = episodes["qualityFlags"].apply(lambda f: "airport_discontinuity" in f)
    checks["airport_discontinuity_count"] = int(gaps_mask.sum())

    # Verify no gap episode is marked recovered
    gaps_as_recovered = int((gaps_mask & (episodes["outcome"] == "recovered")).sum())
    checks["gaps_marked_recovered"] = gaps_as_recovered
    continuity_mask = episodes["qualityFlags"].apply(
        lambda flags: bool({"scheduled_turn_break", "duration_limit"} & set(flags))
    )
    checks["continuity_boundaries_marked_recovered"] = int(
        (continuity_mask & episodes["outcome"].eq("recovered")).sum()
    )

    if "maxEpisodeHours" in episodes.columns:
        durations = (
            pd.to_datetime(episodes["endUTC"], utc=True, errors="coerce")
            - pd.to_datetime(
                episodes["observedStartUTC"], utc=True, errors="coerce"
            )
        ).dt.total_seconds() / 3600
        limits = pd.to_numeric(episodes["maxEpisodeHours"], errors="coerce")
        checks["episode_duration_limit_violations"] = int(
            (limits.notna() & durations.gt(limits + 1e-9)).sum()
        )
    else:
        checks["episode_duration_limit_violations"] = 0

    steps = _v1_steps if steps is None else steps
    if steps is not None and len(steps) > 0:
        steps_sorted = steps.sort_values(["episodeId", "stepIndex"]).copy()
        steps_sorted["_utc"] = pd.to_datetime(
            steps_sorted["nextDepUTC"], utc=True, errors="coerce"
        )
        steps_sorted["_prev_utc"] = steps_sorted.groupby("episodeId")["_utc"].shift(1)
        utc_reversed = int(
            (
                steps_sorted["_utc"].isna()
                | (
                    steps_sorted["_prev_utc"].notna()
                    & (steps_sorted["_prev_utc"] > steps_sorted["_utc"])
                )
            ).sum()
        )
        checks["utc_reversed"] = utc_reversed

        # A recovered episode must end with exactly one terminal recovery step;
        # no delayed step may appear after that terminal step.
        terminal = steps_sorted.groupby("episodeId", sort=False).tail(1)
        terminal_types = terminal.set_index("episodeId")["stepType"]
        recovered_ids = episodes.loc[
            episodes["outcome"].eq("recovered"), "episodeId"
        ]
        invalid_terminal = ~recovered_ids.map(terminal_types).isin(
            ["recovered", "recovered_en_route"]
        )
        recovery_rows = steps_sorted["stepType"].isin(
            ["recovered", "recovered_en_route"]
        )
        recovery_counts = (
            steps_sorted.loc[recovery_rows].groupby("episodeId").size()
        )
        invalid_counts = recovered_ids.map(recovery_counts).fillna(0).ne(1)
        checks["recovery_not_continuing"] = int(
            (invalid_terminal | invalid_counts).sum()
        )

        # Verify the airport path in recorded step order.
        steps_sorted["_next_turn"] = steps_sorted.groupby("episodeId")[
            "turnAirport"
        ].shift(-1)
        has_next = steps_sorted["_next_turn"].notna()
        terminal_en_route = steps_sorted["stepType"].eq("recovered_en_route")
        path_bad = (
            has_next
            & ~terminal_en_route
            & steps_sorted["nextAirport"].ne(steps_sorted["_next_turn"])
        )
        checks["airport_path_discontinuities"] = int(path_bad.sum())

        if "maxScheduledTurnMinutes" in episodes.columns:
            step_limits = steps_sorted[["episodeId", "plannedTurnMinutes"]].merge(
                episodes[["episodeId", "maxScheduledTurnMinutes"]],
                on="episodeId",
                how="left",
            )
            checks["scheduled_turn_limit_violations"] = int(
                (
                    step_limits["maxScheduledTurnMinutes"].notna()
                    & step_limits["plannedTurnMinutes"].gt(
                        step_limits["maxScheduledTurnMinutes"] + 1e-9
                    )
                ).sum()
            )
        else:
            checks["scheduled_turn_limit_violations"] = 0
    else:
        checks["utc_reversed"] = 0
        checks["recovery_not_continuing"] = 0
        checks["airport_path_discontinuities"] = 0
        checks["scheduled_turn_limit_violations"] = 0

    # Never skip discontinuity boundaries: the frozen hard gate applies to all
    # published episodes sharing a tail number.
    ep_times = episodes[
        ["episodeId", "tailNumber", "observedStartUTC", "endUTC"]
    ].copy()
    ep_times["start"] = pd.to_datetime(
        ep_times["observedStartUTC"], utc=True, errors="coerce"
    )
    ep_times["end"] = pd.to_datetime(ep_times["endUTC"], utc=True, errors="coerce")
    ep_times = ep_times.sort_values(["tailNumber", "start", "episodeId"])
    ep_times["next_start"] = ep_times.groupby("tailNumber")["start"].shift(-1)
    checks["invalid_episode_times"] = int(
        (ep_times["start"].isna() | ep_times["end"].isna()).sum()
    )
    checks["overlapping_episodes"] = int(
        (
            ep_times["end"].notna()
            & ep_times["next_start"].notna()
            & (ep_times["end"] > ep_times["next_start"])
        ).sum()
    )

    return checks


# ── directed link metrics ─────────────────────────────────────────

def build_directed_links(links: pd.DataFrame, threshold: int = 15) -> pd.DataFrame:
    """Aggregate chain edges into directed link metrics.

    Two aggregation levels:
      L1: turnAirport -> nextDestination
      L2: previousOrigin -> turnAirport -> nextDestination
    """
    links = links.copy()
    links["upstream_late"] = links["PrevArrDelay"] >= threshold
    links["downstream_late"] = links["DepDelay"] >= threshold

    def _agg(group: pd.DataFrame, level: str) -> dict:
        n_total = len(group)
        n_upstream_late = group["upstream_late"].sum()
        n_downstream_late = group["downstream_late"].sum()
        n_upl = group.loc[group["upstream_late"]]
        n_prop = int(n_upl["downstream_late"].sum()) if len(n_upl) > 0 else 0
        n_caught = int((n_upl["downstream_late"] & (n_upl["DepDelay"] < n_upl["PrevArrDelay"])).sum()) if len(n_upl) > 0 else 0
        n_persisted = n_prop - n_caught
        n_recovered = int((n_upl["downstream_late"] == False).sum()) if len(n_upl) > 0 else 0  # noqa: E712

        p_given_late = n_prop / n_upstream_late if n_upstream_late > 0 else 0.0
        not_late = group[~group["upstream_late"]]
        n_down_when_not = int(not_late["downstream_late"].sum()) if len(not_late) > 0 else 0
        p_given_not_late = n_down_when_not / len(not_late) if len(not_late) > 0 else 0.0
        cond_diff = p_given_late - p_given_not_late

        delay_delta_series = n_upl["DepDelay"] - n_upl["PrevArrDelay"]
        med_delta = float(delay_delta_series.median()) if len(delay_delta_series) > 0 else 0.0
        mean_delta = float(delay_delta_series.mean()) if len(delay_delta_series) > 0 else 0.0
        p10_delta = float(delay_delta_series.quantile(0.1)) if len(delay_delta_series) > 0 else 0.0
        p90_delta = float(delay_delta_series.quantile(0.9)) if len(delay_delta_series) > 0 else 0.0

        med_turn = float(group["ActualTurnMinutes"].median())
        turn_bins: dict[str, int] = {}
        for label, lo, hi in [("<45", 0, 45), ("45-89", 45, 90), ("90-179", 90, 180), (">=180", 180, 1e9)]:
            turn_bins[label] = int(((group["ActualTurnMinutes"] >= lo) & (group["ActualTurnMinutes"] < hi)).sum())

        # Wilson CI — only compute when n>=5, else null
        ci_lo: float | None = None
        ci_hi: float | None = None
        if n_upstream_late >= 5:
            z = 1.96
            denom = 1 + z**2 / n_upstream_late
            centre = (p_given_late + z**2 / (2 * n_upstream_late)) / denom
            margin = z * np.sqrt(p_given_late * (1 - p_given_late) / n_upstream_late + z**2 / (4 * n_upstream_late**2)) / denom
            ci_lo = max(0.0, centre - margin)
            ci_hi = min(1.0, centre + margin)

        return {
            "level": level,
            "nTotal": n_total,
            "nUpstreamLate": n_upstream_late,
            "nDownstreamLate": n_downstream_late,
            "nPropagated": n_prop,
            "nCaughtUp": n_caught,
            "nPersistedOrAmplified": n_persisted,
            "nRecovered": n_recovered,
            "pPropGivenLate": round(p_given_late, 6),
            "pPropGivenNotLate": round(p_given_not_late, 6),
            "conditionalDiff": round(cond_diff, 6),
            "meanDelayDelta": round(mean_delta, 1),
            "medianDelayDelta": round(med_delta, 1),
            "p10DelayDelta": round(p10_delta, 1),
            "p90DelayDelta": round(p90_delta, 1),
            "medianActualTurnMinutes": round(med_turn, 1),
            "turnBins": turn_bins,
            "wilsonCI_low": round(ci_lo, 6) if ci_lo is not None else None,
            "wilsonCI_high": round(ci_hi, 6) if ci_hi is not None else None,
        }

    l1 = links.groupby(["Origin", "Dest"], sort=False).apply(lambda g: _agg(g, "L1_turn_dest"), include_groups=False)
    l1_df = pd.DataFrame(l1.tolist(), index=l1.index).reset_index()
    l1_df.rename(columns={"Origin": "turnAirport", "Dest": "nextDestination"}, inplace=True)

    l2 = links.groupby(["PrevOrigin", "Origin", "Dest"], sort=False).apply(lambda g: _agg(g, "L2_prev_turn_dest"), include_groups=False)
    l2_df = pd.DataFrame(l2.tolist(), index=l2.index).reset_index()
    l2_df.rename(columns={"PrevOrigin": "previousOrigin", "Origin": "turnAirport", "Dest": "nextDestination"}, inplace=True)

    return pd.concat([l1_df, l2_df], ignore_index=True)


def conditional_lift_stratified(links: pd.DataFrame, threshold: int = 15) -> dict:
    """Stratified conditional lift: within each (turnAirport, depHourBin),
    compare P(next dep late | prev arr late) vs P(next dep late | prev arr not late).
    Only includes strata with BOTH upstream-late and upstream-not-late samples.
    Returns dict with weighted lift and coverage stats."""
    links = links.copy()
    links["upstream_late"] = links["PrevArrDelay"] >= threshold
    links["downstream_late"] = links["DepDelay"] >= threshold
    links["depHour"] = pd.to_datetime(links["ScheduledDepartureUTC"]).dt.hour
    links["depBin"] = (links["depHour"] // 2) * 2

    rows = []
    excluded = 0
    excluded_flights = 0
    for (origin, depBin), g in links.groupby(["Origin", "depBin"], sort=False):
        n_total = len(g)
        n_upl = int(g["upstream_late"].sum())
        n_not_upl = n_total - n_upl
        if n_upl == 0 or n_not_upl == 0:
            excluded += 1
            excluded_flights += n_total
            continue
        n_upl_prop = int(g.loc[g["upstream_late"], "downstream_late"].sum())
        n_not_upl_prop = int(g.loc[~g["upstream_late"], "downstream_late"].sum())
        p_late = n_upl_prop / n_upl
        p_not = n_not_upl_prop / n_not_upl
        lift = p_late - p_not
        rows.append({
            "turnAirport": origin,
            "depHourBin": depBin,
            "nTotal": n_total,
            "nUpstreamLate": n_upl,
            "nNotUpstream": n_not_upl,
            "pLate": round(p_late, 6),
            "pNotLate": round(p_not, 6),
            "conditionalLift": round(lift, 6),
        })

    result_df = pd.DataFrame(rows)
    if len(result_df) > 0:
        weights = result_df["nTotal"].values.astype(float)
        weighted_lift = np.average(result_df["conditionalLift"].values, weights=weights)
    else:
        weighted_lift = 0.0

    total_chain_edges = len(links)
    covered = total_chain_edges - excluded_flights

    return {
        "weightedConditionalLift": round(float(weighted_lift), 6),
        "comparableStrata": len(rows),
        "excludedStrata": excluded,
        "coveredFlightEdges": covered,
        "coverageRate": round(covered / total_chain_edges, 4) if total_chain_edges > 0 else 0.0,
        "strataTable": result_df.to_dict(orient="records") if len(result_df) > 0 else [],
    }


# ── airport role metrics ──────────────────────────────────────────

def build_airport_roles(links: pd.DataFrame, episodes: pd.DataFrame, threshold: int = 15) -> pd.DataFrame:
    """Compute transparent airport mechanism dimensions."""
    links = links.copy()
    links["upstream_late"] = links["PrevArrDelay"] >= threshold
    links["downstream_late"] = links["DepDelay"] >= threshold

    rows = []
    for code, group in links.groupby("Origin", sort=False):
        n_edges = len(group)
        n_exposed = int(group["upstream_late"].sum())
        n_persisted = int(group.loc[group["upstream_late"], "downstream_late"].sum())
        n_recovered = n_exposed - n_persisted
        n_caught = int(group.loc[group["upstream_late"] & group["downstream_late"] & (group["DepDelay"] < group["PrevArrDelay"])].shape[0]) if n_exposed > 0 else 0
        n_amplified = n_persisted - n_caught

        upl = group.loc[group["upstream_late"]]
        delta = upl["DepDelay"] - upl["PrevArrDelay"] if len(upl) > 0 else pd.Series(dtype=float)

        # Deep episode rate
        ep_from_airport = episodes[episodes["observedStartAirport"] == code]
        deep2 = int((ep_from_airport["depth"] >= 2).sum())
        deep3 = int((ep_from_airport["depth"] >= 3).sum())
        total_ep = len(ep_from_airport)

        outgoing = group["Dest"].unique()
        additional_reach = len([d for d in outgoing if d != code])

        rows.append({
            "code": code,
            "nEdges": n_edges,
            "exposureRate": round(n_exposed / n_edges, 4) if n_edges > 0 else 0.0,
            "persistenceRate": round(n_persisted / n_exposed, 4) if n_exposed > 0 else 0.0,
            "recoveryRate": round(n_recovered / n_exposed, 4) if n_exposed > 0 else 0.0,
            "caughtUpRate": round(n_caught / n_exposed, 4) if n_exposed > 0 else 0.0,
            "amplificationRate": round(n_amplified / n_exposed, 4) if n_exposed > 0 else 0.0,
            "medianDelayDelta": round(float(delta.median()), 1) if len(delta) > 0 else 0.0,
            "p90DelayDelta": round(float(delta.quantile(0.9)), 1) if len(delta) > 0 else 0.0,
            "nExposed": n_exposed,
            "nEdges": n_edges,
            "deepEpisodeRate2plus": round(deep2 / total_ep, 4) if total_ep > 0 else 0.0,
            "deepEpisodeRate3plus": round(deep3 / total_ep, 4) if total_ep > 0 else 0.0,
            "outgoingReach": additional_reach,
            "totalEpisodes": total_ep,
        })

    result = pd.DataFrame(rows)
    # Only assign role labels to airports with sufficient sample
    MIN_EXPOSED = 500
    eligible_mask = result["nExposed"] >= MIN_EXPOSED
    result["roleLabel"] = "insufficient_sample"

    if eligible_mask.sum() > 0:
        eligible = result[eligible_mask].copy()
        med_persist = eligible["persistenceRate"].median()
        med_recover = eligible["recoveryRate"].median()
        q75_exposed = eligible["exposureRate"].quantile(0.75)
        q75_reach = eligible["outgoingReach"].quantile(0.75)

        def _role(row: pd.Series) -> str:
            exposed = row["exposureRate"] >= q75_exposed
            persist = row["persistenceRate"] >= med_persist
            recover = row["recoveryRate"] >= med_recover
            hub = row["outgoingReach"] >= q75_reach
            if hub and persist and exposed:
                return "high_persistence_hub"
            if hub and recover and exposed:
                return "high_recovery_hub"
            if exposed and persist:
                return "high_exposure_persistent"
            if exposed and recover:
                return "high_exposure_absorbing"
            if exposed and hub:
                return "high_exposure_hub"
            if persist:
                return "persistent"
            if recover:
                return "absorbing"
            return "reference"

        result.loc[eligible_mask, "roleLabel"] = eligible.apply(_role, axis=1).values
    return result


# ── sensitivity ───────────────────────────────────────────────────

def sensitivity_by_threshold(
    links: pd.DataFrame,
    thresholds: tuple[int, ...] = (15, 30, 60),
) -> pd.DataFrame:
    """Recompute key metrics for each delay threshold."""
    rows = []
    for t in thresholds:
        eps = build_shockwave_episodes(links, threshold=t)
        steps = _v1_steps
        d_links = build_directed_links(links, threshold=t)
        l1 = d_links[d_links["level"] == "L1_turn_dest"]
        rows.append({
            "threshold": t,
            "nEpisodes": len(eps),
            "nDeep2": int((eps["depth"] >= 2).sum()),
            "nDeep3": int((eps["depth"] >= 3).sum()),
            "meanDepth": round(float(eps["depth"].mean()), 2),
            "maxDepth": int(eps["depth"].max()),
            "pRecovered": round(eps["outcome"].eq("recovered").mean(), 4),
            "pCensored": round(eps["outcome"].eq("censored").mean(), 4),
            "nLinksWithLateExposure": int(l1["nUpstreamLate"].sum()),
            "nLinksQualified100": int((l1["nUpstreamLate"] >= 100).sum()),
            "nLinksQualified50": int((l1["nUpstreamLate"] >= 50).sum()),
            "nLinksQualified200": int((l1["nUpstreamLate"] >= 200).sum()),
            "nAirportsExposed500": int((pd.DataFrame(
                build_airport_roles(links, eps, threshold=t)
            )["nExposed"] >= 500).sum()),
        })

    return pd.DataFrame(rows)


def concentration_check(episodes: pd.DataFrame, links: pd.DataFrame, d_links: pd.DataFrame) -> dict:
    """Check whether top episodes/links are dominated by single dates/airlines/tails."""
    eps = episodes[episodes["depth"] >= 2].copy()
    n_eps = len(eps)
    result = {}
    if n_eps > 0:
        result["deepEpisodes"] = {
            "n": n_eps,
            "maxDateShare": round(float(eps["observedStartUTC"].str[:10].value_counts().max() / n_eps), 4),
            "maxTailShare": round(float(eps["tailNumber"].value_counts().max() / n_eps), 4),
        }
    # Top 20 directed links by nUpstreamLate: concentration on exact (turn,dest) pairs
    l1 = d_links[d_links["level"] == "L1_turn_dest"].copy()
    top20 = l1.nlargest(20, "nUpstreamLate") if len(l1) >= 20 else l1
    if len(top20) > 0:
        # Filter chain links to only these exact pairs
        top20_pairs = set(zip(top20["turnAirport"], top20["nextDestination"]))
        pair_edges = links[links.apply(lambda r: (r["Origin"], r["Dest"]) in top20_pairs, axis=1)]
        if len(pair_edges) > 0:
            result["top20Links"] = {
                "uniqueAirports": int(top20[["turnAirport", "nextDestination"]].stack().nunique()),
                "nLinks": int(len(pair_edges)),
                "maxAirlineShare": round(float(
                    pair_edges["Reporting_Airline"].value_counts().max() / len(pair_edges)
                ), 4),
                "maxDateShare": round(float(
                    pair_edges["FlightDate"].value_counts().max() / len(pair_edges)
                ), 4),
                "maxTailShare": round(float(
                    pair_edges["Tail_Number"].value_counts().max() / len(pair_edges)
                ), 4) if len(pair_edges) > 0 else 0.0,
            }
    return result


# ── case candidates ───────────────────────────────────────────────

def select_case_candidates(episodes: pd.DataFrame, links: pd.DataFrame) -> dict:
    """Select representative episode candidates for V1 Shockwave Explorer."""
    eps = episodes.copy()
    candidates: dict[str, list[dict]] = {}

    # Deepest episodes
    deepest = eps.nlargest(5, "depth")
    candidates["deepest"] = deepest[["episodeId", "tailNumber", "depth", "maxDepartureDelay", "observedStartUTC", "observedStartAirport", "outcome"]].to_dict(orient="records")

    # High delay that recovered
    rec = eps[eps["outcome"] == "recovered"]
    high_rec = rec.nlargest(5, "initialArrivalDelay") if len(rec) >= 5 else rec
    candidates["high_delay_but_recovered"] = high_rec[["episodeId", "tailNumber", "depth", "initialArrivalDelay", "observedStartUTC", "observedStartAirport", "outcome"]].to_dict(orient="records")

    # Cross-midnight
    midnight = eps[eps["crossesMidnightUTC"] == True]  # noqa: E712
    mid_candidates = midnight.nlargest(5, "depth") if len(midnight) >= 5 else midnight
    candidates["cross_midnight"] = mid_candidates[["episodeId", "tailNumber", "depth", "observedStartUTC", "observedStartAirport", "outcome"]].to_dict(orient="records")

    # High-pressure day (May 18)
    may18 = eps[eps["observedStartUTC"].astype(str).str.startswith("2026-05-18")]
    may18_cand = may18.nlargest(5, "depth") if len(may18) >= 5 else may18
    candidates["high_pressure_day"] = may18_cand[["episodeId", "tailNumber", "depth", "observedStartUTC", "observedStartAirport", "outcome"]].to_dict(orient="records")

    # Normal day (May 7 = low delay day from v0-data.json)
    may7 = eps[eps["observedStartUTC"].astype(str).str.startswith("2026-05-07")]
    may7_cand = may7.nlargest(5, "depth") if len(may7) >= 5 else may7
    candidates["normal_day"] = may7_cand[["episodeId", "tailNumber", "depth", "observedStartUTC", "observedStartAirport", "outcome"]].to_dict(orient="records")

    # Censored / gap cases
    censored = eps[eps["outcome"] == "censored"]
    rej = censored.head(5) if len(censored) >= 5 else censored
    candidates["rejected_or_censored"] = rej[["episodeId", "tailNumber", "depth", "terminationReason", "observedStartUTC", "observedStartAirport", "outcome"]].to_dict(orient="records")

    return candidates


# ── UI contract builder ───────────────────────────────────────────

def build_ui_contract(
    summary: dict,
    d_links: pd.DataFrame,
    airport_roles: pd.DataFrame,
    episodes: pd.DataFrame,
    candidates: dict,
) -> dict:
    """Build a small, controlled-size UI data contract."""
    l1 = d_links[d_links["level"] == "L1_turn_dest"].copy()
    top20 = l1.nlargest(20, "nUpstreamLate")
    top20_links = top20[["turnAirport", "nextDestination", "nTotal", "nUpstreamLate", "nPropagated", "nRecovered", "pPropGivenLate", "wilsonCI_low", "wilsonCI_high", "conditionalDiff"]].to_dict(orient="records")

    # Top 40 airports by exposure
    roles = airport_roles.nlargest(40, "nExposed")
    top_roles = roles[["code", "exposureRate", "persistenceRate", "recoveryRate", "caughtUpRate", "amplificationRate", "deepEpisodeRate2plus", "outgoingReach", "nExposed", "roleLabel"]].to_dict(orient="records")

    contract = {
        "version": "v1_p0_ui_contract",
        "nationalSummary": summary,
        "recommendedThreshold": 15,
        "recommendedLinkThreshold": 100,
        "top20DirectedLinks": top20_links,
        "airportMechanismDimensions": top_roles,
        "caseCandidates": candidates,
        "fieldNotes": {
            "pPropGivenLate": "P(next dep late | previous arr late)",
            "conditionalDiff": "pPropGivenLate - pPropGivenNotLate (descriptive, not causal)",
            "wilsonCI": "Wilson 95% binomial proportion confidence interval",
            "exposureRate": "Proportion of inbound rotation edges where the previous arrival was late",
            "persistenceRate": "Among late inbound exposures, proportion where next departure was also late",
            "roleLabel": "Rule-based descriptive label, not a causal classification",
        },
        "disclaimer": "All metrics are descriptive. No causal claims. Sample thresholds are data-driven, not universal.",
    }
    return contract
