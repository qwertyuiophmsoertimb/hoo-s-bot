import discord
from discord.ext import commands
import json
import os
from datetime import datetime, timezone

# Import configuration and data manager
from config import CONFIG
from data_manager import load_user_data, user_data # Import user_data to access bot_donations

# Define custom prefixes
custom_prefixes = ["owl ", "Owl ", "mumei ", "Mumei "]

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.reactions = True
intents.members = True # Required for fetching members in on_raw_reaction_add

# Initialize the bot
bot = commands.Bot(command_prefix=custom_prefixes, intents=intents, case_insensitive=True)

# Global temporary storage for channels (can be moved to a cog if preferred)
bot.temporary_text_channels = {}

@bot.event
async def on_ready():
    """Event handler for when the bot successfully connects to Discord."""
    print(f'Logged in as {bot.user.name}')
    
    # Load user data at startup
    load_user_data()

    # Set bot's presence
    bot_balance = user_data.get(str(bot.user.id), {"coins": 0}).get("coins", 0)
    await bot.change_presence(activity=discord.Game(name=f"{bot_balance} 根羽毛"))

    # Load cogs
    try:
        await bot.load_extension('cogs.rpg')
        print("Loaded RPG cog.")
    except Exception as e:
        print(f"Failed to load RPG cog: {e}")

    try:
        await bot.load_extension('cogs.minigames')
        print("Loaded Minigames cog.")
    except Exception as e:
        print(f"Failed to load Minigames cog: {e}")

    print("Bot is ready!")

@bot.event
async def on_disconnect():
    """Event handler for when the bot disconnects from Discord."""
    print('Bot disconnected.')
    # Cogs' cog_unload methods will handle stopping their tasks.

# Run the bot with the token from config.json
if __name__ == "__main__":
    bot_token = CONFIG.get("bot_token")
    if bot_token and bot_token != "YOUR_BOT_TOKEN_HERE":
        bot.run(bot_token)
    else:
        print("ERROR: Bot token not found or is default. Please set your bot token in config.json.")

