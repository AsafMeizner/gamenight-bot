# cogs/radio.py
import json
import random
from pathlib import Path
from typing import Optional, Set

import discord
from discord.ext import commands
from discord import app_commands
from utils.common import DATA_DIR, make_embed

FFMPEG_OPTS_RADIO = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

STATIONS_FILE = DATA_DIR / "radio" / "radio_stations.json"

def load_stations():
    try:
        return json.loads(STATIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

STATIONS = load_stations()  # [{name,url},...]

class RadioView(discord.ui.View):
    def __init__(self, cog: 'Radio', current_station: dict, voice_channel: discord.VoiceChannel, message: discord.Message = None):
        super().__init__(timeout=None)
        self.cog = cog
        self.current_station = current_station
        self.voice_channel = voice_channel
        self.message = message
        self.stop_votes: Set[int] = set()
        self.station_votes: dict[str, Set[int]] = {}
        
        # Add 3 random other stations as buttons
        other_stations = [s for s in STATIONS if s['name'] != current_station['name']]
        random_stations = random.sample(other_stations, min(3, len(other_stations)))
        
        for station in random_stations:
            button = discord.ui.Button(
                label=f"🎵 {station['name'][:40]}",
                style=discord.ButtonStyle.primary,
                custom_id=f"station_{station['name']}"
            )
            button.callback = self.make_station_callback(station)
            self.add_item(button)
        
        # Add stop button
        stop_button = discord.ui.Button(
            label="⏹️ Stop Radio",
            style=discord.ButtonStyle.danger,
            custom_id="stop_radio"
        )
        stop_button.callback = self.stop_callback
        self.add_item(stop_button)
    
    def get_eligible_members(self):
        """Get members who can vote (excluding bots, muted, and deafened)"""
        eligible = []
        for m in self.voice_channel.members:
            if m.bot:
                continue
            # Skip if server muted/deafened or self muted/deafened
            if m.voice.mute or m.voice.deaf or m.voice.self_mute or m.voice.self_deaf:
                continue
            eligible.append(m)
        return eligible
    
    def get_vote_display(self):
        """Generate vote status display"""
        eligible = self.get_eligible_members()
        total_voters = len(eligible)
        
        if total_voters == 0:
            return ""
        
        lines = []
        
        # Show station switch votes
        if self.station_votes:
            lines.append("\n**Switch Votes:**")
            for station_name, voters in self.station_votes.items():
                vote_count = len(voters)
                votes_needed = (total_voters + 1) // 2
                lines.append(f"• {station_name}: {vote_count}/{votes_needed}")
        
        # Show stop votes
        if self.stop_votes:
            stop_count = len(self.stop_votes)
            votes_needed = (total_voters + 1) // 2
            lines.append(f"\n**Stop Votes:** {stop_count}/{votes_needed}")
        
        return "\n".join(lines) if lines else ""
    
    async def update_message_votes(self):
        """Update the message to show current vote counts"""
        if not self.message:
            return
        
        vote_display = self.get_vote_display()
        eligible = self.get_eligible_members()
        
        embed = make_embed(
            "📻 Live Radio",
            f"Now streaming **{self.current_station['name']}** in {self.voice_channel.mention}\n\nVote to switch stations or stop the radio:\n**Eligible Voters:** {len(eligible)}{vote_display}",
            discord.Color.green()
        )
        
        try:
            await self.message.edit(embed=embed, view=self)
        except Exception:
            pass
    
    def make_station_callback(self, station: dict):
        async def callback(interaction: discord.Interaction):
            await self.handle_station_vote(interaction, station)
        return callback
    
    async def handle_station_vote(self, interaction: discord.Interaction, station: dict):
        # Check if user is in the voice channel
        if not isinstance(interaction.user, discord.Member) or not interaction.user.voice:
            await interaction.response.send_message("You need to be in the voice channel to vote!", ephemeral=True)
            return
        
        if interaction.user.voice.channel != self.voice_channel:
            await interaction.response.send_message("You need to be in the same voice channel to vote!", ephemeral=True)
            return
        
        # Check if user is muted or deafened
        if interaction.user.voice.mute or interaction.user.voice.deaf or interaction.user.voice.self_mute or interaction.user.voice.self_deaf:
            await interaction.response.send_message("You cannot vote while muted or deafened!", ephemeral=True)
            return
        
        # Count eligible members
        eligible_members = self.get_eligible_members()
        if len(eligible_members) == 0:
            await interaction.response.send_message("No eligible voters in the voice channel!", ephemeral=True)
            return
        
        # Add vote
        station_key = station['name']
        if station_key not in self.station_votes:
            self.station_votes[station_key] = set()
        self.station_votes[station_key].add(interaction.user.id)
        
        votes_needed = (len(eligible_members) + 1) // 2  # Majority
        current_votes = len(self.station_votes[station_key])
        
        if current_votes >= votes_needed:
            # Switch station
            await self.cog.switch_station(interaction.guild, station)
            
            # Update the message
            embed = make_embed(
                "📻 Live Radio - Station Changed!",
                f"Now streaming **{station['name']}** in {self.voice_channel.mention}\n\nVote to switch stations or stop the radio:\n**Eligible Voters:** {len(eligible_members)}",
                discord.Color.green()
            )
            
            # Create new view with different random stations
            new_view = RadioView(self.cog, station, self.voice_channel, self.message)
            new_view.message = self.message
            
            await interaction.response.edit_message(embed=embed, view=new_view)
        else:
            await interaction.response.send_message(
                f"Vote registered! {current_votes}/{votes_needed} votes to switch to **{station['name']}**",
                ephemeral=True
            )
            await self.update_message_votes()
    
    async def stop_callback(self, interaction: discord.Interaction):
        # Check if user is in the voice channel
        if not isinstance(interaction.user, discord.Member) or not interaction.user.voice:
            await interaction.response.send_message("You need to be in the voice channel to vote!", ephemeral=True)
            return
        
        if interaction.user.voice.channel != self.voice_channel:
            await interaction.response.send_message("You need to be in the same voice channel to vote!", ephemeral=True)
            return
        
        # Check if user is muted or deafened
        if interaction.user.voice.mute or interaction.user.voice.deaf or interaction.user.voice.self_mute or interaction.user.voice.self_deaf:
            await interaction.response.send_message("You cannot vote while muted or deafened!", ephemeral=True)
            return
        
        # Count eligible members
        eligible_members = self.get_eligible_members()
        if len(eligible_members) == 0:
            await interaction.response.send_message("No eligible voters in the voice channel!", ephemeral=True)
            return
        
        # Add vote
        self.stop_votes.add(interaction.user.id)
        
        votes_needed = (len(eligible_members) + 1) // 2  # Majority
        current_votes = len(self.stop_votes)
        
        if current_votes >= votes_needed:
            # Stop the radio
            vc = interaction.guild.voice_client
            if vc:
                if vc.is_playing():
                    vc.stop()
                await vc.disconnect()
            
            embed = make_embed(
                "📻 Radio Stopped",
                f"Radio has been stopped in {self.voice_channel.mention}",
                discord.Color.red()
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message(
                f"Vote registered! {current_votes}/{votes_needed} votes to stop the radio",
                ephemeral=True
            )
            await self.update_message_votes()

class Radio(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def switch_station(self, guild: discord.Guild, station: dict):
        """Switch to a new station without breaking the connection"""
        vc = guild.voice_client
        if not vc or not vc.is_connected():
            return
        
        # Stop current playback
        if vc.is_playing():
            vc.stop()
        
        # Small delay to ensure clean stop
        import asyncio
        await asyncio.sleep(0.5)
        
        # Start new stream
        try:
            src = discord.FFmpegPCMAudio(station["url"], **FFMPEG_OPTS_RADIO)
            vc.play(src)
        except Exception:
            pass

    @app_commands.command(name="radio", description="Play a curated radio station in your current voice channel.")
    @app_commands.describe(station="Pick a station to play")
    async def radio(self, inter: discord.Interaction, station: str):
        if not isinstance(inter.user, discord.Member) or not inter.user.voice or not inter.user.voice.channel:
            await inter.response.send_message("Join a voice channel first.", ephemeral=True)
            return

        station_obj = next((s for s in STATIONS if s["name"].lower() == station.lower()), None)
        if not station_obj:
            await inter.response.send_message("Station not found.", ephemeral=True)
            return

        await inter.response.defer()
        vc = inter.guild.voice_client
        
        # Check if already playing - require vote to switch
        if vc and vc.is_connected() and vc.is_playing():
            view = RadioView(self, station_obj, inter.user.voice.channel)
            eligible = view.get_eligible_members()
            
            em = make_embed(
                "📻 Radio Already Playing",
                f"Currently playing in {vc.channel.mention}\n\nVote to switch to **{station_obj['name']}** or choose another option:\n**Eligible Voters:** {len(eligible)}",
                discord.Color.orange()
            )
            
            msg = await inter.followup.send(embed=em, view=view)
            view.message = msg
            
            # Auto-vote for the requester
            view.station_votes[station_obj['name']] = {inter.user.id}
            await view.update_message_votes()
            return
        
        if vc and vc.channel != inter.user.voice.channel:
            try:
                await vc.move_to(inter.user.voice.channel)
            except Exception:
                try:
                    await vc.disconnect(force=True)
                except Exception:
                    pass
                vc = None

        if not vc or not vc.is_connected():
            vc = await inter.user.voice.channel.connect(self_deaf=True, reconnect=True)

        # stop anything currently playing
        if vc.is_playing():
            vc.stop()
        
        # Small delay to ensure clean stop
        import asyncio
        await asyncio.sleep(0.5)

        src = discord.FFmpegPCMAudio(station_obj["url"], **FFMPEG_OPTS_RADIO)
        vc.play(src)

        view = RadioView(self, station_obj, inter.user.voice.channel)
        eligible = view.get_eligible_members()
        
        em = make_embed(
            "📻 Live Radio",
            f"Now streaming **{station_obj['name']}** in {vc.channel.mention}\n\nVote to switch stations or stop the radio:\n**Eligible Voters:** {len(eligible)}",
            discord.Color.green()
        )
        
        msg = await inter.followup.send(embed=em, view=view)
        view.message = msg

    @radio.autocomplete("station")
    async def radio_autocomplete(self, inter: discord.Interaction, current: str):
        q = (current or "").lower()
        opts = []
        for s in STATIONS:
            if not q or q in s["name"].lower():
                opts.append(app_commands.Choice(name=s["name"], value=s["name"]))
            if len(opts) >= 25:
                break
        return opts

    @app_commands.command(name="radio-url", description="Play a custom radio/stream URL in your current voice channel.")
    async def radio_url(self, inter: discord.Interaction, url: str):
        if not isinstance(inter.user, discord.Member) or not inter.user.voice or not inter.user.voice.channel:
            await inter.response.send_message("Join a voice channel first.", ephemeral=True)
            return

        await inter.response.defer()
        vc = inter.guild.voice_client
        
        # Create a custom station object for the URL
        custom_station = {"name": "Custom Stream", "url": url}
        
        # Check if already playing - require vote to switch
        if vc and vc.is_connected() and vc.is_playing():
            view = RadioView(self, custom_station, inter.user.voice.channel)
            eligible = view.get_eligible_members()
            
            em = make_embed(
                "📻 Radio Already Playing",
                f"Currently playing in {vc.channel.mention}\n\nVote to switch to custom stream:\n`{url}`\n\n**Eligible Voters:** {len(eligible)}",
                discord.Color.orange()
            )
            
            msg = await inter.followup.send(embed=em, view=view)
            view.message = msg
            
            # Auto-vote for the requester
            view.station_votes[custom_station['name']] = {inter.user.id}
            await view.update_message_votes()
            return
        
        if vc and vc.channel != inter.user.voice.channel:
            try:
                await vc.move_to(inter.user.voice.channel)
            except Exception:
                try:
                    await vc.disconnect(force=True)
                except Exception:
                    pass
                vc = None

        if not vc or not vc.is_connected():
            vc = await inter.user.voice.channel.connect(self_deaf=True, reconnect=True)

        if vc.is_playing():
            vc.stop()
        
        # Small delay to ensure clean stop
        import asyncio
        await asyncio.sleep(0.5)

        try:
            src = discord.FFmpegPCMAudio(url, **FFMPEG_OPTS_RADIO)
            vc.play(src)
        except Exception as e:
            await inter.followup.send(f"Failed to play URL: {e}")
            return

        view = RadioView(self, custom_station, inter.user.voice.channel)
        eligible = view.get_eligible_members()
        
        em = make_embed(
            "📻 Live Stream",
            f"Now streaming:\n`{url}`\n\nVote to switch stations or stop the radio:\n**Eligible Voters:** {len(eligible)}",
            discord.Color.green()
        )
        
        msg = await inter.followup.send(embed=em, view=view)
        view.message = msg

async def setup(bot: commands.Bot):
    await bot.add_cog(Radio(bot))
