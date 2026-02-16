from discord import app_commands, Interaction
from utils.firestore import update_cookie_in_firestore
from utils.autocomplete import game_autocomplete
import logging

@app_commands.command(name="add_cookie", description="Add a new cookie to Firestore")
@app_commands.describe(
    game="Select a game", 
    account="Enter the account name", 
    cookie="Enter the cookie value"
)
@app_commands.autocomplete(game=game_autocomplete)  # Attach autocomplete
async def command(interaction: Interaction, game: str, account: str, cookie: str):
    logging.info(f"Executing 'add_cookie' with game={game}, account={account}, cookie={cookie}")
    try:
        success = update_cookie_in_firestore(game, [{"name": account, "cookie": cookie}], append=True)
        if success:
            logging.info(f"Cookie added successfully for account '{account}' in game '{game}'.")
            await interaction.response.send_message(
                f"Cookie for account '{account}' in '{game}' added successfully!"
            )
        else:
            logging.warning(f"Failed to add cookie for account '{account}' in '{game}'.")
            await interaction.response.send_message(
                f"Failed to add cookie for account '{account}' in '{game}'."
            )
    except Exception as e:
        logging.error(f"Error in 'add_cookie': {e}")
        await interaction.response.send_message(f"Error adding cookie: {e}")

