import discord
import os
from datetime import datetime
from typing import Optional

from .config import cfg

_TRANSCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "transcripts")


async def get_or_create_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True),
    }
    for cat in guild.categories:
        if cat.name == name:
            if cat.overwrites_for(guild.default_role).view_channel is not False:
                await cat.edit(overwrites=overwrites)
            return cat
    return await guild.create_category(name, overwrites=overwrites)


async def get_ticket_category(guild: discord.Guild) -> discord.CategoryChannel:
    cat_id = cfg.get("ticket_category_id", "")
    if not cat_id:
        raise ValueError("ticket_category_id ist nicht in der config.json gesetzt.")
    category = guild.get_channel(int(cat_id))
    if category is None or not isinstance(category, discord.CategoryChannel):
        raise ValueError(f"Kategorie mit ID {cat_id} nicht gefunden.")

    support_roles = await get_support_roles(guild)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_messages=True),
    }
    for role in support_roles:
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True,
            read_message_history=True, manage_messages=True,
        )

    needs_update = (
        category.overwrites_for(guild.default_role).view_channel is not False
        or any(category.overwrites_for(r).view_channel is not True for r in support_roles)
    )
    if needs_update:
        await category.edit(overwrites=overwrites)

    return category


def is_support(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    support_ids = {int(rid) for rid in cfg.get("support_role_ids", [])}
    return any(r.id in support_ids for r in member.roles)


async def get_support_roles(guild: discord.Guild) -> list[discord.Role]:
    roles = []
    for rid in cfg.get("support_role_ids", []):
        role = guild.get_role(int(rid))
        if role:
            roles.append(role)
    return roles


async def create_transcript(channel: discord.TextChannel) -> str:
    messages = [msg async for msg in channel.history(limit=500, oldest_first=True)]

    rows = []
    for msg in messages:
        ts          = msg.created_at.strftime("%d.%m.%Y %H:%M")
        author      = discord.utils.escape_markdown(msg.author.display_name)
        content     = discord.utils.escape_markdown(msg.content) if msg.content else ""
        attachments = " ".join(
            f'<a href="{a.url}" target="_blank">[📎 {a.filename}]</a>'
            for a in msg.attachments
        )
        rows.append(
            f'<div class="msg">'
            f'<span class="ts">{ts}</span>'
            f'<span class="author">{author}</span>'
            f'<span class="content">{content} {attachments}</span>'
            f'</div>'
        )

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>Transkript – {channel.name}</title>
  <style>
    *  {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #e0e0e0;
           max-width: 860px; margin: 40px auto; padding: 20px; }}
    h1   {{ color: #7289da; font-size: 1.4rem; margin-bottom: 4px; }}
    .meta {{ color: #888; font-size: .85rem; margin-bottom: 20px; }}
    .msg {{ display: grid; grid-template-columns: 130px 160px 1fr;
            gap: 8px; padding: 8px 12px; border-radius: 6px;
            border-left: 3px solid #7289da; margin: 5px 0;
            background: #16213e; font-size: .9rem; }}
    .ts     {{ color: #666; white-space: nowrap; }}
    .author {{ font-weight: 600; color: #99aab5; }}
    .content {{ word-break: break-word; }}
    a {{ color: #7289da; }}
  </style>
</head>
<body>
  <h1>🎫 Ticket Transkript – #{channel.name}</h1>
  <p class="meta">Erstellt am {datetime.utcnow().strftime('%d.%m.%Y um %H:%M')} UTC
     &nbsp;|&nbsp; {len(messages)} Nachrichten</p>
  {''.join(rows)}
</body>
</html>"""

    os.makedirs(_TRANSCRIPTS_DIR, exist_ok=True)
    filename = os.path.join(_TRANSCRIPTS_DIR, f"transcript-{channel.name}.html")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    return filename


def cleanup_transcript(path: str):
    if os.path.exists(path):
        os.remove(path)


async def send_log(guild: discord.Guild, embed: discord.Embed,
                   file: Optional[discord.File] = None):
    log_id = cfg.get("log_channel_id")
    if not log_id:
        return
    channel = guild.get_channel(int(log_id))
    if channel:
        await channel.send(embed=embed, file=file)


def log_embed(title: str, color: str, **fields) -> discord.Embed:
    e = discord.Embed(
        title=title,
        color=discord.Color.from_str(color),
        timestamp=datetime.utcnow(),
    )
    for name, value in fields.items():
        e.add_field(name=name, value=str(value), inline=True)
    return e
