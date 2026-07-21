import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# KONFIGURATION - hier deine echten Channel-IDs eintragen
# ---------------------------------------------------------------------------
MESSAGE_LOG_CHANNEL_ID = 1525603629929599154   # edits / deletes
MEMBER_LOG_CHANNEL_ID  = 1529211146748428449   # join / leave / kick
MOD_LOG_CHANNEL_ID     = 1529211176809136208   # ban / unban / timeout / mute


COLOR_EDIT   = discord.Color.orange()
COLOR_DELETE = discord.Color.red()
COLOR_JOIN   = discord.Color.green()
COLOR_LEAVE  = discord.Color.dark_grey()
COLOR_KICK   = discord.Color.gold()
COLOR_BAN    = discord.Color.dark_red()
COLOR_UNBAN  = discord.Color.blurple()


def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def truncate(text: str, limit: int = 1024) -> str:
    if not text:
        return "*(leer / kein Inhalt)*"
    return text if len(text) <= limit else text[: limit - 3] + "..."


class LoggingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -----------------------------------------------------------------
    # Helper: passenden Channel holen
    # -----------------------------------------------------------------
    def _channel(self, channel_id: int):
        return self.bot.get_channel(channel_id)

    async def _send(self, channel_id: int, embed: discord.Embed):
        channel = self._channel(channel_id)
        if channel is None:
            print(f"[LoggingCog] WARNUNG: Channel {channel_id} nicht gefunden.")
            return
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            print(f"[LoggingCog] Keine Berechtigung fuer Channel {channel_id}.")

    # -----------------------------------------------------------------
    # NACHRICHTEN: Edit / Delete
    # -----------------------------------------------------------------
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return

        embed = discord.Embed(
            title="🗑️ Nachricht gelöscht",
            color=COLOR_DELETE,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Autor", value=f"{message.author} ({message.author.id})", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        embed.add_field(name="Inhalt", value=truncate(message.content), inline=False)
        if message.attachments:
            embed.add_field(
                name="Anhänge",
                value="\n".join(a.url for a in message.attachments),
                inline=False,
            )
        embed.set_footer(text=f"Message-ID: {message.id}")
        await self._send(MESSAGE_LOG_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return
        if before.content == after.content:
            # Nur echte Text-Aenderungen loggen (kein Embed-Unfurl-Trigger etc.)
            return

        embed = discord.Embed(
            title="✏️ Nachricht bearbeitet",
            color=COLOR_EDIT,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Autor", value=f"{before.author} ({before.author.id})", inline=False)
        embed.add_field(name="Channel", value=before.channel.mention, inline=False)
        embed.add_field(name="Vorher", value=truncate(before.content), inline=False)
        embed.add_field(name="Nachher", value=truncate(after.content), inline=False)
        embed.add_field(name="Sprung", value=f"[Zur Nachricht]({after.jump_url})", inline=False)
        embed.set_footer(text=f"Message-ID: {before.id}")
        await self._send(MESSAGE_LOG_CHANNEL_ID, embed)

    # -----------------------------------------------------------------
    # MEMBER: Join / Leave / Kick
    # -----------------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(
            title="📥 Mitglied beigetreten",
            color=COLOR_JOIN,
            timestamp=datetime.now(timezone.utc),
        )
        account_age = datetime.now(timezone.utc) - member.created_at
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Account erstellt", value=f"{member.created_at:%Y-%m-%d} ({account_age.days} Tage alt)", inline=False)
        embed.add_field(name="Mitgliederzahl", value=str(member.guild.member_count), inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self._send(MEMBER_LOG_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Kurze Verzoegerung, damit der Audit-Log-Eintrag (falls Kick) sicher existiert
        await asyncio.sleep(1.0)

        kicked_by = None
        reason = None

        if member.guild.me.guild_permissions.view_audit_log:
            try:
                async for entry in member.guild.audit_logs(
                    limit=5, action=discord.AuditLogAction.kick
                ):
                    if entry.target and entry.target.id == member.id:
                        delta = datetime.now(timezone.utc) - entry.created_at
                        if delta.total_seconds() < 5:
                            kicked_by = entry.user
                            reason = entry.reason
                            break
            except discord.Forbidden:
                pass

        if kicked_by:
            embed = discord.Embed(
                title="👢 Mitglied gekickt",
                color=COLOR_KICK,
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
            embed.add_field(name="Von", value=f"{kicked_by} ({kicked_by.id})", inline=False)
            embed.add_field(name="Grund", value=reason or "*(kein Grund angegeben)*", inline=False)
            await self._send(MOD_LOG_CHANNEL_ID, embed)
        else:
            embed = discord.Embed(
                title="📤 Mitglied verlassen",
                color=COLOR_LEAVE,
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
            joined = member.joined_at
            if joined:
                embed.add_field(name="Server beigetreten am", value=f"{joined:%Y-%m-%d %H:%M UTC}", inline=False)
            await self._send(MEMBER_LOG_CHANNEL_ID, embed)

    # -----------------------------------------------------------------
    # MODERATION: Ban / Unban
    # -----------------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        banned_by = None
        reason = None
        if guild.me.guild_permissions.view_audit_log:
            try:
                async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
                    if entry.target and entry.target.id == user.id:
                        banned_by = entry.user
                        reason = entry.reason
                        break
            except discord.Forbidden:
                pass

        embed = discord.Embed(
            title="🔨 Mitglied gebannt",
            color=COLOR_BAN,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        if banned_by:
            embed.add_field(name="Von", value=f"{banned_by} ({banned_by.id})", inline=False)
        embed.add_field(name="Grund", value=reason or "*(kein Grund angegeben)*", inline=False)
        await self._send(MOD_LOG_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        unbanned_by = None
        if guild.me.guild_permissions.view_audit_log:
            try:
                async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
                    if entry.target and entry.target.id == user.id:
                        unbanned_by = entry.user
                        break
            except discord.Forbidden:
                pass

        embed = discord.Embed(
            title="🔓 Bann aufgehoben",
            color=COLOR_UNBAN,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        if unbanned_by:
            embed.add_field(name="Von", value=f"{unbanned_by} ({unbanned_by.id})", inline=False)
        await self._send(MOD_LOG_CHANNEL_ID, embed)





async def setup(bot: commands.Bot):
    await bot.add_cog(LoggingCog(bot))