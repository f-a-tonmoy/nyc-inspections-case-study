# Insight Discovery Plan

What we'll go hunting for before we write anything. Each item is a specific,
computable question. After this plan is approved we run a **discovery sweep**
that computes every probe, then we pick the strongest findings for the
article based on what the data actually says.

## Tagging key
- **⭐ FUN** — quirky / striking / story-driven anomaly
- **⚖ EQUITY** — fits the original oversight-equity framing
- **🎯 BOTH** — interesting *and* fits the framing
- **🧪 LONGSHOT** — might come up empty but worth a quick check

I've marked my hunches with a `★` next to the ones I think are most likely to
yield something worth writing about. Take the marks as a starting point only.

---

## A · Restaurant-level outliers (the superlatives)

| # | Probe | Tag |
|---|---|---|
| A1 ★ | Which restaurant has the **most violations ever recorded in a single inspection**? (Today's record: 24 rows / 12 codes. What place is that, what cuisine, what was happening that day?) | ⭐ FUN |
| A2 ★ | Which restaurants have been **closed by DOHMH more than once**? Who's the recidivism champion? | ⭐ FUN |
| A3 | How many restaurants achieved a **perfect zero-violation initial cycle inspection**? Where do these saints cluster? | ⭐ FUN |
| A4 ★ | **The biggest comebacks** — restaurants whose initial cycle score was 60+ (very bad) but got an A on re-inspection. How much can a kitchen turn around in weeks? | ⭐ FUN |
| A5 | The **persistent strugglers** — restaurants that have never scored an A across multiple visits. | ⭐ FUN |
| A6 | The most-inspected single restaurant in the window (highest visit count). | ⭐ FUN |

## B · Violation-code anomalies

| # | Probe | Tag |
|---|---|---|
| B1 ★ | Which violation codes are the **strongest predictors of an on-the-spot closure**? ("If your inspection contains code X, your probability of being closed jumps from baseline to N×.") | 🎯 BOTH |
| B2 ★ | **Mice / rats / roaches** — what % of NYC inspections find evidence of vermin? Which neighborhoods are worst? (Specific DOHMH codes exist for each.) | 🎯 BOTH |
| B3 | Which violation codes are **rarest** — the long-tail oddities almost no inspector ever writes? Sometimes these have great stories. | ⭐ FUN |
| B4 | **Co-occurrence patterns**: which pairs of violations tend to show up together? (E.g., "if you have rats you also have…") | 🧪 LONGSHOT |
| B5 ★ | Which **single violation code** has the highest critical-flag rate? Which boring-sounding code is actually deadly? | ⭐ FUN |

## C · Cuisine deep-dive

| # | Probe | Tag |
|---|---|---|
| C1 ★ | Which **cuisines** have the highest critical-violation rate? Highest closure rate? (Pizza vs sushi vs taco trucks vs French — who's actually the worst?) | ⭐ FUN |
| C2 | Which cuisines specialize in which violation patterns? (E.g., do certain cuisines repeatedly fail at temperature control?) | ⭐ FUN |
| C3 ★ | **Cuisine geography** — which cuisines are concentrated where? (Important confound for the borough findings.) | 🎯 BOTH |
| C4 | Which cuisines have the **best median score**? The bar for "good" by cuisine. | ⭐ FUN |
| C5 ★ | **One-of-a-kind cuisines** — cuisines with very few restaurants in NYC; the curiosity tail. | ⭐ FUN |

## D · Geography beyond borough

| # | Probe | Tag |
|---|---|---|
| D1 ★ | **Council district** closure rates — sub-borough granularity. Which 51 districts are the outliers? | ⚖ EQUITY |
| D2 ★ | **ZIP-code level** critical-violation rates — find the dirtiest and cleanest ZIPs and the gap between them. | 🎯 BOTH |
| D3 | **Neighborhood (NTA)** rankings — the data has NTA names built in, no spatial join needed. | ⚖ EQUITY |
| D4 ★ | **Tourist-zone effect** — are restaurants in Times Square / Coney Island / South Street Seaport inspected differently from neighboring residential blocks? | ⭐ FUN |
| D5 | Adjacent-ZIP **border discontinuities** — pairs of neighboring ZIPs with very different outcomes. | 🧪 LONGSHOT |

## E · Time patterns

| # | Probe | Tag |
|---|---|---|
| E1 ★ | **Day-of-week effect** — which weekday do inspections happen on most? Do Friday or Monday inspections find more / fewer violations than midweek? | ⭐ FUN |
| E2 | **Seasonality** — summer heat = food spoilage risk. Are critical-flag rates higher in July–August? | ⭐ FUN |
| E3 | **Inspection ramp** — has the city's monthly inspection volume been growing, flat, or shrinking over the dense window? | ⚖ EQUITY |
| E4 ★ | **Holiday gaps** — visible drops around Thanksgiving / Christmas / July 4? Are inspectors taking the same vacations everyone else is? | ⭐ FUN |
| E5 | **Inspector cadence per restaurant** — what's the typical interval between any two visits to the same restaurant, ignoring re-inspection rules? | ⚖ EQUITY |

## F · Recovery & recidivism

| # | Probe | Tag |
|---|---|---|
| F1 ★ | After a **temporary closure**, how long until DOHMH formally re-opens the restaurant? Distribution + by-borough. | 🎯 BOTH |
| F2 ★ | **Score recovery** — when a restaurant fails its initial cycle (28+ score, a "C-zone"), what's its median score on re-inspection? Do most claw back to an A? | ⭐ FUN |
| F3 | **Repeat closures** — how often does a re-closed restaurant get re-closed again? | 🎯 BOTH |
| F4 | Predictors of **future closure** from prior violation history. | 🧪 LONGSHOT |

## G · Naming & DBA oddities (pure fun)

| # | Probe | Tag |
|---|---|---|
| G1 | Restaurants with the **longest DBA names**; the shortest; all-caps screamers. | ⭐ FUN |
| G2 ★ | **Name twins** — how many restaurants share the same DBA name? Are these chains, franchises, or coincidences? | ⭐ FUN |
| G3 | The most-common restaurant name in NYC. | ⭐ FUN |

## H · The "0" mysteries (data anomalies as findings)

| # | Probe | Tag |
|---|---|---|
| H1 | The **363 restaurants with BORO = "0"** — what are they? Mall food courts? Stadiums? Airports? (The example we saw was at JFK Terminal 4.) | ⭐ FUN |
| H2 ★ | **GRADE "Z"** (pending) — does Z status linger longer in some boroughs? Average days from Z to a final letter grade. | ⚖ EQUITY |
| H3 | Restaurants with **only the 1900 placeholder** — how many are "permitted but never inspected"? How long have they been pending? | 🧪 LONGSHOT |

---

## My recommended starter sweep (12 probes)

If you want me to just go, this is the set I'd run first. Mix of fun and
equity, chosen for highest expected payoff:

1. **A2** — repeat-closure restaurants
2. **A4** — comeback kings (60+ → A)
3. **B1** — violation codes that trigger closure
4. **B2** — vermin findings by neighborhood
5. **C1** — cuisines ranked by closure rate
6. **C3** — cuisine geography (to defuse the confound in the borough story)
7. **D1** — council-district closure outliers
8. **D2** — best/worst ZIPs
9. **D4** — tourist-zone vs residential
10. **E1** — day-of-week patterns
11. **F2** — score recovery after a C-zone initial
12. **H1** — what are the "BORO = 0" restaurants

After the sweep we look at the actual numbers, kill the ones that turned up
flat or boring, and the remaining 3–5 *real* anomalies become the article.

---

## Workflow we'll follow

```
[1] (this doc)  PLAN  - approve the candidate list
[2] SWEEP            - one script computes every probe; outputs a JSON of results + a printable summary
[3] REVIEW           - read the sweep output together, pick the 3-5 best
[4] DEEP DIVE        - for each winner, build the exact chart and write the paragraph
[5] ARTICLE          - rebuild article.html around those winners (current draft is throwaway)
```

## Decisions I need from you

1. **Tone** — fun-quirky (Atlas Obscura), serious data-journalism (NYT
   Upshot), or somewhere between?
2. **Equity lens** — still binding from the original brief, or open to
   non-equity findings if they're the most interesting?
3. **Starter probes** — accept my recommended 12, or change the set?
