#Atlas System

import discord
import os
from dotenv import load_dotenv
from discord.ext import commands

# Modules
from modules.selfroles import RoleView01, RoleView02

# -------------------------------------------------------

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment ERROR")

# -------------------------------------------------------
# Selfroles Embed
# -------------------------------------------------------
EMBED_IMAGE_URL = "attachment://selfroles-bg.gif"
EMBED_COLOR     = discord.Color.purple()
EMBED_TITLE     = "Selfroles"
EMBED_DESC      = (
    "Zeig der Community wer du bist!\n"
    "Du kannst Rollen jederzeit wechseln oder entfernen."
)

ADMIN_ROLES     = (1525603628339957947, 1525603628339957944)

# -------------------------------------------------------
# Bot Setup
# -------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
)


@bot.event
async def setup_hook():
    await bot.load_extension("modules.onboarding")

# -------------------------------------------------------
# Events
# -------------------------------------------------------

@bot.event
async def on_ready():
    print(f"\n{'─'*45}")
    print(f"  ✅  Eingeloggt als : {bot.user} ({bot.user.id})")
    print(f"  📡  Server        : {len(bot.guilds)}")

    # --- Selfrole Views ---
    if not bot.persistent_views:
        bot.add_view(RoleView01())
        bot.add_view(RoleView02())


@bot.event
async def on_command_error(ctx, error):
    """Fehlerhandler für Prefix-Commands (!selfroles, …)"""
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("Du hast keine Berechtigung diesen Befehl auszuführen.", delete_after=3)
    else:
        raise error


# -------------------------------------------------------
# Embed Builder
# -------------------------------------------------------

def build_selfroles_embed() -> discord.Embed:
    embed = discord.Embed(title=EMBED_TITLE, description=EMBED_DESC, color=EMBED_COLOR)
    embed.set_image(url=EMBED_IMAGE_URL)
    return embed

# -------------------------------------------------------
# Prefix-Commands
# -------------------------------------------------------

@bot.command()
@commands.has_any_role(*ADMIN_ROLES)
async def selfroles(ctx):
    file = discord.File("assets/selfroles-bg.gif", filename="selfroles-bg.gif")

    selfroles_ids = {"select_gender", "select_age", "select_state", "select_dm_status", "select_games", "select_ping"}
    async for message in ctx.channel.history(limit=50):
        if message.author == bot.user:
            component_ids = {
                component.custom_id
                for row in message.components
                for component in row.children
                if hasattr(component, "custom_id")
            }
            if component_ids & selfroles_ids:
                try:
                    await message.delete()
                except discord.HTTPException:
                    pass

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass


    await ctx.send("**Selfroles**")
    await ctx.send(file=file)
    await ctx.send(view=RoleView01())
    await ctx.send(view=RoleView02())

# -------------------------------------------------------
# Start
# -------------------------------------------------------

if __name__ == "__main__":
    bot.run(TOKEN)