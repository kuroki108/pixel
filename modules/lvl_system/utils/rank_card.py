"""
Generiert eine Rank-Card als PNG (im Arbeitsspeicher, kein Disk-I/O nötig).

Stil: dunkler Hintergrund + Neon-Akzente (Cyan/Magenta), passend zu einem
Anime-/Arcade-Server-Theme. Reine PIL-Zeichnung, keine externen Assets
außer den mitgelieferten DejaVu-Fonts nötig.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from modules.lvl_system.utils.leveling_math import xp_for_next_level

FONT_DIR = Path(__file__).resolve().parents[3] / "assets" / "fonts"
FONT_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"
FONT_REGULAR = FONT_DIR / "DejaVuSans.ttf"

WIDTH, HEIGHT = 934, 282
NEON_CYAN = (0, 229, 255)
NEON_MAGENTA = (255, 0, 170)
BG_DARK = (13, 10, 28)
BG_PANEL = (20, 16, 40)
TEXT_WHITE = (240, 240, 250)
TEXT_MUTED = (150, 145, 175)


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _rounded_gradient_bar(box: tuple[int, int, int, int], progress: float) -> Image.Image:
    """Erzeugt eine RGBA-Ebene (Kartengröße) mit einer gefüllten Neon-Gradient-Leiste."""
    x0, y0, x1, y1 = box
    height = y1 - y0
    width = x1 - x0
    radius = height // 2
    fill_width = max(0, min(width, int(width * max(0.0, min(progress, 1.0)))))

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    if fill_width <= 2:
        return overlay

    gradient = Image.new("RGB", (fill_width, height), BG_PANEL)
    grad_draw = ImageDraw.Draw(gradient)
    for i in range(fill_width):
        t = i / max(1, width)  # Farbverlauf bezieht sich auf die volle Balkenbreite
        r = int(NEON_CYAN[0] + (NEON_MAGENTA[0] - NEON_CYAN[0]) * t)
        g = int(NEON_CYAN[1] + (NEON_MAGENTA[1] - NEON_CYAN[1]) * t)
        b = int(NEON_CYAN[2] + (NEON_MAGENTA[2] - NEON_CYAN[2]) * t)
        grad_draw.line([(i, 0), (i, height)], fill=(r, g, b))

    mask = Image.new("L", (fill_width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fill_width, height), radius=radius, fill=255)

    overlay.paste(gradient, (x0, y0), mask)
    return overlay


def generate_rank_card(
    *,
    username: str,
    discriminator_tag: str,
    avatar_bytes: bytes,
    level: int,
    xp_in_level: int,
    rank: int,
    total_xp: int,
) -> io.BytesIO:
    needed = xp_for_next_level(level)
    progress = xp_in_level / needed if needed else 0.0

    base = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(base)

    # Panel mit Neon-Rahmen
    panel_box = (10, 10, WIDTH - 10, HEIGHT - 10)
    draw.rounded_rectangle(panel_box, radius=24, fill=BG_PANEL, outline=NEON_CYAN, width=3)
    draw.rounded_rectangle(
        (panel_box[0] + 3, panel_box[1] + 3, panel_box[2] - 3, panel_box[3] - 3),
        radius=22, outline=NEON_MAGENTA, width=1,
    )

    # Avatar (Kreis)
    avatar_size = 170
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((avatar_size, avatar_size))
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
    avatar_pos = (48, (HEIGHT - avatar_size) // 2)
    # Neon-Ring um den Avatar
    ring_pad = 6
    draw.ellipse(
        (
            avatar_pos[0] - ring_pad, avatar_pos[1] - ring_pad,
            avatar_pos[0] + avatar_size + ring_pad, avatar_pos[1] + avatar_size + ring_pad,
        ),
        outline=NEON_CYAN, width=4,
    )
    base.paste(avatar, avatar_pos, mask)

    text_x = avatar_pos[0] + avatar_size + 40

    name_font = _font(FONT_BOLD, 40)
    tag_font = _font(FONT_REGULAR, 22)
    label_font = _font(FONT_REGULAR, 22)
    big_font = _font(FONT_BOLD, 30)

    draw.text((text_x, 40), username, font=name_font, fill=TEXT_WHITE)
    name_w = draw.textlength(username, font=name_font)
    draw.text((text_x + name_w + 10, 55), discriminator_tag, font=tag_font, fill=TEXT_MUTED)

    # Rechts oben: Rang & Level
    rank_text = f"RANG #{rank}"
    level_text = f"LEVEL {level}"
    rank_w = draw.textlength(rank_text, font=big_font)
    level_w = draw.textlength(level_text, font=big_font)
    draw.text((WIDTH - 40 - level_w, 40), level_text, font=big_font, fill=NEON_MAGENTA)
    draw.text((WIDTH - 40 - rank_w, 78), rank_text, font=label_font, fill=NEON_CYAN)

    # Progress-Bar: Hintergrund-Leiste + Neon-Gradient-Füllung
    bar_box = (text_x, 150, WIDTH - 40, 178)
    bar_radius = (bar_box[3] - bar_box[1]) // 2
    draw.rounded_rectangle(bar_box, radius=bar_radius, fill=(35, 30, 60))

    overlay = _rounded_gradient_bar(bar_box, progress)
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(base)

    draw.rounded_rectangle(bar_box, radius=bar_radius, outline=(60, 55, 90), width=1)

    xp_text = f"{xp_in_level:,} / {needed:,} XP".replace(",", ".")
    draw.text((text_x, 188), xp_text, font=label_font, fill=TEXT_MUTED)

    total_text = f"Gesamt: {total_xp:,} XP".replace(",", ".")
    total_w = draw.textlength(total_text, font=label_font)
    draw.text((WIDTH - 40 - total_w, 188), total_text, font=label_font, fill=TEXT_MUTED)

    buf = io.BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    return buf
