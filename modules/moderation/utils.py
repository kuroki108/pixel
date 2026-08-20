from datetime import datetime, timezone

import discord

from config import MOD_LOG_CHANNEL_ID

CASE_EMOJIS = {"ban": "🔨", "kick": "👢", "timeout": "⏱️", "warn": "⚠️"}
CASE_LABELS = {"ban": "Ban", "kick": "Kick", "timeout": "Timeout", "warn": "Warn"}


def build_case_embed(
    case_id: int,
    case_type: str,
    reason: str,
    created_at: float,
    target: discord.abc.User,
    moderator: discord.abc.User,
) -> discord.Embed:
    emoji = CASE_EMOJIS.get(case_type, "📋")
    label = CASE_LABELS.get(case_type, case_type.title())

    embed = discord.Embed(
        title=f"{emoji} {label} — Case #{case_id}",
        color=discord.Color.orange(),
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Nutzer", value=f"{target.mention} (`{target.id}`)", inline=False)
    embed.add_field(name="Moderator", value=moderator.mention, inline=False)
    embed.add_field(name="Grund", value=reason, inline=False)
    embed.timestamp = datetime.fromtimestamp(created_at, tz=timezone.utc)
    return embed


async def send_log(bot: discord.Client, embed: discord.Embed) -> None:
    """Schickt ein Case-Embed in den Mod-Log-Channel (config.MOD_LOG_CHANNEL_ID)."""
    channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(MOD_LOG_CHANNEL_ID)
        except discord.HTTPException:
            return

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        pass


def check_hierarchy(interaction: discord.Interaction, target: discord.Member) -> str | None:
    actor = interaction.user
    guild = interaction.guild

    if target.id == actor.id:
        return "❌ Du kannst diese Aktion nicht auf dich selbst anwenden."
    if target.id == guild.owner_id:
        return "❌ Der Server-Owner kann nicht moderiert werden."
    if actor.id != guild.owner_id and target.top_role >= actor.top_role:
        return "❌ Du kannst keine User mit gleicher oder höherer Rolle moderieren."
    if target.top_role >= guild.me.top_role:
        return "❌ Meine höchste Rolle steht nicht über der Zielrolle - ich kann das nicht ausführen."
    return None
