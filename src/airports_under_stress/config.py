from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "reports"

BTS_URL_TEMPLATE = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)


def archive_path(year: int, month: int) -> Path:
    return RAW_DIR / f"bts_on_time_{year}_{month:02d}.zip"


def source_url(year: int, month: int) -> str:
    return BTS_URL_TEMPLATE.format(year=year, month=month)

