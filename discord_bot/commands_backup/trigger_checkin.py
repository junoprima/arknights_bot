from discord import app_commands, Interaction
import subprocess

@app_commands.command(name="trigger_checkin", description="Manually trigger the daily check-in process")
async def command(interaction: Interaction):
    """Triggers the main.py script."""
    try:
        # Defer the response to avoid interaction timeout
        await interaction.response.defer(thinking=True)

        # Run the check-in process
        result = subprocess.run(["python", "main.py"], capture_output=True, text=True)

        if result.returncode == 0:
            # Send follow-up message with success
            await interaction.followup.send("Daily check-in triggered successfully!")
        else:
            # Send follow-up message with error output
            await interaction.followup.send(
                f"Failed to trigger daily check-in. Error:\n{result.stderr}"
            )
    except Exception as e:
        # Send follow-up message with exception details
        await interaction.followup.send(f"Error triggering daily check-in: {e}")
