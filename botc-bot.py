import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import json
import os
import signal
import sys
import pytz  # You'll need to install this: pip install pytz
import logging

# Setup python logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Timezone config
TIMEZONE = "America/New_York"  # Change this to your timezone
# Other common US timezones:
# "America/New_York" (Eastern)
# "America/Chicago" (Central)
# "America/Denver" (Mountain)
# "America/Los_Angeles" (Pacific)


def get_current_time_info():
    """Helper function to debug timezone issues"""
    tz = pytz.timezone(TIMEZONE)
    now_local = datetime.now(tz)
    now_utc = datetime.now(pytz.UTC)

    return {
        "local_time": now_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "utc_time": now_utc.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "timezone": TIMEZONE,
        "next_game": get_next_thursday().strftime("%Y-%m-%d %H:%M:%S %Z"),
    }


# Workaround for audioop module issue
try:
    import audioop
except ImportError:
    import sys

    sys.modules["audioop"] = None

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.guild_scheduled_events = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Game configuration
MAX_MAIN_PLAYERS = 15
MAX_TRAVELERS = 5
MAIN_PLAYER_EMOJI = "🛡️"  # Shield for solo main player
TRAVELER_EMOJI = "🧳"  # Luggage for solo traveler
HANGOUT_EMOJI = "🏄‍♀️"  # Woman surfing for hanging out

# Guest emojis for main players (1-4 guests)
MAIN_GUEST_EMOJIS = ["🗡️", "⚔️", "🏹", "⚡"]  # Dagger +1, Swords +2, Bow +3, Lightning +4
# Guest emojis for travelers (1-4 guests)
TRAVELER_GUEST_EMOJIS = [
    "🚗",
    "✈️",
    "🚂",
    "🚢",
]  # Car +1, Plane +2, Train +3, Cruise Ship +4

# Combined emoji sets for easy checking
ALL_MAIN_EMOJIS = [MAIN_PLAYER_EMOJI] + MAIN_GUEST_EMOJIS
ALL_TRAVELER_EMOJIS = [TRAVELER_EMOJI] + TRAVELER_GUEST_EMOJIS

GAME_DAY = 3  # Thursday (0=Monday, 6=Sunday)
GAME_TIME = (19, 30)  # 7:30 PM

# Storage for game data
game_data = {
    "players": [],  # [{'user_id': int, 'main_count': int, 'traveler_count': int, 'hangout': bool}, ...]
    "message_id": None,
    "channel_id": None,
    "event_id": None,
    "week_of": None,
}


# Graceful shutdown handling
def signal_handler(signum, frame):
    print(f"Received signal {signum}, shutting down gracefully...")
    save_game_data()
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def save_game_data():
    """Save game data to a JSON file"""
    try:
        with open("game_data.json", "w") as f:
            json.dump(game_data, f, indent=2)
        print("Game data saved successfully")
    except Exception as e:
        print(f"Error saving game data: {e}")


def load_game_data():
    """Load game data from JSON file"""
    global game_data
    try:
        if os.path.exists("game_data.json"):
            with open("game_data.json", "r") as f:
                loaded_data = json.load(f)
                game_data.update(loaded_data)
            print("Game data loaded successfully")
    except Exception as e:
        print(f"Error loading game data: {e}")


def get_total_main_count():
    """Get total count of main players including guests"""
    return sum(player.get("main_count", 0) for player in game_data["players"])


def get_total_traveler_count():
    """Get total count of travelers including guests"""
    return sum(player.get("traveler_count", 0) for player in game_data["players"])


def get_hangout_players():
    """Get list of players who are hanging out"""
    return [player for player in game_data["players"] if player.get("hangout", False)]


def find_player(user_id):
    """Find a player by user_id"""
    for i, player in enumerate(game_data["players"]):
        if player["user_id"] == user_id:
            return i
    return -1


def get_guest_count_from_emoji(emoji, group_type):
    """Get the number of guests from emoji"""
    if group_type == "main":
        if emoji == MAIN_PLAYER_EMOJI:
            return 1  # Solo player counts as 1
        try:
            return (
                MAIN_GUEST_EMOJIS.index(emoji) + 2
            )  # +1 for the emoji index, +1 for the player
        except ValueError:
            return 0
    else:  # traveler
        if emoji == TRAVELER_EMOJI:
            return 1  # Solo traveler counts as 1
        try:
            return (
                TRAVELER_GUEST_EMOJIS.index(emoji) + 2
            )  # +1 for the emoji index, +1 for the player
        except ValueError:
            return 0


