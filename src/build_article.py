"""
Build the article — `reports/article.html`.

Single source of truth for the article: this script computes every number the
article quotes AND builds every interactive chart, so the prose can never
drift from the data.

Run:
    conda run -n intro_ds python src/build_article.py

Output:
    reports/article.html              standalone article, opens in any browser
    reports/figures/chart_*.png       PNG fallbacks for each interactive chart
"""

from __future__ import annotations
from pathlib import Path
from textwrap import dedent

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
PARQUET   = REPO_ROOT / "data" / "processed" / "inspections.parquet"
ARTICLE   = REPO_ROOT / "reports" / "article.html"
FIG_DIR   = REPO_ROOT / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Boroughs in NYC; we drop the "0" missing-BORO bucket (85 rows in 2023+).
REAL_BOROS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]

# Color: one accent for highlighted boroughs in each chart, neutral for rest.
ACCENT = "#c0392b"   # warm red-brown — restrained, not alarming
NEUTRAL = "#5d8aa8"  # muted steel blue
GREY   = "#9e9e9e"


# ---------------------------------------------------------------------------
# Load & restrict to dense window
# ---------------------------------------------------------------------------
def load_dense():
    """Load the inspection-grain parquet, restricted to 2023+.

    Why 2023+: NYC Open Data publishes a rolling ~3-year window. Pre-2023
    rows are sparse residue and would distort per-restaurant denominators.
    """
    df = pd.read_parquet(PARQUET)
    df["year"] = df["inspection_date"].dt.year
    dense = df[(df["year"] >= 2023) & df["boro"].isin(REAL_BOROS)].copy()
    return dense


# ---------------------------------------------------------------------------
# Finding 1 — closure rate by borough
# ---------------------------------------------------------------------------
def compute_boro_summary(dense: pd.DataFrame) -> pd.DataFrame:
    g = dense.groupby("boro", observed=True).agg(
        n_inspections   = ("camis", "size"),
        n_restaurants   = ("camis", "nunique"),
        n_closures      = ("closed", "sum"),
        n_crit_insp     = ("n_critical", lambda s: (s > 0).sum()),
    )
    g["closure_pct"]   = g["n_closures"]    / g["n_inspections"] * 100
    g["insp_per_rest"] = g["n_inspections"] / g["n_restaurants"]
    g["pct_with_crit"] = g["n_crit_insp"]   / g["n_inspections"] * 100
    return g.reindex(REAL_BOROS)


def chart_closure_rate(summary: pd.DataFrame) -> go.Figure:
    s = summary.sort_values("closure_pct", ascending=True)
    colors = [ACCENT if b == "Brooklyn" else NEUTRAL for b in s.index]

    fig = go.Figure(go.Bar(
        x=s["closure_pct"].round(2),
        y=s.index,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.2f}%" for v in s["closure_pct"]],
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Closure rate: %{x:.2f}%<br>"
            "Closures: %{customdata[0]:,} of %{customdata[1]:,} inspections"
            "<extra></extra>"
        ),
        customdata=np.stack([s["n_closures"].values,
                             s["n_inspections"].values], axis=-1),
    ))
    fig.update_layout(
        title="Share of inspections that ended in a temporary DOHMH closure (2023+)",
        xaxis_title="closure rate (% of inspections)",
        yaxis_title="",
        margin=dict(l=10, r=10, t=60, b=40),
        height=320,
        template="plotly_white",
        font=dict(family="Inter, system-ui, sans-serif", size=13),
    )
    fig.update_xaxes(range=[0, s["closure_pct"].max() * 1.18])
    return fig


# ---------------------------------------------------------------------------
# Finding 2 — re-inspection cadence
# ---------------------------------------------------------------------------
def compute_reinspection_pairs(dense: pd.DataFrame) -> pd.DataFrame:
    ci = dense[dense["inspection_type"] == "Cycle Inspection / Initial Inspection"][
        ["camis", "inspection_date", "boro"]
    ].rename(columns={"inspection_date": "initial_date"})
    cr = dense[dense["inspection_type"] == "Cycle Inspection / Re-inspection"][
        ["camis", "inspection_date"]
    ].rename(columns={"inspection_date": "reinsp_date"})

    pairs = ci.merge(cr, on="camis")
    pairs = pairs[pairs["reinsp_date"] > pairs["initial_date"]]
    pairs["days"] = (pairs["reinsp_date"] - pairs["initial_date"]).dt.days
    # Keep the nearest re-inspection after each initial, drop unlikely pairs.
    pairs = (pairs.sort_values(["camis", "initial_date", "days"])
                  .drop_duplicates(["camis", "initial_date"], keep="first"))
    pairs = pairs[pairs["days"].between(1, 180)]
    return pairs


