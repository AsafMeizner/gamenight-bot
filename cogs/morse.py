# cogs/morse.py
import discord
from discord.ext import commands
from discord import app_commands

MORSE_CODE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..',  'E': '.',   'F': '..-.',
    'G': '--.','H': '....','I': '..',   'J': '.---', 'K': '-.-',  'L': '.-..',
    'M': '--', 'N': '-.',  'O': '---',  'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-',  'U': '..-',  'V': '...-', 'W': '.--',  'X': '-..-',
    'Y': '-.--','Z': '--..',
    '1': '.----','2': '..---','3': '...--','4': '....-','5': '.....',
    '6': '-....','7': '--...','8': '---..','9': '----.','0': '-----',
    ',': '--..--','.' : '.-.-.-','?':'..--..','/':'-..-.','-':'-....-',
    '(': '-.--.', ')':'-.--.-', '!':'-.-.--', ':':'---...',';':'-.-.-.',
    "'":'.----.','@':'.--.-.','&':'.-...','=':'-...-','+':'.-.-.',
    '_':'..--.-','"':'.-..-.','$':'...-..-', ' ':'/'
}
REV_MORSE = {v.strip(): k for k, v in MORSE_CODE.items()}

def morse_encrypt(msg: str) -> str:
    return ' '.join(MORSE_CODE.get(ch, '?') for ch in msg.upper())

def morse_decrypt(code: str) -> str:
    tokens = code.replace('   ', ' / ').split(' ')
    out = []
    for t in tokens:
        if not t: continue
        if t == '/': out.append(' ')
        else: out.append(REV_MORSE.get(t, '�'))
    return ''.join(out)

class Morse(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="morse-encrypt", description="Convert text to Morse.")
    async def morse_enc_cmd(self, inter: discord.Interaction, message: str):
        await inter.response.send_message(morse_encrypt(message), ephemeral=False)

    @app_commands.command(name="morse-decrypt", description="Convert Morse to text.")
    async def morse_dec_cmd(self, inter: discord.Interaction, code: str):
        await inter.response.send_message(morse_decrypt(code), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Morse(bot))
