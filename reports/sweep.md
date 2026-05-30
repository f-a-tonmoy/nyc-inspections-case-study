
# Discovery sweep results

Computed by `src/sweep_insights.py`. Dense window: 2023+ (76,896 inspections across the five boroughs).


## A2 · The repeat-closure leaderboard

> *How many NYC restaurants have been closed by DOHMH more than once in the rolling window, and who's the champion?*
- **1,166** distinct restaurants had at least one DOHMH closure in the window.
- **150** were closed *more than once*.
- Maximum closures by a single restaurant: **5**.

**Top 15 recidivists:**

|    |    camis | dba                                          | boro      |   n_closures |
|---:|---------:|:---------------------------------------------|:----------|-------------:|
|  0 | 50138270 | MEEM SPICY GROCERY AND DELI                  | Manhattan |            5 |
|  1 | 50122265 | MAX BAKERY & RESTAURANT                      | Queens    |            4 |
|  2 | 50154720 | OLIVE FAST FOOD                              | Queens    |            4 |
|  3 | 50160368 | HALAL MUNCHIES                               | Brooklyn  |            4 |
|  4 | 41628099 | LLOYD'S CARROT CAKE                          | Manhattan |            3 |
|  5 | 50181493 | HALAL MUNCHIES                               | Manhattan |            3 |
|  6 | 50143154 | CRUMBL                                       | Manhattan |            3 |
|  7 | 50138021 | EL VIEJO YAYO                                | Queens    |            3 |
|  8 | 50153957 | WE NOODLE                                    | Manhattan |            3 |
|  9 | 50156592 | GREAT TASTE USA                              | Manhattan |            3 |
| 10 | 50154039 | AMAR BARI                                    | Brooklyn  |            3 |
| 11 | 50172148 | ADOBO MEXICAN GRILL                          | Queens    |            3 |
| 12 | 50147177 | 1915 LANZHOU HAND PULLED NOODLES & DUMPLINGS | Manhattan |            3 |
| 13 | 50140086 | HENRY & THE LIONS                            | Manhattan |            3 |
| 14 | 50126865 | NOTA BENE                                    | Brooklyn  |            3 |

## A4 · The biggest comebacks (initial 60+ → re-inspection A)

> *How many restaurants posted a brutal initial cycle score (60+) and recovered to an A on re-inspection? What's the median timespan?*
- Initial-cycle inspections scoring **60+** (a deep-C / worse): **333** paired with a re-inspection.
- Of those, **147** (44%) came back with an A.
- Median time from initial to A re-inspection: **58 days**.
- Median score drop: **58 points**.
- Maximum score drop observed: **129 points** (initial 141 → re-inspection 12).

**Top 10 single-inspection comebacks:**

|    | dba                        | boro      | initial_date        |   initial_score |   reinsp_score |   days |
|---:|:---------------------------|:----------|:--------------------|----------------:|---------------:|-------:|
|  0 | KAFFE ARE                  | Manhattan | 2024-06-25 00:00:00 |             141 |             12 |     62 |
|  1 | FUSION EAST                | Brooklyn  | 2024-09-19 00:00:00 |             131 |             13 |    132 |
|  2 | BURGER MAN                 | Manhattan | 2025-06-23 00:00:00 |             128 |             13 |    122 |
|  3 | MARISCOS EL SUBMARINO      | Brooklyn  | 2025-08-26 00:00:00 |             118 |              9 |     56 |
|  4 | TASTE OF CANTON            | Queens    | 2025-09-24 00:00:00 |             110 |              7 |     57 |
|  5 | SAPPS UWS                  | Manhattan | 2025-07-21 00:00:00 |             109 |             13 |     58 |
|  6 | OCHO RIOS SEAFOOD & LOUNGE | Brooklyn  | 2024-10-04 00:00:00 |             106 |             11 |     41 |
|  7 | TAQUERIA EL CEBOLLIN       | Bronx     | 2024-07-08 00:00:00 |             103 |             11 |    156 |
|  8 | EL VIEJO YAYO              | Queens    | 2024-12-04 00:00:00 |             101 |             11 |     58 |
|  9 | DILLINGERS PUB & GRILL     | Queens    | 2025-11-22 00:00:00 |             102 |             13 |     96 |

## B1 · Violation codes that most predict closure

