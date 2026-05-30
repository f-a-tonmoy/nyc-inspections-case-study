"""
Discovery sweep — compute all 12 starter probes from the insight plan.

For each probe, emit a section in reports/sweep.md with the headline numbers
and a short "what's striking" note. The user reads this output and picks
which findings to deep-dive for the article.

Run:
    conda run -n intro_ds python src/sweep_insights.py

Probes (from reports/insight_plan.md):
    A2  repeat-closure restaurants (closure-count leaderboard)
    A4  biggest comebacks (initial 60+ -> re-inspection A)
    B1  violation codes that most predict on-the-spot closure
    B2  vermin (mice/rats/roaches/flies) findings by neighborhood
    C1  cuisines ranked by closure rate
    C3  cuisine geography (top cuisines' borough mix)
    D1  council-district closure-rate outliers
    D2  best/worst ZIP codes for critical-violation rate
    D4  tourist zones vs city baseline
    E1  day-of-week pattern in inspections
    F2  score recovery after a C-zone initial inspection
    H1  what the BORO=0 mystery restaurants actually are
"""

from __future__ import annotations
from pathlib import Path
from textwrap import dedent

import json
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
PARQUET   = REPO_ROOT / "data" / "processed" / "inspections.parquet"
RAW_CSV   = REPO_ROOT / "data" / "raw" / "dohmh_restaurant_inspections.csv"
OUT_MD    = REPO_ROOT / "reports" / "sweep.md"
OUT_JSON  = REPO_ROOT / "reports" / "sweep.json"

REAL_BOROS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]

# Tourist-zone ZIPs (high-confidence single-purpose-tourist neighborhoods).
TOURIST_ZIPS = {
    "10036",  # Times Square / Theater District
    "10019",  # Hell's Kitchen / Lincoln Center fringe
    "10018",  # Garment District
    "10038",  # South Street Seaport / FiDi-east
    "10004",  # Battery / Statue ferries
    "10005",  # Wall Street
    "11201",  # Brooklyn Bridge / DUMBO
    "11224",  # Coney Island
}

# ---------------------------------------------------------------------------
# Output accumulator: every section appends to MD; JSON keeps machine-readable
# bits in case we want to chart them later.
# ---------------------------------------------------------------------------
MD: list[str] = []
JS: dict = {}


def h(level: int, text: str) -> None:
    MD.append("\n" + "#" * level + " " + text + "\n")


def md(text: str = "") -> None:
    MD.append(text)


def tbl(df: pd.DataFrame) -> None:
    """Append a markdown table from a small dataframe."""
    md(df.to_markdown(index=True))


def to_jsonable(obj):
    """Recursively coerce numpy/pandas types into plain Python for json.dump."""
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pd.Series):
        return to_jsonable(obj.to_dict())
    if isinstance(obj, pd.DataFrame):
        return to_jsonable(obj.reset_index().to_dict(orient="records"))
    return obj


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load():
    df = pd.read_parquet(PARQUET)
    df["year"] = df["inspection_date"].dt.year
    dense = df[(df["year"] >= 2023)].copy()
    dense_real = dense[dense["boro"].isin(REAL_BOROS)].copy()
    return df, dense, dense_real


# ---------------------------------------------------------------------------
# A2 — repeat-closure restaurants
# ---------------------------------------------------------------------------
def probe_A2(dense: pd.DataFrame):
    h(2, "A2 · The repeat-closure leaderboard")
    md("> *How many NYC restaurants have been closed by DOHMH more than once "
       "in the rolling window, and who's the champion?*")

    closed = dense[dense["closed"]]
    counts = (closed.groupby(["camis", "dba", "boro"], observed=True)
                    .size().rename("n_closures").reset_index())
    multi = counts[counts["n_closures"] >= 2].sort_values("n_closures", ascending=False)

    md(f"- **{len(counts):,}** distinct restaurants had at least one DOHMH "
       f"closure in the window.")
    md(f"- **{len(multi):,}** were closed *more than once*.")
    md(f"- Maximum closures by a single restaurant: **{int(counts['n_closures'].max())}**.")
    md("\n**Top 15 recidivists:**\n")
    tbl(multi.head(15).reset_index(drop=True))

    JS["A2"] = {
        "n_restaurants_closed_once_plus": len(counts),
        "n_restaurants_closed_2plus":     len(multi),
        "max_closures_by_one":            int(counts["n_closures"].max()),
        "top15":                          multi.head(15),
    }


