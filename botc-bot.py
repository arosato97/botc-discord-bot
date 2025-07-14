import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import json
import os

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
MAIN_PLAYER_EMOJI = "⚔️"  # Sword for main players
TRAVELER_EMOJI = "🎒"  # Backpack for travelers

# Guest emojis for main players (1-5 guests)
MAIN_GUEST_EMOJIS = ["🗡️", "⚡", "🛡️", "🏹", "🔥"]  # 1-5 guests for main players
# Guest emojis for travelers (1-5 guests)
TRAVELER_GUEST_EMOJIS = ["🌟", "🎭", "🎨", "🎪", "🎯"]  # 1-5 guests for travelers

GAME_DAY = 3  # Thursday (0=Monday, 6=Sunday)
GAME_TIME = (19, 30)  # 7:30 PM

# Storage for game data
game_data = {
    "main_players": [],  # [{'user_id': int, 'guests': int}, ...]
    "travelers": [],  # [{'user_id': int, 'guests': int}, ...]
    "message_id": None,
    "channel_id": None,
    "event_id": None,
    "week_of": None,
}


def save_game_data():
    """Save game data to a JSON file"""
    try:
        with open("game_data.json", "w") as f:
            json.dump(game_data, f, indent=2)
    except Exception as e:
        print(f"Error saving game data: {e}")


def load_game_data():
    """Load game data from JSON file"""
    global game_data
    try:
        if os.path.exists("game_data.json"):
            with open("game_data.json", "r") as f:
                game_data = json.load(f)
    except Exception as e:
        print(f"Error loading game data: {e}")


def get_total_main_count():
    """Get total count of main players including guests"""
    return sum(player.get("guests", 0) + 1 for player in game_data["main_players"])


def get_total_traveler_count():
    """Get total count of travelers including guests"""
    return sum(traveler.get("guests", 0) + 1 for traveler in game_data["travelers"])


def find_player_in_group(user_id, group):
    """Find a player in a group by user_id"""
    for i, player in enumerate(group):
        if player["user_id"] == user_id:
            return i
    return -1


def get_guest_count_from_emoji(emoji, group_type):
    """Get the number of guests from emoji"""
    if group_type == "main":
        try:
            return MAIN_GUEST_EMOJIS.index(emoji) + 1
        except ValueError:
            return 0
    else:  # traveler
        try:
            return TRAVELER_GUEST_EMOJIS.index(emoji) + 1
        except ValueError:
            return 0
    """Get the next Thursday at 7:30 PM"""
    now = datetime.now()
    days_ahead = GAME_DAY - now.weekday()
    if days_ahead <= 0:  # Thursday already passed this week
        days_ahead += 7

    next_thursday = now + timedelta(days=days_ahead)
    return next_thursday.replace(
        hour=GAME_TIME[0], minute=GAME_TIME[1], second=0, microsecond=0
    )


