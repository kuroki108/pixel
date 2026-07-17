import discord
from discord.ext import commands
from bot import ADMIN_ROLES

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

    @commands.command(name="set")
    @commands.has_any_role(*ADMIN_ROLES)
    async def set_number(self, ctx: commands.Context, number: int):
        """Setzt den aktuellen Zählerstand (die nächste erwartete Zahl ist number+1)."""
        if number < 0:
            await ctx.send("Die Zahl darf nicht negativ sein.")
            return

        self.count = number
        self.last_user_id = None  # Reset, damit niemand fälschlich als "doppelt dran" gilt

        await ctx.send(
            f"Zählerstand wurde auf **{number}** gesetzt. "
            f"Nächste erwartete Zahl: **{number + 1}**"
        )

    @set_number.error
    async def set_number_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Dafür brauchst du Administrator-Rechte.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Bitte eine gültige Zahl angeben, z. B. `!set 41`.")
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(Counting(bot))