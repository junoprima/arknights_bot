from discord import app_commands, Interaction, Embed
from utils.firestore import fetch_cookies_from_firestore
from utils.autocomplete import game_autocomplete
import logging

# Game icons dictionary
GAME_ICONS = {
    "genshin": "https://fastcdn.hoyoverse.com/static-resource-v2/2024/04/12/b700cce2ac4c68a520b15cafa86a03f0_2812765778371293568.png",
    "honkai": "https://fastcdn.hoyoverse.com/static-resource-v2/2024/02/29/3d96534fd7a35a725f7884e6137346d1_3942255444511793944.png",
    "starrail": "https://fastcdn.hoyoverse.com/static-resource-v2/2024/04/12/74330de1ee71ada37bbba7b72775c9d3_1883015313866544428.png",
    "zenless": "https://hyl-static-res-prod.hoyolab.com/communityweb/business/nap.png",
}

@app_commands.command(name="list_accounts", description="List all accounts for a selected game")
@app_commands.describe(game="Select the game to view its accounts")
@app_commands.autocomplete(game=game_autocomplete)
async def command(interaction: Interaction, game: str):
    """Lists all accounts for a selected game."""
    logging.info(f"Executing 'list_accounts' for game: {game}")
    try:
        cookies = fetch_cookies_from_firestore()  # Fetch all cookies from Firestore
        if game not in cookies:
            await interaction.response.send_message(
                f"No accounts found for the game '{game}'.", ephemeral=True
            )
            return

        accounts = cookies[game]
        if not accounts:
            await interaction.response.send_message(
                f"No accounts found for the game '{game}'.", ephemeral=True
            )
            return

        # Get the game icon
        game_icon = GAME_ICONS.get(game.lower(), "https://via.placeholder.com/150")  # Default icon if not found

        # Create an embed
        embed = Embed(
            title=f"Accounts for {game.capitalize()}",
            color=0x3498db  # Nice blue color
        )
        embed.set_thumbnail(url=game_icon)  # Set the game icon
        embed.set_footer(text="Powered by miHoyo Check-In Bot")

        # Add accounts to the embed
        for idx, account in enumerate(accounts, start=1):
            embed.add_field(
                name=f"{idx}. {account['name']}",
                value=f"Cookie: {account['cookie'][:20]}...",  # Truncate long cookies
                inline=False
            )

        # Send the embed
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        logging.error(f"Error in 'list_accounts': {e}")
        await interaction.response.send_message(
            f"An error occurred while listing accounts for '{game}': {e}",
            ephemeral=True
        )