def get_next_thursday():
    """Get the next Thursday at 7:30 PM in the specified timezone"""
    # Get timezone object
    tz = pytz.timezone(TIMEZONE)

    # Get current time in the specified timezone
    now = datetime.now(tz)

    # Calculate days until next Thursday
    days_ahead = GAME_DAY - now.weekday()
    if days_ahead <= 0:  # Thursday already passed this week
        days_ahead += 7

    # Create next Thursday at game time
    next_thursday = now + timedelta(days=days_ahead)
    next_thursday = next_thursday.replace(
        hour=GAME_TIME[0], minute=GAME_TIME[1], second=0, microsecond=0
    )

    return next_thursday


def create_signup_embed():
    """Create the signup embed message"""
    embed = discord.Embed(
        title="🕐 Blood on the Clocktower - Weekly Game Night",
        description="React to join the game! You can react to multiple emojis to bring mixed groups.",
        color=0x8B0000,
    )

    next_game = get_next_thursday()
    embed.add_field(
        name="📅 Next Game", value=f"<t:{int(next_game.timestamp())}:F>", inline=False
    )

    # Get totals
    total_main_count = get_total_main_count()
    total_traveler_count = get_total_traveler_count()

    # Main players section
    main_players_text = ""
    for i, player in enumerate(game_data["players"], 1):
        main_count = player.get("main_count", 0)
        if main_count > 0:
            main_players_text += f"{i}. <@{player['user_id']}> ({main_count})\n"

    if not main_players_text:
        main_players_text = "No main players signed up yet"

    embed.add_field(
        name=f"🛡️ Main Players ({total_main_count}/{MAX_MAIN_PLAYERS})",
        value=main_players_text,
        inline=True,
    )

    # Travelers section
    travelers_text = ""
    for i, player in enumerate(game_data["players"], 1):
        traveler_count = player.get("traveler_count", 0)
        if traveler_count > 0:
            travelers_text += f"{i}. <@{player['user_id']}> ({traveler_count})\n"

    if not travelers_text:
        travelers_text = "No travelers signed up yet"

    embed.add_field(
        name=f"🧳 Travelers ({total_traveler_count}/{MAX_TRAVELERS})",
        value=travelers_text,
        inline=True,
    )

    # Hangout section
    hangout_players = get_hangout_players()
    hangout_text = ""
    for i, player in enumerate(hangout_players, 1):
        hangout_text += f"{i}. <@{player['user_id']}>\n"

    if not hangout_text:
        hangout_text = "No one hanging out yet"

    embed.add_field(
        name=f"🏄‍♀️ Coming to hang ({len(hangout_players)})",
        value=hangout_text,
        inline=False,
    )

    # Instructions
    instructions = f"""**Main Players:**
{MAIN_PLAYER_EMOJI} +1 Main Player
{MAIN_GUEST_EMOJIS[0]} +2 Main Players
{MAIN_GUEST_EMOJIS[1]} +3 Main Players
{MAIN_GUEST_EMOJIS[2]} +4 Main Players
{MAIN_GUEST_EMOJIS[3]} +5 Main Players

**Travelers:**
{TRAVELER_EMOJI} +1 Traveler
{TRAVELER_GUEST_EMOJIS[0]} +2 Travelers
{TRAVELER_GUEST_EMOJIS[1]} +3 Travelers
{TRAVELER_GUEST_EMOJIS[2]} +4 Travelers
{TRAVELER_GUEST_EMOJIS[3]} +5 Travelers

**Hanging Out:**
{HANGOUT_EMOJI} Coming to hang and watch!

**Mix & Match:** React to multiple emojis to bring mixed groups!
Example: 🛡️ + 🚗 = You as main player + 2 traveler guests!"""

    embed.add_field(name="How to Join", value=instructions, inline=False)

    embed.set_footer(text="🎲 May the odds be ever in your favor! 🎲")

    return embed


def check_bot_permissions(channel):
    """Check if the bot has necessary permissions"""
    permissions = channel.permissions_for(channel.guild.me)

    required_perms = {
        "read_messages": permissions.read_messages,
        "send_messages": permissions.send_messages,
        "manage_messages": permissions.manage_messages,  # Needed to remove reactions
        "add_reactions": permissions.add_reactions,
        "read_message_history": permissions.read_message_history,
        "embed_links": permissions.embed_links,
        "manage_events": permissions.manage_events,  # For Discord events
    }

    missing_perms = [perm for perm, has_perm in required_perms.items() if not has_perm]

    return missing_perms


