import asyncio
import os
from datetime import datetime
from typing import Optional

import discord

from ..utils.config   import cfg
from ..utils.database import TicketDatabase
from ..utils.helpers  import (
    get_ticket_category, get_support_roles,
    is_support, send_log, log_embed,
)

app_db = TicketDatabase(os.path.join(os.path.dirname(__file__), "..", "data", "applications.json"))


class BewerbungModal(discord.ui.Modal, title="Bewerbung für unser Team"):
    ingame_name = discord.ui.TextInput(
        label="Name / Nickname",
        placeholder="Dein Name oder Nickname …",
        max_length=80,
    )
    alter = discord.ui.TextInput(
        label="Alter",
        placeholder="z. B. 18",
        max_length=3,
    )
    erfahrung = discord.ui.TextInput(
        label="Erfahrung als Supporter/Moderator?",
        placeholder="Ja/Nein – wenn ja: wie lange und wo?",
        style=discord.TextStyle.paragraph,
        max_length=500,
    )
    aktivitaet = discord.ui.TextInput(
        label="Aktivität",
        placeholder="Wie oft bist du online? (täglich / wöchentlich)",
        max_length=200,
    )
    warum = discord.ui.TextInput(
        label="Warum sollten wir dich nehmen?",
        placeholder="Überzeuge uns …",
        style=discord.TextStyle.paragraph,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild  = interaction.guild
        user   = interaction.user
        num    = app_db.next_id()

        category = await get_ticket_category(guild)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, manage_channels=True, manage_messages=True,
            ),
        }
        channel = await guild.create_text_channel(
            name=f"bewerbung-{num:04d}-{user.name[:10].lower()}",
            category=category,
            overwrites=overwrites,
            topic=f"Bewerbung #{num:04d} | {user}",
        )

        app_db.set(str(num), {
            "channel_id" : str(channel.id),
            "user_id"    : str(user.id),
            "guild_id"   : str(guild.id),
            "ingame_name": self.ingame_name.value,
            "alter"      : self.alter.value,
            "erfahrung"  : self.erfahrung.value,
            "aktivitaet" : self.aktivitaet.value,
            "warum"      : self.warum.value,
            "status"     : "open",
            "created_at" : datetime.utcnow().isoformat(),
            "closed_at"  : None,
            "handled_by" : None,
        })

        embed = discord.Embed(
            title=f"📝  Bewerbung #{num:04d}",
            color=discord.Color.from_str(cfg["colors"]["open"]),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="Bewerber",                        value=user.mention,              inline=True)
        embed.add_field(name="Name / Nickname",                 value=self.ingame_name.value,    inline=True)
        embed.add_field(name="Alter",                           value=self.alter.value,          inline=True)
        embed.add_field(name="Erfahrung als Supporter/Mod?",    value=self.erfahrung.value,      inline=False)
        embed.add_field(name="Aktivität",                       value=self.aktivitaet.value,     inline=False)
        embed.add_field(name="Warum sollten wir dich nehmen?",  value=self.warum.value,          inline=False)
        embed.set_footer(
            text=f"Bewerbung von {user.display_name}",
            icon_url=user.display_avatar.url,
        )

        support_roles = await get_support_roles(guild)
        mentions = " ".join(r.mention for r in support_roles)
        await channel.send(
            content=f"{user.mention} {mentions}".strip(),
            embed=embed,
            view=ApplicationControlView(num),
        )

        await interaction.followup.send(
            embed=discord.Embed(
                title="✅  Bewerbung eingereicht!",
                description=f"Deine Bewerbung wurde erstellt: {channel.mention}",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

        await send_log(guild, log_embed(
            "📝  Neue Bewerbung", cfg["colors"]["open"],
            **{"Bewerbung": f"#{num:04d}", "User": user.mention,
            "Name": self.ingame_name.value},
        ))


class ApplicationControlView(discord.ui.View):
    def __init__(self, app_number: int):
        super().__init__(timeout=None)
        self.app_number = app_number
        for child in self.children:
            child.custom_id = f"{child.custom_id}_{app_number}"

    @discord.ui.button(
        label="Annehmen", style=discord.ButtonStyle.success,
        emoji="✅", custom_id="app_accept",
    )
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button):
        await _handle_application(interaction, self.app_number, accepted=True)

    @discord.ui.button(
        label="Ablehnen", style=discord.ButtonStyle.danger,
        emoji="❌", custom_id="app_reject",
    )
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button):
        await _handle_application(interaction, self.app_number, accepted=False)

    @discord.ui.button(
        label="Schließen", style=discord.ButtonStyle.secondary,
        emoji="🔒", custom_id="app_close",
    )
    async def close(self, interaction: discord.Interaction, _: discord.ui.Button):
        await _handle_application(interaction, self.app_number, accepted=None)