> *Which violation codes, when present, raise the probability the inspection ends in a DOHMH closure most above the city baseline?*
- City-wide closure rate (baseline): **1.75%** of inspections.
- Codes are filtered to those with ≥ 200 inspection appearances so a single rare-code closure can't dominate.

**Top 15 codes by closure rate when present:**

| code   |   n_inspections |   closure_rate_pct |   lift_vs_baseline | description                                                                                                     |
|:-------|----------------:|-------------------:|-------------------:|:----------------------------------------------------------------------------------------------------------------|
| 04F    |             215 |              33.95 |              19.44 | Food preparation area, food storage area, or other area used by employees or patrons, contaminated by sewage o… |
| 05A    |             257 |              29.96 |              17.15 | Sewage disposal system is not provided, improper, inadequate or unapproved.                                     |
| 05E    |             201 |              24.88 |              14.24 | Toilet facility not provided for employees or for patrons when required. Shared patron-employee toilet accesse… |
| 05F    |             807 |              22.8  |              13.05 | Insufficient or no hot holding, cold storage or cold holding equipment provided to maintain Time/Temperature C… |
| 28-06  |            1898 |              15.81 |               9.05 | Contract with a pest management professional not in place. Record of extermination activities not kept on prem… |
| 05C    |             474 |              14.77 |               8.46 | Food contact surface, refillable, reusable containers, or equipment improperly constructed, placed or maintain… |
| 05H    |            1058 |              11.81 |               6.76 | No approved written standard operating procedure for avoiding contamination by refillable returnable container… |
| 28-01  |             584 |              10.27 |               5.88 | Nuisance created or allowed to exist. Facility not free from unsafe, hazardous, offensive or annoying conditio… |
| 04M    |            4554 |               8.65 |               4.95 | Live roaches in facility's food or non-food area.                                                               |
| 03A    |            1146 |               8.64 |               4.95 | Food, prohibited, from unapproved or unknown source, home canned or home prepared. Animal slaughtered, butcher… |
| 04K    |            2680 |               8.13 |               4.66 | Evidence of rats or live rats in establishment's food or non-food areas.                                        |
| 05D    |            5148 |               6.49 |               3.71 | No hand washing facility in or adjacent to toilet room or within 25 feet of a food preparation, food service o… |
| 04H    |            5435 |               6.27 |               3.59 | Raw, cooked or prepared food is adulterated, contaminated, cross-contaminated, or not discarded in accordance…  |
| 04L    |           13297 |               5.35 |               3.07 | Evidence of mice or live mice in establishment's food or non-food areas.                                        |
| 08C    |            4718 |               5.09 |               2.91 | Pesticide not properly labeled or used by unlicensed individual. Pesticide, other toxic chemical improperly us… |

## B2 · Where the vermin live (mice / rats / roaches / flies)

> *What share of inspections find evidence of pests, and which neighborhoods (NTA) are worst?*
- City-wide: **32.0%** of inspections find at least one vermin-related violation.

**By borough:**

| boro          |   inspections |   % with vermin |
|:--------------|--------------:|----------------:|
| Bronx         |          7253 |            34.8 |
| Brooklyn      |         19778 |            33.2 |
| Manhattan     |         29134 |            30.1 |
| Queens        |         18029 |            33.3 |
| Staten Island |          2702 |            29.1 |

**Worst 10 neighborhoods (NTA, ≥200 inspections):**

|                       |   inspections |   % with vermin |
|:----------------------|--------------:|----------------:|
| ('BK91', 'Brooklyn')  |           216 |            47.7 |
| ('QN55', 'Queens')    |           538 |            46.5 |
| ('QN34', 'Queens')    |           246 |            45.5 |
| ('QN35', 'Queens')    |           212 |            44.3 |
| ('BX44', 'Bronx')     |           250 |            43.2 |
| ('QN54', 'Queens')    |           387 |            43.2 |
| ('MN03', 'Manhattan') |           235 |            43   |
| ('QN08', 'Queens')    |           200 |            42.5 |
| ('QN61', 'Queens')    |           707 |            41.2 |
| ('BK45', 'Brooklyn')  |           240 |            40   |

**Best 10 neighborhoods (NTA, ≥200 inspections):**

