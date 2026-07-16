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
EMBED_TITLE     = "𝐒𝐄𝐋𝐅-𝐑𝐎𝐋𝐄𝐒 🌂"
EMBED_DESC      = (
    "H𝗂𝖾𝗋 𝗄𝖺𝗇𝗇𝗌𝗍 𝖽𝗎 𝖽𝗂𝗋 𝗆𝗂𝗍 𝖾𝗂𝗇𝖾𝗆 𝗄𝗅𝗂𝖼𝗄 𝖽𝖾𝗂𝗇𝖾 𝗋𝗈𝗅𝗅𝖾𝗇 𝖺𝗎𝗌𝗐ä𝗁𝗅𝖾𝗇!\n"
    "Wä𝗁𝗅𝖾 𝗓.𝖻. 𝖽𝖾𝗂𝗇 𝖺𝗅𝗍𝖾𝗋, 𝖽𝖾𝗂𝗇𝖾 𝗅𝗂𝖾𝖻𝗅𝗂𝗇𝗀𝗌𝗌𝗉𝗂𝖾𝗅𝖾 𝗈𝖽𝖾𝗋 𝗉𝗂𝗇𝗀-𝗋𝗈𝗅𝗅𝖾𝗇, 𝖽𝖺𝗆𝗂𝗍 𝖺𝗇𝖽𝖾𝗋𝖾 𝗆𝗂𝗍𝗀𝗅𝗂𝖾𝖽𝖾𝗋 𝗀𝗅𝖾𝗂𝖼𝗁 𝗌𝖾𝗁𝖾𝗇 𝗄ö𝗇𝗇𝖾𝗇, 𝗐𝖺𝗌 𝗓𝗎 𝖽𝗂𝗋 𝗉𝖺𝗌𝗌𝗍. \n"
    "K𝖾𝗂𝗇𝖾 𝗌𝗈𝗋𝗀𝖾, 𝖽𝗎 𝗄𝖺𝗇𝗇𝗌𝗍 𝖽𝖾𝗂𝗇𝖾 𝗋𝗈𝗅𝗅𝖾𝗇 𝗃𝖾𝖽𝖾𝗋𝗓𝖾𝗂𝗍 ä𝗇𝖽𝖾𝗋𝗇 𝗈𝖽𝖾𝗋 𝖾𝗇𝗍𝖿𝖾𝗋𝗇𝖾𝗇."
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
    await bot.load_extension("modules.counting")

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

    
    await ctx.send(file=file)
    await ctx.send(embed=build_selfroles_embed())
    await ctx.send(view=RoleView01())
    await ctx.send(view=RoleView02())

# -------------------------------------------------------
# Start
# -------------------------------------------------------

if __name__ == "__main__":
    bot.run(TOKEN)