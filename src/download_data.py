"""
Step 1 — Download the raw DOHMH Restaurant Inspection Results dataset.

Pulls the full CSV from NYC Open Data and saves it under data/raw/.
The raw file is large and re-downloadable, so it is git-ignored.

Run:
    python src/download_data.py
"""

import sys
import time
import urllib.request
from pathlib import Path

# NYC Open Data export endpoint for dataset 43nn-pn8j (full CSV).
DATA_URL = (
    "https://data.cityofnewyork.us/api/views/43nn-pn8j/rows.csv"
    "?accessType=DOWNLOAD"
)

# Resolve paths relative to the repo root (this file lives in src/).
REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_PATH = RAW_DIR / "dohmh_restaurant_inspections.csv"


def _report_progress(block_num, block_size, total_size):
    """Lightweight progress printer for urlretrieve."""
    downloaded = block_num * block_size
    mb = downloaded / (1024 * 1024)
    if total_size > 0:
        pct = min(downloaded / total_size * 100, 100)
        print(f"\r  downloaded {mb:8.1f} MB ({pct:5.1f}%)", end="", flush=True)
    else:
        # NYC's endpoint often does not send Content-Length.
        print(f"\r  downloaded {mb:8.1f} MB", end="", flush=True)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if OUT_PATH.exists():
        size_mb = OUT_PATH.stat().st_size / (1024 * 1024)
        print(f"Already present: {OUT_PATH} ({size_mb:.1f} MB)")
        print("Delete it and re-run if you want a fresh copy.")
        return

    print(f"Downloading DOHMH inspections from:\n  {DATA_URL}")
    print(f"Saving to:\n  {OUT_PATH}\n")

    start = time.time()
    # Write to a temp file first, then rename, so an interrupted download
    # never leaves a half-written file that looks complete.
    tmp_path = OUT_PATH.with_suffix(".csv.part")
    try:
        urllib.request.urlretrieve(DATA_URL, tmp_path, _report_progress)
    except Exception as exc:  # noqa: BLE001 - surface any download failure
        print(f"\nDownload failed: {exc}", file=sys.stderr)
        if tmp_path.exists():
            tmp_path.unlink()
        sys.exit(1)

    tmp_path.replace(OUT_PATH)
    elapsed = time.time() - start
    size_mb = OUT_PATH.stat().st_size / (1024 * 1024)
    print(f"\n\nDone: {size_mb:.1f} MB in {elapsed:.0f}s -> {OUT_PATH}")


if __name__ == "__main__":
    main()
