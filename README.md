# NYC DOHMH Restaurant Inspections — Enforcement Equity Analysis

A data-analysis portfolio project examining **how the City of New York inspects
restaurants across neighborhoods** — an oversight / enforcement-equity lens,
**not** a consumer "which restaurants are dirty" grade map.

> Source: NYC Open Data — DOHMH New York City Restaurant Inspection Results
> (dataset id `43nn-pn8j`).

## Project status

**Phase 1 — Data understanding (current).** Download the raw data and build an
honest picture of what it contains: grain, coverage, missingness, and known
traps. The analytical angle has **not** been chosen yet; that decision comes
after profiling.

## Repo layout

```
data/
  raw/         # raw CSV from NYC Open Data (git-ignored, re-downloadable)
  processed/   # derived/intermediate files (git-ignored)
src/
  download_data.py   # Step 1: pull the raw CSV into data/raw/
  profile_data.py    # Step 2-3: profile the data and assess two angles
reports/
  profile_report.txt # text output written by profile_data.py
```

## How to run (top to bottom, reproducible)

```bash
python -m pip install -r requirements.txt
python src/download_data.py     # downloads ~ a few hundred MB to data/raw/
python src/profile_data.py      # prints + writes reports/profile_report.txt
```

## Notes on the data (DOHMH conventions)

- `SCORE` is DOHMH's inspection metric where **higher = worse**. `GRADE`
  (A/B/C) is derived by DOHMH from the score — we do **not** recompute it.
- The published file is **one row per violation**, so a single inspection
  (one CAMIS on one date) spans multiple rows.
