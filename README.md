# Blood on the Clocktower Discord Bot Setup Guide

This guide walks you through setting up and deploying the BOTC Discord bot on Render. It covers both Discord bot creation and Render deployment.

## Table of Contents

1. [Discord Bot Creation](#discord-bot-creation)
2. [Render Deployment](#render-deployment)
3. [Configuration](#configuration)
4. [Testing Your Bot](#testing-your-bot)
5. [Troubleshooting](#troubleshooting)

---

## Discord Bot Creation

### Step 1: Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click the **"New Application"** button in the top right
3. Give your application a name (e.g., "BOTC Game Bot")
4. Accept the terms and click **"Create"**
5. You'll be taken to the application overview page

### Step 2: Create the Bot User

1. In the left sidebar, click **"Bot"**
2. Click the **"Add Bot"** button
3. Under the **TOKEN** section, click **"Reset Token"** and copy your token
   - **⚠️ KEEP THIS PRIVATE!** Anyone with this token can control your bot
   - Never commit it to GitHub or share it publicly

### Step 3: Configure Bot Permissions

1. In the left sidebar, click **"OAuth2"** → **"URL Generator"**
2. Under **SCOPES**, select:
   - `bot`
3. Under **PERMISSIONS**, select:
   - `Send Messages`
   - `Read Message History`
   - `Add Reactions`
   - `Manage Messages`
   - `Embed Links`
   - `Manage Events`

4. Copy the generated URL at the bottom (the URL Generator shows your invite link)
5. Open this URL in your browser and select which server to invite the bot to
6. The bot should now appear in your server with a "BOT" badge

### Step 4: Enable Message Content Intent

1. Back in the Developer Portal, go to **"Bot"** in the left sidebar
2. Under **INTENTS**, enable:
   - ✅ **Message Content Intent** (required for reading message reactions)
   - ✅ **Server Members Intent** (optional, but recommended)
   - ✅ **Guild Scheduled Events Intent** (for Discord event creation)

3. Click **"Save Changes"**

---

## Render Deployment

### Step 1: Fork the Repository

1. Go to [arosato97/botc-discord-bot](https://github.com/arosato97/botc-discord-bot) on GitHub
2. Click the **"Fork"** button in the top right corner
3. Choose your GitHub account as the owner
4. Click **"Create fork"**

You now have your own copy of the repository that you can customize!

### Step 2: Clone Your Fork (Optional)

If you want to make local changes before deploying:

```bash
git clone https://github.com/YOUR_USERNAME/botc-discord-bot.git
cd botc-discord-bot
```

Make any customizations (timezone, game time, etc.), then push to your fork:

```bash
git add .
git commit -m "Customize game settings"
git push origin main
```

### Step 3: Set Up Render

1. Go to [Render](https://render.com) and sign up/log in
2. Click **"New"** in the top right and select **"Web Service"**
3. Select **"Build and deploy from a Git repository"**
4. Connect your GitHub account and authorize Render
5. Select the botc-discord-bot repository

### Step 4: Configure the Web Service

Fill in the following settings:

| Setting | Value |
|---------|-------|
| **Name** | `botc-discord-bot` |
| **Environment** | `Python 3` |
| **Region** | Choose closest to your location |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python bot.py` |
| **Instance Type** | `Starter` (0.5 CPU, 512 MB) - $7/month |

### Step 5: Add Environment Variables

1. Scroll down to **"Environment"**
2. Click **"Add Environment Variable"**
3. Add the following:
   - **Key:** `DISCORD_TOKEN`
   - **Value:** *Paste your bot token from Discord Developer Portal*

4. Click **"Save"** for each variable

### Step 6: Deploy

1. Click **"Create Web Service"**
2. Render will start building and deploying your bot automatically
3. Watch the logs to confirm it starts successfully
   - You should see: `BOT READY: [YourBotName] has connected to Discord!`

---

## Configuration

### Timezone Settings

By default, the bot is configured for Eastern Time. To change it:

1. In `bot.py`, find this line (around line 21):
   ```python
   TIMEZONE = "America/New_York"  # Change this to your timezone
   ```

2. Change to your timezone. Common US options:
   - `America/New_York` (Eastern)
   - `America/Chicago` (Central)
   - `America/Denver` (Mountain)
   - `America/Los_Angeles` (Pacific)

3. Or use any timezone from [this list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

4. Commit and push the change:
   ```bash
   git add bot.py
   git commit -m "Update timezone to [YourTimezone]"
   git push origin main
   ```

Render will automatically redeploy with the new timezone.

### Game Time and Location

Update the default game time and location in `bot.py`:

- **Game time (line ~30):** Change `GAME_TIME = (19, 30)` to your preferred time (24-hour format)
- **Game day (line ~28):** Change `GAME_DAY = 3` (0=Monday, 6=Sunday)
- **Location (line ~850):** Update `location="105 Lawton Street..."` to your actual game location

### Player Limits

Adjust these constants as needed:

```python
MAX_MAIN_PLAYERS = 15        # Maximum main players per game
MAX_TRAVELERS = 5            # Maximum travelers per game
MAX_STORYTELLERS = 1         # Number of storytellers needed
```

---

## Testing Your Bot

### In Discord

1. Go to your Discord server
2. Use these commands to test:
   - `/ping` - Check bot responsiveness
   - `/time_debug` - Verify timezone settings
   - `/check_permissions` - Ensure bot has required permissions
   - `/setup_game` - Create the signup message

### Viewing Logs

To see what your bot is doing in real-time:

1. Go to your Render dashboard
2. Click on your service name
3. Click **"Logs"** tab at the top
4. Logs will stream in real-time as events happen

### Using Your Bot

#### For Admins

Once deployed, use these commands to manage signups:

- `/setup_game` - Create the weekly signup message
  - Optional: `/setup_game day:"Thursday" time:"7:30 PM"`
- `/reset_signups` - Clear signups but keep the message
- `/reset_game` - Complete reset for a new week
- `/game_status` - View current signups
- `/debug_players` - See detailed player data (debug only)

#### For Players

Players react to the signup message with emojis to sign up:

- 🕯️ Storyteller (1 needed)
- 🛡️ Main player (+1 main)
- ⚔️ Main players (+2 main)
- 🏹 Main players (+3 main)
- ⚡ Main players (+4 main)
- 🧳 Traveler (+1 traveler)
- 🚗 Travelers (+2 travelers)
- ✈️ Travelers (+3 travelers)
- 🚂 Travelers (+4 travelers)
- 🏄‍♀️ Just hanging out
- 🦭 Get a cute seal GIF!

Players can react to multiple emoji types to bring mixed groups!

---

## Troubleshooting

### Bot Won't Start

**Check the logs in Render:**

1. Go to your service on Render
2. Click **"Logs"** tab
3. Look for error messages

**Common issues:**

- `DISCORD_TOKEN not set` → Add the environment variable in Render settings
- `Module not found` → Update `requirements.txt` with missing packages
- `Connection refused` → Bot token is invalid; regenerate it in Discord Developer Portal

### Bot Stops Running

**Possible causes:**

- Paid Render instances can stop if resources are exceeded
- **Solution:** Upgrade instance size or optimize bot code

**Reactions Not Working**

**Check permissions:**

1. Run `/check_permissions` in Discord
2. If permissions are missing, the bot needs more privileges
3. Go to Discord Developer Portal → OAuth2 → URL Generator → Re-authorize with correct scopes

**Check intents:**

1. Go to Discord Developer Portal → Bot → Intents
2. Ensure these are enabled:
   - ✅ Message Content Intent
   - ✅ Guild Scheduled Events Intent

### Timezone Issues

**If game times are wrong:**

1. Run `/time_debug` in Discord to see current time settings
2. Verify the `TIMEZONE` variable in `bot.py` is correct
3. Check that your Render server region makes sense for your timezone

---

## Extra Info: Custom Game Times

You can set custom game times without editing code using:

```
/setup_game day:"Saturday" time:"8:30 PM" timezone:"America/Los_Angeles"
```

The bot will create a Discord event for the custom time automatically!

---

## Getting Help

If you encounter issues:

1. **Check the Render logs** for detailed error messages
2. **Run debugging commands** in Discord: `/time_debug`, `/check_permissions`, `/debug_players`
3. **Verify Discord permissions** in your server settings
4. **Regenerate the bot token** if you suspect it's compromised

---

## Next Steps

- Customize the game settings to match your group
- Pin the signup message to your game channel
- Create a recurring reminder to run `/reset_game` weekly
- Share this guide with others in your community!

Enjoy your game nights! 🎲