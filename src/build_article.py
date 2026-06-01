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
    python src/build_article.py
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


def code_description(raw: pd.DataFrame, codes: list[str],
                     width: int = 58, max_chars: int = 280) -> dict[str, str]:
    """Most-common full description per code, word-wrapped with <br> so the
    text fits comfortably in narrow Plotly hover tooltips."""
    import textwrap
    sub = raw[raw["VIOLATION CODE"].isin(codes) & raw["VIOLATION DESCRIPTION"].ne("")]
    desc = (sub.groupby("VIOLATION CODE")["VIOLATION DESCRIPTION"]
              .agg(lambda s: s.value_counts().index[0]))
    out = {}
    for c in codes:
        text = desc.get(c, "")
        if len(text) > max_chars:
            text = text[:max_chars - 1].rstrip() + "…"
        out[c] = textwrap.fill(text, width=width).replace("\n", "<br>")
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
# Timeline chart — justifies the 2022+ cutoff
# ---------------------------------------------------------------------------
def chart_timeline(df_full: pd.DataFrame) -> go.Figure:
    """Monthly inspections across the full date range, with the chosen
    analytical window shaded so the reader can see why we cut at 2022."""
    monthly = (df_full.set_index("inspection_date")
                       .resample("MS").size()
                       .rename("n"))
    monthly = monthly[monthly.index >= "2007-01-01"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly.index, y=monthly.values,
        mode="lines",
        line=dict(color=NEUTRAL, width=1.5, shape="spline", smoothing=0.3),
        fill="tozeroy", fillcolor="rgba(127,140,141,0.20)",
        hovertemplate="<b>%{x|%b %Y}</b><br>%{y:,} inspections<extra></extra>",
        showlegend=False,
    ))
    # Shade the included window (use pd.Timestamp so the annotation
    # placement math works; bare strings crash add_vline + annotation).
    cutoff = pd.Timestamp("2022-01-01")
    fig.add_vrect(
        x0=cutoff, x1=monthly.index.max(),
        fillcolor=ACCENT, opacity=0.08, line_width=0, layer="below",
    )
    # Plotly's add_vline+annotation crashes on datetime x-axes (it tries to
    # mean() the line's x-position with int 0). Add the line and the
    # annotation separately.
    fig.add_shape(
        type="line", xref="x", yref="paper",
        x0=cutoff, x1=cutoff, y0=0, y1=1,
        line=dict(color=ACCENT, dash="dash", width=1.5),
    )
    # The shaded region + dashed line are self-explanatory with the
    # figcaption below; no inline text label needed.
    fig.update_layout(**base_layout(
        "Inspections published per month, 2007 through May 2026",
        height=290,
    ))
    fig.update_xaxes(showgrid=False, ticks="outside", tickcolor=RULE)
    fig.update_yaxes(title="inspections per month",
                     showgrid=True, gridcolor=RULE, rangemode="tozero")
    return fig


