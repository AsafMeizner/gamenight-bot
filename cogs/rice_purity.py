# cogs/rice_purity.py
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
from utils.common import DATA_DIR, make_embed

RICE_FILE = DATA_DIR / "rice_purity" / "rice_purity_questions.txt"

def _load_questions(path):
    try:
        return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except FileNotFoundError:
        return []

QUESTIONS = _load_questions(RICE_FILE)

class RicePurityView(discord.ui.View):
    def __init__(self, inter: discord.Interaction, anonymous: bool):
        super().__init__(timeout=300.0)
        self.inter = inter
        self.idx = 0
        self.score = 100
        self.anon = anonymous
        self.msg: Optional[discord.Message] = None

    async def show_q(self):
        if self.idx >= len(QUESTIONS):
            who = "Anonymous User" if self.anon else self.inter.user.mention
            text = f"{who}'s Rice Purity score is: **{self.score}** 😈"
            if self.msg:
                await self.msg.edit(embed=make_embed("Rice Purity – Result", text, discord.Color.brand_red()), view=None)
            else:
                await self.inter.followup.send(text, ephemeral=self.anon)
            return
        q = QUESTIONS[self.idx]
        em = discord.Embed(
            title=f"Rice Purity Test ({self.idx+1}/{len(QUESTIONS)})",
            description=q,
            color=discord.Color.pink()
        )
        em.set_author(name=f"Requested by {self.inter.user.display_name}", icon_url=self.inter.user.display_avatar.url)
        if self.msg is None:
            self.msg = await self.inter.followup.send(embed=em, view=self, ephemeral=self.anon)
        else:
            await self.msg.edit(embed=em, view=self)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.score -= 1
        self.idx += 1
        await self.show_q()

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.idx += 1
        await self.show_q()

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.secondary)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Rice Purity Test stopped.", ephemeral=True)
        if self.msg:
            await self.msg.edit(view=None)

class RicePurity(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ricepurity", description="Take the Rice Purity Test (reads data file).")
    async def ricepurity_cmd(self, inter: discord.Interaction, anonymous: Optional[bool] = False):
        if not QUESTIONS:
            await inter.response.send_message("Questions file not found.", ephemeral=True)
            return
        await inter.response.send_message("Starting Rice Purity Test...", ephemeral=True)
        v = RicePurityView(inter, anonymous or False)
        await v.show_q()

async def setup(bot: commands.Bot):
    await bot.add_cog(RicePurity(bot))
