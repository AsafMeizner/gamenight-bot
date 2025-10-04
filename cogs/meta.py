# cogs/meta.py
import discord
from discord.ext import commands
from discord import app_commands
from utils.common import make_embed

SECTIONS = {
    "General": (
        "• `/help` – this interactive help\n"
        "• `/ping` – latency\n"
        "• `/who-am-i` – your display name\n"
    ),
    "Encryption": (
        "• `/encrypt seed:<text> message:<text>` – secure AEAD, public embed w/ Decrypt button\n"
        "• `/decrypt seed:<text> message:<base64>` – manual decrypt (hidden by default)\n"
    ),
    "Messaging": (
        "• `/clone target_user message` – send via webhook as display name\n"
        "• `/clone-embed target_user title description [color hex]`\n"
    ),
    "Moderation": (
        "• `/server-mute|unmute|deafen|undeafen`\n"
        "• `/disconnect-voice` `/move-voice` `/change-nickname`\n"
        "• `/print-bot-permissions` `/court user seconds`\n"
    ),
    "Games": (
        "• `/rps [opponent]` – quick match w/ rematch & victory embed\n"
        "• `/tictactoe opponent` – button grid, win/draw embed\n"
        "• `/trivia [questions] [timer] [category]` – Kahoot-style timed trivia\n"
        "• `/guess-song [count]` – Guess the Song in VC (artist, song, album)\n"
    ),
    "Morse & Tests": (
        "• `/morse-encrypt` • `/morse-decrypt`\n"
        "• `/truth` • `/dare` – from data files\n"
        "• `/ricepurity [anonymous]` – interactive test\n"
    ),
    "Audio/Radio": (
        "• `/radio station:<name>` – play a curated radio\n"
        "• `/radio-url url:<stream>` – play a custom radio/stream\n"
        "• `/stop-audio` – stop & leave VC\n"
    ),
}

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300.0)
        self.current = "General"
        self.build_buttons()

    def build_buttons(self):
        self.clear_items()
        # top row tabs
        row_names = ["General", "Encryption", "Messaging", "Moderation", "Games", "Morse & Tests", "Audio/Radio"]
        for i, name in enumerate(row_names):
            self.add_item(self.SectionButton(name, self, row=i//5))
        # support row
        self.add_item(self.InviteButton())
        self.add_item(self.SupportButton())

    class SectionButton(discord.ui.Button):
        def __init__(self, name: str, parent: 'HelpView', row: int = 0):
            super().__init__(label=name, style=discord.ButtonStyle.primary if name == parent.current else discord.ButtonStyle.secondary, row=row)
            self.parent_view = parent
            self.name = name
        async def callback(self, interaction: discord.Interaction):
            self.parent_view.current = self.name
            self.parent_view.build_buttons()
            content = SECTIONS.get(self.name, "—")
            em = make_embed(f"Help – {self.name}", content, discord.Color.blurple())
            em.set_footer(text="Use the buttons to switch categories.")
            if interaction.response.is_done():
                await interaction.followup.edit_message(interaction.message.id, embed=em, view=self.parent_view)
            else:
                await interaction.response.edit_message(embed=em, view=self.parent_view)

    class InviteButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Invite", style=discord.ButtonStyle.link, url="https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2416208976&scope=bot%20applications.commands")
    class SupportButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="FFmpeg Setup", style=discord.ButtonStyle.link, url="https://ffmpeg.org/download.html")

class Meta(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping_cmd(self, inter: discord.Interaction):
        await inter.response.send_message(f"Pong! {round(self.bot.latency * 1000)} ms", ephemeral=True)

    @app_commands.command(name="who-am-i", description="Your display name.")
    async def who_am_i(self, inter: discord.Interaction):
        await inter.response.send_message(inter.user.display_name, ephemeral=True)

    @app_commands.command(name="help", description="Interactive help with categories.")
    async def help_cmd(self, inter: discord.Interaction):
        view = HelpView()
        content = SECTIONS["General"]
        em = make_embed("Help – General", content, discord.Color.blurple())
        em.set_footer(text="Use the buttons to switch categories.")
        await inter.response.send_message(embed=em, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Meta(bot))
