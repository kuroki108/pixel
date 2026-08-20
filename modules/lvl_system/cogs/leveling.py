from __future__ import annotations

import logging
import random
import time
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import NO_TEXT_XP_CHANNEL_IDS, NO_VOICE_XP_CHANNEL_IDS
from modules.database import Database
from modules.lvl_system.utils.leveling_math import add_xp, xp_for_next_level
from modules.lvl_system.utils.rank_card import generate_rank_card

log = logging.getLogger("leveling")

LEVEL_ROLE_CHOICES_LIMIT = 25  # Discord-Limit für Autocomplete-Vorschläge
DEFAULT_LEVELUP_TEXT = "{mention} hat soeben Level {level} erreicht! 🎉"

VOICE_XP_CAP_MINUTES = 90  # 1,5h Voice-XP pro Tag
VOICE_XP_CAP_COOLDOWN = timedelta(hours=24)


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db
        # (guild_id, user_id) -> {"minutes": int, "capped": bool, "reset_at": datetime | None}
        # In-Memory only: Cap wird bei Bot-Neustart zurückgesetzt.
        self.voice_xp_tracker: dict[tuple[int, int], dict] = {}
        self.voice_xp_task.start()

    def cog_unload(self) -> None:
        self.voice_xp_task.cancel()

    # ---------------------------------------------------------------
    # Text-XP
    # ---------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        if not message.content and not message.attachments:
            return
        if message.channel.id in NO_TEXT_XP_CHANNEL_IDS:
            return

        guild_id = message.guild.id
        user_id = message.author.id
        config = await self.db.get_guild_config(guild_id)
        stats = await self.db.get_user(guild_id, user_id)

        now = int(time.time())
        if now - stats.last_message_ts < config.cooldown_seconds:
            return  # Cooldown aktiv, kein XP

        gained = random.randint(config.xp_min, config.xp_max)
        new_xp, new_level, levelups = add_xp(stats.xp, stats.level, gained)
        new_total = stats.total_xp + gained

        await self.db.set_user_xp(guild_id, user_id, new_xp, new_total, new_level)
        await self.db.set_last_message_ts(guild_id, user_id, now)

        if levelups > 0:
            await self._handle_levelup(message.guild, message.author, new_level, message.channel)

    # ---------------------------------------------------------------
    # Voice-XP: alle 60s Bonus für aktuell verbundene, nicht-taube/AFK Nutzer
    # ---------------------------------------------------------------

    @tasks.loop(seconds=60)
    async def voice_xp_task(self) -> None:
        for guild in self.bot.guilds:
            config = await self.db.get_guild_config(guild.id)
            if not config.voice_xp_enabled or config.voice_xp_per_min <= 0:
                continue

            afk_channel_id = guild.afk_channel.id if guild.afk_channel else None

            for channel in guild.voice_channels:
                if channel.id == afk_channel_id or channel.id in NO_VOICE_XP_CHANNEL_IDS:
                    continue
                members = [
                    m for m in channel.members
                    if not m.bot and not m.voice.self_deaf and not m.voice.deaf
                ]
                if len(members) < 2:
                    continue  # kein XP wenn alleine im Channel (verhindert AFK-Farming)

                for member in members:
                    key = (guild.id, member.id)
                    now = discord.utils.utcnow()
                    entry = self.voice_xp_tracker.get(key)
                    if entry and entry["capped"]:
                        if now < entry["reset_at"]:
                            continue  # 1,5h/24h-Cap aktiv, kein XP
                        entry = None  # Cap-Fenster abgelaufen, neu starten

                    if entry is None:
                        entry = {"minutes": 0, "capped": False, "reset_at": None}

                    entry["minutes"] += 1
                    if entry["minutes"] >= VOICE_XP_CAP_MINUTES:
                        entry["capped"] = True
                        entry["reset_at"] = now + VOICE_XP_CAP_COOLDOWN
                    self.voice_xp_tracker[key] = entry

                    stats = await self.db.get_user(guild.id, member.id)
                    new_xp, new_level, levelups = add_xp(stats.xp, stats.level, config.voice_xp_per_min)
                    new_total = stats.total_xp + config.voice_xp_per_min
                    await self.db.set_user_xp(guild.id, member.id, new_xp, new_total, new_level)

                    if levelups > 0:
                        target_channel = None
                        if config.levelup_channel_id:
                            target_channel = guild.get_channel(config.levelup_channel_id)
                        await self._handle_levelup(guild, member, new_level, target_channel)

    @voice_xp_task.before_loop
    async def before_voice_xp_task(self) -> None:
        await self.bot.wait_until_ready()

    # ---------------------------------------------------------------
    # Levelup-Handling (Nachricht + Rollenvergabe)
    # ---------------------------------------------------------------

    async def _handle_levelup(
        self,
        guild: discord.Guild,
        member: discord.Member,
        new_level: int,
        fallback_channel: discord.abc.Messageable | None,
    ) -> None:
        config = await self.db.get_guild_config(guild.id)

        channel: discord.abc.Messageable | None = fallback_channel
        if config.levelup_channel_id:
            configured = guild.get_channel(config.levelup_channel_id)
            if configured is not None:
                channel = configured

        if channel is not None:
            text = DEFAULT_LEVELUP_TEXT.format(
                mention=member.mention,
                level=new_level,
                user=member.display_name,
            )
            embed = discord.Embed(
                title="Level Up!",
                description=text,
                color=discord.Color.from_rgb(255, 0, 170),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                log.warning("Konnte Levelup-Nachricht in Guild %s nicht senden", guild.id)

        await self._apply_level_roles(guild, member, new_level)

    async def _apply_level_roles(
        self, guild: discord.Guild, member: discord.Member, new_level: int
    ) -> None:
        level_roles = await self.db.get_level_roles(guild.id)
        if not level_roles:
            return

        eligible = [(lv, rid) for lv, rid in level_roles if lv <= new_level]
        if not eligible:
            return

        me = guild.me
        roles_to_add: list[discord.Role] = []
        roles_to_remove: list[discord.Role] = []

        highest_level, highest_role_id = max(eligible, key=lambda pair: pair[0])
        highest_role = guild.get_role(highest_role_id)
        if highest_role and highest_role not in member.roles:
            roles_to_add.append(highest_role)
        for lv, role_id in level_roles:
            if role_id == highest_role_id:
                continue
            role = guild.get_role(role_id)
            if role and role in member.roles:
                roles_to_remove.append(role)

        try:
            if roles_to_add and me and me.guild_permissions.manage_roles:
                await member.add_roles(*roles_to_add, reason="Level-Belohnung")
            if roles_to_remove and me and me.guild_permissions.manage_roles:
                await member.remove_roles(*roles_to_remove, reason="Level-Belohnung ersetzt")
        except discord.Forbidden:
            log.warning("Fehlende Rechte für Rollenvergabe in Guild %s", guild.id)

    # ---------------------------------------------------------------
    # /rank
    # ---------------------------------------------------------------

    @app_commands.command(name="rank", description="Zeigt deine (oder eine fremde) Rank-Card an.")
    @app_commands.describe(user="Optional: Rank-Card eines anderen Mitglieds anzeigen")
    async def rank(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        member = user or interaction.user
        if member.bot:
            await interaction.response.send_message("Bots haben keine Rank-Card. 🤖", ephemeral=True)
            return

        await interaction.response.defer()

        stats = await self.db.get_user(interaction.guild_id, member.id)
        rank = await self.db.get_rank(interaction.guild_id, member.id)

        avatar_asset = member.display_avatar.replace(size=256, format="png")
        avatar_bytes = await avatar_asset.read()

        tag = f"#{member.discriminator}" if member.discriminator != "0" else ""

        buf = generate_rank_card(
            username=member.display_name,
            discriminator_tag=tag,
            avatar_bytes=avatar_bytes,
            level=stats.level,
            xp_in_level=stats.xp,
            rank=rank,
            total_xp=stats.total_xp,
        )
        file = discord.File(buf, filename="rank.png")
        await interaction.followup.send(file=file)

    # ---------------------------------------------------------------
    # /leaderboard
    # ---------------------------------------------------------------

    @app_commands.command(name="leaderboard", description="Zeigt die Top-Mitglieder nach XP.")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        offset = 0
        entries = await self.db.get_leaderboard(interaction.guild_id, limit=10, offset=offset)

        if not entries:
            await interaction.followup.send("Noch keine XP-Daten auf dieser Seite.")
            return

        lines = []
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for idx, stats in enumerate(entries, start=offset + 1):
            member = interaction.guild.get_member(stats.user_id)
            name = member.display_name if member else f"Nutzer {stats.user_id}"
            prefix = medals.get(idx, f"`#{idx}`")
            lines.append(f"{prefix} **{name}** — Level {stats.level} ({stats.total_xp:,} XP)".replace(",", "."))

        embed = discord.Embed(
            title=f"🏆 Leaderboard — {interaction.guild.name}",
            description="\n".join(lines),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        embed.set_footer(text="Seite 1")
        await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------------
    # Admin: /xp add|remove|set|reset
    # ---------------------------------------------------------------

    xp_group = app_commands.Group(
        name="xp", description="XP eines Mitglieds verwalten (Admin).",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @xp_group.command(name="add", description="Fügt einem Mitglied XP hinzu.")
    async def xp_add(self, interaction: discord.Interaction, user: discord.Member, betrag: app_commands.Range[int, 1, 1_000_000]) -> None:
        stats = await self.db.get_user(interaction.guild_id, user.id)
        new_xp, new_level, levelups = add_xp(stats.xp, stats.level, betrag)
        new_total = stats.total_xp + betrag
        await self.db.set_user_xp(interaction.guild_id, user.id, new_xp, new_total, new_level)
        if levelups > 0:
            await self._apply_level_roles(interaction.guild, user, new_level)
        await interaction.response.send_message(f"✅ {betrag:,} XP zu {user.mention} hinzugefügt (jetzt Level {new_level}).".replace(",", "."), ephemeral=True)

    @xp_group.command(name="remove", description="Zieht einem Mitglied XP ab.")
    async def xp_remove(self, interaction: discord.Interaction, user: discord.Member, betrag: app_commands.Range[int, 1, 1_000_000]) -> None:
        stats = await self.db.get_user(interaction.guild_id, user.id)
        new_total = max(0, stats.total_xp - betrag)
        # Level/XP im Level aus neuer Gesamt-XP neu berechnen
        level = 0
        remaining = new_total
        while remaining >= xp_for_next_level(level):
            remaining -= xp_for_next_level(level)
            level += 1
        await self.db.set_user_xp(interaction.guild_id, user.id, remaining, new_total, level)
        await interaction.response.send_message(f"✅ {betrag:,} XP von {user.mention} abgezogen (jetzt Level {level}).".replace(",", "."), ephemeral=True)

    @xp_group.command(name="set", description="Setzt die Gesamt-XP eines Mitglieds fest.")
    async def xp_set(self, interaction: discord.Interaction, user: discord.Member, betrag: app_commands.Range[int, 0, 100_000_000]) -> None:
        level = 0
        remaining = betrag
        while remaining >= xp_for_next_level(level):
            remaining -= xp_for_next_level(level)
            level += 1
        await self.db.set_user_xp(interaction.guild_id, user.id, remaining, betrag, level)
        await interaction.response.send_message(f"✅ XP von {user.mention} auf {betrag:,} gesetzt (Level {level}).".replace(",", "."), ephemeral=True)

    @xp_group.command(name="reset", description="Setzt die XP eines Mitglieds auf 0 zurück.")
    async def xp_reset(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await self.db.reset_user(interaction.guild_id, user.id)
        await interaction.response.send_message(f"✅ XP von {user.mention} wurde zurückgesetzt.", ephemeral=True)

    @xp_group.command(name="reset-server", description="⚠️ Setzt die XP ALLER Mitglieder auf diesem Server zurück.")
    async def xp_reset_server(self, interaction: discord.Interaction, bestaetigen: bool) -> None:
        if not bestaetigen:
            await interaction.response.send_message(
                "Setze `bestaetigen: True`, um wirklich ALLE XP-Daten dieses Servers zu löschen.",
                ephemeral=True,
            )
            return
        await self.db.reset_guild(interaction.guild_id)
        await interaction.response.send_message("⚠️ Alle XP-Daten dieses Servers wurden gelöscht.", ephemeral=True)

    # ---------------------------------------------------------------
    # Admin: /level-config
    # ---------------------------------------------------------------

    config_group = app_commands.Group(
        name="level-config", description="Leveling-Einstellungen dieses Servers (Admin).",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @config_group.command(name="show", description="Zeigt die aktuelle Leveling-Konfiguration.")
    async def config_show(self, interaction: discord.Interaction) -> None:
        c = await self.db.get_guild_config(interaction.guild_id)
        channel = interaction.guild.get_channel(c.levelup_channel_id) if c.levelup_channel_id else None
        embed = discord.Embed(title="⚙️ Leveling-Konfiguration", color=discord.Color.from_rgb(0, 229, 255))
        embed.add_field(name="Text-XP pro Nachricht", value=f"{c.xp_min}–{c.xp_max}", inline=True)
        embed.add_field(name="Cooldown", value=f"{c.cooldown_seconds}s", inline=True)
        embed.add_field(name="Voice-XP", value=f"{c.voice_xp_per_min}/min" if c.voice_xp_enabled else "deaktiviert", inline=True)
        embed.add_field(name="Levelup-Channel", value=channel.mention if channel else "aktueller Channel", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @config_group.command(name="text-xp", description="Setzt XP-Range und Cooldown für Text-Nachrichten.")
    async def config_text_xp(
        self, interaction: discord.Interaction,
        min_xp: app_commands.Range[int, 1, 1000],
        max_xp: app_commands.Range[int, 1, 1000],
        cooldown_sekunden: app_commands.Range[int, 0, 3600],
    ) -> None:
        if min_xp > max_xp:
            await interaction.response.send_message("❌ min_xp darf nicht größer als max_xp sein.", ephemeral=True)
            return
        await self.db.update_guild_config(interaction.guild_id, xp_min=min_xp, xp_max=max_xp, cooldown_seconds=cooldown_sekunden)
        await interaction.response.send_message("✅ Text-XP-Einstellungen aktualisiert.", ephemeral=True)

    @config_group.command(name="voice-xp", description="Konfiguriert XP für Zeit im Voice-Channel.")
    async def config_voice_xp(
        self, interaction: discord.Interaction,
        aktiviert: bool,
        xp_pro_minute: app_commands.Range[int, 0, 1000] = 10,
    ) -> None:
        await self.db.update_guild_config(
            interaction.guild_id, voice_xp_enabled=int(aktiviert), voice_xp_per_min=xp_pro_minute
        )
        await interaction.response.send_message("✅ Voice-XP-Einstellungen aktualisiert.", ephemeral=True)

    @config_group.command(name="levelup-channel", description="Legt fest, wo Levelup-Nachrichten gepostet werden.")
    async def config_levelup_channel(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
        await self.db.update_guild_config(interaction.guild_id, levelup_channel_id=channel.id if channel else None)
        text = f"✅ Levelup-Nachrichten werden jetzt in {channel.mention} gepostet." if channel else "✅ Levelup-Nachrichten werden im jeweiligen Nachrichtenkanal gepostet."
        await interaction.response.send_message(text, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    # app_commands.Group-Attribute eines Cogs werden von add_cog() automatisch
    # im Command-Tree registriert – ein zusätzliches bot.tree.add_command()
    # würde zu "CommandAlreadyRegistered" führen.
    db: Database = bot.db  # type: ignore[attr-defined]
    cog = Leveling(bot, db)
    await bot.add_cog(cog)
