# bot.py
import os
import asyncio
from pathlib import Path
import random

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("DISCORD_TOKEN missing in .env")

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.message_content = False  # not needed; we use slash commands

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = [
    "cogs.meta",
    "cogs.encryption",
    "cogs.morse",
    "cogs.clone",
    "cogs.moderation",
    "cogs.truth_or_dare",
    "cogs.rice_purity",
    "cogs.trivia",
    "cogs.rps",
    "cogs.tictactoe",
    "cogs.guess_the_song",  
    "cogs.radio",          
]

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception:
        pass
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    if not rotate_presence.is_running():
        rotate_presence.start()

# -------- Rich rotating presence --------
PRESENCES = [
    lambda: discord.Activity(type=discord.ActivityType.listening, name="/trivia"),
    lambda: discord.Activity(type=discord.ActivityType.playing, name="Rock–Paper–Scissors"),
    lambda: discord.Activity(type=discord.ActivityType.listening, name="global radio /radio"),
    lambda: discord.Activity(type=discord.ActivityType.playing, name="Tic-Tac-Toe"),
    lambda: discord.Activity(type=discord.ActivityType.listening, name="your secrets /encrypt"),
    lambda: discord.Activity(type=discord.ActivityType.competing, name="Guess the Song"),
]

@tasks.loop(minutes=2)
async def rotate_presence():
    try:
        activity = random.choice(PRESENCES)()
        await bot.change_presence(
            activity=activity,
            status=random.choice([discord.Status.online, discord.Status.idle])
        )
    except Exception:
        pass

async def load_cogs():
    for ext in COGS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded {ext}")
        except Exception as e:
            print(f"Error loading {ext}: {e}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
