from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import config
from modules.database import Database
from modules.free_games.deal import Deal
from modules.free_games.embeds import build_embed, build_view

_EXAMPLE_DEAL = Deal(
    deal_id="example",
    source="Epic Games",
    title="ARK: Survival Evolved",
    description=(
        "Gestrandet an der Küste einer geheimnisvollen Insel musst du lernen zu überleben. "
        "Nutze deine Fähigkeiten, um die urzeitlichen Kreaturen der Insel zu töten oder zu "
        "zähmen, und triff auf andere Spieler, um zu überleben, zu dominieren … und zu entkommen!"
    ),
    store_url="https://store.epicgames.com/de/p/ark-survival-evolved",
    launcher_url="com.epicgames.launcher://store/product/ark-survival-evolved",
    image_url=None,
    original_price_cents=1679,
    current_price_cents=0,
    currency="EUR",
    end_date=datetime(2026, 8, 23, tzinfo=timezone.utc),
    rating="80/100",
    is_free=True,
)


class ToolsCog(commands.Cog):
    """Hilfsbefehle: Vorschau-Embed testen und Bot-Status prüfen."""

    def __init__(self, bot: commands.Bot, db: Database):
        self.bot = bot
        self.db = db

    @app_commands.command(name="test", description="Postet eine Beispiel-Vorschau des Angebots-Embeds in diesem Kanal")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def test(self, interaction: discord.Interaction):
        embed = build_embed(_EXAMPLE_DEAL)
        view = build_view(_EXAMPLE_DEAL)
        await interaction.response.send_message(
            content="Vorschau (Beispieldaten):", embed=embed, view=view, ephemeral=False
        )

    @app_commands.command(name="status", description="Zeigt den Status des Bots und die Einstellungen dieses Servers")
    @app_commands.guild_only()
    async def status(self, interaction: discord.Interaction):
        settings = await self.db.get_free_games_settings(interaction.guild_id)
        channel = interaction.guild.get_channel(config.FREEGAMES_CHANNEL_ID)
        role = interaction.guild.get_role(config.FREEGAMES_PING_ROLE_ID) if config.FREEGAMES_PING_ROLE_ID else None
        last_check = await self.db.get_free_games_state("last_check")

        embed = discord.Embed(title="Bot-Status", color=0x3498DB)
        embed.add_field(
            name="Letzter Check",
            value=f"<t:{int(datetime.fromisoformat(last_check).timestamp())}:R>" if last_check else "noch kein Check erfolgt",
            inline=False,
        )
        embed.add_field(name="Prüfintervall", value=f"alle {config.FREEGAMES_CHECK_INTERVAL_MINUTES} Minuten", inline=False)
        embed.add_field(name="Kanal", value=channel.mention if channel else "❌ nicht gesetzt", inline=True)
        embed.add_field(name="Ping-Rolle", value=role.mention if role else "keine", inline=True)
        embed.add_field(
            name="Modus",
            value="Nur kostenlose Spiele" if settings.only_free else "Auch reduzierte Angebote",
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ToolsCog(bot, bot.db))
