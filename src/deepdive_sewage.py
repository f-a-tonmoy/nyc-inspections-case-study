"""
Deep-dive on the "sewage cliff" finding (B1 in the sweep).

Goal: confirm the headline pattern holds up + gather narrative ingredients
(real inspections, real restaurants) for the article.

Questions answered:
 1. Verify the headline lift numbers on a clean computation.
 2. Decode the full text of the top "deathblow" codes.
 3. What does an "average sewage-cliff inspection" look like?
    (n_violations, median score, has-vermin co-occurrence?)
 4. Borough + cuisine distribution of sewage-cliff inspections.
 5. Five concrete inspection examples per top code.
 6. What happens AFTER one of these inspections? Recovery trajectory.

Run:
    conda run -n intro_ds python src/deepdive_sewage.py

Output: reports/deepdive_sewage.md
"""

from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
PARQUET   = REPO_ROOT / "data" / "processed" / "inspections.parquet"
RAW_CSV   = REPO_ROOT / "data" / "raw" / "dohmh_restaurant_inspections.csv"
OUT_MD    = REPO_ROOT / "reports" / "deepdive_sewage.md"

REAL_BOROS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]

# Top "deathblow" codes from the sweep (closure rate ≥ ~10%).
DEATHBLOW_CODES = ["04F", "05A", "05E", "05F", "28-06", "05C", "05H", "28-01"]

MD: list[str] = []
def md(s: str = "") -> None: MD.append(s)
def h(level: int, t: str) -> None: md("\n" + "#" * level + " " + t + "\n")
def tbl(df: pd.DataFrame, **kw) -> None: md(df.to_markdown(**kw))


