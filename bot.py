#Pixel System

import discord
import os
from dotenv import load_dotenv
from discord.ext import commands

# Modules
from modules.selfroles import RoleView01, RoleView02
from modules.self_cute_roles import cute_roles

# -------------------------------------------------------

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment ERROR")

# -------------------------------------------------------
# Selfroles Embed
# -------------------------------------------------------
EMBED_IMAGE_URL01 = "attachment://selfroles-bg.gif"
EMBED_COLOR01     = discord.Color.purple()
EMBED_TITLE01     = "𝐒𝐄𝐋𝐅-𝐑𝐎𝐋𝐄𝐒 🌂"
EMBED_DESC01      = (
    "H𝗂𝖾𝗋 𝗄𝖺𝗇𝗇𝗌𝗍 𝖽𝗎 𝖽𝗂𝗋 𝗆𝗂𝗍 𝖾𝗂𝗇𝖾𝗆 𝗄𝗅𝗂𝖼𝗄 𝖽𝖾𝗂𝗇𝖾 𝗋𝗈𝗅𝗅𝖾𝗇 𝖺𝗎𝗌𝗐ä𝗁𝗅𝖾𝗇!\n"
    "Wä𝗁𝗅𝖾 𝗓.𝖻. 𝖽𝖾𝗂𝗇 𝖺𝗅𝗍𝖾𝗋, 𝖽𝖾𝗂𝗇𝖾 𝗅𝗂𝖾𝖻𝗅𝗂𝗇𝗀𝗌𝗌𝗉𝗂𝖾𝗅𝖾 𝗈𝖽𝖾𝗋 𝗉𝗂𝗇𝗀-𝗋𝗈𝗅𝗅𝖾𝗇, 𝖽𝖺𝗆𝗂𝗍 𝖺𝗇𝖽𝖾𝗋𝖾 𝗆𝗂𝗍𝗀𝗅𝗂𝖾𝖽𝖾𝗋 𝗀𝗅𝖾𝗂𝖼𝗁 𝗌𝖾𝗁𝖾𝗇 𝗄ö𝗇𝗇𝖾𝗇, 𝗐𝖺𝗌 𝗓𝗎 𝖽𝗂𝗋 𝗉𝖺𝗌𝗌𝗍."
    "K𝖾𝗂𝗇𝖾 𝗌𝗈𝗋𝗀𝖾, 𝖽𝗎 𝗄𝖺𝗇𝗇𝗌𝗍 𝖽𝖾𝗂𝗇𝖾 𝗋𝗈𝗅𝗅𝖾𝗇 𝗃𝖾𝖽𝖾𝗋𝗓𝖾𝗂𝗍 ä𝗇𝖽𝖾𝗋𝗇 𝗈𝖽𝖾𝗋 𝖾𝗇𝗍𝖿𝖾𝗋𝗇𝖾𝗇."
)


EMBED_IMAGE_URL02 = "attachment://cute-roles.gif"
EMBED_COLOR02     = discord.Color.purple()
EMBED_TITLE02     = "⋆𖦹 𝗌𝖾𝗅𝖿 𝖼𝗎𝗍𝗂𝖾 𝗋𝗈𝗅𝖾𝗌ˎˊ˗⭑.ᐟ"
EMBED_DESC02      = ("𝗐ä𝗁𝗅𝖾 𝗁𝗂𝖾𝗋 𝗋𝗈𝗅𝗅𝖾𝗇, 𝖽𝗂𝖾 𝖺𝗆 𝖻𝖾𝗌𝗍𝖾𝗇 𝗓𝗎 𝖽𝗂𝗋 𝗉𝖺𝗌𝗌𝖾𝗇!\n" 
                    "𝗈𝖻 𝖽𝗎 𝖾𝗂𝗇 𝗌𝗅𝖾𝖾𝗉𝗒𝗁𝖾𝖺𝖽, 𝖾𝗂𝗇𝖾 𝗌ü𝗌𝗌𝗆𝖺𝗎𝗌, 𝖾𝗁𝖾𝗋 𝗂𝗇𝗍𝗋𝗈𝗏𝖾𝗋𝗍𝗂𝖾𝗋𝗍 𝗈𝖽𝖾𝗋 𝖾𝗂𝗇 𝗀𝖺𝗆𝖾𝗋 𝖻𝗂𝗌𝗍, 𝗆𝗂𝗍 𝖽𝖾𝗇 𝗋𝗈𝗅𝗅𝖾𝗇 𝗄ö𝗇𝗇𝖾𝗇 𝖺𝗇𝖽𝖾𝗋𝖾 𝗀𝗅𝖾𝗂𝖼𝗁 𝗌𝖾𝗁𝖾𝗇, 𝗐𝖺𝗌 𝖽𝗂𝖼𝗁 𝖺𝗎𝗌𝗆𝖺𝖼𝗁𝗍. "
                    "𝗌𝗎𝖼𝗁 𝖽𝗂𝗋 𝖾𝗂𝗇𝖿𝖺𝖼𝗁 𝖽𝗂𝖾 𝗋𝗈𝗅𝗅𝖾𝗇 𝖺𝗎𝗌, 𝖽𝗂𝖾 𝗓𝗎 𝖽𝖾𝗂𝗇𝖾𝗋 𝗉𝖾𝗋𝗌ö𝗇𝗅𝗂𝖼𝗁𝗄𝖾𝗂𝗍 𝗉𝖺𝗌𝗌𝖾𝗇! 💤")


ADMIN_ROLES  =  (1525603628339957947, 1525603628339957944)

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
    await bot.load_extension("modules.log")

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
        bot.add_view(cute_roles())


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
    embed01 = discord.Embed(title=EMBED_TITLE01, description=EMBED_DESC01, color=EMBED_COLOR01)
    embed01.set_image(url=EMBED_IMAGE_URL01)
    return embed01

def build_cute_roles_embed() -> discord.Embed:
    embed02 = discord.Embed(title=EMBED_TITLE02, description=EMBED_DESC02, color=EMBED_COLOR02)
    embed02.set_image(url=EMBED_IMAGE_URL02)
    return embed02

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

    
    await ctx.send(file=file, embed=build_selfroles_embed())
    await ctx.send(view=RoleView01())
    await ctx.send(view=RoleView02())




@bot.command()
@commands.has_any_role(*ADMIN_ROLES)
async def cute_role(ctx):
    file = discord.File("assets/cute_role.gif", filename="cute_role.gif")

    selfroles_ids = {"select_aesthetic", "select_holy_triangle", "select_vibes", "select_character", "select_holy triangle"}
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

    
    await ctx.send(file=file, embed=build_cute_roles_embed(), view=cute_roles())



# -------------------------------------------------------
# Start
# -------------------------------------------------------

if __name__ == "__main__":
    bot.run(TOKEN)