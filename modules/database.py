"""
Master-SQLite-Datenbank für den gesamten Bot (ein Connection-Objekt, eine Datei).

Historisch gewachsen aus der Leveling-DB (`modules/lvl_system/database.py`) —
jedes Feature, das Zustand über Neustarts hinweg braucht, bekommt hier eine
eigene Tabelle statt einer eigenen JSON-Datei. `ZenArcadeBot.setup_hook`
verbindet genau eine Instanz (`bot.db`) **bevor** die Extensions geladen
werden; jeder Cog, der Persistenz braucht, bekommt sie im `setup(bot)` als
`bot.db` übergeben (siehe `lvl_system/cogs/leveling.py`, `counting.py`,
`birthday.py`, `number_guessing.py`).

Das Ticket-System (`modules/ticket_system/storage.py`) legt seine Tabellen
ebenfalls hier an (siehe SCHEMA unten), verwaltet seine Queries aber selbst
in einer eigenen `TicketStore`-Klasse, die sich per `store.bind(db.conn)`
an dieselbe Connection hängt — das hält die Ticket-Logik in ihrer eigenen
Schicht, ohne eine zweite Datenbankdatei zu brauchen.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

log = logging.getLogger("database")

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "pixel.sqlite3"

# Alter Speicherort der Leveling-DB, bevor sie zur bot-weiten Master-DB wurde.
# Wird beim ersten Start automatisch (kopierend, nicht verschiebend) übernommen.
_LEGACY_LEVELING_DB_PATH = Path(__file__).resolve().parent / "lvl_system" / "data" / "leveling.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    guild_id        INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    xp              INTEGER NOT NULL DEFAULT 0,   -- XP im aktuellen Level
    total_xp        INTEGER NOT NULL DEFAULT 0,   -- XP gesamt (für Leaderboard-Sortierung)
    level           INTEGER NOT NULL DEFAULT 0,
    last_message_ts INTEGER NOT NULL DEFAULT 0,   -- für Text-XP-Cooldown
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS level_roles (
    guild_id INTEGER NOT NULL,
    level    INTEGER NOT NULL,
    role_id  INTEGER NOT NULL,
    PRIMARY KEY (guild_id, level)
);

CREATE TABLE IF NOT EXISTS guild_config (
    guild_id           INTEGER PRIMARY KEY,
    xp_min             INTEGER NOT NULL DEFAULT 15,
    xp_max             INTEGER NOT NULL DEFAULT 25,
    cooldown_seconds   INTEGER NOT NULL DEFAULT 60,
    voice_xp_per_min   INTEGER NOT NULL DEFAULT 10,
    voice_xp_enabled   INTEGER NOT NULL DEFAULT 1,
    levelup_channel_id INTEGER,
    levelup_message    TEXT NOT NULL DEFAULT '🎉 {mention} ist jetzt **Level {level}**!',
    stack_roles        INTEGER NOT NULL DEFAULT 1  -- 1 = alte Rollenbelohnungen behalten, 0 = nur höchste
);

CREATE INDEX IF NOT EXISTS idx_users_guild_totalxp ON users (guild_id, total_xp DESC);

CREATE TABLE IF NOT EXISTS counting_state (
    channel_id   INTEGER PRIMARY KEY,
    count        INTEGER NOT NULL DEFAULT 0,
    last_user_id INTEGER
);

CREATE TABLE IF NOT EXISTS number_guessing_scores (
    user_id INTEGER PRIMARY KEY,
    points  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS birthdays (
    user_id INTEGER PRIMARY KEY,
    day     INTEGER NOT NULL,
    month   INTEGER NOT NULL,
    year    INTEGER
);

CREATE TABLE IF NOT EXISTS birthday_calendar_messages (
    channel_id INTEGER PRIMARY KEY,
    message_id INTEGER NOT NULL
);

-- Ticket-System (Queries leben in modules/ticket_system/storage.py, Schema hier
-- zentral wie alles andere). added_users/answers als JSON-Text, weil sie nie
-- unabhängig vom Ticket selbst abgefragt werden -- eine eigene Join-Tabelle
-- wäre hier reines Overengineering.
CREATE TABLE IF NOT EXISTS tickets (
    channel_id  INTEGER PRIMARY KEY,
    type        TEXT NOT NULL,
    opener_id   INTEGER NOT NULL,
    created_at  REAL NOT NULL,
    claimed_by  INTEGER,
    closed      INTEGER NOT NULL DEFAULT 0,
    added_users TEXT NOT NULL DEFAULT '[]',
    answers     TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS ticket_counters (
    counter_key TEXT PRIMARY KEY,
    value       INTEGER NOT NULL DEFAULT 0
);
"""