# ---------------------------------------------------------------------------
# Pair-builder shared by A4 and F2
# ---------------------------------------------------------------------------
def cycle_pairs(dense: pd.DataFrame, max_days: int = 90) -> pd.DataFrame:
    ci = dense[dense["inspection_type"] == "Cycle Inspection / Initial Inspection"][
        ["camis", "inspection_date", "boro", "score", "grade", "dba"]
    ].rename(columns={"inspection_date": "initial_date",
                      "score": "initial_score", "grade": "initial_grade"})
    cr = dense[dense["inspection_type"] == "Cycle Inspection / Re-inspection"][
        ["camis", "inspection_date", "score", "grade"]
    ].rename(columns={"inspection_date": "reinsp_date",
                      "score": "reinsp_score", "grade": "reinsp_grade"})
    pairs = ci.merge(cr, on="camis")
    pairs = pairs[pairs["reinsp_date"] > pairs["initial_date"]]
    pairs["days"] = (pairs["reinsp_date"] - pairs["initial_date"]).dt.days
    pairs = (pairs.sort_values(["camis", "initial_date", "days"])
                  .drop_duplicates(["camis", "initial_date"], keep="first"))
    return pairs[pairs["days"].between(1, max_days)].copy()


# ---------------------------------------------------------------------------
# A4 — biggest comebacks
# ---------------------------------------------------------------------------
def probe_A4(dense: pd.DataFrame):
    h(2, "A4 · The biggest comebacks (initial 60+ → re-inspection A)")
    md("> *How many restaurants posted a brutal initial cycle score (60+) "
       "and recovered to an A on re-inspection? What's the median timespan?*")

    pairs = cycle_pairs(dense, max_days=180)
    severe = pairs[pairs["initial_score"] >= 60].copy()
    came_back = severe[severe["reinsp_grade"] == "A"].copy()
    came_back["score_drop"] = came_back["initial_score"] - came_back["reinsp_score"]

    md(f"- Initial-cycle inspections scoring **60+** (a deep-C / worse): "
       f"**{len(severe):,}** paired with a re-inspection.")
    md(f"- Of those, **{len(came_back):,}** ({100*len(came_back)/max(len(severe),1):.0f}%) "
       f"came back with an A.")
    if len(came_back):
        md(f"- Median time from initial to A re-inspection: "
           f"**{came_back['days'].median():.0f} days**.")
        md(f"- Median score drop: **{came_back['score_drop'].median():.0f} points**.")
        md(f"- Maximum score drop observed: **{int(came_back['score_drop'].max())} points** "
           f"(initial {int(came_back.loc[came_back['score_drop'].idxmax(),'initial_score'])} "
           f"→ re-inspection {int(came_back.loc[came_back['score_drop'].idxmax(),'reinsp_score'])}).")
        md("\n**Top 10 single-inspection comebacks:**\n")
        top = came_back.nlargest(10, "score_drop")[
            ["dba", "boro", "initial_date", "initial_score",
             "reinsp_score", "days"]
        ].reset_index(drop=True)
        tbl(top)

    JS["A4"] = {
        "n_severe_pairs": len(severe),
        "n_comebacks_to_A": len(came_back),
        "median_days_to_A": float(came_back["days"].median()) if len(came_back) else None,
        "median_score_drop": float(came_back["score_drop"].median()) if len(came_back) else None,
    }


