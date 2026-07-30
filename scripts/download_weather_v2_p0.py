from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from airports_under_stress.weather import IEM_URL, parse_iem_csv, sha256_bytes, station_query


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "weather"
PROCESSED = ROOT / "data" / "processed"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stations",
        default="",
        help="comma-separated station codes; defaults to airports in p0_flights",
    )
    parser.add_argument("--start", default="2026-05-01")
    parser.add_argument("--end", default="2026-06-01")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    flights = pd.read_parquet(PROCESSED / "p0_flights.parquet")
    stations = [value.strip().upper() for value in args.stations.split(",") if value.strip()]
    stations = sorted(set(stations or set(flights["Origin"]) | set(flights["Dest"])))
    params = station_query(stations, args.start, args.end)
    url = IEM_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url, headers={"User-Agent": "airports-under-stress-v2-p0/1.0"}
    )
    with urllib.request.urlopen(request, timeout=args.timeout) as response:
        data = response.read()
        status = response.status

    RAW.mkdir(parents=True, exist_ok=True)
    request_hash = hashlib.sha256(",".join(stations).encode()).hexdigest()[:12]
    raw_path = RAW / f"iem_asos_{args.start}_{args.end}_{request_hash}.csv"
    raw_path.write_bytes(data)
    frame = parse_iem_csv(data)
    metadata = {
        "source": "Iowa State University Environmental Mesonet ASOS/METAR archive",
        "source_url": IEM_URL,
        "request_url": url,
        "request_parameters": params,
        "stations": stations,
        "start": args.start,
        "end_exclusive": args.end,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "http_status": status,
        "response_bytes": len(data),
        "sha256": sha256_bytes(data),
        "rows": len(frame),
    }
    metadata_path = raw_path.with_suffix(".metadata.json")
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "raw": str(raw_path),
                "metadata": str(metadata_path),
                "rows": len(frame),
                "sha256": metadata["sha256"],
                "status": status,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
