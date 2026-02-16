# Arknights Bot - Deployment Guide

Complete guide to deploy arknights_bot alongside miHoYo_bot on the same server.

## Overview

**Current Setup:**
- Server: 128.199.175.41
- miHoYo_bot: Running on port 8000 (container: mihoyo_bot)
- arknights_bot: Will run on port 8001 (container: arknights_bot)

## Prerequisites

- [x] GitHub repository created: https://github.com/junoprima/arknights_bot
- [ ] Discord bot created and token obtained
- [ ] Bot invited to Discord server
- [ ] Server SSH access

## Step 1: Create Discord Bot

1. Go to https://discord.com/developers/applications
2. Click **"New Application"**
3. Name: **"Arknights Bot"** (or your choice)
4. Go to **"Bot"** tab → Click **"Add Bot"**
5. Copy the **Bot Token** (save for later)
6. Under **"Privileged Gateway Intents"**, enable:
   - ✅ **Server Members Intent**
   - ✅ **Message Content Intent**
7. Save Changes

## Step 2: Invite Bot to Server

1. Go to **"OAuth2"** → **"URL Generator"**
2. Select Scopes:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Select Bot Permissions:
   - ✅ `Read Messages/View Channels`
   - ✅ `Send Messages`
   - ✅ `Embed Links`
   - ✅ `Read Message History`
4. Copy the generated URL
5. Open in browser and select your Discord server
6. Click "Authorize"

## Step 3: Deploy to Server

### 3.1 Clone Repository

```bash
ssh root@128.199.175.41

cd /root/projects
git clone https://github.com/junoprima/arknights_bot.git
cd arknights_bot
```

### 3.2 Create Environment File

```bash
cat > .env << 'EOF'
# Discord Bot Token
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE

# Database
DATABASE_URL=sqlite:////app/data/arknights_bot.db

# Encryption Key (generate new one)
ENCRYPTION_KEY=YOUR_FERNET_KEY_HERE

# Paths
CONSTANTS_PATH=/app/constants.json
LOG_PATH=/app/logs/log.log
EOF
```

**To generate a new encryption key:**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3.3 Create Required Directories

```bash
mkdir -p data logs
```

### 3.4 Update docker-compose.yml

Ensure the file has correct settings:

```yaml
version: '3.8'

services:
  arknights_bot:
    build: .
    container_name: arknights_bot
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    env_file:
      - .env
    ports:
      - "8001:8001"  # Different from miHoYo_bot (8000)
```

### 3.5 Build and Run

```bash
# Build the image
docker-compose build

# Start the container
docker-compose up -d

# Check logs
docker-compose logs -f
```

## Step 4: Initialize Database

```bash
# Enter container
docker exec -it arknights_bot bash

# Run Python to initialize database
python3 << 'PYEOF'
from database.connection import init_database
import asyncio

async def init():
    await init_database()
    print("✅ Database initialized!")

asyncio.run(init())
PYEOF

# Exit container
exit
```

## Step 5: Add Endfield Game to Database

The game will be auto-created from `constants.json` when you add your first account. But you can manually add it:

```bash
docker exec -it arknights_bot python3 << 'PYEOF'
from database.operations import db_ops
from database.connection import init_database
import asyncio

async def add_game():
    await init_database()

    # Check if game exists
    game = await db_ops.get_game_by_name("endfield")
    if game:
        print("✅ Endfield game already exists!")
    else:
        print("Game will be auto-created when first account is added")

asyncio.run(add_game())
PYEOF
```

## Step 6: Configure Discord

In your Discord server:

### 6.1 Set Notification Channel

```
/set_channel channel:#arknights-checkins
```

### 6.2 Add Your Account

Get your SKPort account token:

1. Go to https://www.skport.com/
2. Login to your account
3. Press **F12** (Open DevTools)
4. Go to: **Application** → **Cookies** → `https://www.skport.com`
5. Find: **`account_token`** (NOT `SK_OAUTH_CRED_KEY`)
6. Copy the full value (starts with `eyJ`, ~500+ characters)

Then in Discord:

```
/add_cookie
  game: endfield
  account_name: YourAccountName
  cookie: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9... (paste full token)
```

## Step 7: Test Check-in

```
/trigger_checkin
```

You should see:
- ✅ Processing message
- ✅ Check-in notification in #arknights-checkins channel
- ✅ Reward information displayed

## Step 8: Verify in Logs

```bash
docker-compose logs -f
```

Look for:
```
Processing account: YourAccountName for Arknights: Endfield
OAuth flow successful
Checking Endfield attendance status...
Claiming Endfield attendance...
✓ Claim response status: 200
Attendance claimed successfully! Rewards: ...
```

## Step 9: Set Up Automated Check-ins