# ---------------------------------------------------------------------------
# B1 — violation codes that predict on-the-spot closure
# ---------------------------------------------------------------------------
def probe_B1(dense: pd.DataFrame, raw_codes_desc: pd.DataFrame):
    h(2, "B1 · Violation codes that most predict closure")
    md("> *Which violation codes, when present, raise the probability the "
       "inspection ends in a DOHMH closure most above the city baseline?*")

    baseline = dense["closed"].mean() * 100
    exploded = (dense.assign(code=lambda d: d["violation_codes"].str.split(","))
                     .explode("code"))
    exploded = exploded[exploded["code"].astype(str).ne("")]

    agg = exploded.groupby("code").agg(
        n_inspections=("camis", "size"),
        n_closed=("closed", "sum"),
    )
    agg = agg[agg["n_inspections"] >= 200]  # min cell size, kill noise
    agg["closure_rate_pct"] = agg["n_closed"] / agg["n_inspections"] * 100
    agg["lift_vs_baseline"] = agg["closure_rate_pct"] / baseline

    # Attach the human-readable description (mode per code from raw).
    agg = agg.merge(raw_codes_desc, left_index=True, right_index=True, how="left")
    agg = agg.sort_values("closure_rate_pct", ascending=False)

    md(f"- City-wide closure rate (baseline): **{baseline:.2f}%** of inspections.")
    md("- Codes are filtered to those with ≥ 200 inspection appearances so a "
       "single rare-code closure can't dominate.")
    md("\n**Top 15 codes by closure rate when present:**\n")
    top = agg.head(15)[["n_inspections", "closure_rate_pct",
                        "lift_vs_baseline", "description"]].round(2)
    tbl(top)

    JS["B1"] = {
        "baseline_closure_pct": float(baseline),
        "top15": top,
    }


# ---------------------------------------------------------------------------
# B2 — vermin findings by neighborhood
# ---------------------------------------------------------------------------
VERMIN_RE = r"(?i)(\bmice\b|\bmouse\b|live mice|rodent|rat\b|\brats\b|" \
            r"roach|cockroach|vermin|filth flies|food/refuse/sewage-associated)"


def probe_B2(dense: pd.DataFrame, raw: pd.DataFrame):
    h(2, "B2 · Where the vermin live (mice / rats / roaches / flies)")
    md("> *What share of inspections find evidence of pests, and which "
       "neighborhoods (NTA) are worst?*")

    # Build a (camis, date) -> vermin-flag table from raw violation rows.
    raw["_date"] = pd.to_datetime(raw["INSPECTION DATE"], format="%m/%d/%Y", errors="coerce")
    raw["is_vermin"] = raw["VIOLATION DESCRIPTION"].str.contains(VERMIN_RE, regex=True, na=False)
    vermin_insp = (raw[raw["is_vermin"]]
                       .groupby(["CAMIS", "_date"]).size().rename("n_vermin_codes")
                       .reset_index())
    vermin_insp.columns = ["camis", "inspection_date", "n_vermin_codes"]
    vermin_insp["camis"] = vermin_insp["camis"].astype(str)
    dense2 = dense.merge(vermin_insp, on=["camis", "inspection_date"], how="left")
    dense2["vermin"] = dense2["n_vermin_codes"].fillna(0).gt(0)

    city_rate = dense2["vermin"].mean() * 100
    by_boro = (dense2[dense2["boro"].isin(REAL_BOROS)]
               .groupby("boro", observed=True)["vermin"]
               .agg(["mean", "size"]))
    by_boro["pct"] = by_boro["mean"] * 100

    by_nta = (dense2[dense2["nta"].ne("") & dense2["boro"].isin(REAL_BOROS)]
              .groupby(["nta", "boro"], observed=True)["vermin"]
              .agg(["mean", "size"]))
    by_nta = by_nta[by_nta["size"] >= 200]  # min cell
    by_nta["pct"] = by_nta["mean"] * 100

    md(f"- City-wide: **{city_rate:.1f}%** of inspections find at least one "
       "vermin-related violation.")
    md("\n**By borough:**\n")
    tbl(by_boro.assign(pct=by_boro["pct"].round(1))[["size", "pct"]]
            .rename(columns={"size": "inspections", "pct": "% with vermin"}))

    md("\n**Worst 10 neighborhoods (NTA, ≥200 inspections):**\n")
    tbl(by_nta.sort_values("pct", ascending=False).head(10)
            .assign(pct=lambda d: d["pct"].round(1))[["size", "pct"]]
            .rename(columns={"size": "inspections", "pct": "% with vermin"}))

    md("\n**Best 10 neighborhoods (NTA, ≥200 inspections):**\n")
    tbl(by_nta.sort_values("pct", ascending=True).head(10)
            .assign(pct=lambda d: d["pct"].round(1))[["size", "pct"]]
            .rename(columns={"size": "inspections", "pct": "% with vermin"}))

    JS["B2"] = {
        "city_pct": float(city_rate),
        "by_boro": by_boro[["size", "pct"]].round(2),
        "worst10_nta": by_nta.sort_values("pct", ascending=False).head(10)[["size", "pct"]].round(2),
        "best10_nta": by_nta.sort_values("pct", ascending=True).head(10)[["size", "pct"]].round(2),
    }


