#!/usr/bin/env python
"""build_v1a_data.py — Generate V1-A frontend JSON from frozen V1-P0 products.

Reads only frozen V1-P0 outputs. Produces a controlled, static JSON
with no dynamic timestamps. Does not let the browser load Parquet.
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.airports_under_stress.v1_mechanism import sha256, write_json_safe

DATA = ROOT / "data" / "processed"
OUT = ROOT / "web" / "app" / "v1-a-data.json"


def main() -> None:
    summary = json.loads((DATA / "v1_p0_summary.json").read_text(encoding="utf-8"))
    d_links = pd.read_parquet(DATA / "v1_p0_directed_links.parquet")
    roles = pd.read_parquet(DATA / "v1_p0_airport_roles.parquet")

    # Only L1 links with n>=100
    l1 = d_links[d_links["level"] == "L1_turn_dest"].copy()
    qualified = l1[l1["nUpstreamLate"] >= 100].copy()

    # High volume: sorted by nUpstreamLate
    high_volume = qualified.nlargest(20, "nUpstreamLate")
    high_volume_links = high_volume[[
        "turnAirport", "nextDestination", "nTotal", "nUpstreamLate",
        "nPropagated", "nRecovered", "pPropGivenLate",
        "wilsonCI_low", "wilsonCI_high", "conditionalDiff"
    ]].to_dict(orient="records")

    # High vulnerability: sorted by Wilson CI lower bound (conservative)
    ci_valid = qualified[qualified["wilsonCI_low"].notna()].copy()
    high_vuln = ci_valid.nlargest(20, "wilsonCI_low")
    high_vulnerability_links = high_vuln[[
        "turnAirport", "nextDestination", "nTotal", "nUpstreamLate",
        "nPropagated", "nRecovered", "pPropGivenLate",
        "wilsonCI_low", "wilsonCI_high", "conditionalDiff"
    ]].to_dict(orient="records")

    # Airport mechanism dimensions: only eligible (nExposed >= 500)
    eligible = roles[roles["nExposed"] >= 500].copy()
    airport_dims = eligible[[
        "code", "exposureRate", "persistenceRate", "recoveryRate",
        "caughtUpRate", "amplificationRate", "medianDelayDelta",
        "p90DelayDelta", "deepEpisodeRate2plus", "deepEpisodeRate3plus",
        "outgoingReach", "nExposed", "nEdges", "totalEpisodes", "roleLabel"
    ]].to_dict(orient="records")

    # Input hashes for traceability
    input_hashes = {
        "v1_p0_summary.json": sha256(DATA / "v1_p0_summary.json"),
        "v1_p0_ui_contract.json": sha256(DATA / "v1_p0_ui_contract.json"),
        "v1_p0_directed_links.parquet": sha256(DATA / "v1_p0_directed_links.parquet"),
        "v1_p0_airport_roles.parquet": sha256(DATA / "v1_p0_airport_roles.parquet"),
    }

    payload = {
        "version": "v1-a-data",
        "nationalSummary": summary,
        "recommendedThreshold": 15,
        "recommendedLinkThreshold": 100,
        "airportMechanismDimensions": airport_dims,
        "highVolumeLinks": high_volume_links,
        "highVulnerabilityLinks": high_vulnerability_links,
        "inputHashes": input_hashes,
        "fieldNotes": {
            "pPropGivenLate": "P(next dep late | previous arr late) — descriptive conditional probability",
            "conditionalDiff": "pPropGivenLate - pPropGivenNotLate — descriptive lift, not causal",
            "wilsonCI": "Wilson 95% binomial proportion CI; null when n<5",
            "exposureRate": "Proportion of inbound rotation edges where previous arrival was late",
            "persistenceRate": "Among late exposures, proportion where next departure was also late",
            "recoveryRate": "Among late exposures, proportion where next departure was on time",
            "roleLabel": "Rule-based descriptive label for eligible airports only; not causal classification",
            "highVolumeLinks": "Top 20 directed links by upstream-late exposure count (n>=100)",
            "highVulnerabilityLinks": "Top 20 directed links by Wilson CI lower bound (conservative high-propagation signal, n>=100)",
        },
        "disclaimer": "All metrics are descriptive observations from BTS May 2026 data. No causal claims. Weather and airport congestion not controlled.",
    }

    write_json_safe(payload, OUT)
    size = OUT.stat().st_size
    print(f"Wrote {OUT} ({size:,} bytes)")
    print(f"  {len(airport_dims)} eligible airports")
    print(f"  {len(high_volume_links)} high-volume links")
    print(f"  {len(high_vulnerability_links)} high-vulnerability links")


if __name__ == "__main__":
    main()
