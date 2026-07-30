from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "app" / "v3-a-data.json"
BUILDER = ROOT / "scripts" / "build_v3a_data.py"
WINDOWS = ("30", "60", "90")


def load() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8"))


def test_scope_is_frozen_55_and_91185() -> None:
    data = load()
    assert data["scope"] == {"mechanismAirports": 55, "eventCount": 91185}


def test_three_window_group_sums_equal_91185() -> None:
    data = load()
    for window in WINDOWS:
        g = data["groups"][window]
        assert g["low"]["n"] + g["middle"]["n"] + g["high"]["n"] == 91185


def test_60_minute_low_high_match_frozen_product() -> None:
    data = load()
    g = data["groups"]["60"]
    assert g["low"]["n"] == 26502
    assert round(g["low"]["propagationRate"], 6) == 0.422723
    assert g["high"]["n"] == 20768
    assert round(g["high"]["propagationRate"], 6) == 0.661547


def test_concentration_uses_camelcase_and_matches_frozen() -> None:
    data = load()
    conc = data["concentration"]
    # Frontend V3AData contract: camelCase only.
    assert set(conc.keys()) == {"maxHighAirportShare", "maxHighDayShare"}
    # Frozen values: max_high_airport_share / max_high_day_share.
    assert round(conc["maxHighAirportShare"], 10) == 0.0636556240
    assert round(conc["maxHighDayShare"], 10) == 0.0597553929
    # snake_case keys must not leak into the frontend snapshot.
    raw = OUT.read_text(encoding="utf-8")
    assert "max_high_airport_share" not in raw
    assert "max_high_day_share" not in raw


def test_high_minus_low_is_computed_not_constant() -> None:
    data = load()
    for window in WINDOWS:
        g = data["groups"][window]
        computed = (g["high"]["propagationRate"] - g["low"]["propagationRate"]) * 100
        assert abs(computed - data["highMinusLow"][window]["percentagePoints"]) < 1e-6
    # Distinct across windows proves it is derived, not a single hardcoded constant.
    diffs = {w: data["highMinusLow"][w]["percentagePoints"] for w in WINDOWS}
    assert len({round(v, 4) for v in diffs.values()}) == 3


def test_gate_is_conditional_go_with_oma_82_and_threshold_100() -> None:
    data = load()
    assert data["gateDecision"] == "CONDITIONAL GO"
    gate = data["airportGate"]
    assert gate["minHighN"] == 82
    assert gate["minLowN"] == 112
    assert gate["threshold"] == 100
    assert gate["minHighAirport"] == "OMA"
    assert gate["passed"] is False


def test_snapshot_carries_no_full_events_or_runtime_leakage() -> None:
    raw = OUT.read_text(encoding="utf-8")
    # Schedule-derived event fields must not leak into the frontend snapshot.
    for field in ("Origin", "Dest", "SourceRow", "ScheduledDepartureUTC", "ScheduledArrivalUTC"):
        assert field not in raw
    data = load()
    assert "events" not in data  # never the full event payload
    allowed = {
        "version", "defaultWindowMinutes", "windows", "scope", "plannedMovements",
        "groups", "highMinusLow", "windowSensitivity", "concentration", "airportGate",
        "gateDecision", "interpretationBoundary", "sources",
    }
    assert set(data.keys()) <= allowed


def test_snapshot_is_static_and_byte_reproducible() -> None:
    raw = OUT.read_text(encoding="utf-8")
    assert "generatedAt" not in raw
    assert "\\\\" not in raw
    assert len(hashlib.sha256(raw.encode()).hexdigest()) == 64
    subprocess.run([sys.executable, str(BUILDER)], cwd=ROOT, check=True, capture_output=True)
    first = hashlib.sha256(OUT.read_bytes()).hexdigest()
    subprocess.run([sys.executable, str(BUILDER)], cwd=ROOT, check=True, capture_output=True)
    second = hashlib.sha256(OUT.read_bytes()).hexdigest()
    assert first == second
