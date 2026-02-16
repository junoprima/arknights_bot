import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from discord_bot.commands import add_cookie, delete_cookie, edit_cookie, trigger_checkin, test_command, reload, list_accounts
import logging

# Load environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Register commands
bot.tree.add_command(add_cookie.command)
bot.tree.add_command(delete_cookie.command)
bot.tree.add_command(edit_cookie.command)
bot.tree.add_command(trigger_checkin.command)
bot.tree.add_command(test_command.command)
bot.tree.add_command(reload.command)  # Add reload command
bot.tree.add_command(list_accounts.command)

@bot.event
async def on_ready():
    logging.info(f"Bot is ready! Logged in as {bot.user.name}")
    logging.info("Syncing global commands...")

    try:
        # Sync commands globally
        await bot.tree.sync()
        logging.info("Global commands synced successfully.")
        
        # Log all registered commands
        commands = [cmd.name for cmd in bot.tree.get_commands()]
        logging.info(f"Registered commands: {commands}")
    except Exception as e:
        logging.error(f"Failed to sync commands: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
