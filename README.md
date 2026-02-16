# Arknights Bot - Daily Check-in Automation

Discord bot for automating daily check-ins for Arknights: Endfield via SKPort API.

## Features

- ✅ **Automated Daily Check-ins** - Automatic attendance submission for Arknights: Endfield
- ✅ **Discord Integration** - Slash commands for managing accounts
- ✅ **Multi-Account Support** - Manage multiple Endfield accounts
- ✅ **Encrypted Storage** - Secure token storage using Fernet encryption
- ✅ **Discord Notifications** - Beautiful embeds showing check-in results and rewards
- ✅ **Scheduled Tasks** - Automated daily check-ins via cron

## Architecture

Based on miHoYo_bot design pattern but specialized for Arknights/SKPort API.

## Supported Games

- **Arknights: Endfield** - via SKPort API

## Getting SKPort Account Token

1. Go to https://www.skport.com/
2. Login to your account
3. Press **F12** (DevTools)
4. Go to: **Application** → **Cookies** → `https://www.skport.com`
5. Find cookie: **`account_token`**
6. Copy the **full value** (starts with `eyJ`, very long ~500+ characters)

**DO NOT** use `SK_OAUTH_CRED_KEY` - that's the cred value which won't work for check-ins!

##License

Based on miHoYo_bot architecture
