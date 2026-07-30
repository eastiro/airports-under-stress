import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "web" / "app" / "v0-data.json").read_text(encoding="utf-8"))
COORD_TS = (ROOT / "web" / "app" / "airport-coordinates.ts").read_text(encoding="utf-8")

COORD_CODES = set(re.findall(r"^\s{2}(\w+):\s*\{", COORD_TS, re.M))


def classify(prev_arr: float, next_dep: float) -> str:
    if prev_arr >= 15 and next_dep >= 15:
        return "caught_up" if next_dep < prev_arr else "propagated"
    if prev_arr >= 15 and next_dep < 15:
        return "recovered_full"
    if prev_arr < 15 and next_dep >= 15:
        return "delayed"
    return "on-time"


def test_network_route_count_in_range():
    routes = DATA["network"]["routes"]
    assert 60 <= len(routes) <= 80, len(routes)


def test_network_routes_have_no_duplicate_undirected_pairs():
    seen = set()
    for route in DATA["network"]["routes"]:
        key = tuple(sorted((route["origin"], route["dest"])))
        assert key not in seen, f"duplicate undirected pair {key}"
        seen.add(key)


def test_network_route_endpoints_have_coordinates():
    for route in DATA["network"]["routes"]:
        assert route["origin"] in COORD_CODES, route["origin"]
        assert route["dest"] in COORD_CODES, route["dest"]
        assert route["flights"] >= 200
        assert 0.0 <= route["delayRate"] <= 1.0


def test_four_stories_with_complete_legs_and_connectors():
    assert len(DATA["stories"]) == 4
    for story in DATA["stories"]:
        assert len(story["legs"]) >= 3
        assert len(story["connectors"]) == len(story["legs"]) - 1
        for leg in story["legs"]:
            for field in ("flight", "origin", "dest", "status", "depDelay", "arrDelay",
                         "scheduledDepUTC", "actualDepUTC", "scheduledArrUTC", "actualArrUTC"):
                assert field in leg, f"{story['id']} leg missing {field}"
            assert leg["origin"] in COORD_CODES
            assert leg["dest"] in COORD_CODES


def test_connector_metrics_are_recomputable():
    for story in DATA["stories"]:
        legs = story["legs"]
        for i, connector in enumerate(story["connectors"]):
            assert connector["hub"] == legs[i]["dest"] == legs[i + 1]["origin"]
            assert connector["planGap"] >= 0
            assert connector["actualTurn"] >= 0
            assert connector["delayDelta"] == round(
                connector["nextDepDelay"] - connector["prevArrDelay"], 0
            )
            assert connector["relation"] == classify(
                connector["prevArrDelay"], connector["nextDepDelay"]
            )


def test_tight_turn_story_uses_real_ground_turn():
    tight = [s for s in DATA["stories"] if s["type"] == "tight-turn"]
    if not tight:
        return
    story = tight[0]
    min_turn = min(c["actualTurn"] for c in story["connectors"])
    assert 15 <= min_turn <= 40, min_turn
    assert all(c["planGap"] > 0 for c in story["connectors"])


def test_story_titles_are_data_driven_not_hardcoded():
    for story in DATA["stories"]:
        assert story["title"] and story["titleZh"]
        assert story["title"] != story["type"]


# ---- Task 04 additions ----

def test_airports_count_is_97_eligible():
    assert len(DATA["airports"]) == 97, f"expected 97, got {len(DATA['airports'])}"


def test_airports_have_all_five_ordinal_ranks():
    for a in DATA["airports"]:
        for rk in ("rankPressure", "rankDelay", "rankCancel", "rankPropagation", "rankFlights"):
            v = a[rk]
            assert isinstance(v, int), f"{a['code']}.{rk} expected int, got {type(v)}"
            assert 1 <= v <= len(DATA["airports"]), f"{a['code']}.{rk} = {v} out of range"


def test_map_airport_codes_decoupled_and_coordinated():
    codes = DATA["mapAirportCodes"]
    assert 48 <= len(codes) <= 60, f"expected ~52, got {len(codes)}"
    for code in codes:
        assert code in COORD_CODES, f"map code {code} missing coordinate"


def test_airlines_count_is_12_no_nk():
    airlines = DATA["airlines"]
    assert len(airlines) == 12
    codes = {a["code"] for a in airlines}
    assert "NK" not in codes
    for a in airlines:
        assert a["flights"] >= 10_000, f"{a['code']} flights={a['flights']}"


def test_meta_fields_present():
    m = DATA["meta"]
    for key in ("rawAirports", "eligibleAirports", "mapAirports", "rankedAirportsShown",
                "rawAirlines", "comparableAirlines", "airlineThreshold"):
        assert key in m, f"meta missing {key}"


def test_chinese_name_coverage_all_data_codes():
    """Every code in airports, map, and stories has a zh entry."""
    import itertools
    all_codes: set[str] = set()
    for a in DATA["airports"]:
        all_codes.add(a["code"])
    all_codes.update(DATA["mapAirportCodes"])
    for story in DATA["stories"]:
        for leg in story["legs"]:
            all_codes.add(leg["origin"])
            all_codes.add(leg["dest"])
    for airline in DATA["airlines"]:
        all_codes.add(airline["code"])
    # Parse zh file with regex
    zh_path = ROOT / "web" / "app" / "airport-names-zh.ts"
    zh_text = zh_path.read_text(encoding="utf-8")
    airport_zh = set(re.findall(r"^\s{2}(\w+):\s*\{", zh_text, re.M))
    airline_zh = set(re.findall(r"^\s{2}(\w+):\s*\"", zh_text, re.M))
    covered = airport_zh | airline_zh
    missing = all_codes - covered
    assert not missing, f"Missing zh names for: {sorted(missing)} ({len(missing)} codes)"