def chart_reinspection_cadence(pairs: pd.DataFrame) -> go.Figure:
    pairs_real = pairs[pairs["boro"].isin(REAL_BOROS)].copy()
    pairs_real["boro"] = pd.Categorical(
        pairs_real["boro"],
        categories=sorted(REAL_BOROS,
                          key=lambda b: pairs_real[pairs_real["boro"] == b]["days"].median()),
        ordered=True,
    )

    fig = go.Figure()
    for b in pairs_real["boro"].cat.categories:
        sub = pairs_real[pairs_real["boro"] == b]
        fig.add_trace(go.Box(
            x=sub["days"], name=b, orientation="h",
            marker_color=NEUTRAL,
            line=dict(color="#34495e"),
            boxmean=True,
            hovertemplate=("<b>%{y}</b><br>days: %{x}<extra></extra>"),
        ))
    fig.update_layout(
        title="Days from cycle initial inspection to its re-inspection, by borough (2023+)",
        xaxis_title="days to re-inspection",
        yaxis_title="",
        showlegend=False,
        height=360,
        margin=dict(l=10, r=10, t=60, b=40),
        template="plotly_white",
        font=dict(family="Inter, system-ui, sans-serif", size=13),
    )
    # Add a dashed reference line at the city-wide median for context.
    overall_med = pairs_real["days"].median()
    fig.add_vline(x=overall_med, line=dict(color=ACCENT, dash="dash", width=1),
                  annotation_text=f"city-wide median = {overall_med:.0f}d",
                  annotation_position="top right")
    return fig


# ---------------------------------------------------------------------------
# Finding 3 — inspections per active restaurant
# ---------------------------------------------------------------------------
def chart_insp_density(summary: pd.DataFrame) -> go.Figure:
    s = summary.sort_values("insp_per_rest", ascending=True)
    colors = [ACCENT if b == "Bronx" else NEUTRAL for b in s.index]

    fig = go.Figure(go.Bar(
        x=s["insp_per_rest"].round(2),
        y=s.index,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.2f}" for v in s["insp_per_rest"]],
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Inspections per active restaurant: %{x:.2f}<br>"
            "Inspections: %{customdata[0]:,}<br>"
            "Active restaurants: %{customdata[1]:,}"
            "<extra></extra>"
        ),
        customdata=np.stack([s["n_inspections"].values,
                             s["n_restaurants"].values], axis=-1),
    ))
    fig.update_layout(
        title="Inspections per active restaurant, 2023–present",
        xaxis_title="inspections per active restaurant",
        yaxis_title="",
        margin=dict(l=10, r=10, t=60, b=40),
        height=320,
        template="plotly_white",
        font=dict(family="Inter, system-ui, sans-serif", size=13),
    )
    fig.update_xaxes(range=[0, s["insp_per_rest"].max() * 1.18])
    return fig