|                           |   inspections |   % with vermin |
|:--------------------------|--------------:|----------------:|
| ('MN25', 'Manhattan')     |          1476 |            21.2 |
| ('SI45', 'Staten Island') |           252 |            22.2 |
| ('SI11', 'Staten Island') |           207 |            23.2 |
| ('SI54', 'Staten Island') |           227 |            23.8 |
| ('BK38', 'Brooklyn')      |           972 |            23.9 |
| ('MN17', 'Manhattan')     |          4826 |            24.6 |
| ('MN24', 'Manhattan')     |          2153 |            26.6 |
| ('BK32', 'Brooklyn')      |           522 |            26.6 |
| ('BK43', 'Brooklyn')      |           201 |            26.9 |
| ('QN31', 'Queens')        |          1283 |            27.8 |

## C1 · Cuisines ranked by closure rate

> *Across all NYC cuisines (with ≥500 inspections to keep it fair), which type of restaurant gets shut down most often per inspection?*

**Top 12 cuisines (highest closure rate):**

| cuisine_description      |    n |   n_restaurants |   closure_rate_pct |
|:-------------------------|-----:|----------------:|-------------------:|
| Indian                   |  981 |             325 |               5.1  |
| Middle Eastern           |  727 |             275 |               4.4  |
| Caribbean                | 2512 |             738 |               3.5  |
| Chinese                  | 6908 |            2292 |               3.26 |
| Thai                     | 1046 |             352 |               2.87 |
| Jewish/Kosher            |  945 |             335 |               2.65 |
| Bakery Products/Desserts | 3143 |             925 |               2.35 |
| Mediterranean            |  831 |             320 |               2.29 |
| Latin American           | 3386 |            1069 |               2.13 |
| Asian/Asian Fusion       | 1322 |             480 |               2.12 |
| Spanish                  | 1477 |             509 |               1.96 |
| Korean                   | 1077 |             429 |               1.95 |

**Bottom 12 cuisines (lowest closure rate):**

| cuisine_description   |     n |   n_restaurants |   closure_rate_pct |
|:----------------------|------:|----------------:|-------------------:|
| Tex-Mex               |   922 |             310 |               1.41 |
| Pizza                 |  4680 |            1619 |               1.39 |
| Seafood               |   589 |             235 |               1.36 |
| Coffee/Tea            |  6482 |            2205 |               1.14 |
| Other                 |   875 |             576 |               1.03 |
| American              | 12157 |            4707 |               0.86 |
| Frozen Desserts       |   968 |             382 |               0.83 |
| Italian               |  2475 |             996 |               0.81 |
| Irish                 |   541 |             196 |               0.55 |
| Hamburgers            |  1523 |             496 |               0.46 |
| Donuts                |  1889 |             545 |               0.42 |
| French                |   739 |             293 |               0.41 |

## C3 · Cuisine geography — where each top cuisine lives

> *For the most common NYC cuisines, how are restaurants distributed across boroughs? (Critical confound for any borough finding.)*

**Restaurant counts per cuisine × borough (distinct CAMIS):**