@dataclass
class UserStats:
    guild_id: int
    user_id: int
    xp: int
    total_xp: int
    level: int
    last_message_ts: int


@dataclass
class GuildConfig:
    guild_id: int
    xp_min: int = 15
    xp_max: int = 25
    cooldown_seconds: int = 60
    voice_xp_per_min: int = 10
    voice_xp_enabled: bool = True
    levelup_channel_id: int | None = None
    levelup_message: str = "🎉 {mention} ist jetzt **Level {level}**!"
    stack_roles: bool = True


def _migrate_json_file(json_path: Path, marker: str) -> dict | None:
    """Liest eine Legacy-JSON-Datei, falls vorhanden, und benennt sie nach
    erfolgreichem Import um (`<name>.json.migrated`) statt sie zu löschen --
    im Fehlerfall bleibt sie unangetastet liegen, es gehen also nie Daten
    verloren, im schlimmsten Fall bleibt nur die Migration aus."""
    if not json_path.exists():
        return None
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Konnte Legacy-Datei %s nicht lesen (%s: %s) -- Migration übersprungen.", json_path, marker, e)
        return None
    return data


def _mark_migrated(json_path: Path) -> None:
    try:
        json_path.rename(json_path.with_suffix(json_path.suffix + ".migrated"))
    except OSError as e:
        log.warning("Konnte %s nicht als migriert markieren (%s) -- Datei bleibt liegen.", json_path, e)