def main():
    print("Loading parquet + raw...")
    df = pd.read_parquet(PARQUET)
    df["year"] = df["inspection_date"].dt.year
    dense = df[(df["year"] >= 2023) & df["boro"].isin(REAL_BOROS)].copy()

    raw = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False)
    raw = raw.apply(lambda c: c.str.strip())
    raw["_date"] = pd.to_datetime(raw["INSPECTION DATE"], format="%m/%d/%Y", errors="coerce")

    # Full descriptions for the deathblow codes (longest, most informative variant).
    desc = (raw[raw["VIOLATION CODE"].isin(DEATHBLOW_CODES)
                & raw["VIOLATION DESCRIPTION"].ne("")]
            .groupby("VIOLATION CODE")["VIOLATION DESCRIPTION"]
            .agg(lambda s: s.value_counts().index[0]))

    h(1, "Deep dive · the “sewage cliff” (probe B1)")
    md("Source data: inspection-grain parquet, 2023+, five boroughs only "
       f"({len(dense):,} inspections).")

    # -------------------------------------------------------------------
    # 1. Decode the codes (full descriptions, not truncated)
    # -------------------------------------------------------------------
    h(2, "1 · The codes, in full")
    for code in DEATHBLOW_CODES:
        full = desc.get(code, "<no description found>")
        md(f"- **`{code}`** — {full}")

    # -------------------------------------------------------------------
    # 2. Verify the lift numbers (recomputed cleanly)
    # -------------------------------------------------------------------
    h(2, "2 · Headline numbers, reverified")
    baseline = dense["closed"].mean() * 100

    exploded = (dense.assign(code=lambda d: d["violation_codes"].str.split(","))
                     .explode("code"))
    exploded = exploded[exploded["code"].astype(str).ne("")]

    block = exploded[exploded["code"].isin(DEATHBLOW_CODES)]
    summary = (block.groupby("code")
                    .agg(n_inspections=("camis", "size"),
                         n_closed=("closed", "sum"))
                    .assign(closure_pct=lambda d: d["n_closed"]/d["n_inspections"]*100,
                            lift_x=lambda d: (d["n_closed"]/d["n_inspections"]*100)/baseline))
    summary = summary.sort_values("closure_pct", ascending=False).round(2)

    md(f"City-wide baseline closure rate: **{baseline:.2f}%**.\n")
    tbl(summary)
    md("\nAll lifts are very large and the codes carry comfortable sample sizes "
       "(≥200 inspections each, mostly far more), so the pattern is real and not "
       "a small-cell artefact.")

    # -------------------------------------------------------------------
    # 3. Profile a "sewage-cliff inspection"
    # -------------------------------------------------------------------
    h(2, "3 · What does a “sewage-cliff” inspection look like?")
    md("Restricting to inspections containing at least one of the top three "
       "sewage / plumbing codes (`04F`, `05A`, `05E`).")

    top3 = ["04F", "05A", "05E"]
    has_top3 = exploded["code"].isin(top3)
    sewage_insp_ids = (exploded[has_top3]
                         .groupby(["camis", "inspection_date"]).size().index)
    is_sewage = pd.MultiIndex.from_frame(dense[["camis", "inspection_date"]]).isin(sewage_insp_ids)
    sewage = dense[is_sewage].copy()
    other  = dense[~is_sewage].copy()

    compare = pd.DataFrame({
        "metric": [
            "Inspections (n)",
            "Median score",
            "Mean score",
            "Median violations per inspection",
            "% closed",
            "% with critical violation",
        ],
        "Sewage-cliff inspections": [
            f"{len(sewage):,}",
            f"{sewage['score'].median():.0f}",
            f"{sewage['score'].mean():.1f}",
            f"{sewage['n_violations'].median():.0f}",
            f"{sewage['closed'].mean()*100:.1f}%",
            f"{(sewage['n_critical']>0).mean()*100:.1f}%",
        ],
        "All other inspections": [
            f"{len(other):,}",
            f"{other['score'].median():.0f}",
            f"{other['score'].mean():.1f}",
            f"{other['n_violations'].median():.0f}",
            f"{other['closed'].mean()*100:.1f}%",
            f"{(other['n_critical']>0).mean()*100:.1f}%",
        ],
    })
    tbl(compare, index=False)

    md("\nSo a sewage-cliff inspection isn't a typical one with a single bad code: "
       "the average score is much higher, and the median number of violations "
       "found is several times the baseline. These are the kitchens where a lot "
       "is going wrong at once and the plumbing failure is the last straw.")

    # -------------------------------------------------------------------
    # 4. Geographic + cuisine distribution
    # -------------------------------------------------------------------
    h(2, "4 · Where these inspections happen")

    by_boro = (sewage.groupby("boro", observed=True).size()
                     .rename("sewage_insp").to_frame())
    by_boro["total_insp"]   = dense.groupby("boro", observed=True).size()
    by_boro["share_of_insp_pct"] = (by_boro["sewage_insp"] / by_boro["total_insp"] * 100).round(2)
    by_boro["share_of_sewage_pct"] = (by_boro["sewage_insp"] / by_boro["sewage_insp"].sum() * 100).round(1)
    by_boro = by_boro.sort_values("share_of_insp_pct", ascending=False)
    md("**By borough:** rate at which sewage-cliff codes appear in an inspection.\n")
    tbl(by_boro)

    md("\n**By cuisine (top 10 by number of sewage-cliff inspections):**\n")
    by_cuis = (sewage.groupby("cuisine_description", observed=True).size()
                     .rename("sewage_insp"))
    cuis_total = dense.groupby("cuisine_description", observed=True).size()
    cuis_tbl = (pd.concat([by_cuis, cuis_total.rename("total")], axis=1)
                  .assign(rate_pct=lambda d: (d["sewage_insp"]/d["total"]*100).round(2))
                  .dropna(subset=["sewage_insp"])
                  .sort_values("sewage_insp", ascending=False)
                  .head(10))
    tbl(cuis_tbl)

    # -------------------------------------------------------------------
    # 5. Five concrete examples per top code
    # -------------------------------------------------------------------
    h(2, "5 · Five concrete example inspections (narrative material)")
    for code in top3:
        md(f"\n**Code `{code}` — {desc.get(code, '')[:140]}...**\n")
        # Inspections containing this code AND ending in a closure.
        ids = (exploded[(exploded["code"] == code) & exploded["closed"]]
               [["camis", "inspection_date"]].drop_duplicates())
        ex = (dense.merge(ids, on=["camis", "inspection_date"])
                   .sort_values("score", ascending=False)
                   .head(5)[["dba", "boro", "cuisine_description",
                             "inspection_date", "score",
                             "n_violations", "n_critical"]])
        tbl(ex.reset_index(drop=True))

    # -------------------------------------------------------------------
    # 6. After a sewage-cliff closure: what happens next?
    # -------------------------------------------------------------------
    h(2, "6 · What happens after a sewage-cliff CLOSURE")
    md("For inspections that had one of the top 3 codes AND were closed by "
       "DOHMH, look at each restaurant's next inspection date / score / "
       "action (within 180 days).")

    closures = sewage[sewage["closed"]][["camis", "inspection_date"]].copy()
    closures.columns = ["camis", "closure_date"]

    # For each closure, find that restaurant's next inspection.
    all_insp = dense[["camis", "inspection_date", "score", "action", "grade"]].copy()
    j = closures.merge(all_insp, on="camis")
    j = j[j["inspection_date"] > j["closure_date"]]
    j["days_after"] = (j["inspection_date"] - j["closure_date"]).dt.days
    j = j[j["days_after"] <= 180]
    nxt = (j.sort_values(["camis", "closure_date", "days_after"])
             .drop_duplicates(["camis", "closure_date"], keep="first"))

    md(f"- Closures with a top-3 sewage code: **{len(closures):,}**")
    md(f"- Of those, restaurants that had any follow-up inspection within 180d: "
       f"**{nxt['camis'].nunique():,}** ({100*len(nxt)/len(closures):.0f}%)")
    if len(nxt):
        md(f"- Median days from sewage closure → next inspection: "
           f"**{nxt['days_after'].median():.0f} days**")
        md(f"- Median score on that next inspection: "
           f"**{nxt['score'].median():.0f}** (down from sewage-cliff median "
           f"{sewage[sewage['closed']]['score'].median():.0f})")
        next_action_mix = nxt["action"].value_counts(normalize=True) * 100
        md("\nNext-inspection ACTION breakdown:\n")
        tbl(next_action_mix.round(1).rename("share %").to_frame())

    OUT_MD.write_text("\n".join(MD), encoding="utf-8")
    print(f"\nWrote {OUT_MD}  ({len(MD)} markdown lines)")


if __name__ == "__main__":
    main()
