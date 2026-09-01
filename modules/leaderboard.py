import asyncio
import io
from dataclasses import dataclass
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont

from modules.database import Database

# Wie oft die live im Channel stehende Nachricht neu gerendert wird.
REFRESH_INTERVAL_MINUTES = 10

BG_TOP = (32, 12, 56)
BG_BOTTOM = (72, 20, 112)
ACCENT = (155, 89, 182)
ACCENT_LIGHT = (200, 150, 224)
ROW = (54, 25, 84)
ROW_TOP3 = (92, 46, 132)
TEXT_LIGHT = (240, 230, 250)
TEXT_MUTED = (188, 168, 210)
MEDAL_COLORS = {0: (222, 188, 255), 1: (198, 150, 224), 2: (170, 112, 202)}

EMBED_COLOR = discord.Color.from_rgb(*ACCENT)

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"
FONT_REGULAR = FONT_DIR / "DejaVuSans.ttf"

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


@dataclass
class Entry:
    name: str
    stat: str
    sub: str = ""


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = ("bold" if bold else "regular", size)
    if key in _font_cache:
        return _font_cache[key]
    font = ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)
    _font_cache[key] = font
    return font


def render_combined_leaderboard(sections: list[tuple[str, list[Entry]]]) -> bytes:
    width = 1180
    row_h = 96
    row_gap = 14
    padding = 44
    section_header_h = 64
    section_gap = 40

    def rows_for(entries: list[Entry]) -> int:
        return max(1, len(entries))

    height = padding
    for _title, entries in sections:
        n = rows_for(entries)
        height += section_header_h + n * row_h + (n - 1) * row_gap
    height += section_gap * (len(sections) - 1) + padding

    img = Image.new("RGB", (width, height), BG_TOP)
    draw = ImageDraw.Draw(img)

    for y in range(height):
        t = y / height
        r = round(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = round(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = round(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    title_font = _load_font(38, bold=True)
    rank_font = _load_font(30, bold=True)
    name_font = _load_font(29, bold=True)
    stat_font = _load_font(26, bold=True)
    sub_font = _load_font(20)
    empty_font = _load_font(24)

    y = padding
    for title, entries in sections:
        draw.text((padding, y), title, font=title_font, fill=TEXT_LIGHT)
        y += section_header_h - 10
        draw.line([(padding, y), (width - padding, y)], fill=ACCENT, width=2)
        y += 10

        if not entries:
            draw.text((padding + 12, y + row_h / 2 - 14), "Noch keine Daten", font=empty_font, fill=TEXT_MUTED)
            y += row_h
        else:
            for idx, entry in enumerate(entries):
                row_fill = ROW_TOP3 if idx < 3 else ROW
                draw.rounded_rectangle([padding, y, width - padding, y + row_h], radius=20, fill=row_fill)

                badge_color = MEDAL_COLORS.get(idx, ACCENT)
                cx, cy = padding + 56, y + row_h // 2
                draw.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=badge_color)
                rank_str = str(idx + 1)
                rb = draw.textbbox((0, 0), rank_str, font=rank_font)
                draw.text(
                    (cx - (rb[2] - rb[0]) / 2, cy - (rb[3] - rb[1]) / 2 - rb[1]),
                    rank_str,
                    font=rank_font,
                    fill=(30, 10, 45),
                )

                name_x = padding + 112
                draw.text((name_x, y + 14), entry.name, font=name_font, fill=TEXT_LIGHT)
                if entry.sub:
                    draw.text((name_x, y + 56), entry.sub, font=sub_font, fill=TEXT_MUTED)

                sb = draw.textbbox((0, 0), entry.stat, font=stat_font)
                stat_w = sb[2] - sb[0]
                draw.text(
                    (width - padding - 28 - stat_w, y + row_h / 2 - (sb[3] - sb[1]) / 2 - sb[1]),
                    entry.stat,
                    font=stat_font,
                    fill=ACCENT_LIGHT,
                )
                y += row_h + row_gap
            y -= row_gap

        y += section_gap

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database):
        self.bot = bot
        self.db = db
        self.refresh_task.start()

    def cog_unload(self) -> None:
        self.refresh_task.cancel()

    async def _level_entries(self, guild: discord.Guild) -> list[Entry]:
        # Nur aktuelle Server-Mitglieder anzeigen (gleiche Logik wie das
        # ehemalige /leaderboard in lvl_system/cogs/leveling.py).
        batch_size = 25
        offset = 0
        ranked: list = []
        while len(ranked) < 5:
            batch = await self.db.get_leaderboard(guild.id, limit=batch_size, offset=offset)
            if not batch:
                break
            for stats in batch:
                member = guild.get_member(stats.user_id)
                if member is not None:
                    ranked.append((member, stats))
                    if len(ranked) >= 5:
                        break
            offset += batch_size

        return [
            Entry(
                name=member.display_name,
                stat=f"Level {stats.level}",
                sub=f"{stats.total_xp:,} XP".replace(",", "."),
            )
            for member, stats in ranked
        ]

    async def _ttt_entries(self, guild: discord.Guild) -> list[Entry]:
        rows = await self.db.get_ttt_leaderboard(limit=5)
        entries = []
        for user_id, wins, losses, draws in rows:
            member = guild.get_member(user_id)
            name = member.display_name if member else f"Nutzer {user_id}"
            entries.append(Entry(name=name, stat=f"{wins} Siege", sub=f"{losses}N · {draws}U"))
        return entries

    async def _guessing_entries(self, guild: discord.Guild) -> list[Entry]:
        rows = await self.db.get_number_guessing_scores(limit=5)
        entries = []
        for user_id, points in rows:
            member = guild.get_member(user_id)
            name = member.display_name if member else f"Nutzer {user_id}"
            entries.append(Entry(name=name, stat=f"{points} Punkt{'e' if points != 1 else ''}"))
        return entries

    async def _build_message(self, guild: discord.Guild) -> tuple[discord.Embed, discord.File]:
        sections = [
            ("🏆 Level Leaderboard", await self._level_entries(guild)),
            ("🎮 Tic-Tac-Toe Leaderboard", await self._ttt_entries(guild)),
            ("🔢 Number-Guessing Leaderboard", await self._guessing_entries(guild)),
        ]
        image_bytes = await asyncio.to_thread(render_combined_leaderboard, sections)
        file = discord.File(io.BytesIO(image_bytes), filename="leaderboard.png")

        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_image(url="attachment://leaderboard.png")
        embed.set_footer(text=f"Aktualisiert sich automatisch alle {REFRESH_INTERVAL_MINUTES} Minuten")
        return embed, file

    async def _refresh_messages(self) -> None:
        refs = await self.db.get_leaderboard_messages()
        if not refs:
            return

        for channel_id, message_id in refs.items():
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                await self.db.remove_leaderboard_message(channel_id)
                continue

            embed, file = await self._build_message(channel.guild)
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed, attachments=[file])
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                await self.db.remove_leaderboard_message(channel_id)

    @app_commands.command(name="leaderboard", description="Postet das Server-Leaderboard (aktualisiert sich automatisch).")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        embed, file = await self._build_message(interaction.guild)
        await interaction.followup.send(embed=embed, file=file)

        message = await interaction.original_response()
        await self.db.set_leaderboard_message(message.channel.id, message.id)

    @tasks.loop(minutes=REFRESH_INTERVAL_MINUTES)
    async def refresh_task(self) -> None:
        await self._refresh_messages()

    @refresh_task.before_loop
    async def before_refresh_task(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    db: Database = bot.db  # type: ignore[attr-defined]
    await bot.add_cog(Leaderboard(bot, db))
