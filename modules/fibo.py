from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks


REMINDER_CHANNEL_ID = 1525603629548179610
BUMP_INTERVAL = timedelta(hours=2)


class BumpReminder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.next_bump_at: datetime | None = None
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def fibo(self, ctx: commands.Context):
        self.next_bump_at = datetime.now(timezone.utc) + BUMP_INTERVAL

        await ctx.send("✅ Bump-Timer gestartet. Nächster Ping in 2 Stunden.")

    @tasks.loop(seconds=15)
    async def check_loop(self):
        if self.next_bump_at is None:
            return

        if datetime.now(timezone.utc) < self.next_bump_at:
            return

        channel = self.bot.get_channel(REMINDER_CHANNEL_ID)

        if channel:
            await channel.send(
                "⏰ @here Zeit für den nächsten `/bump`!",
                allowed_mentions=discord.AllowedMentions(everyone=True)
            )

        self.next_bump_at += BUMP_INTERVAL

    @check_loop.before_loop
    async def before_check_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(BumpReminder(bot))