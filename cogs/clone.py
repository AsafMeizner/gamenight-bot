# cogs/clone.py
import re
import discord
from discord.ext import commands
from discord import app_commands

class Clone(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clone", description="Clone a user's display name and send a message via webhook (requires Manage Webhooks).")
    async def clone_cmd(self, inter: discord.Interaction, target_user: discord.Member, message: str):
        try:
            webhook = await inter.channel.create_webhook(name=target_user.display_name)
            avatar_url = target_user.display_avatar.url
            await webhook.send(content=message, username=target_user.display_name, avatar_url=avatar_url)
            await webhook.delete()
            await inter.response.send_message("Message sent via webhook.", ephemeral=True)
        except discord.Forbidden:
            await inter.response.send_message("Missing permission to manage webhooks here.", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Error: {e}", ephemeral=True)

    @app_commands.command(name="clone-embed", description="Clone a user's display name and send an embed via webhook (requires Manage Webhooks).")
    async def clone_embed_cmd(self, inter: discord.Interaction, target_user: discord.Member, title: str, description: str = "", color: str = None):
        webhook = None
        try:
            webhook = await inter.channel.create_webhook(name=target_user.display_name)
            avatar_url = target_user.display_avatar.url
            color_val = int(color, 16) if color and re.match(r'^[0-9a-fA-F]{6}$', color) else 0x3498db
            embed = discord.Embed(title=title, description=description, color=color_val)
            embed.set_author(name=target_user.display_name, icon_url=avatar_url)
            await webhook.send(embed=embed, username=target_user.display_name, avatar_url=avatar_url)
            await inter.response.send_message("Embed sent via webhook.", ephemeral=True)
        except discord.Forbidden:
            await inter.response.send_message("Missing permission to manage webhooks here.", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Error: {e}", ephemeral=True)
        finally:
            if webhook:
                try: await webhook.delete()
                except Exception: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Clone(bot))
