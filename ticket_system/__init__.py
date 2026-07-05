async def setup(bot):
    await bot.load_extension("ticket_system.cogs.ticket_commands")
    await bot.load_extension("ticket_system.cogs.ticket_panel")
    await bot.load_extension("ticket_system.cogs.application_commands")
