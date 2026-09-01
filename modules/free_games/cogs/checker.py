import logging
from datetime import datetime, timezone

import aiohttp
import discord
from discord.ext import commands, tasks

import config
from modules.database import Database
from modules.free_games.embeds import build_embed, build_view
from modules.free_games.sources import epic, steam

log = logging.getLogger("free_games.checker")

_SOURCES = (epic, steam)


class FreeGamesChecker(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database):
        self.bot = bot
        self.db = db
        self.session: aiohttp.ClientSession | None = None
        self.check_deals.start()

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession()

    async def cog_unload(self) -> None:
        self.check_deals.cancel()
        if self.session:
            await self.session.close()

    @tasks.loop(minutes=config.FREEGAMES_CHECK_INTERVAL_MINUTES)
    async def check_deals(self) -> None:
        channel = self.bot.get_channel(config.FREEGAMES_CHANNEL_ID)
        if channel is None:
            log.warning("FREEGAMES_CHANNEL_ID %s nicht gefunden -- überspringe Check.", config.FREEGAMES_CHANNEL_ID)
            return

        settings = await self.db.get_free_games_settings(channel.guild.id)
        role = channel.guild.get_role(config.FREEGAMES_PING_ROLE_ID) if config.FREEGAMES_PING_ROLE_ID else None

        for source in _SOURCES:
            try:
                deals = await source.fetch_candidates(self.session)
            except (aiohttp.ClientError, KeyError, ValueError) as exc:
                log.warning("Konnte Angebote von %s nicht laden: %s", source.__name__, exc)
                continue

            for deal in deals:
                if not deal.is_free and settings.only_free:
                    continue
                if await self.db.is_free_game_deal_posted(deal.deal_id):
                    continue

                deal = await source.enrich(self.session, deal)
                try:
                    await channel.send(
                        content=role.mention if role else None,
                        embed=build_embed(deal),
                        view=build_view(deal),
                    )
                except discord.HTTPException as exc:
                    log.warning("Konnte Angebot %s nicht posten: %s", deal.deal_id, exc)
                    continue
                await self.db.mark_free_game_deal_posted(deal.deal_id)

        await self.db.set_free_games_state("last_check", datetime.now(timezone.utc).isoformat())

    @check_deals.before_loop
    async def before_check_deals(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(FreeGamesChecker(bot, bot.db))
