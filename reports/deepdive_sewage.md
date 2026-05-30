
# Deep dive · the “sewage cliff” (probe B1)

Source data: inspection-grain parquet, 2023+, five boroughs only (76,896 inspections).

## 1 · The codes, in full

- **`04F`** — Food preparation area, food storage area, or other area used by employees or patrons, contaminated by sewage or liquid waste.
- **`05A`** — Sewage disposal system is not provided, improper, inadequate or unapproved.
- **`05E`** — Toilet facility not provided for employees or for patrons when required. Shared patron-employee toilet accessed through kitchen, food prep or storage area or utensil washing area.
- **`05F`** — Insufficient or no hot holding, cold storage or cold holding equipment provided to maintain Time/Temperature Control for Safety Foods (TCS) at required temperatures
- **`28-06`** — Contract with a pest management professional not in place. Record of extermination activities not kept on premises.
- **`05C`** — Food contact surface, refillable, reusable containers, or equipment improperly constructed, placed or maintained. Unacceptable material used. Culinary sink or other acceptable method not provided for washing food.
- **`05H`** — No approved written standard operating procedure for avoiding contamination by refillable returnable containers.
- **`28-01`** — Nuisance created or allowed to exist. Facility not free from unsafe, hazardous, offensive or annoying condition.

## 2 · Headline numbers, reverified

City-wide baseline closure rate: **1.75%**.

| code   |   n_inspections |   n_closed |   closure_pct |   lift_x |
|:-------|----------------:|-----------:|--------------:|---------:|
| 04F    |             215 |         73 |         33.95 |    19.44 |
| 05A    |             257 |         77 |         29.96 |    17.15 |
| 05E    |             201 |         50 |         24.88 |    14.24 |
| 05F    |             807 |        184 |         22.8  |    13.05 |
| 28-06  |            1898 |        300 |         15.81 |     9.05 |
| 05C    |             474 |         70 |         14.77 |     8.46 |
| 05H    |            1058 |        125 |         11.81 |     6.76 |
| 28-01  |             584 |         60 |         10.27 |     5.88 |

All lifts are very large and the codes carry comfortable sample sizes (≥200 inspections each, mostly far more), so the pattern is real and not a small-cell artefact.

## 3 · What does a “sewage-cliff” inspection look like?

Restricting to inspections containing at least one of the top three sewage / plumbing codes (`04F`, `05A`, `05E`).
| metric                           | Sewage-cliff inspections   | All other inspections   |
|:---------------------------------|:---------------------------|:------------------------|
| Inspections (n)                  | 567                        | 76,329                  |
| Median score                     | 54                         | 13                      |
| Mean score                       | 60.9                       | 17.7                    |
| Median violations per inspection | 6                          | 3                       |
| % closed                         | 27.5%                      | 1.6%                    |
| % with critical violation        | 100.0%                     | 85.3%                   |

So a sewage-cliff inspection isn't a typical one with a single bad code: the average score is much higher, and the median number of violations found is several times the baseline. These are the kitchens where a lot is going wrong at once and the plumbing failure is the last straw.

## 4 · Where these inspections happen

**By borough:** rate at which sewage-cliff codes appear in an inspection.

| boro          |   sewage_insp |   total_insp |   share_of_insp_pct |   share_of_sewage_pct |
|:--------------|--------------:|-------------:|--------------------:|----------------------:|
| Brooklyn      |           170 |        19778 |                0.86 |                  30   |
| Manhattan     |           218 |        29134 |                0.75 |                  38.4 |
| Queens        |           127 |        18029 |                0.7  |                  22.4 |
| Bronx         |            40 |         7253 |                0.55 |                   7.1 |
| Staten Island |            12 |         2702 |                0.44 |                   2.1 |

**By cuisine (top 10 by number of sewage-cliff inspections):**

| cuisine_description            |   sewage_insp |   total |   rate_pct |
|:-------------------------------|--------------:|--------:|-----------:|
| American                       |            74 |   12157 |       0.61 |
| Coffee/Tea                     |            74 |    6482 |       1.14 |
| Chinese                        |            47 |    6908 |       0.68 |
| Latin American                 |            29 |    3386 |       0.86 |
| Japanese                       |            26 |    2634 |       0.99 |
| Pizza                          |            25 |    4680 |       0.53 |
| Mexican                        |            20 |    3041 |       0.66 |
| Italian                        |            20 |    2475 |       0.81 |
| Juice, Smoothies, Fruit Salads |            18 |    1589 |       1.13 |
| Caribbean                      |            18 |    2512 |       0.72 |

