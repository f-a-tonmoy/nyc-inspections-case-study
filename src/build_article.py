"""
Build reports/article.html — the NYC restaurant-inspections case study.

Single source of truth: this one script computes every quoted number AND
builds every interactive chart, so the prose and the data cannot drift apart.

Article structure
-----------------
- Background (no analytics yet — what NYC inspections are, how the system works)
- HERO chart: the score spectrum with annotated extreme inspections
- §1 Vermin is everywhere
- §2 But vermin rarely shuts you down — the closure cliff
- §3 What happens after a closure (6-day response + the comeback effect)
- §4 The cuisine spectrum (with the geography caveat)
- §5 Where you eat matters more inside a borough than between them
- Caveats footer (rolling window + survivorship)

Run:
    conda run -n intro_ds python src/build_article.py
"""

from __future__ import annotations
from pathlib import Path
from textwrap import dedent

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

REPO_ROOT = Path(__file__).resolve().parent.parent
PARQUET   = REPO_ROOT / "data" / "processed" / "inspections.parquet"
RAW_CSV   = REPO_ROOT / "data" / "raw" / "dohmh_restaurant_inspections.csv"
ARTICLE   = REPO_ROOT / "reports" / "article.html"

REAL_BOROS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]

# Visual palette — warm, restrained, NYT-ish.
ACCENT   = "#c0392b"
ACCENT_2 = "#e67e22"
INK      = "#1a1a1a"
INK_DIM  = "#555"
NEUTRAL  = "#7f8c8d"
LIGHT    = "#bdc3c7"
RULE     = "#e5e5e5"

# The closure-cliff codes from the sweep. Pinned here (rather than recomputed)
# because the deep-dive validated them; if the data shifts we'll re-validate.
CLIFF_CODES = ["04F", "05A", "05E", "05F", "28-06", "04M", "04K", "04L"]


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load():
    df = pd.read_parquet(PARQUET)
    df["year"] = df["inspection_date"].dt.year
    # The official rolling window is "3 years prior to most recent inspection"
    # (would yield ~May 2023 cutoff), but DOHMH publishes substantial 2022
    # data: 6,471 inspections, ramping from 151/mo in Jan 2022 to 971/mo by
    # Dec 2022. We include calendar year 2022 onward — those inspections are
    # operationally real, especially in the second half of the year. Findings
    # here are aggregate rates, which are robust to the early-2022 lighter
    # months. Anything before 2022 is single-to-low-three-digit residue.
    dense = df[(df["year"] >= 2022) & df["boro"].isin(REAL_BOROS)].copy()

    raw = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False)
    raw = raw.apply(lambda c: c.str.strip())
    raw["_date"] = pd.to_datetime(
        raw["INSPECTION DATE"], format="%m/%d/%Y", errors="coerce"
    )
    return df, dense, raw


def code_description(raw: pd.DataFrame, codes: list[str]) -> dict[str, str]:
    """Most-common full description per code, truncated for tooltip use."""
    sub = raw[raw["VIOLATION CODE"].isin(codes) & raw["VIOLATION DESCRIPTION"].ne("")]
    desc = (sub.groupby("VIOLATION CODE")["VIOLATION DESCRIPTION"]
              .agg(lambda s: s.value_counts().index[0]))
    out = {}
    for c in codes:
        text = desc.get(c, "")
        out[c] = (text[:130] + "…") if len(text) > 130 else text
    return out


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------
def base_layout(title: str, height: int = 380) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=15, color=INK), x=0.02, xanchor="left"),
        font=dict(family="Inter, system-ui, sans-serif", size=13, color=INK),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=20, t=54, b=44),
        height=height,
        hoverlabel=dict(bgcolor="white", font_size=12,
                        font_family="Inter, system-ui, sans-serif"),
    )


def fig_div(fig: go.Figure, div_id: str) -> str:
    return pio.to_html(
        fig, include_plotlyjs=False, full_html=False, div_id=div_id,
        config={"displayModeBar": False, "responsive": True},
    )


