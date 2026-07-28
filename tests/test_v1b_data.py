"""Tests for the deterministic V1-B curated episode payload."""

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_v1b_data", ROOT / "scripts" / "build_v1b_data.py")
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(module)


@pytest.fixture(scope="module")
def payload():
    """Build the expensive 549k-link payload once for the module."""
    return module.build_payload()


def test_payload_is_curated_finite_and_category_complete(payload):
    assert payload["sourceSummary"] == {"nEpisodes": 50526, "nSteps": 89595}
    assert len(payload["episodes"]) == 12
    assert len({episode["episodeId"] for episode in payload["episodes"]}) == 12
    assert {episode["selectionCategory"] for episode in payload["episodes"]} == set(module.TARGETS)
    assert module.finite(payload)
    assert all(episode["outcome"] != "censored" or episode["steps"][-1]["stateKey"] not in {"recovered", "recovered_en_route"} for episode in payload["episodes"])


def test_threshold_sensitivity_matches_frozen_audit(payload):
    assert payload["version"] == "v1_b_threshold_lab"
    assert payload["availableThresholds"] == [15, 30, 60]
    assert payload["thresholdSensitivity"] == module.AUDITED_SENSITIVITY
    assert payload["episodeContinuity"] == {
        "maxScheduledTurnMinutes": 180,
        "maxDurationHours": 18,
        "sensitivityAudit": "reports/V1_P01_CONTINUITY_AUDIT.md",
    }
    counts = payload["thresholdSensitivity"]
    assert [row["nEpisodes"] for row in counts] == sorted(
        [row["nEpisodes"] for row in counts], reverse=True
    )
    assert [row["nDeep3"] for row in counts] == sorted(
        [row["nDeep3"] for row in counts], reverse=True
    )
    report = (ROOT / "reports" / "V1_P0_MECHANISM_AUDIT.md").read_text(encoding="utf-8")
    for row in counts:
        assert str(row["nEpisodes"]) in report
        assert str(row["nDeep3"]) in report


def test_every_case_is_reclassified_at_all_three_thresholds(payload):
    for episode in payload["episodes"]:
        views = episode["thresholdViews"]
        assert set(views) == {"15", "30", "60"}
        baseline = views["15"]
        assert baseline["qualifies"]
        assert baseline["depth"] == episode["depth"]
        assert baseline["outcome"] == episode["outcome"]
        assert baseline["observationCount"] == len(episode["steps"])

        prior_depth = baseline["depth"]
        for threshold in (30, 60):
            view = views[str(threshold)]
            if episode["initialArrivalDelay"] < threshold:
                assert view["qualifies"] is False
                assert view["outcome"] == "not_qualified"
                assert view["steps"] == []
                assert view["depth"] == 0
            else:
                assert view["qualifies"] is True
                assert view["steps"]
                assert view["depth"] <= prior_depth
                assert view["outcome"] in {"recovered", "censored"}
                assert all(step["stateKey"] in {
                    "amplified", "propagated", "caught_up", "recovered", "recovered_en_route"
                } for step in view["steps"])
                prior_depth = view["depth"]


def test_payload_matches_frozen_episodes_and_exact_links(payload):
    frozen = pd.read_parquet(ROOT / "data" / "processed" / "v1_p0_episodes.parquet").set_index("episodeId")
    steps = pd.read_parquet(ROOT / "data" / "processed" / "v1_p0_steps.parquet")
    for episode in payload["episodes"]:
        source = frozen.loc[episode["episodeId"]]
        assert episode["depth"] == source.depth
        assert episode["outcome"] == source.outcome
        raw_steps = steps[steps.episodeId.eq(episode["episodeId"])].sort_values("stepIndex")
        assert len(raw_steps) == len(episode["steps"])
        assert all(step["sourceLinkMatch"] in {"six_key_exact", "prior_delayed_flight"} for step in episode["steps"])


def test_selection_is_stable_and_json_has_no_dynamic_fields(payload):
    generated_text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    checked_in = json.loads((ROOT / "web" / "app" / "v1-b-data.json").read_text(encoding="utf-8"))
    assert payload == checked_in
    assert "generated" not in generated_text.lower()
    assert "nan" not in generated_text.lower()
    assert "infinity" not in generated_text.lower()


def test_exact_link_rejects_missing_or_duplicate_keys():
    step = pd.Series({"episodeId": "ep", "stepIndex": 0, "stepType": "delayed", "tailNumber": "T", "prevAirport": "A", "turnAirport": "B", "nextAirport": "C", "prevArrUTC": "2026-05-01T00:00:00Z", "nextDepUTC": "2026-05-01T01:00:00Z"})
    with pytest.raises(ValueError, match="No exact"):
        module.source_link_for_step(step, {}, None)
    links = pd.DataFrame([{
        "Tail_Number": "T", "PrevOrigin": "A", "Origin": "B", "Dest": "C",
        "PrevActualArrivalUTC": "2026-05-01T00:00:00Z", "ActualDepartureUTC": "2026-05-01T01:00:00Z",
    }] * 2)
    with pytest.raises(ValueError, match="duplicate"):
        module.build_link_index(links)