def create_signup_embed():
    """Create the signup embed message"""
    embed = discord.Embed(
        title="🕐 Blood on the Clocktower - Weekly Game Night",
        description="React to join the game! First come, first served.",
        color=0x8B0000,
    )

    next_game = get_next_thursday()
    embed.add_field(
        name="📅 Next Game", value=f"<t:{int(next_game.timestamp())}:F>", inline=False
    )

    # Main players section
    main_players_text = ""
    total_main_count = get_total_main_count()

    for i, player in enumerate(game_data["main_players"], 1):
        guest_count = player.get("guests", 0)
        guest_text = (
            f" (+{guest_count} guest{'s' if guest_count != 1 else ''})"
            if guest_count > 0
            else ""
        )
        main_players_text += f"{i}. <@{player['user_id']}>{guest_text}\n"

    if not main_players_text:
        main_players_text = "No players signed up yet"

    embed.add_field(
        name=f"⚔️ Main Players ({total_main_count}/{MAX_MAIN_PLAYERS})",
        value=main_players_text,
        inline=True,
    )

    # Travelers section
    travelers_text = ""
    total_traveler_count = get_total_traveler_count()

    for i, traveler in enumerate(game_data["travelers"], 1):
        guest_count = traveler.get("guests", 0)
        guest_text = (
            f" (+{guest_count} guest{'s' if guest_count != 1 else ''})"
            if guest_count > 0
            else ""
        )
        travelers_text += f"{i}. <@{traveler['user_id']}>{guest_text}\n"

    if not travelers_text:
        travelers_text = "No travelers signed up yet"

    embed.add_field(
        name=f"🎒 Travelers ({total_traveler_count}/{MAX_TRAVELERS})",
        value=travelers_text,
        inline=True,
    )

    # Instructions
    instructions = f"""**Main Players:**
{MAIN_PLAYER_EMOJI} Solo player
{' '.join(f'{emoji} +{i+1}' for i, emoji in enumerate(MAIN_GUEST_EMOJIS))}

**Travelers:**
{TRAVELER_EMOJI} Solo traveler
{' '.join(f'{emoji} +{i+1}' for i, emoji in enumerate(TRAVELER_GUEST_EMOJIS))}"""

    embed.add_field(name="How to Join", value=instructions, inline=False)

    embed.set_footer(text="May the odds be in your favor! 🎲")

    return embed


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    load_game_data()

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.event
async def on_reaction_add(reaction, user):
    """Handle reaction additions for signup"""
    if user.bot:
        return

    if reaction.message.id != game_data.get("message_id"):
        return

    user_id = user.id
    emoji = str(reaction.emoji)

    # Remove user from both groups first (in case they're switching)
    main_player_index = find_player_in_group(user_id, game_data["main_players"])
    traveler_index = find_player_in_group(user_id, game_data["travelers"])

    if main_player_index >= 0:
        game_data["main_players"].pop(main_player_index)
    if traveler_index >= 0:
        game_data["travelers"].pop(traveler_index)

    # Handle main player signups
    if emoji == MAIN_PLAYER_EMOJI or emoji in MAIN_GUEST_EMOJIS:
        guests = (
            get_guest_count_from_emoji(emoji, "main")
            if emoji != MAIN_PLAYER_EMOJI
            else 0
        )
        total_new_count = (
            get_total_main_count() + guests + 1
        )  # +1 for the player themselves

        if total_new_count <= MAX_MAIN_PLAYERS:
            game_data["main_players"].append({"user_id": user_id, "guests": guests})
            save_game_data()
        else:
            # Remove the reaction and send message
            await reaction.remove(user)
            available_spots = MAX_MAIN_PLAYERS - get_total_main_count()
            if available_spots > 0:
                await user.send(
                    f"🚫 **Not enough main player spots!** "
                    f"You requested {guests + 1} spot{'s' if guests + 1 != 1 else ''} but only {available_spots} remain. "
                    f"Try a smaller group or react with {TRAVELER_EMOJI} to join as travelers!"
                )
            else:
                await user.send(
                    "🚫 **Main players are full!** "
                    f"Try reacting with {TRAVELER_EMOJI} to join as travelers, "
                    "or come watch the mayhem unfold! 🍿"
                )
            return

    # Handle traveler signups
    elif emoji == TRAVELER_EMOJI or emoji in TRAVELER_GUEST_EMOJIS:
        guests = (
            get_guest_count_from_emoji(emoji, "traveler")
            if emoji != TRAVELER_EMOJI
            else 0
        )
        total_new_count = (
            get_total_traveler_count() + guests + 1
        )  # +1 for the player themselves

        if total_new_count <= MAX_TRAVELERS:
            game_data["travelers"].append({"user_id": user_id, "guests": guests})
            save_game_data()
        else:
            # Remove the reaction and send message
            await reaction.remove(user)
            available_spots = MAX_TRAVELERS - get_total_traveler_count()
            if available_spots > 0:
                await user.send(
                    f"🚫 **Not enough traveler spots!** "
                    f"You requested {guests + 1} spot{'s' if guests + 1 != 1 else ''} but only {available_spots} remain. "
                    f"Try a smaller group or react with {MAIN_PLAYER_EMOJI} to join as main players!"
                )
            else:
                await user.send(
                    "🚫 **Travelers are full!** "
                    f"Try reacting with {MAIN_PLAYER_EMOJI} to join as main players, "
                    "or come watch the mayhem unfold! 🍿"
                )
            return

    # Update the embed
    embed = create_signup_embed()
    await reaction.message.edit(embed=embed)

    # Update Discord event if it exists
    if game_data.get("event_id"):
        await update_discord_event(reaction.message.guild)


@bot.event
async def on_reaction_remove(reaction, user):
    """Handle reaction removals for signups"""
    if user.bot:
        return

    if reaction.message.id != game_data.get("message_id"):
        return

    user_id = user.id
    emoji = str(reaction.emoji)

    # Remove user from appropriate group
    if emoji == MAIN_PLAYER_EMOJI or emoji in MAIN_GUEST_EMOJIS:
        main_player_index = find_player_in_group(user_id, game_data["main_players"])
        if main_player_index >= 0:
            game_data["main_players"].pop(main_player_index)
    elif emoji == TRAVELER_EMOJI or emoji in TRAVELER_GUEST_EMOJIS:
        traveler_index = find_player_in_group(user_id, game_data["travelers"])
        if traveler_index >= 0:
            game_data["travelers"].pop(traveler_index)

    save_game_data()

    # Update the embed
    embed = create_signup_embed()
    await reaction.message.edit(embed=embed)

    # Update Discord event if it exists
    if game_data.get("event_id"):
        await update_discord_event(reaction.message.guild)


async def create_discord_event(guild):
    """Create a Discord scheduled event for the game"""
    try:
        next_game = get_next_thursday()

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

        description = "Weekly Blood on the Clocktower game!\n\n"
        description += f"Main Players: {total_main}/{MAX_MAIN_PLAYERS}\n"
        description += f"Travelers: {total_travelers}/{MAX_TRAVELERS}\n\n"
        description += "React to the signup message to join!"

        await event.edit(description=description)

    except Exception as e:
        print(f"Error updating Discord event: {e}")


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

    # Add all reactions (main emoji + guest emojis for both groups)
    await message.add_reaction(MAIN_PLAYER_EMOJI)
    for emoji in MAIN_GUEST_EMOJIS:
        await message.add_reaction(emoji)

    await message.add_reaction(TRAVELER_EMOJI)
    for emoji in TRAVELER_GUEST_EMOJIS:
        await message.add_reaction(emoji)

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
    game_data["main_players"] = []
    game_data["travelers"] = []
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
    embed = create_signup_embed()
    await interaction.response.send_message(embed=embed, ephemeral=True)


# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set!")
        exit(1)

    bot.run(TOKEN)
