from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "app" / "v2-a-data.json"
EXPECTED_INSUFFICIENT = {"MKE", "ONT", "PDX", "PHX", "SJC", "SJU", "SNA"}


def load() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8"))


def test_v2a_gate0_snapshot_and_scope() -> None:
    data = load()
    assert data["scope"] == {
        "coreMappedAirports": 96,
        "coreTotalAirports": 97,
        "episodes": 12,
        "mechanismAirportCodes": data["scope"]["mechanismAirportCodes"],
        "mechanismMappedAirports": 55,
        "mechanismTotalAirports": 55,
        "pbi": "unavailable",
    }
    assert len(data["scope"]["mechanismAirportCodes"]) == 55
    assert data["national"]["90"]["matched"] == 91055
    assert data["national"]["90"]["adverse"]["n"] == 12743
    assert data["national"]["90"]["nonAdverse"]["n"] == 78312
    assert round(data["national"]["90"]["adverse"]["propagationRate"], 6) == 0.582908
    assert round(data["national"]["90"]["nonAdverse"]["propagationRate"], 6) == 0.568866
    assert data["national"]["60"]["matched"] == 90964


def test_airport_eligibility_is_derived_for_both_tolerances() -> None:
    data = load()
    for tolerance in ("60", "90"):
        rows = data["airportComparisons"][tolerance]
        derived = {
            row["airport"] for row in rows
            if row["adverse"]["n"] < 50 or row["nonAdverse"]["n"] < 50
        }
        assert len(rows) == 55
        assert sum(row["comparable"] for row in rows) == 48
        assert derived == EXPECTED_INSUFFICIENT
        assert set(data["insufficientSampleAirportsByTolerance"][tolerance]) == derived


def test_episode_annotations_are_backward_complete_and_two_tolerance() -> None:
    data = load()
    assert len(data["episodeWeather"]) == 12
    allowed_reasons = set(data["sources"]["missingReasons"])
    available_count = 0
    for episode in data["episodeWeather"]:
        assert episode["steps"]
        for step in episode["steps"]:
            for field in ("weatherAtScheduledDeparture", "weatherAtActualArrival"):
                assert set(step[field]) == {"60", "90"}
                for tolerance, note in step[field].items():
                    assert note["toleranceMinutes"] == int(tolerance)
                    if not note["available"]:
                        assert note["reason"] in allowed_reasons
                        continue
                    available_count += 1
                    assert pd.Timestamp(note["observedUTC"]) <= pd.Timestamp(note["eventUTC"])
                    assert 0 <= note["ageMinutes"] <= int(tolerance)
                    assert note["reportType"] in {"METAR", "SPECI", "METAR_OR_SPECI"}
                    assert set(note["values"]) == {
                        "visibilityKm", "ceilingFt", "windSpeedMps", "windGustMps"
                    }
                    assert note["statusKey"] in {"candidate_adverse", "non_adverse"}
    assert available_count > 0


def test_snapshot_is_static_and_byte_reproducible() -> None:
    raw = OUT.read_text(encoding="utf-8")
    assert "generatedAt" not in raw
    assert "\\\\" not in raw
    assert len(hashlib.sha256(raw.encode()).hexdigest()) == 64
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_v2a_data.py")], cwd=ROOT, check=True, capture_output=True)
    first = hashlib.sha256(OUT.read_bytes()).hexdigest()
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_v2a_data.py")], cwd=ROOT, check=True, capture_output=True)
    second = hashlib.sha256(OUT.read_bytes()).hexdigest()
    assert first == second