| cuisine_description            |   0 |   Bronx |   Brooklyn |   Manhattan |   Queens |   Staten Island |
|:-------------------------------|----:|--------:|-----------:|------------:|---------:|----------------:|
|                                |   0 |       0 |          0 |           0 |        0 |               0 |
| Afghan                         |   0 |       0 |          0 |           0 |        0 |               0 |
| African                        |   0 |       0 |          0 |           0 |        0 |               0 |
| American                       |   0 |     306 |       1059 |        2421 |      768 |             153 |
| Armenian                       |   0 |       0 |          0 |           0 |        0 |               0 |
| Asian/Asian Fusion             |   0 |       0 |          0 |           0 |        0 |               0 |
| Australian                     |   0 |       0 |          0 |           0 |        0 |               0 |
| Bagels/Pretzels                |   0 |       0 |          0 |           0 |        0 |               0 |
| Bakery Products/Desserts       |   0 |      85 |        223 |         311 |      275 |              31 |
| Bangladeshi                    |   0 |       0 |          0 |           0 |        0 |               0 |
| Barbecue                       |   0 |       0 |          0 |           0 |        0 |               0 |
| Basque                         |   0 |       0 |          0 |           0 |        0 |               0 |
| Bottled Beverages              |   0 |       0 |          0 |           0 |        0 |               0 |
| Brazilian                      |   0 |       0 |          0 |           0 |        0 |               0 |
| Cajun                          |   0 |       0 |          0 |           0 |        0 |               0 |
| Californian                    |   0 |       0 |          0 |           0 |        0 |               0 |
| Caribbean                      |   0 |     108 |        349 |          54 |      224 |               3 |
| Chicken                        |   0 |     162 |        215 |         152 |      179 |              23 |
| Chilean                        |   0 |       0 |          0 |           0 |        0 |               0 |
| Chimichurri                    |   0 |       0 |          0 |           0 |        0 |               0 |
| Chinese                        |   0 |     237 |        666 |         540 |      757 |              92 |
| Chinese/Cuban                  |   0 |       0 |          0 |           0 |        0 |               0 |
| Chinese/Japanese               |   0 |       0 |          0 |           0 |        0 |               0 |
| Coffee/Tea                     |   0 |      87 |        601 |        1111 |      346 |              60 |
| Continental                    |   0 |       0 |          0 |           0 |        0 |               0 |
| Creole                         |   0 |       0 |          0 |           0 |        0 |               0 |
| Creole/Cajun                   |   0 |       0 |          0 |           0 |        0 |               0 |
| Czech                          |   0 |       0 |          0 |           0 |        0 |               0 |
| Donuts                         |   0 |      74 |        121 |         166 |      146 |              38 |
| Eastern European               |   0 |       0 |          0 |           0 |        0 |               0 |
| Egyptian                       |   0 |       0 |          0 |           0 |        0 |               0 |
| English                        |   0 |       0 |          0 |           0 |        0 |               0 |
| Ethiopian                      |   0 |       0 |          0 |           0 |        0 |               0 |
| Filipino                       |   0 |       0 |          0 |           0 |        0 |               0 |
| French                         |   0 |       0 |          0 |           0 |        0 |               0 |
| Frozen Desserts                |   0 |       0 |          0 |           0 |        0 |               0 |
| Fruits/Vegetables              |   0 |       0 |          0 |           0 |        0 |               0 |
| Fusion                         |   0 |       0 |          0 |           0 |        0 |               0 |
| German                         |   0 |       0 |          0 |           0 |        0 |               0 |
| Greek                          |   0 |       0 |          0 |           0 |        0 |               0 |
| Hamburgers                     |   0 |       0 |          0 |           0 |        0 |               0 |
| Haute Cuisine                  |   0 |       0 |          0 |           0 |        0 |               0 |
| Hawaiian                       |   0 |       0 |          0 |           0 |        0 |               0 |
| Hotdogs                        |   0 |       0 |          0 |           0 |        0 |               0 |
| Hotdogs/Pretzels               |   0 |       0 |          0 |           0 |        0 |               0 |
| Indian                         |   0 |       0 |          0 |           0 |        0 |               0 |
| Indonesian                     |   0 |       0 |          0 |           0 |        0 |               0 |
| Iranian                        |   0 |       0 |          0 |           0 |        0 |               0 |
| Irish                          |   0 |       0 |          0 |           0 |        0 |               0 |
| Italian                        |   0 |      40 |        180 |         601 |      109 |              66 |
| Japanese                       |   0 |      29 |        240 |         553 |      184 |              45 |
| Jewish/Kosher                  |   0 |       0 |          0 |           0 |        0 |               0 |
| Juice, Smoothies, Fruit Salads |   0 |       0 |          0 |           0 |        0 |               0 |
| Korean                         |   0 |       0 |          0 |           0 |        0 |               0 |
| Latin American                 |   0 |     185 |        209 |         201 |      460 |              14 |
| Lebanese                       |   0 |       0 |          0 |           0 |        0 |               0 |
| Mediterranean                  |   0 |       0 |          0 |           0 |        0 |               0 |
| Mexican                        |   0 |     151 |        325 |         295 |      262 |              57 |
| Middle Eastern                 |   0 |       0 |          0 |           0 |        0 |               0 |
| Moroccan                       |   0 |       0 |          0 |           0 |        0 |               0 |
| New American                   |   0 |       0 |          0 |           0 |        0 |               0 |
| New French                     |   0 |       0 |          0 |           0 |        0 |               0 |
| Not Listed/Not Applicable      |   0 |       0 |          0 |           0 |        0 |               0 |
| Nuts/Confectionary             |   0 |       0 |          0 |           0 |        0 |               0 |
| Other                          |   0 |       0 |          0 |           0 |        0 |               0 |
| Pakistani                      |   0 |       0 |          0 |           0 |        0 |               0 |
| Pancakes/Waffles               |   0 |       0 |          0 |           0 |        0 |               0 |
| Peruvian                       |   0 |       0 |          0 |           0 |        0 |               0 |
| Pizza                          |   0 |     254 |        421 |         486 |      349 |             109 |
| Polish                         |   0 |       0 |          0 |           0 |        0 |               0 |
| Polynesian                     |   0 |       0 |          0 |           0 |        0 |               0 |
| Portuguese                     |   0 |       0 |          0 |           0 |        0 |               0 |
| Russian                        |   0 |       0 |          0 |           0 |        0 |               0 |
| Salads                         |   0 |       0 |          0 |           0 |        0 |               0 |
| Sandwiches                     |   0 |       0 |          0 |           0 |        0 |               0 |
| Sandwiches/Salads/Mixed Buffet |   0 |       0 |          0 |           0 |        0 |               0 |
| Scandinavian                   |   0 |       0 |          0 |           0 |        0 |               0 |
| Seafood                        |   0 |       0 |          0 |           0 |        0 |               0 |
| Soul Food                      |   0 |       0 |          0 |           0 |        0 |               0 |
| Soups                          |   0 |       0 |          0 |           0 |        0 |               0 |
| Soups/Salads/Sandwiches        |   0 |       0 |          0 |           0 |        0 |               0 |
| Southeast Asian                |   0 |       0 |          0 |           0 |        0 |               0 |
| Southwestern                   |   0 |       0 |          0 |           0 |        0 |               0 |
| Spanish                        |   0 |       0 |          0 |           0 |        0 |               0 |
| Steakhouse                     |   0 |       0 |          0 |           0 |        0 |               0 |
| Tapas                          |   0 |       0 |          0 |           0 |        0 |               0 |
| Tex-Mex                        |   0 |       0 |          0 |           0 |        0 |               0 |
| Thai                           |   0 |       0 |          0 |           0 |        0 |               0 |
| Turkish                        |   0 |       0 |          0 |           0 |        0 |               0 |
| Vegan                          |   0 |       0 |          0 |           0 |        0 |               0 |
| Vegetarian                     |   0 |       0 |          0 |           0 |        0 |               0 |

