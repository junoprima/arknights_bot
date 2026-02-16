from discord import app_commands, Interaction
from utils.database_simple import edit_cookie_in_database_simple
from utils.autocomplete_fixed import game_autocomplete, account_autocomplete
import logging

@app_commands.command(name="edit_cookie", description="Edit an existing cookie in database")
@app_commands.describe(
    game="Select a game",
    account="Select an account",
    new_cookie="Enter the updated cookie value"
)
@app_commands.autocomplete(game=game_autocomplete, account=account_autocomplete)
async def command(interaction: Interaction, game: str, account: str, new_cookie: str):
    """Edits an existing cookie in database."""
    logging.info(f"Executing 'edit_cookie' with game={game}, account={account}, new_cookie={new_cookie}")
    try:
        success = edit_cookie_in_database_simple(game, account, new_cookie)
        if success:
            await interaction.response.send_message(
                f"Cookie for account '{account}' in '{game}' updated successfully!"
            )
        else:
            await interaction.response.send_message(
                f"Failed to update cookie for account '{account}' in '{game}'."
            )
    except Exception as e:
        logging.error(f"Error in 'edit_cookie': {e}")
        await interaction.response.send_message(f"Error updating cookie: {e}")