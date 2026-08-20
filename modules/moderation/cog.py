from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from modules.moderation import utils


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log_case(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        case_type: str,
        reason: str,
    ) -> discord.Embed:
        case_id, created_at = await self.bot.db.add_mod_case(
            interaction.guild_id, user.id, interaction.user.id, case_type, reason
        )
        return utils.build_case_embed(case_id, case_type, reason, created_at, user, interaction.user)

    # ---------------------------------------------------------- /ban
    @app_commands.command(name="ban", description="Bannt einen User vom Server")
    @app_commands.describe(
        user="Der zu bannende User",
        reason="Grund für den Bann",
        delete_days="Nachrichten der letzten X Tage löschen (0-7)",
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = None,
        delete_days: app_commands.Range[int, 0, 7] = 0,
    ):
        error = utils.check_hierarchy(interaction, user)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        reason = reason or "Kein Grund angegeben"
        await interaction.guild.ban(user, reason=reason, delete_message_seconds=delete_days * 86400)

        embed = await self._log_case(interaction, user, "ban", reason)
        await interaction.response.send_message(embed=embed)
        await utils.send_log(self.bot, embed)

    # ---------------------------------------------------------- /kick
    @app_commands.command(name="kick", description="Kickt einen User vom Server")
    @app_commands.describe(user="Der zu kickende User", reason="Grund für den Kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        error = utils.check_hierarchy(interaction, user)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        reason = reason or "Kein Grund angegeben"
        await interaction.guild.kick(user, reason=reason)

        embed = await self._log_case(interaction, user, "kick", reason)
        await interaction.response.send_message(embed=embed)
        await utils.send_log(self.bot, embed)

    # ------------------------------------------------------- /timeout
    @app_commands.command(name="timeout", description="Timeoutet einen User für eine bestimmte Dauer")
    @app_commands.describe(
        user="Der zu timeoutende User",
        minuten="Dauer in Minuten (max. 40320 = 28 Tage, Discord-Limit)",
        reason="Grund für den Timeout",
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        minuten: app_commands.Range[int, 1, 40320],
        reason: str = None,
    ):
        error = utils.check_hierarchy(interaction, user)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        reason = reason or "Kein Grund angegeben"
        await user.timeout(timedelta(minutes=minuten), reason=reason)

        embed = await self._log_case(interaction, user, "timeout", reason)
        embed.add_field(name="Dauer", value=f"{minuten} Minuten", inline=False)
        await interaction.response.send_message(embed=embed)
        await utils.send_log(self.bot, embed)

    # ---------------------------------------------------------- /warn
    @app_commands.command(name="warn", description="Verwarnt einen User")
    @app_commands.describe(user="Der zu verwarnende User", reason="Grund für die Verwarnung")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        error = utils.check_hierarchy(interaction, user)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        reason = reason or "Kein Grund angegeben"
        embed = await self._log_case(interaction, user, "warn", reason)
        await interaction.response.send_message(embed=embed)
        await utils.send_log(self.bot, embed)

        try:
            await user.send(f"Du wurdest auf **{interaction.guild.name}** verwarnt.\nGrund: {reason}")
        except discord.Forbidden:
            pass  # DMs geschlossen - kein Problem, Warn ist trotzdem gespeichert

    # ------------------------------------------------------- /user info
    user_group = app_commands.Group(name="user", description="User-bezogene Befehle")

    @user_group.command(name="info", description="Zeigt Account- und Moderationsinfos zu einem User")
    @app_commands.describe(user="Der User, dessen Infos angezeigt werden sollen")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def user_info(self, interaction: discord.Interaction, user: discord.Member):
        stats = await self.bot.db.get_user_mod_case_counts(interaction.guild_id, user.id)
        cases = (await self.bot.db.get_user_mod_cases(interaction.guild_id, user.id))[:3]

        embed = discord.Embed(title=f"👤 {user.display_name}", color=discord.Color.blurple())
        embed.set_thumbnail(url=user.display_avatar.url)

        joined = user.joined_at.strftime("%d.%m.%Y") if user.joined_at else "Unbekannt"
        embed.add_field(
            name="Account",
            value=f"Created: {user.created_at.strftime('%d.%m.%Y')}\nJoined: {joined}",
            inline=False,
        )
        embed.add_field(
            name="Moderation",
            value=(
                f"Warnings: {stats['warn']}\n"
                f"Timeouts: {stats['timeout']}\n"
                f"Kicks: {stats['kick']}\n"
                f"Bans: {stats['ban']}"
            ),
            inline=False,
        )

        if cases:
            lines = [
                f"#{case_id} {utils.CASE_LABELS.get(case_type, case_type.title())} - {reason}"
                for case_id, case_type, reason, _created_at in cases
            ]
            embed.add_field(name="Recent Cases", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Recent Cases", value="Keine Einträge", inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