**Row %: each cuisine's borough distribution (sums to 100%):**

| cuisine_description            |   0 |   Bronx |   Brooklyn |   Manhattan |   Queens |   Staten Island |
|:-------------------------------|----:|--------:|-----------:|------------:|---------:|----------------:|
|                                | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Afghan                         | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| African                        | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| American                       |   0 |     6.5 |       22.5 |        51.4 |     16.3 |             3.3 |
| Armenian                       | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Asian/Asian Fusion             | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Australian                     | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Bagels/Pretzels                | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Bakery Products/Desserts       |   0 |     9.2 |       24.1 |        33.6 |     29.7 |             3.4 |
| Bangladeshi                    | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Barbecue                       | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Basque                         | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Bottled Beverages              | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Brazilian                      | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Cajun                          | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Californian                    | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Caribbean                      |   0 |    14.6 |       47.3 |         7.3 |     30.4 |             0.4 |
| Chicken                        |   0 |    22.2 |       29.4 |        20.8 |     24.5 |             3.1 |
| Chilean                        | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Chimichurri                    | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Chinese                        |   0 |    10.3 |       29.1 |        23.6 |     33   |             4   |
| Chinese/Cuban                  | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Chinese/Japanese               | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Coffee/Tea                     |   0 |     3.9 |       27.3 |        50.4 |     15.7 |             2.7 |
| Continental                    | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Creole                         | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Creole/Cajun                   | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Czech                          | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Donuts                         |   0 |    13.6 |       22.2 |        30.5 |     26.8 |             7   |
| Eastern European               | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Egyptian                       | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| English                        | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Ethiopian                      | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Filipino                       | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| French                         | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Frozen Desserts                | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Fruits/Vegetables              | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Fusion                         | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| German                         | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Greek                          | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Hamburgers                     | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Haute Cuisine                  | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Hawaiian                       | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Hotdogs                        | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Hotdogs/Pretzels               | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Indian                         | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Indonesian                     | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Iranian                        | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Irish                          | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Italian                        |   0 |     4   |       18.1 |        60.3 |     10.9 |             6.6 |
| Japanese                       |   0 |     2.8 |       22.8 |        52.6 |     17.5 |             4.3 |
| Jewish/Kosher                  | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Juice, Smoothies, Fruit Salads | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Korean                         | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Latin American                 |   0 |    17.3 |       19.6 |        18.8 |     43   |             1.3 |
| Lebanese                       | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Mediterranean                  | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Mexican                        |   0 |    13.9 |       29.8 |        27.1 |     24   |             5.2 |
| Middle Eastern                 | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Moroccan                       | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| New American                   | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| New French                     | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Not Listed/Not Applicable      | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Nuts/Confectionary             | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Other                          | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Pakistani                      | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Pancakes/Waffles               | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Peruvian                       | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Pizza                          |   0 |    15.7 |       26   |        30   |     21.6 |             6.7 |
| Polish                         | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Polynesian                     | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Portuguese                     | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Russian                        | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Salads                         | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Sandwiches                     | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Sandwiches/Salads/Mixed Buffet | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Scandinavian                   | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Seafood                        | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Soul Food                      | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Soups                          | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Soups/Salads/Sandwiches        | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Southeast Asian                | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Southwestern                   | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Spanish                        | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Steakhouse                     | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Tapas                          | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Tex-Mex                        | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Thai                           | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Turkish                        | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Vegan                          | nan |   nan   |      nan   |       nan   |    nan   |           nan   |
| Vegetarian                     | nan |   nan   |      nan   |       nan   |    nan   |           nan   |