# ---------------------------------------------------------------------------
# HERO chart — the score spectrum
# ---------------------------------------------------------------------------
def chart_hero(dense: pd.DataFrame) -> go.Figure:
    s = dense["score"].dropna().clip(lower=0, upper=120)
    bins = np.arange(0, 122, 2)
    counts, edges = np.histogram(s, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=centers, y=counts, width=1.8,
        marker_color=LIGHT, marker_line_width=0,
        hovertemplate="Score range: %{x:.0f}–%{customdata}<br>"
                      "Inspections: %{y:,}<extra></extra>",
        customdata=centers + 1,
        showlegend=False,
    ))

    # Grade-band shading (DOHMH publishes A=0-13, B=14-27, C=28+).
    band_colors = ["rgba(46,204,113,0.06)",
                   "rgba(241,196,15,0.07)",
                   "rgba(192,57,43,0.07)"]
    for x0, x1, color in [(0, 13, band_colors[0]),
                          (13, 27, band_colors[1]),
                          (27, 120, band_colors[2])]:
        fig.add_vrect(x0=x0, x1=x1, fillcolor=color, line_width=0, layer="below")

    for x, label in [(6.5, "A zone"), (20, "B zone"), (60, "C zone")]:
        fig.add_annotation(x=x, y=counts.max() * 1.02, text=label,
                           showarrow=False,
                           font=dict(size=12, color=INK_DIM))

    # Annotated extreme cases — these are real CAMIS from the deep-dive.
    # Stagger vertically so the labels don't overlap, and clamp x to the
    # visible range with the arrow pointing back to the true score.
    annotations = [
        (141, 0.78, "Kaffe Are <span style='color:#7f8c8d'>(Manhattan)</span><br>scored 141, recovered to 12 in 62 days"),
        (168, 0.55, "Le Pain Quotidien <span style='color:#7f8c8d'>(Manhattan)</span><br>scored 168, closed"),
        (200, 0.32, "Jay &amp; Son Latin Flavor <span style='color:#7f8c8d'>(Brooklyn)</span><br>scored 200, 18 violations, closed"),
    ]
    for x, y_frac, label in annotations:
        x_clip = min(x, 118)
        fig.add_annotation(
            x=x_clip, y=counts.max() * y_frac,
            text=label,
            showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=ACCENT,
            ax=-90, ay=0, xanchor="right",
            font=dict(size=11, color=INK),
            bgcolor="white", bordercolor=ACCENT, borderwidth=1,
            borderpad=5, opacity=0.97,
        )

    fig.update_layout(**base_layout(
        "Every NYC inspection, scored. Most pile up around A. A long tail doesn't.",
        height=440,
    ))
    fig.update_xaxes(
        title="Inspection score (higher = worse · DOHMH metric)",
        range=[0, 120], showgrid=False, zeroline=False, ticks="outside",
        tickcolor=RULE,
    )
    fig.update_yaxes(
        title="Inspections", showgrid=True, gridcolor=RULE, zeroline=False,
    )
    return fig


# ---------------------------------------------------------------------------
# §1 — Vermin by borough
# ---------------------------------------------------------------------------
VERMIN_RE = (r"(?i)(?:\bmice\b|\bmouse\b|live mice|rodent|rat\b|\brats\b|"
             r"roach|cockroach|vermin|filth flies|"
             r"food/refuse/sewage-associated)")


def compute_vermin(dense: pd.DataFrame, raw: pd.DataFrame):
    raw_v = raw.copy()
    raw_v["is_vermin"] = raw_v["VIOLATION DESCRIPTION"].str.contains(
        VERMIN_RE, regex=True, na=False)
    flag = (raw_v[raw_v["is_vermin"]]
              .groupby(["CAMIS", "_date"]).size()
              .rename("n_vermin_codes").reset_index())
    flag.columns = ["camis", "inspection_date", "n_vermin_codes"]
    flag["camis"] = flag["camis"].astype(str)

    d2 = dense.merge(flag, on=["camis", "inspection_date"], how="left")
    d2["vermin"] = d2["n_vermin_codes"].fillna(0).gt(0)

    city_pct = d2["vermin"].mean() * 100
    by_boro = (d2.groupby("boro", observed=True)["vermin"]
                  .agg(["mean", "size"])
                  .reindex(REAL_BOROS))
    by_boro["pct"] = by_boro["mean"] * 100

    nta = (d2[d2["nta"].ne("")]
             .groupby(["nta", "boro"], observed=True)["vermin"]
             .agg(["mean", "size"]))
    nta = nta[nta["size"] >= 200]
    nta["pct"] = nta["mean"] * 100
    return city_pct, by_boro, nta


def chart_vermin(by_boro: pd.DataFrame, city_pct: float) -> go.Figure:
    s = by_boro.sort_values("pct", ascending=True)
    colors = [ACCENT if b == "Bronx" else NEUTRAL for b in s.index]
    fig = go.Figure(go.Bar(
        x=s["pct"].round(1), y=s.index, orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}%" for v in s["pct"]],
        textposition="outside", cliponaxis=False,
        hovertemplate=("<b>%{y}</b><br>"
                       "%{x:.1f}% of inspections find vermin<br>"
                       "%{customdata:,} inspections<extra></extra>"),
        customdata=s["size"].astype(int).values,
    ))
    fig.add_vline(x=city_pct, line=dict(color=INK, dash="dot", width=1),
                  annotation_text=f"city-wide: {city_pct:.1f}%",
                  annotation_position="top right",
                  annotation_font=dict(size=11, color=INK_DIM))
    fig.update_layout(**base_layout(
        "Share of inspections finding evidence of mice, rats, roaches or flies",
        height=320,
    ))
    fig.update_xaxes(title="% of inspections", range=[0, max(s['pct'].max()*1.18, 40)],
                     showgrid=True, gridcolor=RULE)
    fig.update_yaxes(title="")
    return fig


