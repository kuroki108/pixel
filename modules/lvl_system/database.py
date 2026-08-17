from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

DB_PATH = Path(__file__).parent / "data" / "leveling.sqlite3"

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


class Database:
    """Dünner Wrapper um eine aiosqlite-Connection mit fertigen Queries."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    @classmethod
    async def connect(cls) -> "Database":
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(DB_PATH)
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA foreign_keys=ON;")
        await conn.executescript(SCHEMA)
        await conn.commit()
        return cls(conn)

    async def close(self) -> None:
        await self.conn.close()

    # ---------- users ----------

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