## D1 · Council-district closure-rate outliers

> *NYC has 51 City Council districts. Which are the closure-rate outliers (top and bottom 5)?*

**Top 5 (highest closure rate):**

|   council_district |    n |   n_closed |   closure_pct |
|-------------------:|-----:|-----------:|--------------:|
|                 45 |  706 |         27 |          3.82 |
|                 40 | 1126 |         42 |          3.73 |
|                 48 |  933 |         32 |          3.43 |
|                 23 |  802 |         26 |          3.24 |
|                 24 |  809 |         26 |          3.21 |

**Bottom 5 (lowest closure rate):**

|   council_district |    n |   n_closed |   closure_pct |
|-------------------:|-----:|-----------:|--------------:|
|                 30 |  952 |         10 |          1.05 |
|                 04 | 5597 |         48 |          0.86 |
|                 13 | 1029 |          8 |          0.78 |
|                 50 |  952 |          7 |          0.74 |
|                 51 |  812 |          4 |          0.49 |

## D2 · Best/worst ZIP codes by critical-violation rate

> *Across NYC ZIPs (≥200 inspections), which had the highest and lowest share of inspections finding a critical violation?*

**Top 10 (highest critical-violation rate):**

|   zipcode |    n |   n_crit | boro   |   crit_pct |
|----------:|-----:|---------:|:-------|-----------:|
|     10453 |  311 |      288 | Bronx  |      92.6  |
|     11372 | 1156 |     1066 | Queens |      92.21 |
|     10468 |  327 |      300 | Bronx  |      91.74 |
|     11368 |  789 |      721 | Queens |      91.38 |
|     11355 |  654 |      593 | Queens |      90.67 |
|     10465 |  212 |      192 | Bronx  |      90.57 |
|     11354 | 1435 |     1299 | Queens |      90.52 |
|     11418 |  250 |      226 | Queens |      90.4  |
|     11358 |  400 |      361 | Queens |      90.25 |
|     11104 |  315 |      284 | Queens |      90.16 |

**Bottom 10 (lowest critical-violation rate):**

|   zipcode |    n |   n_crit | boro      |   crit_pct |
|----------:|-----:|---------:|:----------|-----------:|
|     11217 |  775 |      631 | Brooklyn  |      81.42 |
|     11235 |  461 |      374 | Brooklyn  |      81.13 |
|     11238 |  674 |      546 | Brooklyn  |      81.01 |
|     10004 |  404 |      327 | Manhattan |      80.94 |
|     10038 |  532 |      429 | Manhattan |      80.64 |
|     11201 | 1276 |     1023 | Brooklyn  |      80.17 |
|     11225 |  469 |      376 | Brooklyn  |      80.17 |
|     11216 |  615 |      492 | Brooklyn  |      80    |
|     10451 |  401 |      316 | Bronx     |      78.8  |
|     10007 |  469 |      352 | Manhattan |      75.05 |

## D4 · Tourist zones vs city baseline

> *Are restaurants in tourist-magnet ZIPs (['10004', '10005', '10018', '10019', '10036', '10038', '11201', '11224']) inspected differently from the rest of NYC?*