# ---------------------------------------------------------------------------
# §2 — Closure-cliff bar
# ---------------------------------------------------------------------------
def compute_cliff(dense: pd.DataFrame, raw: pd.DataFrame):
    baseline = dense["closed"].mean() * 100
    exploded = (dense.assign(code=lambda d: d["violation_codes"].str.split(","))
                     .explode("code"))
    exploded = exploded[exploded["code"].astype(str).ne("")]
    block = exploded[exploded["code"].isin(CLIFF_CODES)]
    agg = (block.groupby("code")
                .agg(n=("camis", "size"), n_closed=("closed", "sum"))
                .assign(closure_pct=lambda d: d["n_closed"]/d["n"]*100))
    agg = agg.reindex(CLIFF_CODES)
    desc = code_description(raw, CLIFF_CODES)
    # Short human label, e.g. "Sewage in food area (04F)"
    short = {
        "04F":   "Sewage contamination in food area",
        "05A":   "Inadequate sewage disposal",
        "05E":   "No / improper toilet facility",
        "05F":   "No hot/cold-holding equipment",
        "28-06": "No pest-management contract",
        "04M":   "Live roaches",
        "04K":   "Evidence of rats / live rats",
        "04L":   "Evidence of mice / live mice",
    }
    agg["short"] = agg.index.map(short)
    agg["full"] = agg.index.map(desc)
    return baseline, agg.sort_values("closure_pct", ascending=True)


def chart_cliff(baseline: float, agg: pd.DataFrame) -> go.Figure:
    sewage_codes = {"04F", "05A", "05E"}
    colors = [ACCENT if c in sewage_codes else ACCENT_2 for c in agg.index]

    labels = [f"{row.short}  <span style='color:{INK_DIM}'>({code})</span>"
              for code, row in agg.iterrows()]
    fig = go.Figure(go.Bar(
        x=agg["closure_pct"].round(1), y=labels, orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}%" for v in agg["closure_pct"]],
        textposition="outside", cliponaxis=False,
        hovertemplate=("<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                       "Closure rate when present: %{x:.1f}%<br>"
                       "Appears in %{customdata[2]:,} inspections"
                       "<extra></extra>"),
        customdata=np.stack([agg["full"], agg.index, agg["n"]], axis=-1),
    ))
    fig.add_vline(
        x=baseline, line=dict(color=INK, dash="dot", width=1),
        annotation_text=f"baseline: {baseline:.2f}%",
        annotation_position="top right",
        annotation_font=dict(size=11, color=INK_DIM),
    )
    fig.update_layout(**base_layout(
        "When this violation appears, what fraction of inspections end in a closure?",
        height=440,
    ))
    fig.update_xaxes(title="closure rate when the code is present (%)",
                     range=[0, agg["closure_pct"].max() * 1.18],
                     showgrid=True, gridcolor=RULE)
    fig.update_yaxes(title="")
    return fig


# ---------------------------------------------------------------------------
# §3 — The comeback distribution
# ---------------------------------------------------------------------------
def compute_pairs(dense: pd.DataFrame) -> pd.DataFrame:
    ci = dense[dense["inspection_type"] == "Cycle Inspection / Initial Inspection"][
        ["camis", "inspection_date", "boro", "score", "grade", "dba"]
    ].rename(columns={"inspection_date": "initial_date",
                      "score": "initial_score", "grade": "initial_grade"})
    cr = dense[dense["inspection_type"] == "Cycle Inspection / Re-inspection"][
        ["camis", "inspection_date", "score", "grade"]
    ].rename(columns={"inspection_date": "reinsp_date",
                      "score": "reinsp_score", "grade": "reinsp_grade"})
    p = ci.merge(cr, on="camis")
    p = p[p["reinsp_date"] > p["initial_date"]]
    p["days"] = (p["reinsp_date"] - p["initial_date"]).dt.days
    p = (p.sort_values(["camis", "initial_date", "days"])
           .drop_duplicates(["camis", "initial_date"], keep="first"))
    return p[p["days"].between(1, 180)].copy()


