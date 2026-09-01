from __future__ import annotations

import itertools
from dataclasses import dataclass

from .game import Board, Mark, MoveResult

_id_counter = itertools.count(1)


@dataclass
class Player:
    user_id: int
    display_name: str
    avatar_url: str | None


@dataclass
class GameSession:
    session_id: int
    player_x: Player
    player_o: Player
    board: Board
    turn: Mark = Mark.X
    channel_id: int = 0
    message_id: int | None = None

    @property
    def current_player(self) -> Player:
        return self.player_x if self.turn is Mark.X else self.player_o

    def player_for(self, user_id: int) -> Player | None:
        if self.player_x.user_id == user_id:
            return self.player_x
        if self.player_o.user_id == user_id:
            return self.player_o
        return None

    def mark_for(self, user_id: int) -> Mark | None:
        if self.player_x.user_id == user_id:
            return Mark.X
        if self.player_o.user_id == user_id:
            return Mark.O
        return None

    def play(self, index: int) -> MoveResult:
        mark = self.turn
        self.board.play(index, mark)
        result = self.board.evaluate()
        if not result.is_over:
            self.turn = self.turn.other
        return result

    def winner_player(self, result: MoveResult) -> Player | None:
        if result.winner is Mark.X:
            return self.player_x
        if result.winner is Mark.O:
            return self.player_o
        return None

    def loser_player(self, result: MoveResult) -> Player | None:
        winner = self.winner_player(result)
        if winner is None:
            return None
        return self.player_o if winner is self.player_x else self.player_x


class SessionStore:
    """Hält alle aktuell laufenden Spiele im Speicher (pro Prozess)."""

    def __init__(self) -> None:
        self._sessions: dict[int, GameSession] = {}

    def create(self, player_x: Player, player_o: Player, channel_id: int) -> GameSession:
        session = GameSession(
            session_id=next(_id_counter),
            player_x=player_x,
            player_o=player_o,
            board=Board(),
            channel_id=channel_id,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: int) -> GameSession | None:
        return self._sessions.get(session_id)

    def remove(self, session_id: int) -> None:
        self._sessions.pop(session_id, None)
