#!/bin/bash
set -e

# Set timezone
ln -snf /usr/share/zoneinfo/${TIMEZONE:-Asia/Bangkok} /etc/localtime
echo ${TIMEZONE:-Asia/Bangkok} > /etc/timezone

# Setup cron job
CRON_SCHEDULE="${CHECKIN_CRON_SCHEDULE:-5 23 * * *}"
echo "================================================"
echo "Bot starting at $(date)"
echo "Timezone: ${TIMEZONE:-Asia/Bangkok}"
echo "Cron schedule: $CRON_SCHEDULE"
echo "================================================"

# Export env vars for cron
printenv | grep -E "^(DISCORD_|DB_|ENCRYPTION_|TIMEZONE|LOG_|DEBUG)" > /etc/environment

# Create cron job
echo "$CRON_SCHEDULE root cd /app && /usr/local/bin/python main.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/bot-cron
echo "" >> /etc/cron.d/bot-cron
chmod 0644 /etc/cron.d/bot-cron

# Start cron daemon
service cron start
echo "✅ Cron service started"

# Start bot (foreground)
echo "✅ Starting Discord bot..."
exec python -m discord_bot.bot