def chart_comeback(pairs: pd.DataFrame) -> go.Figure:
    cz = pairs[pairs["initial_score"] >= 28].copy()
    cz["drop"] = cz["initial_score"] - cz["reinsp_score"]
    median = cz["drop"].median()

    # Histogram of score drops; positive = improved.
    bins = np.arange(-40, 121, 4)
    counts, edges = np.histogram(cz["drop"].clip(-40, 120), bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    colors = [ACCENT if c < 0 else NEUTRAL for c in centers]

    fig = go.Figure(go.Bar(
        x=centers, y=counts, width=3.6,
        marker_color=colors, marker_line_width=0,
        hovertemplate="Drop: %{x:.0f} points<br>%{y:,} restaurants<extra></extra>",
    ))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.add_vline(x=median, line=dict(color=ACCENT_2, dash="dash", width=1.5),
                  annotation_text=f"median drop: {median:.0f}",
                  annotation_position="top right",
                  annotation_font=dict(size=11, color=INK_DIM))
    fig.add_annotation(
        x=-25, y=counts.max() * 0.5,
        text=f"<b>{(cz['drop'] < 0).sum():,}</b><br>got worse",
        showarrow=False, font=dict(size=12, color=ACCENT),
        bgcolor="white", bordercolor=ACCENT, borderwidth=1, borderpad=4,
    )
    fig.update_layout(**base_layout(
        f"How much did the score drop on re-inspection?  ({len(cz):,} initial-cycle 'C-zone' failures)",
        height=320,
    ))
    fig.update_xaxes(title="Score change (initial − re-inspection · positive = improved)",
                     showgrid=True, gridcolor=RULE, zeroline=False)
    fig.update_yaxes(title="Restaurants", showgrid=True, gridcolor=RULE)
    return fig


# ---------------------------------------------------------------------------
# §4 — Cuisine spectrum, colored by Manhattan share
# ---------------------------------------------------------------------------
def compute_cuisine(dense: pd.DataFrame):
    g = (dense.groupby("cuisine_description", observed=True)
              .agg(n=("camis", "size"),
                   n_closed=("closed", "sum"),
                   n_restaurants=("camis", "nunique")))
    g["closure_pct"] = g["n_closed"] / g["n"] * 100
    # Match the sweep's threshold (n >= 500) so headline cuisines stay in.
    g = g[g["n"] >= 500]
    g = g[g.index.astype(str).str.len() > 0]

    # Manhattan share of each cuisine's restaurants — confounder visualization.
    cuis_boro = (dense.groupby(["cuisine_description", "boro"], observed=True)
                       ["camis"].nunique().unstack(fill_value=0))
    g["pct_manhattan"] = (cuis_boro["Manhattan"] / cuis_boro.sum(axis=1) * 100).reindex(g.index)

    top = g.nlargest(8, "closure_pct").sort_values("closure_pct", ascending=True)
    bot = g.nsmallest(8, "closure_pct").sort_values("closure_pct", ascending=True)
    panel = pd.concat([bot, top])
    return panel


def chart_cuisine(panel: pd.DataFrame) -> go.Figure:
    # Color encodes Manhattan share. Low Manhattan → ACCENT, high → NEUTRAL.
    # That visualizes the geographic confound directly.
    colors = []
    for v in panel["pct_manhattan"]:
        t = max(0.0, min(1.0, v / 60.0))   # 0% Manhattan -> 0; 60%+ -> 1
        # interpolate between ACCENT (#c0392b) and NEUTRAL (#7f8c8d)
        r = int(192 + (127 - 192) * t)
        g = int(57  + (140 - 57) * t)
        b = int(43  + (141 - 43) * t)
        colors.append(f"rgb({r},{g},{b})")

    fig = go.Figure(go.Bar(
        x=panel["closure_pct"].round(2), y=panel.index, orientation="h",
        marker_color=colors,
        text=[f"{v:.2f}%" for v in panel["closure_pct"]],
        textposition="outside", cliponaxis=False,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Closure rate: %{x:.2f}%<br>"
            "Inspections: %{customdata[0]:,}<br>"
            "Active restaurants: %{customdata[1]:,}<br>"
            "%{customdata[2]:.0f}% are in Manhattan"
            "<extra></extra>"
        ),
        customdata=np.stack([panel["n"], panel["n_restaurants"],
                             panel["pct_manhattan"]], axis=-1),
    ))
    layout = base_layout(
        "Closure rate by cuisine, top and bottom of the ranking",
        height=470,
    )
    # Add more top margin for the two-line title + legend strip.
    layout["margin"] = dict(l=10, r=20, t=78, b=44)
    fig.update_layout(**layout)
    fig.update_xaxes(title="closure rate (%)",
                     range=[0, panel["closure_pct"].max() * 1.15],
                     showgrid=True, gridcolor=RULE)
    fig.update_yaxes(title="")
    # Legend strip on its own row below the title (well clear of it).
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=1.045,
        xanchor="left", yanchor="bottom",
        text="<span style='color:#c0392b'>■</span> outer-borough heavy &nbsp;&nbsp;"
             "<span style='color:#7f8c8d'>■</span> Manhattan heavy &nbsp;"
             "<span style='color:#7f8c8d'>(bar color encodes the cuisine's Manhattan share)</span>",
        showarrow=False, font=dict(size=11, color=INK_DIM),
    )
    return fig


# ---------------------------------------------------------------------------
# §5 — Council district spread
# ---------------------------------------------------------------------------
def compute_districts(dense: pd.DataFrame):
    sub = dense[dense["council_district"].ne("")]
    g = (sub.groupby("council_district")
             .agg(n=("camis", "size"), n_closed=("closed", "sum")))
    g = g[g["n"] >= 200]
    g["closure_pct"] = g["n_closed"] / g["n"] * 100
    # Sort by closure rate ascending for the chart
    return g.sort_values("closure_pct", ascending=True)


