import discord
from discord.ext import commands
from discord import app_commands
from utils.database import fetch_all_games, get_guild_accounts
from database.operations import db_ops
import logging

logger = logging.getLogger(__name__)

# Game icons dictionary
GAME_ICONS = {
    "genshin": "https://fastcdn.hoyoverse.com/static-resource-v2/2024/04/12/b700cce2ac4c68a520b15cafa86a03f0_2812765778371293568.png",
    "honkai": "https://fastcdn.hoyoverse.com/static-resource-v2/2024/02/29/3d96534fd7a35a725f7884e6137346d1_3942255444511793944.png",
    "starrail": "https://fastcdn.hoyoverse.com/static-resource-v2/2024/04/12/74330de1ee71ada37bbba7b72775c9d3_1883015313866544428.png",
    "zenless": "https://hyl-static-res-prod.hoyolab.com/communityweb/business/nap.png",
}


class Accounts(commands.Cog):
    """Enhanced Cog for managing account listings with database support"""

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

    @app_commands.command(name="list_accounts", description="List all accounts for a selected game")
    @app_commands.describe(game="Select a game")
    @app_commands.autocomplete(game=game_autocomplete)
    async def list_accounts(self, interaction: discord.Interaction, game: str):
        """List all accounts for a given game in this guild."""
        try:
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!",
                    ephemeral=True
                )
                return

            logger.info(f"Executing 'list_accounts' for game: {game} in guild: {interaction.guild.name}")

            # Get accounts for this guild and game
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

            # Get the game icon
            game_icon = GAME_ICONS.get(game.lower(), "https://via.placeholder.com/150")

            # Create paginated embeds if there are many accounts
            accounts_per_page = 10
            total_pages = (len(accounts) + accounts_per_page - 1) // accounts_per_page

            if total_pages == 1:
                # Single page
                embed = await self.create_accounts_embed(game, accounts, game_icon, 1, 1, interaction.guild.name)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # Multiple pages - create paginated view
                view = AccountsPaginationView(game, accounts, game_icon, interaction.guild.name, interaction.user.id)
                embed = await self.create_accounts_embed(game, accounts[:accounts_per_page], game_icon, 1, total_pages, interaction.guild.name)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in 'list_accounts': {e}")
            await interaction.response.send_message(
                f"❌ An error occurred while listing accounts for `{game}`: {e}",
                ephemeral=True
            )

    async def create_accounts_embed(self, game: str, accounts: list, game_icon: str,
                                  current_page: int, total_pages: int, guild_name: str) -> discord.Embed:
        """Create an embed for displaying accounts"""
        embed = discord.Embed(
            title=f"🎮 {game.title()} Accounts",
            description=f"Accounts registered in **{guild_name}**",
            color=0x3498db
        )

        embed.set_thumbnail(url=game_icon)

        # Add accounts to the embed
        for idx, account in enumerate(accounts, start=(current_page - 1) * 10 + 1):
            account_value = (
                f"**UID:** {account.get('uid', 'Unknown')}\n"
                f"**Nickname:** {account.get('nickname', 'Unknown')}\n"
                f"**Rank:** {account.get('rank', 'Unknown')}\n"
                f"**Region:** {account.get('region', 'Unknown')}\n"
                f"**Cookie:** `{account.get('cookie', 'Unknown')}`"
            )

            embed.add_field(
                name=f"{idx}. {account['name']}",
                value=account_value,
                inline=False
            )

        # Add page info if multiple pages
        if total_pages > 1:
            embed.set_footer(
                text=f"Page {current_page}/{total_pages} • Total: {len(accounts)} accounts • Powered by miHoYo Bot"
            )
        else:
            embed.set_footer(
                text=f"Total: {len(accounts)} accounts • Powered by miHoYo Bot"
            )

        return embed

    @app_commands.command(name="my_accounts", description="List all your accounts across all games")
    async def my_accounts(self, interaction: discord.Interaction):
        """List all accounts belonging to the user across all games"""
        try:
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!",
                    ephemeral=True
                )
                return

            # Get all user's accounts across all games
            user_accounts = {}
            games = await fetch_all_games()

            for game in games:
                accounts = await get_guild_accounts(interaction.guild.id, game)
                # Filter accounts belonging to this user (we need to enhance the function to include user info)
                # For now, we'll show all accounts in the guild
                if accounts:
                    user_accounts[game] = accounts

            if not user_accounts:
                embed = discord.Embed(
                    title="📋 No Accounts Found",
                    description="You don't have any accounts registered in this server.",
                    color=0xe74c3c
                )
                embed.add_field(
                    name="💡 Get Started",
                    value="Use `/add_cookie` to add your first account!",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Create summary embed
            embed = discord.Embed(
                title=f"🎮 Your Game Accounts",
                description=f"All your accounts in **{interaction.guild.name}**",
                color=0x2ecc71
            )

            total_accounts = 0
            for game, accounts in user_accounts.items():
                game_icon = GAME_ICONS.get(game.lower(), "🎮")
                account_count = len(accounts)
                total_accounts += account_count

                account_names = [acc['name'] for acc in accounts[:3]]  # Show first 3
                account_list = ", ".join(account_names)
                if account_count > 3:
                    account_list += f" ... and {account_count - 3} more"

                embed.add_field(
                    name=f"{game_icon} {game.title()}",
                    value=f"**{account_count}** account(s)\n{account_list}",
                    inline=False
                )

            embed.set_footer(text=f"Total: {total_accounts} accounts across {len(user_accounts)} games")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in 'my_accounts': {e}")
            await interaction.response.send_message(
                "❌ An error occurred while retrieving your accounts.",
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

            # Get check-in statistics
            stats = await db_ops.get_checkin_stats(interaction.guild.id)

            embed = discord.Embed(
                title=f"📊 Server Statistics",
                description=f"miHoYo Bot statistics for **{interaction.guild.name}**",
                color=0x9b59b6
            )

            if stats:
                total_checkins = sum(game['total_checkins'] for game in stats.values())
                total_successful = sum(game['successful_checkins'] for game in stats.values())
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

                for game_name, game_stats in stats.items():
                    game_icon = GAME_ICONS.get(game_name.lower().replace(" ", "").replace(":", ""), "🎮")
                    embed.add_field(
                        name=f"{game_icon} {game_name}",
                        value=(
                            f"Check-ins: {game_stats['total_checkins']}\n"
                            f"Success: {game_stats['successful_checkins']}\n"
                            f"Rate: {game_stats['success_rate']}%"
                        ),
                        inline=True
                    )
            else:
                embed.add_field(
                    name="📊 No Data Yet",
                    value="No check-in statistics available for this month.",
                    inline=False
                )

            # Add webhook status
            webhook_url = await db_ops.get_guild_webhook(interaction.guild.id)
            webhook_status = "✅ Configured" if webhook_url else "❌ Not configured"

            embed.add_field(
                name="🔗 Webhook Status",
                value=webhook_status,
                inline=True
            )

            embed.set_footer(
                text=f"Guild ID: {interaction.guild.id} • Data from current month"
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in guild_stats: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while retrieving server statistics.",
                ephemeral=True
            )


class AccountsPaginationView(discord.ui.View):
    """Pagination view for accounts listing"""

    def __init__(self, game: str, accounts: list, game_icon: str, guild_name: str, user_id: int):
        super().__init__(timeout=300)  # 5 minutes
        self.game = game
        self.accounts = accounts
        self.game_icon = game_icon
        self.guild_name = guild_name
        self.user_id = user_id
        self.current_page = 1
        self.accounts_per_page = 10
        self.total_pages = (len(accounts) + self.accounts_per_page - 1) // self.accounts_per_page

        # Update button states
        self.update_button_states()

    def update_button_states(self):
        """Update button enabled/disabled states"""
        self.first_page.disabled = self.current_page == 1
        self.prev_page.disabled = self.current_page == 1
        self.next_page.disabled = self.current_page == self.total_pages
        self.last_page.disabled = self.current_page == self.total_pages

    def get_current_accounts(self):
        """Get accounts for current page"""
        start_idx = (self.current_page - 1) * self.accounts_per_page
        end_idx = start_idx + self.accounts_per_page
        return self.accounts[start_idx:end_idx]

    @discord.ui.button(label="First", style=discord.ButtonStyle.secondary, emoji="⏪")
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate pages.", ephemeral=True)
            return

        self.current_page = 1
        self.update_button_states()

        # Update embed
        from cogs.accounts import Accounts
        accounts_cog = Accounts(None)
        embed = await accounts_cog.create_accounts_embed(
            self.game, self.get_current_accounts(), self.game_icon,
            self.current_page, self.total_pages, self.guild_name
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate pages.", ephemeral=True)
            return

        self.current_page -= 1
        self.update_button_states()

        from cogs.accounts import Accounts
        accounts_cog = Accounts(None)
        embed = await accounts_cog.create_accounts_embed(
            self.game, self.get_current_accounts(), self.game_icon,
            self.current_page, self.total_pages, self.guild_name
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji="➡️")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate pages.", ephemeral=True)
            return

        self.current_page += 1
        self.update_button_states()

        from cogs.accounts import Accounts
        accounts_cog = Accounts(None)
        embed = await accounts_cog.create_accounts_embed(
            self.game, self.get_current_accounts(), self.game_icon,
            self.current_page, self.total_pages, self.guild_name
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Last", style=discord.ButtonStyle.secondary, emoji="⏩")
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the command user can navigate pages.", ephemeral=True)
            return

        self.current_page = self.total_pages
        self.update_button_states()

        from cogs.accounts import Accounts
        accounts_cog = Accounts(None)
        embed = await accounts_cog.create_accounts_embed(
            self.game, self.get_current_accounts(), self.game_icon,
            self.current_page, self.total_pages, self.guild_name
        )

        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True


async def setup(bot: commands.Bot):
    await bot.add_cog(Accounts(bot))