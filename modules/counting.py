import discord
from discord.ext import commands
from bot import ADMIN_ROLES

COUNTING_CHANNEL_ID = 1525603629548179608

ACHIEVEMENTS = {
    42: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Die Antwort**) freigeschalten! 🎉",
        "42?! Die Antwort auf alles.",
    ),
    69: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Nice**) freigeschalten! 🎉",
        "69?! 😏 Nice.",
    ),
    100: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Hunderter**) freigeschalten! 🎉",
        "Erreiche die erste dreistellige Zahl. 💯",
    ),
    123: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Los geht's**) freigeschalten! 🎉",
        "Eine einfache Zahlenfolge.",
    ),
    200: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Doppelte Hunderter**) freigeschalten! 🎉",
        "200 erreicht – weiter so!",
    ),
    222: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Doppeltes Glück**) freigeschalten! 🎉",
        "Drei Zweien.",
    ),
    256: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Byte**) freigeschalten! 🎉",
        "Ein Klassiker der Informatik.",
    ),
    300: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Spartaner**) freigeschalten! 🎉",
        '"This is Sparta!"',
    ),
    360: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Full Circle**) freigeschalten! 🎉",
        "Wie eine volle Drehung.",
    ),
    365: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Ein ganzes Jahr**) freigeschalten! 🎉",
        "365 Tage.",
    ),
    404: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Not Found**) freigeschalten! 🎉",
        "Fehler 404.",
    ),
    500: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Halb zu Tausend**) freigeschalten! 🎉",
        "Ein großer Meilenstein.",
    ),
    512: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Speicherblock**) freigeschalten! 🎉",
        "2⁹.",
    ),
    555: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Hotline**) freigeschalten! 🎉",
        "Drei Fünfen.",
    ),
    666: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Dämonisch**) freigeschalten! 🎉",
        "Die Zahl des Tieres.",
    ),
    720: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Zwei Runden**) freigeschalten! 🎉",
        "720° Drehung.",
    ),
    777: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Jackpot**) freigeschalten! 🎉",
        "Glückszahl.",
    ),
    800: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Höher hinaus**) freigeschalten! 🎉",
        "Auf zum Tausender.",
    ),
    888: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Glücksdrache**) freigeschalten! 🎉",
        "Glückszahl in Asien.",
    ),
    900: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Endspurt**) freigeschalten! 🎉",
        "Nur noch 100 bis 1000.",
    ),
    999: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Fast geschafft**) freigeschalten! 🎉",
        "Die letzte dreistellige Zahl.",
    ),
    1000: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Vierstellig**) freigeschalten! 🎉",
        "Der erste Tausender.",
    ),
    1024: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Kibibyte**) freigeschalten! 🎉",
        "2¹⁰ – jeder Informatiker kennt sie.",
    ),
    1111: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Wunschzeit**) freigeschalten! 🎉",
        "Vier gleiche Ziffern.",
    ),
    1234: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Eins, Zwei, Drei, Vier**) freigeschalten! 🎉",
        "Perfekte Folge.",
    ),
    1337: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Leet**) freigeschalten! 🎉",
        "Der Klassiker der Coder und Hacker.",
    ),
    1444: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Vier gewinnt**) freigeschalten! 🎉",
        "Viermal die Vier mit Verstärkung.",
    ),
    1500: (
        "🎉 Glückwunsch {user}! Du hast das Achievement (**Anderthalbtausend**) freigeschalten! 🎉",
        "Der nächste große Meilenstein.",
    ),
}



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

        if self.count in ACHIEVEMENTS:
            title, description = ACHIEVEMENTS[self.count]
            achievement_lines = [title.format(user=message.author.mention)]
            if description:
                achievement_lines.append(description)
            await message.channel.send("\n".join(achievement_lines))


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