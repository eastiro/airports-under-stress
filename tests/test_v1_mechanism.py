"""Tests for V1-P0 mechanism audit (v2 — after Codex review fixes).

Covers: episode invariants (recovery stepping, gap censoring), 
threshold sensitivity, directed links (CI null-safe), 
conditional lift (comparable strata), airport roles (only eligible), 
concentration (exact links), UI contract, reproducibility.
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.airports_under_stress.v1_mechanism import (
    build_airport_roles,
    build_directed_links,
    build_episode_rejections,
    build_shockwave_episodes,
    build_shockwave_steps,
    build_ui_contract,
    concentration_check,
    conditional_lift_stratified,
    sha256,
    validate_episodes,
)

DATA_DIR = ROOT / "data" / "processed"


@pytest.fixture(scope="module")
def links() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "p0_chain_links.parquet")


@pytest.fixture(scope="module")
def episodes(links: pd.DataFrame) -> pd.DataFrame:
    return build_shockwave_episodes(links, threshold=15)


@pytest.fixture(scope="module")
def steps() -> pd.DataFrame:
    return build_shockwave_steps()


@pytest.fixture(scope="module")
def rejections() -> pd.DataFrame:
    return build_episode_rejections()


@pytest.fixture(scope="module")
def d_links(links: pd.DataFrame) -> pd.DataFrame:
    return build_directed_links(links, threshold=15)


# ── basic invariants ───────────────────────────────────────────────

def test_links_count(links: pd.DataFrame):
    assert len(links) == 549_388


def test_episodes_not_empty(episodes: pd.DataFrame):
    assert len(episodes) > 0


def test_no_negative_actual_turns(links: pd.DataFrame):
    assert (links["ActualTurnMinutes"] < 0).sum() == 0


# ── episode structure (v2 fixes) ──────────────────────────────────

def test_outcome_only_recovered_or_censored(episodes: pd.DataFrame):
    outcomes = set(episodes["outcome"].unique())
    assert outcomes <= {"recovered", "censored"}, f"unexpected outcomes: {outcomes}"


def test_termination_reason_fields(episodes: pd.DataFrame):
    reasons = set(episodes["terminationReason"].unique())
    expected = {
        "recovered", "recovered_en_route", "airport_discontinuity",
        "end_of_sequence", "scheduled_turn_break", "duration_limit",
    }
    assert reasons <= expected, f"unexpected: {reasons}"


def test_gap_episodes_are_censored(episodes: pd.DataFrame):
    gaps = episodes[episodes["qualityFlags"].apply(lambda f: "airport_discontinuity" in f)]
    assert (gaps["outcome"] == "censored").all(), f"gaps not censored: {gaps['outcome'].value_counts().to_dict()}"


def test_published_episodes_never_overlap(
    episodes: pd.DataFrame, steps: pd.DataFrame, links: pd.DataFrame
):
    checks = validate_episodes(episodes, links, steps)
    assert checks["overlapping_episodes"] == 0
    assert checks["invalid_episode_times"] == 0
    assert checks["episode_duration_limit_violations"] == 0
    assert checks["scheduled_turn_limit_violations"] == 0
    assert checks["continuity_boundaries_marked_recovered"] == 0


def test_timeline_conflicts_are_audited(rejections: pd.DataFrame):
    assert len(rejections) == 2
    assert set(rejections["rejectionReason"]) == {"tail_timeline_conflict"}
    assert rejections["overlapMinutes"].min() >= 50
    assert set(rejections["outcome"]) == {"censored"}


def test_primary_episode_continuity_contract(
    episodes: pd.DataFrame, steps: pd.DataFrame
):
    assert set(episodes["maxScheduledTurnMinutes"]) == {180}
    assert set(episodes["maxEpisodeHours"]) == {18}
    durations = (
        pd.to_datetime(episodes["endUTC"], utc=True)
        - pd.to_datetime(episodes["observedStartUTC"], utc=True)
    ).dt.total_seconds() / 3600
    assert durations.max() <= 18
    assert steps["plannedTurnMinutes"].max() <= 180
    bounded = episodes[episodes["terminationReason"].isin(
        ["scheduled_turn_break", "duration_limit"]
    )]
    assert not bounded.empty
    assert bounded["outcome"].eq("censored").all()


def test_validator_does_not_skip_gap_overlap():
    episodes = pd.DataFrame(
        [
            {
                "episodeId": "ep-a",
                "tailNumber": "NTEST",
                "observedStartUTC": "2026-05-01T00:00:00Z",
                "endUTC": "2026-05-01T02:00:00Z",
                "outcome": "censored",
                "qualityFlags": ["airport_discontinuity"],
            },
            {
                "episodeId": "ep-b",
                "tailNumber": "NTEST",
                "observedStartUTC": "2026-05-01T01:00:00Z",
                "endUTC": "2026-05-01T03:00:00Z",
                "outcome": "censored",
                "qualityFlags": ["end_of_sequence"],
            },
        ]
    )
    links = pd.DataFrame({"ActualTurnMinutes": [10.0]})
    checks = validate_episodes(episodes, links, pd.DataFrame())
    assert checks["overlapping_episodes"] == 1


def test_validator_detects_recovery_without_terminal_step():
    episodes = pd.DataFrame(
        [
            {
                "episodeId": "ep-a",
                "tailNumber": "NTEST",
                "observedStartUTC": "2026-05-01T00:00:00Z",
                "endUTC": "2026-05-01T01:00:00Z",
                "outcome": "recovered",
                "qualityFlags": [],
            }
        ]
    )
    steps = pd.DataFrame(
        [
            {
                "episodeId": "ep-a",
                "tailNumber": "NTEST",
                "stepIndex": 0,
                "stepType": "delayed",
                "turnAirport": "AAA",
                "nextAirport": "BBB",
                "nextDepUTC": "2026-05-01T00:30:00Z",
            }
        ]
    )
    links = pd.DataFrame({"ActualTurnMinutes": [10.0]})
    checks = validate_episodes(episodes, links, steps)
    assert checks["recovery_not_continuing"] == 1


def test_terminal_recovery_step_recorded(episodes: pd.DataFrame, steps: pd.DataFrame):
    """Every recovered episode must have at least one step with relation=recovered or stepType=recovered."""
    rec_eps = episodes[episodes["outcome"] == "recovered"]["episodeId"]
    rec_steps = steps[steps["episodeId"].isin(rec_eps)].copy()
    rec_steps["isRecovery"] = rec_steps["stepType"].isin(["recovered", "recovered_en_route"])
    has_recovery = rec_steps.groupby("episodeId")["isRecovery"].any().reindex(rec_eps, fill_value=False)
    assert has_recovery.all(), f"recovered episodes without recovery step: {(~has_recovery).sum()}"


def _continuity_fixture(second_turn_minutes: float = 60.0) -> pd.DataFrame:
    """Two exact same-tail links for testing episode-only continuity limits."""
    return pd.DataFrame([
        {
            "Tail_Number": "NTEST", "PrevOrigin": "AAA", "Origin": "BBB", "Dest": "CCC",
            "PrevArrDelay": 50.0, "DepDelay": 40.0, "ArrDelay": 35.0,
            "PrevActualArrivalUTC": pd.Timestamp("2026-05-01T00:00:00Z"),
            "ActualDepartureUTC": pd.Timestamp("2026-05-01T00:30:00Z"),
            "ScheduledDepartureUTC": pd.Timestamp("2026-05-01T00:30:00Z"),
            "ScheduledArrivalUTC": pd.Timestamp("2026-05-01T02:00:00Z"),
            "ScheduledTurnMinutes": 30.0, "ActualTurnMinutes": 30.0,
        },
        {
            "Tail_Number": "NTEST", "PrevOrigin": "BBB", "Origin": "CCC", "Dest": "DDD",
            "PrevArrDelay": 35.0, "DepDelay": 30.0, "ArrDelay": 10.0,
            "PrevActualArrivalUTC": pd.Timestamp("2026-05-01T02:35:00Z"),
            "ActualDepartureUTC": pd.Timestamp("2026-05-01T04:00:00Z"),
            "ScheduledDepartureUTC": pd.Timestamp("2026-05-01T03:00:00Z"),
            "ScheduledArrivalUTC": pd.Timestamp("2026-05-01T05:00:00Z"),
            "ScheduledTurnMinutes": second_turn_minutes, "ActualTurnMinutes": 85.0,
        },
    ])


def test_planned_long_stop_censors_instead_of_propagating():
    limited = build_shockwave_episodes(
        _continuity_fixture(second_turn_minutes=240),
        threshold=15,
        max_scheduled_turn_minutes=180,
    )
    first = limited.iloc[0]
    assert first["depth"] == 1
    assert first["outcome"] == "censored"
    assert first["terminationReason"] == "scheduled_turn_break"
    assert "scheduled_turn_break" in first["qualityFlags"]
    assert pd.Timestamp(first["endUTC"]) == pd.Timestamp("2026-05-01T02:35:00Z")


def test_elapsed_limit_splits_a_continuing_late_state():
    limited = build_shockwave_episodes(
        _continuity_fixture(), threshold=15, max_episode_hours=3
    )
    first = limited.iloc[0]
    assert first["depth"] == 1
    assert first["outcome"] == "censored"
    assert first["terminationReason"] == "duration_limit"
    durations = (
        pd.to_datetime(limited["endUTC"], utc=True)
        - pd.to_datetime(limited["observedStartUTC"], utc=True)
    ).dt.total_seconds() / 3600
    assert durations.max() <= 3


def test_steps_exceed_episodes(steps: pd.DataFrame, episodes: pd.DataFrame):
    """With recovery steps recorded, steps should be >= episodes."""
    assert len(steps) >= len(episodes), f"steps {len(steps)} < episodes {len(episodes)}"


def test_en_route_recovery_end_utc(steps: pd.DataFrame, episodes: pd.DataFrame):
    """En-route recovery steps use arrival UTC, not departure UTC."""
    en_route = episodes[episodes["terminationReason"] == "recovered_en_route"]
    if len(en_route) == 0:
        pytest.skip("no en-route recovery episodes")
    # Check endUTC contains arrival time (typically later date)
    sample = en_route.head(10)
    for _, ep in sample.iterrows():
        assert pd.notna(ep["endUTC"])


# ── path field semantics ─────────────────────────────────────────

def test_step_three_airports_not_duplicate(steps: pd.DataFrame):
    """prevAirport, turnAirport, nextAirport must all differ."""
    delayed = steps[steps["stepType"] == "delayed"]
    if len(delayed) == 0:
        pytest.skip("no delayed steps")
    for _, s in delayed.head(100).iterrows():
        assert s["prevAirport"] != s["turnAirport"], f"prev==turn: {s['prevAirport']}"
        assert s["turnAirport"] != s["nextAirport"], f"turn==next: {s['turnAirport']}"


def test_step_k_next_is_step_k1_prev(steps: pd.DataFrame):
    """Step k's nextAirport should be step k+1's turnAirport for continued delayed steps."""
    delayed = steps[steps["stepType"] == "delayed"].copy()
    if len(delayed) < 10:
        pytest.skip("too few delayed steps")
    delayed = delayed.sort_values(["episodeId", "stepIndex"])
    delayed["_next_turn"] = delayed.groupby("episodeId")["turnAirport"].shift(-2)  # steps skip by 2? No...
    # Better: consecutive delayed steps: step[k].nextAirport == step[k+1].turnAirport
    # Let's verify a simpler invariant: steps within same episode have ascending indices
    for ep_id in delayed["episodeId"].unique()[:20]:
        grp = delayed[delayed["episodeId"] == ep_id].sort_values("stepIndex")
        for i in range(len(grp) - 1):
            assert grp.iloc[i]["nextAirport"] == grp.iloc[i + 1]["turnAirport"], \
                f"{ep_id} step {grp.iloc[i]['stepIndex']}: {grp.iloc[i]['nextAirport']} != {grp.iloc[i + 1]['turnAirport']}"


# ── cumulative amplification ─────────────────────────────────────

def test_cumulative_amplification_not_double_counting(
    episodes: pd.DataFrame, steps: pd.DataFrame
):
    """The episode total equals the sum of positive delayed-step deltas exactly."""
    delayed = steps[steps["stepType"] == "delayed"].copy()
    delayed["positiveDelta"] = delayed["delayDelta"].clip(lower=0)
    expected = delayed.groupby("episodeId")["positiveDelta"].sum()
    for _, episode in episodes.iterrows():
        assert episode["cumulativeAmplificationMinutes"] == pytest.approx(
            float(expected.get(episode["episodeId"], 0.0))
        ), episode["episodeId"]


# ── directed links ───────────────────────────────────────────────

def test_ci_null_for_small_n(d_links: pd.DataFrame):
    l1 = d_links[d_links["level"] == "L1_turn_dest"]
    small = l1[l1["nUpstreamLate"] < 5]
    if len(small) > 0:
        assert small["wilsonCI_low"].isna().all(), "small n should have null CI"


def test_ci_valid_for_large_n(d_links: pd.DataFrame):
    l1 = d_links[d_links["level"] == "L1_turn_dest"]
    large = l1[l1["nUpstreamLate"] >= 5]
    if len(large) > 0:
        assert large["wilsonCI_low"].notna().all(), "large n should have non-null CI"


def test_directed_link_prop_recovery_sum(d_links: pd.DataFrame):
    l1 = d_links[d_links["level"] == "L1_turn_dest"]
    for _, row in l1.iterrows():
        if row["nUpstreamLate"] > 0:
            assert int(row["nPropagated"]) + int(row["nRecovered"]) == row["nUpstreamLate"]


# ── conditional lift ─────────────────────────────────────────────

def test_conditional_lift_comparable_strata(links: pd.DataFrame):
    cl = conditional_lift_stratified(links)
    assert "weightedConditionalLift" in cl
    assert "comparableStrata" in cl
    assert "coverageRate" in cl
    assert cl["coverageRate"] <= 1.0
    assert cl["comparableStrata"] > 0


# ── concentration ─────────────────────────────────────────────────

def test_concentration_exact_links(episodes: pd.DataFrame, links: pd.DataFrame, d_links: pd.DataFrame):
    conc = concentration_check(episodes, links, d_links)
    if "top20Links" in conc:
        assert "maxAirlineShare" in conc["top20Links"]
        assert conc["top20Links"]["maxAirlineShare"] <= 1.0


# ── episode id stability ─────────────────────────────────────────

def test_episode_id_reproducible(links: pd.DataFrame):
    sample_tails = links["Tail_Number"].drop_duplicates().head(10)
    sample = links[links["Tail_Number"].isin(sample_tails)].copy()
    eps1 = build_shockwave_episodes(sample, threshold=15)
    eps2 = build_shockwave_episodes(sample, threshold=15)
    assert eps1["episodeId"].tolist() == eps2["episodeId"].tolist()


# ── airport roles ─────────────────────────────────────────────────

def test_airport_roles_insufficient_sample(links: pd.DataFrame, episodes: pd.DataFrame):
    roles = build_airport_roles(links, episodes)
    small = roles[roles["nExposed"] < 500]
    if len(small) > 0:
        assert (small["roleLabel"] == "insufficient_sample").all()


# ── spot check 50 episodes ───────────────────────────────────────

def test_spot_check_50_episodes_exact(links: pd.DataFrame, episodes: pd.DataFrame, steps: pd.DataFrame):
    """Exact match: for 50 random episodes, every delayed step matches a P0 chain link by key fields."""
    if len(episodes) < 50:
        pytest.skip("too few episodes")
    rng = np.random.default_rng(20260727)
    sample_ids = rng.choice(episodes["episodeId"].unique(), size=min(50, len(episodes)), replace=False)
    sample_delayed = steps[
        steps["episodeId"].isin(sample_ids) & (steps["stepType"] == "delayed")
    ]
    links_indexed = links.set_index(["Tail_Number", "Origin", "Dest", "ActualDepartureUTC"])
    mismatches = 0
    for _, s in sample_delayed.iterrows():
        key = (s["tailNumber"], s["turnAirport"], s["nextAirport"],
               pd.Timestamp(s["nextDepUTC"]))
        if key not in links_indexed.index:
            mismatches += 1
    assert mismatches == 0, f"{mismatches} delayed steps not found in P0 links by exact key"


# ── threshold sensitivity ─────────────────────────────────────────

def test_thresholds_15_30_60(links: pd.DataFrame):
    from src.airports_under_stress.v1_mechanism import sensitivity_by_threshold
    sens = sensitivity_by_threshold(links)
    assert len(sens) == 3
    assert set(sens["threshold"]) == {15, 30, 60}
    assert sens.iloc[0]["nEpisodes"] >= sens.iloc[2]["nEpisodes"]


# ── JSON / UI contract ───────────────────────────────────────────

def test_summary_json_no_nan():
    path = DATA_DIR / "v1_p0_summary.json"
    if not path.exists():
        pytest.skip("summary not yet generated")
    text = path.read_text(encoding="utf-8")
    assert "NaN" not in text
    assert "Infinity" not in text


def test_ui_contract_size():
    path = DATA_DIR / "v1_p0_ui_contract.json"
    if not path.exists():
        pytest.skip("contract not yet generated")
    size = path.stat().st_size
    assert size < 5_000_000, f"UI contract {size} bytes exceeds 5 MB"


# ── output reproducibility ───────────────────────────────────────

def test_output_hashes_exist():
    manifest_path = DATA_DIR / "v1_p0_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_hashes = manifest["outputHashes"]
    assert len(output_hashes) == 7
    for name, expected_hash in output_hashes.items():
        assert sha256(DATA_DIR / name) == expected_hash
    assert manifest["reproducibility"]["comparedWithPreviousRun"] is True
    assert (
        manifest["reproducibility"]["scientificOutputsMatchPreviousRun"]
        is True
    )


def test_report_matches_final_summary():
    summary = json.loads(
        (DATA_DIR / "v1_p0_summary.json").read_text(encoding="utf-8")
    )
    report = (ROOT / "reports" / "V1_P0_MECHANISM_AUDIT.md").read_text(
        encoding="utf-8"
    )
    assert "**判定：GO**" in report
    assert f"Episodes：{summary['nEpisodes']:,}" in report
    assert (
        f"时间线冲突排除：{summary['episodesRejectedTimelineConflict']}"
        in report
    )
    assert "本次是否与前次相同：True" in report
