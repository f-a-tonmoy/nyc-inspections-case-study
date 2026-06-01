"""
Generate the 1200x630 Open Graph preview card for the article.

Standard OG image dimensions (works for LinkedIn, Twitter, Facebook,
Slack link previews, etc.). Run once after any title/byline change:

    python src/build_og_image.py

Output: reports/og-image.png

The PNG is referenced from article.html's <head> via the og:image meta
tag, and is served alongside article.html when the repo is deployed to
GitHub Pages.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


REPORTS = Path(__file__).resolve().parent.parent / "reports"
OUT = REPORTS / "og-image.png"

# Canvas
W, H = 1200, 630
BG       = (251, 247, 240)   # warm off-white, matches article body
INK      = (26, 26, 26)      # primary text (matches --ink)
INK_DIM  = (102, 102, 102)   # secondary text (matches --ink-dim)
ACCENT   = (192, 57, 43)     # red accent (matches --accent)
RULE     = (218, 218, 218)   # hairline rule color

# Side padding
PAD_L = 80
PAD_R = 80
PAD_T = 90
PAD_B = 80


def load_font(size: int, bold: bool = False, italic: bool = False):
    """Best-effort font loader. Tries Source Serif Pro / Inter if installed
    on the machine, falls back to Georgia / Arial / PIL default."""
    candidates_serif = [
        "SourceSerifPro-Bold.ttf" if bold else "SourceSerifPro-Regular.ttf",
        "Georgia Bold.ttf" if bold else "Georgia.ttf",
        "georgiab.ttf" if bold else "georgia.ttf",
        "Times New Roman Bold.ttf" if bold else "Times New Roman.ttf",
        "timesbd.ttf" if bold else "times.ttf",
    ]
    candidates_sans = [
        "Inter-Bold.ttf" if bold else "Inter-Regular.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    # Caller distinguishes serif via the `italic` flag here — keep it simple:
    # we always try serif first (used for the title and deck), and the
    # eyebrow + byline pass bold=True to get a bolder fallback weight.
    candidates = candidates_serif if not italic else [
        f.replace("Regular", "Italic").replace("Bold", "BoldItalic")
        for f in candidates_serif
    ]
    for name in candidates + candidates_sans:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    """Greedy word-wrap so the title/deck fits the available width."""
    words = text.split()
    lines, current = [], ""
    for w in words:
        trial = (current + " " + w).strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def build_og_image():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Top eyebrow: "A DATA-BACKED CASE STUDY" in red small-caps style
    eyebrow_font = load_font(20, bold=True)
    draw.text(
        (PAD_L, PAD_T),
        "A DATA-BACKED CASE STUDY",
        fill=ACCENT, font=eyebrow_font,
    )

    # Main title — large serif bold
    title_font = load_font(72, bold=True)
    title_text = "The Quiet Math of NYC's Restaurant Inspections"
    max_text_w = W - PAD_L - PAD_R
    title_lines = wrap_text(draw, title_text, title_font, max_text_w)
    title_y = PAD_T + 50
    line_h = 84
    for line in title_lines:
        draw.text((PAD_L, title_y), line, fill=INK, font=title_font)
        title_y += line_h

    # Thin red rule under the title
    rule_y = title_y + 18
    draw.rectangle([PAD_L, rule_y, PAD_L + 60, rule_y + 3], fill=ACCENT)

    # Deck (italic medium serif, dim color)
    deck_font = load_font(30, italic=True)
    deck_text = ("What 83,354 health inspections in 27,350 active NYC "
                 "restaurants reveal about pests, plumbing, and what "
                 "actually gets a kitchen shut down.")
    deck_lines = wrap_text(draw, deck_text, deck_font, max_text_w)
    deck_y = rule_y + 32
    deck_line_h = 42
    for line in deck_lines:
        draw.text((PAD_L, deck_y), line, fill=INK_DIM, font=deck_font)
        deck_y += deck_line_h

    # Byline at bottom
    byline_font = load_font(22, bold=True)
    byline_text = "By Fahim Ahamed"
    draw.text(
        (PAD_L, H - PAD_B - 28),
        byline_text,
        fill=INK, font=byline_font,
    )

    # Subtle "FA" monogram in the bottom-right corner — mirrors the favicon.
    mono_size = 56
    mono_x = W - PAD_R - mono_size
    mono_y = H - PAD_B - mono_size - 4
    draw.rounded_rectangle(
        [mono_x, mono_y, mono_x + mono_size, mono_y + mono_size],
        radius=8, fill=INK,
    )
    fa_font = load_font(26, bold=True)
    fa_bbox = draw.textbbox((0, 0), "FA", font=fa_font)
    fa_w = fa_bbox[2] - fa_bbox[0]
    fa_h = fa_bbox[3] - fa_bbox[1]
    draw.text(
        (mono_x + (mono_size - fa_w) / 2,
         mono_y + (mono_size - fa_h) / 2 - 4),
        "FA",
        fill="white", font=fa_font,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT} ({W}x{H})")


if __name__ == "__main__":
    build_og_image()
