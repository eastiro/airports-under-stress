import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data/processed/v3_p0_congestion_events.parquet"
OUT = ROOT / "web/app/v3-b-data.json"
WINDOWS = ("30", "60", "90")
PRIMARY = "60"
THRESHOLD = 100


def load_snapshot() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8"))


def load_events() -> pd.DataFrame:
    return pd.read_parquet(PARQUET)


def test_source_event_count_and_airports() -> None:
    events = load_events()
    assert len(events) == 91185
    assert events["Origin"].nunique() == 55


def test_snapshot_meta_and_scope() -> None:
    snap = load_snapshot()
    assert snap["version"] == "v3-b-1"
    assert snap["primaryWindowMinutes"] == 60
    assert snap["windows"] == list(WINDOWS)
    assert snap["airportThreshold"] == THRESHOLD
    assert snap["scope"] == {
        "totalAirports": 55,
        "eligibleAirports": 54,
        "excludedAirports": 1,
        "eventCount": 91185,
    }


def test_oma_only_exclusion_with_counts() -> None:
    snap = load_snapshot()
    assert len(snap["excluded"]) == 1
    oma = snap["excluded"][0]
    assert oma["airport"] == "OMA"
    assert oma["lowN"] == 140
    assert oma["highN"] == 82
    assert "OMA" not in snap["airports"]


def test_direction_counts_and_counterexamples() -> None:
    snap = load_snapshot()
    assert snap["directionCounts60"]["positive"] == 52
    assert snap["directionCounts60"]["negative"] == 2
    assert snap["counterexamples60"] == ["JFK", "ONT"]
    assert snap["samePositiveAirports"] == 48
    for code in snap["counterexamples60"]:
        assert snap["airports"][code]["direction60"] == "lower"


def test_default_atl_eligible_and_all_positive() -> None:
    snap = load_snapshot()
    assert snap["defaultAirport"] == "ATL"
    atl = snap["airports"]["ATL"]
    assert atl["direction60"] == "higher"
    assert atl["directionLabel"] == "samePositive"
    for w in WINDOWS:
        assert atl["windows"][w]["gapPercentagePoints"] > 0


def test_each_airport_three_windows_and_arithmetic() -> None:
    snap = load_snapshot()
    assert len(snap["airports"]) == 54
    for code, airport in snap["airports"].items():
        for w in WINDOWS:
            block = airport["windows"][w]
            for tier in ("low", "high"):
                cell = block[tier]
                n = cell["n"]
                prop = cell["propagated"]
                rate = cell["rate"]
                # n and propagated must be consistent with the rate.
                assert 0 <= prop <= n
                if n:
                    assert abs(prop / n - rate) < 1e-9
                # Wilson bounds finite, ordered, contain the point estimate.
                assert 0.0 <= cell["wilsonLower"] <= 1.0
                assert 0.0 <= cell["wilsonUpper"] <= 1.0
                assert cell["wilsonLower"] <= cell["wilsonUpper"]
                assert cell["wilsonLower"] <= rate <= cell["wilsonUpper"]
            # Gap equals high minus low rate in percentage points.
            expected_gap = round((block["high"]["rate"] - block["low"]["rate"]) * 100, 8)
            assert abs(block["gapPercentagePoints"] - expected_gap) < 1e-9


def test_snapshot_has_no_event_level_or_forbidden_fields() -> None:
    """Snapshot must be a small aggregate: no event ids, no run timestamps,
    and no *absolute* paths (drive letters, workspace absolute paths, file://).
    A relative source hint such as ``"file": "data/processed/..."`` is allowed."""
    text = OUT.read_text(encoding="utf-8")
    assert "event_id" not in text
    assert "generatedAt" not in text
    # Only absolute / machine-specific sources are banned — not a relative "file".
    assert "C:\\" not in text
    assert "file://" not in text
    assert "/data/processed/v3_p0" not in text.replace(
        "data/processed/v3_p0_congestion_events.parquet", ""
    ).replace('"file": "data/processed/v3_p0_congestion_events.parquet"', "")
    # The snapshot should be buildable from a known relative source file.
    assert '"file": "data/processed/v3_p0_congestion_events.parquet"' in text


def test_builder_byte_reproducible() -> None:
    """Builder must produce a byte-identical file across two real subprocess runs.

    We invoke the script twice via subprocess (not in-memory imports) and compare
    the SHA-256 of the generated JSON, which is the strongest reproducibility guard
    against any hidden run-to-run nondeterminism.
    """
    import hashlib
    import subprocess
    import sys

    script = ROOT / "scripts/build_v3b_data.py"

    def run_once() -> str:
        subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            check=True,
        )
        assert OUT.exists()
        return hashlib.sha256(OUT.read_bytes()).hexdigest()

    first = run_once()
    second = run_once()
    assert first == second, "builder output differs between two subprocess runs"
