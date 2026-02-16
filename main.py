import os
import sys
import io
import asyncio
import logging
from utils.database import fetch_cookies_from_database
from games.game import GameManager
from utils.logger import setup_logging
from database.connection import init_database, db_manager
from database.operations import db_ops
from dotenv import load_dotenv

# Set up encoding for stdout and stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()

async def check_in_all_games():
    """Fetch configuration from database and execute check-ins."""
    start_time = asyncio.get_event_loop().time()

    logging.info("----------------------------------------")
    logging.info("Starting Daily Check-in Process (Database)")
    logging.info("----------------------------------------")

    try:
        # Initialize database
        await init_database()

        # Get all guilds that have accounts
        guilds_with_accounts = await db_ops.get_all_guilds_with_accounts()
        if not guilds_with_accounts:
            logging.error("No guilds with accounts found in database. Exiting...")
            return

        # Initialize game manager
        game_manager = GameManager()
        total_successes = 0

        # Process each guild separately
        for guild in guilds_with_accounts:
            guild_id = guild.id
            guild_name = guild.name
            logging.info(f"======== Processing Guild: {guild_name} ({guild_id}) ========")

            # Fetch cookies for this guild
            cookies = await fetch_cookies_from_database(guild_id)
            if not cookies:
                logging.warning(f"No account cookies for guild {guild_name}")
                continue

            # Process each game for this guild
            for game_name, accounts in cookies.items():
                if accounts:
                    logging.info(f"--------- Processing {game_name} for {guild_name} ---------")

                    # Get game configuration from database
                    game_config = await db_ops.get_game_config(game_name)
                    if not game_config:
                        logging.error(f"No configuration found for game: {game_name}")
                        continue

                    try:
                        successes = await game_manager.process_game_checkins(
                            guild_id, game_name, game_config, accounts
                        )
                        total_successes += len(successes)
                        logging.info(f"{len(successes)} successful check-ins for {game_config['game']} in {guild_name}")
                    except Exception as e:
                        logging.error(f"Error during check-ins for {game_config['game']} in {guild_name}: {e}")

        end_time = asyncio.get_event_loop().time()
        logging.info("----------------------------------------")
        logging.info(f"Check-in process completed in {end_time - start_time:.2f} seconds.")
        logging.info(f"Total successful check-ins: {total_successes}")
        logging.info("----------------------------------------")

    except Exception as e:
        logging.error(f"Fatal error in check-in process: {e}")
    finally:
        # Clean up database connections
        await db_manager.close()


async def main():
    """Main async entry point"""
    await check_in_all_games()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())