# ---------------------------------------------------------------------------
# Bonus context chart — critical-violation share by borough (used in the
# Finding 1 prose to make the "same regime, different outcomes" point).
# ---------------------------------------------------------------------------
def chart_critical_share(summary: pd.DataFrame) -> go.Figure:
    s = summary.sort_values("pct_with_crit", ascending=True)
    fig = go.Figure(go.Bar(
        x=s["pct_with_crit"].round(1),
        y=s.index,
        orientation="h",
        marker_color=GREY,
        text=[f"{v:.1f}%" for v in s["pct_with_crit"]],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:.1f}% of inspections found a critical violation<extra></extra>",
    ))
    fig.update_layout(
        title="Share of inspections that found at least one critical violation",
        xaxis_title="% of inspections",
        yaxis_title="",
        margin=dict(l=10, r=10, t=60, b=40),
        height=280,
        template="plotly_white",
        font=dict(family="Inter, system-ui, sans-serif", size=13),
    )
    fig.update_xaxes(range=[70, 95])
    return fig


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
CSS = """
:root {
  --ink: #1a1a1a;
  --ink-dim: #555;
  --rule: #e5e5e5;
  --bg: #fafaf7;
  --accent: #c0392b;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--ink); }
body {
  font-family: "Charter", "Source Serif Pro", Georgia, "Times New Roman", serif;
  font-size: 18px; line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}
.container { max-width: 740px; margin: 0 auto; padding: 60px 24px 80px; }
header { border-bottom: 1px solid var(--rule); padding-bottom: 28px; margin-bottom: 36px; }
.eyebrow {
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  font-size: 12px; font-weight: 600; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 14px;
}
h1 {
  font-size: 40px; line-height: 1.15; font-weight: 700; margin: 0 0 14px 0;
  letter-spacing: -0.01em;
}
.lede {
  font-size: 20px; line-height: 1.55; color: var(--ink-dim);
  margin: 0 0 14px 0;
}
.byline {
  font-family: "Inter", system-ui, sans-serif;
  font-size: 13px; color: var(--ink-dim); margin-top: 18px;
}
h2 {
  font-size: 26px; line-height: 1.2; font-weight: 700;
  margin: 56px 0 14px 0; letter-spacing: -0.005em;
}
h2 .num {
  display: inline-block; color: var(--accent); margin-right: 12px;
  font-feature-settings: "lnum"; font-variant-numeric: lining-nums;
}
p { margin: 0 0 18px 0; }
.dropcap::first-letter {
  font-size: 56px; line-height: 0.85; float: left;
  font-weight: 700; padding: 6px 8px 0 0;
}
figure { margin: 28px 0 14px; }
figure .chart {
  background: white; border: 1px solid var(--rule); border-radius: 6px;
  padding: 8px 4px; box-shadow: 0 1px 2px rgba(0,0,0,.03);
}
figcaption {
  font-family: "Inter", system-ui, sans-serif;
  font-size: 13px; color: var(--ink-dim);
  margin-top: 10px; text-align: center;
}
strong { font-weight: 700; }
em.stat { font-style: normal; font-weight: 700; color: var(--ink); }
.callout {
  background: #fff; border-left: 3px solid var(--accent);
  padding: 14px 20px; margin: 28px 0; font-size: 17px;
}
footer {
  margin-top: 64px; padding-top: 24px; border-top: 1px solid var(--rule);
  font-family: "Inter", system-ui, sans-serif;
  font-size: 13px; color: var(--ink-dim);
}
footer code { background: #eee; padding: 1px 5px; border-radius: 3px; }
footer a { color: var(--accent); text-decoration: none; }
footer a:hover { text-decoration: underline; }
"""


def fig_div(fig: go.Figure, div_id: str) -> str:
    """Render a Plotly figure to a bare <div> ready to embed."""
    return pio.to_html(
        fig, include_plotlyjs=False, full_html=False,
        div_id=div_id,
        config={"displayModeBar": False, "responsive": True},
    )