class Database:
    """Dünner Wrapper um eine aiosqlite-Connection mit fertigen Queries."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    @classmethod
    async def connect(cls) -> "Database":
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        if not DB_PATH.exists() and _LEGACY_LEVELING_DB_PATH.exists():
            # Alte Leveling-DB an den neuen Master-Ort *kopieren* (nicht verschieben) --
            # die Originaldatei bleibt als Backup unangetastet liegen.
            shutil.copy2(_LEGACY_LEVELING_DB_PATH, DB_PATH)
            log.info("Alte Leveling-Datenbank nach %s übernommen (Original bleibt erhalten).", DB_PATH)

        conn = await aiosqlite.connect(DB_PATH)
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA foreign_keys=ON;")
        await conn.executescript(SCHEMA)
        await conn.commit()
        db = cls(conn)
        await db._migrate_legacy_json()
        return db

    async def close(self) -> None:
        await self.conn.close()

    async def _migrate_legacy_json(self) -> None:
        """Importiert alte JSON-Zustände einmalig in die jeweilige Tabelle,
        aber nur wenn die Tabelle noch leer ist (idempotent bei jedem Neustart)."""
        data_dir = REPO_ROOT / "data"

        # counting_state.json war eine einzelne globale Zählung ohne Channel-Bezug;
        # counting.py übergibt beim Laden die konfigurierte COUNTING_CHANNEL_ID.
        await self._migrate_counting_json(data_dir / "counting_state.json")
        await self._migrate_number_guessing_json(data_dir / "number_guessing_scores.json")
        await self._migrate_birthdays_json(data_dir / "birthdays.json")
        await self._migrate_calendar_messages_json(data_dir / "birthday_calendar_messages.json")

    async def _migrate_counting_json(self, path: Path) -> None:
        cur = await self.conn.execute("SELECT COUNT(*) FROM counting_state")
        (count,) = await cur.fetchone()
        if count > 0:
            return
        data = _migrate_json_file(path, "counting_state")
        if data is None or "count" not in data:
            return
        # Channel-ID war in der alten JSON nicht enthalten (globaler Zustand) --
        # counting.py legt beim ersten Laden mit der echten Channel-ID nach.
        # Hier nur als Platzhalter-Zeile mit channel_id=0 ablegen; cog_load()
        # von counting.py hebt sie beim ersten Start auf die echte ID.
        await self.conn.execute(
            "INSERT INTO counting_state (channel_id, count, last_user_id) VALUES (0, ?, ?)",
            (data.get("count", 0), data.get("last_user_id")),
        )
        await self.conn.commit()
        _mark_migrated(path)
        log.info("counting_state.json migriert.")

    async def _migrate_number_guessing_json(self, path: Path) -> None:
        cur = await self.conn.execute("SELECT COUNT(*) FROM number_guessing_scores")
        (count,) = await cur.fetchone()
        if count > 0:
            return
        data = _migrate_json_file(path, "number_guessing_scores")
        if not data:
            return
        rows = [(int(uid), int(points)) for uid, points in data.items()]
        await self.conn.executemany(
            "INSERT INTO number_guessing_scores (user_id, points) VALUES (?, ?)", rows
        )
        await self.conn.commit()
        _mark_migrated(path)
        log.info("number_guessing_scores.json migriert (%d Einträge).", len(rows))

    async def _migrate_birthdays_json(self, path: Path) -> None:
        cur = await self.conn.execute("SELECT COUNT(*) FROM birthdays")
        (count,) = await cur.fetchone()
        if count > 0:
            return
        data = _migrate_json_file(path, "birthdays")
        if not data:
            return
        rows = [
            (int(uid), entry["day"], entry["month"], entry.get("year"))
            for uid, entry in data.items()
        ]
        await self.conn.executemany(
            "INSERT INTO birthdays (user_id, day, month, year) VALUES (?, ?, ?, ?)", rows
        )
        await self.conn.commit()
        _mark_migrated(path)
        log.info("birthdays.json migriert (%d Einträge).", len(rows))

    async def _migrate_calendar_messages_json(self, path: Path) -> None:
        cur = await self.conn.execute("SELECT COUNT(*) FROM birthday_calendar_messages")
        (count,) = await cur.fetchone()
        if count > 0:
            return
        data = _migrate_json_file(path, "birthday_calendar_messages")
        if not data:
            return
        rows = [(int(cid), int(mid)) for cid, mid in data.items()]
        await self.conn.executemany(
            "INSERT INTO birthday_calendar_messages (channel_id, message_id) VALUES (?, ?)", rows
        )
        await self.conn.commit()
        _mark_migrated(path)
        log.info("birthday_calendar_messages.json migriert (%d Einträge).", len(rows))

    # ---------- users (Leveling) ----------

    async def get_user(self, guild_id: int, user_id: int) -> UserStats:
        cur = await self.conn.execute(
            "SELECT guild_id, user_id, xp, total_xp, level, last_message_ts "
            "FROM users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        row = await cur.fetchone()
        if row is None:
            await self.conn.execute(
                "INSERT INTO users (guild_id, user_id) VALUES (?, ?)",
                (guild_id, user_id),
            )
            await self.conn.commit()
            return UserStats(guild_id, user_id, 0, 0, 0, 0)
        return UserStats(*row)

    async def set_user_xp(self, guild_id: int, user_id: int, xp: int, total_xp: int, level: int) -> None:
        await self.conn.execute(
            """
            INSERT INTO users (guild_id, user_id, xp, total_xp, level)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (guild_id, user_id)
            DO UPDATE SET xp = excluded.xp, total_xp = excluded.total_xp, level = excluded.level
            """,
            (guild_id, user_id, xp, total_xp, level),
        )
        await self.conn.commit()

    async def set_last_message_ts(self, guild_id: int, user_id: int, ts: int | None = None) -> None:
        ts = ts if ts is not None else int(time.time())
        await self.conn.execute(
            "UPDATE users SET last_message_ts = ? WHERE guild_id = ? AND user_id = ?",
            (ts, guild_id, user_id),
        )
        await self.conn.commit()

    async def reset_user(self, guild_id: int, user_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        )
        await self.conn.commit()

    async def reset_guild(self, guild_id: int) -> None:
        await self.conn.execute("DELETE FROM users WHERE guild_id = ?", (guild_id,))
        await self.conn.commit()

    async def get_leaderboard(self, guild_id: int, limit: int = 10, offset: int = 0) -> list[UserStats]:
        cur = await self.conn.execute(
            """
            SELECT guild_id, user_id, xp, total_xp, level, last_message_ts
            FROM users WHERE guild_id = ?
            ORDER BY total_xp DESC
            LIMIT ? OFFSET ?
            """,
            (guild_id, limit, offset),
        )
        rows = await cur.fetchall()
        return [UserStats(*row) for row in rows]

    async def get_rank(self, guild_id: int, user_id: int) -> int:
        """1-basierter Rang des Users nach total_xp (0 = noch nicht in DB / kein XP)."""
        cur = await self.conn.execute(
            """
            SELECT COUNT(*) + 1 FROM users
            WHERE guild_id = ? AND total_xp > (
                SELECT total_xp FROM users WHERE guild_id = ? AND user_id = ?
            )
            """,
            (guild_id, guild_id, user_id),
        )
        row = await cur.fetchone()
        return row[0] if row else 1

    async def get_member_count_with_xp(self, guild_id: int) -> int:
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM users WHERE guild_id = ? AND total_xp > 0", (guild_id,)
        )
        row = await cur.fetchone()
        return row[0] if row else 0

    # ---------- level roles ----------

    async def add_level_role(self, guild_id: int, level: int, role_id: int) -> None:
        await self.conn.execute(
            """
            INSERT INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?)
            ON CONFLICT (guild_id, level) DO UPDATE SET role_id = excluded.role_id
            """,
            (guild_id, level, role_id),
        )
        await self.conn.commit()

    async def remove_level_role(self, guild_id: int, level: int) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM level_roles WHERE guild_id = ? AND level = ?", (guild_id, level)
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def get_level_roles(self, guild_id: int) -> list[tuple[int, int]]:
        """Liste von (level, role_id), aufsteigend nach level sortiert."""
        cur = await self.conn.execute(
            "SELECT level, role_id FROM level_roles WHERE guild_id = ? ORDER BY level ASC",
            (guild_id,),
        )
        return list(await cur.fetchall())

    # ---------- guild config ----------

    async def get_guild_config(self, guild_id: int) -> GuildConfig:
        cur = await self.conn.execute(
            """
            SELECT guild_id, xp_min, xp_max, cooldown_seconds, voice_xp_per_min,
                   voice_xp_enabled, levelup_channel_id, levelup_message, stack_roles
            FROM guild_config WHERE guild_id = ?
            """,
            (guild_id,),
        )
        row = await cur.fetchone()
        if row is None:
            await self.conn.execute(
                "INSERT INTO guild_config (guild_id) VALUES (?)", (guild_id,)
            )
            await self.conn.commit()
            return GuildConfig(guild_id=guild_id)
        (
            gid, xp_min, xp_max, cooldown, voice_xp, voice_enabled,
            levelup_channel, levelup_msg, stack_roles,
        ) = row
        return GuildConfig(
            guild_id=gid,
            xp_min=xp_min,
            xp_max=xp_max,
            cooldown_seconds=cooldown,
            voice_xp_per_min=voice_xp,
            voice_xp_enabled=bool(voice_enabled),
            levelup_channel_id=levelup_channel,
            levelup_message=levelup_msg,
            stack_roles=bool(stack_roles),
        )

    async def update_guild_config(self, guild_id: int, **fields) -> None:
        if not fields:
            return
        await self.get_guild_config(guild_id)  # sorgt für existierende Zeile
        columns = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [guild_id]
        await self.conn.execute(
            f"UPDATE guild_config SET {columns} WHERE guild_id = ?", values
        )
        await self.conn.commit()

    # ---------- counting ----------

    async def get_counting_state(self, channel_id: int) -> tuple[int, int | None]:
        """Gibt (count, last_user_id) zurück, (0, None) falls noch nichts gespeichert.

        Migriert transparent eine channel_id=0-Platzhalterzeile (aus einer alten,
        channel-losen counting_state.json) auf die erste echte channel_id, die
        hier angefragt wird.
        """
        cur = await self.conn.execute(
            "SELECT count, last_user_id FROM counting_state WHERE channel_id = ?", (channel_id,)
        )
        row = await cur.fetchone()
        if row is not None:
            return row[0], row[1]

        cur = await self.conn.execute(
            "SELECT count, last_user_id FROM counting_state WHERE channel_id = 0"
        )
        legacy_row = await cur.fetchone()
        if legacy_row is not None:
            await self.conn.execute("DELETE FROM counting_state WHERE channel_id = 0")
            await self.conn.execute(
                "INSERT INTO counting_state (channel_id, count, last_user_id) VALUES (?, ?, ?)",
                (channel_id, legacy_row[0], legacy_row[1]),
            )
            await self.conn.commit()
            return legacy_row[0], legacy_row[1]

        return 0, None

    async def set_counting_state(self, channel_id: int, count: int, last_user_id: int | None) -> None:
        await self.conn.execute(
            """
            INSERT INTO counting_state (channel_id, count, last_user_id) VALUES (?, ?, ?)
            ON CONFLICT (channel_id) DO UPDATE SET count = excluded.count, last_user_id = excluded.last_user_id
            """,
            (channel_id, count, last_user_id),
        )
        await self.conn.commit()

    # ---------- number guessing ----------

    async def add_number_guessing_point(self, user_id: int) -> None:
        await self.conn.execute(
            """
            INSERT INTO number_guessing_scores (user_id, points) VALUES (?, 1)
            ON CONFLICT (user_id) DO UPDATE SET points = points + 1
            """,
            (user_id,),
        )
        await self.conn.commit()

    async def get_number_guessing_scores(self, limit: int = 10) -> list[tuple[int, int]]:
        """Liste von (user_id, points), absteigend nach Punkten sortiert."""
        cur = await self.conn.execute(
            "SELECT user_id, points FROM number_guessing_scores ORDER BY points DESC LIMIT ?",
            (limit,),
        )
        return list(await cur.fetchall())

    # ---------- birthdays ----------

    async def set_birthday(self, user_id: int, day: int, month: int, year: int | None) -> None:
        await self.conn.execute(
            """
            INSERT INTO birthdays (user_id, day, month, year) VALUES (?, ?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET day = excluded.day, month = excluded.month, year = excluded.year
            """,
            (user_id, day, month, year),
        )
        await self.conn.commit()

    async def remove_birthday(self, user_id: int) -> bool:
        cur = await self.conn.execute("DELETE FROM birthdays WHERE user_id = ?", (user_id,))
        await self.conn.commit()
        return cur.rowcount > 0

    async def get_all_birthdays(self) -> dict[int, dict]:
        cur = await self.conn.execute("SELECT user_id, day, month, year FROM birthdays")
        rows = await cur.fetchall()
        return {row[0]: {"day": row[1], "month": row[2], "year": row[3]} for row in rows}

    async def get_birthdays_for_day(self, day: int, month: int) -> dict[int, dict]:
        cur = await self.conn.execute(
            "SELECT user_id, day, month, year FROM birthdays WHERE day = ? AND month = ?",
            (day, month),
        )
        rows = await cur.fetchall()
        return {row[0]: {"day": row[1], "month": row[2], "year": row[3]} for row in rows}

    # ---------- birthday calendar messages ----------

    async def get_calendar_messages(self) -> dict[int, int]:
        cur = await self.conn.execute("SELECT channel_id, message_id FROM birthday_calendar_messages")
        rows = await cur.fetchall()
        return {row[0]: row[1] for row in rows}

    async def set_calendar_message(self, channel_id: int, message_id: int) -> None:
        await self.conn.execute(
            """
            INSERT INTO birthday_calendar_messages (channel_id, message_id) VALUES (?, ?)
            ON CONFLICT (channel_id) DO UPDATE SET message_id = excluded.message_id
            """,
            (channel_id, message_id),
        )
        await self.conn.commit()

    async def remove_calendar_message(self, channel_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM birthday_calendar_messages WHERE channel_id = ?", (channel_id,)
        )
        await self.conn.commit()
