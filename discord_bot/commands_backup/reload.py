from discord import app_commands, Interaction
import logging

@app_commands.command(name="reload", description="Reload all commands and sync them")
async def command(interaction: Interaction):
    """Reloads all commands."""
    try:
        await interaction.response.defer()  # Acknowledge the command
        bot = interaction.client
        await bot.tree.sync()
        logging.info("Commands reloaded successfully.")
        await interaction.followup.send("Commands reloaded and synced successfully!")
    except Exception as e:
        logging.error(f"Error during reload: {e}")
        await interaction.followup.send(f"Failed to reload commands: {e}")
