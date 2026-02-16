import discord
from discord.ext import commands
from discord import app_commands

class Admin(commands.Cog):
    """Cog for admin commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="reload", description="Reload all commands and sync them")
    async def reload(self, interaction: discord.Interaction):
        """Reload all commands."""
        try:
            await self.bot.tree.sync()
            await interaction.response.send_message("Commands reloaded and synced successfully!")
        except Exception as e:
            await interaction.response.send_message(f"Failed to reload commands: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
