import logging
import discord

from discord.ext import commands

from config import WELCOME_CHANNEL_ID
from config import ONBOARDING_ROLE_IDS as ROLE_IDS

logger = logging.getLogger("bot.onboarding")


class Onboarding(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._assign_roles(member)

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


class WelcomeImageCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_welcome_channel(self, guild: discord.Guild) -> discord.abc.GuildChannel | None:
        channel = guild.get_channel(WELCOME_CHANNEL_ID)
        if channel is not None:
            return channel
        return guild.system_channel

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        channel = self.get_welcome_channel(member.guild)
        if not channel:
            logger.warning("Kein Willkommenskanal für %s gefunden (system_channel oder %s).", member, WELCOME_CHANNEL_ID)
            return

        embed = discord.Embed(
            title="Herzlich willkommen in der Arcade!",
            description=f"Schön, dass du da bist, {member.mention}!",
            color=discord.Color.teal(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Du bist Mitglied Nummer {member.guild.member_count}.")

        await channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Onboarding(bot))
    await bot.add_cog(WelcomeImageCog(bot))