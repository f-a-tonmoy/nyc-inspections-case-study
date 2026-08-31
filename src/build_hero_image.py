"""
Editorial hero / cover image for the NYC restaurant-inspection case study.

Left column carries the hook and the headline stats; the right side carries
the article's signature finding: the "closure cliff". Pest violations barely
move the odds of an on-the-spot closure. Plumbing failures multiply them.

    python src/build_hero_image.py

Output: reports/hero-image.png  (2400x1350, 16:9)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

REPORTS = Path(__file__).resolve().parent.parent / "reports"
OUT = REPORTS / "hero-image.png"

# Palette lifted from the article's CSS custom properties.
BG      = "#faf8f3"
INK     = "#1a1a1a"
DIM     = "#555555"
ACCENT  = "#c0392b"   # --accent, plumbing bars
ORANGE  = "#e67e22"   # pest bars
SLATE   = "#7f8c8d"

W_IN, H_IN, DPI = 12.0, 6.75, 200
PAD_L = 0.062


def pick(*families):
    """First font family actually installed, else matplotlib's default."""
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in families:
        if name in have:
            return name
    return "DejaVu Sans"


SERIF = pick("Source Serif Pro", "Source Serif 4", "Georgia", "Charter", "DejaVu Serif")
SANS = pick("Inter", "Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans")

# The closure cliff. Three most common pest findings, three plumbing failures.
# Values are closure rates when that code appears on the inspection.
# Sub-label is the multiple of the city-wide baseline, printed under the value.
BARS = [
    ("Evidence of mice",     5.3,  ORANGE, "3× baseline"),
    ("Live rats",            8.0,  ORANGE, "5× baseline"),
    ("Live roaches",         8.7,  ORANGE, "5× baseline"),
    ("No toilet facility",   24.3, ACCENT, "14× baseline"),
    ("Sewage disposal",      31.1, ACCENT, "18× baseline"),
    ("Sewage in food area",  34.3, ACCENT, "19× baseline"),
]
BASELINE = 1.74


def draw_left_column(fig):
    fig.text(PAD_L, 0.923, "NYC RESTAURANT INSPECTIONS  ·  83,354 RECORDS",
             fontfamily=SANS, fontsize=10.5, fontweight="bold",
             color=DIM, va="center")

    fig.text(PAD_L, 0.742, "What actually\nshuts a kitchen\ndown?",
             fontfamily=SERIF, fontsize=35, fontweight="bold",
             color=INK, va="center", linespacing=1.18)

    fig.text(PAD_L, 0.488,
             "Inspectors close a restaurant on the spot in\n"
             "fewer than 2% of visits. But when certain\n"
             "violations appear, the odds don't creep up.\n"
             "They jump.",
             fontfamily=SANS, fontsize=12.2, color=DIM,
             va="center", linespacing=1.6)

    # Legend: two categories, matching the bar colours.
    for i, (colour, label) in enumerate([
        (ACCENT, "Plumbing and sewage failures"),
        (ORANGE, "Pest violations"),
    ]):
        y = 0.338 - i * 0.062
        fig.patches.append(plt.Rectangle(
            (PAD_L, y - 0.018), 0.020, 0.036,
            transform=fig.transFigure, facecolor=colour, edgecolor="none"))
        fig.text(PAD_L + 0.033, y, label, fontfamily=SANS, fontsize=11.5,
                 color=INK, va="center")

    # Headline stat pair: the counterintuitive comparison.
    for x, value, colour, caption in [
        (PAD_L, "34%", ACCENT, "Of inspections close when\nsewage reaches the food area"),
        (PAD_L + 0.19, "8%", SLATE, "Of inspections close when\ninspectors find live rats"),
    ]:
        fig.text(x, 0.178, value, fontfamily=SERIF, fontsize=30,
                 fontweight="bold", color=colour, va="center")
        fig.text(x, 0.088, caption, fontfamily=SANS, fontsize=9.5,
                 color=DIM, va="center", linespacing=1.5)


def draw_chart(fig):
    ax = fig.add_axes([0.575, 0.185, 0.372, 0.585])
    ax.set_facecolor(BG)

    labels = [b[0] for b in BARS]
    values = [b[1] for b in BARS]
    colours = [b[2] for b in BARS]
    ys = range(len(BARS))

    ax.barh(ys, values, color=colours, height=0.56, zorder=3)

    # Value label, with the baseline multiple tucked underneath it.
    for y, v, colour, multiple in zip(ys, values, colours, [b[3] for b in BARS]):
        ax.text(v + 1.1, y + 0.11, f"{v:.1f}%", va="center", ha="left",
                fontfamily=SANS, fontsize=11.5, fontweight="bold",
                color=INK, zorder=4)
        ax.text(v + 1.1, y - 0.26, multiple, va="center", ha="left",
                fontfamily=SANS, fontsize=8.5, color=colour, zorder=4)

    # City-wide baseline.
    ax.axvline(BASELINE, color=INK, linestyle=(0, (2, 2)),
               linewidth=1, zorder=2)
    ax.text(BASELINE + 0.8, len(BARS) - 0.34, "all inspections: 1.7%",
            fontfamily=SANS, fontsize=9, color=DIM, va="bottom", zorder=4)

    # The cliff: the gap between the pest cluster and the plumbing cluster.
    ax.axhline(2.5, color=SLATE, linestyle=(0, (3, 3)),
               linewidth=1, alpha=0.55, zorder=2)
    ax.text(0.6, 2.5, "THE CLIFF", fontfamily=SANS, fontsize=9.5,
            fontweight="bold", color=SLATE, va="center", ha="left", zorder=4,
            bbox=dict(facecolor=BG, edgecolor="none", pad=3))

    ax.set_yticks(list(ys))
    ax.set_yticklabels(labels, fontfamily=SANS, fontsize=11, color=INK)
    ax.set_xlim(0, 48)
    ax.set_ylim(-0.7, len(BARS) - 0.3)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0, pad=8)

    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    ax.set_title("Share of inspections ending in an on-the-spot closure",
                 fontfamily=SANS, fontsize=11.5, fontweight="bold",
                 color=INK, loc="left", pad=22, x=-0.245)

    fig.text(0.492, 0.088,
             "Data: NYC DOHMH inspection results via NYC Open Data",
             fontfamily=SANS, fontsize=9.5, color="#8a8378", va="center")


def build():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI, facecolor=BG)

    draw_left_column(fig)
    draw_chart(fig)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=DPI, facecolor=BG)
    plt.close(fig)
    print(f"Wrote {OUT} ({int(W_IN * DPI)}x{int(H_IN * DPI)})")
    print(f"Fonts: serif={SERIF}, sans={SANS}")


if __name__ == "__main__":
    build()
