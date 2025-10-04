# cogs/rps.py
from typing import Dict, Optional, List
import discord
from discord.ext import commands
from discord import app_commands

RPS_CHOICES = ("rock", "paper", "scissors")
RPS_BEATS = {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}

def rps_result(a: str, b: str) -> int:
    if a == b: return 0
    return 1 if (a, b) in RPS_BEATS else -1

def rps_score_line(scores: Dict[int, int], p1: discord.Member, p2: discord.Member) -> str:
    return f"**Score:** {p1.display_name} {scores.get(p1.id,0)} — {scores.get(p2.id,0)} {p2.display_name}"

def rps_embed(title: str, desc: str, p1: discord.Member, p2: discord.Member, scores: Dict[int, int]) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=discord.Color.blurple())
    e.add_field(name="Players", value=f"{p1.mention} vs {p2.mention}", inline=False)
    e.add_field(name="Score", value=rps_score_line(scores, p1, p2), inline=False)
    return e

def rps_victory_embed(p1: discord.Member, p2: discord.Member, scores: Dict[int,int]) -> discord.Embed:
    s1, s2 = scores.get(p1.id,0), scores.get(p2.id,0)
    if s1 == s2:
        title = "RPS – Match Over (Tie)"
        desc = f"Tied at **{s1}**–**{s2}**!"
    elif s1 > s2:
        title = "RPS – Victory!"
        desc = f"**{p1.display_name}** wins **{s1}**–**{s2}** over **{p2.display_name}**"
    else:
        title = "RPS – Victory!"
        desc = f"**{p2.display_name}** wins **{s2}**–**{s1}** over **{p1.display_name}**"
    return discord.Embed(title=title, description=desc, color=discord.Color.green())

