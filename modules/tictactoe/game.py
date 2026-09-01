from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

_WIN_LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Reihen
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Spalten
    (0, 4, 8), (2, 4, 6),             # Diagonalen
)


class Mark(Enum):
    EMPTY = " "
    X = "X"
    O = "O"

    @property
    def other(self) -> "Mark":
        if self is Mark.X:
            return Mark.O
        if self is Mark.O:
            return Mark.X
        return Mark.EMPTY


@dataclass
class MoveResult:
    winner: Mark | None = None
    winning_line: tuple[int, int, int] | None = None
    is_draw: bool = False

    @property
    def is_over(self) -> bool:
        return self.winner is not None or self.is_draw


@dataclass
class Board:
    cells: list[Mark] = field(default_factory=lambda: [Mark.EMPTY] * 9)

    def copy(self) -> "Board":
        return Board(cells=list(self.cells))

    def legal_moves(self) -> list[int]:
        return [i for i, c in enumerate(self.cells) if c is Mark.EMPTY]

    def play(self, index: int, mark: Mark) -> None:
        if self.cells[index] is not Mark.EMPTY:
            raise ValueError(f"Feld {index} ist bereits belegt")
        self.cells[index] = mark

    def evaluate(self) -> MoveResult:
        for line in _WIN_LINES:
            a, b, c = line
            if self.cells[a] is not Mark.EMPTY and self.cells[a] == self.cells[b] == self.cells[c]:
                return MoveResult(winner=self.cells[a], winning_line=line)
        if not self.legal_moves():
            return MoveResult(is_draw=True)
        return MoveResult()
