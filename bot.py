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
EMBED_IMAGE_URL = "attachment://banner.png"
EMBED_COLOR     = discord.Color.purple()
EMBED_TITLE     = "Selfroles"
EMBED_DESC      = (
    "Zeig der Community wer du bist!\n"
    "Du kannst Rollen jederzeit wechseln oder entfernen."
)

COLOR_IMAGE_URL = "attachment://banner_color.png"
COLOR_COLOR     = discord.Color.purple()
COLOR_TITLE     = "🎨 Wähl deine Farbe"
COLOR_DESC      = (
    "Als Booster hast du Zugang zu exklusiven Farbrollen!\n"
    "Such dir eine Farbe aus und mach deinen Namen zum Hingucker."
)

ADMIN_ROLES     = (1522925471912820816, 1522925471740989539, 1519697116212232232)
BOOSTER_ROLE_ID = 1435948381355900989

# -------------------------------------------------------
# Bot Setup
# -------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# -------------------------------------------------------
# Events
# -------------------------------------------------------

@bot.event
async def on_ready():
    print(f"\n{'─'*45}")
    print(f"  ✅  Eingeloggt als : {bot.user}")

    # --- Selfrole Views ---
    if not bot.persistent_views:
        bot.add_view(RoleView01())
        bot.add_view(RoleView02())





@bot.event
async def on_command_error(ctx, error):
    """Fehlerhandler für Prefix-Commands (!selfroles, !color, …)"""
    if isinstance(error, (commands.MissingRole, commands.MissingAnyRole)):
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


@bot.command()
async def ping(ctx):
    await ctx.send("Pong 🏓")


@bot.command()
@commands.has_any_role(*ADMIN_ROLES)
async def selfroles(ctx):
    file = discord.File("assets/banner.png", filename="banner.png")

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

    await ctx.send(file=file, embed=build_selfroles_embed(), view=RoleView01())
    await ctx.send(view=RoleView02())


@bot.command()
@commands.has_any_role(*ADMIN_ROLES)
async def color(ctx):
    file = discord.File("assets/banner_color.png", filename="banner_color.png")

    async for message in ctx.channel.history(limit=50):
        if message.author == bot.user and (message.components or message.embeds):
            try:
                await message.delete()
            except discord.HTTPException:
                pass


# -------------------------------------------------------
# Start
# -------------------------------------------------------

if __name__ == "__main__":
    bot.run(TOKEN)