async def safe_remove_reaction(message, emoji, user):
    """Safely remove a reaction with error handling"""
    try:
        # Check if bot has manage_messages permission
        if not message.channel.permissions_for(message.guild.me).manage_messages:
            print(f"Bot lacks 'Manage Messages' permission in {message.channel.name}")
            return False

        await message.remove_reaction(emoji, user)
        return True
    except discord.Forbidden:
        print(
            f"Bot doesn't have permission to remove reactions in {message.channel.name}"
        )
        return False
    except discord.NotFound:
        print(f"Reaction {emoji} not found or user {user} hasn't reacted")
        return False
    except discord.HTTPException as e:
        print(f"HTTP error removing reaction: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error removing reaction: {e}")
        return False


async def remove_user_reactions_from_group(message, user, group_emojis):
    """Remove all of a user's reactions from a specific emoji group"""
    try:
        # Check permissions first
        missing_perms = check_bot_permissions(message.channel)
        if "manage_messages" in missing_perms:
            print(
                f"Warning: Bot missing 'Manage Messages' permission in {message.channel.name}"
            )
            return False

        success = True
        for emoji in group_emojis:
            # Check if the user has reacted to this emoji
            for reaction in message.reactions:
                if str(reaction.emoji) == emoji:
                    # Check if the user has reacted to this
                    async for reaction_user in reaction.users():
                        if reaction_user.id == user.id:
                            removal_success = await safe_remove_reaction(
                                message, emoji, user
                            )
                            if not removal_success:
                                success = False
                            break
        return success
    except Exception as e:
        print(f"Error removing user reactions: {e}")
        return False


@bot.tree.command(
    name="debug_reactions", description="Create a test message to debug reaction events"
)
async def debug_reactions(interaction: discord.Interaction):
    """Create a simple test message to debug reaction events"""
    embed = discord.Embed(
        title="🧪 Reaction Event Test",
        description="React to this message with any emoji, then remove it.\nCheck the server logs for debugging info.",
        color=0x0099FF,
    )

    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()

    # Add a simple reaction for testing
    await message.add_reaction("👍")

    # Store this test message ID temporarily for debugging
    global test_message_id
    test_message_id = message.id

    logger.info(f"DEBUG TEST: Created test message with ID {message.id}")


# Add a global variable for test message ID
test_message_id = None


@bot.tree.command(
    name="check_permissions", description="Check bot permissions in this channel"
)
async def check_permissions(interaction: discord.Interaction):
    """Check if the bot has all required permissions"""
    missing_perms = check_bot_permissions(interaction.channel)

    if not missing_perms:
        await interaction.response.send_message(
            "✅ Bot has all required permissions!", ephemeral=True
        )
    else:
        perm_list = "\n".join(
            [f"• {perm.replace('_', ' ').title()}" for perm in missing_perms]
        )
        await interaction.response.send_message(
            f"❌ Bot is missing the following permissions:\n{perm_list}\n\n"
            f"Please ask a server administrator to grant these permissions to the bot.",
            ephemeral=True,
        )


@bot.tree.command(name="botc_help", description="List all available BOTC bot commands")
async def botc_help(interaction: discord.Interaction):
    """Help command that lists all available commands"""
    embed = discord.Embed(
        title="🎲 Blood on the Clocktower Bot Commands",
        description="Here are all the available commands for the BOTC bot:",
        color=0x8B0000,
    )

    commands_info = [
        {
            "name": "/setup_game",
            "description": "Set up the weekly BOTC game signup message with reaction emojis",
            "permissions": "Requires 'Manage Events' permission",
        },
        {
            "name": "/reset_signups",
            "description": "Reset current signups but keep the message and event",
            "permissions": "Requires 'Manage Events' permission",
        },
        {
            "name": "/reset_game",
            "description": "Reset the game completely for a new week",
            "permissions": "Requires 'Manage Events' permission",
        },
        {
            "name": "/game_status",
            "description": "Check the current game status and signups",
            "permissions": "Available to everyone",
        },
        {
            "name": "/check_permissions",
            "description": "Check if the bot has all required permissions in this channel",
            "permissions": "Available to everyone",
        },
        {
            "name": "/ping",
            "description": "Check if the bot is responsive and view latency",
            "permissions": "Available to everyone",
        },
        {
            "name": "/time_debug",
            "description": "Debug timezone and time settings",
            "permissions": "Available to everyone",
        },
        {
            "name": "/botc_help",
            "description": "Show this help message",
            "permissions": "Available to everyone",
        },
    ]

    for cmd in commands_info:
        embed.add_field(
            name=cmd["name"],
            value=f"{cmd['description']}\n*{cmd['permissions']}*",
            inline=False,
        )

    embed.add_field(
        name="📝 How to Use Reactions",
        value=f"""React to the signup message with:
• {MAIN_PLAYER_EMOJI} or {'/'.join(MAIN_GUEST_EMOJIS)} for main players
• {TRAVELER_EMOJI} or {'/'.join(TRAVELER_GUEST_EMOJIS)} for travelers
• {HANGOUT_EMOJI} to hang out and watch the game

You can react to multiple emojis to bring mixed groups!""",
        inline=False,
    )

    embed.set_footer(text="🎲 Happy gaming! 🎲")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.event
