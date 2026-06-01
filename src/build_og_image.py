"""
Generate the 1200x630 Open Graph preview card for the article.

Standard OG image dimensions (works for LinkedIn, Twitter, Facebook,
Slack link previews, etc.). Run once after any title/byline change:

    python src/build_og_image.py

Output: reports/og-image.png

Design notes
------------
LinkedIn / Twitter compositors aggressively downscale the OG image to
small thumbnails in compact preview modes. Anything light-grey or below
~32pt becomes mush. This card uses:
  * Solid dark text (no greys for secondary copy)
  * 96pt title that fills the top half
  * 38pt deck text, two lines max
  * 28pt byline
  * High-contrast monogram badge
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


REPORTS = Path(__file__).resolve().parent.parent / "reports"
OUT = REPORTS / "og-image.png"

# Canvas
W, H = 1200, 630
BG       = (251, 247, 240)   # warm off-white, matches article body
INK      = (20, 20, 20)      # primary text, slightly darker than --ink
SUBTLE   = (60, 60, 60)      # deck text — darker than --ink-dim for thumbnail legibility
ACCENT   = (192, 57, 43)     # red accent (matches --accent)
MONO_BG  = (20, 20, 20)      # dark badge background for FA monogram

# Side padding
PAD_L = 80
PAD_R = 80
PAD_T = 80
PAD_B = 70


def load_font(size: int, bold: bool = False, italic: bool = False):
    """Best-effort font loader. Tries Source Serif Pro / Inter / Georgia
    candidates in order, falls back to PIL default if nothing's found."""
    candidates_serif_bold = [
        "SourceSerifPro-Bold.ttf",
        "Georgia Bold.ttf",
        "georgiab.ttf",
        "Times New Roman Bold.ttf",
        "timesbd.ttf",
    ]
    candidates_serif_regular = [
        "SourceSerifPro-Regular.ttf",
        "Georgia.ttf",
        "georgia.ttf",
        "Times New Roman.ttf",
        "times.ttf",
    ]
    candidates_serif_italic = [
        "SourceSerifPro-Italic.ttf",
        "Georgia Italic.ttf",
        "georgiai.ttf",
    ]
    candidates_sans_bold = [
        "Inter-Bold.ttf",
        "Arial Bold.ttf",
        "arialbd.ttf",
    ]
    if italic:
        candidates = candidates_serif_italic
    elif bold:
        candidates = candidates_serif_bold + candidates_sans_bold
    else:
        candidates = candidates_serif_regular
    for name in candidates:
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

    max_text_w = W - PAD_L - PAD_R

    # Top eyebrow: red, bold, larger than original.
    eyebrow_font = load_font(26, bold=True)
    eyebrow_text = "A DATA-BACKED CASE STUDY"
    draw.text((PAD_L, PAD_T), eyebrow_text, fill=ACCENT, font=eyebrow_font)

    # Main title — much larger serif, dark, 2 lines max.
    title_font = load_font(82, bold=True)
    title_text = "The Quiet Math of NYC's Restaurant Inspections"
    title_lines = wrap_text(draw, title_text, title_font, max_text_w)
    title_y = PAD_T + 56
    line_h = 94
    for line in title_lines:
        draw.text((PAD_L, title_y), line, fill=INK, font=title_font)
        title_y += line_h

    # Deck — bigger and DARKER than before so it survives thumbnail compression.
    deck_font = load_font(34, bold=False)
    deck_text = ("What 83,354 health inspections reveal about pests, "
                 "plumbing, and what gets a kitchen shut down.")
    deck_lines = wrap_text(draw, deck_text, deck_font, max_text_w)
    deck_y = title_y + 18
    deck_line_h = 46
    for line in deck_lines:
        draw.text((PAD_L, deck_y), line, fill=SUBTLE, font=deck_font)
        deck_y += deck_line_h

    # Byline at bottom-left — bigger, dark.
    byline_font = load_font(36, bold=True)
    byline_text = "By Fahim Ahamed"
    byline_bbox = draw.textbbox((0, 0), byline_text, font=byline_font)
    byline_h = byline_bbox[3] - byline_bbox[1]
    byline_y = H - PAD_B - byline_h - 6
    draw.text((PAD_L, byline_y), byline_text, fill=INK, font=byline_font)

    # "FA" monogram badge bottom-right — matches the favicon, slightly larger.
    mono_size = 70
    mono_x = W - PAD_R - mono_size
    mono_y = H - PAD_B - mono_size - 4
    draw.rounded_rectangle(
        [mono_x, mono_y, mono_x + mono_size, mono_y + mono_size],
        radius=10, fill=MONO_BG,
    )
    fa_font = load_font(32, bold=True)
    fa_bbox = draw.textbbox((0, 0), "FA", font=fa_font)
    fa_w = fa_bbox[2] - fa_bbox[0]
    fa_h = fa_bbox[3] - fa_bbox[1]
    draw.text(
        (mono_x + (mono_size - fa_w) / 2,
         mono_y + (mono_size - fa_h) / 2 - 6),
        "FA",
        fill="white", font=fa_font,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT} ({W}x{H})")


if __name__ == "__main__":
    build_og_image()