async def _handle_application(
    interaction: discord.Interaction,
    app_number: int,
    accepted: Optional[bool],
):
    if not is_support(interaction.user):
        return await interaction.response.send_message("❌  Keine Berechtigung.", ephemeral=True)

    adata = app_db.get(str(app_number))
    if not adata:
        return await interaction.response.send_message("❌  Bewerbung nicht gefunden.", ephemeral=True)

    if adata.get("status") != "open":
        return await interaction.response.send_message(
            "❌  Diese Bewerbung wurde bereits bearbeitet.", ephemeral=True
        )

    guild         = interaction.guild
    channel       = interaction.channel
    applicant     = guild.get_member(int(adata["user_id"]))
    applicant_ref = applicant.mention if applicant else f'<@{adata["user_id"]}>'

    if accepted is True:
        status     = "accepted"
        color      = cfg["colors"]["open"]
        dm_title   = f"✅  Deine Bewerbung #{app_number:04d} wurde angenommen!"
        result_msg = f"✅  Bewerbung von {applicant_ref} **angenommen** von {interaction.user.mention}."
    elif accepted is False:
        status     = "rejected"
        color      = cfg["colors"]["closed"]
        dm_title   = f"❌  Deine Bewerbung #{app_number:04d} wurde abgelehnt."
        result_msg = f"❌  Bewerbung von {applicant_ref} **abgelehnt** von {interaction.user.mention}."
    else:
        status     = "closed"
        color      = cfg["colors"]["closed"]
        dm_title   = f"🔒  Deine Bewerbung #{app_number:04d} wurde geschlossen."
        result_msg = f"🔒  Bewerbung geschlossen von {interaction.user.mention}."

    app_db.update(str(app_number), {
        "status"    : status,
        "closed_at" : datetime.utcnow().isoformat(),
        "handled_by": str(interaction.user.id),
    })

    if applicant:
        try:
            await applicant.send(embed=discord.Embed(
                title=dm_title,
                description=f"**Server:** {guild.name}",
                color=discord.Color.from_str(color),
                timestamp=datetime.utcnow(),
            ))
        except discord.Forbidden:
            pass
        await channel.set_permissions(applicant, overwrite=None)

    await interaction.response.send_message(
        embed=discord.Embed(
            description=result_msg,
            color=discord.Color.from_str(color),
            timestamp=datetime.utcnow(),
        )
    )

    await interaction.message.edit(view=None)

    await send_log(guild, log_embed(
        f"📝  Bewerbung {status}", color,
        **{
            "Bewerbung"     : f"#{app_number:04d}",
            "Bewerber"      : f"<@{adata['user_id']}>",
            "Bearbeitet von": interaction.user.mention,
        },
    ))

    if accepted is True:
        new_name = channel.name.replace("bewerbung-", "closed-bewerbung-", 1)
        await channel.edit(name=new_name)

        delay = cfg.get("delete_closed_after_seconds", 0)
        if delay > 0:
            await asyncio.sleep(delay)
            try:
                await channel.delete()
            except Exception:
                pass
