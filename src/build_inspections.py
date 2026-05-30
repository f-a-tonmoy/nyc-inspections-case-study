"""
Step — collapse the violation-grain raw CSV into one row per INSPECTION.

The raw file is one row per violation, so a single inspection (one CAMIS on
one INSPECTION DATE) spans many rows. Every downstream analysis works at
inspection grain, so we build it ONCE and persist it.

Outputs:
    data/processed/inspections.parquet   typed, compact, fast to reload
    data/processed/inspections_sample.csv  200-row peek for eyeballing

Run:
    conda run -n intro_ds python src/build_inspections.py

Design choices (worth understanding):
- The raw file contains EXACT duplicate violation rows (we observed an
  inspection with 12 violation codes each listed twice = 24 rows). We dedup
  on (CAMIS, INSPECTION DATE, VIOLATION CODE) before counting.
- GRADE can occasionally differ across rows of the same inspection. We take
  the MODE (most common non-blank value) so each inspection gets one answer.
- We DROP the 01/01/1900 placeholder rows (3,434 registered-but-never-
  inspected establishments). They aren't inspections.
- Categorical dtypes (BORO, ACTION, GRADE, etc.) shrink the parquet a lot.
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_CSV   = REPO_ROOT / "data" / "raw" / "dohmh_restaurant_inspections.csv"
OUT_DIR   = REPO_ROOT / "data" / "processed"
OUT_PQT   = OUT_DIR / "inspections.parquet"
OUT_SMPL  = OUT_DIR / "inspections_sample.csv"

PLACEHOLDER_DATE = "01/01/1900"

# Closure ACTIONs we boolean-flag for convenience. We match by prefix because
# the "Closed by DOHMH" string is very long.
CLOSED_PREFIX   = "Establishment Closed by DOHMH"
REOPENED_EXACT  = "Establishment re-opened by DOHMH."
RECLOSED_EXACT  = "Establishment re-closed by DOHMH."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def first_nonblank(series: pd.Series) -> str:
    """Return the first non-empty value, or '' if all are empty."""
    nb = series[series.ne("")]
    return nb.iloc[0] if len(nb) else ""


def mode_nonblank(series: pd.Series) -> str:
    """Return the most common non-empty value (ties broken by first seen)."""
    nb = series[series.ne("")]
    if not len(nb):
        return ""
    m = nb.mode()
    return m.iloc[0] if len(m) else ""


def to_float_with_zero_nan(series: pd.Series) -> pd.Series:
    """Coerce to float; treat blank AND literal 0 / 0.0... as NaN.

    DOHMH uses '0' as 'unknown' for lat/long — keeping it as 0.0 would put
    those restaurants on Null Island in any map. NaN is the honest value.
    """
    s = pd.to_numeric(series, errors="coerce")
    s = s.where(~(s == 0), np.nan)
    return s


def to_date(series: pd.Series) -> pd.Series:
    """Parse DOHMH's m/d/Y string dates; bad values -> NaT."""
    return pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def main():
    if not RAW_CSV.exists():
        print(f"ERROR: raw file not found at {RAW_CSV}", file=sys.stderr)
        print("Run src/download_data.py first.", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading {RAW_CSV} as strings...")
    raw = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False)
    raw = raw.apply(lambda c: c.str.strip())
    print(f"  raw rows (violation grain): {len(raw):,}")

    # 1) Drop the 01/01/1900 placeholder rows — they aren't inspections.
    real = raw[raw["INSPECTION DATE"] != PLACEHOLDER_DATE].copy()
    print(f"  after dropping {PLACEHOLDER_DATE} placeholder: {len(real):,}")

    # 2) Add typed copies of the columns we'll need numerically/temporally.
    real["_date"]  = to_date(real["INSPECTION DATE"])
    real["_score"] = pd.to_numeric(real["SCORE"], errors="coerce")
    real["_lat"]   = to_float_with_zero_nan(real["Latitude"])
    real["_lon"]   = to_float_with_zero_nan(real["Longitude"])

    # Pre-dedupe (CAMIS, _date, VIOLATION CODE) for honest violation COUNTS.
    # We still keep the full table for inspection-level aggregations because
    # the inspection-level columns are identical across the duplicate rows.
    dedup_violations = real.drop_duplicates(
        subset=["CAMIS", "_date", "VIOLATION CODE"]
    )
    print(f"  rows after deduping exact-duplicate violations: "
          f"{len(dedup_violations):,}")

    # 3) Aggregate to one row per (CAMIS, _date).
    #
    # NamedAgg lets us name and compute every output column in one .agg call.
    # Inspection-level fields use first_nonblank (constant across the group
    # in practice); GRADE/SCORE/ACTION use mode in case they ever disagree.
    print("Aggregating to inspection grain...")
    insp = real.groupby(["CAMIS", "_date"], as_index=False).agg(
        # --- restaurant attributes (constant per inspection) -----------------
        dba                 = ("DBA",                 first_nonblank),
        boro                = ("BORO",                first_nonblank),
        building            = ("BUILDING",            first_nonblank),
        street              = ("STREET",              first_nonblank),
        zipcode             = ("ZIPCODE",             first_nonblank),
        phone               = ("PHONE",               first_nonblank),
        cuisine_description = ("CUISINE DESCRIPTION", first_nonblank),
        # --- inspection-level fields (mode for the few that can vary) -------
        action              = ("ACTION",              mode_nonblank),
        inspection_type     = ("INSPECTION TYPE",     mode_nonblank),
        grade               = ("GRADE",               mode_nonblank),
        grade_date_str      = ("GRADE DATE",          first_nonblank),
        score               = ("_score",              "max"),  # constant; max ignores NaN
        # --- geography (already in the file — no spatial join needed) -------
        latitude            = ("_lat",                "first"),
        longitude           = ("_lon",                "first"),
        community_board     = ("Community Board",     first_nonblank),
        council_district    = ("Council District",    first_nonblank),
        census_tract        = ("Census Tract",        first_nonblank),
        bin_num             = ("BIN",                 first_nonblank),
        bbl                 = ("BBL",                 first_nonblank),
        nta                 = ("NTA",                 first_nonblank),
    )

    # 4) Violation counts come from the DEDUPED frame.
    counts = (
        dedup_violations.assign(
            _is_critical=lambda d: d["CRITICAL FLAG"].eq("Critical").astype("int16")
        )
        .groupby(["CAMIS", "_date"], as_index=False)
        .agg(
            n_violations    = ("VIOLATION CODE", "count"),
            n_critical      = ("_is_critical",   "sum"),
            violation_codes = ("VIOLATION CODE",
                               lambda s: ",".join(sorted(s[s.ne("")].unique()))),
        )
    )
    insp = insp.merge(counts, on=["CAMIS", "_date"], how="left")

    # 5) Rename _date -> inspection_date, and add convenience boolean flags.
    insp = insp.rename(columns={"_date": "inspection_date"})
    insp["closed"]   = insp["action"].str.startswith(CLOSED_PREFIX, na=False)
    insp["reopened"] = insp["action"].eq(REOPENED_EXACT)
    insp["reclosed"] = insp["action"].eq(RECLOSED_EXACT)

    # 6) Final typing: dates parsed, categoricals for repeating strings.
    insp["grade_date"] = to_date(insp["grade_date_str"])
    insp = insp.drop(columns=["grade_date_str"])

    for col in ["boro", "action", "inspection_type", "grade",
                "cuisine_description"]:
        insp[col] = insp[col].astype("category")

    for col in ["n_violations", "n_critical"]:
        insp[col] = insp[col].fillna(0).astype("int16")

    # Stable column order — id/when/where first, then what happened, then geo.
    insp = insp.rename(columns={"CAMIS": "camis"})
    insp = insp[[
        "camis", "inspection_date",
        "dba", "boro", "building", "street", "zipcode", "phone",
        "cuisine_description",
        "inspection_type", "action", "grade", "grade_date", "score",
        "n_violations", "n_critical", "violation_codes",
        "closed", "reopened", "reclosed",
        "latitude", "longitude",
        "community_board", "council_district", "census_tract",
        "bin_num", "bbl", "nta",
    ]]

    # 7) Write parquet + a small CSV sample.
    insp.to_parquet(OUT_PQT, index=False)
    insp.head(200).to_csv(OUT_SMPL, index=False)

    # 8) Verification — should match the profile report's "84,635" exactly.
    expected = real.groupby(["CAMIS", "_date"]).ngroups
    print()
    print(f"Wrote {OUT_PQT.name}: {len(insp):,} inspection rows, "
          f"{insp.shape[1]} columns "
          f"({OUT_PQT.stat().st_size / (1024 * 1024):.1f} MB).")
    print(f"  expected (distinct CAMIS+date in real rows): {expected:,}  "
          f"-> {'OK' if expected == len(insp) else 'MISMATCH'}")
    print(f"  no-CAMIS  rows: {insp['camis'].isna().sum()}")
    print(f"  no-date   rows: {insp['inspection_date'].isna().sum()}")
    print(f"  closure events: {int(insp['closed'].sum()):,}")
    print(f"  has-grade rows: {(insp['grade'] != '').sum():,} / {len(insp):,}")
    print(f"Wrote {OUT_SMPL.name}: 200-row sample for human inspection.")


if __name__ == "__main__":
    main()
