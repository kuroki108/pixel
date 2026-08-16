"""
Einfache, dateibasierte Speicherung des Ticket-Zustands.

Statt einer Datenbank verwenden wir eine einzelne JSON-Datei
(data/tickets.json). Ein asyncio.Lock verhindert, dass zwei
gleichzeitige Schreibzugriffe sich gegenseitig überschreiben.
Geschrieben wird atomar (erst in eine .tmp-Datei, dann umbenennen),
damit die JSON-Datei bei einem Absturz mitten im Schreibvorgang nicht
korrupt wird.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATA_FILE = os.path.join(DATA_DIR, "tickets.json")

_lock = asyncio.Lock()

_DEFAULT_DATA: dict[str, Any] = {
    "tickets": {},
    "counters": {"support": 0, "application": 0},
}


def _normalize_data(data: dict[str, Any]) -> dict[str, Any]:
    tickets = data.get("tickets")
    counters = data.get("counters")

    if not isinstance(tickets, dict):
        tickets = {}
    if not isinstance(counters, dict):
        counters = {}

    normalized = {
        "tickets": tickets,
        "counters": {
            "support": int(counters.get("support", 0) or 0),
            "application": int(counters.get("application", 0) or 0),
        },
    }

    for key, value in counters.items():
        if key not in normalized["counters"]:
            try:
                normalized["counters"][key] = int(value)
            except (TypeError, ValueError):
                normalized["counters"][key] = 0

    return normalized


def _ensure_file() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(_DEFAULT_DATA, f, indent=2)


def _read_raw() -> dict[str, Any]:
    _ensure_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return _normalize_data(json.load(f))
        except json.JSONDecodeError:
            # Datei ist beschädigt/leer -> mit Defaults neu anlegen statt zu crashen
            return _normalize_data(json.loads(json.dumps(_DEFAULT_DATA)))


def _write_raw(data: dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_path = DATA_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, DATA_FILE)  # atomar auf allen gängigen Betriebssystemen


@dataclass
class TicketData:
    channel_id: int
    type: str  # "support" | "application_supporter" | "application_designer" | "application_eventmanager"
    opener_id: int
    created_at: float = field(default_factory=time.time)
    claimed_by: Optional[int] = None
    closed: bool = False
    added_users: list[int] = field(default_factory=list)
    answers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "TicketData":
        return TicketData(
            channel_id=d["channel_id"],
            type=d["type"],
            opener_id=d["opener_id"],
            created_at=d.get("created_at", time.time()),
            claimed_by=d.get("claimed_by"),
            closed=d.get("closed", False),
            added_users=list(d.get("added_users", [])),
            answers=dict(d.get("answers", {})),
        )


class TicketStore:
    """Async-sichere Schnittstelle auf die JSON-Datei."""

    async def get_ticket(self, channel_id: int) -> Optional[TicketData]:
        async with _lock:
            data = _read_raw()
            raw = data["tickets"].get(str(channel_id))
            return TicketData.from_dict(raw) if raw else None

    async def save_ticket(self, ticket: TicketData) -> None:
        async with _lock:
            data = _read_raw()
            data["tickets"][str(ticket.channel_id)] = ticket.to_dict()
            _write_raw(data)

    async def delete_ticket(self, channel_id: int) -> None:
        async with _lock:
            data = _read_raw()
            data["tickets"].pop(str(channel_id), None)
            _write_raw(data)

    async def open_tickets_by_user(self, user_id: int, type_prefix: str) -> list[TicketData]:
        """Alle offenen Tickets eines Nutzers, deren type mit type_prefix beginnt."""
        async with _lock:
            data = _read_raw()
            result = []
            for raw in data["tickets"].values():
                if raw["opener_id"] == user_id and raw["type"].startswith(type_prefix) and not raw.get("closed", False):
                    result.append(TicketData.from_dict(raw))
            return result

    async def next_counter(self, key: str) -> int:
        async with _lock:
            data = _read_raw()
            data["counters"][key] = data["counters"].get(key, 0) + 1
            value = data["counters"][key]
            _write_raw(data)
            return value

    async def all_tickets(self) -> list[TicketData]:
        async with _lock:
            data = _read_raw()
            return [TicketData.from_dict(raw) for raw in data["tickets"].values()]


store = TicketStore()
