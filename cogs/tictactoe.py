# cogs/tictactoe.py
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
from utils.common import make_embed

T3_WIN = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]

class TTT(discord.ui.View):
    def __init__(self, inter: discord.Interaction, p2: discord.Member):
        super().__init__(timeout=300.0)
        self.inter = inter
        self.p1 = inter.user
        self.p2 = p2
        self.turn = self.p1
        self.board = [' '] * 9

        for i in range(9):
            self.add_item(self.Cell(i, self))

    class Cell(discord.ui.Button):
        def __init__(self, idx: int, game: 'TTT'):
            super().__init__(label="⬜", style=discord.ButtonStyle.secondary, row=idx//3)
            self.idx = idx
            self.game = game
        async def callback(self, interaction: discord.Interaction):
            g = self.game
            if interaction.user.id != g.turn.id:
                await interaction.response.send_message("Not your turn.", ephemeral=True); return
            if g.board[self.idx] != ' ':
                await interaction.response.send_message("Cell already taken.", ephemeral=True); return
            mark = 'X' if g.turn.id == g.p1.id else 'O'
            g.board[self.idx] = mark
            self.label = mark
            self.style = discord.ButtonStyle.success if mark == 'X' else discord.ButtonStyle.danger
            self.disabled = True
            g.turn = g.p2 if g.turn.id == g.p1.id else g.p1

            state = g._state_text()
            win = g._winner()
            if win:
                for item in g.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = True
                await interaction.response.edit_message(content=state + f"\n**Winner:** {win.mention}", view=g)
                v = make_embed("Tic-Tac-Toe – Victory!", f"Winner: {win.mention}", discord.Color.green())
                await interaction.followup.send(embed=v)
                g.stop()
            elif ' ' not in g.board:
                for item in g.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = True
                await interaction.response.edit_message(content=state + "\n**Draw!**", view=g)
                v = make_embed("Tic-Tac-Toe – Draw", "No more moves left.", discord.Color.orange())
                await interaction.followup.send(embed=v)
                g.stop()
            else:
                await interaction.response.edit_message(content=state + f"\nTurn: {g.turn.mention}", view=g)

    def _winner(self) -> Optional[discord.Member]:
        for a,b,c in T3_WIN:
            if self.board[a] != ' ' and self.board[a] == self.board[b] == self.board[c]:
                return self.p1 if self.board[a] == 'X' else self.p2
        return None

    def _state_text(self) -> str:
        rows = [' | '.join(self.board[r*3:(r+1)*3]) for r in range(3)]
        return "```\n" + "\n---------\n".join(rows) + "\n```"

    async def start(self):
        e = make_embed("Tic-Tac-Toe", f"{self.p1.mention} (X) vs {self.p2.mention} (O)")
        await self.inter.response.send_message(
            content=self._state_text() + f"\nTurn: {self.turn.mention}",
            embed=e,
            view=self
        )

class TicTacToe(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="tictactoe", description="Challenge someone to Tic-Tac-Toe.")
    async def tictactoe_cmd(self, inter: discord.Interaction, opponent: discord.Member):
        if opponent.bot:
            await inter.response.send_message("Pick a human opponent :)", ephemeral=True); return
        game = TTT(inter, opponent)
        await game.start()

async def setup(bot: commands.Bot):
    await bot.add_cog(TicTacToe(bot))
