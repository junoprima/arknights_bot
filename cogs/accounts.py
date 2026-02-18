import discord
from discord.ext import commands
from discord import app_commands
from utils.database import fetch_all_games, get_guild_accounts
from database.operations import db_ops
import logging

logger = logging.getLogger(__name__)

# Game icons for Endfield
GAME_ICONS = {
    "endfield": "https://play-lh.googleusercontent.com/IHJeGhqSpth4VzATp_afjsCnFRc-uYgGC1EV3b2tryjyZsVrbcaeN5L_m8VKwvOSpIu_Skc49mDpLsAzC6Jl3mM",
}


class Accounts(commands.Cog):
    """Cog for managing Endfield account listings"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def game_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for game names"""
        try:
            games = await fetch_all_games()
            return [
                app_commands.Choice(name=game.title(), value=game)
                for game in games
                if current.lower() in game.lower()
            ][:25]
        except Exception as e:
            logger.error(f"Error in game autocomplete: {e}")
            return []

    @app_commands.command(name="list_accounts", description="List all accounts for Endfield")
    @app_commands.describe(game="Select a game")
    @app_commands.autocomplete(game=game_autocomplete)
    async def list_accounts(self, interaction: discord.Interaction, game: str):
        """List all accounts for Endfield in this guild."""
        try:
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!",
                    ephemeral=True
                )
                return

            logger.info(f"Executing 'list_accounts' for game: {game} in guild: {interaction.guild.name}")

            accounts = await get_guild_accounts(interaction.guild.id, game)

            if not accounts:
                embed = discord.Embed(
                    title=f"📋 No Accounts Found",
                    description=f"No accounts found for **{game.title()}** in this server.",
                    color=0xe74c3c
                )
                embed.add_field(
                    name="💡 Get Started",
                    value=f"Use `/add_cookie` to add your first {game.title()} account!",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            game_icon = GAME_ICONS.get(game.lower(), "https://via.placeholder.com/150")

            embed = discord.Embed(
                title=f"🎮 {game.title()} Accounts",
                description=f"Accounts registered in **{interaction.guild.name}**",
                color=0x3498db
            )
            embed.set_thumbnail(url=game_icon)

            for idx, account in enumerate(accounts, start=1):
                account_name = getattr(account, 'name', 'Unknown')
                is_active = getattr(account, 'is_active', True)
                status = "✅ Active" if is_active else "❌ Inactive"
                
                embed.add_field(
                    name=f"{idx}. {account_name}",
                    value=f"**Status:** {status}",
                    inline=False
                )

            embed.set_footer(text=f"Total: {len(accounts)} accounts")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in 'list_accounts': {e}")
            await interaction.response.send_message(
                f"❌ An error occurred: {e}",
                ephemeral=True
            )

    @app_commands.command(name="my_accounts", description="List all your accounts")
    async def my_accounts(self, interaction: discord.Interaction):
        """List all accounts in the guild"""
        try:
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!",
                    ephemeral=True
                )
                return

            user_accounts = {}
            games = await fetch_all_games()

            for game in games:
                accounts = await get_guild_accounts(interaction.guild.id, game)
                if accounts:
                    user_accounts[game] = accounts

            if not user_accounts:
                embed = discord.Embed(
                    title="📋 No Accounts Found",
                    description="No accounts registered in this server.",
                    color=0xe74c3c
                )
                embed.add_field(
                    name="💡 Get Started",
                    value="Use `/add_cookie` to add your first account!",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title=f"🎮 Game Accounts",
                description=f"All accounts in **{interaction.guild.name}**",
                color=0x2ecc71
            )

            total_accounts = 0
            for game, accounts in user_accounts.items():
                account_count = len(accounts)
                total_accounts += account_count
                account_names = [getattr(acc, 'name', 'Unknown') for acc in accounts[:5]]
                account_list = ", ".join(account_names)
                if account_count > 5:
                    account_list += f" ... +{account_count - 5} more"

                embed.add_field(
                    name=f"🎮 {game.title()}",
                    value=f"**{account_count}** account(s)\n{account_list}",
                    inline=False
                )

            embed.set_footer(text=f"Total: {total_accounts} accounts")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in 'my_accounts': {e}")
            await interaction.response.send_message(
                "❌ An error occurred while retrieving accounts.",
                ephemeral=True
            )

    @app_commands.command(name="guild_stats", description="Show server statistics (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def guild_stats(self, interaction: discord.Interaction):
        """Show guild statistics"""
        try:
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!",
                    ephemeral=True
                )
                return

            stats = await db_ops.get_checkin_stats(interaction.guild.id)

            embed = discord.Embed(
                title=f"📊 Server Statistics",
                description=f"Bot statistics for **{interaction.guild.name}**",
                color=0x9b59b6
            )

            if stats:
                total_checkins = sum(game.get('total_checkins', 0) for game in stats.values())
                total_successful = sum(game.get('successful_checkins', 0) for game in stats.values())
                overall_rate = (total_successful / total_checkins * 100) if total_checkins > 0 else 0

                embed.add_field(
                    name="📈 Overall Statistics",
                    value=(
                        f"**Total Check-ins:** {total_checkins}\n"
                        f"**Successful:** {total_successful}\n"
                        f"**Success Rate:** {overall_rate:.1f}%"
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="📊 No Data Yet",
                    value="No check-in statistics available.",
                    inline=False
                )

            embed.set_footer(text=f"Guild ID: {interaction.guild.id}")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in guild_stats: {e}")
            await interaction.response.send_message(
                "❌ An error occurred.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Accounts(bot))
