#!/usr/bin/env python
"""Validate V2-B model math, scientific output, and Gate 1 contract."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "data/processed/v2_b_model_results.json"
FRONTEND = ROOT / "web/app/v2-b-data.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.build_v2b_model import cluster_sandwich_covariance, design, logistic_fit

LEAKAGE = {"DepDelay", "ArrDelay", "ActualDepartureUTC", "ActualTurnMinutes", "LateAircraftDelay", "OfficialLateAircraft", "PropagationSignal", "RecoverySignal", "DownstreamDepDelayed15"}


def load_result():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_gate0_and_gate1_contract():
    data = load_result()
    expected = {
        "60": (90964, 12716, 78248, 0.5827304183705567, 0.5688196503425008),
        "90": (91055, 12743, 78312, 0.5829082633602762, 0.5688655633874757),
    }
    assert data["gate1"] == "GO"
    assert data["scope"]["mechanismAirports"] == 55
    assert data["scope"]["pbi"] == "unavailable"
    for tolerance, values in expected.items():
        gate = data["gate0"][tolerance]
        assert (gate["matched"], gate["adverse"], gate["nonAdverse"]) == values[:3]
        assert np.isclose(gate["adverseRate"], values[3])
        assert np.isclose(gate["nonAdverseRate"], values[4])
        assert gate["retention"] == 1.0
        assert gate["maxWeatherAgeMinutes"] <= int(tolerance)
        assert all(count == 0 for count in gate["missingCovariates"].values())


def test_all_four_models_have_auditable_diagnostics():
    data = load_result()
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    for tolerance in ("60", "90"):
        assert set(data["models"][tolerance]) == {"baseAdjustment", "operatingConditions"}
        for model in data["models"][tolerance].values():
            assert model["converged"] and model["nClusters"] == 31
            assert model["gradientInfinityNorm"] < 1e-5
            assert model["covarianceMethod"] == "CR1 clustered by FlightDate"
            assert model["covarianceFiniteSampleCorrection"] > 1
            assert 0 < model["predictionRange"][0] < model["predictionRange"][1] < 1
            assert model["clusterRobustCI95"][0] < model["standardizedProbabilityDifference"] < model["clusterRobustCI95"][1]
            assert not LEAKAGE.intersection(model["designColumns"])
            assert len(model["designColumns"]) == len(set(model["designColumns"]))
            assert set(model["referenceLevels"]) >= {"airport", "scheduled_hour_utc", "weekday_utc"}


def test_logistic_fixture_has_expected_direction():
    x = np.array([
        [1, 0], [1, 0], [1, 0], [1, 0],
        [1, 1], [1, 1], [1, 1], [1, 1],
    ], dtype=float)
    y = np.array([0, 0, 0, 1, 0, 1, 1, 1], dtype=float)
    clusters = np.array(["a", "a", "b", "b", "c", "c", "d", "d"])
    fitted = logistic_fit(x, y, clusters)
    assert fitted["success"]
    assert fitted["beta"][1] > 0
    p0 = 1 / (1 + np.exp(-fitted["beta"][0]))
    p1 = 1 / (1 + np.exp(-(fitted["beta"][0] + fitted["beta"][1])))
    assert np.isclose(p0, 0.25, atol=1e-8)
    assert np.isclose(p1, 0.75, atol=1e-8)


def test_cluster_covariance_matches_independent_matrix_calculation():
    x = np.array([
        [1, 0], [1, 1], [1, 0], [1, 1],
        [1, 0], [1, 1], [1, 0], [1, 1],
    ], dtype=float)
    y = np.array([0, 1, 0, 0, 1, 1, 0, 1], dtype=float)
    probability = np.array([0.3, 0.6, 0.3, 0.6, 0.3, 0.6, 0.3, 0.6])
    clusters = np.array(["a", "a", "b", "b", "c", "c", "d", "d"])
    actual, correction = cluster_sandwich_covariance(x, y, probability, clusters)

    bread_inv = np.linalg.inv(x.T @ ((probability * (1 - probability))[:, None] * x))
    scores = x * (y - probability)[:, None]
    grouped = np.vstack([scores[clusters == group].sum(axis=0) for group in ("a", "b", "c", "d")])
    expected_correction = (4 / 3) * (7 / 6)
    expected = bread_inv @ (grouped.T @ grouped) @ bread_inv * expected_correction
    assert np.isclose(correction, expected_correction)
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)


def test_design_uses_reference_coding_without_leakage():
    rows = []
    for airport in ("AAA", "BBB"):
        for hour in (8, 9):
            for weekday in (0, 1):
                for airline in ("AA", "BB"):
                    for scheduled_turn in (45, 75):
                        for previous_delay in (20, 70):
                            for adverse in (False, True):
                                rows.append({
                                    "adverse_weather": adverse,
                                    "Origin": airport,
                                    "ScheduledDepartureUTC": pd.Timestamp("2026-05-04", tz="UTC") + pd.Timedelta(days=weekday, hours=hour),
                                    "Reporting_Airline": airline,
                                    "ScheduledTurnMinutes": scheduled_turn,
                                    "PrevArrDelay": previous_delay,
                                })
    matrix, names, references = design(pd.DataFrame(rows), adjusted=True)
    assert matrix.shape[0] == len(rows)
    assert np.linalg.matrix_rank(matrix) == matrix.shape[1]
    assert len(names) == len(set(names))
    assert not LEAKAGE.intersection(names)
    assert references["airport"] == "AAA"
    assert "airport_AAA" not in names and "airport_BBB" in names


def test_frontend_snapshot_is_projection_of_scientific_output():
    scientific = load_result()
    frontend = json.loads(FRONTEND.read_text(encoding="utf-8"))
    assert frontend["version"] == scientific["version"]
    assert frontend["scope"] == scientific["scope"]
    assert frontend["tolerances"] == scientific["models"]
    assert frontend["gate1"] == scientific["gate1"]