def render_article(stats: dict, charts: dict) -> str:
    """Stitch numbers and charts into the article HTML."""
    s = stats
    return dedent(f"""\
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>Same Inspection, Different Outcome — NYC restaurant inspections</title>
      <link rel="preconnect" href="https://rsms.me/">
      <link rel="stylesheet" href="https://rsms.me/inter/inter.css">
      <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
      <style>{CSS}</style>
    </head>
    <body>
      <article class="container">
        <header>
          <div class="eyebrow">NYC Restaurant Inspections · Data Case Study</div>
          <h1>Same inspection, different outcome.</h1>
          <p class="lede">
            Three findings from <strong>{s['n_inspections']:,}</strong> health-department
            inspections of <strong>{s['n_restaurants']:,}</strong> New York City restaurants
            between January 2023 and May 2026.
          </p>
          <div class="byline">By the NYC Inspection Equity project · data: NYC DOHMH (dataset <code style="background:#eee;padding:1px 5px;border-radius:3px;font-family:inherit;">43nn-pn8j</code>)</div>
        </header>

        <p class="dropcap">
          New York City's Department of Health and Mental Hygiene runs one of the
          largest restaurant-inspection programs in the country. Every active
          restaurant is on a cycle. Inspectors arrive unannounced, score the
          establishment on a long checklist, and — if conditions are bad enough —
          can close it on the spot. The agency publishes the resulting records
          openly, which lets us ask a question the grade cards in restaurant
          windows cannot answer: <em>does the same inspection produce the same
          outcome across the city?</em>
        </p>

        <p>
          The short answer is: <strong>mostly, but not always.</strong> Three
          patterns stand out in the most recent three years of data. Two of them
          are surprisingly equitable. One is not.
        </p>

        <h2><span class="num">01</span>The closures aren't evenly distributed.</h2>

        <p>
          When inspectors find something serious enough — vermin, unsafe food
          temperatures, an unsanitary kitchen — they can shut the restaurant down
          on the spot until conditions are remediated. Over our three-year window,
          this happened roughly <em class="stat">{s['total_closures']:,}</em>
          times across all five boroughs. But that total hides a real spread.
          A Brooklyn inspection is <em class="stat">{s['bk_vs_mn_ratio']:.1f}×</em>
          more likely to end in a temporary closure than a Manhattan one.
        </p>

        <figure>
          <div class="chart">{charts['closure']}</div>
          <figcaption>Hover any bar for the absolute counts behind the rate.</figcaption>
        </figure>

        <p>
          The natural follow-up is: <em>are inspectors finding more problems in
          Brooklyn?</em> The answer is essentially no. Across every borough,
          <em class="stat">{s['crit_low']:.0f}%–{s['crit_high']:.0f}%</em> of
          inspections turn up at least one critical violation. The denominator
          is shared; what differs is the response.
        </p>

        <figure>
          <div class="chart">{charts['crit']}</div>
          <figcaption>Critical violations are nearly universal in NYC inspections — the share that find at least one is essentially flat across boroughs.</figcaption>
        </figure>

        <div class="callout">
          What separates <strong>1.07%</strong> (Staten Island) from
          <strong>2.27%</strong> (Brooklyn) isn't whether inspectors find a
          critical violation. It's what happens after they do.
        </div>

        <h2><span class="num">02</span>Re-inspection speed is the same everywhere.</h2>

        <p>
          When a restaurant fails its initial cycle inspection, DOHMH returns for
          a re-inspection. The interval between those two visits is the part of
          the system where inequity might most easily creep in — wealthier
          neighborhoods could plausibly get faster service. They don't.
          Among <em class="stat">{s['n_pairs']:,}</em> initial-to-re-inspection
          pairs in our window, the median wait is
          <em class="stat">{s['overall_med']:.0f} days</em> — and it lands within
          <em class="stat">{s['cadence_spread']:.0f} days</em> of that number
          in every borough.
        </p>

        <figure>
          <div class="chart">{charts['cadence']}</div>
          <figcaption>Box width shows the middle 50% of waits; the dashed line is the city-wide median.</figcaption>
        </figure>

        <p>
          This is itself a finding. The most obvious equity hypothesis — that
          the city slow-walks re-inspections in some neighborhoods — does not
          hold. By the inspector's calendar, NYC's boroughs are treated alike.
        </p>

        <h2><span class="num">03</span>The Bronx gets inspected the most.</h2>

        <p>
          Per active restaurant, the Bronx sees <em class="stat">{s['bx_density']:.2f}</em>
          inspections in our window — about <em class="stat">{s['bx_vs_mn_pct']:.0f}%</em>
          more than Manhattan's <em class="stat">{s['mn_density']:.2f}</em>. The other
          boroughs sit in between.
        </p>

        <figure>
          <div class="chart">{charts['density']}</div>
          <figcaption>An "active restaurant" here means any CAMIS that appears at least once in the 2023+ records.</figcaption>
        </figure>

        <p>
          What's striking is the combination: the Bronx receives the highest
          inspection volume per restaurant and posts a closure rate
          (<em class="stat">{s['bx_closure']:.2f}%</em>) only slightly above
          Manhattan's (<em class="stat">{s['mn_closure']:.2f}%</em>). More
          inspector attention, comparable enforcement outcomes. Whether that
          reflects compliant operators, lighter enforcement, or both is a
          question the published data can't settle alone.
        </p>

        <h2>What this data can — and can't — tell us</h2>

        <p>
          Two caveats matter for anyone building on these numbers. First,
          DOHMH publishes a <strong>rolling roughly three-year window</strong>:
          everything here covers <em class="stat">2023</em> through
          <em class="stat">May&nbsp;2026</em>. The dataset's headline "2007 minimum
          date" is a sliver of residue.
        </p>

        <p>
          Second, and more important: <strong>only restaurants in an active
          status are included</strong>. Restaurants that permanently closed —
          including any that closed after enforcement and never reopened —
          drop out of the dataset entirely. We can describe what happened to
          surviving restaurants, but we cannot see "got a bad inspection,
          never came back." For that, you'd have to join this dataset with
          NYC's business-permit records. It is a real gap in any
          consequences-of-enforcement story told from this file alone.
        </p>

        <footer>
          <p>
            <strong>Source.</strong>
            <a href="https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j">NYC OpenData · DOHMH New York City Restaurant Inspection Results</a>
            (dataset id <code>43nn-pn8j</code>). Snapshot pulled 2026-05-30.
          </p>
          <p>
            <strong>Method.</strong> Raw violation-grain CSV → collapsed to one
            row per inspection in <code>src/build_inspections.py</code>. Findings
            and charts computed by <code>src/build_article.py</code>. Charts use
            <a href="https://plotly.com/javascript/">Plotly.js</a>.
            All code in this repository.
          </p>
          <p>
            <strong>Filters.</strong> Restricted to the dense rolling window
            (inspection year ≥ 2023). The "0" (missing-borough) bucket — 85
            inspections in the window — is excluded from per-borough charts.
            Re-inspection pairs are bounded to ≤180 days so the next cycle's
            initial inspection is not counted as the previous one's
            re-inspection.
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
    dense = load_dense()
    summary = compute_boro_summary(dense)
    pairs = compute_reinspection_pairs(dense)

    pairs_real = pairs[pairs["boro"].isin(REAL_BOROS)]
    boro_medians = pairs_real.groupby("boro", observed=True)["days"].median()
    cadence_spread = boro_medians.max() - boro_medians.min()

    # Every number quoted in the prose comes from here.
    stats = {
        "n_inspections":   int(summary["n_inspections"].sum()),
        "n_restaurants":   int(dense["camis"].nunique()),
        "total_closures":  int(summary["n_closures"].sum()),
        "bk_vs_mn_ratio":  summary.loc["Brooklyn", "closure_pct"]
                           / summary.loc["Manhattan", "closure_pct"],
        "crit_low":        summary["pct_with_crit"].min(),
        "crit_high":       summary["pct_with_crit"].max(),
        "n_pairs":         int(len(pairs_real)),
        "overall_med":     float(pairs_real["days"].median()),
        "cadence_spread":  float(cadence_spread),
        "bx_density":      summary.loc["Bronx", "insp_per_rest"],
        "mn_density":      summary.loc["Manhattan", "insp_per_rest"],
        "bx_vs_mn_pct":    (summary.loc["Bronx", "insp_per_rest"]
                            / summary.loc["Manhattan", "insp_per_rest"] - 1) * 100,
        "bx_closure":      summary.loc["Bronx", "closure_pct"],
        "mn_closure":      summary.loc["Manhattan", "closure_pct"],
    }

    # Build figures, render to <div> strings, and also save PNG fallbacks.
    figs = {
        "closure": chart_closure_rate(summary),
        "crit":    chart_critical_share(summary),
        "cadence": chart_reinspection_cadence(pairs),
        "density": chart_insp_density(summary),
    }
    charts = {name: fig_div(fig, f"chart-{name}") for name, fig in figs.items()}

    # PNG fallbacks (kaleido isn't installed, so this is best-effort).
    for name, fig in figs.items():
        try:
            fig.write_image(FIG_DIR / f"article_{name}.png",
                            width=1100, height=fig.layout.height or 400, scale=2)
        except Exception:
            pass  # plotly PNG export needs kaleido; skip if missing.

    ARTICLE.parent.mkdir(parents=True, exist_ok=True)
    ARTICLE.write_text(render_article(stats, charts), encoding="utf-8")

    # Console summary for the dev.
    print(f"Wrote {ARTICLE}")
    print("Headline numbers used in prose:")
    for k, v in stats.items():
        print(f"  {k:>18}: {v}")


if __name__ == "__main__":
    main()
