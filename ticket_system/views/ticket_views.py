import asyncio
import discord
from datetime import datetime

from ..utils.config   import cfg
from ..utils.database import db
from ..utils.helpers  import (
    get_ticket_category, get_support_roles, is_support,
    create_transcript, cleanup_transcript, send_log, log_embed,
)


class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=cat["label"],
                description=cat["description"],
                emoji=cat["emoji"],
                value=cat["value"],
            )
            for cat in cfg["ticket_categories"]
        ]
        super().__init__(
            placeholder="📂  Wähle eine Kategorie …",
            options=options,
            custom_id="ticket_category_select",
        )

    async def callback(self, interaction: discord.Interaction):
        cat_data = next(
            c for c in cfg["ticket_categories"] if c["value"] == self.values[0]
        )
        await interaction.response.send_modal(TicketCreateModal(cat_data))


class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())


class TicketCreateModal(discord.ui.Modal):
    subject = discord.ui.TextInput(
        label="Betreff",
        placeholder="Kurze Beschreibung deines Anliegens …",
        max_length=100,
    )
    description = discord.ui.TextInput(
        label="Beschreibung",
        placeholder="Beschreibe dein Problem so genau wie möglich …",
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    def __init__(self, cat_data: dict):
        super().__init__(title=f"Ticket – {cat_data['label']}")
        self.cat_data = cat_data

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild  = interaction.guild
        user   = interaction.user
        num    = db.next_id()

        category = await get_ticket_category(guild)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, attach_files=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, manage_channels=True, manage_messages=True,
            ),
        }
        channel  = await guild.create_text_channel(
            name=f"ticket-{num:04d}-{user.name[:10].lower()}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket #{num:04d} | {user} | {self.cat_data['label']}",
        )

        db.set(str(num), {
            "channel_id"    : str(channel.id),
            "user_id"       : str(user.id),
            "guild_id"      : str(guild.id),
            "category"      : self.cat_data["value"],
            "category_label": self.cat_data["label"],
            "subject"       : self.subject.value,
            "description"   : self.description.value,
            "status"        : "open",
            "claimed_by"    : None,
            "created_at"    : datetime.utcnow().isoformat(),
            "closed_at"     : None,
            "ticket_number" : num,
        })

        embed = discord.Embed(
            title=f"{self.cat_data['emoji']}  Ticket #{num:04d} – {self.cat_data['label']}",
            description=(
                f"Willkommen {user.mention}!\n\n"
                f"**Betreff:** {self.subject.value}\n\n"
                f"**Beschreibung:**\n{self.description.value}\n\n"
                f"Unser Support-Team kümmert sich so bald wie möglich um dich.\n"
                f"Bitte teile alle relevanten Informationen mit."
            ),
            color=discord.Color.from_str(cfg["colors"]["open"]),
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(
            text=f"Erstellt von {user.display_name}",
            icon_url=user.display_avatar.url,
        )

        support_roles = await get_support_roles(guild)
        mentions = " ".join(r.mention for r in support_roles)
        await channel.send(
            content=f"{user.mention} {mentions}".strip(),
            embed=embed,
            view=TicketControlView(num),
        )

        await interaction.followup.send(
            embed=discord.Embed(
                title="✅  Ticket erstellt!",
                description=f"Dein Ticket wurde geöffnet: {channel.mention}",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

        await send_log(guild, log_embed(
            "📥  Neues Ticket", cfg["colors"]["open"],
            **{"Ticket": f"#{num:04d}", "User": user.mention,
               "Kategorie": self.cat_data["label"], "Betreff": self.subject.value},
        ))


class TicketControlView(discord.ui.View):
    def __init__(self, ticket_number: int):
        super().__init__(timeout=None)
        self.ticket_number = ticket_number
        for child in self.children:
            child.custom_id = f"{child.custom_id}_{ticket_number}"

    @discord.ui.button(
        label="Schließen", style=discord.ButtonStyle.danger,
        emoji="🔒", custom_id="ticket_close",
    )
    async def close_ticket(self, interaction: discord.Interaction, _: discord.ui.Button):
        tdata = db.get(str(self.ticket_number))
        if not tdata:
            return await interaction.response.send_message("❌  Ticket nicht gefunden.", ephemeral=True)
        is_owner = str(interaction.user.id) == str(tdata["user_id"])
        if not (is_owner or is_support(interaction.user)):
            return await interaction.response.send_message("❌  Keine Berechtigung.", ephemeral=True)
        await interaction.response.send_message(
            "⚠️  Ticket wirklich schließen?",
            view=ConfirmCloseView(self.ticket_number),
            ephemeral=True,
        )

    @discord.ui.button(
        label="User hinzufügen", style=discord.ButtonStyle.secondary,
        emoji="➕", custom_id="ticket_add_user",
    )
    async def add_user(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not is_support(interaction.user):
            return await interaction.response.send_message("❌  Keine Berechtigung.", ephemeral=True)
        await interaction.response.send_modal(AddUserModal(self.ticket_number))


class ConfirmCloseView(discord.ui.View):
    def __init__(self, ticket_number: int):
        super().__init__(timeout=30)
        self.ticket_number = ticket_number

    @discord.ui.button(label="Ja, schließen", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, _: discord.ui.Button):
        await _close_ticket(interaction, self.ticket_number)
        self.stop()

    @discord.ui.button(label="Abbrechen", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_message("Abgebrochen.", ephemeral=True)
        self.stop()


class AddUserModal(discord.ui.Modal, title="User hinzufügen"):
    user_id = discord.ui.TextInput(
        label="User-ID oder @Erwähnung",
        placeholder="z. B.  123456789012345678",
        max_length=30,
    )

    def __init__(self, ticket_number: int):
        super().__init__()
        self.ticket_number = ticket_number

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.user_id.value.strip().lstrip("<@!").rstrip(">")
        try:
            member = interaction.guild.get_member(int(raw)) \
                     or await interaction.guild.fetch_member(int(raw))
        except Exception:
            return await interaction.response.send_message("❌  User nicht gefunden.", ephemeral=True)
        await interaction.channel.set_permissions(
            member,
            view_channel=True, send_messages=True, read_message_history=True,
        )
        await interaction.response.send_message(f"✅  {member.mention} wurde hinzugefügt.")



async def _close_ticket(interaction: discord.Interaction, ticket_number: int):
    tdata = db.get(str(ticket_number))
    if not tdata:
        return await interaction.response.send_message("❌  Ticket nicht gefunden.", ephemeral=True)

    await interaction.response.defer()

    guild   = interaction.guild
    channel = interaction.channel

    transcript = await create_transcript(channel)

    owner = guild.get_member(int(tdata["user_id"]))
    if owner:
        try:
            dm_embed = discord.Embed(
                title=f"🔒  Ticket #{ticket_number:04d} wurde geschlossen",
                description=(
                    f"**Server:** {guild.name}\n"
                    f"**Kategorie:** {tdata['category_label']}\n"
                    f"**Betreff:** {tdata['subject']}\n\n"
                    f"Das Transkript liegt im Anhang."
                ),
                color=discord.Color.from_str(cfg["colors"]["closed"]),
                timestamp=datetime.utcnow(),
            )
            await owner.send(embed=dm_embed, file=discord.File(transcript))
        except discord.Forbidden:
            pass

    db.update(str(ticket_number), {
        "status"   : "closed",
        "closed_at": datetime.utcnow().isoformat(),
    })

    if owner:
        await channel.set_permissions(owner, overwrite=None)
    await channel.edit(name=channel.name.replace("ticket-", "closed-", 1))

    await interaction.followup.send(
        embed=discord.Embed(
            title="🔒  Ticket geschlossen",
            description=f"Geschlossen von {interaction.user.mention}.",
            color=discord.Color.from_str(cfg["colors"]["closed"]),
            timestamp=datetime.utcnow(),
        ),
    )

    le = log_embed(
        "🔒  Ticket geschlossen", cfg["colors"]["closed"],
        **{
            "Ticket"         : f"#{ticket_number:04d}",
            "Erstellt von"   : f"<@{tdata['user_id']}>",
            "Geschlossen von": interaction.user.mention,
            "Kategorie"      : tdata["category_label"],
            "Betreff"        : tdata["subject"],
        },
    )
    await send_log(guild, le, file=discord.File(transcript))
    cleanup_transcript(transcript)

    delay = cfg.get("delete_closed_after_seconds", 0)
    if delay > 0:
        await asyncio.sleep(delay)
        try:
            await channel.delete()
        except Exception:
            pass
