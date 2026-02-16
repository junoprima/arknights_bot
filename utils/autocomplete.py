from discord import app_commands
from discord import Interaction
from utils.database_simple import fetch_cookies_from_database
import logging

async def game_autocomplete(interaction: Interaction, current: str):
    logging.info(f"Autocomplete triggered with input: '{current}'")
    games = fetch_cookies_from_database().keys()  # Fetch all available games from database
    logging.info(f"Autocomplete fetched games: {games}")
    return [
        app_commands.Choice(name=game, value=game)
        for game in games
        if current.lower() in game.lower()
    ]

async def account_autocomplete(interaction: Interaction, current: str):
    """Fetch accounts for the selected game and provide autocomplete suggestions."""
    selected_game = interaction.namespace.game  # Get the selected game from the interaction context
    logging.info(f"Autocomplete for accounts triggered with game: {selected_game}, input: '{current}'")

    if not selected_game:
        logging.warning("No game selected for account autocomplete.")
        return []

    cookies = fetch_cookies_from_database()
    accounts = [
        account["name"]
        for account in cookies.get(selected_game, [])
        if current.lower() in account["name"].lower()
    ]

    logging.info(f"Autocomplete fetched accounts: {accounts}")
    return [
        app_commands.Choice(name=account, value=account)
        for account in accounts
    ]