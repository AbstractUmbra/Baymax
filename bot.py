""" A simple and fun discord bot. """
import logging
import json
import os
import sys
import traceback
import itertools

import discord
from discord.ext import commands
import discord.utils

# Set logging
logging.basicConfig(level=logging.INFO)

# Constants
CONFIG_PATH = "config/settings.json"
SETTINGS = {}
INVITE_LINK = "https://discordapp.com/api/oauth2/authorize?client_id=^ID^&permissions=0&scope=bot"


def save_settings(config):
    """ Save settings in a passed config file. """
    with open(config, "w") as write_config_file:
        json.dump(SETTINGS, write_config_file, indent=4)


# Load Settings
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH) as read_config_file:
        SETTINGS = json.load(read_config_file)
else:
    print(f"No settings file exists at {CONFIG_PATH}. Using defaults.")
    SETTINGS = {
        "bot_id": 1234567890,
        "bot_token": 1234567890,
        "admins": [],
        "bound_text_channels": [],
        "bot_description": "A generic use bot for fun, games and memes.",
    }

    with open(CONFIG_PATH, "w+"):
        json.dump(SETTINGS, CONFIG_PATH)


def check_bound_text():
    """ Checks the channel executing from is in the whitelist. """
    def permitted_text(ctx):
        if ctx.channel.id not in SETTINGS["bound_text_channels"]:
            raise UnpermittedChannel(
                f"The bot is not bound to this text channel: {ctx.channel}")
        else:
            return True
    return commands.check(permitted_text)

def all_voice_members_guild(ctx):
    """ Gets all the members currently in a voice channel. """
    guild_vms = list(itertools.chain.from_iterable(
        [member for member in [ch.members for ch in ctx.guild.voice_channels]]))
    return guild_vms


def admin_check():
    """ Checks the executing user is in the Admin list. """
    def predicate(ctx):
        if ctx.message.author.id not in SETTINGS["admins"]:
            return False
        return True
    return commands.check(predicate)

class UnpermittedChannel(Exception):
    """ Exception for an unpermitted text channel. """


def main():
    """ Run the bot woooooo """
    if "bot_token" not in SETTINGS:
        SETTINGS["bot_token"] = input("Please input your bot token here: ")
        save_settings(CONFIG_PATH)

    if "bot_id" not in SETTINGS:
        SETTINGS["bot_token"] = 1234567890
        save_settings(CONFIG_PATH)

    if "admins" not in SETTINGS:
        # defaults to random int
        SETTINGS["admins"] = [123456789123456789, 123456789123456789]
        save_settings(CONFIG_PATH)
    print(f"Current list of admins are: {SETTINGS['admins']}")

    if "bound_text_channels" not in SETTINGS:
        # defaults to random ints - can be more than one.
        SETTINGS["bound_text_channels"] = [
            123456789123456789, 123456789123456789
        ]
        save_settings(CONFIG_PATH)
    print(
        f"Currently bound to these text channels: {SETTINGS['bound_text_channels']}"
    )

    if "bot_prefix" not in SETTINGS:
        # defaults to "^"
        SETTINGS["bot_prefix"] = ("^")
        save_settings(CONFIG_PATH)
    print(f"Current bot prefix is: {SETTINGS['bot_prefix']}")

    if "bot_description" not in SETTINGS:
        # defaults to "blah Blah"
        SETTINGS["bot_description"] = "Blah Blah"
        save_settings(CONFIG_PATH)

    bot = commands.Bot(
        command_prefix=SETTINGS["bot_prefix"], description=SETTINGS["bot_description"]
    )

    @bot.event
    async def on_command_completion(ctx):
        await ctx.message.delete(delay=5)

    @bot.event
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
            await ctx.send(f"Error caught. Type: {error}.")

    @bot.event
    async def on_member_join(member):
        new_user_role = discord.utils.get(
            member.guild.roles, id=174703372631277569
        )
        await member.add_roles(new_user_role, reason="Server welcome.", atomic=True)

    @bot.event
    async def on_ready():
        await bot.change_presence(
            activity=discord.Game(name="Welcome to the Dark Side."), status=discord.Status.online
        )
        print(f"Logged in as: {bot.user.name}: {bot.user.id}")
        new_link = INVITE_LINK.replace("^ID^", str(SETTINGS['bot_id']))
        print(
            f"Use this URL to invite the bot to your server: {new_link}")

    @bot.command()
    async def ping(ctx):
        await ctx.send("Pong!")


    @bot.command()
    @check_bound_text()
    async def perms(ctx, member: discord.Member = None):
        """ Print the passed user perms to the console. """
        if member is None:
            member = ctx.author
        user_roles = '\n'.join(
            perm for perm, value in member.guild_permissions if value)
        role_embed = discord.Embed(title=f"User roles for {member}",
                                   description=f"Server: {ctx.guild.name}",
                                   colour=member.colour)
        role_embed.set_author(icon_url=member.avatar_url, name=str(member))
        role_embed.add_field(
            name="\uFEFF", value=user_roles, inline=True)
        await ctx.author.send(embed=role_embed)

    # Load these two, make the others extra.
    bot.load_extension("cogs.admin")
    bot.load_extension("cogs.cleanup")

    bot.run(SETTINGS["bot_token"])


if __name__ == "__main__":
    main()
