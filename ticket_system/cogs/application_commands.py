import discord
from discord.ext import commands
from discord import app_commands

from ..views.application_views import BewerbungModal, app_db


class ApplicationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ticket-bewerbung", description="Reiche eine Team-Bewerbung ein")
    async def bewerbung(self, interaction: discord.Interaction):
        for aid, adata in app_db.all().items():
            if (str(adata.get("user_id")) == str(interaction.user.id)
                    and str(adata.get("guild_id")) == str(interaction.guild.id)
                    and adata.get("status") == "open"):
                ch = interaction.guild.get_channel(int(adata["channel_id"]))
                if ch is None:
                    app_db.update(aid, {"status": "closed"})
                    continue
                return await interaction.response.send_message(
                    f"❌  Du hast bereits eine offene Bewerbung: {ch.mention}",
                    ephemeral=True,
                )
        await interaction.response.send_modal(BewerbungModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(ApplicationCog(bot))
