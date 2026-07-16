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
            title="𝐖𝐈𝐋𝐋𝐊𝐎𝐌𝐌𝐄𝐍! 🪻",
            description=(
                f"Hey {member.mention}, 𝗌𝖼𝗁ö𝗇, 𝖽𝖺𝗌𝗌 𝖽𝗎 𝗍𝖾𝗂𝗅 𝗎𝗇𝗌𝖾𝗋𝖾𝗋 **{member.guild.name}** 𝖼𝗈𝗆𝗆𝗎𝗇𝗂𝗍𝗒 𝗀𝖾𝗐𝗈𝗋𝖽𝖾𝗇 𝖻𝗂𝗌𝗍!"
                f"S𝖼𝗁𝖺𝗎 𝗓𝗎𝖾𝗋𝗌𝗍 𝗂𝗇 #𝗋𝖾𝗀𝖾𝗅𝗇 𝗎𝗇𝖽 𝗁𝗈𝗅 𝖽𝗂𝗋 𝗂𝗇 #𝗌𝖾𝗅𝖿-𝗋𝗈𝗅𝖾𝗌ᝰᐟ 𝖽𝖾𝗂𝗇𝖾 𝗋𝗈𝗅𝗅𝖾𝗇. D𝖺𝗇𝖺𝖼𝗁 𝗄𝖺𝗇𝗇𝗌𝗍 𝖽𝗎 𝗎𝗇𝗌 𝗂𝗇 #𝗏𝗈𝗋𝗌𝗍𝖾𝗅𝗅𝗎𝗇𝗀 𝖾𝗍𝗐𝖺𝗌 𝗎̈𝖻𝖾𝗋 𝖽𝗂𝖼𝗁 𝖾𝗋𝗓𝖺̈𝗁𝗅𝖾𝗇 𝗎𝗇𝖽 𝖽𝗂𝗋𝖾𝗄𝗍 𝗆𝗂𝗍 𝖽𝖾𝗋 𝖼𝗈𝗆𝗆𝗎𝗇𝗂𝗍𝗒 𝗌𝖼𝗁𝗋𝖾𝗂𝖻𝖾𝗇. \n" 
                f"W𝗂𝗋 𝗐ü𝗇𝗌𝖼𝗁𝖾𝗇 𝖽𝗂𝗋 𝗏𝗂𝖾𝗅 s𝗉𝖺ß, 𝗏𝗂𝖾𝗅𝖾 𝗇𝖾𝗎𝖾 𝖻𝖾𝗄𝖺𝗇𝗇𝗍𝗌𝖼𝗁𝖺𝖿𝗍𝖾𝗇 𝗎𝗇𝖽 𝖾𝗂𝗇𝖾 𝗍𝗈𝗅𝗅𝖾 𝗓𝖾𝗂𝗍 𝖻𝖾𝗂 𝗎𝗇𝗌."
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
    