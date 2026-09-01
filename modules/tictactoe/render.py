from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .game import Board, Mark
from .session import GameSession, Player
from .stats import PlayerStats

W, H = 860, 860

_BG_TOP = (20, 12, 38)
_BG_BOTTOM = (36, 18, 64)
_PANEL = (40, 24, 72)
_PANEL_BORDER = (94, 60, 158)
_CELL = (48, 30, 86)
_CELL_BORDER = (108, 72, 176)
_TEXT = (240, 235, 250)
_MUTED = (176, 158, 214)
_RED = (255, 71, 130)
_BLUE = (168, 105, 255)
_GREEN = (72, 235, 137)
_GOLD = (255, 205, 86)

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
FONT_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"
FONT_REGULAR = FONT_DIR / "DejaVuSans.ttf"

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    key = ("bold" if bold else "regular", size)
    if key in _font_cache:
        return _font_cache[key]
    font = ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)
    _font_cache[key] = font
    return font


def _vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (1, h), 0)
    for y in range(h):
        t = y / max(h - 1, 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        base.putpixel((0, y), color)
    return base.resize((w, h))


def _rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def _glow_layer(size: tuple[int, int], draw_fn, color: tuple[int, int, int], blur: int, alpha: int = 200) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer), (*color, alpha))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def _circular_avatar(avatar_bytes: bytes | None, size: int, fallback_letter: str, fallback_color: tuple[int, int, int]) -> Image.Image:
    if avatar_bytes:
        try:
            img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((size, size))
        except OSError:
            img = None
    else:
        img = None

    if img is None:
        img = Image.new("RGBA", (size, size), (*fallback_color, 255))
        draw = ImageDraw.Draw(img)
        font = _load_font(size // 2, bold=True)
        bbox = draw.textbbox((0, 0), fallback_letter, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), fallback_letter, font=font, fill=(255, 255, 255, 255))

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def _draw_x(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int, int], width: int) -> None:
    x0, y0, x1, y1 = box
    pad = (x1 - x0) * 0.18
    draw.line((x0 + pad, y0 + pad, x1 - pad, y1 - pad), fill=color, width=width, joint="curve")
    draw.line((x1 - pad, y0 + pad, x0 + pad, y1 - pad), fill=color, width=width, joint="curve")


def _draw_o(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int, int], width: int) -> None:
    x0, y0, x1, y1 = box
    pad = (x1 - x0) * 0.14
    draw.ellipse((x0 + pad, y0 + pad, x1 - pad, y1 - pad), outline=color, width=width)


