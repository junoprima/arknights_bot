"""
Discord Bot Notification System
Sends check-in results to guild-specific channels using the Discord bot
"""
import logging
import discord
import asyncio
import os
from typing import Dict, Any, Optional
from database.operations import db_ops

logger = logging.getLogger(__name__)

class DiscordBotNotifier:
    """Discord bot notification system for check-in results"""

    def __init__(self):
        self.bot = None
        self.bot_token = os.getenv('DISCORD_BOT_TOKEN')

    async def get_bot_instance(self):
        """Get the Discord bot instance"""
        if self.bot is None:
            intents = discord.Intents.default()
            intents.message_content = True
            self.bot = discord.Client(intents=intents)

            if self.bot_token:
                await self.bot.login(self.bot_token)

        return self.bot

    async def send_checkin_notification(self, guild_id: int, success_data: Dict[str, Any]):
        """Send check-in notification to the configured channel for this guild"""
        try:
            # Get the configured channel for this guild
            channel_id = await db_ops.get_guild_setting(guild_id, "channel_checkin")
            if not channel_id:
                logger.warning(f"No check-in channel configured for guild {guild_id}")
                return False

            # Get bot instance
            bot = await self.get_bot_instance()
            if not bot:
                logger.error("Could not get bot instance")
                return False

            # Get the channel
            channel = bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Could not find channel {channel_id} in guild {guild_id}")
                return False

            # Create embed for check-in result
            embed = self.create_checkin_embed(success_data)

            # Send the notification
            await channel.send(embed=embed)
            logger.info(f"Check-in notification sent to channel {channel_id} in guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False

    def create_checkin_embed(self, data: Dict[str, Any]) -> discord.Embed:
        """Create a Discord embed for check-in results"""
        # Handle different data formats
        account_name = data.get('account_name', data.get('name', 'Unknown'))
        game_name = data.get('game_name', 'Unknown Game')
        reward_name = data.get('reward_name', 'Unknown Reward')
        reward_count = data.get('reward_count', 0)
        total_checkins = data.get('total_checkins', data.get('total', 0))
        already_signed = data.get('already_signed', False)

        # Determine embed color and title
        if already_signed:
            color = 0xFFA500  # Orange for already signed
            status = "✅ Already Checked In Today"
        else:
            color = 0x00FF00  # Green for successful check-in
            status = "🎉 Check-in Successful!"

        embed = discord.Embed(
            title=f"🎮 {game_name} Daily Check-in",
            description=status,
            color=color
        )

        # Add account info
        embed.add_field(
            name="👤 Account",
            value=account_name,
            inline=True
        )

        # Add reward info if available
        if reward_name and reward_count:
            embed.add_field(
                name="🎁 Today's Reward",
                value=f"{reward_name} x{reward_count}",
                inline=True
            )

        # Add total check-ins
        embed.add_field(
            name="📅 Total Check-ins",
            value=str(total_checkins),
            inline=True
        )

        # Add timestamp
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text="miHoYo Auto Check-in Bot")

        return embed

# Global instance
discord_notifier = DiscordBotNotifier()

async def send_discord_bot_notification(guild_id: int, success_data: Dict[str, Any]):
    """Send notification using Discord bot to guild-specific channel"""
    return await discord_notifier.send_checkin_notification(guild_id, success_data)