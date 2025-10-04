# cogs/meta.py
import discord
from discord.ext import commands
from discord import app_commands
from utils.common import make_embed

class Meta(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping_cmd(self, inter: discord.Interaction):
        await inter.response.send_message(f"Pong! {round(self.bot.latency * 1000)} ms", ephemeral=True)

    @app_commands.command(name="who-am-i", description="Your display name.")
    async def who_am_i(self, inter: discord.Interaction):
        await inter.response.send_message(inter.user.display_name, ephemeral=True)

    @app_commands.command(name="help", description="Show all commands & features.")
    async def help_cmd(self, inter: discord.Interaction):
        desc = (
            "**Encryption**\n"
            "• `/encrypt seed:<text> message:<text> [hidden:false]`\n"
            "• `/decrypt seed:<text> message:<base64> [hidden:true]`\n\n"
            "**Morse**\n"
            "• `/morse-encrypt` • `/morse-decrypt`\n\n"
            "**Clone**\n"
            "• `/clone` • `/clone-embed`\n\n"
            "**Moderation**\n"
            "• `/server-mute` `/server-unmute` `/server-deafen` `/server-undeafen`\n"
            "• `/disconnect-voice` `/move-voice` `/change-nickname` `/print-bot-permissions`\n"
            "• `/court`\n\n"
            "**Truth/Dare & Tests**\n"
            "• `/truth` • `/dare` • `/ricepurity`\n\n"
            "**Games**\n"
            "• `/coinflip` • `/roll` • `/rps` • `/trivia` • `/tictactoe`\n"
        )
        await inter.response.send_message(embed=make_embed("Mega Bot – Commands", desc), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Meta(bot))
