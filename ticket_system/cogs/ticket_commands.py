import discord
from discord.ext import commands
from discord import app_commands

from ..utils.database import db
from ..utils.helpers  import is_support
from ..views.ticket_views import _close_ticket


class TicketCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ticket-add", description="User zum aktuellen Ticket hinzufügen")
    @app_commands.describe(member="Der User, der Zugriff erhalten soll")
    async def ticket_add(self, interaction: discord.Interaction, member: discord.Member):
        if not is_support(interaction.user):
            return await interaction.response.send_message("❌  Keine Berechtigung.", ephemeral=True)
        await interaction.channel.set_permissions(
            member, view_channel=True, send_messages=True, read_message_history=True,
        )
        await interaction.response.send_message(f"✅  {member.mention} wurde hinzugefügt.")

    @app_commands.command(name="ticket-remove", description="User aus dem aktuellen Ticket entfernen")
    @app_commands.describe(member="Der User, dem der Zugriff entzogen werden soll")
    async def ticket_remove(self, interaction: discord.Interaction, member: discord.Member):
        if not is_support(interaction.user):
            return await interaction.response.send_message("❌  Keine Berechtigung.", ephemeral=True)
        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(f"✅  {member.mention} wurde entfernt.")

    @app_commands.command(name="ticket-rename", description="Aktuellen Ticket-Kanal umbenennen")
    @app_commands.describe(name="Neuer Name (ohne 'ticket-' Prefix)")
    async def ticket_rename(self, interaction: discord.Interaction, name: str):
        if not is_support(interaction.user):
            return await interaction.response.send_message("❌  Keine Berechtigung.", ephemeral=True)
        safe = name.lower().replace(" ", "-")[:80]
        await interaction.channel.edit(name=f"ticket-{safe}")
        await interaction.response.send_message(f"✅  Umbenannt zu `ticket-{safe}`.")

    @app_commands.command(name="ticket-close", description="Aktuelles Ticket schließen (Support)")
    async def ticket_close(self, interaction: discord.Interaction):
        tdata = next(
            (t for t in db.all().values()
             if str(t.get("channel_id")) == str(interaction.channel.id)),
            None,
        )
        if not tdata:
            return await interaction.response.send_message(
                "❌  Dieser Kanal ist kein Ticket.", ephemeral=True
            )
        is_owner = str(interaction.user.id) == str(tdata["user_id"])
        if not (is_owner or is_support(interaction.user)):
            return await interaction.response.send_message("❌  Keine Berechtigung.", ephemeral=True)
        await _close_ticket(interaction, tdata["ticket_number"])


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketCommands(bot))
