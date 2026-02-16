import discord
from discord.ext import commands
from discord import app_commands
from utils.database import (
    update_cookie_in_database,
    delete_cookie_in_database,
    edit_cookie_in_database,
    fetch_all_games,
    get_account_names_for_game
)
from database.operations import db_ops
import logging
import traceback

logger = logging.getLogger(__name__)


class Cookies(commands.Cog):
    """Enhanced Cog for cookie-related commands with database support"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("COOKIES COG: Initializing Cookies cog")

    async def game_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for game names"""
        logger.info(f"GAME AUTOCOMPLETE: Called with current='{current}'")
        try:
            games = await fetch_all_games()
            logger.info(f"GAME AUTOCOMPLETE: Fetched {len(games)} games")
            return [
                app_commands.Choice(name=game, value=game)
                for game in games
                if current.lower() in game.lower()
            ][:25]  # Discord limit
        except Exception as e:
            logger.error(f"GAME AUTOCOMPLETE ERROR: {e}")
            logger.error(f"GAME AUTOCOMPLETE TRACEBACK: {traceback.format_exc()}")
            return []

    async def account_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for account names"""
        logger.info(f"ACCOUNT AUTOCOMPLETE: Called with current='{current}'")
        try:
            if not interaction.guild:
                logger.warning("ACCOUNT AUTOCOMPLETE: No guild found")
                return []

            # Get the selected game from the interaction
            game = interaction.namespace.game if hasattr(interaction.namespace, 'game') else None
            logger.info(f"ACCOUNT AUTOCOMPLETE: Selected game='{game}'")
            if not game:
                logger.warning("ACCOUNT AUTOCOMPLETE: No game selected")
                return []

            accounts = await get_account_names_for_game(interaction.guild.id, game)
            logger.info(f"ACCOUNT AUTOCOMPLETE: Fetched {len(accounts)} accounts for game '{game}'")
            return [
                app_commands.Choice(name=account, value=account)
                for account in accounts
                if current.lower() in account.lower()
            ][:25]
        except Exception as e:
            logger.error(f"ACCOUNT AUTOCOMPLETE ERROR: {e}")
            logger.error(f"ACCOUNT AUTOCOMPLETE TRACEBACK: {traceback.format_exc()}")
            return []

    @app_commands.command(name="add_cookie", description="Add a new cookie to the database")
    @app_commands.describe(
        game="Select a game",
        account="Enter the account name",
        cookie="Enter the cookie value"
    )
    @app_commands.autocomplete(game=game_autocomplete)
    async def add_cookie(self, interaction: discord.Interaction, game: str, account: str, cookie: str):
        """Add a cookie for a specific game."""
        logger.info(f"ADD_COOKIE STEP 1: Called with game='{game}', account='{account}', cookie_len={len(cookie)}")
        try:
            logger.info("ADD_COOKIE STEP 2: Starting add_cookie process")

            # Register user if not exists
            logger.info(f"ADD_COOKIE STEP 3: Registering user {interaction.user.id} ({interaction.user.name})")
            await db_ops.register_user(
                user_id=999999999,  # Use default user_id like before migration
                username=interaction.user.name,
                discriminator=interaction.user.discriminator
            )
            logger.info("ADD_COOKIE STEP 4: User registration completed")

            # Add guild membership
            if interaction.guild:
                logger.info(f"ADD_COOKIE STEP 5: Adding guild member for guild {interaction.guild.id} ({interaction.guild.name})")
                await db_ops.add_guild_member(interaction.guild.id, interaction.user.id)
                logger.info("ADD_COOKIE STEP 6: Guild membership added")
            else:
                logger.error("ADD_COOKIE STEP 5: No guild found")

            # Validate inputs
            logger.info(f"ADD_COOKIE STEP 7: Validating cookie length: {len(cookie)}")
            if len(cookie) < 10:
                logger.warning("ADD_COOKIE STEP 8: Cookie too short, rejecting")
                await interaction.response.send_message(
                    "❌ Cookie appears to be too short. Please provide a valid cookie.",
                    ephemeral=True
                )
                return
            logger.info("ADD_COOKIE STEP 8: Cookie validation passed")

            if not interaction.guild:
                logger.error("ADD_COOKIE STEP 9: No guild context")
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!",
                    ephemeral=True
                )
                return
            logger.info(f"ADD_COOKIE STEP 9: Guild context validated: {interaction.guild.name}")

            # Add cookie to database
            logger.info("ADD_COOKIE STEP 10: Calling update_cookie_in_database")
            success = await update_cookie_in_database(
                guild_id=interaction.guild.id,
                user_id=999999999,  # Use default user_id like before migration
                game_name=game,
                account_name=account,
                cookie=cookie
            )
            logger.info(f"ADD_COOKIE STEP 11: Database update result: {success}")

            if success:
                logger.info("ADD_COOKIE STEP 12: Creating success embed")
                embed = discord.Embed(
                    title="✅ Cookie Added Successfully!",
                    description=f"Account `{account}` for **{game.title()}** has been added.",
                    color=0x2ecc71
                )
                embed.add_field(
                    name="🎮 Game", value=game.title(), inline=True
                )
                embed.add_field(
                    name="👤 Account", value=account, inline=True
                )
                embed.add_field(
                    name="🔐 Security", value="Cookie encrypted & stored securely", inline=False
                )
                embed.set_footer(text=f"Added by miHoYo CheckIn Bot")

                logger.info("ADD_COOKIE STEP 13: Sending success response")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"ADD_COOKIE SUCCESS: Cookie added: {account} for {game} by miHoYo CheckIn Bot in {interaction.guild.name}")
            else:
                logger.error("ADD_COOKIE STEP 12: Database update failed")
                await interaction.response.send_message(
                    f"❌ Failed to add cookie for account `{account}` in `{game}`.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"ADD_COOKIE ERROR: {e}")
            logger.error(f"ADD_COOKIE TRACEBACK: {traceback.format_exc()}")
            await interaction.response.send_message(
                "❌ An error occurred while adding the cookie. Please try again.",
                ephemeral=True
            )

    @app_commands.command(name="edit_cookie", description="Edit an existing cookie in the database")
    @app_commands.describe(
        game="Select a game",
        account="Enter the account name",
        new_cookie="Enter the new cookie value"
    )
    @app_commands.autocomplete(game=game_autocomplete, account=account_autocomplete)
    async def edit_cookie(self, interaction: discord.Interaction, game: str, account: str, new_cookie: str):
        """Edit an existing cookie."""
        logger.info(f"EDIT_COOKIE STEP 1: Called with game='{game}', account='{account}', new_cookie_len={len(new_cookie)}")
        try:
            logger.info("EDIT_COOKIE STEP 2: Starting edit_cookie process")

            if not interaction.guild:
                logger.error("EDIT_COOKIE STEP 3: No guild context")
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!",
                    ephemeral=True
                )
                return
            logger.info(f"EDIT_COOKIE STEP 3: Guild context validated: {interaction.guild.name}")

            if len(new_cookie) < 10:
                logger.warning("EDIT_COOKIE STEP 4: Cookie too short, rejecting")
                await interaction.response.send_message(
                    "❌ Cookie appears to be too short. Please provide a valid cookie.",
                    ephemeral=True
                )
                return
            logger.info("EDIT_COOKIE STEP 4: Cookie validation passed")

            logger.info("EDIT_COOKIE STEP 5: Calling edit_cookie_in_database")
            success = await edit_cookie_in_database(
                guild_id=interaction.guild.id,
                user_id=999999999,  # Use default user_id like before migration
                game_name=game,
                account_name=account,
                new_cookie=new_cookie
            )
            logger.info(f"EDIT_COOKIE STEP 6: Database update result: {success}")

            if success:
                logger.info("EDIT_COOKIE STEP 7: Creating success embed")
                embed = discord.Embed(
                    title="✅ Cookie Updated Successfully!",
                    description=f"Account `{account}` for **{game.title()}** has been updated.",
                    color=0x3498db
                )
                embed.add_field(
                    name="🎮 Game", value=game.title(), inline=True
                )
                embed.add_field(
                    name="👤 Account", value=account, inline=True
                )
                embed.set_footer(text=f"Updated by miHoYo CheckIn Bot")

                logger.info("EDIT_COOKIE STEP 8: Sending success response")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"EDIT_COOKIE SUCCESS: Cookie updated: {account} for {game} by miHoYo CheckIn Bot")
            else:
                logger.error("EDIT_COOKIE STEP 7: Database update failed")
                await interaction.response.send_message(
                    f"❌ Failed to update cookie for account `{account}` in `{game}`. Account may not exist.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"EDIT_COOKIE ERROR: {e}")
            logger.error(f"EDIT_COOKIE TRACEBACK: {traceback.format_exc()}")
            await interaction.response.send_message(
                "❌ An error occurred while updating the cookie. Please try again.",
                ephemeral=True
            )

    @app_commands.command(name="delete_cookie", description="Delete an existing cookie from the database")
    @app_commands.describe(
        game="Select a game",
        account="Enter the account name"
    )
    @app_commands.autocomplete(game=game_autocomplete, account=account_autocomplete)
    async def delete_cookie(self, interaction: discord.Interaction, game: str, account: str):
        """Delete a cookie."""
        logger.info(f"DELETE_COOKIE STEP 1: Called with game='{game}', account='{account}'")
        try:
            if not interaction.guild:
                logger.error("DELETE_COOKIE: No guild context")
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!",
                    ephemeral=True
                )
                return

            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Confirm Deletion",
                description=f"Are you sure you want to delete account `{account}` for **{game.title()}**?",
                color=0xe74c3c
            )
            embed.add_field(
                name="📝 Note",
                value="This action cannot be undone. You'll need to re-add the cookie manually.",
                inline=False
            )

            # Create confirmation view
            view = ConfirmationView(interaction.user.id, game, account, interaction.guild.id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            logger.info("DELETE_COOKIE: Confirmation dialog sent")

        except Exception as e:
            logger.error(f"DELETE_COOKIE ERROR: {e}")
            logger.error(f"DELETE_COOKIE TRACEBACK: {traceback.format_exc()}")
            await interaction.response.send_message(
                "❌ An error occurred. Please try again.",
                ephemeral=True
            )


class ConfirmationView(discord.ui.View):
    """Confirmation view for cookie deletion"""

    def __init__(self, user_id: int, game: str, account: str, guild_id: int):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.game = game
        self.account = account
        self.guild_id = guild_id
        logger.info(f"CONFIRMATION VIEW: Created for user {user_id}, game {game}, account {account}")

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"CONFIRM DELETE: Button clicked by user {interaction.user.id}")
        if interaction.user.id != self.user_id:
            logger.warning(f"CONFIRM DELETE: Wrong user clicked button")
            await interaction.response.send_message("❌ Only the command user can confirm this action.", ephemeral=True)
            return

        try:
            logger.info("CONFIRM DELETE: Calling delete_cookie_in_database")
            success = await delete_cookie_in_database(
                guild_id=self.guild_id,
                user_id=self.user_id,
                game_name=self.game,
                account_name=self.account
            )
            logger.info(f"CONFIRM DELETE: Database delete result: {success}")

            if success:
                embed = discord.Embed(
                    title="✅ Cookie Deleted Successfully!",
                    description=f"Account `{self.account}` for **{self.game.title()}** has been deleted.",
                    color=0x2ecc71
                )
                logger.info(f"CONFIRM DELETE SUCCESS: Cookie deleted: {self.account} for {self.game} by miHoYo CheckIn Bot")
            else:
                embed = discord.Embed(
                    title="❌ Deletion Failed",
                    description=f"Could not delete account `{self.account}` for **{self.game.title()}**. It may not exist.",
                    color=0xe74c3c
                )

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            logger.error(f"CONFIRM DELETE ERROR: {e}")
            logger.error(f"CONFIRM DELETE TRACEBACK: {traceback.format_exc()}")
            await interaction.response.send_message("❌ An error occurred during deletion.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"CANCEL DELETE: Button clicked by user {interaction.user.id}")
        if interaction.user.id != self.user_id:
            logger.warning(f"CANCEL DELETE: Wrong user clicked button")
            await interaction.response.send_message("❌ Only the command user can cancel this action.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🚫 Deletion Cancelled",
            description="The cookie deletion has been cancelled.",
            color=0x95a5a6
        )

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)
        logger.info("CANCEL DELETE: Deletion cancelled")

    async def on_timeout(self):
        """Handle timeout"""
        logger.info("CONFIRMATION VIEW: Timeout reached")
        for item in self.children:
            item.disabled = True


async def setup(bot: commands.Bot):
    logger.info("COOKIES COG: Setup function called")
    await bot.add_cog(Cookies(bot))
    logger.info("COOKIES COG: Successfully added to bot")