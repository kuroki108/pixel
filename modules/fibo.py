from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks


REMINDER_CHANNEL_ID = 1525603629548179610
BUMP_ROLE_ID = 1525603628256329916
BUMP_INTERVAL = timedelta(hours=2)

DISBOARD_BOT_ID = 302050872383242240


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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != REMINDER_CHANNEL_ID:
            return

        if message.author.id != DISBOARD_BOT_ID:
            return

        if not message.embeds:
            return

        embed = message.embeds[0]
        description = embed.description or ""

        if "Bump done" not in description:
            return

        self.next_bump_at = datetime.now(timezone.utc) + BUMP_INTERVAL

    @tasks.loop(seconds=15)
    async def check_loop(self):
        if self.next_bump_at is None:
            return

        if datetime.now(timezone.utc) < self.next_bump_at:
            return

        channel = self.bot.get_channel(REMINDER_CHANNEL_ID)

        if channel:
            role_mention = f"<@&{BUMP_ROLE_ID}>"

            await channel.send(
                f"⏰ {role_mention} Zeit für den nächsten `/bump`!",
                allowed_mentions=discord.AllowedMentions(
                    roles=[discord.Object(id=BUMP_ROLE_ID)] if BUMP_ROLE_ID else False,
                    everyone=not BUMP_ROLE_ID
                )
            )

        self.next_bump_at = None

    @check_loop.before_loop
    async def before_check_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(BumpReminder(bot))