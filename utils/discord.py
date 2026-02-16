"""
Discord Bot Notification System
Sends check-in results to guild-specific channels using Discord bot
No more webhooks - uses /set_channel command configured channels
"""
import logging
import asyncio
import os
from typing import Dict, Any, Optional
from database.operations import db_ops

logger = logging.getLogger(__name__)

async def send_discord_notification(guild_id: int, success_data: Dict[str, Any]):
    """
    Send check-in notification to Discord channel configured for this guild
    Uses the channel set by /set_channel command
    """
    try:
        # Get the configured check-in channel for this guild
        channel_id = await db_ops.get_guild_setting(guild_id, "channel_checkin")
        if not channel_id:
            logger.warning(f"No check-in channel configured for guild {guild_id}. Use /set_channel command to configure.")
            return False

        # Import discord here to avoid circular imports
        import discord

        # Get bot instance from the running bot
        # This will be called from main.py which runs alongside the Discord bot
        bot_instance = get_bot_instance()
        if not bot_instance:
            logger.error("Discord bot not available for notifications")
            return False

        # Get the channel
        channel = bot_instance.get_channel(int(channel_id))
        if not channel:
            logger.error(f"Could not find channel {channel_id} in guild {guild_id}")
            return False

        # Set bot identity to game character (like original webhook)
        guild = channel.guild
        game_character_name = success_data.get('assets', {}).get('author', 'miHoYo CheckIn')
        game_character_avatar = success_data.get('assets', {}).get('icon', '')

        # Try to update bot nickname to game character name
        try:
            if guild.me.display_name != game_character_name:
                await guild.me.edit(nick=game_character_name)
        except discord.Forbidden:
            pass  # Bot doesn't have permission to change nickname
        except Exception:
            pass  # Ignore other errors

        # Try to update bot avatar to game character avatar (rate limited)
        try:
            if game_character_avatar and bot_instance.user.avatar:
                # Check if current avatar URL matches the game character
                current_avatar_url = str(bot_instance.user.avatar.url)
                if game_character_avatar not in current_avatar_url:
                    # Download the new avatar image
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(game_character_avatar) as resp:
                            if resp.status == 200:
                                avatar_data = await resp.read()
                                await bot_instance.user.edit(avatar=avatar_data)
                                logger.info(f"Updated bot avatar to {game_character_name}")
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                logger.warning("Avatar update rate limited - will use current avatar")
            else:
                logger.warning(f"Could not update avatar: {e}")
        except Exception as e:
            logger.warning(f"Avatar update failed: {e}")
            pass  # Ignore avatar update errors

        # Create embed
        embed = create_checkin_embed(success_data)

        # Send notification (bot will appear as game character if nickname was set)
        await channel.send(embed=embed)
        logger.info(f"Check-in notification sent to {channel.name} in {channel.guild.name}")
        return True

    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")
        return False

def create_checkin_embed(success: Dict[str, Any]):
    """Create Discord embed using EXACT original format from before session started"""
    import discord
    from datetime import datetime, timezone

    # Use EXACT same embed structure as original - just convert to discord.Embed
    embed_dict = {
        "color": 16748258,
        "title": f"{success['assets']['game']} Daily Check-In",
        "author": {
            "name": success["name"],
            "icon_url": success["assets"]["icon"]
        },
        "fields": [
            {"name": "Nickname", "value": success["account"]["nickname"], "inline": True},
            {"name": "UID", "value": success["account"]["uid"], "inline": True},
            {"name": "Rank", "value": success["account"]["rank"], "inline": True},
            {"name": "Region", "value": success["account"]["region"], "inline": True},
            {
                "name": "Today's Reward",
                "value": f"{success['award']['name']} x{success['award']['count']}",
                "inline": True,
            },
            {"name": "Total Check-Ins", "value": success["total"], "inline": True},
            {"name": "Result", "value": success["result"], "inline": False},
        ],
        "thumbnail": {"url": success["award"]["icon"]},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": f"{success['assets']['game']} Daily Check-In"},
    }

    # Convert to discord.Embed
    embed = discord.Embed.from_dict(embed_dict)
    return embed

def get_bot_instance():
    """Get the Discord bot instance - to be implemented by the bot runner"""
    # This will be set by the bot when it starts
    return getattr(get_bot_instance, '_bot_instance', None)

def set_bot_instance(bot):
    """Set the Discord bot instance for notifications"""
    get_bot_instance._bot_instance = bot