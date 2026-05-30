"""
Step 2 & 3 — Profile the DOHMH inspection data and assess two analytical angles.

This script ONLY describes the data. It does not pick an angle, model anything,
or build dashboards. It collects every line of the report in memory and writes
it ONCE to reports/profile_report.txt (a single atomic write — no incremental
appends), then prints the same text at the end.

Run (after download_data.py):
    python src/profile_data.py

Design notes for a learner:
- We load every column as a *string* first (dtype=str). Raw strings are the
  honest view: we can see blanks, placeholder dates like "01/01/1900", and odd
  category values without pandas silently coercing them. We make typed COPIES
  (dates, score) only where we need them, leaving the original untouched.
- "Grain" = what one row represents. We confirm the published file is one row
  per *violation*, so one inspection (a CAMIS on a date) spans several rows.
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = REPO_ROOT / "data" / "raw" / "dohmh_restaurant_inspections.csv"
REPORT_PATH = REPO_ROOT / "reports" / "profile_report.txt"

# Columns the analysis is most likely to need (DOHMH's exact header names).
KEY_COLUMNS = [
    "CAMIS", "INSPECTION DATE", "BORO", "ZIPCODE", "Latitude", "Longitude",
    "ACTION", "VIOLATION CODE", "CRITICAL FLAG", "SCORE", "GRADE", "GRADE DATE",
    "INSPECTION TYPE",
]

# Categorical key columns worth listing distinct values + frequencies for.
CATEGORICAL_KEY_COLUMNS = ["BORO", "ACTION", "CRITICAL FLAG", "GRADE", "INSPECTION TYPE"]

PLACEHOLDER_DATE = "01/01/1900"  # DOHMH "no inspection yet" sentinel

# The report is built up here as a list of strings, then written ONCE at the end.
LINES = []


def out(*parts):
    """Append one line to the in-memory report."""
    LINES.append(" ".join(str(p) for p in parts))


def section(title):
    """Append a titled section header (single unique line — no repeated bars)."""
    out("")
    out(f">>>>> {title}")


def fmt_pct(n, total):
    pct = (n / total * 100) if total else 0.0
    return f"{n:,} ({pct:.1f}%)"


# ----------------------------------------------------------------------------
# Load
# ----------------------------------------------------------------------------
def load_raw():
    if not RAW_CSV.exists():
        print(f"ERROR: raw file not found at {RAW_CSV}. Run download_data.py first.")
        sys.exit(1)

    print(f"Loading {RAW_CSV} (as strings)...")
    # keep_default_na=False -> empty cells stay "" (not NaN), so blanks are exact.
    df = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False)
    # Strip surrounding whitespace on every string cell once.
    df = df.apply(lambda col: col.str.strip())
    print(f"Loaded {len(df):,} rows x {df.shape[1]} columns.")
    return df


def is_blank(series):
    return series.eq("")


# ----------------------------------------------------------------------------
# STEP 2 — Profile
# ----------------------------------------------------------------------------
def step2_overview(df):
    section("STEP 2.1 — Shape, columns, dtypes, sample")
    out(f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
    out("")
    out("All columns (raw dtype is 'object'/string for every column by design):")
    for i, col in enumerate(df.columns):
        out(f"  [{i:2d}] {col}")

    missing_expected = [c for c in KEY_COLUMNS if c not in df.columns]
    if missing_expected:
        out("")
        out("WARNING: expected key columns NOT found:", missing_expected)
    else:
        out("")
        out("All expected key columns are present.")

    out("")
    out("Sample — key fields for the first 2 rows (one field per line):")
    present = [c for c in KEY_COLUMNS if c in df.columns]
    for row_i in range(min(2, len(df))):
        out(f"  --- row {row_i} ---")
        row = df.iloc[row_i]
        for col in present:
            out(f"    {col:<16}= {row[col]!r}")


def step2_grain(df):
    section("STEP 2.2 — Confirm the grain (one row per VIOLATION)")
    out("If one row = one violation, a single inspection (one CAMIS on one")
    out("INSPECTION DATE) should appear on MULTIPLE rows.")

    grp = df.groupby(["CAMIS", "INSPECTION DATE"]).size()
    real = grp[grp.index.get_level_values("INSPECTION DATE") != PLACEHOLDER_DATE]
    if real.empty:
        out("Could not find a non-placeholder inspection to demonstrate.")
        return

    example_camis, example_date = real.idxmax()
    n_rows = int(real.max())
    out("")
    out(f"Example inspection with the most rows: CAMIS={example_camis}, "
        f"DATE={example_date} -> {n_rows} rows.")
    sub = df[(df["CAMIS"] == example_camis) & (df["INSPECTION DATE"] == example_date)]

    # Show the columns that are CONSTANT across those rows (identify the
    # inspection) vs. the column that VARIES (the violation) — the essence of
    # the grain. We print each varying value on its own enumerated line.
    const_cols = [c for c in ["CAMIS", "INSPECTION DATE", "SCORE", "GRADE",
                              "INSPECTION TYPE", "ACTION"] if c in df.columns]
    out("")
    out("Columns that are CONSTANT across all those rows (the inspection):")
    for c in const_cols:
        uniq = sub[c].unique()
        shown = uniq[0] if len(uniq) == 1 else list(uniq)
        out(f"    {c:<16}= {shown!r}  (n distinct = {len(uniq)})")

    out("")
    codes = list(sub["VIOLATION CODE"]) if "VIOLATION CODE" in sub else []
    out(f"Column that VARIES row to row: VIOLATION CODE has {sub['VIOLATION CODE'].nunique()}"
        f" distinct values across the {n_rows} rows.")
    out(f"    VIOLATION CODE sequence: {codes}")

    out("")
    out("=> CAMIS/DATE/SCORE/GRADE/INSPECTION TYPE are constant while VIOLATION")
    out("   CODE differs: grain is one row per violation, not per inspection.")

    multi = int((real > 1).sum())
    out("")
    out(f"Of {len(real):,} real inspections, {fmt_pct(multi, len(real))} "
        f"span more than one row.")


def step2_missingness(df):
    section("STEP 2.3 — Missingness for key columns")
    total = len(df)
    out(f"(% of {total:,} rows that are blank/empty)")
    out("")
    for col in KEY_COLUMNS:
        if col not in df.columns:
            out(f"  {col}: COLUMN NOT PRESENT")
            continue
        n_missing = int(is_blank(df[col]).sum())
        out(f"  {col:<18}: {fmt_pct(n_missing, total)} missing")


def step2_categoricals(df):
    section("STEP 2.4 — Distinct values & frequencies (categorical keys)")
    total = len(df)
    for col in CATEGORICAL_KEY_COLUMNS:
        if col not in df.columns:
            out("")
            out(f"{col}: COLUMN NOT PRESENT")
            continue
        values = df[col].replace("", "<blank>")
        vc = values.value_counts(dropna=False)
        out("")
        out(f"{col} — {vc.shape[0]} distinct values"
            + (" (showing top 20)" if vc.shape[0] > 20 else "") + ":")
        for val, count in vc.head(20).items():
            label = (str(val)[:64] + "...") if len(str(val)) > 67 else val
            out(f"    {fmt_pct(int(count), total):>20}  {label}")


def step2_dates_counts(df):
    section("STEP 2.5 — Date range, distinct restaurants, distinct inspections")

    dates = pd.to_datetime(df["INSPECTION DATE"], format="%m/%d/%Y", errors="coerce")
    is_placeholder = df["INSPECTION DATE"] == PLACEHOLDER_DATE
    real_dates = dates[~is_placeholder]
    n_unparsed = int(dates.isna().sum() - is_placeholder.sum())

    out(f"INSPECTION DATE range (excluding {PLACEHOLDER_DATE} placeholder):")
    out(f"    earliest: {real_dates.min()}")
    out(f"    latest:   {real_dates.max()}")
    if n_unparsed > 0:
        out(f"    (note: {n_unparsed:,} dates failed to parse, ignored)")

    out("")
    out(f"Distinct restaurants (unique CAMIS): {df['CAMIS'].nunique():,}")

    insp = df[["CAMIS", "INSPECTION DATE"]].drop_duplicates()
    n_all = len(insp)
    n_real = len(insp[insp["INSPECTION DATE"] != PLACEHOLDER_DATE])
    out(f"Distinct inspections (CAMIS + INSPECTION DATE): {n_all:,}")
    out(f"    ...excluding {PLACEHOLDER_DATE} placeholder: {n_real:,}")


def step2_traps(df):
    section("STEP 2.6 — Quantify the known traps")
    total = len(df)

    n_1900 = int((df["INSPECTION DATE"] == PLACEHOLDER_DATE).sum())
    camis_1900 = df.loc[df["INSPECTION DATE"] == PLACEHOLDER_DATE, "CAMIS"].nunique()
    out(f"INSPECTION DATE = {PLACEHOLDER_DATE}: {fmt_pct(n_1900, total)}")
    out(f"    ...covering {camis_1900:,} distinct CAMIS (registered, never inspected).")

    if "GRADE" in df.columns:
        n_blank = int(is_blank(df["GRADE"]).sum())
        out("")
        out(f"Blank GRADE: {fmt_pct(n_blank, total)}")

    if "BORO" in df.columns:
        boro = df["BORO"]
        n_bad = int((boro.eq("0") | boro.eq("") | boro.str.lower().eq("missing")).sum())
        out("")
        out(f"BORO missing ('0', blank, or 'Missing'): {fmt_pct(n_bad, total)}")

    for coord in ("Latitude", "Longitude"):
        if coord in df.columns:
            c = df[coord]
            zeroish = c.eq("") | c.astype(str).str.fullmatch(r"0(\.0+)?")
            out("")
            out(f"{coord} missing (blank or 0): {fmt_pct(int(zeroish.sum()), total)}")


# ----------------------------------------------------------------------------
# STEP 3 — Feasibility of two angles
# ----------------------------------------------------------------------------
def step3_angle_a(df):
    section("STEP 3(a) — Re-inspection SPEED feasibility")
    out("Need: do restaurants reliably have MULTIPLE inspections over time, so a")
    out("gap between them can be measured? Distribution of distinct inspection")
    out(f"DATES per restaurant (CAMIS), excluding the {PLACEHOLDER_DATE} placeholder:")

    insp = df[["CAMIS", "INSPECTION DATE"]].drop_duplicates()
    insp = insp[insp["INSPECTION DATE"] != PLACEHOLDER_DATE]
    per_camis = insp.groupby("CAMIS").size()

    out("")
    out("Inspections-per-restaurant (describe):")
    desc = per_camis.describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95])
    for k, v in desc.items():
        out(f"    {k:>6}: {v:,.2f}")

    out("")
    out("Restaurants by number of inspections (binned):")
    bins = [0, 1, 2, 3, 5, 10, 20, np.inf]
    labels = ["1", "2", "3", "4-5", "6-10", "11-20", "21+"]
    binned = pd.cut(per_camis, bins=bins, labels=labels, right=True)
    vc = binned.value_counts().reindex(labels)
    total_camis = len(per_camis)
    for label, count in vc.items():
        out(f"    {label:>6} inspection(s): {fmt_pct(int(count), total_camis)} of restaurants")

    n_multi = int((per_camis >= 2).sum())
    out("")
    out(f"Restaurants with >= 2 inspections (needed to measure a gap): "
        f"{fmt_pct(n_multi, total_camis)}")


def step3_angle_b(df):
    section("STEP 3(b) — Failing-grade CONSEQUENCES feasibility")
    out("Need: can outcomes after a bad result (re-inspected / closed / improved)")
    out("be cleanly derived from ACTION and GRADE? Distributions below.")
    total = len(df)

    if "ACTION" in df.columns:
        out("")
        out("ACTION — full distinct values & frequencies:")
        vc = df["ACTION"].replace("", "<blank>").value_counts(dropna=False)
        for val, count in vc.items():
            out(f"    {fmt_pct(int(count), total):>20}  {val}")

    if "GRADE" in df.columns:
        out("")
        out("GRADE — full distinct values & frequencies:")
        vc = df["GRADE"].replace("", "<blank>").value_counts(dropna=False)
        for val, count in vc.items():
            out(f"    {fmt_pct(int(count), total):>20}  {val}")

        insp = df[["CAMIS", "INSPECTION DATE", "GRADE"]].drop_duplicates()
        insp = insp[insp["INSPECTION DATE"] != PLACEHOLDER_DATE]
        n_c = int((insp["GRADE"] == "C").sum())
        out("")
        out(f"Distinct inspections graded 'C': {n_c:,} (of {len(insp):,} real "
            f"inspections). These would anchor angle (b).")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = load_raw()

    out("DOHMH RESTAURANT INSPECTIONS — DATA PROFILE (Phase 1)")
    out("Descriptive only — no analytical angle chosen.")
    out(f"Source rows: {len(df):,}  |  columns: {df.shape[1]}")

    step2_overview(df)
    step2_grain(df)
    step2_missingness(df)
    step2_categoricals(df)
    step2_dates_counts(df)
    step2_traps(df)
    step3_angle_a(df)
    step3_angle_b(df)

    # SINGLE atomic write of the whole report (avoids any incremental-write issues).
    REPORT_PATH.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print(f"Report written ({len(LINES)} lines) to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
