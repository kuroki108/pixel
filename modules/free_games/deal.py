from dataclasses import dataclass
from datetime import datetime


@dataclass
class Deal:
    """Ein einzelnes Angebot / Freegame, quellenunabhängig normalisiert."""

    deal_id: str  # eindeutige ID, z.B. "epic:slug" oder "steam:appid:end_ts"
    source: str  # "Epic Games" oder "Steam"
    title: str
    description: str
    store_url: str
    launcher_url: str | None
    image_url: str | None
    original_price_cents: int
    current_price_cents: int
    currency: str  # immer "EUR"
    end_date: datetime | None
    rating: str | None  # z.B. "82/100", optional
    is_free: bool

    @property
    def is_discount_only(self) -> bool:
        return not self.is_free
