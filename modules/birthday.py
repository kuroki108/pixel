import asyncio
import json
from datetime import date, datetime, time, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks

# TODO: echte Channel-ID eintragen, in der der tägliche Geburtstags-Reminder gepostet wird.
BIRTHDAY_CHANNEL_ID = 1525603629321683007

# Uhrzeit (UTC), zu der täglich auf Geburtstage geprüft wird.
REMINDER_TIME_UTC = time(hour=8, minute=0, tzinfo=timezone.utc)
# Uhrzeit (UTC), zu der die /kalender-Embeds täglich neu sortiert werden.
CALENDAR_REFRESH_TIME_UTC = time(hour=0, minute=5, tzinfo=timezone.utc)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "birthdays.json"
CALENDAR_MESSAGES_PATH = Path(__file__).resolve().parent.parent / "data" / "birthday_calendar_messages.json"


class Birthday(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()
        self._calendar_lock = asyncio.Lock()
        self.reminder_task.start()
        self.calendar_refresh_task.start()

    def cog_unload(self) -> None:
        self.reminder_task.cancel()
        self.calendar_refresh_task.cancel()

    # ---------------------------------------------------------------
    # Persistenz (JSON-Datei: user_id -> {"day": int, "month": int, "year": int|None})
    # ---------------------------------------------------------------

    async def _load(self) -> dict[str, dict]:
        def _read() -> dict[str, dict]:
            if not DATA_PATH.exists():
                return {}
            try:
                return json.loads(DATA_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}

        return await asyncio.to_thread(_read)

    async def _save(self, data: dict[str, dict]) -> None:
        def _write() -> None:
            DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = DATA_PATH.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp_path.replace(DATA_PATH)

        async with self._lock:
            await asyncio.to_thread(_write)

    # ---------------------------------------------------------------
    # Persistenz der live aktualisierten /kalender-Nachrichten
    # (channel_id -> message_id, eine live Nachricht pro Channel)
    # ---------------------------------------------------------------

    async def _load_calendar_messages(self) -> dict[str, int]:
        def _read() -> dict[str, int]:
            if not CALENDAR_MESSAGES_PATH.exists():
                return {}
            try:
                return json.loads(CALENDAR_MESSAGES_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}

        return await asyncio.to_thread(_read)

    async def _save_calendar_messages(self, refs: dict[str, int]) -> None:
        def _write() -> None:
            CALENDAR_MESSAGES_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = CALENDAR_MESSAGES_PATH.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(refs), encoding="utf-8")
            tmp_path.replace(CALENDAR_MESSAGES_PATH)

        async with self._calendar_lock:
            await asyncio.to_thread(_write)

    async def _register_calendar_message(self, channel_id: int, message_id: int) -> None:
        refs = await self._load_calendar_messages()
        refs[str(channel_id)] = message_id
        await self._save_calendar_messages(refs)

    async def _refresh_calendar_messages(self) -> None:
        refs = await self._load_calendar_messages()
        if not refs:
            return

        changed = False
        for channel_id_str, message_id in list(refs.items()):
            channel = self.bot.get_channel(int(channel_id_str))
            if channel is None:
                del refs[channel_id_str]
                changed = True
                continue

            embed = await self._build_kalender_embed(channel.guild)
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                del refs[channel_id_str]
                changed = True

        if changed:
            await self._save_calendar_messages(refs)

    # ---------------------------------------------------------------
    # /birthday set|remove
    # ---------------------------------------------------------------

    birthday_group = app_commands.Group(
        name="birthday", description="Verwalte deinen Geburtstag."
    )

    @birthday_group.command(name="set", description="Trägt deinen Geburtstag ein.")
    @app_commands.describe(
        tag="Tag (1-31)", monat="Monat (1-12)", jahr="Optional: Geburtsjahr"
    )
    async def birthday_set(
        self,
        interaction: discord.Interaction,
        tag: app_commands.Range[int, 1, 31],
        monat: app_commands.Range[int, 1, 12],
        jahr: app_commands.Range[int, 1900, 2100] | None = None,
    ) -> None:
        try:
            # 2004 als Referenzjahr (Schaltjahr), um auch den 29. Februar zuzulassen
            date(jahr or 2004, monat, tag)
        except ValueError:
            await interaction.response.send_message(
                "❌ Das ist kein gültiges Datum.", ephemeral=True
            )
            return

        data = await self._load()
        data[str(interaction.user.id)] = {"day": tag, "month": monat, "year": jahr}
        await self._save(data)
        await self._refresh_calendar_messages()

        wann = f"{tag:02d}.{monat:02d}." + (f"{jahr}" if jahr else "")
        await interaction.response.send_message(
            f"✅ Dein Geburtstag wurde auf **{wann}** gesetzt.", ephemeral=True
        )

    @birthday_group.command(name="remove", description="Entfernt deinen eingetragenen Geburtstag.")
    async def birthday_remove(self, interaction: discord.Interaction) -> None:
        data = await self._load()
        key = str(interaction.user.id)
        if key not in data:
            await interaction.response.send_message(
                "Du hast noch keinen Geburtstag eingetragen.", ephemeral=True
            )
            return
        del data[key]
        await self._save(data)
        await self._refresh_calendar_messages()
        await interaction.response.send_message("✅ Dein Geburtstag wurde entfernt.", ephemeral=True)

    # ---------------------------------------------------------------
    # /kalender
    # ---------------------------------------------------------------

    async def _build_kalender_embed(self, guild: discord.Guild | None) -> discord.Embed:
        data = await self._load()
        if not data:
            return discord.Embed(
                title="🎂 Geburtstagskalender",
                description="Es sind noch keine Geburtstage eingetragen.",
                color=discord.Color.from_rgb(0, 229, 255),
            )

        today = date.today()

        def days_until(entry: dict) -> int:
            next_occurrence = date(today.year, entry["month"], entry["day"])
            if next_occurrence < today:
                next_occurrence = date(today.year + 1, entry["month"], entry["day"])
            return (next_occurrence - today).days

        entries = []
        for user_id, entry in data.items():
            try:
                order = days_until(entry)
            except ValueError:
                continue  # z. B. 29. Februar in einem Nicht-Schaltjahr, wird trotzdem einmal im Jahr gefeiert
            entries.append((order, user_id, entry))
        entries.sort(key=lambda item: item[0])

        lines = []
        for order, user_id, entry in entries:
            member = guild.get_member(int(user_id)) if guild else None
            name = member.display_name if member else f"Nutzer {user_id}"
            wann = f"{entry['day']:02d}.{entry['month']:02d}."
            if entry.get("year"):
                wann += f"{entry['year']}"
            marker = " 🎂" if order == 0 else ""
            lines.append(f"**{wann}** — {name}{marker}")

        embed = discord.Embed(
            title="🎂 Geburtstagskalender",
            description="\n".join(lines),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        embed.set_footer(text="Aktualisiert sich automatisch täglich sowie bei Änderungen")
        return embed

    @app_commands.command(name="kalender", description="Zeigt alle eingetragenen Geburtstage (aktualisiert sich automatisch).")
    async def kalender(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        embed = await self._build_kalender_embed(interaction.guild)
        await interaction.followup.send(embed=embed)

        message = await interaction.original_response()
        await self._register_calendar_message(message.channel.id, message.id)

    # ---------------------------------------------------------------
    # Täglicher Reminder
    # ---------------------------------------------------------------

    @tasks.loop(time=REMINDER_TIME_UTC)
    async def reminder_task(self) -> None:
        data = await self._load()
        if not data:
            return

        today = date.today()
        birthday_user_ids = [
            user_id for user_id, entry in data.items()
            if entry["day"] == today.day and entry["month"] == today.month
        ]
        if not birthday_user_ids:
            return

        channel = self.bot.get_channel(BIRTHDAY_CHANNEL_ID)
        if channel is None:
            return

        for user_id in birthday_user_ids:
            entry = data[user_id]
            age_text = ""
            if entry.get("year"):
                age_text = f" und wird heute **{today.year - entry['year']}** Jahre alt"
            embed = discord.Embed(
                title="🎉 Alles Gute zum Geburtstag!",
                description=f"<@{user_id}> hat heute Geburtstag{age_text}! 🎂🥳",
                color=discord.Color.from_rgb(255, 0, 170),
            )
            try:
                await channel.send(content=f"<@{user_id}>", embed=embed)
            except discord.HTTPException:
                pass

        await self._refresh_calendar_messages()

    @reminder_task.before_loop
    async def before_reminder_task(self) -> None:
        await self.bot.wait_until_ready()

    @tasks.loop(time=CALENDAR_REFRESH_TIME_UTC)
    async def calendar_refresh_task(self) -> None:
        await self._refresh_calendar_messages()

    @calendar_refresh_task.before_loop
    async def before_calendar_refresh_task(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Birthday(bot))
