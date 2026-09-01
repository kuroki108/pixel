import discord
from discord import app_commands
from discord.ext import commands

import config
from modules.database import Database


class SettingsCog(commands.Cog):
    """Server-Einstellungen für den Freegames-Bot."""

    settings_group = app_commands.Group(
        name="settings",
        description="Einstellungen für automatische Freegame-Benachrichtigungen",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    def __init__(self, bot: commands.Bot, db: Database):
        self.bot = bot
        self.db = db

    @settings_group.command(name="modus", description="Nur echte Freegames oder auch reduzierte Angebote posten")
    @app_commands.choices(
        modus=[
            app_commands.Choice(name="Nur kostenlose Spiele (0 €)", value="nur_free"),
            app_commands.Choice(name="Auch reduzierte Angebote", value="auch_rabatte"),
        ]
    )
    async def modus(self, interaction: discord.Interaction, modus: app_commands.Choice[str]):
        only_free = modus.value == "nur_free"
        await self.db.set_free_games_only_free(interaction.guild_id, only_free)
        await interaction.response.send_message(f"✅ Modus geändert: **{modus.name}**.", ephemeral=True)

    @settings_group.command(name="anzeigen", description="Zeigt die aktuellen Einstellungen für diesen Server")
    async def show(self, interaction: discord.Interaction):
        settings = await self.db.get_free_games_settings(interaction.guild_id)
        channel = interaction.guild.get_channel(config.FREEGAMES_CHANNEL_ID)
        role = interaction.guild.get_role(config.FREEGAMES_PING_ROLE_ID) if config.FREEGAMES_PING_ROLE_ID else None

        embed = discord.Embed(title="Aktuelle Einstellungen", color=0x2ECC71)
        embed.add_field(
            name="Kanal",
            value=f"{channel.mention} (fest in config.py hinterlegt)" if channel else "❌ Kanal-ID aus config.py nicht auf diesem Server gefunden",
            inline=False,
        )
        embed.add_field(name="Ping-Rolle", value=f"{role.mention} (fest in config.py hinterlegt)" if role else "keine", inline=False)
        embed.add_field(
            name="Modus",
            value="Nur kostenlose Spiele" if settings.only_free else "Auch reduzierte Angebote",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot, bot.db))
