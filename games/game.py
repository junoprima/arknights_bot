import logging
import json
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import discord

from games.endfield_adapter import EndfieldAdapter

load_dotenv()
constants_path = os.getenv("CONSTANTS_PATH", "/app/constants.json")

def load_constants(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Constants file not found at: {file_path}")
    with open(file_path, "r") as file:
        return json.load(file)

constants = load_constants(constants_path)
print(f"Using constants file at: {constants_path}")

logger = logging.getLogger(__name__)

class Game:
    """
    Game class for Arknights: Endfield using SKPort API
    This is simplified compared to miHoYo_bot since we only support Endfield
    """

    def __init__(self, name, config, cookies):
        self.name = name  # "endfield"
        self.full_name = config["game"]  # "Arknights: Endfield"
        self.config = config
        self.data = cookies  # List of {name, cookie} dicts

    def sign(self, account_token):
        """
        Perform check-in using SKPort API

        Args:
            account_token: JWT token or cred value

        Returns:
            dict: {"success": bool, "message": str, ...}
        """
        try:
            logger.info(f"Processing Endfield account using SKPort API")

            # Create adapter instance
            adapter = EndfieldAdapter(account_token)

            # Perform check-in
            result = adapter.perform_checkin()

            return {
                "success": result["success"],
                "message": result["message"],
                "already_signed": result.get("already_signed", False),
                "reward": result.get("reward"),
                "total_sign_day": result.get("total_sign_day", 0)
            }

        except Exception as e:
            logger.error(f"Endfield check-in error: {e}")
            return {
                "success": False,
                "message": str(e),
                "already_signed": False,
                "reward": None,
                "total_sign_day": 0
            }

    async def process_all_accounts(self) -> List[Dict[str, Any]]:
        """
        Process all accounts for this game

        Returns:
            List of result dicts for each account
        """
        results = []

        for account_data in self.data:
            account_name = account_data['name']
            account_token = account_data['cookie']  # Actually the token for Endfield

            logger.info(f"Processing account: {account_name} for {self.full_name}")

            # Perform check-in
            sign_result = self.sign(account_token)

            # Build result
            result = {
                "account_name": account_name,
                "game": self.full_name,
                "success": sign_result["success"],
                "message": sign_result["message"],
                "already_signed": sign_result.get("already_signed", False),
                "reward": sign_result.get("reward"),
                "total_sign_day": sign_result.get("total_sign_day", 0),
                "uid": None,  # SKPort doesn't easily expose UID in check-in flow
                "nickname": None,
                "rank": None,
                "region": None
            }

            results.append(result)

        return results

    async def send_discord_notification_direct(self, guild_id, success_data):
        """
        Send Discord notification to configured channel

        Args:
            guild_id: Discord guild ID
            success_data: Dict with check-in results
        """
        try:
            # Import here to avoid circular imports
            from database.operations import db_ops
            from discord_bot.bot import get_bot_instance

            # Get channel ID from database
            channel_id_str = await db_ops.get_guild_setting(guild_id, "channel_checkin")
            if not channel_id_str:
                logger.warning(f"No check-in channel configured for guild {guild_id}")
                return

            channel_id = int(channel_id_str)

            # Get bot instance
            bot = get_bot_instance()
            if not bot:
                logger.error("Bot instance not available")
                return

            channel = bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found")
                return

            # Build embed
            embed = self._build_notification_embed(success_data)

            # Send message
            await channel.send(embed=embed)
            logger.info(f"Sent Endfield notification to channel {channel_id}")

        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")

    def _build_notification_embed(self, data: Dict[str, Any]) -> discord.Embed:
        """Build Discord embed for check-in notification"""

        # Get assets from config
        assets = self.config.get("assets", {})
        author_name = assets.get("author", "Endministrator")
        game_name = assets.get("game", "Arknights: Endfield")
        icon_url = assets.get("icon", "")

        # Determine color based on success
        color = discord.Color.green() if data["success"] else discord.Color.red()

        # Create embed
        embed = discord.Embed(
            title=f"📋 Daily Check-in Report",
            description=data["message"],
            color=color
        )

        # Set author
        account_name = data.get("account_name", "Doctor")
        embed.set_author(
            name=f"{author_name} • {account_name}",
            icon_url=icon_url
        )

        # Add fields
        if data["success"] or data.get("already_signed"):
            # Show total sign days
            total_days = data.get("total_sign_day", 0)
            embed.add_field(
                name="📅 Total Sign-ins",
                value=f"{total_days} days",
                inline=True
            )

            # Show reward if available
            reward = data.get("reward")
            if reward:
                reward_text = f"{reward.get('name', 'Unknown')} x{reward.get('count', 0)}"
                embed.add_field(
                    name="🎁 Reward",
                    value=reward_text,
                    inline=True
                )

        # Add footer
        embed.set_footer(text=game_name)

        # Add thumbnail
        if icon_url:
            embed.set_thumbnail(url=icon_url)

        return embed


class GameManager:
    """Manages check-in processing for all games"""

    def __init__(self):
        self.constants = constants

    async def process_game_checkins(self, guild_id, game_name, game_config, accounts):
        """
        Process check-ins for a specific game

        Args:
            guild_id: Discord guild ID
            game_name: Name of the game (e.g., "endfield")
            game_config: Game configuration dict
            accounts: List of account dicts with 'name' and 'cookie'

        Returns:
            List of successful check-in results
        """
        logger.info(f"Processing {len(accounts)} accounts for {game_config['game']}")

        # Create game instance
        game = Game(game_name, game_config, accounts)

        # Process all accounts
        results = await game.process_all_accounts()

        # Send Discord notifications
        success_results = [r for r in results if r["success"] or r.get("already_signed")]

        if success_results:
            # Group by success to send one notification
            for result in success_results:
                await game.send_discord_notification_direct(guild_id, result)

        return success_results
