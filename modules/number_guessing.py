import asyncio
import json
import random
import time
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

GUESS_TIME_LIMIT_SECONDS = 120
MAX_ATTEMPTS_FOR_POINT = 7

SCORES_PATH = Path(__file__).resolve().parent.parent / "data" / "number_guessing_scores.json"


class NumberGuessing(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.game: dict | None = None  # es läuft immer nur ein Spiel gleichzeitig (global)
        self.timeout_task: asyncio.Task | None = None
        self._scores_lock = asyncio.Lock()

    def cog_unload(self) -> None:
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()

    # ---------------------------------------------------------------
    # Score-Persistenz (JSON-Datei)
    # ---------------------------------------------------------------

    async def _load_scores(self) -> dict[str, int]:
        def _read() -> dict[str, int]:
            if not SCORES_PATH.exists():
                return {}
            try:
                return json.loads(SCORES_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}

        return await asyncio.to_thread(_read)

    async def _save_scores(self, scores: dict[str, int]) -> None:
        def _write() -> None:
            SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = SCORES_PATH.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(scores, indent=2), encoding="utf-8")
            tmp_path.replace(SCORES_PATH)

        await asyncio.to_thread(_write)

    async def _add_point(self, user_id: int) -> None:
        async with self._scores_lock:
            scores = await self._load_scores()
            key = str(user_id)
            scores[key] = scores.get(key, 0) + 1
            await self._save_scores(scores)

    # ---------------------------------------------------------------
    # /number_guessing
    # ---------------------------------------------------------------

    @app_commands.command(
        name="number_guessing",
        description="Starte ein Number-Guessing-Spiel."
    )
    async def number_guessing(self, interaction: discord.Interaction):
        if self.game is not None:
            await interaction.response.send_message(
                f"⏳ Es läuft bereits ein Spiel von <@{self.game['user_id']}>. "
                "Warte, bis es beendet oder abgelaufen ist.",
                ephemeral=True,
            )
            return

        number = random.randint(1, 100)
        self.game = {
            "number": number,
            "user_id": interaction.user.id,
            "attempts": 0,
            "started_at": time.monotonic(),
        }
        self.timeout_task = asyncio.create_task(
            self._run_timeout(interaction.channel, interaction.user.id)
        )

        embed = discord.Embed(
            title="🔢 Number Guessing",
            description=(
                "Ich habe mir eine Zahl zwischen **1 und 100** ausgesucht.\n\n"
                "Schreib deine Vermutung in den Chat!\n"
                f"Du hast **{GUESS_TIME_LIMIT_SECONDS // 60} Minuten** Zeit und brauchst "
                f"**{MAX_ATTEMPTS_FOR_POINT} oder weniger Versuche** für einen Punkt."
            ),
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(embed=embed)

    async def _run_timeout(self, channel: discord.abc.Messageable, user_id: int) -> None:
        try:
            await asyncio.sleep(GUESS_TIME_LIMIT_SECONDS)
        except asyncio.CancelledError:
            return

        if self.game is None or self.game["user_id"] != user_id:
            return  # Spiel wurde inzwischen regulär beendet

        number = self.game["number"]
        self.game = None

        embed = discord.Embed(
            title="⏰ Zeit abgelaufen!",
            description=(
                f"Die Zahl war **{number}**. Kein Punkt diesmal.\n"
                "Ein neues Spiel kann jetzt mit `/number_guessing` gestartet werden."
            ),
            color=discord.Color.orange()
        )
        try:
            await channel.send(f"<@{user_id}>", embed=embed)
        except discord.HTTPException:
            pass

    # ---------------------------------------------------------------
    # Rate-Verarbeitung
    # ---------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or self.game is None:
            return
        if message.author.id != self.game["user_id"]:
            return

        # Nur einzelne Zahlen akzeptieren
        try:
            guess = int(message.content)
        except ValueError:
            return

        self.game["attempts"] += 1
        number = self.game["number"]
        attempts = self.game["attempts"]

        if guess < number:
            await message.reply("⬆️ **Zu niedrig!**")
            return

        if guess > number:
            await message.reply("⬇️ **Zu hoch!**")
            return

        elapsed = time.monotonic() - self.game["started_at"]
        won_point = attempts <= MAX_ATTEMPTS_FOR_POINT and elapsed <= GUESS_TIME_LIMIT_SECONDS

        self.game = None
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()

        embed = discord.Embed(
            title="🎉 Richtig!",
            description=(
                f"Die Zahl war **{number}**!\n\n"
                f"Du hast **{attempts} Versuche** gebraucht."
            ),
            color=discord.Color.green()
        )
        if won_point:
            embed.add_field(name="Punkt", value="✅ +1 (in ≤7 Versuchen erraten)", inline=False)
            await self._add_point(message.author.id)
        else:
            embed.add_field(name="Punkt", value="❌ Kein Punkt (mehr als 7 Versuche gebraucht)", inline=False)

        await message.reply(embed=embed)

    # ---------------------------------------------------------------
    # /number_score
    # ---------------------------------------------------------------

    @app_commands.command(
        name="number_score",
        description="Zeigt das Number-Guessing-Leaderboard."
    )
    async def number_score(self, interaction: discord.Interaction):
        await interaction.response.defer()

        scores = await self._load_scores()
        if not scores:
            await interaction.followup.send("Noch keine Punkte vergeben.")
            return

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:10]

        lines = []
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for idx, (user_id, points) in enumerate(ranked, start=1):
            member = interaction.guild.get_member(int(user_id)) if interaction.guild else None
            name = member.display_name if member else f"Nutzer {user_id}"
            prefix = medals.get(idx, f"`#{idx}`")
            lines.append(f"{prefix} **{name}** — {points} Punkt{'e' if points != 1 else ''}")

        embed = discord.Embed(
            title="🔢 Number-Guessing-Leaderboard",
            description="\n".join(lines),
            color=discord.Color.from_rgb(0, 229, 255)
        )
        embed.set_footer(text="Seite 1")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(NumberGuessing(bot))
