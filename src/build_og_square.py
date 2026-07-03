"""
Generate a 1200x1200 square OG image variant with thematic icons.
No byline, no monogram, rounded inspection count.

    python src/build_og_square.py

Output: reports/og-image-square.png
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

REPORTS = Path(__file__).resolve().parent.parent / "reports"
OUT = REPORTS / "og-image-square.png"

W, H = 1200, 1200
BG       = (251, 247, 240)
INK      = (20, 20, 20)
SUBTLE   = (80, 75, 68)
ACCENT   = (192, 57, 43)
ICON_CLR = (215, 205, 192)

PAD_L = 100
PAD_R = 100


def load_font(size, bold=False, italic=False):
    candidates_serif_bold = [
        "SourceSerifPro-Bold.ttf", "Georgia Bold.ttf", "georgiab.ttf",
        "Times New Roman Bold.ttf", "timesbd.ttf",
    ]
    candidates_serif_regular = [
        "SourceSerifPro-Regular.ttf", "Georgia.ttf", "georgia.ttf",
        "Times New Roman.ttf", "times.ttf",
    ]
    candidates_serif_italic = [
        "SourceSerifPro-Italic.ttf", "Georgia Italic.ttf", "georgiai.ttf",
    ]
    candidates_sans_bold = ["Inter-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]
    candidates_sans = ["Inter-Regular.ttf", "Arial.ttf", "arial.ttf"]
    if italic:
        candidates = candidates_serif_italic
    elif bold:
        candidates = candidates_serif_bold + candidates_sans_bold
    else:
        candidates = candidates_serif_regular + candidates_sans
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
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


# --- Icon drawing on separate images for rotation support ---

def _icon_canvas(size):
    s = int(size * 2.5)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    return img, draw, s // 2, s // 2


def make_bar_chart(size, color):
    img, draw, cx, cy = _icon_canvas(size)
    s = size
    bar_w = s * 0.2
    gap = s * 0.1
    heights = [0.35, 0.75, 0.55]
    total_w = len(heights) * bar_w + (len(heights) - 1) * gap
    x_start = cx - total_w / 2
    base_y = cy + s * 0.35
    for i, h in enumerate(heights):
        x = x_start + i * (bar_w + gap)
        bar_h = s * h
        draw.rectangle([x, base_y - bar_h, x + bar_w, base_y], fill=color)
    draw.line([x_start - 4, base_y, x_start + total_w + 4, base_y], fill=color, width=3)
    draw.line([x_start - 4, base_y - s * 0.8, x_start - 4, base_y], fill=color, width=3)
    return img


def make_magnifying_glass(size, color):
    img, draw, cx, cy = _icon_canvas(size)
    r = size * 0.3
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=5)
    hx = cx + r * 0.7
    hy = cy + r * 0.7
    draw.line([hx, hy, hx + size * 0.25, hy + size * 0.25], fill=color, width=6)
    return img


def make_clipboard(size, color):
    img, draw, cx, cy = _icon_canvas(size)
    s = size
    bw, bh = s * 0.5, s * 0.65
    draw.rounded_rectangle(
        [cx - bw/2, cy - bh/2, cx + bw/2, cy + bh/2],
        radius=8, outline=color, width=4
    )
    tw = s * 0.22
    draw.rounded_rectangle(
        [cx - tw/2, cy - bh/2 - 5, cx + tw/2, cy - bh/2 + 12],
        radius=5, fill=color
    )
    for i in range(3):
        ly = cy - bh * 0.18 + i * (s * 0.15)
        draw.line([cx - bw * 0.28, ly, cx + bw * 0.28, ly], fill=color, width=3)
    return img


def make_bug(size, color):
    img, draw, cx, cy = _icon_canvas(size)
    s = size
    draw.ellipse([cx - s*0.17, cy - s*0.05, cx + s*0.17, cy + s*0.32], outline=color, width=4)
    draw.ellipse([cx - s*0.12, cy - s*0.22, cx + s*0.12, cy - s*0.02], fill=color)
    for yoff in [-0.02, 0.1, 0.22]:
        ly = cy + s * yoff
        draw.line([cx - s*0.17, ly, cx - s*0.34, ly - s*0.08], fill=color, width=3)
        draw.line([cx + s*0.17, ly, cx + s*0.34, ly - s*0.08], fill=color, width=3)
    draw.line([cx - s*0.07, cy - s*0.22, cx - s*0.18, cy - s*0.38], fill=color, width=3)
    draw.line([cx + s*0.07, cy - s*0.22, cx + s*0.18, cy - s*0.38], fill=color, width=3)
    return img


def make_fork_knife(size, color):
    img, draw, cx, cy = _icon_canvas(size)
    s = size
    fx = cx - s * 0.1
    draw.line([fx, cy - s*0.32, fx, cy + s*0.32], fill=color, width=3)
    for dx in [-s*0.07, 0, s*0.07]:
        draw.line([fx + dx, cy - s*0.32, fx + dx, cy - s*0.1], fill=color, width=3)
    kx = cx + s * 0.12
    draw.line([kx, cy - s*0.32, kx, cy + s*0.32], fill=color, width=3)
    draw.ellipse([kx - s*0.05, cy - s*0.32, kx + s*0.07, cy - s*0.08], outline=color, width=3)
    return img


def make_pie_chart(size, color):
    img, draw, cx, cy = _icon_canvas(size)
    r = size * 0.35
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=4)
    draw.line([cx, cy, cx, cy - r], fill=color, width=3)
    angle = math.radians(120)
    draw.line([cx, cy, cx + r * math.sin(angle), cy - r * math.cos(angle)], fill=color, width=3)
    draw.pieslice([cx - r, cy - r, cx + r, cy + r], start=-90, end=30, fill=color)
    return img


def make_trend_line(size, color):
    img, draw, cx, cy = _icon_canvas(size)
    s = size
    points = [
        (cx - s*0.35, cy + s*0.18),
        (cx - s*0.1, cy - s*0.08),
        (cx + s*0.08, cy + s*0.08),
        (cx + s*0.35, cy - s*0.25),
    ]
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=color, width=4)
    for p in points:
        draw.ellipse([p[0]-5, p[1]-5, p[0]+5, p[1]+5], fill=color)
    return img


def paste_icon(canvas, icon_img, cx, cy, rotation=0):
    """Paste a rotated icon centered at (cx, cy)."""
    if rotation:
        icon_img = icon_img.rotate(rotation, resample=Image.BICUBIC, expand=True)
    x = int(cx - icon_img.width / 2)
    y = int(cy - icon_img.height / 2)
    canvas.paste(icon_img, (x, y), icon_img)


def build():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    max_text_w = W - PAD_L - PAD_R

    # --- Measure text block first to know safe zones ---
    eyebrow_font = load_font(24, bold=True)
    title_font = load_font(108, bold=True)
    deck_font = load_font(36)

    eyebrow_text = "A DATA-BACKED CASE STUDY"
    title_text = "The Quiet Math of NYC's Restaurant Inspections"
    deck_text = ("What ~83,000 health inspections reveal about pests, "
                 "plumbing, and what gets a kitchen shut down.")

    title_lines = wrap_text(draw, title_text, title_font, max_text_w)
    deck_lines = wrap_text(draw, deck_text, deck_font, max_text_w)

    eyebrow_h = 24
    gap_after_eyebrow = 24
    title_line_h = 124
    gap_after_title = 28
    deck_line_h = 50

    total_h = (eyebrow_h + gap_after_eyebrow
               + title_line_h * len(title_lines)
               + gap_after_title
               + deck_line_h * len(deck_lines))

    text_top_y = (H - total_h) // 2
    text_bot_y = text_top_y + total_h

    # --- Icons: scattered in top/bottom margins, varied sizes & rotations ---
    # (maker_fn, cx, cy, size, rotation_degrees)
    icon_specs = [
        # Top zone
        (make_bar_chart,        150,   110,  100,  -8),
        (make_magnifying_glass, 1060,  90,   120,  12),
        (make_pie_chart,        550,   100,  65,   -5),
        (make_trend_line,       820,   130,  80,   6),
        # Bottom zone
        (make_bug,              160,   1050, 110,  10),
        (make_fork_knife,       420,   1100, 75,   -12),
        (make_clipboard,        1050,  1020, 100,  8),
        (make_trend_line,       700,   1090, 90,   -6),
        (make_bar_chart,        900,   1100, 65,   15),
        (make_pie_chart,        280,   1110, 55,   -10),
    ]
    for fn, x, y, sz, rot in icon_specs:
        icon = fn(sz, ICON_CLR)
        paste_icon(img, icon, x, y, rot)

    # Redraw after icon paste (icons are behind text)
    draw = ImageDraw.Draw(img)

    # --- Draw text ---
    y = text_top_y

    # Eyebrow: spaced-out uppercase, smaller
    spaced = "  ".join(eyebrow_text)
    draw.text((PAD_L, y), spaced, fill=ACCENT, font=eyebrow_font)
    y += eyebrow_h + gap_after_eyebrow

    for line in title_lines:
        draw.text((PAD_L, y), line, fill=INK, font=title_font)
        y += title_line_h

    y += gap_after_title
    for line in deck_lines:
        draw.text((PAD_L, y), line, fill=SUBTLE, font=deck_font)
        y += deck_line_h

    # Thin accent rule between title and deck
    rule_y = y - gap_after_title - deck_line_h * len(deck_lines) - 6
    draw.line([PAD_L, rule_y, PAD_L + 80, rule_y], fill=ACCENT, width=3)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT} ({W}x{H})")


if __name__ == "__main__":
    build()
