import random

import discord
from discord import app_commands
from discord.ext import commands


class NumberGuessing(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = {}

    @app_commands.command(
        name="number",
        description="Starte ein Number-Guessing-Spiel."
    )
    async def number(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        # Neues Spiel starten
        number = random.randint(1, 100)

        self.games[user_id] = {
            "number": number,
            "attempts": 0
        }

        embed = discord.Embed(
            title="🔢 Number Guessing",
            description=(
                "Ich habe mir eine Zahl zwischen **1 und 100** ausgesucht.\n\n"
                "Schreib deine Vermutung in den Chat!"
            ),
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        user_id = message.author.id

        if user_id not in self.games:
            return

        # Nur einzelne Zahlen akzeptieren
        try:
            guess = int(message.content)
        except ValueError:
            return

        game = self.games[user_id]
        game["attempts"] += 1

        number = game["number"]
        attempts = game["attempts"]

        if guess < number:
            await message.reply("⬆️ **Zu niedrig!**")

        elif guess > number:
            await message.reply("⬇️ **Zu hoch!**")

        else:
            embed = discord.Embed(
                title="🎉 Richtig!",
                description=(
                    f"Die Zahl war **{number}**!\n\n"
                    f"Du hast **{attempts} Versuche** gebraucht."
                ),
                color=discord.Color.green()
            )

            await message.reply(embed=embed)

            # Spiel beenden
            del self.games[user_id]


async def setup(bot: commands.Bot):
    await bot.add_cog(NumberGuessing(bot))