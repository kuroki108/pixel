
import discord
from discord.ext import commands


# Hier die ID des Channels eintragen, in dem gezaehlt werden soll.
# Rechtsklick auf den Channel in Discord -> "ID kopieren"
# (Entwicklermodus muss dafuer in den Discord-Einstellungen aktiviert sein).
COUNTING_CHANNEL_ID = 1525603629548179608



class Counting(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.count = 0
        self.last_user_id = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id != COUNTING_CHANNEL_ID:
            return

        try:
            number = int(message.content.strip())
        except ValueError:
            return  # keine Zahl -> ignorieren, kein Reset

        expected = self.count + 1

        # Gleicher User zweimal hintereinander -> Reset
        if self.last_user_id is not None and message.author.id == self.last_user_id:
            self.count = 0
            self.last_user_id = None
            await message.add_reaction("❌")
            await message.channel.send(
                f"{message.author.mention}, du warst bereits dran. "
                f"Zaehlung zurueckgesetzt. Naechste Zahl: **1**"
            )
            return

        # Falsche Zahl -> Reset
        if number != expected:
            self.count = 0
            self.last_user_id = None
            await message.add_reaction("❌")
            await message.channel.send(
                f"Falsche Zahl! Erwartet wurde **{expected}**. "
                f"Zaehlung zurueckgesetzt. Naechste Zahl: **1**"
            )
            return

        # Richtig
        self.count = number
        self.last_user_id = message.author.id
        await message.add_reaction("✅")


async def setup(bot: commands.Bot):
    await bot.add_cog(Counting(bot))

