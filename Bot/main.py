""" A simple and fun discord bot. """
import logging
from time import sleep
import json
import os
import sys
import random
import traceback
from math import ceil
import itertools

import discord
from discord.ext import commands
import discord.utils

# Set logging
logging.basicConfig(level=logging.INFO)

# Constants
CONFIG_PATH = "config/settings.json"
SETTINGS = {}


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
        "bot_token": 1234567890,
        "admins": [],
        "bound_text_channels": [],
        "bot_description": "A generic use bot for fun, games and memes.",
    }

    with open(CONFIG_PATH, "w+"):
        json.dump(SETTINGS, CONFIG_PATH)


class NeedAdmin(Exception):
    """ Exception for the requirement of admin privs. """


class UnpermittedChannel(Exception):
    """ Exception for an unpermitted text channel. """


def main():
    """ Run the bot woooooo """
    if "bot_token" not in SETTINGS:
        SETTINGS["bot_token"] = input("Please input your bot token here: ")
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

    if "dick" not in SETTINGS:
        # defaults to a dickhead tbh
        SETTINGS["dick"] = 194176688668540929
        save_settings(CONFIG_PATH)

    bot = commands.Bot(
        command_prefix=SETTINGS["bot_prefix"], description=SETTINGS["bot_description"]
    )

    def all_voice_members_guild(ctx):
        guild_vms = list(itertools.chain.from_iterable(
            [member for member in [ch.members for ch in ctx.guild.voice_channels]]))
        return guild_vms

    @bot.event
    async def on_command_error(ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, "on_error"):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.author.send(
                f"error: Command '{ctx.message}' requires additional arguments."
            )
        elif isinstance(error, commands.CommandNotFound):
            await ctx.author.send(
                f"error: Command '{ctx.message}' is not found."
            )
        elif isinstance(error, NeedAdmin):
            await ctx.author.send(
                f"error: Command '{ctx.message}' requires admin privileges, loser."
            )
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send(
                f"error: Command '{ctx.message}' This command cannot be used as it is disabled."
            )
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
                traceback.print_tb(original.__traceback__)
                print(f"{original.__class__.__name__}: {original}",
                      file=sys.stderr)
        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.send(error)
        else:
            await ctx.author.send(f"Error caught. Type: {error}.")

    @bot.event
    async def on_ready():
        await bot.change_presence(
            activity=discord.Game(name="Welcome to the Dark Side."), status=discord.Status.online
        )
        print(f"Logged in as: {bot.user.name}: {bot.user.id}")

    def check_bound_text():
        def predicate(ctx):
            if ctx.channel.id not in SETTINGS["bound_text_channels"]:
                raise UnpermittedChannel(
                    f"The bot is not bound to this text channel: {ctx.channel}")
            else:
                return True
        return commands.check(predicate)

    @bot.group()
    @check_bound_text()
    async def admin(ctx):
        if ctx.message.author.id not in SETTINGS["admins"]:
            raise NeedAdmin("You are not an administrator of the bot.")
        if ctx.invoked_subcommand is None:
            await ctx.send(
                f"Invalid usage of command: use {SETTINGS['bot_prefix']}admin to prefix command."
            )

    @admin.command()
    @check_bound_text()
    async def add(ctx, member: discord.Member):
        if member is None:
            await ctx.send(f"Invalid usage; use {SETTINGS['bot_prefix']}admin add <@user>.")
        elif member.id in SETTINGS["admins"]:
            await ctx.send(f"User {member} is already an admin.")
        else:
            SETTINGS["admins"].append(member.id)
            save_settings(CONFIG_PATH)
            await ctx.send(f"{member} has been added to admin list.")

    @admin.command()
    @check_bound_text()
    async def remove(ctx, member: discord.Member):
        if member is None:
            await ctx.send(f"Missing argument use {SETTINGS['bot_prefix']}admin remove <@user>")
        elif member.id not in SETTINGS["admins"]:
            await ctx.send("Admin not found in admin list.")
        else:
            SETTINGS["admins"].remove(member.id)
            save_settings(CONFIG_PATH)
            await ctx.send(f"{member} was removed from admin list.")

    @admin.command()
    @check_bound_text()
    async def add_channel(ctx, channel: discord.TextChannel):
        if channel is None:
            await ctx.send(
                f"Invalid usage, use {SETTINGS['bot_prefix']}admin add_channel <@text_channel>."
            )
        elif channel.id in SETTINGS["bound_text_channels"]:
            await ctx.send(f"Channel {channel} is already bot bound.")
        else:
            SETTINGS["bound_text_channels"].append(channel.id)
            save_settings(CONFIG_PATH)
            await ctx.send(f"{channel} has been added to the bound channel list.")

    @admin.command()
    @check_bound_text()
    async def adminlist(ctx):
        for admin in SETTINGS["admins"]:
            await ctx.send(ctx.guild.get_member(admin))

    @admin.command()
    @check_bound_text()
    async def scattertheweak(ctx):
        for dcmember in all_voice_members_guild(ctx):
            await ctx.send(f"You are weak, {dcmember}")
            await dcmember.move_to(
                random.choice(ctx.message.guild.voice_channels), reason="Was too weak."
            )

    @admin.command()
    @check_bound_text()
    async def addadick(ctx, member: discord.Member):
        if member is None:
            await ctx.send(f"Missing argument, use '{SETTINGS['bot_prefix']}")
        else:
            SETTINGS["dicks"].append(member.id)
            save_settings(CONFIG_PATH)

    @admin.command()
    @check_bound_text()
    async def whatadick(ctx):
        for dick in SETTINGS["dicks"]:
            current_dick_user = ctx.guild.get_member(dick)
            if current_dick_user is None:
                await ctx.send("The dick wasn't found on this server.")
            else:
                await ctx.send(f"Honestly, you're a bit of a dick {current_dick_user.mention}")
                await ctx.guild.ban(discord.Object(id=current_dick_user.id))

    @admin.command()
    @check_bound_text()
    async def SNAP(ctx):
        half_of_current_voice_list = ceil(
            len(all_voice_members_guild(ctx)) / 2)
        snapped_users = random.sample(
            all_voice_members_guild(ctx), half_of_current_voice_list)
        snapped_channel = discord.utils.get(
            ctx.message.guild.channels, name="The Soul Stone"
        )

        if os.path.exists("content/snap.gif"):
            await ctx.send(file=discord.File("content/snap.gif"))
            sleep(5)
            for member in snapped_users:
                print(f"Snapped {member.name}.")
                await member.move_to(snapped_channel, reason="was snapped.")
        else:
            for member in snapped_users:
                await ctx.send("You should have gone for the head.")
                await ctx.send("**SNAP!**")
                print(f"Snapped {member.name}.")
                await member.move_to(snapped_channel, reason="was snapped.")

    @admin.command()
    @check_bound_text()
    async def setup(ctx):
        """ Performs vanilla server set up - can be tailored. """
        setup_details = {}
        setup_file = "config/setup.json"

        # Load Settings
        if os.path.exists(setup_file):
            with open(setup_file) as read_setup_file:
                setup_details = json.load(read_setup_file)
        else:
            print(f"No settings file exists at {setup_file}. Using defaults.")
            setup_details = {
                "Superadmin": ["Superadmin", 123456789123456789],
                "Moderators": ["Moderators", 123456789123456789, 123456789123456789],
            }
            with open(setup_file, "w+"):
                json.dump(setup_details, setup_file)

        # Sanity Checks
        if "Superadmin" not in setup_details:
            # Should be RoleName and  list of user IDs to apply - generally just one user.
            setup_details["Superadmin"] = ["Superadmin", [123456789123456789]]
            save_settings(setup_file)

        if "Moderators" not in setup_details:
            # Should be RoleName and a list of user IDs to apply - multiple users preferably.
            setup_details["Moderators"] = ["Moderators", [123456789123456789]]
            save_settings(setup_file)

    bot.run(SETTINGS["bot_token"])


if __name__ == "__main__":
    main()