class RPSMatchView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=600.0)
        self.p1 = p1
        self.p2 = p2
        self.choices: Dict[int, Optional[str]] = {p1.id: None, p2.id: None}
        self.scores: Dict[int, int] = {p1.id: 0, p2.id: 0}
        self.round_no = 1
        self.match_msg: Optional[discord.Message] = None

    def _guard_player(self, u: discord.abc.User) -> bool:
        return u.id in self.choices

    async def start(self, interaction: discord.Interaction):
        """Start the RPS match by sending the initial round message."""
        desc = f"{self.p1.mention} vs {self.p2.mention}\n\n{self.p1.display_name}: ❓ Waiting...\n{self.p2.display_name}: ❓ Waiting..."
        emb = discord.Embed(title=f"🎮 ROUND {self.round_no} 🎮", description=desc, color=discord.Color.blurple())
        emb.add_field(name="Score", value=rps_score_line(self.scores, self.p1, self.p2), inline=False)
        msg = await interaction.followup.send(embed=emb, view=self, wait=True)
        self.match_msg = msg

    async def _handle_pick(self, interaction: discord.Interaction, pick: str):
        if not self._guard_player(interaction.user):
            await interaction.response.send_message("You're not in this match.", ephemeral=True)
            return
        if self.choices[interaction.user.id] is not None:
            await interaction.response.send_message("You already picked this round.", ephemeral=True)
            return
        self.choices[interaction.user.id] = pick

        # Update message to show who has picked
        if not all(self.choices.values()):
            # Show that this player picked, waiting for other
            p1_status = "✅ Locked in!" if self.choices[self.p1.id] else "❓ Waiting..."
            p2_status = "✅ Locked in!" if self.choices[self.p2.id] else "❓ Waiting..."
            desc = f"{self.p1.mention} vs {self.p2.mention}\n\n{self.p1.display_name}: {p1_status}\n{self.p2.display_name}: {p2_status}"
            emb = discord.Embed(title=f"🎮 ROUND {self.round_no} 🎮", description=desc, color=discord.Color.blurple())
            emb.add_field(name="Score", value=rps_score_line(self.scores, self.p1, self.p2), inline=False)
            
            if self.match_msg:
                try:
                    await self.match_msg.edit(embed=emb, view=self)
                except Exception:
                    pass
            await interaction.response.send_message(f"You picked **{pick}**!", ephemeral=True)
        else:
            # Both picked - show results
            c1 = self.choices[self.p1.id]
            c2 = self.choices[self.p2.id]
            res = rps_result(c1, c2)  # type: ignore

            if res == 1:
                self.scores[self.p1.id] += 1
                verdict = f"🎉 **{self.p1.display_name}** wins this round!"
            elif res == -1:
                self.scores[self.p2.id] += 1
                verdict = f"🎉 **{self.p2.display_name}** wins this round!"
            else:
                verdict = "🤝 **It's a tie!**"

            # Map choices to emojis
            emoji_map = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
            desc = f"{self.p1.mention} vs {self.p2.mention}\n\n{self.p1.display_name}: {emoji_map.get(c1, c1)} **{c1}**\n{self.p2.display_name}: {emoji_map.get(c2, c2)} **{c2}**\n\n{verdict}\n\n*Pick your next move!*"
            
            emb = discord.Embed(title=f"🎮 ROUND {self.round_no} RESULT 🎮", description=desc, color=discord.Color.gold())
            emb.add_field(name="Score", value=rps_score_line(self.scores, self.p1, self.p2), inline=False)

            # Reset choices for next round
            self.round_no += 1
            self.choices[self.p1.id] = None
            self.choices[self.p2.id] = None

            # Enable end button
            for child in self.children:
                if isinstance(child, discord.ui.Button) and child.custom_id == "rps_end":
                    child.disabled = False

            # Edit the original message with results and ready for next round
            if self.match_msg:
                try:
                    await self.match_msg.edit(embed=emb, view=self)
                except Exception:
                    pass
            await interaction.response.send_message(f"You picked **{pick}**!", ephemeral=True)

    @discord.ui.button(label="Rock", style=discord.ButtonStyle.secondary, row=0, custom_id="rps_rock")
    async def btn_rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_pick(interaction, "rock")

    @discord.ui.button(label="Paper", style=discord.ButtonStyle.secondary, row=0, custom_id="rps_paper")
    async def btn_paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_pick(interaction, "paper")

    @discord.ui.button(label="Scissors", style=discord.ButtonStyle.secondary, row=0, custom_id="rps_scissors")
    async def btn_scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_pick(interaction, "scissors")



    @discord.ui.button(label="End Match", style=discord.ButtonStyle.danger, row=1, disabled=True, custom_id="rps_end")
    async def btn_end(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._guard_player(interaction.user):
            await interaction.response.send_message("Only the current players can end the match.", ephemeral=True)
            return
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        
        # Determine winner
        s1, s2 = self.scores.get(self.p1.id, 0), self.scores.get(self.p2.id, 0)
        if s1 == s2:
            title = "🤝 MATCH OVER - TIE 🤝"
            desc = f"Tied at **{s1}**–**{s2}**!"
            color = discord.Color.orange()
        elif s1 > s2:
            title = "🏆 VICTORY 🏆"
            desc = f"**{self.p1.display_name}** wins **{s1}**–**{s2}** over **{self.p2.display_name}**!"
            color = discord.Color.green()
        else:
            title = "🏆 VICTORY 🏆"
            desc = f"**{self.p2.display_name}** wins **{s2}**–**{s1}** over **{self.p1.display_name}**!"
            color = discord.Color.green()
        
        emb = discord.Embed(title=title, description=desc, color=color)
        emb.add_field(name="Final Score", value=rps_score_line(self.scores, self.p1, self.p2), inline=False)
        
        if self.match_msg:
            try:
                await self.match_msg.edit(embed=emb, view=self)
            except Exception:
                pass
        
        await interaction.response.send_message("Match ended!", ephemeral=True)
        self.stop()

class RPSLobbyView(discord.ui.View):
    def __init__(self, starter: discord.Member, opponent: Optional[discord.Member] = None):
        super().__init__(timeout=180.0)
        self.starter = starter
        self.opponent = opponent
        self.joined: List[discord.Member] = [starter] if opponent is None else []
        self.msg: Optional[discord.Message] = None

        if opponent is None:
            self.add_item(self.JoinBtn(self))
        else:
            self.add_item(self.AcceptBtn(self))
            self.add_item(self.DeclineBtn(self))

    class JoinBtn(discord.ui.Button):
        def __init__(self, lobby: 'RPSLobbyView'):
            super().__init__(label="Join", style=discord.ButtonStyle.primary)
            self.lobby = lobby
        async def callback(self, interaction: discord.Interaction):
            if not isinstance(interaction.user, discord.Member):
                await interaction.response.send_message("Only guild members can join.", ephemeral=True)
                return
            if interaction.user in self.lobby.joined:
                await interaction.response.send_message("You're already in!", ephemeral=True)
                return
            if len(self.lobby.joined) >= 2:
                await interaction.response.send_message("Two players already joined.", ephemeral=True)
                return
            self.lobby.joined.append(interaction.user)
            await interaction.response.send_message(f"You joined! ({len(self.lobby.joined)}/2)", ephemeral=True)
            if len(self.lobby.joined) == 2:
                p1, p2 = self.lobby.joined
                match = RPSMatchView(p1, p2)
                if self.lobby.msg:
                    try:
                        await self.lobby.msg.edit(content=f"**RPS Match:** {p1.mention} vs {p2.mention}", view=None)
                    except Exception:
                        pass
                desc = f"{p1.mention} vs {p2.mention}\n\n{p1.display_name}: ❓ Waiting...\n{p2.display_name}: ❓ Waiting..."
                emb = discord.Embed(title=f"🎮 ROUND {match.round_no} 🎮", description=desc, color=discord.Color.blurple())
                emb.add_field(name="Score", value=rps_score_line(match.scores, p1, p2), inline=False)
                msg = await interaction.followup.send(embed=emb, view=match, wait=True)
                match.match_msg = msg

    class AcceptBtn(discord.ui.Button):
        def __init__(self, lobby: 'RPSLobbyView'):
            super().__init__(label="Accept Challenge", style=discord.ButtonStyle.success)
            self.lobby = lobby
        async def callback(self, interaction: discord.Interaction):
            if not isinstance(interaction.user, discord.Member):
                await interaction.response.send_message("Only guild members can accept.", ephemeral=True)
                return
            if interaction.user.id != self.lobby.opponent.id:
                await interaction.response.send_message("This challenge isn't for you.", ephemeral=True)
                return
            p1 = self.lobby.starter
            p2 = self.lobby.opponent
            match = RPSMatchView(p1, p2)
            await interaction.response.edit_message(content=f"**RPS Match:** {p1.mention} vs {p2.mention}", view=None)
            await match.start(interaction)

    class DeclineBtn(discord.ui.Button):
        def __init__(self, lobby: 'RPSLobbyView'):
            super().__init__(label="Decline", style=discord.ButtonStyle.danger)
            self.lobby = lobby
        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != self.lobby.opponent.id:
                await interaction.response.send_message("Only the challenged user can decline.", ephemeral=True)
                return
            await interaction.response.edit_message(content="Challenge declined.", view=None)
            self.lobby.stop()

    async def send(self, interaction: discord.Interaction):
        if self.opponent is None:
            text = f"**RPS Free-for-all!** First two people to press **Join** will play."
        else:
            text = (
                f"**Rock Paper Scissors Challenge:** {self.starter.mention} vs {self.opponent.mention}\n"
                f"{self.opponent.mention}, press **Accept** to start."
            )
        await interaction.response.send_message(text, view=self)
        self.msg = await interaction.original_response()

class RPS(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rps", description="Rock–Paper–Scissors: free-for-all or challenge a user.")
    @app_commands.describe(opponent="Optionally challenge a specific user")
    async def rps_cmd(self, inter: discord.Interaction, opponent: Optional[discord.Member] = None):
        lobby = RPSLobbyView(inter.user, opponent=opponent)
        await lobby.send(inter)

async def setup(bot: commands.Bot):
    await bot.add_cog(RPS(bot))