# ---------------------------------------------------------------------------
# C1 — cuisines ranked by closure rate
# ---------------------------------------------------------------------------
def probe_C1(dense: pd.DataFrame):
    h(2, "C1 · Cuisines ranked by closure rate")
    md("> *Across all NYC cuisines (with ≥500 inspections to keep it fair), "
       "which type of restaurant gets shut down most often per inspection?*")

    g = (dense.groupby("cuisine_description", observed=True)
              .agg(n=("camis", "size"),
                   n_closed=("closed", "sum"),
                   n_restaurants=("camis", "nunique")))
    g["closure_rate_pct"] = g["n_closed"] / g["n"] * 100
    g = g[g["n"] >= 500]
    g = g.sort_values("closure_rate_pct", ascending=False)

    md("\n**Top 12 cuisines (highest closure rate):**\n")
    tbl(g.head(12)[["n", "n_restaurants", "closure_rate_pct"]].round(2))
    md("\n**Bottom 12 cuisines (lowest closure rate):**\n")
    tbl(g.tail(12)[["n", "n_restaurants", "closure_rate_pct"]].round(2))

    JS["C1"] = {
        "top12": g.head(12)[["n", "n_restaurants", "closure_rate_pct"]].round(2),
        "bottom12": g.tail(12)[["n", "n_restaurants", "closure_rate_pct"]].round(2),
    }


# ---------------------------------------------------------------------------
# C3 — cuisine geography (top cuisines' borough mix)
# ---------------------------------------------------------------------------
def probe_C3(dense: pd.DataFrame):
    h(2, "C3 · Cuisine geography — where each top cuisine lives")
    md("> *For the most common NYC cuisines, how are restaurants distributed "
       "across boroughs? (Critical confound for any borough finding.)*")

    top_cuisines = (dense["cuisine_description"].value_counts().head(12).index.tolist())
    sub = dense[dense["cuisine_description"].isin(top_cuisines)
                & dense["boro"].isin(REAL_BOROS)]
    ct = pd.crosstab(sub["cuisine_description"], sub["boro"],
                     values=sub["camis"], aggfunc="nunique").fillna(0).astype(int)
    pct = ct.div(ct.sum(axis=1), axis=0) * 100

    md("\n**Restaurant counts per cuisine × borough (distinct CAMIS):**\n")
    tbl(ct)
    md("\n**Row %: each cuisine's borough distribution (sums to 100%):**\n")
    tbl(pct.round(1))

    JS["C3"] = {"counts": ct, "row_pct": pct.round(1)}


# ---------------------------------------------------------------------------
# D1 — council-district closure-rate outliers
# ---------------------------------------------------------------------------
def probe_D1(dense_real: pd.DataFrame):
    h(2, "D1 · Council-district closure-rate outliers")
    md("> *NYC has 51 City Council districts. Which are the closure-rate "
       "outliers (top and bottom 5)?*")

    sub = dense_real[dense_real["council_district"].ne("")]
    g = (sub.groupby("council_district")
            .agg(n=("camis", "size"), n_closed=("closed", "sum"))
            .assign(closure_pct=lambda d: d["n_closed"] / d["n"] * 100))
    g = g[g["n"] >= 200]
    g = g.sort_values("closure_pct", ascending=False)

    md("\n**Top 5 (highest closure rate):**\n")
    tbl(g.head(5).round(2))
    md("\n**Bottom 5 (lowest closure rate):**\n")
    tbl(g.tail(5).round(2))

    JS["D1"] = {"top5": g.head(5).round(2), "bottom5": g.tail(5).round(2)}


# ---------------------------------------------------------------------------
# D2 — best/worst ZIPs (critical-violation rate)
# ---------------------------------------------------------------------------
def probe_D2(dense_real: pd.DataFrame):
    h(2, "D2 · Best/worst ZIP codes by critical-violation rate")
    md("> *Across NYC ZIPs (≥200 inspections), which had the highest and "
       "lowest share of inspections finding a critical violation?*")

    sub = dense_real[dense_real["zipcode"].ne("")]
    g = (sub.groupby("zipcode")
            .agg(n=("camis", "size"),
                 n_crit=("n_critical", lambda s: (s > 0).sum()),
                 boro=("boro", "first"))
            .assign(crit_pct=lambda d: d["n_crit"] / d["n"] * 100))
    g = g[g["n"] >= 200].sort_values("crit_pct", ascending=False)

    md("\n**Top 10 (highest critical-violation rate):**\n")
    tbl(g.head(10).round(2))
    md("\n**Bottom 10 (lowest critical-violation rate):**\n")
    tbl(g.tail(10).round(2))

    JS["D2"] = {"top10": g.head(10).round(2), "bottom10": g.tail(10).round(2)}


