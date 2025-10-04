# cogs/trivia.py
import math
import time
import random
from typing import Dict, List, Optional, Set, Tuple
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from utils.common import DATA_DIR, load_trivia_local, make_embed
from utils import trivia_api as TA

TRIVIA_FALLBACK = load_trivia_local(DATA_DIR / "trivia" / "trivia_questions.json")

def q_embed(qobj: Dict, qnum: int, total: int, seconds: int, scores: Dict[int,int], category_name: Optional[str]) -> discord.Embed:
    cat = f" · {category_name}" if category_name else ""
    e = discord.Embed(
        title=f"Trivia – Q{qnum}/{total} · {seconds}s{cat}",
        description=qobj["question"],
        color=discord.Color.gold()
    )
    labels = ["A", "B", "C", "D"]
    for idx, ch in enumerate(qobj["choices"]):
        e.add_field(name=f"{labels[idx]}", value=ch, inline=False)
    if scores:
        top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:5]
        board = "\n".join([f"<@{uid}> — **{pts}**" for uid, pts in top]) or "—"
        e.add_field(name="Top Scores", value=board, inline=False)
    e.set_footer(text="Pick fast! More time left = more points (correct only).")
    return e

def result_embed(qobj: Dict, qnum: int, total: int, counts: List[int], correct_idx: int,
                 scores: Dict[int,int], winners: List[int], category_name: Optional[str]) -> discord.Embed:
    total_answers = sum(counts) or 1
    labels = ["A","B","C","D"]
    rows = []
    for i, cnt in enumerate(counts):
        pct = int(round(100 * cnt / total_answers))
        rows.append(f"**{labels[i]}** – {pct}% ({cnt})" + (" ✅" if i == correct_idx else ""))
    desc = qobj["question"] + "\n\n" + "\n".join(rows)
    cat = f" · {category_name}" if category_name else ""
    e = discord.Embed(title=f"Trivia – Reveal Q{qnum}/{total}{cat}", description=desc, color=discord.Color.green())
    if winners:
        e.add_field(name="Fastest correct", value=", ".join([f"<@{uid}>" for uid in winners[:5]]), inline=False)
    if scores:
        top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:10]
        e.add_field(name="Scoreboard", value="\n".join([f"<@{uid}> — **{pts}**" for uid, pts in top]) or "—", inline=False)
    return e

