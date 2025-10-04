# cogs/truth_or_dare.py
import random
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
from utils.common import DATA_DIR

TRUTH_FILE = DATA_DIR / "truth_or_dare" / "truth.txt"
DARE_FILE  = DATA_DIR / "truth_or_dare" / "dare.txt"

def _load(path):
    try:
        return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except FileNotFoundError:
        return []

TRUTHS = _load(TRUTH_FILE)
DARES  = _load(DARE_FILE)

class TruthOrDareView(discord.ui.View):
    def __init__(self, inter: discord.Interaction):
        super().__init__(timeout=180.0)
        self.inter = inter
        self.kind: Optional[str] = None
        self.msg: Optional[discord.Message] = None

    def _pick(self) -> str:
        if self.kind == "truth":
            return random.choice(TRUTHS) if TRUTHS else "No truths found."
        return random.choice(DARES) if DARES else "No dares found."

    def _embed(self, text: str) -> discord.Embed:
        c = discord.Color.green() if self.kind == "truth" else discord.Color.red()
        e = discord.Embed(title=f"Random {self.kind.title()}", description=text, color=c)
        e.set_author(name=f"Requested by {self.inter.user.display_name}", icon_url=self.inter.user.display_avatar.url)
        return e

    async def start(self, first_kind: str):
        self.kind = first_kind
        q = self._pick()
        self.msg = await self.inter.response.send_message(embed=self._embed(q), view=self)

    async def _next(self, interaction: discord.Interaction, kind: Optional[str] = None):
        if kind:
            self.kind = kind
        q = self._pick()
        await interaction.response.defer()
        if self.msg:
            await self.msg.edit(view=None)
        self.msg = await interaction.followup.send(embed=self._embed(q), view=self)

    @discord.ui.button(label="Truth", style=discord.ButtonStyle.success)
    async def btn_truth(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._next(interaction, "truth")

    @discord.ui.button(label="Dare", style=discord.ButtonStyle.danger)
    async def btn_dare(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._next(interaction, "dare")

    @discord.ui.button(label="Random", style=discord.ButtonStyle.primary)
    async def btn_random(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._next(interaction, random.choice(["truth", "dare"]))

class TruthDare(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="truth", description="Get a random truth ☺️")
    async def truth_cmd(self, inter: discord.Interaction):
        v = TruthOrDareView(inter)
        await v.start("truth")

    @app_commands.command(name="dare", description="Get a random dare 😈")
    async def dare_cmd(self, inter: discord.Interaction):
        v = TruthOrDareView(inter)
        await v.start("dare")

async def setup(bot: commands.Bot):
    await bot.add_cog(TruthDare(bot))
