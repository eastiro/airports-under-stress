from __future__ import annotations

import hashlib
import os
import shutil
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_zip(path: Path, expected_size: int | None = None) -> bool:
    if not path.exists():
        return False
    if expected_size is not None and path.stat().st_size != expected_size:
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip() is None
    except zipfile.BadZipFile:
        return False


def _download_range(
    url: str,
    start: int,
    end: int,
    output_path: Path,
    retries: int = 5,
) -> Path:
    expected_size = end - start + 1
    if output_path.exists() and output_path.stat().st_size == expected_size:
        return output_path

    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    headers = {"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"}

    for attempt in range(1, retries + 1):
        try:
            with requests.get(
                url,
                headers=headers,
                stream=True,
                timeout=(30, 90),
            ) as response:
                response.raise_for_status()
                if response.status_code != 206:
                    raise RuntimeError(
                        f"Server ignored byte range {start}-{end}: "
                        f"HTTP {response.status_code}"
                    )
                with temporary_path.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=256 * 1024):
                        if chunk:
                            handle.write(chunk)

            if temporary_path.stat().st_size != expected_size:
                raise RuntimeError(
                    f"Range {start}-{end} has {temporary_path.stat().st_size} bytes; "
                    f"expected {expected_size}"
                )
            temporary_path.replace(output_path)
            return output_path
        except (OSError, requests.RequestException, RuntimeError):
            if temporary_path.exists():
                temporary_path.unlink()
            if attempt == retries:
                raise
            time.sleep(min(2 ** attempt, 12))

    raise AssertionError("unreachable")


def download_with_ranges(
    url: str,
    destination: Path,
    workers: int = 24,
) -> dict[str, object]:
    """Download a BTS ZIP with validated parallel byte ranges."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    head = requests.head(url, timeout=(30, 90), allow_redirects=True)
    head.raise_for_status()
    total_bytes = int(head.headers["Content-Length"])
    last_modified = head.headers.get("Last-Modified")

    if validate_zip(destination, total_bytes):
        return {
            "path": str(destination),
            "bytes": total_bytes,
            "sha256": sha256_file(destination),
            "last_modified": last_modified,
            "reused": True,
        }

    parts_dir = destination.parent / f".{destination.name}.parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    worker_count = max(1, min(workers, 32, total_bytes))
    chunk_size = (total_bytes + worker_count - 1) // worker_count
    ranges: list[tuple[int, int, Path]] = []
    for index in range(worker_count):
        start = index * chunk_size
        if start >= total_bytes:
            break
        end = min(start + chunk_size - 1, total_bytes - 1)
        ranges.append((start, end, parts_dir / f"part-{index:03d}"))

    completed = 0
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {
            pool.submit(_download_range, url, start, end, part): (start, end)
            for start, end, part in ranges
        }
        for future in as_completed(futures):
            future.result()
            completed += 1
            print(f"downloaded ranges: {completed}/{len(ranges)}", flush=True)

    assembled = destination.with_suffix(destination.suffix + ".assembling")
    with assembled.open("wb") as output:
        for _, _, part in ranges:
            with part.open("rb") as source:
                shutil.copyfileobj(source, output, length=1024 * 1024)

    if not validate_zip(assembled, total_bytes):
        raise RuntimeError("Downloaded archive failed size or ZIP integrity validation")

    os.replace(assembled, destination)
    shutil.rmtree(parts_dir)
    return {
        "path": str(destination),
        "bytes": total_bytes,
        "sha256": sha256_file(destination),
        "last_modified": last_modified,
        "reused": False,
    }