class TriviaView(discord.ui.View):
    def __init__(self, inter: discord.Interaction, total_q: int, seconds: int, category_id: Optional[int], category_name: Optional[str]):
        super().__init__(timeout=1200.0)
        self.inter = inter
        self.total_target = max(1, min(50, total_q))
        self.seconds = max(5, min(60, seconds))
        self.round_size = self.total_target
        self.current_index = 0
        self.qobj: Optional[Dict] = None
        self.msg: Optional[discord.Message] = None

        self.scores: Dict[int,int] = {}
        self.participants: Set[int] = set()
        self.end_votes: Set[int] = set()
        self.answers: Dict[int, Tuple[int, float]] = {}
        self.started_at: float = 0.0
        self.timer_task: Optional[asyncio.Task] = None

        self.token: Optional[str] = None
        self.bank: List[Dict] = []
        self.category_id = category_id
        self.category_name = category_name

    # buttons
    @discord.ui.button(label="A", style=discord.ButtonStyle.primary, row=0)
    async def a_btn(self, i: discord.Interaction, b: discord.ui.Button): await self._choose(i, 0)
    @discord.ui.button(label="B", style=discord.ButtonStyle.primary, row=0)
    async def b_btn(self, i: discord.Interaction, b: discord.ui.Button): await self._choose(i, 1)
    @discord.ui.button(label="C", style=discord.ButtonStyle.primary, row=1)
    async def c_btn(self, i: discord.Interaction, b: discord.ui.Button): await self._choose(i, 2)
    @discord.ui.button(label="D", style=discord.ButtonStyle.primary, row=1)
    async def d_btn(self, i: discord.Interaction, b: discord.ui.Button): await self._choose(i, 3)

    @discord.ui.button(label="End (vote)", style=discord.ButtonStyle.danger, row=2)
    async def end_vote(self, i: discord.Interaction, b: discord.ui.Button):
        uid = i.user.id
        self.participants.add(uid)
        if uid in self.end_votes:
            await i.response.send_message("You already voted to end.", ephemeral=True)
            return
        self.end_votes.add(uid)
        threshold = max(1, math.ceil(len(self.participants) / 2))
        if len(self.end_votes) >= threshold:
            await i.response.defer()
            await self._finish("Ended early by majority vote.")
        else:
            remain = threshold - len(self.end_votes)
            await i.response.send_message(f"End vote registered. **{remain}** more needed.", ephemeral=True)

    @discord.ui.button(label="Continue (+batch)", style=discord.ButtonStyle.success, row=2, disabled=True)
    async def continue_btn(self, i: discord.Interaction, b: discord.ui.Button):
        added = await self._fetch_more(self.round_size)
        self.total_target += added
        self.end_votes.clear()
        self.continue_btn.disabled = True  # type: ignore
        await i.response.send_message(f"Continuing! Added **{added}** more questions. New total: **{self.total_target}**", ephemeral=True)
        await self._next_question(i)

    # lifecycle
    async def start(self):
        await self.inter.response.send_message(embed=make_embed("Trivia", "Fetching questions…"), ephemeral=False)
        self.msg = await self.inter.original_response()

        async with aiohttp.ClientSession() as session:
            self.token = await TA.get_token(session)
            self.bank, rc = await TA.fetch_questions(session, self.total_target, self.token, self.category_id)
            if rc == 4 and self.token:
                await TA.reset_token(session, self.token)
                self.bank, rc = await TA.fetch_questions(session, self.total_target, self.token, self.category_id)

        if not self.bank:
            if TRIVIA_FALLBACK:
                self.bank = random.sample(TRIVIA_FALLBACK, min(len(TRIVIA_FALLBACK), self.total_target))
                self.category_name = self.category_name or "Local"
            else:
                await self.msg.edit(embed=make_embed("Trivia", "Couldn't fetch questions and no local fallback."), view=None)
                self.stop()
                return

        await self._next_question(self.inter)

    async def _fetch_more(self, amount: int) -> int:
        amount = max(1, min(TA.OTDB_AMOUNT_MAX, amount))
        fetched = []
        async with aiohttp.ClientSession() as session:
            if not self.token:
                self.token = await TA.get_token(session)
            fetched, rc = await TA.fetch_questions(session, amount, self.token, self.category_id)
            if rc == 4 and self.token:
                await TA.reset_token(session, self.token)
                fetched, rc = await TA.fetch_questions(session, amount, self.token, self.category_id)
        self.bank.extend(fetched)
        return len(fetched)

    async def _next_question(self, interaction: discord.Interaction):
        if self.current_index >= self.total_target:
            self.continue_btn.disabled = False  # type: ignore
            done_embed = discord.Embed(
                title="Trivia – Set complete!",
                description="Click **Continue (+batch)** to add more questions or **End (vote)**.",
                color=discord.Color.blurple()
            )
            if self.scores:
                top = sorted(self.scores.items(), key=lambda kv: kv[1], reverse=True)
                board = "\n".join([f"<@{uid}> — **{pts}**" for uid, pts in top]) or "—"
                done_embed.add_field(name="Scores so far", value=board, inline=False)

            if interaction.response.is_done():
                await interaction.followup.send(embed=done_embed, view=self)
            else:
                await interaction.response.edit_message(embed=done_embed, view=self)
            return

        if self.current_index >= len(self.bank):
            added = await self._fetch_more(max(1, self.round_size))
            if added == 0 and self.current_index >= len(self.bank):
                await self._finish("No more questions available.")
                return

        self.current_index += 1
        self.qobj = self.bank[self.current_index - 1]
        self.answers.clear()
        self.started_at = time.perf_counter()
        self.end_votes.clear()

        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label in ("A","B","C","D"):
                child.disabled = False
        self.continue_btn.disabled = True  # type: ignore

        emb = q_embed(self.qobj, self.current_index, self.total_target, self.seconds, self.scores, self.category_name)
        if interaction.response.is_done():
            if self.msg:
                await self.msg.edit(embed=emb, view=self)
            else:
                self.msg = await interaction.followup.send(embed=emb, view=self)
        else:
            if self.msg:
                await interaction.response.edit_message(embed=emb, view=self)
            else:
                await interaction.response.send_message(embed=emb, view=self)

        if hasattr(self, "timer_task") and self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
        import asyncio
        self.timer_task = asyncio.create_task(self._round_timer())

    async def _choose(self, i: discord.Interaction, choice_idx: int):
        if not self.qobj:
            await i.response.send_message("No question active.", ephemeral=True)
            return
        uid = i.user.id
        self.participants.add(uid)
        if uid in self.answers:
            await i.response.send_message("You've already answered this question.", ephemeral=True)
            return
        t = time.perf_counter()
        self.answers[uid] = (choice_idx, t)
        await i.response.send_message(f"Answer received: **{['A','B','C','D'][choice_idx]}**", ephemeral=True)

    async def _round_timer(self):
        import asyncio
        await asyncio.sleep(self.seconds)
        await self._reveal_and_score()
        await asyncio.sleep(2.0)
        await self._next_question(self.inter)

    async def _reveal_and_score(self):
        if not self.qobj or not self.msg:
            return
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label in ("A","B","C","D"):
                child.disabled = True

        correct = self.qobj["answer"]
        counts = [0,0,0,0]
        winners: List[int] = []

        for uid, (choice, t_ans) in self.answers.items():
            counts[choice] += 1
            if choice == correct:
                time_taken = max(0.0, t_ans - self.started_at)
                remaining = max(0.0, self.seconds - time_taken)
                pts = int(500 + 500 * (remaining / self.seconds))
                self.scores[uid] = self.scores.get(uid, 0) + pts
                winners.append(uid)

        emb = result_embed(self.qobj, self.current_index, self.total_target, counts, correct, self.scores, winners, self.category_name)
        await self.msg.edit(embed=emb, view=self)

    async def _finish(self, reason: str):
        if hasattr(self, "timer_task") and self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        emb = discord.Embed(title="Trivia – Finished", description=reason, color=discord.Color.dark_gold())
        if self.scores:
            top = sorted(self.scores.items(), key=lambda kv: kv[1], reverse=True)
            lines = []
            medal = ["🥇","🥈","🥉"]
            for idx, (uid, pts) in enumerate(top, start=1):
                prefix = medal[idx-1] if idx <= 3 else f"{idx}."
                lines.append(f"{prefix} <@{uid}> — **{pts}**")
            emb.add_field(name="Final Scores", value="\n".join(lines) if lines else "—", inline=False)
        else:
            emb.add_field(name="Final Scores", value="No points awarded.", inline=False)

        if self.msg:
            await self.msg.edit(embed=emb, view=self)
        self.stop()

