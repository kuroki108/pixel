import discord
from discord import app_commands
from discord.ext import commands


class Voice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    vc_group = app_commands.Group(name="vc", description="Voice-Moderationsbefehle")

    # ---------------------------------------------------------- /vc move
    @vc_group.command(name="move", description="Verschiebt einen User in einen anderen Voice-Channel")
    @app_commands.describe(user="Der zu verschiebende User", channel="Ziel-Voice-Channel")
    @app_commands.checks.has_permissions(move_members=True)
    async def move(self, interaction: discord.Interaction, user: discord.Member, channel: discord.VoiceChannel):
        if user.voice is None:
            await interaction.response.send_message(f"❌ {user.mention} ist in keinem Voice-Channel.", ephemeral=True)
            return
        await user.move_to(channel)
        await interaction.response.send_message(f"➡️ {user.mention} wurde nach {channel.mention} verschoben.")

    # ---------------------------------------------------- /vc disconnect
    @vc_group.command(name="disconnect", description="Trennt einen User aus dem Voice-Channel")
    @app_commands.describe(user="Der zu trennende User")
    @app_commands.checks.has_permissions(move_members=True)
    async def disconnect(self, interaction: discord.Interaction, user: discord.Member):
        if user.voice is None:
            await interaction.response.send_message(f"❌ {user.mention} ist in keinem Voice-Channel.", ephemeral=True)
            return
        await user.move_to(None)
        await interaction.response.send_message(f"🔌 {user.mention} wurde aus dem Voice-Channel getrennt.")

    # ---------------------------------------------------------- /vc mute
    @vc_group.command(name="mute", description="Server-mutet einen User im Voice-Channel")
    @app_commands.describe(user="Der zu mutende User")
    @app_commands.checks.has_permissions(mute_members=True)
    async def mute(self, interaction: discord.Interaction, user: discord.Member):
        await user.edit(mute=True)
        await interaction.response.send_message(f"🔇 {user.mention} wurde gemuted.")

    # -------------------------------------------------------- /vc unmute
    @vc_group.command(name="unmute", description="Hebt den Server-Mute eines Users auf")
    @app_commands.describe(user="Der zu entmutende User")
    @app_commands.checks.has_permissions(mute_members=True)
    async def unmute(self, interaction: discord.Interaction, user: discord.Member):
        await user.edit(mute=False)
        await interaction.response.send_message(f"🔊 {user.mention} wurde entmuted.")

    # ------------------------------------------------------- /vc muteall
    @vc_group.command(name="muteall", description="Muted alle User in einem Voice-Channel")
    @app_commands.describe(channel="Der Voice-Channel")
    @app_commands.checks.has_permissions(mute_members=True)
    async def muteall(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        await interaction.response.defer()
        count = 0
        for member in channel.members:
            try:
                await member.edit(mute=True)
                count += 1
            except discord.HTTPException:
                continue
        await interaction.followup.send(f"🔇 {count} User in {channel.mention} wurden gemuted.")

    # ----------------------------------------------------- /vc unmuteall
    @vc_group.command(name="unmuteall", description="Entmuted alle User in einem Voice-Channel")
    @app_commands.describe(channel="Der Voice-Channel")
    @app_commands.checks.has_permissions(mute_members=True)
    async def unmuteall(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        await interaction.response.defer()
        count = 0
        for member in channel.members:
            try:
                await member.edit(mute=False)
                count += 1
            except discord.HTTPException:
                continue
        await interaction.followup.send(f"🔊 {count} User in {channel.mention} wurden entmuted.")

    # ------------------------------------------------------- /vc moveall
    @vc_group.command(name="moveall", description="Verschiebt alle User aus einem Voice-Channel in einen anderen")
    @app_commands.describe(channel="Quell-Voice-Channel", ziel="Ziel-Voice-Channel")
    @app_commands.checks.has_permissions(move_members=True)
    async def moveall(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel,
        ziel: discord.VoiceChannel,
    ):
        await interaction.response.defer()
        count = 0
        for member in list(channel.members):
            try:
                await member.move_to(ziel)
                count += 1
            except discord.HTTPException:
                continue
        await interaction.followup.send(
            f"➡️ {count} User wurden von {channel.mention} nach {ziel.mention} verschoben."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Voice(bot))