async def on_ready():
    logger.info(f"BOT READY: {bot.user} has connected to Discord!")
    logger.info(f"BOT INFO: Connected to {len(bot.guilds)} guild(s)")

    # Log intents for debugging
    logger.info(
        f"BOT INTENTS: reactions={bot.intents.reactions}, message_content={bot.intents.message_content}"
    )

    load_game_data()
    logger.info("GAME DATA: Loaded successfully")

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"COMMANDS: Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"COMMANDS: Failed to sync - {e}")

    # Start health check task now that bot is ready
    bot.loop.create_task(health_check())
    logger.info("HEALTH CHECK: Task started")


@bot.event
async def on_reaction_add(reaction, user):
    """Handle reaction additions for signup"""
    if not user.bot:
        logger.info(
            f"REACTION ADD: {user.display_name} added {reaction.emoji} to message {reaction.message.id}"
        )

        # Special logging for test message
        if (
            hasattr(globals(), "test_message_id")
            and reaction.message.id == test_message_id
        ):
            logger.info(f"TEST MESSAGE: Reaction add detected on test message")

    if user.bot:
        return

    if reaction.message.id != game_data.get("message_id"):
        return

    # Check permissions at the start
    missing_perms = check_bot_permissions(reaction.message.channel)
    if "manage_messages" in missing_perms:
        logger.warning(f"PERMISSION WARNING: Bot lacks 'Manage Messages' permission")
        await user.send(
            "⚠️ **Bot Permission Issue**: The bot doesn't have 'Manage Messages' permission, "
            "so it can't remove your old reactions. Please ask a server admin to grant this permission."
        )

    user_id = user.id
    emoji = str(reaction.emoji)

    # Find or create player entry
    player_index = find_player(user_id)
    if player_index == -1:
        game_data["players"].append(
            {"user_id": user_id, "main_count": 0, "traveler_count": 0, "hangout": False}
        )
        player_index = len(game_data["players"]) - 1

    player = game_data["players"][player_index]

    # Handle hangout emoji
    if emoji == HANGOUT_EMOJI:
        player["hangout"] = True
        save_game_data()
    # Handle main player emojis
    elif emoji in ALL_MAIN_EMOJIS:
        new_main_count = get_guest_count_from_emoji(emoji, "main")
        current_main_total = get_total_main_count()
        current_player_main = player.get("main_count", 0)

        # Calculate if this change would exceed limits
        new_total = current_main_total - current_player_main + new_main_count

        if new_total <= MAX_MAIN_PLAYERS:
            # Remove all other main player reactions from this user
            other_emojis = [e for e in ALL_MAIN_EMOJIS if e != emoji]
            removal_success = await remove_user_reactions_from_group(
                reaction.message, user, other_emojis
            )

            player["main_count"] = new_main_count
            save_game_data()
        else:
            # Remove the reaction and send message
            await safe_remove_reaction(reaction.message, emoji, user)
            available_spots = MAX_MAIN_PLAYERS - (
                current_main_total - current_player_main
            )
            await user.send(
                f"🚫 **Not enough main player spots!** "
                f"You requested {new_main_count} main player spot{'s' if new_main_count != 1 else ''} but only {available_spots} remain. "
                f"Try a smaller group or add travelers instead!"
            )
            return

    # Handle traveler emojis
    elif emoji in ALL_TRAVELER_EMOJIS:
        new_traveler_count = get_guest_count_from_emoji(emoji, "traveler")
        current_traveler_total = get_total_traveler_count()
        current_player_traveler = player.get("traveler_count", 0)

        # Calculate if this change would exceed limits
        new_total = (
            current_traveler_total - current_player_traveler + new_traveler_count
        )

        if new_total <= MAX_TRAVELERS:
            # Remove all other traveler reactions from this user
            other_emojis = [e for e in ALL_TRAVELER_EMOJIS if e != emoji]
            removal_success = await remove_user_reactions_from_group(
                reaction.message, user, other_emojis
            )

            player["traveler_count"] = new_traveler_count
            save_game_data()
        else:
            # Remove the reaction and send message
            await safe_remove_reaction(reaction.message, emoji, user)
            available_spots = MAX_TRAVELERS - (
                current_traveler_total - current_player_traveler
            )
            await user.send(
                f"🚫 **Not enough traveler spots!** "
                f"You requested {new_traveler_count} traveler spot{'s' if new_traveler_count != 1 else ''} but only {available_spots} remain. "
                f"Try a smaller group or add main players instead!"
            )
            return

    # Clean up empty players (keep if they have any activity)
    game_data["players"] = [
        p
        for p in game_data["players"]
        if p.get("main_count", 0) > 0
        or p.get("traveler_count", 0) > 0
        or p.get("hangout", False)
    ]

    # Update the embed
    embed = create_signup_embed()
    await reaction.message.edit(embed=embed)

    # Update Discord event if it exists
    if game_data.get("event_id"):
        await update_discord_event(reaction.message.guild)