## 5 · Five concrete example inspections (narrative material)


**Code `04F` — Food preparation area, food storage area, or other area used by employees or patrons, contaminated by sewage or liquid waste....**

|    | dba                        | boro      | cuisine_description   | inspection_date     |   score |   n_violations |   n_critical |
|---:|:---------------------------|:----------|:----------------------|:--------------------|--------:|---------------:|-------------:|
|  0 | 1313 CAFE & JUICE BAR      | Queens    | Indian                | 2026-03-12 00:00:00 |     191 |             14 |            9 |
|  1 | DELI & GRILL               | Manhattan | American              | 2025-08-28 00:00:00 |     175 |             15 |           11 |
|  2 | Sushi Q                    | Bronx     | Japanese              | 2024-06-20 00:00:00 |     142 |             14 |           10 |
|  3 | BLAZE HALAL GRILL          | Brooklyn  | Pakistani             | 2025-09-22 00:00:00 |     135 |             18 |           11 |
|  4 | CARIBBEAN CRAVE RESTAURANT | Queens    | Caribbean             | 2026-01-28 00:00:00 |     131 |             12 |            7 |

**Code `05A` — Sewage disposal system is not provided, improper, inadequate or unapproved....**

|    | dba                    | boro      | cuisine_description   | inspection_date     |   score |   n_violations |   n_critical |
|---:|:-----------------------|:----------|:----------------------|:--------------------|--------:|---------------:|-------------:|
|  0 | JAY & SON LATIN FLAVOR | Brooklyn  | Latin American        | 2026-04-13 00:00:00 |     200 |             18 |           11 |
|  1 | 1313 CAFE & JUICE BAR  | Queens    | Indian                | 2026-03-12 00:00:00 |     191 |             14 |            9 |
|  2 | DELI & GRILL           | Manhattan | American              | 2025-08-28 00:00:00 |     175 |             15 |           11 |
|  3 | LE PAIN QUOTIDIEN      | Manhattan | Coffee/Tea            | 2023-07-20 00:00:00 |     168 |              9 |            8 |
|  4 | % ARABICA              | Manhattan | Middle Eastern        | 2026-03-31 00:00:00 |     163 |             10 |            7 |

**Code `05E` — Toilet facility not provided for employees or for patrons when required. Shared patron-employee toilet accessed through kitchen, food prep o...**

|    | dba                          | boro      | cuisine_description   | inspection_date     |   score |   n_violations |   n_critical |
|---:|:-----------------------------|:----------|:----------------------|:--------------------|--------:|---------------:|-------------:|
|  0 | JAY & SON LATIN FLAVOR       | Brooklyn  | Latin American        | 2026-04-13 00:00:00 |     200 |             18 |           11 |
|  1 | LE PAIN QUOTIDIEN            | Manhattan | Coffee/Tea            | 2023-07-20 00:00:00 |     168 |              9 |            8 |
|  2 | WENZHOU SEAFOOD NOODLES SOUP | Queens    | Chinese               | 2025-02-20 00:00:00 |     168 |             17 |           10 |
|  3 | KING SUNSHINE #2 JERK CENTER | Bronx     | Caribbean             | 2026-04-30 00:00:00 |     160 |              8 |            7 |
|  4 | GLACE BY NOGLU               | Manhattan | Frozen Desserts       | 2026-03-02 00:00:00 |     152 |              9 |            6 |

## 6 · What happens after a sewage-cliff CLOSURE

For inspections that had one of the top 3 codes AND were closed by DOHMH, look at each restaurant's next inspection date / score / action (within 180 days).
- Closures with a top-3 sewage code: **156**
- Of those, restaurants that had any follow-up inspection within 180d: **115** (76%)
- Median days from sewage closure → next inspection: **6 days**
- Median score on that next inspection: **4** (down from sewage-cliff median 84)

Next-inspection ACTION breakdown:

| action                                                                                                                             |   share % |
|:-----------------------------------------------------------------------------------------------------------------------------------|----------:|
| Establishment re-opened by DOHMH.                                                                                                  |      68.9 |
| Establishment re-closed by DOHMH.                                                                                                  |      17.6 |
| Establishment Closed by DOHMH. Violations were cited in the following area(s) and those requiring immediate action were addressed. |      12.6 |
| Violations were cited in the following area(s).                                                                                    |       0.8 |
| No violations were recorded at the time of this inspection.                                                                        |       0   |