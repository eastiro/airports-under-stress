#!/usr/bin/env python
"""Build deterministic V2-B adjusted weather association models."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "v2_b_model_results.json"
FRONTEND_OUT = ROOT / "web" / "app" / "v2-b-data.json"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
from airports_under_stress.weather import backward_join_by_station

TOLERANCES = (60, 90)
EXPECTED_GATE0 = {
    "90": (91055, 12743, 78312, 0.582908, 0.568866),
    "60": (90964, 12716, 78248, 0.582730, 0.568820),
}
LEAKAGE = {"DepDelay", "ArrDelay", "ActualDepartureUTC", "ActualTurnMinutes", "LateAircraftDelay", "OfficialLateAircraft", "PropagationSignal", "RecoverySignal", "DownstreamDepDelayed15"}


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    if pd.isna(value):
        return None
    return value


def cluster_sandwich_covariance(
    x: np.ndarray,
    y: np.ndarray,
    probability: np.ndarray,
    clusters: np.ndarray,
) -> tuple[np.ndarray, float]:
    """CR1 cluster-robust covariance with an explicit finite-sample correction."""
    n, p = x.shape
    unique_clusters = np.sort(pd.unique(clusters))
    g = len(unique_clusters)
    if g <= 1 or n <= p:
        raise ValueError("cluster covariance requires multiple clusters and n > p")
    weights = probability * (1.0 - probability)
    bread_inv = np.linalg.pinv(x.T @ (weights[:, None] * x), rcond=1e-10)
    scores = x * (y - probability)[:, None]
    meat = np.zeros((p, p), dtype=float)
    for cluster in unique_clusters:
        cluster_score = scores[clusters == cluster].sum(axis=0)
        meat += np.outer(cluster_score, cluster_score)
    correction = (g / (g - 1)) * ((n - 1) / (n - p))
    return bread_inv @ meat @ bread_inv * correction, float(correction)


def logistic_fit(x: np.ndarray, y: np.ndarray, clusters: np.ndarray) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n, p = x.shape

    beta = np.zeros(p, dtype=float)
    iterations = 0
    for iterations in range(1, 101):
        eta = np.clip(x @ beta, -35, 35)
        prob = 1.0 / (1.0 + np.exp(-eta))
        grad = x.T @ (prob - y)
        hessian = x.T @ ((prob * (1.0 - prob))[:, None] * x)
        step = np.linalg.pinv(hessian, rcond=1e-10) @ grad
        beta_next = beta - step
        if np.max(np.abs(step)) < 1e-8 and np.linalg.norm(grad, ord=np.inf) < 1e-5:
            beta = beta_next
            break
        beta = beta_next
    else:
        raise ValueError("logistic did not converge within 100 IRLS iterations")
    final_eta = np.clip(x @ beta, -35, 35)
    final_prob = 1.0 / (1.0 + np.exp(-final_eta))
    final_loss = float(np.sum(np.logaddexp(0.0, final_eta) - y * final_eta))
    final_grad = x.T @ (final_prob - y)
    if not np.isfinite(final_loss) or not np.all(np.isfinite(beta)) or np.linalg.norm(final_grad, ord=np.inf) > 1e-5:
        raise ValueError(f"logistic did not converge; gradient={np.linalg.norm(final_grad, ord=np.inf)}")
    covariance, correction = cluster_sandwich_covariance(
        x, y, final_prob, np.asarray(clusters)
    )
    return {
        "success": True,
        "message": "converged",
        "beta": beta,
        "prob": final_prob,
        "covariance": covariance,
        "covarianceCorrection": correction,
        "loss": final_loss,
        "iterations": iterations,
        "gradientInfinityNorm": float(np.linalg.norm(final_grad, ord=np.inf)),
    }


def design(
    frame: pd.DataFrame, adjusted: bool
) -> tuple[np.ndarray, list[str], dict[str, str]]:
    values = pd.DataFrame({
        "adverse_weather": frame["adverse_weather"].astype(int),
        "airport": frame["Origin"].astype(str),
        "scheduled_hour_utc": pd.to_datetime(frame["ScheduledDepartureUTC"], utc=True).dt.hour.astype(str),
        "weekday_utc": pd.to_datetime(frame["ScheduledDepartureUTC"], utc=True).dt.dayofweek.astype(str),
    })
    if adjusted:
        values["airline"] = frame["Reporting_Airline"].astype(str)
        values["scheduled_turn_bin"] = pd.cut(frame["ScheduledTurnMinutes"], [-np.inf, 30, 60, 90, 120, np.inf], labels=["<=30", "31-60", "61-90", "91-120", ">120"], right=True).astype(str)
        values["prev_arr_delay_bin"] = pd.cut(frame["PrevArrDelay"], [15, 30, 60, 120, np.inf], labels=["15-29", "30-59", "60-119", ">=120"], right=False).astype(str)
    parts = [pd.Series(1.0, index=values.index, name="intercept"), values["adverse_weather"]]
    names = ["intercept", "adverse_weather"]
    reference_levels: dict[str, str] = {}
    for column in values.columns[1:]:
        categories = sorted(values[column].unique().tolist())
        reference_levels[column] = str(categories[0])
        categorical = pd.Categorical(values[column], categories=categories)
        dummies = pd.get_dummies(categorical, prefix=column, dtype=float)
        dummies.index = values.index
        dummies = dummies.iloc[:, 1:]
        parts.append(dummies)
        names.extend(dummies.columns.tolist())
    matrix = pd.concat(parts, axis=1).to_numpy(dtype=float)
    if np.linalg.matrix_rank(matrix) != matrix.shape[1] or np.any(np.all(matrix == 0, axis=0)):
        raise ValueError("design matrix is rank deficient or contains an empty column")
    return matrix, names, reference_levels


def summarize_model(frame: pd.DataFrame, adjusted: bool) -> dict[str, Any]:
    matrix, names, reference_levels = design(frame, adjusted)
    y = frame["DownstreamDepDelayed15"].astype(float).to_numpy()
    clusters = frame["FlightDate"].dt.strftime("%Y-%m-%d").to_numpy()
    fitted = logistic_fit(matrix, y, clusters)
    if not fitted["success"] or not np.isfinite(fitted["loss"]) or not np.all(np.isfinite(fitted["beta"])):
        raise ValueError(f"logistic did not converge: {fitted['message']}")
    adverse_index = names.index("adverse_weather")
    x1, x0 = matrix.copy(), matrix.copy()
    x1[:, adverse_index] = 1.0
    x0[:, adverse_index] = 0.0
    p1 = 1 / (1 + np.exp(-np.clip(x1 @ fitted["beta"], -35, 35)))
    p0 = 1 / (1 + np.exp(-np.clip(x0 @ fitted["beta"], -35, 35)))
    diff = float(np.mean(p1 - p0))
    derivative = np.mean(p1[:, None] * (1 - p1[:, None]) * x1 - p0[:, None] * (1 - p0[:, None]) * x0, axis=0)
    se = float(np.sqrt(max(0.0, derivative @ fitted["covariance"] @ derivative)))
    ci = [diff - 1.959963984540054 * se, diff + 1.959963984540054 * se]
    odds = float(np.exp(np.clip(fitted["beta"][adverse_index], -30, 30)))
    return {
        "specification": "operating_conditions" if adjusted else "base_adjustment",
        "nRows": len(frame), "nParameters": matrix.shape[1], "nClusters": len(set(clusters)),
        "iterations": fitted["iterations"], "loss": round(fitted["loss"], 8),
        "converged": True, "adverseCoefficient": round(float(fitted["beta"][adverse_index]), 8),
        "adverseOddsRatio": round(odds, 8), "standardizedProbabilityDifference": round(diff, 8),
        "standardizedProbabilityDifferencePercentagePoints": round(diff * 100, 8),
        "clusterRobustSE": round(se, 8), "clusterRobustCI95": [round(v, 8) for v in ci],
        "covarianceMethod": "CR1 clustered by FlightDate",
        "covarianceFiniteSampleCorrection": round(fitted["covarianceCorrection"], 8),
        "gradientInfinityNorm": fitted["gradientInfinityNorm"],
        "predictionRange": [round(float(min(p1.min(), p0.min())), 8), round(float(max(p1.max(), p0.max())), 8)],
        "designColumns": names,
        "referenceLevels": reference_levels,
    }


def main() -> None:
    links = pd.read_parquet(DATA / "p0_chain_links.parquet")
    roles = pd.read_parquet(DATA / "v1_p0_airport_roles.parquet")
    observations = pd.read_parquet(DATA / "v2_p0_weather_observations.parquet")
    mechanism = sorted(set(roles.loc[roles["nExposed"] >= 500, "code"]))
    base = links[links["UpstreamArrDelayed15"].eq(True) & links["Origin"].isin(mechanism)].copy()
    base = base.reset_index(drop=True)
    base["_event_id"] = np.arange(len(base), dtype=np.int64)
    events = base[["_event_id", "Origin", "ScheduledDepartureUTC", "DownstreamDepDelayed15"]].rename(columns={"Origin": "airport_code", "ScheduledDepartureUTC": "event_utc"})
    usable = observations[observations["usable_for_exposure"].eq(True) & observations["airport_code"].notna()].copy()
    usable["valid_utc"] = pd.to_datetime(usable["valid_utc"], utc=True)
    gate0, models = {}, {}
    for tolerance in TOLERANCES:
        joined = backward_join_by_station(events, usable, station_col="airport_code", time_col="event_utc", tolerance_minutes=tolerance)
        joined = joined[joined["weather_age_minutes"].notna()].copy()
        joined["adverse_weather"] = joined["adverse_weather"].astype(bool)
        adverse = joined[joined.adverse_weather]
        non = joined[~joined.adverse_weather]
        observed = (len(joined), len(adverse), len(non), float(adverse.DownstreamDepDelayed15.mean()), float(non.DownstreamDepDelayed15.mean()))
        expected = EXPECTED_GATE0[str(tolerance)]
        if observed[:3] != expected[:3] or not np.allclose(observed[3:], expected[3:], atol=1e-7):
            raise ValueError(f"Gate 0 mismatch for {tolerance}: {observed} != {expected}")
        if joined["weather_age_minutes"].lt(0).any():
            raise ValueError("future weather report detected")
        if joined["weather_age_minutes"].gt(tolerance).any():
            raise ValueError("weather report exceeds matching tolerance")
        frame = joined.merge(base[["_event_id", "Reporting_Airline", "ScheduledTurnMinutes", "PrevArrDelay", "FlightDate"]], on="_event_id", how="left", validate="one_to_one")
        frame["Origin"] = frame["airport_code"]
        frame["ScheduledDepartureUTC"] = frame["event_utc"]
        missing = {field: int(frame[field].isna().sum()) for field in ["Reporting_Airline", "ScheduledTurnMinutes", "PrevArrDelay", "FlightDate"]}
        frame = frame.dropna(subset=["Reporting_Airline", "ScheduledTurnMinutes", "PrevArrDelay", "FlightDate"]).copy()
        retained = len(frame) / len(joined)
        if retained < 0.95:
            raise ValueError(f"retention below 95%: {retained}")
        gate0[str(tolerance)] = {"matched": len(joined), "adverse": len(adverse), "nonAdverse": len(non), "adverseRate": observed[3], "nonAdverseRate": observed[4], "analysisRows": len(frame), "retention": retained, "missingCovariates": missing, "maxWeatherAgeMinutes": float(joined.weather_age_minutes.max())}
        models[str(tolerance)] = {"baseAdjustment": summarize_model(frame, False), "operatingConditions": summarize_model(frame, True)}
    output = {"version": "v2-b-1", "scope": {"mechanismAirports": len(mechanism), "mechanismAirportCodes": mechanism, "pbi": "unavailable"}, "gate0": gate0, "models": models, "leakageFieldsExcluded": sorted(LEAKAGE), "deterministic": True, "gate1": "GO"}
    OUT.write_text(json.dumps(clean(output), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    frontend = {
        "version": output["version"],
        "scope": output["scope"],
        "tolerances": output["models"],
        "gate1": output["gate1"],
        "disclaimer": "Adjusted descriptive association; not causal attribution or prediction.",
    }
    FRONTEND_OUT.write_text(
        json.dumps(clean(frontend), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(OUT), "gate0": gate0, "models": models}, ensure_ascii=False))


if __name__ == "__main__":
    main()
