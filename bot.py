from __future__ import annotations

import logging
from pathlib import Path

import discord
from discord.ext import commands

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  

import config
from config import ADMIN_ROLES
from modules.selfroles import RoleView01, RoleView02, build_selfroles_embed
from modules.self_cute_roles import cute_roles, build_cute_roles_embed

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("zen_arcade")

INITIAL_EXTENSIONS = [
    "modules.onboarding",
    "modules.counting",
    "modules.log",
    "modules.media_threads",
]

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
intents.voice_states = True 


class ZenArcadeBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        self.add_view(RoleView01())
        self.add_view(RoleView02())
        self.add_view(cute_roles())

        for extension in INITIAL_EXTENSIONS:
            try:
                await self.load_extension(extension)
                log.info("Extension %s geladen.", extension)
            except Exception as e:
                log.error("Fehler beim Laden von Extension %s: %s", extension, e)

        if config.GUILD_ID:
            guild_obj = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
            log.info("Slash-Commands für Guild %s synchronisiert.", config.GUILD_ID)
        else:
            await self.tree.sync()
            log.info("Slash-Commands global synchronisiert (kann bis zu 1h dauern, bis sie überall sichtbar sind).")

    async def close(self) -> None:
        await super().close()

    async def on_ready(self) -> None:
        log.info("Eingeloggt als %s (ID: %s)", self.user, self.user.id)
        log.info("Bereit! Bot ist aktiv.")
        print(f"\n{'─'*45}")
        print(f"  ✅  Eingeloggt als : {self.user} ({self.user.id})")
        print(f"  📡  Server        : {len(self.guilds)}")
        print(f"{'─'*45}\n")

    async def on_command_error(self, ctx, error):
        """Fehlerhandler für Prefix-Commands (!selfroles, …)"""
        if isinstance(error, (commands.MissingAnyRole, commands.MissingPermissions, commands.MissingRole)):
            await ctx.send("Du hast keine Berechtigung diesen Befehl auszuführen.", delete_after=3)
        else:
            raise error


bot = ZenArcadeBot()


@bot.command()
@commands.has_any_role(*ADMIN_ROLES)
async def selfroles(ctx):
    file = discord.File(ASSETS_DIR / "selfroles-bg.gif", filename="selfroles-bg.gif")

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
    file = discord.File(ASSETS_DIR / "cute_role.gif", filename="cute_role.gif")

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


def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit(
            "Kein Bot-Token gefunden. Setze die Umgebungsvariable DISCORD_TOKEN "
            "(siehe .env.example) bevor du den Bot startest."
        )

    bot.run(config.BOT_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