# ---------------------------------------------------------------------------
# D4 — tourist zones vs city baseline
# ---------------------------------------------------------------------------
def probe_D4(dense_real: pd.DataFrame):
    h(2, "D4 · Tourist zones vs city baseline")
    md(f"> *Are restaurants in tourist-magnet ZIPs ({sorted(TOURIST_ZIPS)}) "
       "inspected differently from the rest of NYC?*")

    sub = dense_real.copy()
    sub["zone"] = np.where(sub["zipcode"].isin(TOURIST_ZIPS), "Tourist ZIPs", "Rest of NYC")
    g = (sub.groupby("zone")
            .agg(n=("camis", "size"),
                 n_restaurants=("camis", "nunique"),
                 n_closed=("closed", "sum"),
                 n_crit=("n_critical", lambda s: (s > 0).sum()),
                 median_score=("score", "median")))
    g["closure_pct"] = g["n_closed"] / g["n"] * 100
    g["crit_pct"]    = g["n_crit"]   / g["n"] * 100
    g["insp_per_rest"] = g["n"] / g["n_restaurants"]

    md("\n**Side-by-side:**\n")
    tbl(g[["n", "n_restaurants", "insp_per_rest", "closure_pct",
           "crit_pct", "median_score"]].round(2))

    JS["D4"] = {"comparison": g[["n", "n_restaurants", "insp_per_rest",
                                  "closure_pct", "crit_pct",
                                  "median_score"]].round(2)}


# ---------------------------------------------------------------------------
# E1 — day-of-week pattern
# ---------------------------------------------------------------------------
def probe_E1(dense_real: pd.DataFrame):
    h(2, "E1 · Day-of-week pattern in inspections")
    md("> *Which weekday does the city inspect on most? Do Monday/Friday "
       "inspections find more critical violations than midweek?*")

    sub = dense_real.copy()
    sub["dow"] = sub["inspection_date"].dt.day_name()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"]
    g = (sub.groupby("dow")
            .agg(n=("camis", "size"),
                 n_closed=("closed", "sum"),
                 n_crit=("n_critical", lambda s: (s > 0).sum()),
                 median_score=("score", "median")))
    g["share_pct"]   = g["n"] / g["n"].sum() * 100
    g["closure_pct"] = g["n_closed"] / g["n"] * 100
    g["crit_pct"]    = g["n_crit"]   / g["n"] * 100
    g = g.reindex(order)

    md("\n**By weekday:**\n")
    tbl(g[["n", "share_pct", "closure_pct", "crit_pct", "median_score"]].round(2))

    JS["E1"] = {"by_dow": g[["n", "share_pct", "closure_pct",
                              "crit_pct", "median_score"]].round(2)}


# ---------------------------------------------------------------------------
# F2 — score recovery after a C-zone initial
# ---------------------------------------------------------------------------
def probe_F2(dense: pd.DataFrame):
    h(2, "F2 · Score recovery after a C-zone initial")
    md("> *When a restaurant fails its initial cycle inspection (score 28+ "
       "= C-zone), how much does its score drop by re-inspection?*")

    pairs = cycle_pairs(dense, max_days=180)
    cz = pairs[pairs["initial_score"] >= 28].copy()
    cz["score_drop"] = cz["initial_score"] - cz["reinsp_score"]
    cz["recovered_to_A"] = cz["reinsp_grade"] == "A"

    md(f"- Pairs where initial score ≥ 28 (C-zone): **{len(cz):,}**.")
    if len(cz):
        md(f"- Median initial score: **{cz['initial_score'].median():.0f}**.")
        md(f"- Median re-inspection score: **{cz['reinsp_score'].median():.0f}**.")
        md(f"- Median score drop: **{cz['score_drop'].median():.0f} points**.")
        md(f"- Recovered to A: **{cz['recovered_to_A'].mean()*100:.0f}%**.")
        md(f"- Median days to re-inspection: **{cz['days'].median():.0f}**.")
        md(f"- Cases where score got *worse* on re-inspection: "
           f"**{(cz['score_drop'] < 0).sum():,}** "
           f"({100*(cz['score_drop'] < 0).mean():.1f}%).")

    JS["F2"] = {
        "n_pairs_cz":         len(cz),
        "median_initial":     float(cz["initial_score"].median()) if len(cz) else None,
        "median_reinsp":      float(cz["reinsp_score"].median())  if len(cz) else None,
        "median_drop":        float(cz["score_drop"].median())    if len(cz) else None,
        "pct_recovered_to_A": float(cz["recovered_to_A"].mean()*100) if len(cz) else None,
        "pct_got_worse":      float(100*(cz["score_drop"] < 0).mean()) if len(cz) else None,
    }


