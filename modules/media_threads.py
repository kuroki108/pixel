import discord
from discord.ext import commands

from config import MEDIA_CHANNEL_ID_1, SELFIE_CHANNEL_ID_1, VORSTELLUNG_CHANNEL_ID_1

MEDIA_CHANNEL_IDS = {MEDIA_CHANNEL_ID_1, SELFIE_CHANNEL_ID_1}
TEXT_ONLY_THREAD_CHANNEL_IDS = {VORSTELLUNG_CHANNEL_ID_1}


class MediaThreads(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if message.channel.id in MEDIA_CHANNEL_IDS:
            if not message.attachments:
                await message.delete()
                return
        elif message.channel.id in TEXT_ONLY_THREAD_CHANNEL_IDS:
            pass  # kein Attachment nötig, direkt Thread erstellen
        else:
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