@bot.event
async def on_raw_reaction_remove(payload):
    """Handle raw reaction removals for signups"""
    logger.info(
        f"RAW REACTION REMOVE: User {payload.user_id} removed {payload.emoji} from message {payload.message_id}"
    )

    # Skip if no user_id (shouldn't happen, but just in case)
    if not payload.user_id:
        logger.info("SKIPPING: No user_id in payload")
        return

    # Get the user object - use fetch_user to get from API if not in cache
    try:
        user = bot.get_user(payload.user_id)
        if not user:
            logger.info(f"User not in cache, fetching from API: {payload.user_id}")
            user = await bot.fetch_user(payload.user_id)
    except Exception as e:
        logger.error(f"ERROR: Could not fetch user with ID {payload.user_id}: {e}")
        return

    if user.bot:
        logger.info(f"SKIPPING: User is a bot")
        return

    if payload.message_id != game_data.get("message_id"):
        logger.info(
            f"SKIPPING: Wrong message ID. Got {payload.message_id}, expected {game_data.get('message_id')}"
        )
        return

    logger.info(f"PROCESSING: Valid reaction removal from {user.display_name}")

    user_id = user.id
    emoji = str(payload.emoji)

    # Find player
    player_index = find_player(user_id)
    if player_index == -1:
        logger.error(f"ERROR: Player {user.display_name} not found in game data")
        return

    player = game_data["players"][player_index]
    logger.info(
        f"FOUND PLAYER: {user.display_name} - main: {player.get('main_count', 0)}, traveler: {player.get('traveler_count', 0)}, hangout: {player.get('hangout', False)}"
    )

    # Get the message to check remaining reactions
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        logger.error(f"ERROR: Could not find channel {payload.channel_id}")
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception as e:
        logger.error(f"ERROR: Could not fetch message {payload.message_id}: {e}")
        return

    # Handle hangout emoji removal
    if emoji == HANGOUT_EMOJI:
        logger.info(
            f"HANGOUT REMOVAL: Setting hangout to False for {user.display_name}"
        )
        player["hangout"] = False

    # Handle main player emoji removal
    elif emoji in ALL_MAIN_EMOJIS:
        logger.info(f"MAIN PLAYER REMOVAL: Processing {emoji} for {user.display_name}")

        # Find what main player reaction the user currently has (if any)
        current_main_emoji = None
        logger.info("CHECKING remaining main reactions...")
        for reaction_check in message.reactions:
            emoji_str = str(reaction_check.emoji)
            if emoji_str in ALL_MAIN_EMOJIS:
                async for reaction_user in reaction_check.users():
                    if reaction_user.id == user_id:
                        current_main_emoji = emoji_str
                        logger.info(
                            f"FOUND remaining main reaction: {current_main_emoji}"
                        )
                        break
                if current_main_emoji:
                    break

        # Update count based on current remaining reaction
        old_count = player["main_count"]
        if current_main_emoji:
            new_count = get_guest_count_from_emoji(current_main_emoji, "main")
            player["main_count"] = new_count
            logger.info(
                f"UPDATED main_count: {old_count} -> {new_count} (based on {current_main_emoji})"
            )
        else:
            player["main_count"] = 0
            logger.info(
                f"CLEARED main_count: {old_count} -> 0 (no remaining reactions)"
            )

    # Handle traveler emoji removal
    elif emoji in ALL_TRAVELER_EMOJIS:
        logger.info(f"TRAVELER REMOVAL: Processing {emoji} for {user.display_name}")

        # Find what traveler reaction the user currently has (if any)
        current_traveler_emoji = None
        for reaction_check in message.reactions:
            emoji_str = str(reaction_check.emoji)
            if emoji_str in ALL_TRAVELER_EMOJIS:
                async for reaction_user in reaction_check.users():
                    if reaction_user.id == user_id:
                        current_traveler_emoji = emoji_str
                        logger.info(
                            f"FOUND remaining traveler reaction: {current_traveler_emoji}"
                        )
                        break
                if current_traveler_emoji:
                    break

        # Update count based on current remaining reaction
        old_count = player["traveler_count"]
        if current_traveler_emoji:
            new_count = get_guest_count_from_emoji(current_traveler_emoji, "traveler")
            player["traveler_count"] = new_count
            logger.info(f"UPDATED traveler_count: {old_count} -> {new_count}")
        else:
            player["traveler_count"] = 0
            logger.info(f"CLEARED traveler_count: {old_count} -> 0")

    # Clean up empty players
    players_before = len(game_data["players"])
    game_data["players"] = [
        p
        for p in game_data["players"]
        if p.get("main_count", 0) > 0
        or p.get("traveler_count", 0) > 0
        or p.get("hangout", False)
    ]
    players_after = len(game_data["players"])

    if players_before != players_after:
        logger.info(f"CLEANUP: Removed {players_before - players_after} empty players")

    save_game_data()
    logger.info(f"SAVED: Game data updated")

    try:
        # Update the embed
        embed = create_signup_embed()
        await message.edit(embed=embed)
        logger.info(f"SUCCESS: Message embed updated")

        # Update Discord event if it exists
        if game_data.get("event_id"):
            guild = bot.get_guild(payload.guild_id)
            if guild:
                await update_discord_event(guild)
                logger.info(f"SUCCESS: Discord event updated")

    except Exception as e:
        logger.error(f"ERROR updating message/event: {e}")
        import traceback

        logger.error(traceback.format_exc())