class Trivia(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await TA.load_categories()

    @app_commands.command(name="trivia", description="Play Kahoot-style trivia (timer, speed points, API-backed).")
    @app_commands.describe(
        questions="How many questions in this set (1-50)",
        timer="Seconds per question (5-60)",
        category="Category name or ID (autocomplete). Leave empty for Any."
    )
    async def trivia_cmd(self, inter: discord.Interaction,
                         questions: Optional[app_commands.Range[int,1,50]] = 10,
                         timer: Optional[app_commands.Range[int,5,60]] = 15,
                         category: Optional[str] = None):
        cat_id, cat_name = TA.resolve_category_id(category)
        v = TriviaView(inter, total_q=questions or 10, seconds=timer or 15, category_id=cat_id, category_name=cat_name)
        await v.start()

    @trivia_cmd.autocomplete("category")
    async def trivia_category_autocomplete(self, inter: discord.Interaction, current: str):
        q = (current or "").lower().strip()
        options = [app_commands.Choice(name="Any Category", value="Any Category")]
        for c in TA.OTDB_CATEGORIES:
            name = c["name"]
            if not q or q in name.lower():
                options.append(app_commands.Choice(name=name, value=name))
            if len(options) >= 25:
                break
        return options

async def setup(bot: commands.Bot):
    await bot.add_cog(Trivia(bot))
