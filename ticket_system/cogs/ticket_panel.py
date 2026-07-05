import discord
from discord.ext import commands
from discord import app_commands

from ..utils.config       import cfg
from ..views.ticket_views import TicketCategoryView


class TicketPanel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="ticket-panel",
        description="Sendet das Ticket-Panel in diesen Kanal (nur Admins)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=cfg["panel"]["title"],
            description=cfg["panel"]["description"],
            color=discord.Color.from_str(cfg["colors"]["panel"]),
        )
        embed.set_footer(text=cfg["panel"]["footer"])
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        await interaction.channel.send(embed=embed, view=TicketCategoryView())
        await interaction.response.send_message("✅  Panel wurde gesendet!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketPanel(bot))