# Also add a raw test for the debug command
@bot.event
async def on_raw_reaction_add(payload):
    """Handle raw reaction additions - for debugging"""
    if (
        payload.user_id
        and hasattr(globals(), "test_message_id")
        and payload.message_id == test_message_id
    ):
        user = bot.get_user(payload.user_id)
        if user and not user.bot:
            logger.info(
                f"RAW TEST MESSAGE: Reaction add detected on test message from {user.display_name}"
            )


async def create_discord_event(guild):
    """Create a Discord scheduled event for the game"""
    try:
        next_game = get_next_thursday()

        # Make sure we're working with timezone-aware datetime
        if next_game.tzinfo is None:
            tz = pytz.timezone(TIMEZONE)
            next_game = tz.localize(next_game)

        # Create the event
        event = await guild.create_scheduled_event(
            name="Blood on the Clocktower - Weekly Game Night",
            description="Weekly Blood on the Clocktower game! React to the signup message to join.",
            start_time=next_game,
            end_time=next_game + timedelta(hours=3),  # Assuming 3-hour games
            location="Voice Channel",
            privacy_level=discord.PrivacyLevel.guild_only,
            entity_type=discord.EntityType.voice,
            reason="Weekly BOTC game night",
        )

        game_data["event_id"] = event.id
        save_game_data()

        return event
    except Exception as e:
        print(f"Error creating Discord event: {e}")
        return None


async def update_discord_event(guild):
    """Update the Discord event with current attendees"""
    try:
        if not game_data.get("event_id"):
            return

        event = guild.get_scheduled_event(game_data["event_id"])
        if not event:
            return

        # Update event description with current signups
        total_main = get_total_main_count()
        total_travelers = get_total_traveler_count()
        total_hangout = len(get_hangout_players())

        description = "Weekly Blood on the Clocktower game!\n\n"
        description += f"Main Players: {total_main}/{MAX_MAIN_PLAYERS}\n"
        description += f"Travelers: {total_travelers}/{MAX_TRAVELERS}\n"
        description += f"Hanging Out: {total_hangout}\n\n"
        description += "React to the signup message to join!"

        await event.edit(description=description)

    except Exception as e:
        print(f"Error updating Discord event: {e}")


