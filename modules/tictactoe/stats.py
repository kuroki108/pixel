from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlayerStats:
    user_id: int
    wins: int = 0
    losses: int = 0
    draws: int = 0

    @property
    def games(self) -> int:
        return self.wins + self.losses + self.draws

    @property
    def win_rate(self) -> float:
        return (self.wins / self.games * 100) if self.games else 0.0