**Side-by-side:**

| zone         |     n |   n_restaurants |   insp_per_rest |   closure_pct |   crit_pct |   median_score |
|:-------------|------:|----------------:|----------------:|--------------:|-----------:|---------------:|
| Rest of NYC  | 69951 |           24724 |            2.83 |          1.8  |      85.74 |             13 |
| Tourist ZIPs |  6945 |            2553 |            2.72 |          1.18 |      82.55 |             12 |

## E1 · Day-of-week pattern in inspections

> *Which weekday does the city inspect on most? Do Monday/Friday inspections find more critical violations than midweek?*

**By weekday:**

| dow       |     n |   share_pct |   closure_pct |   crit_pct |   median_score |
|:----------|------:|------------:|--------------:|-----------:|---------------:|
| Monday    | 14108 |       18.35 |          1.94 |      86.33 |             13 |
| Tuesday   | 16542 |       21.51 |          1.78 |      86.81 |             13 |
| Wednesday | 16859 |       21.92 |          1.78 |      86.67 |             13 |
| Thursday  | 17138 |       22.29 |          1.81 |      87.15 |             13 |
| Friday    |  9476 |       12.32 |          1.56 |      83.78 |             12 |
| Saturday  |  2288 |        2.98 |          0.61 |      58.87 |              9 |
| Sunday    |   485 |        0.63 |          0.41 |      69.69 |             12 |

## F2 · Score recovery after a C-zone initial

> *When a restaurant fails its initial cycle inspection (score 28+ = C-zone), how much does its score drop by re-inspection?*
- Pairs where initial score ≥ 28 (C-zone): **4,118**.
- Median initial score: **37**.
- Median re-inspection score: **13**.
- Median score drop: **22 points**.
- Recovered to A: **57%**.
- Median days to re-inspection: **64**.
- Cases where score got *worse* on re-inspection: **342** (8.3%).

## H1 · What the BORO = '0' restaurants actually are

> *363 raw rows have BORO = '0'. At inspection grain, what are these places? Airports? Stadiums?*
- Rows in dense window: **85** (across **30** distinct restaurants).

**Top streets / building strings:**

|    | street       |   building |   inspections |
|---:|:-------------|-----------:|--------------:|
|  0 | 8TH AVE      |        421 |            10 |
|  1 | SMITH STREET |        128 |             7 |
|  2 | 3rd Ave      |       1000 |             6 |
|  3 | RICHMOND RD  |        598 |             6 |
|  4 | COLUMBIA PL  |          6 |             5 |
|  5 | FRANKLIN ST  |        113 |             4 |
|  6 | 5TH AVE      |        486 |             4 |
|  7 | Madison ave  |         25 |             4 |
|  8 | PARK AVE     |          2 |             4 |
|  9 | HYLAN BLVD   |       2510 |             4 |
| 10 | AVENUE C     |        102 |             3 |
| 11 | W 40TH ST    |         41 |             3 |
| 12 | REED ST      |         24 |             3 |
| 13 | CENTRAL AVE  |        447 |             3 |
| 14 | COLUMBUS AVE |        555 |             3 |

**Top DBA names:**

| dba                                                 |   inspections |
|:----------------------------------------------------|--------------:|
| BAR TABAC                                           |             7 |
| EL PASO COFFEE SHOP                                 |             6 |
| PASTRAMI QUEEN                                      |             5 |
| CHA CHA MATCHA (LOCATED INSIDE MOYNIHAN TRAIN HALL) |             5 |
| LAUNDRY & LATTE                                     |             5 |
| SOUTH SLOPE RESTAURANT & BAR                        |             4 |
| TERIYAKI ONE                                        |             4 |
| SERENECO                                            |             4 |
| HI LOT                                              |             3 |
| CAFFEINE UNDERGROUND                                |             3 |
| BROOKLYN CRAB                                       |             3 |
| PLANTSHED                                           |             3 |
| FRENCH LOUIE                                        |             2 |
| JUICE GENERATION                                    |             2 |
| WISE                                                |             2 |

**ZIP codes (if present):**

| zipcode   |   inspections |
|:----------|--------------:|
| 10116     |            10 |
| <blank>   |             9 |
| 07307     |             7 |
| 11701     |             7 |
| 10304     |             6 |
| 08550     |             5 |
| 11542     |             4 |
| 10538     |             4 |
| 07071     |             4 |
| 10306     |             4 |