@bot.tree.command(name="test_logging", description="Test if logging is working")
async def test_logging(interaction: discord.Interaction):
    """Test command to verify logging works"""
    logger.info(f"TEST COMMAND: Called by {interaction.user.display_name}")
    logger.warning("TEST WARNING: This is a warning message")
    logger.error("TEST ERROR: This is an error message")

    await interaction.response.send_message(
        "Logging test completed! Check the server logs.", ephemeral=True
    )


@bot.tree.command(name="debug_players", description="Debug current player data")
async def debug_players(interaction: discord.Interaction):
    """Debug command to see current player data"""

    debug_info = "**Current Game Data:**\n"
    debug_info += f"Total players in data: {len(game_data['players'])}\n"
    debug_info += f"Message ID: {game_data.get('message_id')}\n"
    debug_info += f"Channel ID: {game_data.get('channel_id')}\n\n"

    debug_info += "**Player Details:**\n"
    for i, player in enumerate(game_data["players"]):
        user = bot.get_user(player["user_id"])
        username = user.display_name if user else f"Unknown ({player['user_id']})"
        debug_info += f"{i+1}. {username}:\n"
        debug_info += f"   - Main count: {player.get('main_count', 0)}\n"
        debug_info += f"   - Traveler count: {player.get('traveler_count', 0)}\n"
        debug_info += f"   - Hangout: {player.get('hangout', False)}\n"

    if not game_data["players"]:
        debug_info += "No players currently signed up.\n"

    debug_info += f"\n**Totals:**\n"
    debug_info += f"Main players: {get_total_main_count()}/{MAX_MAIN_PLAYERS}\n"
    debug_info += f"Travelers: {get_total_traveler_count()}/{MAX_TRAVELERS}\n"
    debug_info += f"Hanging out: {len(get_hangout_players())}\n"

    await interaction.response.send_message(debug_info, ephemeral=True)


@bot.tree.command(name="setup_game", description="Set up the weekly BOTC game signup")
async def setup_game(interaction: discord.Interaction):
    """Slash command to set up the weekly game"""
    # Check if user has manage events permission
    if not interaction.user.guild_permissions.manage_events:
        await interaction.response.send_message(
            "You need 'Manage Events' permission to set up the game!", ephemeral=True
        )
        return

    # Create the signup embed
    embed = create_signup_embed()

    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()

    # Add all reactions (main emoji + guest emojis for both groups + hangout)
    await message.add_reaction(MAIN_PLAYER_EMOJI)
    for emoji in MAIN_GUEST_EMOJIS:
        await message.add_reaction(emoji)

    await message.add_reaction(TRAVELER_EMOJI)
    for emoji in TRAVELER_GUEST_EMOJIS:
        await message.add_reaction(emoji)

    await message.add_reaction(HANGOUT_EMOJI)

    # Store message info
    game_data["message_id"] = message.id
    game_data["channel_id"] = interaction.channel.id
    game_data["week_of"] = get_next_thursday().strftime("%Y-%m-%d")

    # Create Discord event
    event = await create_discord_event(interaction.guild)

    save_game_data()

    # Send confirmation
    await interaction.followup.send(
        f"✅ Game setup complete! "
        f"{'Event created successfully!' if event else 'Note: Could not create Discord event.'}",
        ephemeral=True,
    )


@bot.tree.command(
    name="reset_signups",
    description="Reset current signups but keep the message and event",
)
async def reset_signups(interaction: discord.Interaction):
    """Slash command to reset only the player signups"""
    # Check permissions
    if not interaction.user.guild_permissions.manage_events:
        await interaction.response.send_message(
            "You need 'Manage Events' permission to reset signups!", ephemeral=True
        )
        return

    # Check if there's an active game setup
    if not game_data.get("message_id"):
        await interaction.response.send_message(
            "❌ No active game found! Use `/setup_game` to create a new signup first.",
            ephemeral=True,
        )
        return

    # Clear only the player data, keep message and event info
    game_data["players"] = []
    save_game_data()

    # Try to update the existing message with reset embed
    try:
        channel = bot.get_channel(game_data["channel_id"])
        if channel:
            message = await channel.fetch_message(game_data["message_id"])
            embed = create_signup_embed()
            await message.edit(embed=embed)

            # Update Discord event if it exists
            if game_data.get("event_id"):
                await update_discord_event(interaction.guild)

            await interaction.response.send_message(
                "✅ All signups have been cleared! The signup message has been updated.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "⚠️ Signups cleared but couldn't find the original message to update.",
                ephemeral=True,
            )
    except Exception as e:
        print(f"Error updating message after reset: {e}")
        await interaction.response.send_message(
            "✅ Signups cleared but there was an error updating the message.",
            ephemeral=True,
        )


