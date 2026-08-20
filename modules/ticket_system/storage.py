from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import aiosqlite

log = logging.getLogger("ticket_system.storage")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
LEGACY_JSON_PATH = DATA_DIR / "tickets.json"


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

    @staticmethod
    def _from_row(row: tuple) -> "TicketData":
        channel_id, type_, opener_id, created_at, claimed_by, closed, added_users_json, answers_json = row
        return TicketData(
            channel_id=channel_id,
            type=type_,
            opener_id=opener_id,
            created_at=created_at,
            claimed_by=claimed_by,
            closed=bool(closed),
            added_users=json.loads(added_users_json),
            answers=json.loads(answers_json),
        )


class TicketStore:
    """Async-sichere Schnittstelle auf die `tickets`/`ticket_counters`-Tabellen
    der Master-DB (siehe modules/database.py). Hängt sich per bind() an die
    vom Bot bereits geöffnete aiosqlite-Connection -- store ist ein Modul-Singleton,
    der schon beim Import existiert, lange bevor die DB-Connection in
    setup_hook() steht, daher die getrennte bind()-Stufe."""

    def __init__(self) -> None:
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    def bind(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    def _require_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError(
                "TicketStore wurde noch nicht an eine DB-Connection gebunden -- "
                "bind() muss in setup_hook() vor dem Laden der Extensions laufen."
            )
        return self._conn

    async def migrate_legacy_json(self) -> None:
        """Importiert die alte tickets.json einmalig (nur falls die Tabelle noch
        leer ist) und benennt die Datei danach in .migrated um, statt sie zu
        löschen -- im Fehlerfall bleibt sie unangetastet liegen."""
        conn = self._require_conn()

        cur = await conn.execute("SELECT COUNT(*) FROM tickets")
        (existing,) = await cur.fetchone()
        if existing > 0:
            return
        if not LEGACY_JSON_PATH.exists():
            return

        try:
            raw = json.loads(LEGACY_JSON_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Konnte tickets.json nicht lesen (%s) -- Migration übersprungen.", e)
            return

        tickets = raw.get("tickets", {})
        counters = raw.get("counters", {})

        for entry in tickets.values():
            opener_id = entry.get("opener_id")
            ticket_type = entry.get("type")
            channel_id = entry.get("channel_id")
            if opener_id is None or ticket_type is None or channel_id is None:
                continue  # unvollstaendiger/beschaedigter Eintrag -> ignorieren statt crashen
            await conn.execute(
                """
                INSERT INTO tickets (channel_id, type, opener_id, created_at, claimed_by, closed, added_users, answers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (channel_id) DO NOTHING
                """,
                (
                    channel_id,
                    ticket_type,
                    opener_id,
                    entry.get("created_at", time.time()),
                    entry.get("claimed_by"),
                    int(entry.get("closed", False)),
                    json.dumps(list(entry.get("added_users", []))),
                    json.dumps(dict(entry.get("answers", {}))),
                ),
            )
        for counter_key, value in counters.items():
            await conn.execute(
                """
                INSERT INTO ticket_counters (counter_key, value) VALUES (?, ?)
                ON CONFLICT (counter_key) DO UPDATE SET value = excluded.value
                """,
                (counter_key, int(value or 0)),
            )
        await conn.commit()

        try:
            LEGACY_JSON_PATH.rename(LEGACY_JSON_PATH.with_suffix(".json.migrated"))
        except OSError as e:
            log.warning("Konnte tickets.json nicht als migriert markieren (%s) -- Datei bleibt liegen.", e)

        log.info("tickets.json migriert (%d Tickets, %d Zähler).", len(tickets), len(counters))

    async def get_ticket(self, channel_id: int) -> Optional[TicketData]:
        conn = self._require_conn()
        async with self._lock:
            cur = await conn.execute(
                "SELECT channel_id, type, opener_id, created_at, claimed_by, closed, added_users, answers "
                "FROM tickets WHERE channel_id = ?",
                (channel_id,),
            )
            row = await cur.fetchone()
            return TicketData._from_row(row) if row else None

    async def save_ticket(self, ticket: TicketData) -> None:
        conn = self._require_conn()
        async with self._lock:
            await conn.execute(
                """
                INSERT INTO tickets (channel_id, type, opener_id, created_at, claimed_by, closed, added_users, answers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (channel_id) DO UPDATE SET
                    type = excluded.type, opener_id = excluded.opener_id, created_at = excluded.created_at,
                    claimed_by = excluded.claimed_by, closed = excluded.closed,
                    added_users = excluded.added_users, answers = excluded.answers
                """,
                (
                    ticket.channel_id,
                    ticket.type,
                    ticket.opener_id,
                    ticket.created_at,
                    ticket.claimed_by,
                    int(ticket.closed),
                    json.dumps(ticket.added_users),
                    json.dumps(ticket.answers),
                ),
            )
            await conn.commit()

    async def delete_ticket(self, channel_id: int) -> None:
        conn = self._require_conn()
        async with self._lock:
            await conn.execute("DELETE FROM tickets WHERE channel_id = ?", (channel_id,))
            await conn.commit()

    async def open_tickets_by_user(self, user_id: int, type_prefix: str) -> list[TicketData]:
        """Alle offenen Tickets eines Nutzers, deren type mit type_prefix beginnt."""
        conn = self._require_conn()
        async with self._lock:
            cur = await conn.execute(
                "SELECT channel_id, type, opener_id, created_at, claimed_by, closed, added_users, answers "
                "FROM tickets WHERE opener_id = ? AND type LIKE ? AND closed = 0",
                (user_id, f"{type_prefix}%"),
            )
            rows = await cur.fetchall()
            return [TicketData._from_row(row) for row in rows]

    async def reserve_ticket_slot(
        self, user_id: int, type_prefix: str, max_allowed: int, counter_key: str
    ) -> Optional[int]:
        """Prueft das Ticket-Limit und zieht bei freiem Slot atomar einen neuen Zaehlerwert.

        Haelt den Lock ueber Pruefung + Inkrement, damit zwei gleichzeitige
        Ticket-Erstellungen desselben Nutzers das Limit nicht umgehen koennen.
        Gibt None zurueck, wenn das Limit bereits erreicht ist.
        """
        conn = self._require_conn()
        async with self._lock:
            cur = await conn.execute(
                "SELECT COUNT(*) FROM tickets WHERE opener_id = ? AND type LIKE ? AND closed = 0",
                (user_id, f"{type_prefix}%"),
            )
            (open_count,) = await cur.fetchone()
            if open_count >= max_allowed:
                return None

            await conn.execute(
                """
                INSERT INTO ticket_counters (counter_key, value) VALUES (?, 1)
                ON CONFLICT (counter_key) DO UPDATE SET value = value + 1
                """,
                (counter_key,),
            )
            cur = await conn.execute(
                "SELECT value FROM ticket_counters WHERE counter_key = ?", (counter_key,)
            )
            (value,) = await cur.fetchone()
            await conn.commit()
            return value

    async def next_counter(self, key: str) -> int:
        conn = self._require_conn()
        async with self._lock:
            await conn.execute(
                """
                INSERT INTO ticket_counters (counter_key, value) VALUES (?, 1)
                ON CONFLICT (counter_key) DO UPDATE SET value = value + 1
                """,
                (key,),
            )
            cur = await conn.execute(
                "SELECT value FROM ticket_counters WHERE counter_key = ?", (key,)
            )
            (value,) = await cur.fetchone()
            await conn.commit()
            return value

    async def all_tickets(self) -> list[TicketData]:
        conn = self._require_conn()
        async with self._lock:
            cur = await conn.execute(
                "SELECT channel_id, type, opener_id, created_at, claimed_by, closed, added_users, answers "
                "FROM tickets"
            )
            rows = await cur.fetchall()
            return [TicketData._from_row(row) for row in rows]


store = TicketStore()