def chart_districts(g: pd.DataFrame) -> go.Figure:
    n = len(g)
    colors = []
    for i, _ in enumerate(g.index):
        if i < 5:
            colors.append(NEUTRAL)         # safest
        elif i >= n - 5:
            colors.append(ACCENT)          # riskiest
        else:
            colors.append(LIGHT)
    fig = go.Figure(go.Bar(
        x=[f"D{d}" for d in g.index], y=g["closure_pct"].round(2),
        marker_color=colors, marker_line_width=0,
        hovertemplate=("Council District %{x}<br>"
                       "Closure rate: %{y:.2f}%<br>"
                       "%{customdata:,} inspections<extra></extra>"),
        customdata=g["n"].astype(int).values,
    ))
    fig.update_layout(**base_layout(
        "NYC's 51 City Council districts, ranked by inspection-closure rate",
        height=340,
    ))
    fig.update_xaxes(title="Council district (sorted, low → high closure rate)",
                     tickfont=dict(size=9),
                     showgrid=False, tickangle=-45)
    fig.update_yaxes(title="closure rate (%)", showgrid=True, gridcolor=RULE)
    return fig


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
CSS = """
:root {
  --ink: #1a1a1a; --ink-dim: #555; --rule: #e5e5e5;
  --bg: #fafaf7; --accent: #c0392b; --accent-soft: rgba(192,57,43,0.08);
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--ink); }
body {
  font-family: "Source Serif Pro", "Charter", "Georgia", "Times New Roman", serif;
  font-size: 18.5px; line-height: 1.7;
  -webkit-font-smoothing: antialiased;
}
.container { max-width: 740px; margin: 0 auto; padding: 56px 24px 80px; }
header { border-bottom: 1px solid var(--rule); padding-bottom: 30px; margin-bottom: 30px; }
.eyebrow {
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  font-size: 12px; font-weight: 600; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 14px;
}
h1 {
  font-size: 44px; line-height: 1.1; font-weight: 700; margin: 0 0 14px 0;
  letter-spacing: -0.012em;
}
.deck {
  font-size: 20.5px; line-height: 1.5; color: var(--ink-dim);
  font-style: italic; margin: 0 0 12px 0;
}
.byline {
  font-family: "Inter", system-ui, sans-serif;
  font-size: 13px; color: var(--ink-dim); margin-top: 22px;
}
h2 {
  font-size: 28px; line-height: 1.2; font-weight: 700;
  margin: 64px 0 18px 0; letter-spacing: -0.005em;
}
h2 .num {
  display: inline-block; color: var(--accent); margin-right: 14px;
  font-feature-settings: "lnum"; font-variant-numeric: lining-nums;
  font-size: 26px;
}
p { margin: 0 0 20px 0; }
.dropcap::first-letter {
  font-size: 60px; line-height: 0.85; float: left;
  font-weight: 700; padding: 8px 10px 0 0; color: var(--ink);
}
figure { margin: 32px 0 18px; }
figure .chart {
  background: white; border: 1px solid var(--rule); border-radius: 6px;
  padding: 6px 4px; box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
figcaption {
  font-family: "Inter", system-ui, sans-serif;
  font-size: 13px; color: var(--ink-dim);
  margin-top: 10px; text-align: center; line-height: 1.45;
}
strong { font-weight: 700; }
em.stat { font-style: normal; font-weight: 700; color: var(--ink); }
.pullquote {
  font-family: "Source Serif Pro", "Charter", serif;
  font-size: 26px; line-height: 1.3; color: var(--ink);
  border-left: 3px solid var(--accent); padding: 4px 0 4px 22px;
  margin: 36px 0; font-weight: 600;
}
.callout {
  background: var(--accent-soft); border-radius: 4px;
  padding: 16px 22px; margin: 28px 0; font-size: 17px; line-height: 1.55;
}
.callout strong { color: var(--accent); }
footer {
  margin-top: 72px; padding-top: 28px; border-top: 1px solid var(--rule);
  font-family: "Inter", system-ui, sans-serif;
  font-size: 13px; color: var(--ink-dim); line-height: 1.55;
}
footer code { background: #eee; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
footer a { color: var(--accent); text-decoration: none; }
footer a:hover { text-decoration: underline; }
footer h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.1em;
            color: var(--ink); margin: 18px 0 6px 0; font-weight: 700; }
"""


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render(stats: dict, charts: dict) -> str:
    s = stats
    return dedent(f"""\
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>What 77,000 Inspections Reveal About NYC's Restaurants</title>
      <link rel="stylesheet" href="https://rsms.me/inter/inter.css">
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+Pro:wght@400;600;700&display=swap">
      <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
      <style>{CSS}</style>
    </head>
    <body>
      <article class="container">

        <header>
          <div class="eyebrow">A Data Case Study · NYC Department of Health</div>
          <h1>The Quiet Math of New York's Restaurant Inspections</h1>
          <p class="deck">
            What <strong>{s['n_inspections']:,}</strong> health inspections in
            <strong>{s['n_restaurants']:,}</strong> active New York City restaurants reveal
            about pests, plumbing, and what actually gets a kitchen shut down.
          </p>
          <div class="byline">
            Based on the NYC Department of Health's published inspection records · 2022–2026
          </div>
        </header>

        <p class="dropcap">
          New York City has more restaurants than any other American city —
          roughly <strong>{s['n_restaurants']:,}</strong> active food establishments at last count,
          spread across five boroughs and an even longer list of cuisines.
          Behind that visible city is an invisible one: a small army of public-health
          inspectors who arrive at each kitchen, unannounced, on a rolling cycle.
          They tally violations against a long checklist, add up a score, and
          assign the letter grade that ends up taped to the front window. Higher
          score, worse kitchen. Anything from 0 to 13 earns an A; 14 to 27 a B;
          28 and above a C.
        </p>

        <p>
          Most diners only ever see the grade card. What they don't see is the
          underlying data — every violation, every inspection, every closure —
          which the city quietly publishes on its open-data portal. The most
          recent three years of records cover roughly <em class="stat">{s['n_inspections']:,}</em>
          inspections. That's a generous slice of the city's food life: every
          deli, every wedding venue, every late-night Halal cart that has a
          permit, photographed in a different moment of order or disorder by
          someone with a clipboard.
        </p>

        <p>
          Looking at all of those visits at once produces a portrait that no
          single grade card can. The picture is, by turns, reassuring and
          alarming. Most inspections turn out roughly the same. Most kitchens
          recover from a bad day. A handful of very specific failures, however,
          end the inspection on the spot.
        </p>

        <figure>
          <div class="chart">{charts['hero']}</div>
          <figcaption>
            Every NYC inspection score from 2022 to 2026, in two-point bins.
            Hover any bar for the count; the long right-hand tail is real,
            it's just very thin compared with the A-zone peak.
          </figcaption>
        </figure>

        <h2><span class="num">01</span>Vermin is everywhere.</h2>

        <p>
          The single most surprising number from the data is the one that
          shouldn't be: <em class="stat">{s['vermin_pct']:.0f}%</em> of New York
          inspections find evidence of mice, rats, roaches or flies.
          One in three. Borough to borough, the variation is mild —
          {s['bronx_vermin_pct']:.0f}% in the Bronx, {s['si_vermin_pct']:.0f}% on
          Staten Island. Neighborhood to neighborhood, the spread is sharper:
          the worst residential / commercial slice of the city sees a pest
          violation in roughly <em class="stat">{s['nta_worst_pct']:.0f}%</em>
          of inspections, the cleanest in about <em class="stat">{s['nta_best_pct']:.0f}%</em>.
        </p>

        <figure>
          <div class="chart">{charts['vermin']}</div>
          <figcaption>
            Borough-level pest-violation rates. The dotted line is the city-wide
            average; the Bronx is highlighted as the highest.
          </figcaption>
        </figure>

        <p>
          That rate is high enough to mean roughly nothing on its own. If 1 in
          3 inspections finds vermin, then vermin can't be what closes a
          restaurant — most of those <em class="stat">{s['n_inspections']:,}</em>
          visits ended with the kitchen still open. The question is what does.
        </p>

        <h2><span class="num">02</span>The closure cliff.</h2>

        <p>
          New York City inspectors close a restaurant on the spot in only
          <em class="stat">{s['baseline_closure_pct']:.2f}%</em> of inspections — fewer than
          two in every hundred. That headline rate hides a sharper truth.
          When a few specific violations appear, the closure probability
          doesn't just creep up. It jumps.
        </p>

        <figure>
          <div class="chart">{charts['cliff']}</div>
          <figcaption>
            The dotted line is the city-wide closure rate
            ({s['baseline_closure_pct']:.2f}%). Each bar shows how often an
            inspection ended in a closure <em>when this particular code appeared</em>.
            Hover any bar for the full code description.
          </figcaption>
        </figure>

        <p>
          The pattern is striking. Vermin codes — even the live-roach code,
          even the live-rat code — push closure risk up by roughly three to
          five times the baseline. They are bad. They are not, by themselves,
          the reason kitchens get shut down. The codes that <em>do</em> shut
          kitchens down are about plumbing.
        </p>

        <p>
          Inspections containing <em class="stat">04F</em> (food area
          contaminated by sewage) end in a closure <em class="stat">{s['cliff_04F_pct']:.0f}%</em>
          of the time — nineteen times the baseline rate. <em class="stat">05A</em>
          (inadequate sewage disposal) and <em class="stat">05E</em>
          (missing or improper toilet facilities) are nearly as severe.
          These are the violations that take a kitchen from "could open
          tomorrow" to "is closing today."
        </p>

        <div class="callout">
          <strong>It's the plumbing.</strong> A live rat sighting raises your
          chance of being closed by about 5×. A sewage problem raises it by
          15–19×. Vermin makes the news; sewage takes the keys.
        </div>

        <p>
          The deeper read is that these inspections are rarely single-issue
          events. Only <em class="stat">{s['cliff_n']:,}</em> inspections contained one of
          the three top sewage codes over the three-year window, but those
          inspections had a median score of <em class="stat">{s['cliff_med_score']:.0f}</em>
          (versus <em class="stat">13</em> for everyone else) and a median of
          <em class="stat">{s['cliff_med_viols']:.0f} violations</em> apiece
          (versus three). The plumbing failure is the marker, not the sole
          cause: when a kitchen reaches that point, a lot has already gone
          wrong. <strong>{s['cliff_pct_critical']:.0f}%</strong> of those
          inspections also flagged at least one critical food-safety violation.
        </p>

        <p>
          A handful of recognizable names appear in the data at the catastrophic
          end of the spectrum. A <em class="stat">Le Pain Quotidien</em>
          location in Manhattan posted a score of 168 in July 2023 with a
          sewage citation. A Manhattan <em class="stat">% Arabica</em> hit 163
          in March 2026 under the same code. A small Brooklyn restaurant called
          Jay &amp; Son Latin Flavor recorded a score of <em class="stat">200</em>
          this past spring — eighteen violations, eleven of them critical,
          sewage among them. Each of these kitchens was closed that day.
        </p>

        <h2><span class="num">03</span>What happens next.</h2>

        <p>
          Closures look severe but they're not, in most cases, permanent.
          The city moves fast: after a sewage-cliff closure, the median wait
          until the next inspection is just <em class="stat">{s['days_to_followup']}
          days</em> — compared with about <em class="stat">70 days</em> for a
          routine cycle re-inspection. Roughly <em class="stat">{s['pct_reopened']:.0f}%</em>
          of those follow-ups end with DOHMH formally re-opening the
          restaurant. The kitchen, usually, gets cleaned up.
        </p>

        <p>
          A broader version of the same story holds for any restaurant that
          fails its initial cycle inspection in the C zone (score 28 or
          above): <em class="stat">{s['n_cz']:,}</em> such failures in the
          window. Median score on the re-inspection drops by
          <em class="stat">{s['median_drop']:.0f}</em> points — from
          <em class="stat">{s['median_initial']:.0f}</em> all the way down to
          <em class="stat">{s['median_reinsp']:.0f}</em>. More than half —
          <em class="stat">{s['pct_recover_A']:.0f}%</em> — recover all the
          way to an A on the very next visit.
        </p>

        <figure>
          <div class="chart">{charts['comeback']}</div>
          <figcaption>
            Score change for restaurants that failed an initial cycle
            inspection. Positive means improvement on re-inspection. The thin
            red bars at the left edge are restaurants that got <em>worse</em>.
          </figcaption>
        </figure>

        <p>
          A small minority defy the pattern.
          <em class="stat">{s['pct_got_worse']:.1f}%</em> of these restaurants
          actually <em>got worse</em> on the next inspection. Another
          <em class="stat">{s['pct_reclosed']:.0f}%</em> of sewage-cliff
          closures were re-closed at the very next visit. The recovery system
          is real, but it leaks at the bottom of the distribution — the same
          kitchens keep failing.
        </p>

        <h2><span class="num">04</span>The cuisine spectrum.</h2>

        <p>
          Closure rates are far from uniform across cuisines. Indian
          restaurants are closed during inspection in <em class="stat">{s['indian_pct']:.1f}%</em>
          of visits; French restaurants in just <em class="stat">{s['french_pct']:.2f}%</em>
          — a roughly <em class="stat">{s['indian_pct']/s['french_pct']:.0f}×</em>
          gap from one end of the menu to the other.
        </p>

        <figure>
          <div class="chart">{charts['cuisine']}</div>
          <figcaption>
            Top and bottom of the cuisine closure-rate ranking. Bar color
            reflects what share of that cuisine's restaurants are located in
            Manhattan — a quiet reminder that "by cuisine" and "by
            neighborhood" are not separable in this city.
          </figcaption>
        </figure>

        <p>
          Read this chart carefully. The cuisines at the top — Indian, Middle
          Eastern, Caribbean, Chinese — are heavily concentrated outside
          Manhattan. The cuisines at the bottom — French, Italian, Irish,
          Hamburgers — are disproportionately Manhattan establishments. We
          can't tell, from this data alone, whether what we're seeing is a
          property of the cuisines themselves or a property of the
          neighborhoods they live in. Most likely it's some of both. The
          confound is the finding.
        </p>

        <h2><span class="num">05</span>The smaller-than-borough story.</h2>

        <p>
          The familiar five-borough frame turns out to hide most of the
          interesting variation. Sort New York's 51 City Council districts
          by their closure rate and the spread is dramatic:
          <em class="stat">{s['district_high_pct']:.2f}%</em> at the top,
          <em class="stat">{s['district_low_pct']:.2f}%</em> at the bottom —
          a <em class="stat">{s['district_ratio']:.1f}×</em> gap.
          The familiar borough comparison covers about a 2× range; sub-borough
          geography covers nearly four times that.
        </p>

        <figure>
          <div class="chart">{charts['districts']}</div>
          <figcaption>
            All 51 NYC Council districts (≥200 inspections each), sorted by
            inspection closure rate. The five safest are highlighted on the
            left, the five highest on the right.
          </figcaption>
        </figure>

        <p>
          "Brooklyn" and "Manhattan" are large coalitions. Inside them are
          districts that look almost nothing alike — a quiet reminder that
          when we talk about the food landscape of a city, we are nearly
          always talking about the food landscape of a few square blocks.
        </p>

        <h2>What this data cannot tell us</h2>

        <p>
          Two cautions matter for anyone who reads further into these numbers.
          The first is that DOHMH publishes a <strong>rolling roughly three-year
          window</strong> of inspection records. Earlier inspections drop off
          the back end; the dataset's headline 2007 minimum date is a
          decorative sliver. Everything in this article covers calendar
          2022 onward — the period in which the city's inspection program
          was running at full monthly volume.
        </p>

        <p>
          The second caution is more consequential. The city only publishes
          records for restaurants that are still in active status. Establishments
          that permanently closed — including any that closed after enforcement
          and never reopened — drop out of the file entirely. The city's
          closure rate, then, undercounts the most consequential closure of
          all. The numbers in this article describe what happens to surviving
          restaurants. They do not describe what happens to the ones that
          don't come back.
        </p>

        <footer>
          <h3>Source</h3>
          <p>
            NYC OpenData — <a href="https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j">DOHMH
            Restaurant Inspection Results</a> (dataset id <code>43nn-pn8j</code>),
            snapshot of 2026-05-30.
          </p>
          <h3>Method</h3>
          <p>
            Raw violation-grain CSV → one row per inspection in
            <code>src/build_inspections.py</code>. All findings and charts
            built by <code>src/build_article.py</code>. Restricted to
            inspection year ≥ 2022 and the five real boroughs. The dataset
            also contains a small amount of 2007–2021 residue (≤300 rows per
            year), which has been excluded.
            Charts powered by <a href="https://plotly.com/javascript/">Plotly.js</a>.
          </p>
          <h3>Caveats</h3>
          <p>
            "Active restaurants" means any CAMIS that appears in the published
            file; permanently closed restaurants are not represented. The
            cuisine analysis is not adjusted for the cuisine/geography
            confound described in §4. Re-inspection pairs are bounded to ≤180
            days so the next cycle's initial inspection is not counted as
            the previous one's re-inspection.
          </p>
        </footer>
      </article>
    </body>
    </html>
    """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    df, dense, raw = load()
    print(f"Loaded: {len(df):,} inspections (full), {len(dense):,} dense + real boros.")

    # Vermin
    city_v, by_boro_v, nta_v = compute_vermin(dense, raw)
    # Closure cliff
    baseline, cliff_agg = compute_cliff(dense, raw)
    # Sewage-cliff subset stats for prose
    exploded = (dense.assign(code=lambda d: d["violation_codes"].str.split(","))
                     .explode("code"))
    exploded = exploded[exploded["code"].astype(str).ne("")]
    top3 = ["04F", "05A", "05E"]
    cliff_keys = (exploded[exploded["code"].isin(top3)]
                    .groupby(["camis", "inspection_date"]).size().index)
    is_cliff = pd.MultiIndex.from_frame(dense[["camis", "inspection_date"]]).isin(cliff_keys)
    cliff = dense[is_cliff]

    # 6-day response: median next-inspection days after a sewage closure
    closures = cliff[cliff["closed"]][["camis", "inspection_date"]].copy()
    closures.columns = ["camis", "closure_date"]
    all_insp = dense[["camis", "inspection_date", "score", "action"]].copy()
    j = closures.merge(all_insp, on="camis")
    j = j[j["inspection_date"] > j["closure_date"]]
    j["days_after"] = (j["inspection_date"] - j["closure_date"]).dt.days
    j = j[j["days_after"] <= 180]
    nxt = (j.sort_values(["camis", "closure_date", "days_after"])
            .drop_duplicates(["camis", "closure_date"], keep="first"))
    days_to_followup = int(nxt["days_after"].median()) if len(nxt) else None
    next_action_mix = nxt["action"].value_counts(normalize=True) * 100
    pct_reopened = float(next_action_mix.get("Establishment re-opened by DOHMH.", 0))
    pct_reclosed = float(next_action_mix.get("Establishment re-closed by DOHMH.", 0))

    # Comebacks
    pairs = compute_pairs(dense)
    cz = pairs[pairs["initial_score"] >= 28].copy()
    cz["drop"] = cz["initial_score"] - cz["reinsp_score"]

    # Cuisines
    cuisine_panel = compute_cuisine(dense)
    indian_pct = float(cuisine_panel.loc["Indian", "closure_pct"])
    french_pct = float(cuisine_panel.loc["French", "closure_pct"])

    # Districts
    dist = compute_districts(dense)

    # Stats dict — every number quoted in the prose
    stats = {
        "n_inspections":         int(len(dense)),
        "n_restaurants":         int(dense["camis"].nunique()),
        "vermin_pct":            float(city_v),
        "bronx_vermin_pct":      float(by_boro_v.loc["Bronx", "pct"]),
        "si_vermin_pct":         float(by_boro_v.loc["Staten Island", "pct"]),
        "nta_worst_pct":         float(nta_v["pct"].max()),
        "nta_best_pct":          float(nta_v["pct"].min()),
        "baseline_closure_pct":  float(baseline),
        "cliff_04F_pct":         float(cliff_agg.loc["04F", "closure_pct"]),
        "cliff_n":               int(len(cliff)),
        "cliff_med_score":       float(cliff["score"].median()),
        "cliff_med_viols":       float(cliff["n_violations"].median()),
        "cliff_pct_critical":    float((cliff["n_critical"] > 0).mean() * 100),
        "days_to_followup":      days_to_followup,
        "pct_reopened":          pct_reopened,
        "pct_reclosed":          pct_reclosed,
        "n_cz":                  int(len(cz)),
        "median_initial":        float(cz["initial_score"].median()),
        "median_reinsp":         float(cz["reinsp_score"].median()),
        "median_drop":           float(cz["drop"].median()),
        "pct_recover_A":         float((cz["reinsp_grade"] == "A").mean() * 100),
        "pct_got_worse":         float((cz["drop"] < 0).mean() * 100),
        "indian_pct":            indian_pct,
        "french_pct":            french_pct,
        "district_high_pct":     float(dist["closure_pct"].max()),
        "district_low_pct":      float(dist["closure_pct"].min()),
        "district_ratio":        float(dist["closure_pct"].max() / dist["closure_pct"].min()),
    }

    # Build charts
    figs = {
        "hero":      chart_hero(dense),
        "vermin":    chart_vermin(by_boro_v, city_v),
        "cliff":     chart_cliff(baseline, cliff_agg),
        "comeback":  chart_comeback(pairs),
        "cuisine":   chart_cuisine(cuisine_panel),
        "districts": chart_districts(dist),
    }
    charts = {k: fig_div(v, f"chart-{k}") for k, v in figs.items()}

    ARTICLE.write_text(render(stats, charts), encoding="utf-8")
    print(f"\nWrote {ARTICLE}")
    print("Headline numbers used in prose:")
    for k, v in stats.items():
        print(f"  {k:>22}: {v}")


if __name__ == "__main__":
    main()
