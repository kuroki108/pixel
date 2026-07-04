# Pixel System

import os

import discord
from discord.ext import commands
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not found.")


# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# Create bot
bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"\n{'─' * 45}")
    print(f"✅ Logged in as : {bot.user}")


@bot.command()
async def ping(ctx):
    """Replies with Pong."""
    await ctx.send("🏓 Pong!")


if __name__ == "__main__":
    bot.run(TOKEN)