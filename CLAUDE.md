# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Pixel is a Discord bot (discord.py) for the "zen arcade" Discord server. It is a single-guild bot: most behavior is gated to one hardcoded guild via IDs in `config.py`, and text in embeds/messages is German.

## Running the bot

- Entry point: `python bot.py` (runs the `ZenArcadeBot` defined there).
- Requires `DISCORD_TOKEN` in the environment or a `.env` file (see `.env.example`); loaded via `python-dotenv` if installed, otherwise `.env` is silently skipped and the bot exits with an error at startup if no token is found.
- Install deps: `pip install -r requirements.txt`. Note: `discord` and `discord.py` (and `dotenv`/`python-dotenv`) are two different PyPI packages that both install into the same top-level module namespace — only `discord.py` and `python-dotenv` belong in `requirements.txt`; never add the other two back.
- There is no test suite, linter, or build step configured in this repo.
- `config.GUILD_ID` controls slash-command sync: if set, commands sync instantly to that guild only (`tree.copy_global_to` + `tree.sync(guild=...)`); commands only sync globally (slow, up to 1h propagation) if `GUILD_ID` is falsy.

## Architecture

`bot.py` is the single composition root for the whole bot — everything (including the leveling system) loads through it; there is no separate entry point anymore.
- Defines `ZenArcadeBot(commands.Bot)`, admin role IDs (`ADMIN_ROLES`), and loads a fixed list of cogs as extensions (`INITIAL_EXTENSIONS`): `ticket_system.panels`, `onboarding`, `counting`, `log`, `fibo`, `number_guessing`, `lvl_system.cogs.leveling`.
- `setup_hook` connects `self.db` (a `modules.lvl_system.database.Database`, SQLite via `aiosqlite`) **before** extensions load, because `lvl_system/cogs/leveling.py::setup()` reads `bot.db`. `close()` is overridden to close that connection on shutdown.
- Selfroles (`modules/selfroles.py`, `modules/self_cute_roles.py`) are **not** cogs/extensions — their persistent views are registered manually in `setup_hook`, and their posting commands (`!selfroles`, `!cute_role`) live directly in `bot.py` as prefix commands guarded by `@commands.has_any_role(*ADMIN_ROLES)`. Both commands load their image asset via `discord.File(ASSETS_DIR / "...")`, where `ASSETS_DIR` is resolved from `bot.py`'s own location — this makes them independent of the process's current working directory.
- `modules/counting.py` imports `ADMIN_ROLES` back from `bot.py` (`from bot import ADMIN_ROLES`). This only works because extensions are loaded lazily inside `setup_hook` (i.e. after `bot.py` has fully executed at import time) — don't move that import to module load time in `bot.py` without checking for a real circular-import break.
- All persistent (`timeout=None`) views must be re-registered via `bot.add_view(...)` in `setup_hook` on every restart, since discord.py doesn't restore them automatically. `modules/ticket_system/views.py::all_persistent_views()` centralizes this for the ticket system.
- `on_command_error` is the single global handler for **prefix** commands (`!selfroles`, `!fibo`, `!set`, …) and catches `MissingAnyRole`/`MissingPermissions`/`MissingRole` with one friendly message. A cog-level `@command.error` handler (e.g. `counting.py`'s `set_number_error`) takes priority over this global one for that specific command when present — if you add a new prefix command with its own local error handler, make sure it checks the exception type `has_any_role`/`has_permissions` actually raises (`MissingAnyRole` vs `MissingPermissions` are not interchangeable).

`config.py` is a flat module of constants (channel/role/category Discord snowflake IDs, embed color, emojis, ticket limits) — no env-based overrides except the bot token. `SUPPORT_CATEGORY_ID == APPLICATION_CATEGORY_ID` and `SUPPORT_STAFF_ROLE_ID == APPLICATION_STAFF_ROLE_ID` intentionally point at the same IDs (single support-staff role/category serving both ticket kinds) — left as-is.

### Ticket system (`modules/ticket_system/`)

The most substantial subsystem. Layers:
- `panels.py` — slash commands (`/setup-support`, `/setup-bewerbung`) that post the entry-point panel embeds/views into a channel.
- `views.py` — all Discord UI: `SupportPanelView`, `ApplicationPanelView` (button → opens a ticket or an application modal), `TicketControlView` (Claim/Close/Transcript/Add/Remove/Delete buttons posted inside each ticket channel), plus short-lived ephemeral helper views for user add/remove and delete confirmation.
- `modals.py` — application forms (Supporter/Designer/Event Manager); `on_submit` calls into `ticket_manager.create_ticket` via a shared `_finish_application` helper.
- `ticket_manager.py` — all ticket business logic (create/close/claim/delete/add/remove user, transcript generation), used by both `views.py` and `modals.py` so the logic exists in one place. `create_ticket` reserves a ticket slot via `store.reserve_ticket_slot(...)`, which checks the per-user open-ticket limit and increments the channel-numbering counter atomically under one lock — don't split that check-then-increment back into two separate store calls, that reintroduces a race where rapid double-clicks can exceed `MAX_OPEN_*_TICKETS_PER_USER`.
- `permissions.py` — role/permission checks (`is_staff_for_ticket_type`, `is_admin`, etc.), all keyed off `config.py` role IDs.
- `storage.py` — persistence layer: `TicketData` dataclass + `TicketStore`, backed by a single JSON file at `data/tickets.json` (path resolved as `<repo_root>/data/tickets.json`, migrated here from the old `data_ticket/` location). All reads/writes go through one `asyncio.Lock()`, the actual file I/O is offloaded via `asyncio.to_thread` so it doesn't block the event loop, and writes are atomic (write to `.tmp`, then `os.replace`). Malformed ticket entries (missing `opener_id`/`type`) are skipped rather than raising `KeyError`.
- `transcript.py` — builds an HTML transcript of a channel's message history for the Transcript button / delete-log.

Ticket "type" strings (`"support"`, `"application_supporter"`, `"application_designer"`, `"application_eventmanager"`) drive category placement, staff-role resolution, and per-type open-ticket limits (`config.MAX_OPEN_SUPPORT_TICKETS_PER_USER` / `MAX_OPEN_APPLICATION_TICKETS_PER_USER`) — application sub-types share one combined limit/category via the `"application"` prefix check in `ticket_manager._category_and_prefix`/`create_ticket`.

### Leveling system (`modules/lvl_system/`)

Integrated as a regular cog (`lvl_system.cogs.leveling`), loaded through the main `ZenArcadeBot` — it is **not** a separate bot process. All internal imports already use the absolute `modules.lvl_system...` form, which is what makes this work when loaded from the repo root.
- `database.py` — `Database` wrapper around one long-lived `aiosqlite` connection (WAL mode), storing per-guild users/XP, level-role mappings, and per-guild leveling config (`guild_config` table — cooldown, XP range, voice-XP rate, levelup channel/message, etc., all editable live via `/level-config`). The connection is owned by `ZenArcadeBot.db`, created in `setup_hook` and closed in `close()`.
- `cogs/leveling.py` — text-XP (`on_message`, cooldown-gated), voice-XP (`tasks.loop` every 60s, skips solo voice channels and the guild's AFK channel), automatic level-role assignment, and slash commands: `/rank`, `/leaderboard`, `/xp add|remove|set|reset|reset-server` (admin), `/level-config show|text-xp|voice-xp|levelup-channel` (admin).
- `utils/leveling_math.py` — pure XP curve (`5*level² + 50*level + 100` XP per level).
- `utils/rank_card.py` — generates the `/rank` PNG via PIL; loads fonts from the repo-root `assets/fonts/DejaVuSans{,-Bold}.ttf` (shared with `onboarding.py`'s welcome image, moved there from the old per-module `assets_lvl/` copy) so a font is always available regardless of host OS.
- Requires the `voice_states` intent (set in `bot.py`) for the voice-XP loop's channel-member checks, and the `aiosqlite` package (in `requirements.txt`).
- `scripts/dedupe_commands.py` is a standalone maintenance script (not imported by the bot) for removing duplicate global/guild slash commands via the raw Discord API; run manually with `DISCORD_TOKEN` (and optionally `DEV_GUILD_ID`) set. It needs the `requests` package, which is intentionally **not** in `requirements.txt` since it's a dev-only tool, not a bot runtime dependency.

### Other cogs

- `onboarding.py` — two cogs: `Onboarding` (auto-assigns a fixed `ROLE_IDS` list on member join) and `WelcomeImageCog` (generates a PIL-composited welcome image from the member's avatar + `assets/background.png`; PIL work runs via `asyncio.to_thread` to avoid blocking the event loop; fonts come from the shared `assets/fonts/` DejaVu files, same as the rank card).
- `counting.py` — counting-game cog for one channel (`COUNTING_CHANNEL_ID`), with a hardcoded `ACHIEVEMENTS` dict of milestone numbers, plus `!set` admin override.
- `log.py` — mod/audit logging cog, posts to three separate log channels (message edits/deletes, member join/leave/kick, ban/unban) with 1s audit-log-lag delay before attributing kicks.
- `fibo.py` — bump-reminder cog (`!fibo`), a `tasks.loop` polling every 15s against a stored `next_bump_at` timestamp.
- `number_guessing.py` — `/number` guessing-game cog; in-memory per-user game state (`self.games` dict), not persisted.

All Discord snowflake IDs (roles, channels, categories) throughout the codebase are hardcoded per-file rather than centralized — `config.py` holds the ticket-system-relevant ones, but `onboarding.py`, `counting.py`, and `log.py` each define their own channel/role ID constants at the top of the file.
