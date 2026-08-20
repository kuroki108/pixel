import asyncio
import logging
import discord
import io
import os
from pathlib import Path

from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from config import WELCOME_CHANNEL_ID
from config import ONBOARDING_ROLE_IDS as ROLE_IDS

logger = logging.getLogger("bot.onboarding")


class Onboarding(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._assign_roles(member)

    # ------------------------------------------------------------------ #
    # Rollenvergabe
    # ------------------------------------------------------------------ #
    async def _assign_roles(self, member: discord.Member) -> None:
        if not ROLE_IDS:
            logger.warning(
                "ROLE_IDS ist leer - für %s wurden keine Rollen vergeben.", member
            )
            return

        roles_to_add = []
        for role_id in ROLE_IDS:
            role = member.guild.get_role(role_id)
            if role is None:
                logger.error(
                    "Rolle mit ID %s existiert nicht auf Server '%s'.",
                    role_id, member.guild.name,
                )
                continue
            roles_to_add.append(role)

        if not roles_to_add:
            return

        try:
            await member.add_roles(
                *roles_to_add, reason="Automatische Rollenvergabe beim Beitritt"
            )
        except discord.Forbidden:
            logger.error(
                "Keine Berechtigung, Rollen an %s zu vergeben. "
                "Prüfe, ob die Bot-Rolle in der Rollen-Hierarchie über "
                "den zu vergebenden Rollen steht.",
                member,
            )
        except discord.HTTPException as exc:
            logger.error("Fehler beim Vergeben der Rollen an %s: %s", member, exc)

    # ------------------------------------------------------------------ #
    # Willkommensnachricht
    # ------------------------------------------------------------------ #


class WelcomeImageCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_dir = Path(__file__).resolve().parent.parent
        self.asset_dir = self.base_dir / "assets"

    def get_welcome_channel(self, guild: discord.Guild) -> discord.abc.GuildChannel | None:
        channel = guild.get_channel(WELCOME_CHANNEL_ID)
        if channel is not None:
            return channel
        return guild.system_channel

    def create_welcome_image(
        self,
        avatar_bytes: bytes,
        username: str,
        background_path: str | None = None,
        font_path: str | None = None,
    ) -> io.BytesIO:
        if background_path is None:
            background_file = self.asset_dir / "background.png"
            if background_file.exists():
                background_path = str(background_file)
            elif (self.asset_dir / "image.png").exists():
                background_path = str(self.asset_dir / "image.png")

        if background_path and os.path.exists(background_path):
            background = Image.open(background_path).convert("RGBA")
        else:
            background = Image.new("RGBA", (1200, 600), (18, 18, 28, 255))
            draw_bg = ImageDraw.Draw(background)
            draw_bg.rounded_rectangle((30, 30, 1170, 570), radius=35, fill=(28, 30, 42, 255))
            draw_bg.rectangle((0, 0, 1200, 90), fill=(0, 255, 255, 80))
            draw_bg.rectangle((0, 510, 1200, 600), fill=(255, 0, 255, 60))

        draw = ImageDraw.Draw(background)
        _, bg_height = background.size

        avatar_image = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar_size = 200
        avatar_image = avatar_image.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)

        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar_image.putalpha(mask)

        border_size = 216
        avatar_with_border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(avatar_with_border)
        border_draw.ellipse((0, 0, border_size, border_size), fill=(0, 255, 255, 255))

        offset = (border_size - avatar_size) // 2
        avatar_with_border.paste(avatar_image, (offset, offset), avatar_image)

        avatar_x = 80
        avatar_y = (bg_height - border_size) // 2
        background.paste(avatar_with_border, (avatar_x, avatar_y), avatar_with_border)

        # Reihenfolge: expliziter Pfad -> mitgelieferte DejaVu-Fonts (immer im Repo
        # vorhanden, funktionieren plattformunabhaengig) -> gaengige System-Fonts als
        # letzter Versuch -> PIL-Default-Bitmap-Font (siehe load_font()).
        shared_font_dir = self.base_dir / "assets" / "fonts"
        font_candidates = []
        if font_path and os.path.exists(font_path):
            font_candidates.append(font_path)

        font_candidates.extend([
            str(shared_font_dir / "DejaVuSans-Bold.ttf"),
            str(shared_font_dir / "DejaVuSans.ttf"),
            r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ])

        def load_font(size: int):
            for candidate in font_candidates:
                try:
                    return ImageFont.truetype(candidate, size)
                except OSError:
                    continue
            return ImageFont.load_default()

        font_title = load_font(60)
        font_welcome = load_font(38)
        font_subtitle = load_font(30)
        font_text = load_font(30)

        text_x = avatar_x + border_size + 60

        draw.text((text_x, avatar_y), username, font=font_title, fill=(0, 255, 255))
        draw.text((text_x, avatar_y + 80), "HERZLICH WILLKOMMEN", font=font_welcome, fill=(255, 0, 255))
        draw.text((text_x, avatar_y + 130), "Bei Zen Arcade", font=font_subtitle, fill=(0, 255, 255))

        greeting = f"Wir freuen uns, dich hier zu haben!\n"
        draw.text((text_x, avatar_y + 190), greeting, font=font_text, fill=(230, 230, 230))

        buffer = io.BytesIO()
        background.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        channel = self.get_welcome_channel(member.guild)
        if not channel:
            logger.warning("Kein Willkommenskanal für %s gefunden (system_channel oder %s).", member, WELCOME_CHANNEL_ID)
            return

        avatar_bytes = await member.display_avatar.replace(size=256, format="png").read()
        image_buffer = await asyncio.to_thread(self.create_welcome_image, avatar_bytes, member.display_name)
        file = discord.File(fp=image_buffer, filename="welcome.png")

        await channel.send(file=file)

async def setup(bot: commands.Bot):
    await bot.add_cog(Onboarding(bot))
    await bot.add_cog(WelcomeImageCog(bot))
    