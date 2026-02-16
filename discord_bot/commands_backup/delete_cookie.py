from discord import app_commands, Interaction
from utils.firestore import delete_cookie_in_firestore
from utils.autocomplete import game_autocomplete, account_autocomplete
import logging

@app_commands.command(name="delete_cookie", description="Delete an existing cookie from Firestore")
@app_commands.describe(
    game="Select a game",
    account="Select an account"
)
@app_commands.autocomplete(game=game_autocomplete, account=account_autocomplete)
async def command(interaction: Interaction, game: str, account: str):
    """Deletes a cookie from Firestore."""
    logging.info(f"Executing 'delete_cookie' with game={game}, account={account}")
    try:
        success = delete_cookie_in_firestore(game, account)
        if success:
            await interaction.response.send_message(
                f"Cookie for account '{account}' in '{game}' deleted successfully!"
            )
        else:
            await interaction.response.send_message(
                f"Failed to delete cookie for account '{account}' in '{game}'."
            )
    except Exception as e:
        logging.error(f"Error in 'delete_cookie': {e}")
        await interaction.response.send_message(f"Error deleting cookie: {e}")
