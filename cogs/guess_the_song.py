# cogs/guess_the_song.py
import asyncio
import random
import re
import time
from typing import Dict, List, Optional, Set, Tuple

import discord
from discord.ext import commands
from discord import app_commands
from utils.music import get_guess_song_pack
from utils.common import make_embed

FFMPEG_OPTIONS = {
    "options": "-vn -filter:a \"atrim=0:15,asetpts=N/SR/TB\""  # play first 15 seconds
}
# Note: FFmpeg must be installed; discord.py needs PyNaCl package too.

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

class GuessSongGame:
    def __init__(self, guild: discord.Guild, voice_client: discord.VoiceClient, text_channel: discord.abc.Messageable):
        self.guild = guild
        self.vc = voice_client
        self.ch = text_channel
        self.pack: List[Dict] = []
        self.index = -1
        self.scores: Dict[int, int] = {}
        self.active = False
        self.answer_open = False
        self.current: Optional[Dict] = None
        self.found_artist: Set[int] = set()
        self.found_track: Set[int] = set()
        self.found_album: Set[int] = set()
        self.start_time = 0.0

    def everyone_found_all(self) -> bool:
        # move to next when all 3 distinct properties claimed (by anyone)
        return bool(self.found_artist and self.found_track and self.found_album)

    def award(self, user_id: int, kind: str):
        if kind == "artist":
            if user_id in self.found_artist: return False
            self.found_artist.add(user_id)
        elif kind == "track":
            if user_id in self.found_track: return False
            self.found_track.add(user_id)
        elif kind == "album":
            if user_id in self.found_album: return False
            self.found_album.add(user_id)
        else:
            return False
        self.scores[user_id] = self.scores.get(user_id, 0) + 1
        return True

    def scoreboard(self, limit: int = 10) -> str:
        if not self.scores: return "—"
        top = sorted(self.scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return "\n".join([f"<@{uid}> — **{pts}**" for uid, pts in top])

    async def countdown(self, seconds: int = 3):
        for n in range(seconds, 0, -1):
            await self.ch.send(embed=make_embed("Guess the Song", f"Starting in **{n}**…", discord.Color.blurple()))
            await asyncio.sleep(1)

    async def reveal(self):
        if not self.current: return
        art = self.current.get("art")
        e = discord.Embed(
            title="Reveal",
            description=(
                f"**Song:** {self.current['track']}\n"
                f"**Artist:** {self.current['artist']}\n"
                f"**Album:** {self.current['album']}"
            ),
            color=discord.Color.green()
        )
        if art:
            e.set_thumbnail(url=art)
        e.add_field(name="Scores", value=self.scoreboard(), inline=False)
        await self.ch.send(embed=e)

    async def next_song(self) -> bool:
        self.index += 1
        self.found_artist.clear()
        self.found_track.clear()
        self.found_album.clear()
        if self.index >= len(self.pack):
            return False
        self.current = self.pack[self.index]
        self.answer_open = True
        self.start_time = time.perf_counter()

        # play in VC
        source = discord.FFmpegPCMAudio(self.current["preview"], **FFMPEG_OPTIONS)
        self.vc.play(source)

        # safety timeout: 20s max per round (clip is trimmed to 15s, plus buffer)
        asyncio.create_task(self.round_timeout(20))
        # info embed
        await self.ch.send(embed=make_embed(f"🎧 Track {self.index+1}/{len(self.pack)}", "Guess **Artist**, **Song name**, and **Album**!", discord.Color.blurple()))
        return True

    async def round_timeout(self, seconds: int):
        await asyncio.sleep(seconds)
        if self.answer_open:
            self.answer_open = False
            await self.reveal()
            if self.vc and self.vc.is_playing():
                self.vc.stop()
            await asyncio.sleep(1)
            await self.next_song_or_end()

    async def next_song_or_end(self):
        if self.index + 1 >= len(self.pack):
            await self.ch.send(embed=discord.Embed(
                title="Guess the Song – Finished",
                description="Thanks for playing!",
                color=discord.Color.dark_gold()
            ).add_field(name="Final Scores", value=self.scoreboard(), inline=False))
            self.active = False
            if self.vc and self.vc.is_connected():
                await self.vc.disconnect(force=True)
            return
        await asyncio.sleep(1)
        await self.next_song()

    async def on_message(self, message: discord.Message):
        if not self.answer_open or not self.current: return
        if message.author.bot: return
        text = message.content.strip()
        if not text: return

        target_track = norm(self.current["track"])
        target_artist = norm(self.current["artist"])
        target_album = norm(self.current["album"])
        guess = norm(text)

        awarded = False
        # loose containment matching
        if target_artist and (target_artist in guess or guess in target_artist):
            awarded = self.award(message.author.id, "artist") or awarded
        if target_track and (target_track in guess or guess in target_track):
            awarded = self.award(message.author.id, "track") or awarded
        if target_album and (target_album in guess or guess in target_album):
            awarded = self.award(message.author.id, "album") or awarded

        if awarded:
            await message.add_reaction("✅")

        if self.everyone_found_all():
            self.answer_open = False
            # stop current audio and reveal
            if self.vc and self.vc.is_playing():
                self.vc.stop()
            await self.reveal()
            await self.next_song_or_end()

# keep one game per text channel
ACTIVE_GAMES: Dict[int, GuessSongGame] = {}

class GuessSong(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_unload(self):
        for game in list(ACTIVE_GAMES.values()):
            try:
                if game.vc and game.vc.is_connected():
                    await game.vc.disconnect(force=True)
            except Exception:
                pass
        ACTIVE_GAMES.clear()

    @app_commands.command(name="guess-song", description="Start a Guess the Song game (joins your VC, 15s clips, artist/song/album).")
    @app_commands.describe(count="How many songs (5–20)")
    async def guess_song(self, inter: discord.Interaction, count: Optional[app_commands.Range[int,5,20]] = 10):
        count = count or 10
        # must be in a voice channel
        if not isinstance(inter.user, discord.Member) or not inter.user.voice or not inter.user.voice.channel:
            await inter.response.send_message("Join a voice channel first.", ephemeral=True)
            return

        text_chan_id = inter.channel.id  # game bound to the current text channel
        if text_chan_id in ACTIVE_GAMES and ACTIVE_GAMES[text_chan_id].active:
            await inter.response.send_message("A game is already running in this channel.", ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)
        # connect to user's VC
        vc = await inter.user.voice.channel.connect(self_deaf=True, reconnect=True)
        await inter.followup.send(f"Joined **{inter.user.voice.channel.name}**. Fetching {count} songs…", ephemeral=True)

        # build game
        game = GuessSongGame(inter.guild, vc, inter.channel)
        game.pack = await get_guess_song_pack(count)
        if not game.pack:
            await inter.followup.send("Couldn't fetch songs right now. Try again later.", ephemeral=True)
            try:
                await vc.disconnect(force=True)
            except Exception:
                pass
            return

        ACTIVE_GAMES[text_chan_id] = game
        game.active = True

        # lobby info & countdown
        await inter.channel.send(embed=make_embed("Guess the Song", f"{inter.user.mention} started a game!\nGet ready…", discord.Color.blurple()))
        await game.countdown(3)
        await game.next_song()

    @app_commands.command(name="stop-audio", description="Stop any ongoing audio (song/radio) and leave VC.")
    async def stop_audio(self, inter: discord.Interaction):
        await inter.response.defer(ephemeral=True)
        # stop guess_song if present
        game = ACTIVE_GAMES.get(inter.channel.id)
        if game and game.vc and game.vc.is_connected():
            try:
                game.active = False
                if game.vc.is_playing():
                    game.vc.stop()
                await game.vc.disconnect(force=True)
            except Exception:
                pass
            ACTIVE_GAMES.pop(inter.channel.id, None)

        # also try generic voice client on this guild
        vc = inter.guild.voice_client
        if vc and vc.is_connected():
            try:
                if vc.is_playing():
                    vc.stop()
                await vc.disconnect(force=True)
            except Exception:
                pass

        await inter.followup.send("Stopped audio and left the voice channel (if connected).", ephemeral=True)

    # listen to messages for guesses
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None: return
        game = ACTIVE_GAMES.get(message.channel.id)
        if game and game.active:
            await game.on_message(message)

async def setup(bot: commands.Bot):
    await bot.add_cog(GuessSong(bot))
