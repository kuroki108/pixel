from __future__ import annotations

import discord

import config
from modules.ticket_system import permissions
from modules.ticket_system import ticket_manager
from modules.ticket_system.storage import store
from modules.ticket_system.ticket_manager import TicketLimitReached
from modules.ticket_system.modals import (
    SupporterApplicationModal,
    DesignerApplicationModal,
    EventManagerApplicationModal,
)


# ---------------------------------------------------------------------------
# Panel: Support
# ---------------------------------------------------------------------------
class SupportPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ticket erstellen",
        emoji=config.EMOJI_OPEN_TICKET,
        style=discord.ButtonStyle.primary,
        custom_id="za_open_support",
    )
    async def open_support(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            channel = await ticket_manager.create_ticket(
                guild=interaction.guild, member=interaction.user, ticket_type="support"
            )
        except TicketLimitReached:
            await interaction.followup.send(
                "❌ Du hast bereits ein offenes Support-Ticket. Bitte warte, bis dieses bearbeitet wurde.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🎫 Neues Support-Ticket",
            description=(
                f"Willkommen {interaction.user.mention}!\n\n"
                "Bitte beschreibe dein Anliegen so genau wie möglich. "
                "Ein Teammitglied meldet sich in Kürze bei dir."
            ),
            color=config.EMBED_COLOR,
            timestamp=discord.utils.utcnow(),
        )
        await channel.send(content=interaction.user.mention, embed=embed, view=TicketControlView())
        await interaction.followup.send(f"✅ Dein Ticket wurde erstellt: {channel.mention}", ephemeral=True)


# ---------------------------------------------------------------------------
# Panel: Bewerbungen
# ---------------------------------------------------------------------------
class ApplicationPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Supporter",
        emoji=config.EMOJI_SUPPORTER,
        style=discord.ButtonStyle.primary,
        custom_id="za_open_app_supporter",
        row=0,
    )
    async def apply_supporter(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(SupporterApplicationModal())

    @discord.ui.button(
        label="Designer",
        emoji=config.EMOJI_DESIGNER,
        style=discord.ButtonStyle.primary,
        custom_id="za_open_app_designer",
        row=0,
    )
    async def apply_designer(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(DesignerApplicationModal())

    @discord.ui.button(
        label="Event Manager",
        emoji=config.EMOJI_EVENTMANAGER,
        style=discord.ButtonStyle.primary,
        custom_id="za_open_app_eventmanager",
        row=0,
    )
    async def apply_eventmanager(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(EventManagerApplicationModal())


# ---------------------------------------------------------------------------
# Nutzerauswahl für Add/Remove (kurzlebige, ephemere Hilfs-Views)
# ---------------------------------------------------------------------------
class _AddUserSelectView(discord.ui.View):
    def __init__(self, ticket_channel_id: int) -> None:
        super().__init__(timeout=60)
        self.ticket_channel_id = ticket_channel_id

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Nutzer auswählen...")
    async def select_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect) -> None:
        target = select.values[0]
        ticket = await store.get_ticket(self.ticket_channel_id)
        if not ticket:
            await interaction.response.edit_message(content="❌ Ticket wurde nicht gefunden.", view=None)
            return
        ok = await ticket_manager.add_user(interaction.channel, target, ticket)
        if not ok:
            await interaction.response.edit_message(
                content=f"⚠️ {target.mention} ist bereits im Ticket oder ist der Ersteller.", view=None
            )
            return
        await interaction.response.edit_message(content=f"✅ {target.mention} wurde hinzugefügt.", view=None)
        await interaction.channel.send(f"➕ {target.mention} wurde von {interaction.user.mention} zum Ticket hinzugefügt.")


class _RemoveUserSelectView(discord.ui.View):
    def __init__(self, ticket_channel_id: int) -> None:
        super().__init__(timeout=60)
        self.ticket_channel_id = ticket_channel_id

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Nutzer auswählen...")
    async def select_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect) -> None:
        target = select.values[0]
        ticket = await store.get_ticket(self.ticket_channel_id)
        if not ticket:
            await interaction.response.edit_message(content="❌ Ticket wurde nicht gefunden.", view=None)
            return
        ok = await ticket_manager.remove_user(interaction.channel, target, ticket)
        if not ok:
            await interaction.response.edit_message(
                content=f"⚠️ {target.mention} kann nicht entfernt werden (nicht im Ticket oder Ersteller).",
                view=None,
            )
            return
        await interaction.response.edit_message(content=f"✅ {target.mention} wurde entfernt.", view=None)
        await interaction.channel.send(f"➖ {target.mention} wurde von {interaction.user.mention} aus dem Ticket entfernt.")


class _ConfirmDeleteView(discord.ui.View):
    def __init__(self, ticket_channel_id: int) -> None:
        super().__init__(timeout=30)
        self.ticket_channel_id = ticket_channel_id

    @discord.ui.button(label="Ja, endgültig löschen", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await store.get_ticket(self.ticket_channel_id)
        if not ticket:
            await interaction.response.edit_message(content="❌ Ticket wurde nicht gefunden.", view=None)
            return
        await interaction.response.edit_message(content="🗑️ Ticket wird gelöscht...", view=None)
        await ticket_manager.delete_ticket(interaction.channel, interaction.user, ticket)

    @discord.ui.button(label="Abbrechen", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="Abgebrochen.", view=None)


# ---------------------------------------------------------------------------
# Ticket-Steuerung: wird in jedes Ticket gepostet
# ---------------------------------------------------------------------------
class TicketControlView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    async def _get_ticket_or_warn(self, interaction: discord.Interaction):
        ticket = await store.get_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ Dies ist kein aktiver Ticket-Kanal.", ephemeral=True)
            return None
        return ticket

    # -- Claim -------------------------------------------------------------
    @discord.ui.button(label="Claim", emoji=config.EMOJI_CLAIM, style=discord.ButtonStyle.secondary, custom_id="za_claim", row=0)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await self._get_ticket_or_warn(interaction)
        if not ticket:
            return
        if not permissions.is_staff_for_ticket_type(interaction.user, ticket.type):
            await interaction.response.send_message("❌ Nur Teammitglieder können Tickets claimen.", ephemeral=True)
            return
        if ticket.claimed_by:
            await interaction.response.send_message(f"⚠️ Dieses Ticket wurde bereits von <@{ticket.claimed_by}> übernommen.", ephemeral=True)
            return
        await ticket_manager.claim_ticket(interaction.channel, interaction.user, ticket)
        await interaction.response.send_message(f"🙋 {interaction.user.mention} hat dieses Ticket übernommen.")

    # -- Close ---------------------------------------------------------------
    @discord.ui.button(label="Close", emoji=config.EMOJI_CLOSE, style=discord.ButtonStyle.secondary, custom_id="za_close", row=0)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await self._get_ticket_or_warn(interaction)
        if not ticket:
            return
        is_opener = interaction.user.id == ticket.opener_id
        if not is_opener and not permissions.is_staff_for_ticket_type(interaction.user, ticket.type):
            await interaction.response.send_message("❌ Du hast keine Berechtigung, dieses Ticket zu schließen.", ephemeral=True)
            return
        if ticket.closed:
            await interaction.response.send_message("⚠️ Dieses Ticket ist bereits geschlossen.", ephemeral=True)
            return
        await ticket_manager.close_ticket(interaction.channel, interaction.user, ticket)
        await interaction.response.send_message(
            f"🔒 Ticket wurde von {interaction.user.mention} geschlossen. Nur das Team kann jetzt noch schreiben."
        )

    # -- Transcript ------------------------------------------------------------
    @discord.ui.button(label="Transcript", emoji=config.EMOJI_TRANSCRIPT, style=discord.ButtonStyle.secondary, custom_id="za_transcript", row=0)
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await self._get_ticket_or_warn(interaction)
        if not ticket:
            return
        is_opener = interaction.user.id == ticket.opener_id
        if not is_opener and not permissions.is_staff_for_ticket_type(interaction.user, ticket.type):
            await interaction.response.send_message("❌ Du hast keine Berechtigung, das Transcript abzurufen.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        file = await ticket_manager.generate_transcript_file(interaction.channel)
        await interaction.followup.send("📄 Hier ist das Transcript:", file=file, ephemeral=True)

    # -- Add user ------------------------------------------------------------
    @discord.ui.button(label="Add User", emoji=config.EMOJI_ADD_USER, style=discord.ButtonStyle.success, custom_id="za_adduser", row=1)
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await self._get_ticket_or_warn(interaction)
        if not ticket:
            return
        if not permissions.is_staff_for_ticket_type(interaction.user, ticket.type):
            await interaction.response.send_message("❌ Nur Teammitglieder können Nutzer hinzufügen.", ephemeral=True)
            return
        await interaction.response.send_message(
            "Wähle den Nutzer aus, der hinzugefügt werden soll:", view=_AddUserSelectView(interaction.channel.id), ephemeral=True
        )

    # -- Remove user ---------------------------------------------------------
    @discord.ui.button(label="Remove User", emoji=config.EMOJI_REMOVE_USER, style=discord.ButtonStyle.secondary, custom_id="za_removeuser", row=1)
    async def remove_user(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await self._get_ticket_or_warn(interaction)
        if not ticket:
            return
        if not permissions.is_staff_for_ticket_type(interaction.user, ticket.type):
            await interaction.response.send_message("❌ Nur Teammitglieder können Nutzer entfernen.", ephemeral=True)
            return
        if not ticket.added_users:
            await interaction.response.send_message("⚠️ Es wurden bisher keine zusätzlichen Nutzer hinzugefügt.", ephemeral=True)
            return
        await interaction.response.send_message(
            "Wähle den Nutzer aus, der entfernt werden soll:", view=_RemoveUserSelectView(interaction.channel.id), ephemeral=True
        )

    # -- Delete ----------------------------------------------------------------
    @discord.ui.button(label="Delete", emoji=config.EMOJI_DELETE, style=discord.ButtonStyle.danger, custom_id="za_delete", row=1)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = await self._get_ticket_or_warn(interaction)
        if not ticket:
            return
        if not permissions.is_staff_for_ticket_type(interaction.user, ticket.type):
            await interaction.response.send_message("❌ Nur Teammitglieder können Tickets löschen.", ephemeral=True)
            return
        await interaction.response.send_message(
            "⚠️ Bist du sicher? Das Ticket wird inkl. Transcript unwiderruflich gelöscht.",
            view=_ConfirmDeleteView(interaction.channel.id),
            ephemeral=True,
        )


def all_persistent_views() -> list[discord.ui.View]:
    """Wird beim Bot-Start verwendet, um alle persistenten Views zu registrieren."""
    return [SupportPanelView(), ApplicationPanelView(), TicketControlView()]
