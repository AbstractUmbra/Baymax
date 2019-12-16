""" A simple and fun discord bot. """
import logging
import sys
import traceback

import discord
from discord.ext import commands
import discord.utils

from utils.settings import SETTINGS, load_settings

# Set logging
logging.basicConfig(level=logging.INFO)

# Constants
CONFIG_PATH = "config/settings.json"
SETTINGS = load_settings()
INVITE_LINK = "https://discordapp.com/api/oauth2/authorize?client_id=^ID^&permissions=0&scope=bot"


BOT = commands.Bot(
    command_prefix=SETTINGS["bot_prefix"], description=SETTINGS["bot_description"]
)


@BOT.event
async def on_command_completion(ctx):
    """ When a command successfully completes. """
    await ctx.message.delete(delay=5)


@BOT.event
async def on_command_error(ctx, error):
    """The event triggered when an error is raised while invoking a command.
    ctx   : Context
    error : Exception"""
    # This prevents any commands with local handlers being handled here in on_command_error.
    if hasattr(ctx.command, "on_error"):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"error: Command '{ctx.message.content}' requires additional arguments.",
            delete_after=5
        )
        await ctx.message.delete(delay=5)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(
            f"error: Command '{ctx.message.content}' is not found.",
            delete_after=5
        )
        await ctx.message.delete(delay=5)
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send(
            f"error: Command '{ctx.message.content}' "
            "This command cannot be used as it is disabled.",
            delete_after=5
        )
        await ctx.message.delete(delay=5)
    elif isinstance(error, commands.CommandInvokeError):
        original = error.original
        if not isinstance(original, discord.HTTPException):
            print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
            traceback.print_tb(original.__traceback__)
            print(f"{original.__class__.__name__}: {original}",
                  file=sys.stderr)
    elif isinstance(error, commands.ArgumentParsingError):
        await ctx.send(error)
        await ctx.message.delete(delay=5)
    else:
        await ctx.send(f"Error caught. Type: {error}.", delete_after=10)


@BOT.event
async def on_ready():
    """ When Discord bot is ready. """
    await BOT.change_presence(
        activity=discord.Game(
            name=f"{SETTINGS['bot_prefix']}help for help, fuckers.",
            status=discord.Status.online))
    print(f"Logged in as {BOT.user.name}: {BOT.user.id}")
    new_link = INVITE_LINK.replace("^ID^", str(SETTINGS['bot_id']))
    print(
        f"Use this URL to invite the bot to your server: {new_link}")


@BOT.command()
async def ping(ctx):
    """ Alive checker. """
    await ctx.send("Pong!")

# Load these two, make the others extra.
BOT.load_extension("cogs.admin")
BOT.load_extension("cogs.cleanup")
BOT.load_extension("cogs.automod")
BOT.load_extension("cogs.autoroles")
BOT.load_extension("cogs.rust")

BOT.run(SETTINGS["bot_token"])
