from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from .game import Mark
from .session import GameSession

if TYPE_CHECKING:
    from .cog import TicTacToeCog

_EMPTY_LABEL = "​"


class ChallengeView(discord.ui.View):
    def __init__(self, cog: "TicTacToeCog", challenger_id: int, opponent_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message(
                "Diese Herausforderung ist nicht an dich gerichtet.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Annehmen", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await self.cog.on_challenge_accept(interaction, self.challenger_id, self.opponent_id)

    @discord.ui.button(label="Ablehnen", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await self.cog.on_challenge_decline(interaction, self.challenger_id, self.opponent_id)

    async def on_timeout(self) -> None:
        if self.message is not None:
            try:
                await self.message.edit(content="⌛ Herausforderung abgelaufen.", view=None)
            except discord.HTTPException:
                pass


class CellButton(discord.ui.Button["GameView"]):
    def __init__(self, index: int, mark: Mark, disabled: bool):
        row, _ = divmod(index, 3)
        if mark is Mark.X:
            label, style = "X", discord.ButtonStyle.danger
        elif mark is Mark.O:
            label, style = "O", discord.ButtonStyle.primary
        else:
            label, style = _EMPTY_LABEL, discord.ButtonStyle.secondary
        super().__init__(label=label, style=style, row=row, disabled=disabled or mark is not Mark.EMPTY)
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.cog.on_cell_click(interaction, self.view.session_id, self.index)


class RematchButton(discord.ui.Button["GameView"]):
    def __init__(self):
        super().__init__(label="Neues Spiel", style=discord.ButtonStyle.success, emoji="🔄", row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.cog.on_rematch(interaction, self.view.session_id)


class StatsButton(discord.ui.Button["GameView"]):
    def __init__(self):
        super().__init__(label="Statistiken", style=discord.ButtonStyle.secondary, emoji="📊", row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.cog.on_stats(interaction, self.view.session_id)


class GameView(discord.ui.View):
    def __init__(self, cog: "TicTacToeCog", session: GameSession, game_over: bool):
        super().__init__(timeout=600)
        self.cog = cog
        self.session_id = session.session_id
        self._build(session, game_over)

    def _build(self, session: GameSession, game_over: bool) -> None:
        self.clear_items()
        for i, mark in enumerate(session.board.cells):
            self.add_item(CellButton(i, mark, disabled=game_over))
        if game_over:
            self.add_item(RematchButton())
            self.add_item(StatsButton())

    async def on_timeout(self) -> None:
        self.cog.sessions.remove(self.session_id)
        if self.message is not None:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class BackToGameButton(discord.ui.Button["StatsBackView"]):
    def __init__(self):
        super().__init__(label="Zurück zum Spiel", style=discord.ButtonStyle.secondary, emoji="◀️", row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.cog.on_back_to_game(interaction, self.view.session_id)


class StatsBackView(discord.ui.View):
    def __init__(self, cog: "TicTacToeCog", session_id: int):
        super().__init__(timeout=600)
        self.cog = cog
        self.session_id = session_id
        self.add_item(BackToGameButton())
