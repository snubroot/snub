import discord
from discord.ext import commands
import asyncio
import os
import sys
import aiohttp

import config

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(
    command_prefix=config.PREFIX,
    intents=intents,
    case_insensitive=True,
    owner_ids=set(config.OWNER_IDS)
)

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print(f'Connected to {len(bot.guilds)} guilds')
    
    activity_type = {
        'playing': discord.ActivityType.playing,
        'watching': discord.ActivityType.watching,
        'listening': discord.ActivityType.listening
    }.get(config.ACTIVITY_TYPE.lower(), discord.ActivityType.listening)
    
    activity = discord.Activity(
        type=activity_type,
        name=config.ACTIVITY_NAME
    )
    
    await bot.change_presence(activity=activity)
    print("Bot is ready!")

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler for events"""
    print(f"Error in event {event}", file=sys.stderr)
    print(sys.exc_info(), file=sys.stderr)
    
    # The error_logger cog will handle detailed logging to Discord

async def load_extensions():
    """Load all extensions from the cogs directory"""
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('_'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded extension: {filename[:-3]}')
            except Exception as e:
                print(f'Failed to load extension {filename[:-3]}: {e}')

async def main():
    bot.session = aiohttp.ClientSession()
    
    try:
        async with bot:
            await load_extensions()
            await bot.start(config.TOKEN)
    except KeyboardInterrupt:
        print("Received keyboard interrupt. Shutting down...")
    except discord.LoginFailure:
        print("Invalid token. Please check your .env file.")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        if hasattr(bot, 'session'):
            await bot.session.close()
            print("Closed aiohttp session.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shut down by user.")
