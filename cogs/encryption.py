# cogs/encryption.py
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
from utils.crypto import encrypt_strong, decrypt_strong

class DecryptModal(discord.ui.Modal, title="Decrypt Message"):
    seed: discord.ui.TextInput = discord.ui.TextInput(
        label="Seed / Key",
        placeholder="Enter the exact seed you used to encrypt",
        style=discord.TextStyle.short,
        required=True,
        max_length=200,
    )
    def __init__(self, ciphertext: str):
        super().__init__()
        self.ciphertext = ciphertext
    async def on_submit(self, interaction: discord.Interaction):
        try:
            plaintext = decrypt_strong(self.ciphertext, self.seed.value)
            await interaction.response.send_message(f":unlock: **Decrypted:** {plaintext}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Decryption failed: {e}", ephemeral=True)

class DecryptView(discord.ui.View):
    def __init__(self, ciphertext: str):
        super().__init__(timeout=600.0)
        self.ciphertext = ciphertext
    @discord.ui.button(label="Decrypt", style=discord.ButtonStyle.primary)
    async def decrypt_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DecryptModal(self.ciphertext))

class Encryption(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="encrypt",
        description="Encrypt text (Base64URL) and post an embed with your avatar/name + Decrypt button."
    )
    @app_commands.describe(
        hidden="If true, the ack is hidden (default: True).",
        anonymous="If true, the embed won't show your name/avatar (default: False)."
    )
    async def encrypt_cmd(self, inter: discord.Interaction, seed: str, message: str, hidden: Optional[bool] = True, anonymous: Optional[bool] = False):
        await inter.response.defer(ephemeral=bool(hidden))
        try:
            ciphertext = encrypt_strong(message, seed)
            emb = discord.Embed(
                description=f":lock: `{ciphertext}`\n\n🔐 Need to read it? Click **Decrypt** and enter the seed.",
                color=discord.Color.blurple()
            )
            
            if not anonymous:
                avatar_url = inter.user.display_avatar.url
                emb.set_author(name=inter.user.display_name, icon_url=avatar_url)
            
            emb.set_footer(text="Decrypt opens a private modal; result is sent ephemerally to you.")
            view = DecryptView(ciphertext)
            
            # Send as a new message to the channel instead of a reply
            await inter.channel.send(embed=emb, view=view)
            # Confirm to user ephemerally
            await inter.followup.send("✅ Encrypted message sent!", ephemeral=True)
        except Exception as e:
            await inter.followup.send(f"Error during encryption: {e}", ephemeral=True)

    @app_commands.command(name="decrypt", description="Decrypt a Base64URL ciphertext from /encrypt (hidden by default).")
    @app_commands.describe(hidden="If true, only you see the result (default: True)")
    async def decrypt_cmd(self, inter: discord.Interaction, seed: str, message: str, hidden: Optional[bool] = True):
        try:
            out = decrypt_strong(message, seed)
            await inter.response.send_message(f":unlock: {out}", ephemeral=bool(hidden))
        except Exception as e:
            await inter.response.send_message(f"Error: {e}", ephemeral=bool(hidden))

async def setup(bot: commands.Bot):
    await bot.add_cog(Encryption(bot))