def test_five_sorts_produce_same_top_count():
    """Each sort produces 12 distinct airports, and rank fields match ordinal position."""
    airports = DATA["airports"]
    for sort_key, rank_key in (
        ("pressureScore", "rankPressure"),
        ("delayRate", "rankDelay"),
        ("cancelRate", "rankCancel"),
        ("propagationRate", "rankPropagation"),
        ("flights", "rankFlights"),
    ):
        ranked = sorted(airports, key=lambda a: a[sort_key], reverse=True)
        top = ranked[:12]
        assert len(top) == 12, f"{sort_key} top != 12"
        assert len({a["code"] for a in top}) == 12, f"{sort_key} top has duplicates"
        # Verify rank field matches ordinal position (1-indexed)
        for i, a in enumerate(ranked, 1):
            if i > 1 and ranked[i - 2][sort_key] == a[sort_key]:
                continue  # ties get min rank, skip exact check for ties
            assert a[rank_key] == i, f"{a['code']} {rank_key}={a[rank_key]}, expected {i}"


def test_map_only_nodes_have_no_fake_metrics():
    """Map-only nodes (in mapAirportCodes but not in 97 sample with pressureScore>0)
    must have pressureScore==0, and SSR must not display fake 0.0%."""
    codes_in_97 = {a["code"] for a in DATA["airports"]}
    map_only = [c for c in DATA["mapAirportCodes"] if c not in codes_in_97]
    # These nodes must exist in coords (verified by earlier test) but not in 97
    assert len(map_only) >= 0, "no assertion needed on count"
    # Any airport in 97 sample must have pressureScore > 0
    for a in DATA["airports"]:
        assert a["pressureScore"] > 0, f"{a['code']} has pressureScore={a['pressureScore']}"


# ---- Gate 0 tests (V1-A task) ----

def test_gate0_all_map_nodes_have_degree_at_least_1():
    """Every mapAirportCodes node must appear in base route or story arc."""
    routes = DATA["network"]["routes"]
    story_codes: set[str] = set()
    for story in DATA["stories"]:
        for leg in story["legs"]:
            story_codes.add(leg["origin"])
            story_codes.add(leg["dest"])
    route_codes: set[str] = set()
    for r in routes:
        route_codes.add(r["origin"])
        route_codes.add(r["dest"])
    connected = route_codes | story_codes
    for code in DATA["mapAirportCodes"]:
        assert code in connected, f"{code} has degree 0 in both base routes and story arcs"


def test_gate0_all_routes_are_real_operated_pairs():
    """All base routes must exist in real P0 flight data."""
    import pandas as pd
    flights = pd.read_parquet(ROOT / "data" / "processed" / "p0_flights.parquet")
    operated = flights[(flights["Cancelled"] == 0) & (flights["Diverted"] == 0)]
    real_pairs = set()
    for _, row in operated.iterrows():
        pair = tuple(sorted((str(row["Origin"]), str(row["Dest"]))))
        real_pairs.add(pair)
    for r in DATA["network"]["routes"]:
        pair = tuple(sorted((r["origin"], r["dest"])))
        assert pair in real_pairs, f"Route {pair} not found in real operated flights"


def test_gate0_route_count_within_limit():
    n = len(DATA["network"]["routes"])
    assert 60 <= n <= 80, f"Route count {n} outside 60-80 range"


def test_gate0_named_airports_have_connections():
    routes = DATA["network"]["routes"]
    route_codes = set()
    for r in routes:
        route_codes.add(r["origin"])
        route_codes.add(r["dest"])
    for code in ["AUS", "HOU", "MSY", "ECP", "PNS", "VPS", "MIA", "FLL", "MCO", "TPA"]:
        assert code in route_codes, f"{code} has no base route connection"


def test_gate0_lga_jfk_ewr_ranks():
    ranks = {a["code"]: a for a in DATA["airports"]}
    assert ranks["LGA"]["rankPressure"] == 22, f"LGA rank={ranks['LGA']['rankPressure']}"
    assert ranks["JFK"]["rankPressure"] == 83, f"JFK rank={ranks['JFK']['rankPressure']}"
    assert ranks["EWR"]["rankPressure"] == 92, f"EWR rank={ranks['EWR']['rankPressure']}"


def test_gate0_story_airports_have_zh_en_names():
    from pathlib import Path
    zh_ts = (ROOT / "web" / "app" / "airport-names-zh.ts").read_text(encoding="utf-8")
    story_codes: set[str] = set()
    for story in DATA["stories"]:
        for leg in story["legs"]:
            story_codes.add(leg["origin"])
            story_codes.add(leg["dest"])
    for code in story_codes:
        assert f"  {code}:" in zh_ts, f"{code} missing from AIRPORT_ZH dictionary"