### 9.1 Create Cron Job

```bash
# Edit crontab
crontab -e

# Add this line (runs at 6 PM Thailand time daily)
0 18 * * * cd /root/projects/arknights_bot && /usr/bin/docker exec arknights_bot python /app/main.py >> /root/projects/arknights_bot/logs/cron.log 2>&1
```

### 9.2 Verify Cron Job

```bash
# List cron jobs
crontab -l

# Check cron log
tail -f /root/projects/arknights_bot/logs/cron.log
```

## Troubleshooting

### Bot Not Responding to Commands

**Check if bot is running:**
```bash
docker ps | grep arknights
```

**Check logs:**
```bash
docker-compose logs -f
```

**Restart bot:**
```bash
docker-compose restart
```

### Check-in Fails

**Error: "OAuth authentication failed"**
- Token might be expired
- Get fresh token from browser cookies
- Update using `/edit_cookie`

**Error: "Cred-only mode cannot use v2 signature"**
- You used `SK_OAUTH_CRED_KEY` instead of `account_token`
- Get the correct `account_token` from cookies (starts with `eyJ`)

**Check-in shows success but website shows 0 days**
- This is the token issue - using cred instead of JWT
- Get proper `account_token` from browser

### Database Issues

**Reset database (WARNING: Deletes all data):**
```bash
docker-compose down
rm -f data/arknights_bot.db
docker-compose up -d
# Re-initialize database and add accounts
```

### View Current Accounts

```bash
docker exec -it arknights_bot python3 << 'PYEOF'
from database.operations import db_ops
from database.connection import init_database
import asyncio

async def list_accounts():
    await init_database()
    # Query accounts
    print("Checking accounts...")

asyncio.run(list_accounts())
PYEOF
```

## Monitoring

### Check Bot Status

```bash
# Container status
docker ps

# Resource usage
docker stats arknights_bot

# Recent logs
docker-compose logs --tail=50
```

### Check Database Size

```bash
ls -lh data/arknights_bot.db
```

### Check Log Files

```bash
ls -lh logs/
tail -n 100 logs/log.log
```

## Both Bots Running

### Port Allocation
- miHoYo_bot: Port 8000
- arknights_bot: Port 8001

### Container Names
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Should show:
```
NAMES            STATUS        PORTS
mihoyo_bot       Up X hours    8000->8000
arknights_bot    Up X hours    8001->8001
```

### Stop/Start Individual Bots

```bash
# Stop miHoYo bot
cd /root/projects/miHoYo_bot && docker-compose stop

# Start arknights bot
cd /root/projects/arknights_bot && docker-compose start

# Restart both
docker restart mihoyo_bot arknights_bot
```

## Discord Channels Setup

Recommended channel structure:

```
📋 CHECK-INS
├── #hoyo-check-ins        (miHoYo_bot notifications)
└── #arknights-checkins    (arknights_bot notifications)
```

Configure each bot:
```
# In miHoYo_bot
/set_channel channel:#hoyo-check-ins

# In arknights_bot
/set_channel channel:#arknights-checkins
```

## Update Bot

```bash
cd /root/projects/arknights_bot

# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

## Backup

### Backup Database

```bash
# Create backup
cp data/arknights_bot.db data/arknights_bot.db.backup.$(date +%Y%m%d)

# Restore from backup
cp data/arknights_bot.db.backup.20260216 data/arknights_bot.db
docker-compose restart
```

### Backup Environment

```bash
# Backup .env
cp .env .env.backup
```

## Summary Checklist

- [ ] Discord bot created and token obtained
- [ ] Bot invited to Discord server
- [ ] Repository cloned to server
- [ ] `.env` file created with correct token
- [ ] Docker container built and running
- [ ] Database initialized
- [ ] Discord channel configured (`/set_channel`)
- [ ] Account added (`/add_cookie` with JWT token)
- [ ] Test check-in successful (`/trigger_checkin`)
- [ ] Cron job configured for daily automation
- [ ] Logs verified (no errors)
- [ ] Website shows check-in registered

## Support

If you encounter issues:

1. Check logs: `docker-compose logs -f`
2. Verify token type (must be JWT starting with `eyJ`)
3. Check Discord bot permissions
4. Ensure database is initialized
5. Verify environment variables in `.env`

## Next Steps After Deployment

1. Monitor for 24 hours to ensure automated check-ins work
2. Check SKPort website to verify check-ins register properly
3. Add additional accounts if needed
4. Configure notification preferences
5. Set up monitoring/alerting if desired

---

**Deployment completed!** 🎉

Both bots should now be running independently:
- ✅ miHoYo_bot → HoYoverse games
- ✅ arknights_bot → Arknights: Endfield
