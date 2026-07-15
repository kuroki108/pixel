import logging

import discord
from discord.ext import commands

WELCOME_CHANNEL_ID = 1525603628977619056

logger = logging.getLogger("bot.onboarding")

# ---------------------------------------------------------------------- #
# Hier deine Rollen-IDs eintragen, die neue Mitglieder automatisch
# bekommen sollen. Rechtsklick auf eine Rolle in Discord > "ID kopieren"
# (Entwicklermodus muss dafür aktiviert sein: Einstellungen > Erweitert).
#
# Beispiel mit zwei Rollen:
# ROLE_IDS: list[int] = [123456789012345678, 987654321098765432]
# ---------------------------------------------------------------------- #
ROLE_IDS: list[int] = [
    1525603628318982325, #Special
    1525603628298141788, #About me
    1525603628256329917, #Pings 
    1525603628256329909, #Gaming
    1525603628298141789  #Member
]


class Onboarding(commands.Cog):
    """
    Kümmert sich um alles, was beim Beitritt eines neuen Mitglieds passiert:
    - Automatische Rollenvergabe (siehe ROLE_IDS oben)
    - Willkommensnachricht im Server-Channel
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._assign_roles(member)
        await self._send_welcome(member)

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
    async def _send_welcome(self, member: discord.Member) -> None:
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel is None:
            logger.error(
                "Welcome-Channel mit ID %s wurde nicht gefunden.", WELCOME_CHANNEL_ID
            )
            return

        embed = discord.Embed(
            title="Willkommen! 👋",
            description=(
                f"Hey {member.mention}, schön dass du auf "
                f"**{member.guild.name}** gelandet bist!"
            ),
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="Mitglied Nr.", value=str(member.guild.member_count), inline=True
        )
        embed.set_footer(text=f"User-ID: {member.id}")

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            logger.error(
                "Keine Berechtigung, um im Welcome-Channel (%s) zu schreiben.",
                channel,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Onboarding(bot))