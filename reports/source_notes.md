# Source notes — official DOHMH dataset description

The text below is the official description from NYC Open Data for the
"DOHMH New York City Restaurant Inspection Results" dataset (`43nn-pn8j`).
After each paragraph, annotated implications for *our* analysis.

> The dataset contains every **sustained or not yet adjudicated** violation
> citation from every full or special program inspection conducted **up to
> three years prior to the most recent inspection** for restaurants and
> college cafeterias **in an active status on the RECORD DATE** (date of
> the data pull). When an inspection results in more than one violation,
> values for associated fields are repeated for each additional violation
> record. Establishments are uniquely identified by their CAMIS (record ID)
> number. Keep in mind that thousands of restaurants start business and go
> out of business every year; **only restaurants in an active status are
> included in the dataset.**

**Implications:**
- **"Three-year rolling window"** — confirms what we observed on
  `02_inspections_per_month.png`: the snapshot's effective coverage is the
  most recent ~3 years (today: ~2023–2026). The pre-2022 sparse residue
  is the long tail of older inspections still attached to restaurants that
  remain active. Any time-series claim should be confined to the dense
  window.
- **"Sustained or not yet adjudicated"** — violations that were challenged
  and dismissed are NOT here. Our `n_violations` / `n_critical` are
  post-adjudication / pending counts, not raw observed counts. Treat them
  as a conservative lower bound on what an inspector originally wrote up.
- **"Only active restaurants"** — *survivorship bias.* Restaurants that
  permanently closed (e.g. after enforcement) drop out of the dataset.
  We can describe what happened to surviving restaurants but cannot see
  "permanently shut down after a bad inspection." This is the single most
  important caveat for any **consequences** angle.

> Records are also included for each restaurant that has applied for a
> permit but has not yet been inspected and for inspections resulting in no
> violations. Establishments with **inspection date of 1/1/1900** are new
> establishments that have not yet received an inspection. Restaurants that
> received no violations are represented by a **single row and coded as
> having no violations using the ACTION field**.

**Implications:**
- `01/01/1900` rows are not inspections; we drop them in
  `build_inspections.py`. The 3,434 we counted matches the "registered,
  awaiting first inspection" cohort.
- "No violations" rows (`ACTION = "No violations were recorded..."`) are
  legitimate single-row inspections. In our parquet they appear with
  `n_violations = 0`. There are 2,397 such rows in the raw file.

> Because this dataset is compiled from several large administrative data
> systems, it contains some illogical values that could be a result of data
> entry or transfer errors. Data may also be missing.

**Implications:**
- Validates our defensive loading (strings first, blanks preserved as `''`).
- Specific quirks we already quantified: `BORO = "0"` (363 rows),
  `Latitude/Longitude = 0` placeholder (4,703 rows), `GRADE` blank
  on 51% of rows, exact-duplicate violation rows (134 deduped).

> This dataset and the information on the Health Department's Restaurant
> Grading website come from the same data source.

**Implication:** the consumer-facing "grade card" view and our row-level
view share a backend — so the published `GRADE` values are authoritative
and we should never recompute them from `SCORE`.

---

## What this adds to the angle-feasibility picture

The official description **strengthens one angle and weakens another**:

- **(a) Re-inspection SPEED.** Mostly unchanged. The "active restaurants
  only" constraint slightly biases our sample toward survivors (a
  restaurant that closed before its re-inspection window expired would not
  appear), but for the majority of the analyzable cohort the cadence is
  observable directly. Three-year window means we can't compare 2015 vs
  2025; comparisons should be within recent years.

- **(b) Failing-grade CONSEQUENCES.** Significantly weakened. We can
  measure "after a C / a closure, what happened *to survivors*" but cannot
  see "after a C, the restaurant permanently closed." That's the most
  consequential outcome of all, and it's invisible here. We'd be looking
  at a censored sample. Any consequences framing needs to flag this loudly
  or pair the dataset with NYC business-license / permit data to see
  permanent closures.
