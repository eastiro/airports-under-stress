from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from airports_under_stress.config import PROCESSED_DIR, archive_path, source_url
from airports_under_stress.download import download_with_ranges


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and verify one BTS month")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, choices=range(1, 13), required=True)
    parser.add_argument("--workers", type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    url = source_url(args.year, args.month)
    result = download_with_ranges(
        url=url,
        destination=archive_path(args.year, args.month),
        workers=args.workers,
    )
    result["url"] = url
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    metadata_path = PROCESSED_DIR / "source_metadata.json"
    metadata_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

