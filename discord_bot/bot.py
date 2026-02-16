import discord
from discord.ext import commands
import os
import logging
from dotenv import load_dotenv
from database.connection import init_database, db_manager
from database.operations import db_ops
from utils.discord import set_bot_instance

# Load environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Initialize bot with enhanced intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
logger = logging.getLogger(__name__)

@bot.event
async def on_ready():
    """Bot ready event - initialize database and register existing guilds"""
    logger.info(f"Bot is ready! Logged in as {bot.user.name}")
    
    # Set bot instance for Discord notifications
    set_bot_instance(bot)
    logger.info("Bot instance set for Discord notifications")

    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")

        # Register all existing guilds the bot is in
        logger.info("Registering existing guilds...")
        for guild in bot.guilds:
            try:
                await db_ops.register_guild(
                    guild_id=guild.id,
                    guild_name=guild.name,
                    webhook_url=None
                )
                logger.info(f"Registered existing guild: {guild.name} ({guild.id})")
            except Exception as e:
                logger.error(f"Error registering guild {guild.name}: {e}")

        # Load Cogs
        logger.info("Loading Cogs...")
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await bot.load_extension(cog_name)
                    logger.info(f"Loaded cog: {cog_name}")
                except Exception as e:
                    logger.error(f"Failed to load cog {cog_name}: {e}")

        logger.info("Bot startup completed successfully!")

    except Exception as e:
        logger.error(f"Error during bot startup: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