# ---------------------------------------------------------------------------
# H1 — what the BORO=0 mystery restaurants actually are
# ---------------------------------------------------------------------------
def probe_H1(dense: pd.DataFrame):
    h(2, "H1 · What the BORO = '0' restaurants actually are")
    md("> *363 raw rows have BORO = '0'. At inspection grain, what are these "
       "places? Airports? Stadiums?*")

    miss = dense[dense["boro"] == "0"]
    md(f"- Rows in dense window: **{len(miss):,}** "
       f"(across **{miss['camis'].nunique()}** distinct restaurants).")

    md("\n**Top streets / building strings:**\n")
    streets = (miss.groupby(["street", "building"], observed=True)
                   .size().rename("inspections")
                   .sort_values(ascending=False).head(15))
    tbl(streets.reset_index())

    md("\n**Top DBA names:**\n")
    tbl(miss["dba"].value_counts().head(15).rename("inspections").to_frame())

    md("\n**ZIP codes (if present):**\n")
    tbl(miss["zipcode"].replace("", "<blank>").value_counts().head(10)
            .rename("inspections").to_frame())

    JS["H1"] = {
        "n_inspections": len(miss),
        "n_restaurants": int(miss["camis"].nunique()),
        "top_streets":   streets.reset_index(),
        "top_dba":       miss["dba"].value_counts().head(15),
    }


# ---------------------------------------------------------------------------
# Build a lookup: violation code -> human description (mode per code)
# ---------------------------------------------------------------------------
def build_code_descriptions(raw: pd.DataFrame) -> pd.DataFrame:
    sub = raw[raw["VIOLATION CODE"].ne("") & raw["VIOLATION DESCRIPTION"].ne("")]
    out = (sub.groupby("VIOLATION CODE")["VIOLATION DESCRIPTION"]
              .agg(lambda s: s.mode().iloc[0] if len(s.mode()) else "")
              .rename("description"))
    # Truncate long descriptions for readability in tables.
    out = out.str.slice(0, 110).str.rstrip() + (out.str.len() > 110).map({True: "…", False: ""})
    return out.to_frame()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Loading inspection-grain parquet...")
    df, dense, dense_real = load()
    print(f"  full parquet: {len(df):,}  |  2023+: {len(dense):,}  |  real boros: {len(dense_real):,}")

    print("Loading raw CSV for code/description access (this takes a few seconds)...")
    raw = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False)
    raw = raw.apply(lambda c: c.str.strip())

    code_desc = build_code_descriptions(raw)
    print(f"  built {len(code_desc)} code -> description lookups")

    h(1, "Discovery sweep results")
    md("Computed by `src/sweep_insights.py`. Dense window: 2023+ "
       f"({len(dense_real):,} inspections across the five boroughs).\n")

    print("Probe A2..."); probe_A2(dense_real)
    print("Probe A4..."); probe_A4(dense_real)
    print("Probe B1..."); probe_B1(dense_real, code_desc)
    print("Probe B2..."); probe_B2(dense, raw)
    print("Probe C1..."); probe_C1(dense_real)
    print("Probe C3..."); probe_C3(dense_real)
    print("Probe D1..."); probe_D1(dense_real)
    print("Probe D2..."); probe_D2(dense_real)
    print("Probe D4..."); probe_D4(dense_real)
    print("Probe E1..."); probe_E1(dense_real)
    print("Probe F2..."); probe_F2(dense_real)
    print("Probe H1..."); probe_H1(dense)

    OUT_MD.write_text("\n".join(MD), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(to_jsonable(JS), indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