def _player_card(
    base: Image.Image,
    box: tuple[int, int, int, int],
    player: Player,
    avatar_bytes: bytes | None,
    mark: Mark,
    highlight_color: tuple[int, int, int] | None,
) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(card)
    cdraw.rounded_rectangle((0, 0, w - 1, h - 1), radius=18, fill=(*_PANEL, 255), outline=(*_PANEL_BORDER, 255), width=2)

    if highlight_color:
        glow = _glow_layer(
            (w, h),
            lambda d, c: d.rounded_rectangle((0, 0, w - 1, h - 1), radius=18, outline=c, width=6),
            highlight_color,
            blur=6,
            alpha=230,
        )
        card = Image.alpha_composite(glow, card)
        cdraw = ImageDraw.Draw(card)
        cdraw.rounded_rectangle((0, 0, w - 1, h - 1), radius=18, outline=(*highlight_color, 255), width=3)

    avatar_size = 74
    mark_color = _RED if mark is Mark.X else _BLUE
    fallback_letter = next((c for c in player.display_name if c.isalnum()), "?").upper()
    avatar = _circular_avatar(avatar_bytes, avatar_size, fallback_letter, mark_color)
    avatar_pos = (20, (h - avatar_size) // 2)
    card.paste(avatar, avatar_pos, avatar)
    ring = ImageDraw.Draw(card)
    ax0, ay0 = avatar_pos
    ring.ellipse((ax0 - 2, ay0 - 2, ax0 + avatar_size + 2, ay0 + avatar_size + 2), outline=(*mark_color, 255), width=4)

    name_font = _load_font(25, bold=True)
    sub_font = _load_font(18, bold=False)
    text_x = avatar_pos[0] + avatar_size + 17
    name = player.display_name if len(player.display_name) <= 16 else player.display_name[:15] + "…"
    cdraw.text((text_x, h / 2 - 24), name, font=name_font, fill=_TEXT)
    badge_text = f"Spielt als {mark.value}"
    cdraw.text((text_x, h / 2 + 8), badge_text, font=sub_font, fill=_MUTED)

    base.alpha_composite(card, (x0, y0))


def render_game_card(
    session: GameSession,
    status_text: str,
    winning_line: Sequence[int] | None,
    avatars: dict[int, bytes | None],
    active_mark: Mark | None,
) -> bytes:
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gradient = _vertical_gradient((W, H), _BG_TOP, _BG_BOTTOM).convert("RGBA")
    panel_mask = _rounded_mask((W - 40, H - 40), 28)
    panel = Image.new("RGBA", (W - 40, H - 40), (0, 0, 0, 0))
    panel.paste(gradient.crop((20, 20, W - 20, H - 20)), (0, 0))
    panel.putalpha(panel_mask)
    base.alpha_composite(panel, (20, 20))
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle((20, 20, W - 20, H - 20), radius=28, outline=(*_PANEL_BORDER, 255), width=2)

    title_font = _load_font(39, bold=True)
    title = "TIC TAC TOE"
    tb = draw.textbbox((0, 0), title, font=title_font)
    tw = tb[2] - tb[0]
    title_x = (W - tw) / 2
    title_y = 52
    draw.text((title_x, title_y), title, font=title_font, fill=_TEXT)
    _draw_x(draw, (title_x - 56, title_y + 2, title_x - 56 + 34, title_y + 2 + 34), (*_RED, 255), 6)
    _draw_o(draw, (title_x + tw + 22, title_y + 2, title_x + tw + 22 + 34, title_y + 2 + 34), (*_BLUE, 255), 6)

    x_highlight = _RED if active_mark is Mark.X else None
    o_highlight = _BLUE if active_mark is Mark.O else None
    _player_card(base, (48, 135, 412, 256), session.player_x, avatars.get(session.player_x.user_id), Mark.X, x_highlight)
    _player_card(base, (448, 135, 812, 256), session.player_o, avatars.get(session.player_o.user_id), Mark.O, o_highlight)

    cell = 145
    gap = 12
    grid_w = cell * 3 + gap * 2
    grid_x0 = (W - grid_w) / 2
    grid_y0 = 290

    for i, mark in enumerate(session.board.cells):
        row, col = divmod(i, 3)
        x0 = grid_x0 + col * (cell + gap)
        y0 = grid_y0 + row * (cell + gap)
        x1, y1 = x0 + cell, y0 + cell
        is_win_cell = winning_line is not None and i in winning_line
        border_color = _GREEN if is_win_cell else _CELL_BORDER
        draw.rounded_rectangle((x0, y0, x1, y1), radius=17, fill=(*_CELL, 255), outline=(*border_color, 255), width=4 if is_win_cell else 2)

        if mark is Mark.EMPTY:
            continue
        color = _RED if mark is Mark.X else _BLUE
        box = (x0, y0, x1, y1)
        glow = _glow_layer(
            (W, H),
            lambda d, c, box=box, mark=mark: (_draw_x(d, box, c, 15) if mark is Mark.X else _draw_o(d, box, c, 12)),
            color,
            blur=9,
        )
        base.alpha_composite(glow)
        draw = ImageDraw.Draw(base)
        if mark is Mark.X:
            _draw_x(draw, box, (*color, 255), 15)
        else:
            _draw_o(draw, box, (*color, 255), 12)

    if winning_line:
        a, c = winning_line[0], winning_line[2]
        ar, ac = divmod(a, 3)
        cr, cc = divmod(c, 3)
        p1 = (grid_x0 + ac * (cell + gap) + cell / 2, grid_y0 + ar * (cell + gap) + cell / 2)
        p2 = (grid_x0 + cc * (cell + gap) + cell / 2, grid_y0 + cr * (cell + gap) + cell / 2)
        line_glow = _glow_layer((W, H), lambda d, col: d.line((*p1, *p2), fill=col, width=17), _GREEN, blur=12)
        base.alpha_composite(line_glow)
        draw = ImageDraw.Draw(base)
        draw.line((*p1, *p2), fill=(*_GREEN, 255), width=10)

    grid_bottom = grid_y0 + grid_w
    status_font = _load_font(27, bold=True)
    sb = draw.textbbox((0, 0), status_text, font=status_font)
    sw = sb[2] - sb[0]
    status_color = _GREEN if winning_line else (_GOLD if "Unentschieden" in status_text else _TEXT)
    draw.text(((W - sw) / 2, grid_bottom + 27), status_text, font=status_font, fill=status_color)

    out = io.BytesIO()
    base.convert("RGB").save(out, format="PNG")
    return out.getvalue()


def render_stats_card(entries: list[tuple[Player, PlayerStats]]) -> bytes:
    height = 200 + 110 * max(len(entries), 1)
    base = Image.new("RGBA", (W, height), (0, 0, 0, 0))
    gradient = _vertical_gradient((W, height), _BG_TOP, _BG_BOTTOM).convert("RGBA")
    panel_mask = _rounded_mask((W - 40, height - 40), 28)
    panel = Image.new("RGBA", (W - 40, height - 40), (0, 0, 0, 0))
    panel.paste(gradient.crop((20, 20, W - 20, height - 20)), (0, 0))
    panel.putalpha(panel_mask)
    base.alpha_composite(panel, (20, 20))
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle((20, 20, W - 20, height - 20), radius=28, outline=(*_PANEL_BORDER, 255), width=2)

    title_font = _load_font(30, bold=True)
    title = "STATISTIKEN"
    tb = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((W - (tb[2] - tb[0])) / 2, 42), title, font=title_font, fill=_TEXT)

    name_font = _load_font(20, bold=True)
    stat_font = _load_font(18, bold=False)
    y = 120
    for player, stats in entries:
        card_box = (40, y, W - 40, y + 90)
        draw.rounded_rectangle(card_box, radius=16, fill=(*_PANEL, 255), outline=(*_PANEL_BORDER, 255), width=2)
        draw.text((64, y + 16), player.display_name, font=name_font, fill=_TEXT)
        line = f"Siege: {stats.wins}   Niederlagen: {stats.losses}   Unentschieden: {stats.draws}"
        draw.text((64, y + 48), line, font=stat_font, fill=_MUTED)
        rate = f"{stats.win_rate:.0f}% Winrate ({stats.games} Spiele)"
        rb = draw.textbbox((0, 0), rate, font=stat_font)
        draw.text((W - 64 - (rb[2] - rb[0]), y + 48), rate, font=stat_font, fill=_GOLD)
        y += 110

    out = io.BytesIO()
    base.convert("RGB").save(out, format="PNG")
    return out.getvalue()
