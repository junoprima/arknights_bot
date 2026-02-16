import discord
from discord.ext import commands
from discord import app_commands

class CheckIn(commands.Cog):
    """Cog for triggering the daily check-in."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="trigger_checkin", description="Manually trigger the daily check-in process")
    async def trigger_checkin(self, interaction: discord.Interaction):
        """Manually trigger the daily check-in process."""
        try:
            await interaction.response.send_message("✅ Daily check-in command received! This feature will be available soon.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to trigger check-in: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(CheckIn(bot))
