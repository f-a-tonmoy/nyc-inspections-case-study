# The Quiet Math of NYC's Restaurant Inspections

A data-driven case study of NYC's restaurant inspection program: what
**~83,000 inspections of ~27,000 active restaurants** reveal about pests,
plumbing, geography, and what actually gets a kitchen shut down.

**By Fahim Ahamed** · [LinkedIn](https://www.linkedin.com/in/f-a-tonmoy/) · [Portfolio](https://f-a-tonmoy.github.io/)

> **Live article:** _(will be linked here once GitHub Pages is configured)_

Built as a reproducible Python pipeline that profiles, analyses, and renders
a single self-contained HTML article with interactive Plotly charts. Source
data: NYC Open Data dataset [`43nn-pn8j`](https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j).

## What's in the article

Seven numbered findings + intro + conclusion:

1. **Vermin is everywhere** — 1 in 3 NYC inspections find evidence of mice, rats, roaches or flies
2. **The closure cliff** — most violations don't shut a kitchen down; sewage codes do (~19× the baseline closure rate)
3. **The 13-point ceiling** — inspection scores pile up just under the A/B grade boundary
4. **Most kitchens bounce back** — after a failed inspection, 58% recover to an A on the next visit
5. **NYC's food map is sliced into pockets** — five cultural cuisines plotted on an interactive city map
6. **The summer effect** — closure rates jump in summer, hot-food violations drop
7. **What an 'A' really means** — 96% of restaurants have been cited for at least one critical violation in the past three years

## Repo layout

```
data/
  README.md               how to download the raw CSV + geojson
  raw/                    gitignored — populated by download_data.py
  processed/              gitignored — produced by build_inspections.py
src/
  download_data.py        Step 1 — pull raw CSV into data/raw/
  build_inspections.py    Step 2 — collapse violations to one row per inspection
  build_article.py        Step 3 — compute findings + render article.html
notebooks/
  01_visual_overview.ipynb   initial visual profile (outputs baked in)
reports/
  article.html            THE CASE STUDY — open in any browser
  data_dictionary.md      column-by-column notes on the raw CSV
  source_notes.md         official dataset description + annotated implications
requirements.txt          minimal Python dependencies
```

## How to reproduce

Requires Python 3.10+ and the packages in `requirements.txt`
(pandas, numpy, plotly).

```bash
# 1. Set up a virtual environment (use whatever you like — venv, conda, uv, ...)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Download the source data (see data/README.md for details)
python src/download_data.py

# 3. Build the analysis-ready table
python src/build_inspections.py

# 4. Render the article
python src/build_article.py
# -> writes reports/article.html

# 5. Preview locally
python -m http.server 8000 --directory reports
# open http://localhost:8000/article.html
```

The article HTML is self-contained: all CSS is inline, Plotly loads from CDN,
and there are no other local asset dependencies.

## Key conventions in the data

- **`SCORE`** is DOHMH's inspection metric where **higher = worse**. `GRADE`
  (A / B / C) is derived from the score by DOHMH; this pipeline never
  recomputes it.
- **Grain:** the raw CSV is **one row per violation**, so a single inspection
  (one `CAMIS` on one date) spans multiple rows. `build_inspections.py`
  collapses it to one row per `(camis, inspection_date)`.
- **Coverage:** the published file is a **rolling ~3-year window** of active
  restaurants. The pre-2022 records are a sparse tail (under 300/year through
  2021); everything in the article uses inspections from mid-2022 onward.
- **Active-status filter:** restaurants that permanently closed or lost their
  permit drop out of the file entirely. The article's closure rates therefore
  describe surviving restaurants only.

## License

The analysis code in this repository is released as-is for portfolio /
educational use. The underlying inspection data is published by the City of
New York under the [NYC Open Data terms of use](https://www.nyc.gov/home/terms-of-use.page).
