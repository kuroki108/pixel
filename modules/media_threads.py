import discord
from discord.ext import commands

MEDIA_CHANNEL_ID_1 = 1525603629321683005
MEDIA_CHANNEL_IDS = {MEDIA_CHANNEL_ID_1}


class MediaThreads(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.channel.id not in MEDIA_CHANNEL_IDS:
            return

        if not message.attachments:
            await message.delete()
            return

        try:
            await message.create_thread(
                name=f"💬 Talk about it • {message.author.display_name}",
                auto_archive_duration=1440,
            )
        except discord.HTTPException as e:
            print(f"Thread konnte nicht erstellt werden: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(MediaThreads(bot))
