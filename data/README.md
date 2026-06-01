# Data — how to get it

The `data/` directory is **gitignored** (`data/raw/` and `data/processed/` both).
The raw CSV is ~140 MB and the processed parquet is regenerated from it, so
neither belongs in git. This README explains how to populate the directory
locally so you can re-run the build.

## What lives here

```
data/
├── raw/                              gitignored
│   ├── dohmh_restaurant_inspections.csv   ~140 MB · the raw NYC Open Data export
│   └── nyc_council_districts.geojson      ~860 KB · NYC council district polygons
└── processed/                        gitignored
    ├── inspections.parquet           ~3.8 MB · collapsed to one row per (camis, inspection_date)
    └── inspections_sample.csv        ~60 KB  · 200-row human-eyeball preview
```

## Source

**DOHMH New York City Restaurant Inspection Results.** NYC Open Data dataset id
[`43nn-pn8j`](https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j).
Updated daily by the NYC Department of Health and Mental Hygiene. The published
file is a rolling ~3-year window of inspection records for restaurants in
active status.

The council-district geojson is from NYC Open Data dataset id
[`mkqi-d8x3`](https://data.cityofnewyork.us/City-Government/City-Council-Districts-Water-Areas-Included-/mkqi-d8x3).

## How to populate it

### Option A — run the helper script (recommended)

```bash
python src/download_data.py
```

This downloads the CSV into `data/raw/dohmh_restaurant_inspections.csv` using
the NYC Open Data API. The council-district geojson is fetched separately by
`src/_fetch_districts_geojson.py` if you don't already have it.

### Option B — manual download

1. Visit <https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j>
2. Click **Export → CSV**
3. Save as `data/raw/dohmh_restaurant_inspections.csv`
4. For the council districts: visit <https://data.cityofnewyork.us/City-Government/City-Council-Districts-Water-Areas-Included-/mkqi-d8x3>, export as GeoJSON, save as `data/raw/nyc_council_districts.geojson`

### Then build the processed table

```bash
python src/build_inspections.py
```

This collapses the raw "one row per violation" file into the analysis-ready
"one row per inspection" parquet at `data/processed/inspections.parquet`.

### Then build the article

```bash
python src/build_article.py
```

Writes `reports/article.html` — the case-study deliverable.

## Why the dataset isn't in git

- **Size**: 140 MB is well above GitHub's 100 MB hard limit and far above the
  50 MB warning. It would require Git LFS, which adds friction.
- **Reproducibility**: the file is publicly available and re-downloadable in
  one command. Pinning a snapshot in git creates a stale fork that diverges
  from the official rolling-window data.
- **Drift**: the rolling window means the file changes daily. Re-running the
  build always uses the latest published snapshot. The article's headline
  numbers will shift slightly if rebuilt months later — that's a feature, not
  a bug.

## Citation

NYC Department of Health and Mental Hygiene. *DOHMH New York City Restaurant
Inspection Results* [dataset]. NYC Open Data. Retrieved from
<https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j>.