@bot.tree.command(name="reset_game", description="Reset the game for a new week")
async def reset_game(interaction: discord.Interaction):
    """Slash command to reset the game for a new week"""
    # Check permissions
    if not interaction.user.guild_permissions.manage_events:
        await interaction.response.send_message(
            "You need 'Manage Events' permission to reset the game!", ephemeral=True
        )
        return

    # Clear game data
    game_data["players"] = []
    game_data["message_id"] = None
    game_data["channel_id"] = None
    game_data["event_id"] = None
    game_data["week_of"] = None

    save_game_data()

    await interaction.response.send_message(
        "✅ Game data has been reset! Use `/setup_game` to create a new signup.",
        ephemeral=True,
    )


@bot.tree.command(name="game_status", description="Check the current game status")
async def game_status(interaction: discord.Interaction):
    """Slash command to check game status"""
    try:
        embed = create_signup_embed()

        # Check if we can respond to the interaction
        if interaction.response.is_done():
            # If already responded, use followup
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # Normal response
            await interaction.response.send_message(embed=embed, ephemeral=True)

    except discord.NotFound:
        # Interaction expired or not found
        print(
            f"Interaction expired for game_status command from user {interaction.user}"
        )
        try:
            # Try to send a followup message
            await interaction.followup.send(
                "⚠️ The interaction expired. Please try the command again.",
                ephemeral=True,
            )
        except:
            # If followup also fails, just log it
            print("Failed to send followup message for expired interaction")
    except discord.HTTPException as e:
        print(f"HTTP exception in game_status: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ There was an error processing your request. Please try again.",
                    ephemeral=True,
                )
        except:
            pass
    except Exception as e:
        print(f"Unexpected error in game_status: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An unexpected error occurred. Please try again.", ephemeral=True
                )
        except:
            pass


@bot.tree.command(name="ping", description="Check if the bot is responsive")
async def ping(interaction: discord.Interaction):
    """Simple ping command to test bot responsiveness"""
    try:
        latency = round(bot.latency * 1000)

        if interaction.response.is_done():
            await interaction.followup.send(
                f"🏓 Pong! Latency: {latency}ms", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"🏓 Pong! Latency: {latency}ms", ephemeral=True
            )

    except discord.NotFound:
        print(f"Interaction expired for ping command from user {interaction.user}")
    except Exception as e:
        print(f"Error in ping command: {e}")


@bot.tree.command(name="time_debug", description="Debug timezone and time settings")
async def time_debug(interaction: discord.Interaction):
    """Debug command to check timezone settings"""
    try:
        time_info = get_current_time_info()

        embed = discord.Embed(title="🕐 Time Debug Information", color=0x0099FF)

        embed.add_field(
            name="Current Local Time", value=time_info["local_time"], inline=False
        )

        embed.add_field(
            name="Current UTC Time", value=time_info["utc_time"], inline=False
        )

        embed.add_field(
            name="Configured Timezone", value=time_info["timezone"], inline=False
        )

        embed.add_field(
            name="Next Game Time", value=time_info["next_game"], inline=False
        )

        next_game = get_next_thursday()
        embed.add_field(
            name="Discord Timestamp",
            value=f"<t:{int(next_game.timestamp())}:F>",
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(
            f"Error getting time info: {e}", ephemeral=True
        )


# Health check function (for monitoring)
async def health_check():
    """Simple health check that runs periodically"""
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            if bot.is_ready():
                print(f"Bot health check: OK - Connected to {len(bot.guilds)} guilds")
            else:
                print("Bot health check: NOT READY")
        except Exception as e:
            print(f"Health check error: {e}")


# Run the bot
if __name__ == "__main__":
    # Load environment variables from .env file if it exists (for local development)
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass  # dotenv not installed, which is fine for production

    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set!")
        print("Please set it in your Render dashboard or .env file")
        sys.exit(1)

    try:
        print("Starting Discord bot...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot crashed: {e}")
        save_game_data()
        sys.exit(1)
