from __future__ import annotations

import asyncio
import io
import logging

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from modules.database import Database
from modules.tictactoe.game import Board, Mark, MoveResult
from modules.tictactoe.render import render_game_card, render_stats_card
from modules.tictactoe.session import GameSession, Player, SessionStore
from modules.tictactoe.stats import PlayerStats
from modules.tictactoe.views import ChallengeView, GameView, StatsBackView

logger = logging.getLogger("tictactoe")


class TicTacToeCog(commands.Cog, name="TicTacToe"):
    def __init__(self, bot: commands.Bot, db: Database):
        self.bot = bot
        self.db = db
        self.sessions = SessionStore()
        self._avatar_cache: dict[int, bytes | None] = {}
        self._own_http_session: aiohttp.ClientSession | None = None

    async def cog_unload(self) -> None:
        if self._own_http_session is not None:
            await self._own_http_session.close()

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        logger.exception("Fehler im tictactoe-Command", exc_info=error)
        message = "❌ Da ist etwas schiefgelaufen. Bitte versuch es erneut."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @property
    def http_session(self) -> aiohttp.ClientSession:
        bot_session = getattr(self.bot, "http_session", None)
        if isinstance(bot_session, aiohttp.ClientSession) and not bot_session.closed:
            return bot_session
        if self._own_http_session is None or self._own_http_session.closed:
            self._own_http_session = aiohttp.ClientSession()
        return self._own_http_session

    # -- Avatare ------------------------------------------------------------

    async def _avatar_bytes(self, user_id: int, url: str | None) -> bytes | None:
        if user_id in self._avatar_cache:
            return self._avatar_cache[user_id]
        data: bytes | None = None
        if url:
            try:
                async with self.http_session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
            except aiohttp.ClientError as exc:
                logger.warning("Avatar für Nutzer %s konnte nicht geladen werden: %s", user_id, exc)
        self._avatar_cache[user_id] = data
        return data

    async def _avatars_for(self, session: GameSession) -> dict[int, bytes | None]:
        return {
            session.player_x.user_id: await self._avatar_bytes(session.player_x.user_id, session.player_x.avatar_url),
            session.player_o.user_id: await self._avatar_bytes(session.player_o.user_id, session.player_o.avatar_url),
        }

    @staticmethod
    def _player_from_member(member: discord.abc.User) -> Player:
        avatar_url = member.display_avatar.replace(size=128, format="png").url
        display_name = getattr(member, "display_name", None) or member.name
        return Player(user_id=member.id, display_name=display_name, avatar_url=avatar_url)

    # -- Rendering ------------------------------------------------------------

    @staticmethod
    def _status_text(session: GameSession, result: MoveResult) -> str:
        if result.winner is not None:
            winner = session.winner_player(result)
            assert winner is not None
            return f"{winner.display_name.upper()} HAT GEWONNEN!"
        if result.is_draw:
            return "UNENTSCHIEDEN!"
        return f"{session.current_player.display_name} ist am Zug"

    async def _render_state(self, session: GameSession) -> tuple[discord.File, GameView, MoveResult]:
        result = session.board.evaluate()
        status_text = self._status_text(session, result)
        avatars = await self._avatars_for(session)
        active_mark = None if result.is_over else session.turn
        image_bytes = await asyncio.to_thread(
            render_game_card, session, status_text, result.winning_line, avatars, active_mark
        )
        file = discord.File(io.BytesIO(image_bytes), filename="tictactoe.png")
        view = GameView(self, session, game_over=result.is_over)
        return file, view, result

    # -- Slash Command ------------------------------------------------------

    @app_commands.command(name="tictactoe", description="Starte eine Runde Tic-Tac-Toe gegen einen Mitspieler.")
    @app_commands.describe(gegner="Server-Mitglied, das du herausfordern willst")
    async def tictactoe(self, interaction: discord.Interaction, gegner: discord.Member) -> None:
        if gegner.id == interaction.user.id:
            await interaction.response.send_message("Du kannst nicht gegen dich selbst spielen.", ephemeral=True)
            return
        if gegner.bot:
            await interaction.response.send_message("Du kannst keinen Bot herausfordern.", ephemeral=True)
            return

        view = ChallengeView(self, interaction.user.id, gegner.id)
        await interaction.response.send_message(
            content=f"🎮 {gegner.mention}, **{interaction.user.display_name}** fordert dich zu einer Runde Tic-Tac-Toe heraus!",
            view=view,
            allowed_mentions=discord.AllowedMentions(users=True),
        )
        view.message = await interaction.original_response()

    # -- Herausforderung ------------------------------------------------------

    async def on_challenge_accept(self, interaction: discord.Interaction, challenger_id: int, opponent_id: int) -> None:
        guild = interaction.guild
        challenger = guild.get_member(challenger_id) if guild else None
        if challenger is None:
            try:
                challenger = await self.bot.fetch_user(challenger_id)
            except discord.HTTPException:
                await interaction.response.edit_message(content="⚠️ Der Herausforderer ist nicht mehr auffindbar.", view=None)
                return

        player_x = self._player_from_member(challenger)
        player_o = self._player_from_member(interaction.user)
        session = self.sessions.create(player_x, player_o, interaction.channel_id or 0)

        file, view, _result = await self._render_state(session)
        await interaction.response.edit_message(content=None, attachments=[file], view=view)
        view.message = await interaction.original_response()
        session.message_id = view.message.id

    async def on_challenge_decline(self, interaction: discord.Interaction, challenger_id: int, opponent_id: int) -> None:
        await interaction.response.edit_message(
            content=f"❌ <@{opponent_id}> hat die Herausforderung von <@{challenger_id}> abgelehnt.",
            view=None,
        )

    # -- Spielzüge ------------------------------------------------------------

    async def on_cell_click(self, interaction: discord.Interaction, session_id: int, index: int) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            await interaction.response.send_message("Dieses Spiel ist nicht mehr aktiv.", ephemeral=True)
            return

        mark = session.mark_for(interaction.user.id)
        if mark is None:
            await interaction.response.send_message("Du bist nicht Teil dieses Spiels.", ephemeral=True)
            return
        if mark is not session.turn:
            await interaction.response.send_message("Du bist gerade nicht am Zug.", ephemeral=True)
            return

        result = session.play(index)

        if result.is_over:
            await self._finish_game(session, result)

        file, view, _result = await self._render_state(session)
        await interaction.response.edit_message(attachments=[file], view=view)
        view.message = await interaction.original_response()

    async def _finish_game(self, session: GameSession, result: MoveResult) -> None:
        if result.winner is not None:
            winner = session.winner_player(result)
            loser = session.loser_player(result)
            await self.db.record_ttt_result(
                winner_id=(winner.user_id if winner else None),
                loser_id=(loser.user_id if loser else None),
            )
        elif result.is_draw:
            draw_ids = (session.player_x.user_id, session.player_o.user_id)
            await self.db.record_ttt_result(winner_id=None, loser_id=None, draw_ids=draw_ids)

    # -- Rematch / Statistiken ------------------------------------------------

    async def on_rematch(self, interaction: discord.Interaction, session_id: int) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            await interaction.response.send_message("Dieses Spiel ist nicht mehr verfügbar.", ephemeral=True)
            return
        if interaction.user.id not in (session.player_x.user_id, session.player_o.user_id):
            await interaction.response.send_message("Nur die Spieler dieser Runde können ein neues Spiel starten.", ephemeral=True)
            return

        session.board = Board()
        session.turn = Mark.X

        file, view, _result = await self._render_state(session)
        await interaction.response.edit_message(attachments=[file], view=view)
        view.message = await interaction.original_response()

    async def on_stats(self, interaction: discord.Interaction, session_id: int) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            await interaction.response.send_message("Dieses Spiel ist nicht mehr verfügbar.", ephemeral=True)
            return

        entries = []
        for player in (session.player_x, session.player_o):
            wins, losses, draws = await self.db.get_ttt_stats(player.user_id)
            entries.append((player, PlayerStats(user_id=player.user_id, wins=wins, losses=losses, draws=draws)))

        image_bytes = await asyncio.to_thread(render_stats_card, entries)
        file = discord.File(io.BytesIO(image_bytes), filename="tictactoe_stats.png")
        view = StatsBackView(self, session_id)
        await interaction.response.edit_message(attachments=[file], view=view)
        view.message = await interaction.original_response()

    async def on_back_to_game(self, interaction: discord.Interaction, session_id: int) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            await interaction.response.edit_message(content="Dieses Spiel ist nicht mehr verfügbar.", attachments=[], view=None)
            return

        file, view, _result = await self._render_state(session)
        await interaction.response.edit_message(content=None, attachments=[file], view=view)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicTacToeCog(bot, bot.db))
