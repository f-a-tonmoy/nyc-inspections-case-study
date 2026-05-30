# NYC DOHMH Restaurant Inspections — Enforcement Equity Analysis

A data-analysis portfolio project examining **how the City of New York inspects
restaurants across neighborhoods** — an oversight / enforcement-equity lens,
**not** a consumer "which restaurants are dirty" grade map.

> Source: NYC Open Data — DOHMH New York City Restaurant Inspection Results
> (dataset id `43nn-pn8j`).

## Project status

**Phase 1 — Data understanding (current).** Honest profile of what the file
contains: grain, coverage, missingness, and known traps. The analytical angle
has **not** been chosen yet.

## Environment

This project uses the **`intro_ds`** conda environment (Python 3.12, pandas,
numpy, matplotlib, seaborn, jupyter). All commands and the notebook kernel
should run inside it.

```bash
# one-time: register the kernel under the same name (so notebooks find it)
conda run -n intro_ds python -m ipykernel install --user --name intro_ds \
    --display-name "Python (intro_ds)"
```

## Repo layout

```
data/
  raw/        raw CSV from NYC Open Data (git-ignored, re-downloadable)
  processed/  derived/intermediate files (git-ignored)
src/
  download_data.py   Step 1: pull the raw CSV into data/raw/
  profile_data.py    Step 2-3: profile + assess two analytical angles
notebooks/
  01_visual_overview.ipynb   Visual companion to the profile report
reports/
  profile_report.txt         Text profile written by profile_data.py
  figures/                   PNGs exported from the notebook
```

## How to run (top to bottom, reproducible)

```bash
conda run -n intro_ds python src/download_data.py     # downloads to data/raw/
conda run -n intro_ds python src/profile_data.py      # writes reports/profile_report.txt
conda run -n intro_ds jupyter lab notebooks/01_visual_overview.ipynb
```

## Notes on the data (DOHMH conventions)

- **Grain:** the file is **one row per violation**, so a single inspection
  (one CAMIS on one date) spans multiple rows. Collapse to inspection grain
  before any analysis.
- **`SCORE`** is DOHMH's inspection metric where **higher = worse**. `GRADE`
  (A/B/C) is derived by DOHMH from the score — we do **not** recompute it.
- **`GRADE`** is blank ~51% of the time (re-inspections, pre-permit visits,
  etc.). For severity, prefer `SCORE` and `ACTION` over the letter grade.
- **`01/01/1900`** appears as `INSPECTION DATE` for restaurants that are
  registered but have never been inspected — exclude when analyzing inspection
  events.
- **Temporal coverage:** despite a min date of 2007, the snapshot is
  effectively a **rolling ~3-year window** — virtually all inspections fall in
  2022 onwards (see `reports/figures/02_inspections_per_month.png`).