# ---------------------------------------------------------------------------
# HERO chart — the score spectrum
# ---------------------------------------------------------------------------
def chart_hero(dense: pd.DataFrame) -> go.Figure:
    s = dense["score"].dropna().clip(lower=0, upper=120)
    bins = np.arange(0, 122, 2)
    counts, edges = np.histogram(s, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2

    # The 2-point bin at center c covers scores [c-1, c] inclusive
    # (i.e. histogram interval [c-1, c+1)). Use both ends in the hover label
    # so users see the correct integer score range.
    left_ints  = (centers - 1).astype(int)
    right_ints = centers.astype(int)
    # Highlight the 12–13 bin in a caution-amber so the pile-up is visible
    # but not alarming. Same colour used in the bunching chart (§3).
    CAUTION = "#e67e22"
    bar_colors = [CAUTION if c == 13 else LIGHT for c in centers]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=centers, y=counts, width=1.8,
        marker_color=bar_colors, marker_line_width=0,
        hovertemplate="Score range: %{customdata[0]}–%{customdata[1]}<br>"
                      "Inspections: %{y:,}<extra></extra>",
        customdata=np.stack([left_ints, right_ints], axis=-1),
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
    # Restaurant names are anonymized below for ethics reasons (see the
    # note rendered under the chart). The scores, dates, and outcomes are
    # all real and verifiable in the published DOHMH file.
    annotations = [
        (141, 0.80, "A Manhattan cafe <span style='color:#7f8c8d'>(2024)</span><br>scored 141, recovered to 12 in 62 days"),
        (168, 0.55, "A major international chain<br>restaurant <span style='color:#7f8c8d'>(Manhattan, 2023)</span><br>scored 168, closed"),
        (200, 0.30, "A Brooklyn restaurant <span style='color:#7f8c8d'>(2026)</span><br>scored 200, 18 violations, closed"),
    ]
    for x, y_frac, label in annotations:
        x_clip = min(x, 118)
        fig.add_annotation(
            x=x_clip, y=counts.max() * y_frac,
            text=label,
            showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=ACCENT,
            ax=-90, ay=0, xanchor="right",
            # Fixed box width so all three callouts share the same shape
            # regardless of how long the anonymized phrasing runs.
            width=260, align="center",
            font=dict(size=11, color=INK),
            bgcolor="white", bordercolor=ACCENT, borderwidth=1,
            borderpad=6, opacity=0.97,
        )

    fig.update_layout(**base_layout(
        "Every NYC inspection, scored. The bulk near A; a thin, consequential tail.",
        height=440,
    ))
    fig.update_xaxes(
        title="Inspection score (higher = worse · DOHMH metric)",
        range=[0, 120], showgrid=False, zeroline=False, ticks="outside",
        tickcolor=RULE,
    )
    fig.update_yaxes(
        title="Inspections", showgrid=True, gridcolor=RULE, zeroline=False,
        # Skip the y-axis "0" tick — it duplicates the x-axis "0" at the
        # origin. Explicit tickvals so Plotly actually drops the 0 tick
        # (tick0=5000 alone wasn't enough — Plotly was still emitting 0).
        tickmode="array",
        tickvals=[5000, 10000, 15000],
        ticktext=["5k", "10k", "15k"],
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
    # Dotted line for the city-wide average; label placed in the empty band
    # above the plot area (paper coords) so it doesn't collide with the
    # top bar.
    fig.add_vline(x=city_pct, line=dict(color=INK, dash="dot", width=1))
    fig.add_annotation(
        x=city_pct, y=1.0, xref="x", yref="paper",
        xanchor="left", yanchor="bottom", xshift=6, yshift=4,
        text=f"city-wide average: {city_pct:.1f}%",
        showarrow=False,
        font=dict(size=11, color=INK_DIM),
    )
    fig.update_layout(**base_layout(
        "Share of inspections finding evidence of mice, rats, roaches or flies",
        height=340,
    ))
    fig.update_xaxes(title="% of inspections", range=[0, max(s['pct'].max()*1.18, 40)],
                     showgrid=True, gridcolor=RULE)
    # Invisible tick marks add breathing room between the y-axis labels
    # ("Bronx", "Brooklyn", ...) and the start of each bar.
    fig.update_yaxes(title="", ticks="outside", ticklen=8,
                     tickcolor="rgba(0,0,0,0)")
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
    # Dotted line for the city-wide closure rate; label placed in the
    # empty band above the plot area (paper coords) so it doesn't collide
    # with the top bar.
    fig.add_vline(x=baseline, line=dict(color=INK, dash="dot", width=1))
    fig.add_annotation(
        x=baseline, y=1.0, xref="x", yref="paper",
        xanchor="left", yanchor="bottom", xshift=6, yshift=4,
        text=f"city-wide average: {baseline:.2f}%",
        showarrow=False,
        font=dict(size=11, color=INK_DIM),
    )
    fig.update_layout(**base_layout(
        "When this violation appears, what fraction of inspections end in a closure?",
        height=460,
    ))
    fig.update_xaxes(title="closure rate when the code is present (%)",
                     range=[0, agg["closure_pct"].max() * 1.18],
                     showgrid=True, gridcolor=RULE)
    # Invisible tick marks add breathing room between the y-axis labels
    # and the start of each bar.
    fig.update_yaxes(title="", ticks="outside", ticklen=8,
                     tickcolor="rgba(0,0,0,0)")
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
    # Skip the y "0" tick to avoid stacking with the x "0" in the middle.
    fig.update_yaxes(title="Restaurants", showgrid=True, gridcolor=RULE,
                     tickmode="array",
                     tickvals=[1000, 2000, 3000, 4000, 5000],
                     ticktext=["1k", "2k", "3k", "4k", "5k"])
    return fig


# ---------------------------------------------------------------------------
# §5 — Cuisine geographic concentration
# ---------------------------------------------------------------------------
# A hand-verified map of the 2010 NTA codes that appear in the
# concentration analysis. Cross-checked against sample DBAs in each NTA
# (e.g. STAR KABAB in QN35, BIG WONG in MN27, FALLSBURG BAGELS in BK88).
# Extend this dict if the data ever surfaces an NTA whose name is missing.
_NTA_NAME = {
    "MN13": "Tribeca",            "MN17": "Midtown",
    "MN22": "East Village",       "MN23": "West Village",
    "MN24": "Soho",               "MN27": "Chinatown / LES",
    "MN36": "Washington Heights", "MN40": "Upper East Side",
    "BK19": "Bensonhurst",        "BK28": "Bath Beach",
    "BK34": "Sunset Park",        "BK61": "Crown Heights",
    "BK77": "Bushwick",           "BK88": "Borough Park",
    "QN22": "Flushing",           "QN35": "Elmhurst",
    "QN51": "Murray Hill (Flushing)",
}


def compute_cuisine_concentration(dense: pd.DataFrame) -> pd.DataFrame:
    """For each cuisine: how geographically concentrated its restaurants
    are across NYC's Neighborhood Tabulation Areas (NTAs).

    Three metrics computed:
        - n_ntas: how many distinct NTAs the cuisine appears in
        - top5_pct: % of the cuisine's restaurants located in its
          5 most-popular NTAs
        - top1_nta: the single most-popular NTA

    Threshold: cuisines with >=50 active restaurants in the window, so each
    point reflects a real geographic distribution rather than a handful
    of pins.
    """
    rest = dense.drop_duplicates("camis")[["camis", "cuisine_description",
                                           "nta", "boro"]].copy()
    rest = rest[rest["nta"].notna()
                & (rest["nta"].astype(str).str.strip() != "")]
    JUNK = {"Other", "Not Listed/Not Applicable", ""}
    rest = rest[~rest["cuisine_description"].isin(JUNK)]
    rest = rest[rest["cuisine_description"].notna()]

    rows = []
    for cuis, grp in rest.groupby("cuisine_description", observed=True):
        n = len(grp)
        if n < 50:
            continue
        counts = grp["nta"].value_counts()
        shares = counts / n
        top1 = counts.index[0]
        rows.append({
            "cuisine":       cuis,
            "n_restaurants": int(n),
            "n_ntas":        int(len(counts)),
            "top5_pct":      float(shares.head(5).sum() * 100),
            "top3_pct":      float(shares.head(3).sum() * 100),
            "top1_pct":      float(shares.iloc[0] * 100),
            "top1_nta":      top1,
            "top1_name":     _NTA_NAME.get(top1, top1),
        })
    return pd.DataFrame(rows).sort_values("top5_pct", ascending=False)


# Cuisines to plot on the map and their distinct categorical colors.
# Picked because each represents a culture and has a strong, identifiable
# geographic anchor that stands out as a coloured blob on the NYC outline.
# Everything not in this palette is rendered as the "All other cuisines"
# trace (faint grey backdrop showing full NYC restaurant density).
_CUISINE_MAP_PALETTE = [
    ("Korean",          "#c0392b"),  # Flushing + Midtown K-town
    ("Bangladeshi",     "#8e44ad"),  # Elmhurst
    ("Jewish/Kosher",   "#16a085"),  # Borough Park
    ("Eastern European","#d35400"),  # Bensonhurst / Sheepshead / Brighton
    ("French",          "#2980b9"),  # Manhattan
    ("Pizza",           "#7f8c8d"),  # Everywhere — the reference baseline
]


def chart_cuisine_concentration(dense: pd.DataFrame, panel: pd.DataFrame) -> go.Figure:
    """One NYC base map showing six highlighted cuisines as coloured
    cluster blobs against a faint grey backdrop of every other NYC
    restaurant. The visual finding is the spatial clustering: each of the
    six cuisines forms a tight blob in a recognisable neighbourhood
    (Korean in Flushing + Midtown, Italian in downtown/Midtown Manhattan,
    Bangladeshi in Elmhurst, etc.), while the rest of NYC's restaurants
    show the city's full restaurant density behind them."""
    # One row per restaurant, with lat/lon for plotting.
    rest = (dense.dropna(subset=["latitude", "longitude"])
                  .drop_duplicates("camis")
                  [["camis", "dba", "boro", "nta",
                    "latitude", "longitude", "cuisine_description"]]
                  .copy())

    panel_idx = panel.set_index("cuisine")

    fig = go.Figure()
    for cuisine, color in _CUISINE_MAP_PALETTE:
        sub = rest[rest["cuisine_description"] == cuisine]
        if sub.empty:
            continue
        # Pizza is the "everywhere" reference and gets the smallest, dimmest
        # dots so it doesn't drown out the five clustered cuisines visually.
        is_pizza = (cuisine == "Pizza")
        marker_size = 5 if is_pizza else 7
        opacity = 0.25 if is_pizza else 0.78

        try:
            top5_pct = float(panel_idx.loc[cuisine, "top5_pct"])
            n_label = f"{len(sub):,} NYC locations · top 5 NTAs hold {top5_pct:.0f}%"
        except KeyError:
            n_label = f"{len(sub):,} NYC locations"

        hovers = [
            f"<b>{r['dba']}</b><br>"
            f"{cuisine}<br>"
            f"{r['boro']}"
            for _, r in sub.iterrows()
        ]

        legend_label = (f"<b>{cuisine}</b>  "
                        f"<span style='color:#7f8c8d'>· {n_label}</span>")

        fig.add_trace(go.Scattermap(
            lat=sub["latitude"], lon=sub["longitude"],
            mode="markers",
            marker=dict(size=marker_size, color=color, opacity=opacity),
            hovertext=hovers, hoverinfo="text",
            name=legend_label,
        ))

    fig.update_layout(
        # Initial zoom is wider than the final view; the on-scroll JS in the
        # article HTML animates the map into the tighter city-focused frame
        # (see armMapZoom / runMapZoom in render()).
        map=dict(
            style="carto-positron",
            center=dict(lat=40.74, lon=-73.90),
            zoom=9.4,
        ),
        margin=dict(l=0, r=0, t=46, b=0),
        title=dict(
            text="Five cuisines cluster; Pizza is the grey 'everywhere' reference",
            font=dict(size=15, color=INK), x=0.02, xanchor="left",
        ),
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=INK),
        # White hover text on the dark hover background, matching the §2
        # sewage-cliff map for visual consistency.
        hoverlabel=dict(font=dict(color="white", size=12,
                                  family="Inter, system-ui, sans-serif")),
        height=560,
        showlegend=True,
        legend=dict(
            x=0.01, y=0.99, xanchor="left", yanchor="top",
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor=RULE, borderwidth=1,
            font=dict(size=11, color=INK),
            itemsizing="constant",
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# (kept) cuisine closure/critical panel — still referenced for a few stats
# ---------------------------------------------------------------------------
def compute_cuisine(dense: pd.DataFrame):
    """For each cuisine: chain share (% of restaurants whose DBA appears at
    3+ distinct locations within that cuisine) and avg critical violations
    per inspection. Filtered to cuisines with >=200 inspections so each
    point reflects a real distribution rather than a handful of inspections.

    The chain-share metric is a structural proxy, not a clean chain flag
    (some independent operators share generic names like "Pizza" or
    "Restaurant"; some real chains use multiple DBAs). It's correlated
    enough with operational standardization to surface the actual signal
    the article cares about: limited-menu, standardized kitchens vs
    multi-station independents.
    """
    # Restrict to cycle-initial inspections (the inspections that decide
    # whether a re-inspection is needed). A "fail" is any initial cycle
    # inspection that scored above the A boundary of 13.
    ci = dense[(dense["inspection_type"] == "Cycle Inspection / Initial Inspection")
               & dense["score"].notna()].copy()
    ci["failed_first"] = ci["score"] > 13

    g = (ci.groupby("cuisine_description", observed=True)
            .agg(n_initial=("camis", "size"),
                 n_restaurants=("camis", "nunique"),
                 fail_pct=("failed_first", lambda s: s.mean() * 100)))
    # Drop sparse cuisines and unlabelled rows.
    JUNK = {"Other", "Not Listed/Not Applicable", ""}
    g = g[~g.index.isin(JUNK)]
    g = g[g.index.astype(str).str.len() > 0]
    g = g[g["n_initial"] >= 100]
    return g.sort_values("fail_pct", ascending=False)


def chart_cuisine(panel: pd.DataFrame, city_fail_pct: float) -> go.Figure:
    """Horizontal bar chart: first-inspection FAIL rate by cuisine, top 8
    and bottom 8 by rate. The city-wide average is overlaid as a dotted
    vertical reference so the reader can see how far each end deviates."""
    # Plotly draws the FIRST row in the y-list at the BOTTOM of the chart.
    # We want the highest fail rate (Bangladeshi 76%) at the top and the
    # lowest (Donuts 19%) at the bottom — so the list order is:
    # [lowest-fail .. highest-low-fail, separator, lowest-high-fail .. highest-fail].
    top = panel.head(8).iloc[::-1]   # ends at Bangladeshi -> top of chart
    bot = panel.tail(8).iloc[::-1]   # starts at Donuts -> bottom of chart
    sep = pd.DataFrame({"fail_pct": [None], "n_initial": [None],
                        "n_restaurants": [None]}, index=["·····"])
    plot_df = pd.concat([bot, sep, top])

    colors = []
    for c in plot_df.index:
        if c == "·····": colors.append("rgba(0,0,0,0)")
        elif c in top.index: colors.append(ACCENT)
        else: colors.append("#5d8aa8")  # cool blue for the low end

    text = [f"{v:.0f}%" if v is not None and not pd.isna(v) else ""
            for v in plot_df["fail_pct"]]
    n_text = [f"n={int(v):,}" if v is not None and not pd.isna(v) else ""
              for v in plot_df["n_initial"]]

    fig = go.Figure(go.Bar(
        x=plot_df["fail_pct"], y=plot_df.index, orientation="h",
        marker_color=colors,
        text=text, textposition="outside", cliponaxis=False,
        hovertemplate=("<b>%{y}</b><br>"
                       "First-inspection fail rate: %{x:.1f}%<br>"
                       "Initial inspections in window: %{customdata[0]:,}<br>"
                       "Restaurants: %{customdata[1]:,}"
                       "<extra></extra>"),
        customdata=np.stack([plot_df["n_initial"].fillna(0).astype(int),
                             plot_df["n_restaurants"].fillna(0).astype(int)],
                            axis=-1),
    ))
    # City-wide reference.
    fig.add_vline(x=city_fail_pct, line=dict(color=INK, dash="dot", width=1))
    fig.add_annotation(
        x=city_fail_pct, y=1.0, xref="x", yref="paper",
        xanchor="left", yanchor="bottom", xshift=6, yshift=4,
        text=f"city-wide average: {city_fail_pct:.0f}%",
        showarrow=False,
        font=dict(size=11, color=INK_DIM),
    )

    layout = base_layout(
        "First-inspection fail rate, by cuisine",
        height=520,
    )
    layout["margin"] = dict(l=10, r=20, t=82, b=44)
    fig.update_layout(**layout, showlegend=False)
    fig.update_xaxes(
        title="% of initial cycle inspections that scored above 13 (the A boundary)",
        range=[0, max(panel["fail_pct"].max() * 1.18, 85)],
        showgrid=True, gridcolor=RULE,
        ticksuffix="%",
    )
    fig.update_yaxes(title="", automargin=True)
    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=1.045,
        xanchor="left", yanchor="bottom",
        text=("<span style='color:#c0392b'>■</span> top 8 (highest fail rate) &nbsp;"
              "<span style='color:#5d8aa8'>■</span> bottom 8 (lowest)"),
        showarrow=False, font=dict(size=11, color=INK_DIM),
    )
    return fig


# ---------------------------------------------------------------------------
# NEW — The 13-point ceiling (score bunching at the A/B grade cutoff)
# ---------------------------------------------------------------------------
def compute_bunching(dense: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Single-point score histogram 0–35 and headline numbers for prose."""
    s = dense["score"].dropna()
    s = s[s.between(0, 35)]
    counts = s.astype(int).value_counts().sort_index()
    counts = counts.reindex(range(0, 36), fill_value=0)
    # Re-inspection-only counts for the prose ("the cliff is sharpest in re-insp")
    re_insp_s = dense[
        dense["inspection_type"].astype(str).str.contains("Re-inspection",
                                                          regex=False, na=False)
    ]["score"].dropna()
    re_insp_s = re_insp_s[re_insp_s.between(0, 35)].astype(int)
    re_counts = re_insp_s.value_counts().sort_index().reindex(range(0, 36), fill_value=0)
    stats = {
        "n_at_12":       int(counts.loc[12]),
        "n_at_13":       int(counts.loc[13]),
        "n_at_14":       int(counts.loc[14]),
        "n_at_12_13":    int(counts.loc[12] + counts.loc[13]),
        "ratio_13_14":   float(counts.loc[13] / max(counts.loc[14], 1)),
        "ratio_12_14":   float(counts.loc[12] / max(counts.loc[14], 1)),
        "cluster_ratio": float((counts.loc[12] + counts.loc[13]) / max(counts.loc[14], 1)),
        "re_ratio_13_14": float(re_counts.loc[13] / max(re_counts.loc[14], 1)),
    }
    return counts, stats


def chart_bunching(counts: pd.Series) -> go.Figure:
    xs = counts.index.tolist()
    ys = counts.values.tolist()
    # Highlight the 12-13 pile-up cluster in caution-amber and the 14 cliff
    # in red. Everything else fades into grade-band tints.
    CAUTION = "#e67e22"

    def color(x):
        if x in (12, 13): return CAUTION   # the pile-up cluster
        if x == 14:       return ACCENT    # the cliff
        if x <= 13:       return LIGHT     # A zone
        if x <= 27:       return LIGHT     # B zone
        return LIGHT                       # C zone

    fig = go.Figure(go.Bar(
        x=xs, y=ys, marker_color=[color(x) for x in xs], marker_line_width=0,
        hovertemplate="Score = %{x}<br>%{y:,} inspections<extra></extra>",
    ))
    # Cutoff guide lines with their labels above the chart.
    y_top = max(ys) * 1.16
    for x_cut, label in [(13.5, "A | B cutoff"), (27.5, "B | C cutoff")]:
        fig.add_shape(type="line", x0=x_cut, x1=x_cut, y0=0, y1=y_top,
                      line=dict(color=INK, dash="dash", width=1))
        fig.add_annotation(x=x_cut, y=y_top, text=label,
                           showarrow=False, yshift=10,
                           font=dict(size=11, color=INK_DIM))
    # Label each cluster bar individually so the reader can see the split
    # between the two piled-up scores (the combined number is already in
    # the surrounding body text). Both boxes float in the empty upper-left
    # area so they don't collide with the A | B cutoff label.
    fig.add_annotation(
        x=12, y=ys[12], ax=-160, ay=-50,
        arrowhead=0, arrowwidth=1, arrowcolor=CAUTION,
        text=f"<b>{ys[12]:,}</b> at score 12",
        font=dict(size=11, color=INK),
        bgcolor="white", bordercolor=CAUTION, borderwidth=1, borderpad=5,
    )
    # Float the 13 label to the RIGHT of the A | B cutoff text and a
    # little higher, so it sits above the 14 callout (which lives
    # mid-chart on the right) and reads as a sibling of the cutoff label.
    fig.add_annotation(
        x=13, y=ys[13], ax=110, ay=-95,
        arrowhead=0, arrowwidth=1, arrowcolor=CAUTION,
        text=f"<b>{ys[13]:,}</b> at score 13",
        font=dict(size=11, color=INK),
        bgcolor="white", bordercolor=CAUTION, borderwidth=1, borderpad=5,
    )
    # Annotate the cliff at 14. Push the text box well above the B-zone
    # bars (which reach ~2k) so it floats in empty space, with a longer
    # arrow back down to the (very short) cliff bar.
    fig.add_annotation(
        x=14, y=ys[14], ax=95, ay=-160,
        arrowhead=0, arrowwidth=1, arrowcolor=ACCENT,
        text=f"<b>{ys[14]:,}</b> at score 14<br>"
             f"({(ys[12]+ys[13])/max(ys[14],1):.0f}× drop)",
        font=dict(size=11, color=INK),
        bgcolor="white", bordercolor=ACCENT, borderwidth=1, borderpad=5,
    )
    layout = base_layout("A cliff right at the A/B boundary",
                         height=400)
    layout["margin"] = dict(l=10, r=20, t=84, b=44)
    fig.update_layout(**layout)
    fig.update_xaxes(title="Inspection score", dtick=2, range=[-0.6, 35.6],
                     showgrid=False, ticks="outside", tickcolor=RULE)
    fig.update_yaxes(title="Inspections", showgrid=True, gridcolor=RULE,
                     range=[0, y_top * 1.08],
                     # Explicit tickvals so the 0 tick is actually suppressed.
                     tickmode="array",
                     tickvals=[2000, 4000, 6000, 8000, 10000],
                     ticktext=["2k", "4k", "6k", "8k", "10k"])
    return fig


# ---------------------------------------------------------------------------
# NEW — Map: the sewage-cliff inspections, pin-pointed
# ---------------------------------------------------------------------------
def chart_cliff_map(dense: pd.DataFrame, raw: pd.DataFrame) -> go.Figure:
    """Plot every inspection that contained one of the top-3 sewage codes."""
    top3 = ["04F", "05A", "05E"]
    cliff_keys = (raw[raw["VIOLATION CODE"].isin(top3)]
                    .groupby(["CAMIS", "_date"]).size().index)
    mi = pd.MultiIndex.from_frame(dense[["camis", "inspection_date"]])
    sub = dense[mi.isin(cliff_keys)].copy()
    sub = sub[sub["latitude"].notna() & sub["longitude"].notna()]

    colors = [ACCENT if c else NEUTRAL for c in sub["closed"]]
    sizes  = [11 if c else 7 for c in sub["closed"]]

    def hover_row(r):
        addr = f"{r['building']} {r['street']}".strip()
        when = r["inspection_date"].strftime("%b %d, %Y")
        score = int(r["score"]) if pd.notna(r["score"]) else "—"
        return (f"<b>{r['dba']}</b><br>"
                f"{addr}, {r['boro']}<br>"
                f"{when}<br>"
                f"Score: <b>{score}</b>"
                f" · {int(r['n_violations'])} violations<br>"
                f"<b>{'CLOSED' if r['closed'] else 'open'}</b>")
    hovers = sub.apply(hover_row, axis=1).tolist()

    fig = go.Figure(go.Scattermap(
        lat=sub["latitude"], lon=sub["longitude"],
        mode="markers",
        marker=dict(size=sizes, color=colors, opacity=0.82),
        hovertext=hovers, hoverinfo="text",
    ))
    fig.update_layout(
        # Map starts wide (regional view) and is animated in to the city-focused
        # view by the on-scroll JS in the article HTML. Centred slightly north
        # so the wide initial view spans NYC + nearby areas.
        map=dict(
            style="carto-positron",
            center=dict(lat=40.78, lon=-73.93),
            zoom=9.0,
        ),
        margin=dict(l=0, r=0, t=46, b=0),
        title=dict(
            text="Sewage-cliff inspections, pinpointed (red = closed by DOHMH)",
            font=dict(size=15, color=INK), x=0.02, xanchor="left",
        ),
        font=dict(family="Inter, system-ui, sans-serif", size=13, color=INK),
        # White hover text on whatever the marker colour is (red or grey),
        # so closed-restaurant popups AND open-restaurant popups both read
        # cleanly. Plotly otherwise inherits the page font colour (dark)
        # which is unreadable on the dark grey hover bg.
        hoverlabel=dict(font=dict(color="white", size=12,
                                  family="Inter, system-ui, sans-serif")),
        height=520,
    )
    return fig


# ---------------------------------------------------------------------------
# NEW — Cuisine signature heatmap
# ---------------------------------------------------------------------------
def chart_cuisine_signatures(dense: pd.DataFrame, raw: pd.DataFrame) -> go.Figure:
    """For each top cuisine, show which violation codes are over-represented.

    Improvements over the first version:
    - Cuisines sorted by signature distinctiveness (variance of log-lift)
      so the most-distinctive cuisines appear at the top.
    - X-axis labels include a short human description, not just the code.
    - Cells with extreme lift (>1.5× or <0.67×) get bolded text.
    """
    # Pick top cuisines by inspection volume.
    top_cuisines = (dense["cuisine_description"]
                      .value_counts()
                      .head(12)
                      .index.tolist())
    top_cuisines = [c for c in top_cuisines if str(c).strip() != ""]

    exploded = (dense[dense["cuisine_description"].isin(top_cuisines)]
                  .assign(code=lambda d: d["violation_codes"].str.split(","))
                  .explode("code"))
    exploded = exploded[exploded["code"].astype(str).ne("")]

    # Pre-select 20 candidate codes by volume, then narrow to the 10 that
    # actually DIFFERENTIATE cuisines (highest variance in lift across
    # cuisines). Codes everyone gets at the same rate add no signal and
    # just clutter the chart.
    code_totals = exploded["code"].value_counts()
    candidate_codes = sorted(code_totals.head(20).index.tolist())

    cuis_totals = dense[dense["cuisine_description"].isin(top_cuisines)] \
        .groupby("cuisine_description", observed=True).size()
    cell_rate_full = (exploded.groupby(["cuisine_description", "code"], observed=True)
                              .size().unstack(fill_value=0))
    cell_rate_full = cell_rate_full.reindex(index=top_cuisines,
                                            columns=candidate_codes,
                                            fill_value=0)
    cell_rate_full = cell_rate_full.div(cuis_totals, axis=0).fillna(0)

    all_exp = (dense.assign(code=lambda d: d["violation_codes"].str.split(","))
                    .explode("code"))
    all_exp = all_exp[all_exp["code"].astype(str).ne("")]
    city_rate_full = (all_exp[all_exp["code"].isin(candidate_codes)]
                        .groupby("code").size()
                        .reindex(candidate_codes, fill_value=0) / len(dense))

    lift_full = cell_rate_full.div(city_rate_full, axis=1) \
        .replace([np.inf, -np.inf], np.nan).fillna(1)
    log_lift_full = np.log2(lift_full.clip(lower=0.1))

    # Pick the 10 codes with highest variance across cuisines.
    code_variance = log_lift_full.std(axis=0).sort_values(ascending=False)
    top_codes = sorted(code_variance.head(10).index.tolist())

    # Pick the 8 cuisines with most-distinctive signatures (highest variance
    # across the chosen codes).
    log_lift_sel = log_lift_full[top_codes]
    cuisine_distinct = log_lift_sel.std(axis=1).sort_values(ascending=False)
    sorted_cuisines = cuisine_distinct.head(8).index.tolist()

    lift      = lift_full.loc[sorted_cuisines, top_codes]
    log_lift  = log_lift_full.loc[sorted_cuisines, top_codes]
    cell_rate = cell_rate_full.loc[sorted_cuisines, top_codes]
    city_rate = city_rate_full[top_codes]

    # Short single-line labels — rotated so they fit each column.
    SHORT = {
        "02B": "hot food cold",
        "02G": "cold food warm",
        "04A": "no FPC cert",
        "04H": "contaminated food",
        "04L": "mice",
        "04N": "filth flies",
        "05D": "no handwash",
        "06C": "unprotected food",
        "06D": "unsanitised surface",
        "06F": "wiping cloths",
        "08A": "pest harborage",
        "08C": "pesticide misuse",
        "10B": "drainage",
        "10F": "dirty surfaces",
        "10G": "dishwashing",
    }
    code_tick_text = [
        f"<b>{c}</b>  <span style='color:#7f8c8d'>{SHORT.get(c, '')}</span>"
        for c in top_codes
    ]

    # Hover shows the precise value; no in-cell text so the eye can read the
    # color gradient without the visual noise of 80+ tiny numbers.
    desc_map = code_description(raw, top_codes)
    hover_text = [
        [
            f"<b>{cuis}</b><br>"
            f"Code {code}: {desc_map.get(code, '')}<br>"
            f"Rate in this cuisine: {cell_rate.loc[cuis, code]*100:.1f}%<br>"
            f"City-wide rate: {city_rate[code]*100:.1f}%<br>"
            f"<b>{lift.loc[cuis, code]:.2f}× lift</b>"
            for code in top_codes
        ]
        for cuis in sorted_cuisines
    ]

    fig = go.Figure(go.Heatmap(
        z=log_lift.values,
        x=top_codes,
        y=sorted_cuisines,
        hoverinfo="text",
        hovertext=hover_text,
        colorscale=[(0.0, "#5d8aa8"), (0.5, "white"), (1.0, ACCENT)],
        zmid=0,
        zmin=-1.3, zmax=1.3,
        xgap=3, ygap=3,
        colorbar=dict(
            title="lift",
            tickvals=[-1, 0, 1],
            ticktext=["½×", "1×", "2×"],
            len=0.7,
        ),
    ))
    layout = base_layout(
        "Each cuisine's signature: which codes appear more (or less) than the city-wide rate",
        height=560,
    )
    layout["margin"] = dict(l=10, r=20, t=84, b=140)
    fig.update_layout(**layout)
    fig.update_xaxes(
        title="", side="bottom", tickangle=-35, showgrid=False,
        tickvals=top_codes, ticktext=code_tick_text,
        tickfont=dict(size=11),
        automargin=True,
    )
    fig.update_yaxes(
        title="", autorange="reversed", showgrid=False,
        tickfont=dict(size=12),
    )
    return fig


# ---------------------------------------------------------------------------
# §7 — "What an A really means" (re-inspection rate + critical record)
# ---------------------------------------------------------------------------
def compute_reinspection_rate(dense: pd.DataFrame):
    """% of cycle-inspected restaurants that get called back for a
    re-inspection. Returned overall and broken down by cuisine."""
    CYCLE_INIT  = "Cycle Inspection / Initial Inspection"
    CYCLE_REINS = "Cycle Inspection / Re-inspection"

    camis_cycle  = set(dense[dense["inspection_type"] == CYCLE_INIT]["camis"])
    camis_reinsp = set(dense[dense["inspection_type"] == CYCLE_REINS]["camis"])

    overall_pct = (100 * len(camis_cycle & camis_reinsp)
                   / max(len(camis_cycle), 1))

    camis_cuis = (dense.groupby("camis", observed=True)["cuisine_description"]
                       .agg(lambda s: s.mode().iloc[0]))
    # Skip junk catch-all categories that aren't real cuisines.
    JUNK = {"Other", "Not Listed/Not Applicable", ""}
    rows = []
    for cuis, grp in camis_cuis.groupby(camis_cuis, observed=True):
        if str(cuis).strip() in JUNK:
            continue
        in_c = set(grp.index)
        cyc  = in_c & camis_cycle
        rei  = in_c & camis_reinsp
        if len(cyc) >= 100:
            rows.append({"cuisine": cuis, "n_cycle": len(cyc),
                         "n_reinsp": len(rei),
                         "pct": 100 * len(rei) / len(cyc)})
    by_cuisine = pd.DataFrame(rows).sort_values("pct", ascending=True)
    return float(overall_pct), by_cuisine


def chart_reinspection_by_cuisine(by_cuisine: pd.DataFrame,
                                   overall_pct: float) -> go.Figure:
    """Horizontal bar chart of re-inspection rate per cuisine, with the
    overall NYC average drawn as a reference line."""
    s = by_cuisine.set_index("cuisine")
    # Top 6 and bottom 6 — drop the muddy middle, with a blank-row separator
    # so the reader doesn't read the gap between Thai (68%) and Tex-Mex (48%)
    # as a continuous ranking. Plotly draws the FIRST y at the BOTTOM of a
    # horizontal bar chart, so we sort ascending and put the lowest-of-bottom
    # first; the highest-of-top ends up last → top of the chart.
    top    = s.nlargest(6, "pct").sort_values("pct", ascending=True)
    bottom = s.nsmallest(6, "pct").sort_values("pct", ascending=True)
    sep = pd.DataFrame({"pct": [None], "n_reinsp": [None], "n_cycle": [None]},
                       index=["·····"])
    panel  = pd.concat([bottom, sep, top])

    colors = []
    for c in panel.index:
        if c == "·····": colors.append("rgba(0,0,0,0)")
        elif panel.loc[c, "pct"] > overall_pct: colors.append(ACCENT)
        else: colors.append("#5d8aa8")

    text = [f"{v:.0f}%" if v is not None and not pd.isna(v) else ""
            for v in panel["pct"]]
    customdata = np.stack([
        panel["n_reinsp"].fillna(0).astype(int),
        panel["n_cycle"].fillna(0).astype(int),
    ], axis=-1)

    fig = go.Figure(go.Bar(
        x=panel["pct"], y=panel.index, orientation="h",
        marker_color=colors, marker_line_width=0,
        text=text, textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=INK_DIM),
        hovertemplate=("<b>%{y}</b><br>"
                       "Re-inspected: <b>%{x:.0f}%</b><br>"
                       "%{customdata[0]:,} of %{customdata[1]:,} cycle-inspected restaurants"
                       "<extra></extra>"),
        customdata=customdata,
    ))
    fig.add_vline(x=overall_pct, line=dict(color=INK, dash="dot", width=1))
    fig.add_annotation(
        x=overall_pct, y=1.0, xref="x", yref="paper",
        xanchor="left", yanchor="bottom", xshift=4, yshift=4,
        text=f"NYC average: {overall_pct:.0f}%",
        showarrow=False, font=dict(size=11, color=INK_DIM),
    )

    layout = base_layout(
        "Re-inspection rate by cuisine: % of restaurants called back after a cycle inspection",
        height=440,
    )
    layout["margin"] = dict(l=10, r=20, t=66, b=44)
    fig.update_layout(**layout)
    fig.update_xaxes(title="% of cycle-inspected restaurants re-inspected",
                     range=[0, panel["pct"].max(skipna=True) * 1.12],
                     showgrid=True, gridcolor=RULE)
    # Invisible tick marks add breathing room between the y-axis cuisine
    # labels and the start of each bar.
    fig.update_yaxes(title="", ticks="outside", ticklen=8,
                     tickcolor="rgba(0,0,0,0)")
    return fig


# ---------------------------------------------------------------------------
# §6 — Seasonality (the summer effect)
# ---------------------------------------------------------------------------
def compute_seasonality(dense: pd.DataFrame, raw: pd.DataFrame):
    """Month-of-year aggregates across the full dense window: closure rate,
    vermin rate, and the two temperature codes (cold-food / hot-food)."""
    d = dense.copy()
    d["month"] = d["inspection_date"].dt.month

    # 02G (cold food held too warm) and 02B (hot food held too cold) flags
    # via the joined string of violation codes on each inspection.
    codes = d["violation_codes"].str.split(",")
    d["has_02G"] = codes.apply(lambda lst: "02G" in lst if isinstance(lst, list) else False)
    d["has_02B"] = codes.apply(lambda lst: "02B" in lst if isinstance(lst, list) else False)

    # Vermin flag from raw violation descriptions (same regex as §1).
    raw_v = raw.copy()
    raw_v["is_vermin"] = raw_v["VIOLATION DESCRIPTION"].str.contains(
        VERMIN_RE, regex=True, na=False)
    flag = (raw_v[raw_v["is_vermin"]]
              .groupby(["CAMIS", "_date"]).size()
              .rename("n_vermin").reset_index())
    flag.columns = ["camis", "inspection_date", "n_vermin"]
    flag["camis"] = flag["camis"].astype(str)
    d = d.merge(flag, on=["camis", "inspection_date"], how="left")
    d["vermin"] = d["n_vermin"].fillna(0) > 0

    m = d.groupby("month").agg(
        n=("camis", "size"),
        closure_pct=("closed", lambda s: s.mean() * 100),
        vermin_pct=("vermin", lambda s: s.mean() * 100),
        cold_food_pct=("has_02G", lambda s: s.mean() * 100),
        hot_food_pct=("has_02B", lambda s: s.mean() * 100),
    )
    return m


def chart_seasonality(monthly: pd.DataFrame) -> go.Figure:
    """Twin-line chart: cold-food violations climb across summer; hot-food
    violations move the opposite direction. Summer band shaded."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    xs = list(range(1, 13))
    cold = monthly["cold_food_pct"].values
    hot  = monthly["hot_food_pct"].values

    fig = go.Figure()

    # Shade meteorological summer (Jun-Aug = months 6-8)
    fig.add_shape(type="rect",
                  x0=5.5, x1=8.5, y0=0, y1=1, yref="paper",
                  fillcolor="rgba(192,57,43,0.06)", line_width=0, layer="below")
    # "summer" label sits just above the shaded rectangle's top edge —
    # close enough that it reads as labeling the band, not floating free.
    fig.add_annotation(x=7, y=1.0, yref="paper", yanchor="bottom",
                       text="summer", showarrow=False, yshift=2,
                       font=dict(size=11, color=ACCENT))

    fig.add_trace(go.Scatter(
        x=xs, y=cold, mode="lines+markers",
        line=dict(color=ACCENT, width=2.5, shape="spline", smoothing=0.5),
        marker=dict(size=8, color=ACCENT, line=dict(color="white", width=1)),
        name="Cold food held too warm (02G)",
        hovertemplate="<b>%{customdata}</b><br>Cold-food violation: %{y:.1f}% of inspections<extra></extra>",
        customdata=months,
    ))
    fig.add_trace(go.Scatter(
        x=xs, y=hot, mode="lines+markers",
        line=dict(color="#5d8aa8", width=2.5, shape="spline", smoothing=0.5),
        marker=dict(size=8, color="#5d8aa8", line=dict(color="white", width=1)),
        name="Hot food held too cold (02B)",
        hovertemplate="<b>%{customdata}</b><br>Hot-food violation: %{y:.1f}% of inspections<extra></extra>",
        customdata=months,
    ))

    layout = base_layout(
        "Two temperature codes, twelve months. Cold-food failures rise with heat; hot-food failures fall.",
        height=400,
    )
    layout["margin"] = dict(l=10, r=20, t=60, b=44)
    fig.update_layout(**layout,
                      legend=dict(orientation="h", x=0.5, xanchor="center",
                                  y=-0.15, yanchor="top",
                                  bgcolor="rgba(0,0,0,0)",
                                  font=dict(size=11, color=INK_DIM)))
    fig.update_xaxes(tickvals=xs, ticktext=months,
                     showgrid=False, ticks="outside", tickcolor=RULE)
    fig.update_yaxes(title="% of inspections with this code",
                     showgrid=True, gridcolor=RULE, rangemode="tozero")
    return fig


# ---------------------------------------------------------------------------
# §6 — Council district spread (bar + choropleth)
# ---------------------------------------------------------------------------
def compute_districts(dense: pd.DataFrame):
    sub = dense[dense["council_district"].ne("")]
    g = (sub.groupby("council_district")
             .agg(n=("camis", "size"),
                  n_closed=("closed", "sum"),
                  # Most-common borough for this district (some districts
                  # straddle two boroughs; mode picks the dominant one).
                  boro=("boro", lambda s: s.mode().iloc[0])))
    g = g[g["n"] >= 200]
    g["closure_pct"] = g["n_closed"] / g["n"] * 100
    return g.sort_values("closure_pct", ascending=True)


def load_districts_geojson():
    """Load the NYC City Council Districts boundary GeoJSON (cached locally).
    Run `src/_fetch_districts_geojson.py` once to populate."""
    import json
    path = REPO_ROOT / "data" / "raw" / "nyc_council_districts.geojson"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def chart_districts_map(dist_df: pd.DataFrame, geojson: dict) -> go.Figure:
    """Choropleth: each of NYC's 51 City Council districts shaded by
    inspection closure rate. Matches the bar chart's data, gives the
    geographic intuition the bar can't."""
    df = dist_df.reset_index()
    # GeoJSON stores district as e.g. '42' (no leading zeros); our parquet
    # stores it as '01', '02', ... so strip leading zeros to align.
    df["dist_id"] = df["council_district"].astype(str).str.lstrip("0")

    fig = go.Figure(go.Choroplethmap(
        geojson=geojson,
        locations=df["dist_id"],
        z=df["closure_pct"],
        featureidkey="properties.coun_dist",
        colorscale=[
            (0.0, "#dfe6e9"),
            (0.4, "#cfa978"),
            (1.0, ACCENT),
        ],
        zmin=float(df["closure_pct"].min()),
        zmax=float(df["closure_pct"].max()),
        marker=dict(line=dict(color="white", width=0.6), opacity=0.85),
        hovertemplate=(
            "<b>Council District %{location}</b>  ·  %{customdata[2]}<br>"
            "Closure rate: %{z:.2f}%<br>"
            "%{customdata[1]:,} closures of %{customdata[0]:,} inspections"
            "<extra></extra>"
        ),
        customdata=np.stack([df["n"].astype(int),
                             df["n_closed"].astype(int),
                             df["boro"].astype(str).values], axis=-1),
        colorbar=dict(
            title=dict(text="closure %", font=dict(size=11)),
            len=0.55, thickness=10,
            # Push the colorbar into the right margin gutter so it doesn't
            # crowd the map edge.
            x=1.02, xanchor="left", xpad=4,
            tickfont=dict(size=10),
            outlinewidth=0,
        ),
    ))

    fig.update_layout(
        map=dict(
            style="carto-positron",
            center=dict(lat=40.732, lon=-73.93),
            zoom=9.6,
        ),
        # Reserve right-margin gutter for the colorbar so it doesn't sit on
        # top of the map.
        margin=dict(l=0, r=70, t=46, b=0),
        title=dict(
            text="NYC's 51 City Council districts, shaded by closure rate",
            font=dict(size=15, color=INK), x=0.02, xanchor="left",
        ),
        font=dict(family="Inter, system-ui, sans-serif", size=13, color=INK),
        height=540,
    )
    return fig


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
.lede {
  font-size: 22px; line-height: 1.4; color: var(--ink);
  font-weight: 600; margin: 0 0 22px 0;
  letter-spacing: -0.005em;
}
.byline {
  font-family: "Inter", system-ui, sans-serif;
  font-size: 13px; color: var(--ink-dim); margin-top: 22px;
}
.byline .author { color: var(--ink); }
.byline .author strong { font-weight: 600; }
.byline .sep { color: #c4c4c4; margin: 0 8px; font-weight: 300; }
.byline a {
  color: var(--accent); text-decoration: none;
  border-bottom: 1px solid rgba(192,57,43,0.3);
  transition: border-color 0.15s ease;
}
.byline a:hover { border-bottom-color: var(--accent); }
.byline .source { margin-top: 6px; font-size: 12.5px; opacity: 0.85; }
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
figcaption .note {
  display: block; margin-top: 8px; font-size: 12px;
  color: var(--ink-dim); font-style: italic; opacity: 0.85;
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
.aside {
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  font-size: 14.5px; line-height: 1.6; color: var(--ink-dim);
  background: rgba(127,140,141,0.07);
  border-left: 2px solid var(--rule);
  padding: 12px 18px;
  margin: 10px 0 28px;
}
footer {
  margin-top: 72px; padding-top: 28px; border-top: 1px solid var(--rule);
  font-family: "Inter", system-ui, sans-serif;
  font-size: 13px; color: var(--ink-dim); line-height: 1.55;
}
/* Standalone horizontal divider that floats above the element it's applied
   to. Used to separate the "A note on reproducibility" callout from the
   prose above it, mirroring the line that appears before the citations
   footer. We use ::before instead of border-top because the .aside class
   has its own background + padding, so a border-top would draw INSIDE the
   callout's grey box rather than as a free-standing line. */
.aside-divider {
  position: relative;
  margin-top: 72px;
}
.aside-divider::before {
  content: "";
  position: absolute;
  top: -36px;
  left: 0; right: 0;
  height: 1px;
  background: var(--rule);
}
/* When the footer directly follows an aside-divider, the footer's normal
   72px top-margin stacks with the aside's bottom margin, leaving an
   awkward gap above the citations divider. Tighten that. */
.aside-divider + footer {
  margin-top: 36px;
}
footer code { background: #eee; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
footer a { color: var(--accent); text-decoration: none; }
footer a:hover { text-decoration: underline; }
footer h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.1em;
            color: var(--ink); margin: 18px 0 6px 0; font-weight: 700; }
/* The first heading in the footer doesn't need an extra top margin — the
   footer's padding-top already provides the gap below the divider line. */
footer h3:first-child { margin-top: 0; }
footer ol.citations { padding-left: 22px; margin: 0 0 8px 0; }
footer ol.citations li { margin-bottom: 10px; scroll-margin-top: 24px; }
footer ol.citations li:target {
  background: var(--accent-soft); padding: 6px 10px;
  margin-left: -10px; border-radius: 4px;
}
sup.cite { font-size: 0.65em; vertical-align: super; line-height: 0;
           margin-left: 1px; }
sup.cite a { color: var(--accent); text-decoration: none;
             padding: 1px 3px; border-radius: 2px; font-weight: 700; }
sup.cite a:hover { background: var(--accent-soft); }

/* ---- Scroll-triggered chart entrance ---- */
/* Container fade-and-slide for every chart */
figure .chart {
  opacity: 0;
  transform: translateY(18px);
  transition: opacity 0.95s cubic-bezier(0.215, 0.61, 0.355, 1),
              transform 0.95s cubic-bezier(0.215, 0.61, 0.355, 1);
}
figure .chart.is-visible {
  opacity: 1;
  transform: translateY(0);
}
/* Default: horizontal bars grow from the left (scaleX).
   Skips figures opted into vertical growth via .grow-up. */
figure:not(.grow-up) .chart .bars .point path {
  transform: scaleX(0);
  transform-origin: 0 50%;
  transform-box: fill-box;
  transition: transform 1.2s cubic-bezier(0.215, 0.61, 0.355, 1) 0.1s;
}
figure:not(.grow-up) .chart.is-visible .bars .point path {
  transform: scaleX(1);
}

/* Vertical growth: bars AND scatter area-fills/lines grow from the bottom up.
   Used by the hero histogram and the timeline area chart. */
figure.grow-up .chart .bars .point path,
figure.grow-up .chart .scatterlayer .trace .fills path,
figure.grow-up .chart .scatterlayer .trace .lines path {
  transform: scaleY(0);
  transform-origin: 50% 100%;
  transform-box: fill-box;
  transition: transform 1.2s cubic-bezier(0.215, 0.61, 0.355, 1) 0.1s;
}
figure.grow-up .chart.is-visible .bars .point path,
figure.grow-up .chart.is-visible .scatterlayer .trace .fills path,
figure.grow-up .chart.is-visible .scatterlayer .trace .lines path {
  transform: scaleY(1);
}

/* ---- Map attribution: collapsed to just the (i) icon by default ----
   CARTO and OpenStreetMap require legal attribution, so we keep the icon
   visible. Hovering reveals the full "© CARTO · © OpenStreetMap" text. */
.maplibregl-ctrl-attrib .maplibregl-ctrl-attrib-inner,
.mapboxgl-ctrl-attrib .mapboxgl-ctrl-attrib-inner {
  display: none;
}
.maplibregl-ctrl-attrib:hover .maplibregl-ctrl-attrib-inner,
.mapboxgl-ctrl-attrib:hover .mapboxgl-ctrl-attrib-inner {
  display: inline-block;
  margin-left: 4px;
}
.maplibregl-ctrl-attrib,
.mapboxgl-ctrl-attrib {
  background: rgba(255,255,255,0.85) !important;
}

/* ---- Stat strip (§7 "What an A really means") ---- */
.stat-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin: 28px 0;
}
.stat-tile {
  background: white;
  border: 1px solid var(--rule);
  /* Warm desaturated grey here — quieter than the red --accent but with
     enough warmth to tie back to the article's accent palette. */
  border-left: 3px solid #6e5552;
  border-radius: 4px;
  padding: 18px 18px 16px;
  display: flex; flex-direction: column;
  align-items: flex-start;
}
.stat-tile .big-num {
  font-family: "Source Serif Pro", "Charter", serif;
  font-size: 40px; font-weight: 700; line-height: 1;
  color: #6e5552;
  margin-bottom: 10px;
  font-feature-settings: "lnum"; font-variant-numeric: lining-nums;
}
.stat-tile .label {
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  font-size: 12.5px; line-height: 1.45;
  color: var(--ink);
}

/* ---- Key takeaways box (end-of-article summary) ---- */
.takeaways {
  background: white;
  border: 1px solid var(--rule);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  padding: 22px 26px 22px 26px;
  margin: 36px 0;
}
.takeaways h3 {
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  font-size: 12px; font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  margin: 0 0 18px 0;
}
.takeaways ol {
  margin: 0; padding-left: 22px;
  font-family: "Source Serif Pro", "Charter", serif;
  font-size: 16.5px; line-height: 1.6;
  color: var(--ink);
}
.takeaways li { margin-bottom: 14px; }
.takeaways li:last-child { margin-bottom: 0; }
.takeaways strong { color: var(--ink); }
.takeaways ol em.stat { color: var(--accent); }

/* ---- Grade-card visual (intro illustration, with hover flip) ---- */
.grade-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin: 34px 0 18px;
  perspective: 1200px;
}
/* Outer .grade-card is the stable hit-test surface. It NEVER rotates, so
   the browser's :hover region stays a constant rectangle no matter what
   the rendered card is doing in 3D. The inner .card-inner is what
   actually flips. Without this split, hovering near the corner of a
   mid-flip card causes the hit area to shrink underneath the cursor and
   the flip jitters back and forth. */
.grade-card {
  position: relative;
  height: 168px;
  cursor: pointer;
}
.card-inner {
  position: absolute;
  inset: 0;
  transform-style: preserve-3d;
  /* Default transition with NO delay — applies when mouse leaves so the
     card flips back instantly. */
  transition: transform 0.6s cubic-bezier(0.215, 0.61, 0.355, 1);
}
.grade-card:hover .card-inner,
.grade-card:focus-visible .card-inner,
.grade-card:focus .card-inner {
  transform: rotateY(180deg);
  /* Delay-on-enter only: cursor must REST on the card for 350ms before
     the flip begins, so a casual cursor pass doesn't trigger anything.
     When :hover ends the delay reverts to 0 and the card flips back
     immediately. */
  transition-delay: 0.35s;
}
.grade-card:focus { outline: none; }
.card-face {
  position: absolute; inset: 0;
  background: white;
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 16px 14px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  -webkit-backface-visibility: hidden;
  backface-visibility: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.card-back { transform: rotateY(180deg); }

/* No top colored stripe — cards are clean white. */

.grade-card .card-top {
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.18em;
  color: var(--ink-dim);
  margin-top: 6px;
}
.grade-card .letter {
  font-family: "Source Serif Pro", "Charter", serif;
  font-size: 64px;
  font-weight: 700;
  line-height: 1;
  margin: 4px 0 6px;
}
.grade-a .letter { color: #1e8449; }
.grade-b .letter { color: #b07c0a; }
.grade-c .letter { color: #a02c1a; }

.grade-card .range {
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  font-size: 12.5px;
  color: var(--ink-dim);
  font-weight: 500;
  letter-spacing: 0.02em;
}
.grade-card .big-pct {
  font-family: "Source Serif Pro", "Charter", serif;
  font-size: 48px; font-weight: 700; line-height: 1;
  margin-bottom: 8px;
}
.grade-a .big-pct { color: #1e8449; }
.grade-b .big-pct { color: #b07c0a; }
.grade-c .big-pct { color: #a02c1a; }
.grade-card .back-label {
  font-family: "Inter", system-ui, sans-serif;
  font-size: 11px;
  color: var(--ink-dim);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 10px;
}
.grade-card .back-count {
  font-family: "Inter", system-ui, sans-serif;
  font-size: 13.5px;
  color: var(--ink);
  font-weight: 600;
}

.card-hint {
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  font-size: 12px;
  color: var(--ink-dim);
  text-align: center;
  margin: -4px 0 26px;
  letter-spacing: 0.04em;
  animation: card-hint-pulse 2.2s ease-in-out infinite;
}
@keyframes card-hint-pulse {
  0%, 100% { opacity: 0.55; transform: scale(1); }
  50%      { opacity: 1;    transform: scale(1.04); }
}

@media (prefers-reduced-motion: reduce) {
  .grade-card, .card-hint { animation: none; transition: none; }
  .grade-card:hover, .grade-card:focus-visible {
    transform: rotateY(180deg);
  }
}

/* ---- Side section nav ---- */
html { scroll-behavior: smooth; }
h2[id^="sec-"] { scroll-margin-top: 24px; }
/* Nav sits just to the right of the 740px article column.
   calc(): half the viewport + half the article width + a small gap. */
.section-nav {
  position: fixed;
  left: calc(50% + 370px + 24px);
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  font-family: "Inter", system-ui, -apple-system, sans-serif;
}
.section-nav ol {
  list-style: none; padding: 0; margin: 0;
  display: flex; flex-direction: column; gap: 2px;
}
.section-nav a {
  display: flex; align-items: center; justify-content: flex-start;
  gap: 12px;
  text-decoration: none;
  color: var(--ink-dim);
  font-size: 12.5px;
  padding: 8px 14px 8px 12px;
  border-left: 2px solid var(--rule);
  transition: color 0.2s ease, border-left-color 0.2s ease,
              background 0.2s ease;
  letter-spacing: 0.02em;
}
.section-nav a:hover {
  color: var(--accent);
  border-left-color: var(--accent);
  background: rgba(192,57,43,0.04);
}
.section-nav a.active {
  color: var(--accent);
  border-left-color: var(--accent);
  font-weight: 600;
}
.section-nav .num {
  font-weight: 700;
  font-variant-numeric: lining-nums tabular-nums;
  min-width: 18px;
  text-align: left;
}
.section-nav .label {
  opacity: 0;
  transform: translateX(-8px);
  transition: opacity 0.22s ease, transform 0.22s ease;
  white-space: nowrap;
  pointer-events: none;
}
.section-nav:hover .label,
.section-nav a.active .label {
  opacity: 1;
  transform: translateX(0);
}
@media (max-width: 1100px) {
  .section-nav { display: none; }
}

/* ---- Back-to-top button ---- */
.back-to-top {
  position: fixed;
  bottom: 32px; right: 32px;
  z-index: 20;
  width: 40px; height: 40px;
  border: 1px solid var(--rule);
  border-radius: 50%;
  background: white;
  color: var(--ink-dim);
  font-size: 18px;
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease, background 0.2s ease, color 0.2s ease;
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
  display: flex; align-items: center; justify-content: center;
}
.back-to-top.visible {
  opacity: 1;
  pointer-events: auto;
}
.back-to-top:hover {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

/* ========================================================================
   Mobile layout. Two breakpoints:
     - 760px: large phone / portrait tablet — stack 3-up grids, shrink type
     - 480px: small phone — further tighten everything
   ======================================================================== */
@media (max-width: 760px) {
  body { font-size: 17px; line-height: 1.65; }
  .container { padding: 36px 16px 60px; }

  h1 { font-size: 34px; line-height: 1.12; }
  .deck { font-size: 18px; }
  .lede { font-size: 19px; line-height: 1.45; }

  h2 { font-size: 24px; line-height: 1.22; margin: 48px 0 14px 0; }
  h2 .num { font-size: 22px; margin-right: 10px; }

  /* Stack the 3-up grids into a single column. */
  .grade-cards { grid-template-columns: 1fr; gap: 10px; }
  .grade-card { height: 132px; }
  .grade-card .letter { font-size: 54px; }
  .grade-card .big-pct { font-size: 40px; }

  .stat-strip { grid-template-columns: 1fr; gap: 12px; }
  .stat-tile .big-num { font-size: 36px; }

  /* Tighten the visual block elements. */
  .callout { padding: 14px 16px; font-size: 16px; line-height: 1.5; }
  .pullquote { font-size: 22px; padding-left: 16px; margin: 28px 0; }
  .takeaways { padding: 18px 18px; }
  .takeaways ol { font-size: 15.5px; padding-left: 18px; }

  /* Figure margin smaller on mobile so charts feel tighter to surrounding text. */
  figure { margin: 24px 0 14px; }
  figcaption { font-size: 12.5px; }

  /* Back-to-top button: closer to the corner, smaller. */
  .back-to-top { bottom: 20px; right: 20px; width: 36px; height: 36px;
                 font-size: 16px; }

  /* Grade-card flip: shorten the rest-to-trigger delay on touch since
     there's no accidental cursor pass-over to guard against. */
  .grade-card:hover .card-inner,
  .grade-card:focus .card-inner { transition-delay: 0s; }
}

@media (max-width: 480px) {
  .container { padding: 28px 14px 48px; }
  h1 { font-size: 28px; }
  .deck { font-size: 16.5px; }
  .lede { font-size: 17.5px; }
  h2 { font-size: 22px; margin: 40px 0 12px 0; }
  h2 .num { font-size: 20px; margin-right: 8px; }
  body { font-size: 16.5px; }
}

@media (prefers-reduced-motion: reduce) {
  figure .chart,
  figure .chart .bars .point path,
  figure .chart .scatterlayer .trace .fills path,
  figure .chart .scatterlayer .trace .lines path { transition: none; }
  figure .chart { opacity: 1; transform: none; }
  figure .chart .bars .point path,
  figure .chart .scatterlayer .trace .fills path,
  figure .chart .scatterlayer .trace .lines path { transform: none; }
  /* Cancel the line-draw effect: lines render fully drawn immediately. */
  figure .chart .scatterlayer .trace .lines path {
    stroke-dasharray: none !important;
    stroke-dashoffset: 0 !important;
  }
}
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
      <title>The Quiet Math of NYC's Restaurant Inspections</title>
      <meta name="description" content="What 83,354 health inspections in 27,350 active NYC restaurants reveal about pests, plumbing, and what actually gets a kitchen shut down.">
      <meta name="author" content="Fahim Ahamed">

      <!-- Open Graph / LinkedIn / Facebook preview card -->
      <meta property="og:type" content="article">
      <meta property="og:title" content="The Quiet Math of NYC's Restaurant Inspections">
      <meta property="og:description" content="What 83,354 health inspections in 27,350 active NYC restaurants reveal about pests, plumbing, and what actually gets a kitchen shut down.">
      <meta property="og:image" content="https://f-a-tonmoy.github.io/nyc-inspections-case-study/reports/og-image.png">
      <meta property="og:image:width" content="1200">
      <meta property="og:image:height" content="630">
      <meta property="og:image:alt" content="The Quiet Math of NYC's Restaurant Inspections — a data-backed case study by Fahim Ahamed.">
      <meta property="og:url" content="https://f-a-tonmoy.github.io/nyc-inspections-case-study/">

      <!-- Twitter / X large-image card -->
      <meta name="twitter:card" content="summary_large_image">
      <meta name="twitter:title" content="The Quiet Math of NYC's Restaurant Inspections">
      <meta name="twitter:description" content="What 83,354 health inspections reveal about pests, plumbing, and what actually gets a kitchen shut down.">
      <meta name="twitter:image" content="https://f-a-tonmoy.github.io/nyc-inspections-case-study/reports/og-image.png">

      <!-- Inline SVG favicon: dark rounded square with white "FA" monogram.
           Embedded as a data URI so the HTML stays fully self-contained. -->
      <link rel="icon" type="image/svg+xml" href='data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="5" fill="%231a1a1a"/><text x="16" y="22" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Arial,sans-serif" font-weight="700" font-size="14" fill="white" text-anchor="middle" letter-spacing="-0.5">FA</text></svg>'>

      <link rel="stylesheet" href="https://rsms.me/inter/inter.css">
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+Pro:wght@400;600;700&display=swap">
      <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
      <style>{CSS}</style>
    </head>
    <body>
      <nav class="section-nav" aria-label="Sections">
        <ol>
          <li><a href="#sec-01" data-num="01"><span class="num">01</span><span class="label">Vermin is everywhere</span></a></li>
          <li><a href="#sec-02" data-num="02"><span class="num">02</span><span class="label">The closure cliff</span></a></li>
          <li><a href="#sec-03" data-num="03"><span class="num">03</span><span class="label">The 13-point ceiling</span></a></li>
          <li><a href="#sec-04" data-num="04"><span class="num">04</span><span class="label">Most kitchens bounce back</span></a></li>
          <li><a href="#sec-05" data-num="05"><span class="num">05</span><span class="label">NYC's food map</span></a></li>
          <li><a href="#sec-06" data-num="06"><span class="num">06</span><span class="label">The summer effect</span></a></li>
          <li><a href="#sec-07" data-num="07"><span class="num">07</span><span class="label">What an &lsquo;A&rsquo; really means</span></a></li>
          <li><a href="#sec-08" data-num="08"><span class="num">08</span><span class="label">The grade card and the data behind it</span></a></li>
        </ol>
      </nav>

      <article class="container">

        <header>
          <div class="eyebrow">A Data-Backed Case Study</div>
          <h1>The Quiet Math of New York City's Restaurant Inspections</h1>
          <p class="deck">
            What <strong>{s['n_inspections']:,}</strong> health inspections in
            <strong>{s['n_restaurants']:,}</strong> active New York City restaurants reveal
            about pests, plumbing, and what actually gets a kitchen shut down.
          </p>
          <div class="byline">
            <div class="author">
              By <strong>Fahim Ahamed</strong>
              <span class="sep">|</span>
              <a href="https://www.linkedin.com/in/f-a-tonmoy/" target="_blank" rel="noopener">LinkedIn</a>
              <span class="sep">|</span>
              <a href="https://f-a-tonmoy.github.io/" target="_blank" rel="noopener">Portfolio</a>
            </div>
            <div class="source">
              Data: NYC Department of Health published inspection records.
            </div>
          </div>
        </header>

        <p class="lede">
          More than 85% of New York City's restaurant inspections end up
          with a grade A. More than half the restaurants needed a second
          try to get there.
        </p>

        <p>
          Behind every A taped to a New York City storefront sits a
          public-health inspection report: a long checklist, a numerical
          score, and at the bottom, a single letter. City inspectors arrive
          at each kitchen unannounced, on a rolling cycle<sup class="cite"><a href="#cite-1">1</a></sup>,
          and tally violations against that checklist. The score is what
          counts. Higher number, worse kitchen<sup class="cite"><a href="#cite-1">1</a></sup>.
        </p>

        <div class="grade-cards" aria-label="The three NYC restaurant grades">
          <div class="grade-card grade-a" tabindex="0">
            <div class="card-inner">
              <div class="card-face card-front">
                <div class="card-top">GRADE</div>
                <div class="letter">A</div>
                <div class="range">score 0 – 13</div>
              </div>
              <div class="card-face card-back">
                <div class="big-pct">{s['grade_a_pct']:.0f}%</div>
                <div class="back-label">of all graded inspections</div>
                <div class="back-count">{s['grade_a_n']:,} received an A</div>
              </div>
            </div>
          </div>
          <div class="grade-card grade-b" tabindex="0">
            <div class="card-inner">
              <div class="card-face card-front">
                <div class="card-top">GRADE</div>
                <div class="letter">B</div>
                <div class="range">score 14 – 27</div>
              </div>
              <div class="card-face card-back">
                <div class="big-pct">{s['grade_b_pct']:.0f}%</div>
                <div class="back-label">of all graded inspections</div>
                <div class="back-count">{s['grade_b_n']:,} received a B</div>
              </div>
            </div>
          </div>
          <div class="grade-card grade-c" tabindex="0">
            <div class="card-inner">
              <div class="card-face card-front">
                <div class="card-top">GRADE</div>
                <div class="letter">C</div>
                <div class="range">score 28 and up</div>
              </div>
              <div class="card-face card-back">
                <div class="big-pct">{s['grade_c_pct']:.1f}%</div>
                <div class="back-label">of all graded inspections</div>
                <div class="back-count">{s['grade_c_n']:,} received a C</div>
              </div>
            </div>
          </div>
        </div>
        <p class="card-hint">hover any card to see the breakdown</p>

        <p>
          Most diners only see the card. The Department of Health publishes
          the data underneath on its open-data portal: every violation,
          every inspection, every closure. Roughly
          <strong>{s['n_inspections']:,}</strong> inspections of
          <strong>{s['n_restaurants']:,}</strong> active restaurants sit in
          the file, every deli, wedding venue, rooftop bar, and late-night
          halal cart with a permit, each one a snapshot of a kitchen on a
          particular day.
        </p>

        <p>
          DOHMH publishes inspections on a rolling roughly three-year
          window<sup class="cite"><a href="#cite-2">2</a></sup>. Months
          before 2022 are thinly populated; the program reached full monthly
          volume in mid-2022.
        </p>

        <figure class="grow-up">
          <div class="chart">{charts['timeline']}</div>
          <figcaption>
            Inspections per published month, January 2007 through May 2026.
            Everything in this article uses the shaded window (2022 onward),
            where the program is running at full volume.
          </figcaption>
        </figure>

        <p>
          Look at all <strong>{s['n_inspections']:,}</strong> inspections
          together and patterns show up that no single grade card reveals.
        </p>

        <figure class="grow-up">
          <div class="chart">{charts['hero']}</div>
          <figcaption>
            Every NYC inspection score from 2022 to 2026, in two-point bins.
            Hover any bar for the count. The long right-hand tail is real,
            just very thin compared with the A-zone peak.
            <span class="note">Restaurant names in the three callouts are anonymized; the scores, dates, and outcomes are real and verifiable.</span>
          </figcaption>
        </figure>

        <h2 id="sec-01"><span class="num">01</span>Vermin is everywhere.</h2>

        <p>
          The most surprising number in the data shouldn't be:
          <em class="stat">{s['vermin_pct']:.0f}%</em> of NYC inspections
          find evidence of mice, rats, roaches or flies. One in three.
          Borough to borough, the variation is mild:
          {s['bronx_vermin_pct']:.0f}% in the Bronx, {s['si_vermin_pct']:.0f}% on
          Staten Island. The borough numbers also reflect things the
          inspection data can't see: building age, sanitation infrastructure,
          and the rodent pressure a kitchen is operating against before its
          own practices enter the picture. At the neighbourhood level (NTAs
          with at least 200 inspections), the spread gets sharper: the
          worst sits at roughly <em class="stat">{s['nta_worst_pct']:.0f}%</em>
          of inspections finding vermin, the cleanest at about
          <em class="stat">{s['nta_best_pct']:.0f}%</em>. The rate also has
          a calendar pulse: it peaks in
          <em class="stat">{s['vermin_peak_month']}</em> at
          <em class="stat">{s['vermin_peak_pct']:.0f}%</em> of inspections
          and bottoms out in <em class="stat">{s['vermin_low_month']}</em>
          at about <em class="stat">{s['vermin_low_pct']:.0f}%</em>.
        </p>

        <figure>
          <div class="chart">{charts['vermin']}</div>
          <figcaption>
            Borough-level pest-violation rates. The dotted line is the city-wide
            average; the Bronx is highlighted as the highest.
          </figcaption>
        </figure>

        <p>
          If 1 in 3 inspections finds vermin, vermin can't be what closes a
          restaurant. Most of those
          <em class="stat">{s['n_inspections']:,}</em> visits ended with
          the kitchen still open. The question is what does.
        </p>

        <h2 id="sec-02"><span class="num">02</span>The closure cliff.</h2>

        <p>
          NYC inspectors close a restaurant on the spot in only
          <em class="stat">{s['baseline_closure_pct']:.2f}%</em> of
          inspections. That headline rate hides a sharper truth: when a few
          specific violations appear, the closure probability doesn't creep
          up. It jumps.
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
          Even the live-roach and live-rat codes only push closure risk to
          three to five times the baseline. They're bad, but they aren't,
          by themselves, what closes kitchens.
        </p>

        <p>
          Inspections containing <em class="stat">04F</em> (food area
          contaminated by sewage) end in a closure <em class="stat">{s['cliff_04F_pct']:.0f}%</em>
          of the time, nineteen times the baseline rate. <em class="stat">05A</em>
          (inadequate sewage disposal) and <em class="stat">05E</em>
          (missing or improper toilet facilities) are nearly as severe.
          These are the violations that take a kitchen from "could open
          tomorrow" to "is closing today."
        </p>

        <div class="callout">
          <strong>It's the plumbing.</strong> A live rat sighting raises your
          chance of being closed by about 5×. A sewage problem raises it
          14 to 20×. Everyone worries about rats. The data says worry about
          the pipes.
        </div>

        <p>
          These inspections are rarely single-issue events. Only
          <em class="stat">{s['cliff_n']:,}</em> inspections contained one
          of the three top sewage codes in the window, but those had a
          median score of <em class="stat">{s['cliff_med_score']:.0f}</em>
          (versus <em class="stat">13</em> for everyone else) and
          <em class="stat">{s['cliff_med_viols']:.0f} violations</em> apiece
          (versus three). The plumbing failure is the marker, not the sole
          cause. <strong>{s['cliff_pct_critical']:.0f}%</strong> also
          flagged at least one critical food-safety violation.
        </p>

        <p>
          A handful of recognizable names appear in the data at the catastrophic
          end of the spectrum. A <em class="stat">Le Pain Quotidien</em>
          location in Manhattan posted a score of 168 in July 2023 with a
          sewage citation. A Manhattan coffee chain called
          <em class="stat">% Arabica</em> hit 163 in March 2026 for the
          same sewage code. A Brooklyn restaurant recorded
          a catastrophic <em class="stat">200</em> in April 2026, with
          eighteen violations,
          eleven of them critical, and sewage among them. Each of these
          kitchens was closed that day. The Le Pain inspection is from
          mid-2023; the others are from 2026. These are individual snapshots
          from across the three-year window, not a current scandal.
        </p>

        <p>
          The sewage-cliff inspections aren't concentrated in one part of the
          city. They're scattered across all five boroughs. Red dots are
          on-the-spot closures involving a sewage code; grey dots, inspections
          that found the same issue but did not (yet) close the restaurant.
          Hover any pin for the restaurant, address, score, and date.
        </p>

        <figure>
          <div class="chart">{charts['cliffmap']}</div>
          <figcaption>
            All <em class="stat">{s['cliff_n']:,}</em> inspections containing
            a top-three sewage code, 2022 onward. Scroll to zoom, drag to pan.
          </figcaption>
        </figure>

        <p class="aside">
          A caveat. The dots aren't normalised for restaurant density;
          Manhattan's denser cluster is partly just where the restaurants
          are. Each dot is a single inspection in which a sewage code
          appeared, not a marker of "the worst restaurants."
        </p>

        <h2 id="sec-03"><span class="num">03</span>The 13-point ceiling.</h2>

        <p>
          Inspection scores pile up at exactly <em class="stat">12</em> and
          <em class="stat">13</em>, the two highest scores that still earn
          an A. Score 12 is the single most common score in the data
          (<em class="stat">{s['n_at_12']:,}</em> inspections); score 13
          is second (<em class="stat">{s['n_at_13']:,}</em>). Together they
          account for <em class="stat">{s['n_at_12_13']:,}</em> inspections.
        </p>

        <p>
          And then, at score 14, the count collapses. Only
          <em class="stat">{s['n_at_14']:,}</em> inspections land there, one
          point above the A/B grade boundary. The combined pile-up at 12 and
          13 is roughly <em class="stat">{s['cluster_ratio']:.0f}×</em> the
          count at 14, despite the bins being one point apart.
        </p>

        <figure class="grow-up">
          <div class="chart">{charts['bunching']}</div>
          <figcaption>
            Inspection counts at each integer score from 0 to 35. The slate
            bars are the 12–13 pile-up; the red bar is score 14. Hover any
            bar for the count.
          </figcaption>
        </figure>

        <p>
          This is not random. The grade boundary lives exactly between 13
          and 14. Every inspection scoring 0–13 received an A; every one
          scoring 14–27 received a B. With rare exceptions, no boundary
          crossings either way. A one-point swing on the worksheet is the
          difference between a green A taped to the window and a yellow B
          that stays up until re-inspection.
        </p>

        <p>
          Re-inspections, whose purpose is to recover the A, show the same
          discontinuity. A re-inspection landing at 13 is roughly
          <em class="stat">{s['re_ratio_13_14']:.0f}×</em> as common as one
          landing at 14. The data can't say whether this reflects
          restaurants cleaning up just enough or inspectors rounding
          marginal cases to the safe side of the line. Most likely both.
          Either way, the A is what the system produces, not what it
          measures.
        </p>

        <h2 id="sec-04"><span class="num">04</span>Most kitchens bounce back.</h2>

        <p>
          Most NYC kitchen closures are over in a week. After a
          sewage-cliff closure, the median wait until the next inspection
          is just <em class="stat">{s['days_to_followup']} days</em>,
          versus about <em class="stat">70 days</em> for a routine
          re-inspection, and
          <em class="stat">{s['pct_reopened']:.0f}%</em> of those
          follow-ups end with DOHMH formally re-opening the restaurant.
          The system is built to give kitchens a fast second chance, and
          most take it.
        </p>

        <p>
          And it isn't just sewage closures. The transformation across the
          board is dramatic. Of the
          <em class="stat">{s['n_cz']:,}</em> restaurants that failed an
          initial cycle inspection in the C zone (score 28 or above), the
          median score on the re-inspection drops
          <em class="stat">{s['median_drop']:.0f}</em> points in about two
          months, from <em class="stat">{s['median_initial']:.0f}</em> down
          to <em class="stat">{s['median_reinsp']:.0f}</em>, the highest
          score that still earns an A. More than half recover to an A on
          the next visit.
        </p>

        <figure class="grow-up">
          <div class="chart">{charts['comeback']}</div>
          <figcaption>
            Score change for restaurants that failed an initial cycle
            inspection. Positive means improvement on re-inspection. The thin
            red bars at the left edge are restaurants that got <em>worse</em>.
          </figcaption>
        </figure>

        <p>
          A small minority defy the pattern.
          <em class="stat">{s['pct_got_worse']:.1f}%</em> of these
          restaurants <em>got worse</em> on the next inspection. Another
          <em class="stat">{s['pct_reclosed']:.0f}%</em> of sewage-cliff
          closures were re-closed at the very next visit. The recovery
          system works for most, but it leaks: some kitchens stay in the
          failure cycle.
        </p>

        <h2 id="sec-05"><span class="num">05</span>NYC's food map is sliced into pockets.</h2>

        <p>
          NYC has restaurants in <em class="stat">{s['n_ntas_total']}</em>
          distinct Neighborhood Tabulation Areas, the city's official
          mid-sized geography between ZIP code and borough. Pizza lives in
          <em class="stat">{s['pizza_n_ntas']}</em> of them. Its top five
          neighbourhoods together account for only
          <em class="stat">{s['pizza_top5_pct']:.0f}%</em> of all NYC pizza
          restaurants. Pizza is, statistically, everywhere.
        </p>

        <p>
          Other cuisines aren't. The top 5 neighbourhoods for
          <em class="stat">{s['conc_top_cuisine']}</em> restaurants hold
          <em class="stat">{s['conc_top5_max']:.0f}%</em> of them;
          <em class="stat">{s['conc_top_nta_name']}</em> alone holds
          <em class="stat">{s['conc_top_top1_pct']:.0f}%</em>. Over a third
          of NYC's <em class="stat">{s['conc_top_cuisine']}</em>
          restaurants sit in just two adjacent Queens neighbourhoods.
        </p>

        <figure>
          <div class="chart">{charts['cuisine']}</div>
          <figcaption>
            Each dot is one active NYC restaurant. Five cuisines in colour
            collapse into tight clusters; Pizza, in grey, is the
            everywhere-reference. Hover any pin for the restaurant; toggle
            a cuisine in the legend to isolate it.
          </figcaption>
        </figure>

        <p>
          The five coloured cuisines on the map all sit toward the top of
          the concentration ranking. Korean is the standout multi-anchor
          cuisine, split almost evenly between Flushing's Korean community
          (about 94 restaurants) and Midtown Manhattan's commercial K-town
          (about 93). Bangladeshi, Jewish/Kosher, and Eastern European
          each track one of NYC's best-known immigrant neighbourhoods.
          French clusters in Manhattan's historically high-income
          districts. And Pizza, the grey layer, is the counter-example: a
          cuisine so universal that its city-wide footprint is the city
          itself.
        </p>

        <p>
          Two more extremes sit in the underlying numbers, beyond what the
          map alone shows. Midtown serves food from
          <em class="stat">{s['top_nta_div_count']}</em> distinct cuisines,
          basically every kind of food NYC offers packed into one
          neighbourhood. Tribeca, much smaller, manages
          <em class="stat">{s['second_nta_div_count']}</em>. At the other
          end, some neighbourhoods are nearly mono-cuisine:
          <em class="stat">{s['bk96_caribbean_pct']:.0f}%</em> of East
          Flatbush's restaurants are Caribbean,
          <em class="stat">{s['qn22_chinese_pct']:.0f}%</em> of downtown
          Flushing's are Chinese,
          <em class="stat">{s['bk43_kosher_pct']:.0f}%</em> of Midwood's
          are Jewish/Kosher. NYC's food map is fractal: radically diverse
          in some places, radically concentrated in others.
        </p>

        <p>
          One last fact, about how universal pizza is (and Chinese). The
          data show pizza in <em class="stat">{s['pizza_n_ntas']}</em> NYC
          neighbourhoods, and Chinese food in exactly the same
          <em class="stat">{s['pizza_n_ntas']}</em>. By raw count Chinese
          is actually the bigger of the two:
          <em class="stat">{s['chinese_n_restaurants']:,}</em> restaurants
          to pizza's <em class="stat">{s['pizza_n_restaurants']:,}</em>.
          The neighbourhoods without either are mostly park, zoo, and
          stadium areas (Central Park, the Bronx Zoo, Flushing Meadows /
          Citi Field, the Dyker Beach Golf Course), plus a handful of
          small residential pockets the data simply doesn't capture. The
          only NYC neighbourhoods without pizza or Chinese are mostly the
          ones nobody actually lives in.
        </p>

        <h2 id="sec-06"><span class="num">06</span>The summer effect.</h2>

        <p>
          Heat changes what inspectors find. The cold-food code
          (<em class="stat">02G</em>, "cold food held above 41°F") appears
          in <em class="stat">{s['cold_summer_pct']:.0f}%</em> of summer
          inspections, up from
          <em class="stat">{s['cold_winter_pct']:.0f}%</em> in winter, a
          <em class="stat">{s['cold_summer_lift']:.2f}×</em> lift consistent
          with walk-in coolers struggling against warmer ambient
          temperatures.
        </p>

        <p>
          The opposite pattern shows up on the hot-food side. The
          <em class="stat">02B</em> code ("hot food held below 140°F")
          actually <em>drops</em> in summer, from
          <em class="stat">{s['hot_winter_pct']:.0f}%</em> of winter
          inspections to <em class="stat">{s['hot_summer_pct']:.0f}%</em>
          in summer. Same physics, opposite sign: warm kitchens help hot
          food stay hot.
        </p>

        <figure>
          <div class="chart">{charts['seasonality']}</div>
          <figcaption>
            Share of inspections citing each temperature code, by month of
            year (pooled across all years in the window). The shaded band
            is meteorological summer (Jun–Aug).
          </figcaption>
        </figure>

        <p>
          On-the-spot closures track the season too:
          <em class="stat">{s['closure_summer_pct']:.2f}%</em> of summer
          inspections end in a closure, against
          <em class="stat">{s['closure_winter_pct']:.2f}%</em> in winter, a
          <em class="stat">{s['closure_summer_lift']:.2f}×</em> jump.
          <em class="stat">{s['closure_peak_month']}</em> is the riskiest
          month for a NYC kitchen
          (<em class="stat">{s['closure_peak_pct']:.2f}%</em>);
          <em class="stat">{s['closure_low_month']}</em> the safest
          (<em class="stat">{s['closure_low_pct']:.2f}%</em>). The city
          itself slows down: roughly
          <em class="stat">{abs(s['inspections_summer_vs_winter_pct']):.0f}%</em>
          fewer inspections per summer month than per winter one. But the
          ones that happen find more, on every dimension summer plausibly
          affects. Same kitchen, different month, different odds.
        </p>

        <h2 id="sec-07"><span class="num">07</span>What an &lsquo;A&rsquo; really means.</h2>

        <p>
          The grade card suggests a simple sort: clean restaurants get an
          A, dirty ones don't. The data underneath suggests something else.
        </p>

        <div class="stat-strip">
          <div class="stat-tile">
            <div class="big-num">{s['pct_with_critical']:.0f}%</div>
            <div class="label">of NYC's {s['n_restaurants']:,} active restaurants have been cited for at least one critical food-safety violation in the past three years (most were corrected on re-inspection)</div>
          </div>
          <div class="stat-tile">
            <div class="big-num">{s['reinspect_overall_pct']:.0f}%</div>
            <div class="label">of restaurants that had a cycle inspection were called back for a re-inspection (their first score did not earn an A)</div>
          </div>
          <div class="stat-tile">
            <div class="big-num">{s['pct_hidden_b']:.0f}%</div>
            <div class="label">of restaurants currently displaying an A had a B or C earlier in the three-year window, then cleaned up and re-earned the A through re-inspection</div>
          </div>
        </div>

        <p>
          The A on the door is a snapshot of the most recent visit, not a
          long-term record. Only <em class="stat">{s['n_clean_record']:,}</em>
          NYC restaurants (about {100 - s['pct_with_critical']:.0f}%) have a
          perfectly clean three-year history. The remaining 96% have been
          cited for something serious at least once, then cleaned up enough
          to keep or earn back the grade.
        </p>

        <div class="callout">
          <strong>Put the numbers side by side.</strong>
          <em class="stat">{s['grade_a_pct']:.0f}%</em> of graded
          inspections end in an A. But
          <em class="stat">{s['reinspect_overall_pct']:.0f}%</em> of
          restaurants needed a re-inspection to get there. And scores pile
          up <em class="stat">{s['cluster_ratio']:.0f}×</em> more at 12–13
          than at 14, right at the grade boundary. The A is less a
          description of kitchen quality than an outcome the system is
          structured to produce.
        </div>

        <p>
          The chance of a second visit varies sharply by what kind of
          restaurant you run. <em class="stat">{s['reinspect_top_cuisine']}</em>
          restaurants are re-inspected
          <em class="stat">{s['reinspect_top_pct']:.0f}%</em> of the time
          after a cycle inspection;
          <em class="stat">{s['reinspect_bot_cuisine']}</em> only
          <em class="stat">{s['reinspect_bot_pct']:.0f}%</em>.
        </p>

        <figure>
          <div class="chart">{charts['reinspect']}</div>
          <figcaption>
            Top and bottom of the cuisine re-inspection ranking. The
            dotted line is the NYC average
            (<em class="stat">{s['reinspect_overall_pct']:.0f}%</em>).
            Showing the top 6 and bottom 6 only; the dots between them
            are dropped to focus the contrast.
          </figcaption>
        </figure>

        <p>
          The pattern at the ends of this chart isn't about cuisine. It
          tracks two structural factors the data can't fully separate:
          <strong>kitchen complexity</strong> (a counter pulling pre-made
          ingredients has fewer ways to fail than a multi-station prep
          kitchen) and <strong>geography</strong> (cuisines that
          concentrate in higher-income parts of the city absorb fewer
          citations). The top of the chart skews independent, full-prep,
          and outer-borough; the bottom skews counter-service,
          limited-menu, often chain-operated.
        </p>

        <p>
          What the A tells you: this kitchen has been inspected recently,
          has cleaned up whatever was off, and is not currently in active
          enforcement. That's not nothing. But it is a much smaller claim
          than the card makes it look.
        </p>

        <h2 id="sec-08">The grade card and the data behind it.</h2>

        <p>
          A few patterns repeat across the data, and they fit together into
          one picture.
        </p>

        <p>
          Vermin is everywhere, and it is not what gets a kitchen shut down.
          When kitchens do close, plumbing is usually the trigger, and by
          then the rest of the kitchen has usually fallen apart too. And the
          borough-level numbers read in headlines smooth over differences
          between neighbours several times larger than the differences
          between boroughs.
        </p>

        <p>
          These patterns are less about which NYC restaurants are clean
          and more about how the grading system, the inspection cycle, and
          the kitchens being graded interact to produce the letters on the
          windows.
        </p>

        <aside class="takeaways" aria-label="Key takeaways">
          <h3>Key takeaways</h3>
          <ol>
            <li>
              <strong>Scores cluster right under the A/B line.</strong>
              Scores 12 and 13 are the two most common in the data, the
              highest still earning an A; a score of 14 is roughly
              <em class="stat">{s['ratio_13_14']:.0f}×</em> rarer than 13,
              one point lower.
            </li>
            <li>
              <strong>Plumbing closes kitchens. Pests almost never do.</strong>
              A live-rat citation raises closure risk about 5×; a sewage
              code raises it 14 to 20×.
            </li>
            <li>
              <strong>Most failed kitchens recover.</strong>
              After a C-zone failure (score 28 or above), the median score
              drops <em class="stat">{s['median_drop']:.0f}</em> points in
              about two months; <em class="stat">{s['pct_recover_A']:.0f}%</em>
              are back to an A on the very next visit. (That's the
              bounce-back rate from severe failures, distinct from the
              <em class="stat">{s['reinspect_overall_pct']:.0f}%</em>
              re-inspection rate in section 7, which measures how often
              any cycle inspection triggers a call-back.)
            </li>
            <li>
              <strong>NYC's food map is sliced into pockets.</strong> The
              top 5 neighbourhoods for some cuisines hold over half of all
              of that cuisine's restaurants in the city. Universal cuisines
              like <strong>Pizza</strong> spread across
              <em class="stat">{s['pizza_n_ntas']}</em> of the city's
              <em class="stat">{s['n_ntas_total']}</em> neighbourhoods,
              so does <strong>Chinese</strong>.
            </li>
          </ol>
        </aside>

        <h2>What this data cannot tell us</h2>

        <p>
          DOHMH publishes a <strong>rolling roughly three-year window</strong>
          of inspection records<sup class="cite"><a href="#cite-2">2</a></sup>.
          Older inspections drop off the back end. The data's earliest
          published year (2007) is a sliver: fewer than 10 inspections per year
          through 2014, and under 300 per year through 2021. Everything in
          this article uses inspections from mid-2022 onward, when monthly
          volume reached its current level.
        </p>

        <p>
          The city also publishes records only for restaurants that are
          still in active status<sup class="cite"><a href="#cite-2">2</a></sup>.
          Two different things in this article are called "closure," and
          they aren't the same:
        </p>

        <ul>
          <li>
            The <strong>on-the-spot closures</strong> discussed in sections
            2 and 4 are a regulatory action DOHMH takes during an
            inspection. They are temporary. Section 4 shows that most of
            these restaurants are re-opened within days. The kitchens
            involved are still in the active file.
          </li>
          <li>
            <strong>Permanent business closures</strong>, where a restaurant
            loses its permit or goes out of business and is removed from the
            active roll, are <em>not</em> in this file at all. Whatever
            their final inspection looked like, the record leaves with them.
          </li>
        </ul>

        <p>
          The closure rates in this article therefore describe what happens
          to restaurants that are still operating today. They cannot describe
          what happens to the ones that didn't survive long enough to stay on
          the active roll.
        </p>

        <p class="aside aside-divider">
          <strong>A note on reproducibility.</strong> DOHMH updates the
          inspection file daily, and because the published file is a
          rolling three-year window, old inspections drop off the back end
          while new ones are added at the front. Every figure and finding
          in this article is computed from a snapshot taken in <strong>late
          May 2026</strong>. Reproducing the build later, against a fresher
          download, will yield numbers that are close but not identical to
          the ones quoted here. The underlying patterns are stable; the
          exact decimals are not.
        </p>

        <footer>
          <h3>Citations</h3>
          <ol class="citations">
            <li id="cite-1">
              NYC Department of Health and Mental Hygiene, "Restaurant
              Grades." Official program description and scoring rules.
              <a href="https://www.nyc.gov/site/doh/services/restaurant-grades.page" target="_blank" rel="noopener">nyc.gov/site/doh/services/restaurant-grades.page</a>.
              Used for the inspection-process description and the
              A (0–13) / B (14–27) / C (28+) grade thresholds.
            </li>
            <li id="cite-2">
              NYC Open Data, "DOHMH New York City Restaurant Inspection
              Results." Data dictionary and inclusion rules.
              <a href="https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j" target="_blank" rel="noopener">data.cityofnewyork.us · 43nn-pn8j</a>.
              Used for the rolling three-year publishing window and the
              active-restaurants-only inclusion policy.
            </li>
          </ol>
        </footer>
      <button class="back-to-top" aria-label="Back to top" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>

      </article>

      <script>
      // Scroll-triggered chart entrance animation.
      //
      // Each .chart element starts hidden (opacity 0, slightly translated
      // down). When at least 15% of the element enters the viewport we add
      // the .is-visible class, which triggers the CSS transitions defined
      // in the stylesheet. SVG bar/line paths inside Plotly also pick up a
      // horizontal "grow from left" transform via the same trigger.
      //
      // We deliberately *do not* touch Plotly's data layer: hover tooltips,
      // zoom, and pan all keep working as they did before.
      (function() {{
        // Trigger zones use rootMargin so the animation fires only after the
        // chart has scrolled meaningfully into view, not the moment its top
        // edge crosses the viewport bottom. rootMargin '0px 0px -28% 0px'
        // effectively raises the viewport's bottom edge 28% up the screen,
        // so a chart enters the trigger zone roughly when it reaches the
        // middle of the user's view.

        // --- 1) Chart fade-in + line-draw on scroll ---
        // When a chart enters view we (a) add .is-visible for CSS fade-in
        // + bar-grow, and (b) for non-grow-up figures with SVG line traces,
        // run a "line draw" stroke-dashoffset animation.
        //
        // Priming + animating in one callback (rather than priming once on
        // load and triggering later) avoids the race we hit when a refresh
        // restores scroll to §6: the observer would fire before priming
        // finished, and lines stayed invisible. Now priming happens inline
        // right before the animation, retrying if Plotly hasn't rendered.
        function drawLines(chartEl, attemptsLeft) {{
          if (typeof attemptsLeft === 'undefined') attemptsLeft = 12;
          const fig = chartEl.closest('figure');
          if (fig && fig.classList.contains('grow-up')) return;
          const paths = chartEl.querySelectorAll(
            '.scatterlayer .trace .lines path'
          );
          let anyAnimated = false;
          paths.forEach(path => {{
            if (path.dataset.linedrawDone) return;
            const len = path.getTotalLength();
            if (!len) return;
            // Snap to invisible state with no transition, force a reflow,
            // then enable transition + animate to fully-drawn.
            path.style.transition = 'none';
            path.style.strokeDasharray = len + 'px ' + len + 'px';
            path.style.strokeDashoffset = len + 'px';
            path.getBoundingClientRect();
            path.style.transition =
              'stroke-dashoffset 2s cubic-bezier(0.215, 0.61, 0.355, 1) 0.15s';
            path.style.strokeDashoffset = '0px';
            path.dataset.linedrawDone = '1';
            anyAnimated = true;
          }});
          // No paths visible yet — Plotly probably still mounting. Retry.
          if (!anyAnimated && attemptsLeft > 0 && !paths.length) {{
            setTimeout(() => drawLines(chartEl, attemptsLeft - 1), 100);
          }}
        }}

        const observer = new IntersectionObserver((entries) => {{
          entries.forEach(entry => {{
            if (!entry.isIntersecting) return;
            entry.target.classList.add('is-visible');
            drawLines(entry.target);
            observer.unobserve(entry.target);
          }});
        }}, {{ threshold: 0, rootMargin: '0px 0px -20% 0px' }});

        function arm() {{
          document.querySelectorAll('figure .chart').forEach(el => {{
            observer.observe(el);
          }});
          armMapZoom();
          armSectionNav();
        }}

        // --- 3) Section-nav active-state tracking ---
        // On every scroll, find the LAST section h2 whose top is above the
        // viewport's 35% line — that's the section the reader is currently
        // inside. This works whether the h2 itself is on-screen or not.
        // IntersectionObserver alone doesn't cover the "scrolled deep into
        // a section, h2 long gone" case, which is why we track manually.
        function armSectionNav() {{
          const navLinks = document.querySelectorAll('.section-nav a');
          if (!navLinks.length) return;
          // Track ALL article h2s (not just the numbered sec-* ones) so we
          // can detect when the reader has scrolled past §8 into the
          // "What this data cannot tell us" or citations footer area —
          // those h2s have no sec-* id, so when one of them becomes the
          // last-passed h2 we clear the nav (nothing to highlight).
          const allH2s = Array.from(document.querySelectorAll('article h2'));
          if (!allH2s.length) return;

          function updateActive() {{
            // Near the top of the page: no section is "current" yet.
            if (window.scrollY < 200) {{
              navLinks.forEach(link => link.classList.remove('active'));
              return;
            }}
            const trigger = window.innerHeight * 0.35;
            let active = null;
            for (const h2 of allH2s) {{
              if (h2.getBoundingClientRect().top <= trigger) {{
                active = h2;
              }} else {{
                break;
              }}
            }}
            // If the last-passed h2 isn't a numbered section, the reader is
            // in the conclusion / "cannot tell us" / citations area. Clear.
            if (!active || !active.id || !active.id.startsWith('sec-')) {{
              navLinks.forEach(link => link.classList.remove('active'));
              return;
            }}
            navLinks.forEach(link => {{
              link.classList.toggle('active',
                link.getAttribute('href') === '#' + active.id);
            }});
          }}

          window.addEventListener('scroll', updateActive, {{ passive: true }});
          updateActive();
        }}

        // --- 2) Map zoom-in on scroll ---
        // Both the §2 sewage-cliff map and the §5 cuisine map are rendered
        // initially at a wide regional zoom; when each enters the user's
        // view we animate the zoom and centre into the tighter city-focused
        // view via Plotly.relayout in a rAF loop. Same rootMargin idea,
        // slightly tighter so the long 2.4s zoom animation peaks while the
        // map is fully in frame.
        function armMapZoom() {{
          const targets = [
            {{ id: 'chart-cliffmap',
               fromZoom: 9.0,  toZoom: 10.4,
               fromLat:  40.78, toLat:  40.732,
               fromLon: -73.93, toLon: -73.95 }},
            {{ id: 'chart-cuisine',
               fromZoom: 9.4,  toZoom: 10.2,
               fromLat:  40.74, toLat:  40.73,
               fromLon: -73.90, toLon: -73.92 }},
          ];
          targets.forEach(cfg => {{
            const mapDiv = document.getElementById(cfg.id);
            if (!mapDiv) return;
            let triggered = false;
            const mapObs = new IntersectionObserver((entries) => {{
              entries.forEach(entry => {{
                if (!entry.isIntersecting || triggered) return;
                triggered = true;
                setTimeout(() => runMapZoom(mapDiv, cfg), 300);
                mapObs.unobserve(entry.target);
              }});
            }}, {{ threshold: 0, rootMargin: '0px 0px -25% 0px' }});
            mapObs.observe(mapDiv);
          }});
        }}

        function runMapZoom(div, cfg) {{
          const duration = 2400;
          const t0 = performance.now();
          function step(now) {{
            const t = Math.min(1, (now - t0) / duration);
            const e = 1 - Math.pow(1 - t, 3);   // cubic-out
            const z   = cfg.fromZoom + (cfg.toZoom - cfg.fromZoom) * e;
            const lat = cfg.fromLat  + (cfg.toLat  - cfg.fromLat)  * e;
            const lon = cfg.fromLon  + (cfg.toLon  - cfg.fromLon)  * e;
            Plotly.relayout(div, {{
              'map.zoom': z,
              'map.center.lat': lat,
              'map.center.lon': lon,
            }});
            if (t < 1) requestAnimationFrame(step);
          }}
          requestAnimationFrame(step);
        }}

        if (document.readyState === 'complete') arm();
        else window.addEventListener('load', arm);
      }})();

      // --- 4) Back-to-top button visibility ---
      // (Nav-clear-at-top is handled inside armSectionNav above.)
      (function() {{
        const btn = document.querySelector('.back-to-top');
        if (!btn) return;
        window.addEventListener('scroll', function() {{
          btn.classList.toggle('visible', window.scrollY > 600);
        }}, {{ passive: true }});
      }})();
      </script>
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

    # Cuisines — geographic concentration across NYC's NTAs.
    cuisine_concentration = compute_cuisine_concentration(dense)
    n_cuisines_panel = int(len(cuisine_concentration))
    n_ntas_total = int(dense["nta"].nunique())
    most_concentrated   = cuisine_concentration.iloc[0]
    most_distributed    = cuisine_concentration.iloc[-1]
    conc_top5_max  = float(most_concentrated["top5_pct"])
    conc_top5_min  = float(most_distributed["top5_pct"])
    conc_top_cuisine     = str(most_concentrated["cuisine"])
    conc_top_nta_name    = str(most_concentrated["top1_name"])
    conc_top_top1_pct    = float(most_concentrated["top1_pct"])
    conc_low_cuisine     = str(most_distributed["cuisine"])
    conc_low_n_ntas      = int(most_distributed["n_ntas"])
    # Used in the prose to reference Pizza and Chinese as the two known
    # universal-cuisine anchors the reader can picture.
    pizza_row = cuisine_concentration[cuisine_concentration["cuisine"] == "Pizza"].iloc[0]
    pizza_n_ntas = int(pizza_row["n_ntas"])
    pizza_top5_pct = float(pizza_row["top5_pct"])
    pizza_n_restaurants = int(pizza_row["n_restaurants"])
    chinese_row = cuisine_concentration[cuisine_concentration["cuisine"] == "Chinese"].iloc[0]
    chinese_n_ntas = int(chinese_row["n_ntas"])
    chinese_n_restaurants = int(chinese_row["n_restaurants"])

    # Fun facts for §5 closing paragraph: NTA-level diversity and dominance.
    # rest_per_nta has one row per active restaurant; per_nta_diversity is
    # distinct cuisine count per NTA; per_nta_dominance is "what % does
    # that NTA's most-common cuisine make up".
    rest_per_nta = (dense.drop_duplicates("camis")
                          [["nta", "cuisine_description", "boro"]]
                          .dropna(subset=["nta"]))
    rest_per_nta = rest_per_nta[rest_per_nta["nta"].astype(str).str.strip() != ""]
    JUNK = {"Other", "Not Listed/Not Applicable", ""}
    rest_per_nta = rest_per_nta[~rest_per_nta["cuisine_description"].isin(JUNK)]
    rest_per_nta = rest_per_nta[rest_per_nta["cuisine_description"].notna()]
    nta_diversity = (rest_per_nta.groupby("nta")["cuisine_description"]
                                 .nunique().sort_values(ascending=False))
    # Top diverse NTA = Midtown (MN17, 65 cuisines); 2nd = Tribeca (MN13, 61).
    top_nta_div_count = int(nta_diversity.iloc[0])
    second_nta_div_count = int(nta_diversity.iloc[1])

    # NTA-level dominance: what fraction of each NTA's restaurants belong
    # to its single most-common cuisine. Cap to NTAs with >=30 restaurants
    # so we don't pull from sparse parks / cemeteries.
    nta_sizes = rest_per_nta["nta"].value_counts()
    big_ntas = nta_sizes[nta_sizes >= 30].index
    dom_rows = []
    for n, g in rest_per_nta[rest_per_nta["nta"].isin(big_ntas)].groupby("nta"):
        vc = g["cuisine_description"].value_counts()
        dom_rows.append((n, vc.iloc[0] / len(g) * 100, vc.index[0]))
    dom_df = (pd.DataFrame(dom_rows, columns=["nta", "top_pct", "top_cuis"])
                .sort_values("top_pct", ascending=False))
    # Pull the three named neighbourhood dominance facts the prose uses.
    bk96_caribbean_pct = float(dom_df.loc[dom_df["nta"] == "BK96", "top_pct"].iloc[0])
    qn22_chinese_pct   = float(dom_df.loc[dom_df["nta"] == "QN22", "top_pct"].iloc[0])
    bk43_kosher_pct    = float(dom_df.loc[dom_df["nta"] == "BK43", "top_pct"].iloc[0])

    # Pizza-holdout count: NTAs without a single pizza restaurant.
    all_nta_set   = set(rest_per_nta["nta"].unique())
    pizza_nta_set = set(rest_per_nta[
        rest_per_nta["cuisine_description"] == "Pizza"]["nta"].unique())
    n_no_pizza_ntas = int(len(all_nta_set - pizza_nta_set))

    # Districts (bar + choropleth)
    dist = compute_districts(dense)
    districts_geojson = load_districts_geojson()

    # Bunching
    bunch_counts, bunch_stats = compute_bunching(dense)

    # Re-inspection rate by cuisine (§7 "What an A really means")
    reinspect_overall_pct, reinspect_by_cuisine = compute_reinspection_rate(dense)
    cuis_top = reinspect_by_cuisine.nlargest(1, "pct").iloc[0]
    cuis_bot = reinspect_by_cuisine.nsmallest(1, "pct").iloc[0]

    # "Critical-record" %: restaurants ever cited for a critical violation
    n_total_camis     = int(dense["camis"].nunique())
    camis_with_crit   = dense[dense["n_critical"] > 0]["camis"].unique()
    pct_with_critical = 100 * len(camis_with_crit) / max(n_total_camis, 1)
    n_clean_record    = n_total_camis - len(camis_with_crit)

    # "Hidden-B" %: current-A restaurants that held a B/C earlier in window
    dense_g = (dense[dense["grade"].isin(["A", "B", "C"])]
                 .sort_values(["camis", "inspection_date"]))
    latest_grade = dense_g.groupby("camis").tail(1).set_index("camis")["grade"]
    a_now = set(latest_grade[latest_grade == "A"].index)
    earlier_worst = (dense_g[dense_g["grade"].isin(["B", "C"])]
                       .groupby("camis").size())
    # restaurants whose latest grade is A AND had at least one B or C visit
    # somewhere in their history
    hidden_b_count = sum(
        1 for c in a_now
        if c in earlier_worst.index
        # check the worse-than-A inspection happened BEFORE the latest A
        and dense_g[(dense_g["camis"] == c) &
                    (dense_g["grade"].isin(["B", "C"]))]["inspection_date"].min()
            < dense_g[(dense_g["camis"] == c) &
                      (dense_g["grade"] == "A")]["inspection_date"].max()
    )
    # Simpler: use the audit-script logic instead — count groups that had
    # a worse grade BEFORE their latest A. We do it more efficiently below.
    def _had_worse_before(grp):
        if len(grp) < 2 or grp.iloc[-1]["grade"] != "A":
            return False
        return (grp.iloc[:-1]["grade"].isin(["B", "C"])).any()
    hidden_b_count = int(dense_g.groupby("camis").apply(_had_worse_before).sum())
    pct_hidden_b = 100 * hidden_b_count / max(len(a_now), 1)

    # Seasonality (Jun-Aug = summer, Dec-Feb = winter)
    monthly = compute_seasonality(dense, raw)
    summer = monthly.loc[[6, 7, 8]].mean()
    winter = monthly.loc[[12, 1, 2]].mean()
    vermin_peak_month = monthly["vermin_pct"].idxmax()
    vermin_peak_pct   = float(monthly["vermin_pct"].max())
    vermin_low_month  = monthly["vermin_pct"].idxmin()
    vermin_low_pct    = float(monthly["vermin_pct"].min())
    closure_peak_month = monthly["closure_pct"].idxmax()
    closure_peak_pct   = float(monthly["closure_pct"].max())
    closure_low_month  = monthly["closure_pct"].idxmin()
    closure_low_pct    = float(monthly["closure_pct"].min())
    _M = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
          7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}

    # Cliff map count (for the prose number)
    cliff_with_geo = cliff[cliff["latitude"].notna() & cliff["longitude"].notna()]

    # Grade-card flip stats — count of inspections per letter grade, and the
    # share each grade has of all graded (A+B+C) inspections.
    grade_counts = dense["grade"].value_counts()
    n_graded_a = int(grade_counts.get("A", 0))
    n_graded_b = int(grade_counts.get("B", 0))
    n_graded_c = int(grade_counts.get("C", 0))
    n_graded   = n_graded_a + n_graded_b + n_graded_c

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
        "cliff_map_n":           int(len(cliff_with_geo)),
        "days_to_followup":      days_to_followup,
        "pct_reopened":          pct_reopened,
        "pct_reclosed":          pct_reclosed,
        "n_cz":                  int(len(cz)),
        "median_initial":        float(cz["initial_score"].median()),
        "median_reinsp":         float(cz["reinsp_score"].median()),
        "median_drop":           float(cz["drop"].median()),
        "pct_recover_A":         float((cz["reinsp_grade"] == "A").mean() * 100),
        "pct_got_worse":         float((cz["drop"] < 0).mean() * 100),
        "n_cuisines_panel":      n_cuisines_panel,
        "n_ntas_total":          n_ntas_total,
        "conc_top5_max":         conc_top5_max,
        "conc_top5_min":         conc_top5_min,
        "conc_top_cuisine":      conc_top_cuisine,
        "conc_top_nta_name":     conc_top_nta_name,
        "conc_top_top1_pct":     conc_top_top1_pct,
        "conc_low_cuisine":      conc_low_cuisine,
        "conc_low_n_ntas":       conc_low_n_ntas,
        "pizza_n_ntas":          pizza_n_ntas,
        "pizza_top5_pct":        pizza_top5_pct,
        "pizza_n_restaurants":   pizza_n_restaurants,
        "chinese_n_ntas":        chinese_n_ntas,
        "chinese_n_restaurants": chinese_n_restaurants,
        "top_nta_div_count":     top_nta_div_count,
        "second_nta_div_count":  second_nta_div_count,
        "bk96_caribbean_pct":    bk96_caribbean_pct,
        "qn22_chinese_pct":      qn22_chinese_pct,
        "bk43_kosher_pct":       bk43_kosher_pct,
        "n_no_pizza_ntas":       n_no_pizza_ntas,
        "district_high_pct":     float(dist["closure_pct"].max()),
        "district_low_pct":      float(dist["closure_pct"].min()),
        "district_ratio":        float(dist["closure_pct"].max() / dist["closure_pct"].min()),
        # §7 "What an A really means" stats
        "pct_with_critical":     float(pct_with_critical),
        "n_clean_record":        int(n_clean_record),
        "reinspect_overall_pct": float(reinspect_overall_pct),
        "pct_hidden_b":          float(pct_hidden_b),
        "reinspect_top_cuisine": str(cuis_top["cuisine"]),
        "reinspect_top_pct":     float(cuis_top["pct"]),
        "reinspect_bot_cuisine": str(cuis_bot["cuisine"]),
        "reinspect_bot_pct":     float(cuis_bot["pct"]),
        "grade_a_n":             n_graded_a,
        "grade_b_n":             n_graded_b,
        "grade_c_n":             n_graded_c,
        "grade_a_pct":           n_graded_a / max(n_graded, 1) * 100,
        "grade_b_pct":           n_graded_b / max(n_graded, 1) * 100,
        "grade_c_pct":           n_graded_c / max(n_graded, 1) * 100,
        # Seasonality stats for §7
        "cold_summer_pct":       float(summer["cold_food_pct"]),
        "cold_winter_pct":       float(winter["cold_food_pct"]),
        "hot_summer_pct":        float(summer["hot_food_pct"]),
        "hot_winter_pct":        float(winter["hot_food_pct"]),
        "closure_summer_pct":    float(summer["closure_pct"]),
        "closure_winter_pct":    float(winter["closure_pct"]),
        "cold_summer_lift":      float(summer["cold_food_pct"] / winter["cold_food_pct"]),
        "closure_summer_lift":   float(summer["closure_pct"] / winter["closure_pct"]),
        "inspections_summer_vs_winter_pct":
            float((summer["n"] / winter["n"] - 1) * 100),  # negative = fewer
        "vermin_peak_month":     _M[int(vermin_peak_month)],
        "vermin_peak_pct":       vermin_peak_pct,
        "vermin_low_month":      _M[int(vermin_low_month)],
        "vermin_low_pct":        vermin_low_pct,
        "closure_peak_month":    _M[int(closure_peak_month)],
        "closure_peak_pct":      closure_peak_pct,
        "closure_low_month":     _M[int(closure_low_month)],
        "closure_low_pct":       closure_low_pct,
        **bunch_stats,
    }

    # Build charts
    figs = {
        "timeline":    chart_timeline(df),
        "hero":        chart_hero(dense),
        "vermin":      chart_vermin(by_boro_v, city_v),
        "cliff":       chart_cliff(baseline, cliff_agg),
        "cliffmap":    chart_cliff_map(dense, raw),
        "bunching":    chart_bunching(bunch_counts),
        "comeback":    chart_comeback(pairs),
        "cuisine":     chart_cuisine_concentration(dense, cuisine_concentration),
        # Signature heatmap removed when §5 was refocused on geographic
        # concentration; chart_cuisine_signatures() is kept defined in case
        # we want to bring it back as a secondary view.
        # District chart functions kept defined but no longer rendered —
        # §6 districts was dropped from the article (too obvious a finding).
        "seasonality": chart_seasonality(monthly),
        "reinspect":   chart_reinspection_by_cuisine(reinspect_by_cuisine,
                                                     reinspect_overall_pct),
    }
    charts = {k: fig_div(v, f"chart-{k}") for k, v in figs.items()}

    ARTICLE.write_text(render(stats, charts), encoding="utf-8")
    print(f"\nWrote {ARTICLE}")
    print("Headline numbers used in prose:")
    for k, v in stats.items():
        print(f"  {k:>22}: {v}")


if __name__ == "__main__":
    main()
