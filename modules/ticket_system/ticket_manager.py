"""
Zentrale Logik für alles rund um Ticket-Kanäle. Wird sowohl von den
Panel-Views (Ticket öffnen) als auch von der Ticket-Control-View
(Claim/Close/Delete/Transcript/Add/Remove) verwendet, damit die
eigentliche Logik nur an einer Stelle steht.
"""

from __future__ import annotations

import io
import re
from typing import Optional

import discord

import config
from modules.ticket_system.storage import TicketData, store
from modules.ticket_system.transcript import build_transcript

# Menschlich lesbare Labels für die Ticket-Typen (u. a. für Embeds/Kanalnamen)
TICKET_TYPE_LABELS = {
    "support": "Support",
    "application_supporter": "Bewerbung - Supporter",
    "application_designer": "Bewerbung - Designer",
    "application_eventmanager": "Bewerbung - Event Manager",
}


def _sanitize(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\-]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name[:20] or "user"


def _category_and_prefix(ticket_type: str) -> tuple[int, str]:
    if ticket_type == "support":
        return config.SUPPORT_CATEGORY_ID, config.SUPPORT_CHANNEL_PREFIX
    return config.APPLICATION_CATEGORY_ID, config.APPLICATION_CHANNEL_PREFIX


def _staff_role_id(ticket_type: str) -> int:
    if ticket_type == "support":
        return config.SUPPORT_STAFF_ROLE_ID
    return config.APPLICATION_STAFF_ROLE_ID


class TicketLimitReached(Exception):
    """Wird ausgelöst, wenn ein Nutzer bereits die maximale Anzahl offener Tickets dieses Typs hat."""


async def create_ticket(
    guild: discord.Guild,
    member: discord.Member,
    ticket_type: str,
    answers: Optional[dict[str, str]] = None,
) -> discord.TextChannel:
    """Erstellt einen neuen Ticket-Kanal inkl. Berechtigungen, Speicherung und Begrüßungsnachricht."""

    # Limit pruefen + Zaehler ziehen: atomar in einem Lock, damit zwei gleichzeitige
    # Ticket-Erstellungen desselben Nutzers das Limit nicht umgehen koennen.
    prefix_for_limit = "application" if ticket_type.startswith("application") else "support"
    max_allowed = (
        config.MAX_OPEN_APPLICATION_TICKETS_PER_USER
        if prefix_for_limit == "application"
        else config.MAX_OPEN_SUPPORT_TICKETS_PER_USER
    )
    counter_key = "application" if prefix_for_limit == "application" else "support"
    number = await store.reserve_ticket_slot(
        member.id, ticket_type if prefix_for_limit == "application" else "support", max_allowed, counter_key
    )
    if number is None:
        raise TicketLimitReached()

    category_id, channel_prefix = _category_and_prefix(ticket_type)
    category = guild.get_channel(category_id) if category_id else None
    staff_role_id = _staff_role_id(ticket_type)
    staff_role = guild.get_role(staff_role_id) if staff_role_id else None
    admin_role = guild.get_role(config.ADMIN_ROLE_ID) if config.ADMIN_ROLE_ID else None

    channel_name = f"{channel_prefix}-{number:04d}-{_sanitize(member.name)}"

    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True, manage_permissions=True, read_message_history=True
        ),
    }
    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, manage_messages=True
        )
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, manage_messages=True
        )

    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        topic=f"Ticket-Typ: {ticket_type} | Ersteller: {member.id} | Geclaimt von: -",
        reason=f"Ticket erstellt von {member} ({member.id})",
    )

    ticket = TicketData(channel_id=channel.id, type=ticket_type, opener_id=member.id, answers=answers or {})
    await store.save_ticket(ticket)

    return channel


async def close_ticket(channel: discord.TextChannel, closer: discord.Member, ticket: TicketData) -> None:
    ticket.closed = True
    await store.save_ticket(ticket)

    guild = channel.guild
    opener = guild.get_member(ticket.opener_id)
    overwrite_targets = [opener] if opener else []
    for uid in ticket.added_users:
        m = guild.get_member(uid)
        if m:
            overwrite_targets.append(m)

    for target in overwrite_targets:
        await channel.set_permissions(target, view_channel=True, send_messages=False, read_message_history=True)

    await channel.edit(topic=f"Ticket-Typ: {ticket.type} | Ersteller: {ticket.opener_id} | Geclaimt von: {ticket.claimed_by or '-'} | GESCHLOSSEN")


async def generate_transcript_file(channel: discord.TextChannel) -> discord.File:
    html_content = await build_transcript(channel)
    buffer = io.BytesIO(html_content.encode("utf-8"))
    return discord.File(buffer, filename=f"transcript-{channel.name}.html")


async def delete_ticket(channel: discord.TextChannel, deleter: discord.Member, ticket: TicketData) -> None:
    log_channel = None
    if config.TRANSCRIPT_LOG_CHANNEL_ID:
        log_channel = channel.guild.get_channel(config.TRANSCRIPT_LOG_CHANNEL_ID)

    if log_channel:
        try:
            file = await generate_transcript_file(channel)
            opener = channel.guild.get_member(ticket.opener_id)
            embed = discord.Embed(
                title="🗑️ Ticket gelöscht",
                description=(
                    f"**Kanal:** #{channel.name}\n"
                    f"**Typ:** {TICKET_TYPE_LABELS.get(ticket.type, ticket.type)}\n"
                    f"**Ersteller:** {opener.mention if opener else ticket.opener_id}\n"
                    f"**Gelöscht von:** {deleter.mention}"
                ),
                color=config.EMBED_COLOR,
                timestamp=discord.utils.utcnow(),
            )
            await log_channel.send(embed=embed, file=file)
        except Exception:
            pass  # Transcript-Fehler soll das Löschen nicht verhindern

    await store.delete_ticket(channel.id)
    await channel.delete(reason=f"Ticket gelöscht von {deleter} ({deleter.id})")


async def claim_ticket(channel: discord.TextChannel, member: discord.Member, ticket: TicketData) -> None:
    ticket.claimed_by = member.id
    await store.save_ticket(ticket)
    await channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True, manage_messages=True)
    await channel.edit(topic=f"Ticket-Typ: {ticket.type} | Ersteller: {ticket.opener_id} | Geclaimt von: {member.id}")


async def add_user(channel: discord.TextChannel, target: discord.Member, ticket: TicketData) -> bool:
    if target.id == ticket.opener_id or target.id in ticket.added_users:
        return False
    ticket.added_users.append(target.id)
    await store.save_ticket(ticket)
    await channel.set_permissions(target, view_channel=True, send_messages=True, read_message_history=True)
    return True


async def remove_user(channel: discord.TextChannel, target: discord.Member, ticket: TicketData) -> bool:
    if target.id == ticket.opener_id:
        return False  # Ersteller kann nicht über "Remove" entfernt werden, nur über Close/Delete
    if target.id not in ticket.added_users:
        return False
    ticket.added_users.remove(target.id)
    await store.save_ticket(ticket)
    await channel.set_permissions(target, overwrite=None)
    return True
