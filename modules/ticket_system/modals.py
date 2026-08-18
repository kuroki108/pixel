from __future__ import annotations

import discord

import config
from modules.ticket_system import ticket_manager
from modules.ticket_system.ticket_manager import TicketLimitReached, TICKET_TYPE_LABELS


async def _finish_application(interaction: discord.Interaction, ticket_type: str, answers: dict[str, str]) -> None:
    from modules.ticket_system.views import TicketControlView  # lokaler Import verhindert Zirkelbezug

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        channel = await ticket_manager.create_ticket(
            guild=interaction.guild,
            member=interaction.user,
            ticket_type=ticket_type,
            answers=answers,
        )
    except TicketLimitReached:
        await interaction.followup.send(
            "❌ Du hast bereits eine offene Bewerbung dieser Art. Bitte warte, bis diese bearbeitet wurde.",
            ephemeral=True,
        )
        return

    desc = "\n".join(f"**{q}**\n{a}" for q, a in answers.items())
    embed = discord.Embed(
        title=f"📋 {TICKET_TYPE_LABELS.get(ticket_type, ticket_type)}",
        description=f"Bewerbung von {interaction.user.mention}\n\n{desc}",
        color=config.EMBED_COLOR,
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    await channel.send(content=interaction.user.mention, embed=embed, view=TicketControlView())
    await interaction.followup.send(f"✅ Deine Bewerbung wurde erstellt: {channel.mention}", ephemeral=True)


class SupporterApplicationModal(discord.ui.Modal, title="Bewerbung: Supporter"):
    alter = discord.ui.TextInput(label="Wie alt bist du?", max_length=10, required=True)
    erfahrung = discord.ui.TextInput(
        label="Hast du Erfahrung als Supporter?", style=discord.TextStyle.paragraph, max_length=500, required=True
    )
    motivation = discord.ui.TextInput(
        label="Warum möchtest du Supporter werden?", style=discord.TextStyle.paragraph, max_length=500, required=True
    )
    verfuegbarkeit = discord.ui.TextInput(label="Wie viel Zeit hast du pro Woche?", max_length=100, required=True)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        answers = {
            "Alter": self.alter.value,
            "Erfahrung als Supporter": self.erfahrung.value,
            "Motivation": self.motivation.value,
            "Verfügbarkeit pro Woche": self.verfuegbarkeit.value,
        }
        await _finish_application(interaction, "application_supporter", answers)