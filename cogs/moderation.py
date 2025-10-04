# cogs/moderation.py
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="server-mute", description="Server mute a user.")
    async def server_mute(self, inter: discord.Interaction, target_user: discord.Member):
        await target_user.edit(mute=True)
        await inter.response.send_message(f"{target_user.mention} has been server muted.", ephemeral=True)

    @app_commands.command(name="server-unmute", description="Server unmute a user.")
    async def server_unmute(self, inter: discord.Interaction, target_user: discord.Member):
        await target_user.edit(mute=False)
        await inter.response.send_message(f"{target_user.mention} has been server unmuted.", ephemeral=True)

    @app_commands.command(name="server-deafen", description="Server deafen a user.")
    async def server_deafen(self, inter: discord.Interaction, target_user: discord.Member):
        await target_user.edit(deafen=True)
        await inter.response.send_message(f"{target_user.mention} has been server deafened.", ephemeral=True)

    @app_commands.command(name="server-undeafen", description="Server undeafen a user.")
    async def server_undeafen(self, inter: discord.Interaction, target_user: discord.Member):
        await target_user.edit(deafen=False)
        await inter.response.send_message(f"{target_user.mention} has been server undeafened.", ephemeral=True)

    @app_commands.command(name="disconnect-voice", description="Disconnect a user from voice.")
    async def disconnect_voice(self, inter: discord.Interaction, target_user: discord.Member):
        await target_user.edit(voice_channel=None)
        await inter.response.send_message(f"{target_user.mention} has been disconnected.", ephemeral=True)

    @app_commands.command(name="move-voice", description="Move a user to a target voice channel.")
    async def move_voice(self, inter: discord.Interaction, target_user: discord.Member, target_channel: discord.VoiceChannel):
        await target_user.edit(voice_channel=target_channel)
        await inter.response.send_message(f"{target_user.mention} moved to {target_channel.mention}.", ephemeral=True)

    @app_commands.command(name="change-nickname", description="Change a user's server nickname.")
    async def change_nick(self, inter: discord.Interaction, target_user: discord.Member, new_nickname: str):
        await target_user.edit(nick=new_nickname)
        await inter.response.send_message(f"{target_user.mention} nickname changed to **{new_nickname}**.", ephemeral=True)

    @app_commands.command(name="print-bot-permissions", description="Print bot guild permissions.")
    async def print_perms(self, inter: discord.Interaction):
        await inter.response.send_message(f"Bot permissions: `{inter.guild.me.guild_permissions}`", ephemeral=True)

    @app_commands.command(name="court", description="Give 'Jail' role to a user for X seconds, then remove it.")
    async def court_cmd(self, inter: discord.Interaction, user: discord.Member, seconds: app_commands.Range[int, 1, 86400]):
        role = discord.utils.get(inter.guild.roles, name="Jail")
        if not role:
            await inter.response.send_message("Role 'Jail' not found.", ephemeral=True)
            return
        await user.add_roles(role, reason=f"Court by {inter.user} for {seconds}s")
        await inter.response.send_message(f"Sending {user.mention} to court for {seconds} seconds.", ephemeral=True)
        await asyncio.sleep(seconds)
        try:
            await user.remove_roles(role, reason="Court time elapsed")
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
