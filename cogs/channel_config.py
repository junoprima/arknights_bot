import discord
from discord.ext import commands
from discord import app_commands
from database.operations import db_ops
import logging

logger = logging.getLogger(__name__)

class ChannelConfig(commands.Cog):
    """Cog for configuring bot channels and settings"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="set_channel", description="Set the channel for automated messages (Admin only)")
    @app_commands.describe(
        channel="Select the channel for check-in results and notifications",
        message_type="Type of messages to send to this channel"
    )
    @app_commands.choices(message_type=[
        app_commands.Choice(name="Check-in Results", value="checkin"),
        app_commands.Choice(name="All Bot Messages", value="all"),
        app_commands.Choice(name="Error Notifications", value="errors")
    ])
    @app_commands.default_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel, message_type: str = "checkin"):
        """Set channel for automated bot messages"""
        try:
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!",
                    ephemeral=True
                )
                return

            # Register guild if not exists
            await db_ops.register_guild(
                guild_id=interaction.guild.id,
                guild_name=interaction.guild.name
            )

            # Set channel configuration
            await db_ops.set_guild_setting(
                guild_id=interaction.guild.id,
                key=f"channel_{message_type}",
                value=str(channel.id)
            )

            # Create success embed
            embed = discord.Embed(
                title="✅ Channel Configured Successfully!",
                description=f"**{channel.mention}** has been set for **{message_type}** messages.",
                color=0x00ff00
            )

            embed.add_field(
                name="📋 Configuration Details",
                value=(
                    f"**Channel:** {channel.name}\n"
                    f"**Channel ID:** {channel.id}\n"
                    f"**Message Type:** {message_type.title()}\n"
                    f"**Configured by:** {interaction.user.mention}"
                ),
                inline=False
            )

            embed.add_field(
                name="🎮 What happens next?",
                value=(
                    "✅ Daily check-in results will be sent here\n"
                    "✅ Bot notifications will appear in this channel\n"
                    "✅ You can change this anytime with `/set_channel`"
                ),
                inline=False
            )

            embed.set_footer(
                text=f"Server: {interaction.guild.name} • miHoYo Bot",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )

            await interaction.response.send_message(embed=embed)

            # Also send a test message to the configured channel
            test_embed = discord.Embed(
                title="🤖 Channel Setup Complete!",
                description=f"This channel has been configured for **{message_type}** messages.",
                color=0x3498db
            )
            test_embed.add_field(
                name="✨ Ready for:",
                value="• Daily check-in results\n• Game notifications\n• Bot status updates",
                inline=False
            )

            await channel.send(embed=test_embed)

        except Exception as e:
            logger.error(f"Error in set_channel: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred while setting the channel: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="show_channels", description="Show current channel configuration (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def show_channels(self, interaction: discord.Interaction):
        """Show current channel configuration"""
        try:
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!",
                    ephemeral=True
                )
                return

            # Get channel settings
            checkin_channel_id = await db_ops.get_guild_setting(interaction.guild.id, "channel_checkin")
            all_channel_id = await db_ops.get_guild_setting(interaction.guild.id, "channel_all")
            errors_channel_id = await db_ops.get_guild_setting(interaction.guild.id, "channel_errors")

            embed = discord.Embed(
                title="📋 Channel Configuration",
                description=f"Current channel settings for **{interaction.guild.name}**",
                color=0x3498db
            )

            # Check-in channel
            if checkin_channel_id:
                try:
                    channel = interaction.guild.get_channel(int(checkin_channel_id))
                    if channel:
                        embed.add_field(
                            name="🎮 Check-in Results",
                            value=f"✅ {channel.mention}",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="🎮 Check-in Results",
                            value="❌ Channel not found (deleted?)",
                            inline=False
                        )
                except:
                    embed.add_field(
                        name="🎮 Check-in Results",
                        value="❌ Invalid channel ID",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="🎮 Check-in Results",
                    value="❌ Not configured",
                    inline=False
                )

            embed.add_field(
                name="🔧 How to configure",
                value="Use `/set_channel` to configure channels for different message types.",
                inline=False
            )

            embed.set_footer(text="Use /set_channel to configure channels")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in show_channels: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelConfig(bot))