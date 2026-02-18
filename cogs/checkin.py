import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
from utils.database import fetch_cookies_from_database
from games.game import GameManager
from database.operations import db_ops

logger = logging.getLogger(__name__)

class CheckIn(commands.Cog):
    """Cog for triggering the daily check-in."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="trigger_checkin", description="Manually trigger the daily check-in process")
    async def trigger_checkin(self, interaction: discord.Interaction):
        """Manually trigger the daily check-in process."""
        try:
            # Defer the response since check-in might take a while
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild_id
            if not guild_id:
                await interaction.followup.send("❌ This command can only be used in a server.", ephemeral=True)
                return

            logger.info(f"Manual check-in triggered by {interaction.user.name} in guild {guild_id}")

            # Fetch cookies for this guild
            cookies = await fetch_cookies_from_database(guild_id)
            if not cookies:
                await interaction.followup.send("❌ No accounts configured for this server. Use `/add_cookie` to add an account.", ephemeral=True)
                return

            # Initialize game manager
            game_manager = GameManager()
            total_successes = 0

            # Process each game for this guild
            for game_name, accounts in cookies.items():
                if accounts:
                    logger.info(f"Processing {game_name} with {len(accounts)} account(s)")

                    # Get game configuration from database
                    game_config = await db_ops.get_game_config(game_name)
                    if not game_config:
                        logger.error(f"No configuration found for game: {game_name}")
                        continue

                    try:
                        successes = await game_manager.process_game_checkins(
                            guild_id, game_name, game_config, accounts
                        )
                        total_successes += len(successes)
                        logger.info(f"{len(successes)} successful check-ins for {game_config['game']}")
                    except Exception as e:
                        logger.error(f"Error during check-ins for {game_config['game']}: {e}")
                        await interaction.followup.send(f"❌ Error checking in for {game_config['game']}: {str(e)}", ephemeral=True)
                        return

            # Send success message
            if total_successes > 0:
                await interaction.followup.send(f"✅ Check-in completed! {total_successes} account(s) checked in successfully.", ephemeral=True)
            else:
                await interaction.followup.send("ℹ️ All accounts have already checked in today.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in trigger_checkin: {e}")
            try:
                await interaction.followup.send(f"❌ Failed to trigger check-in: {str(e)}", ephemeral=True)
            except:
                await interaction.response.send_message(f"❌ Failed to trigger check-in: {str(e)}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(CheckIn(bot))
