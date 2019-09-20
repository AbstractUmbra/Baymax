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
import urllib.parse

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


class NeedAdmin(Exception):
    """ Exception for the requirement of admin privs. """


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
            await ctx.send(
                f"error: Command '{ctx.message}' requires additional arguments."
            )
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send(
                f"error: Command '{ctx.message}' is not found."
            )
        elif isinstance(error, NeedAdmin):
            await ctx.send(
                f"error: Command '{ctx.message}' requires admin privileges, loser."
            )
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send(
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
            await ctx.send(f"Error caught. Type: {error}.")

    @bot.event
    async def on_member_join(member):
        await member.edit(roles=[624726664731164682], reason="Server welcome.")

    @bot.event
    async def on_ready():
        await bot.change_presence(
            activity=discord.Game(name="Welcome to the Dark Side."), status=discord.Status.online
        )
        print(f"Logged in as: {bot.user.name}: {bot.user.id}")
        new_link = INVITE_LINK.replace("^ID^", str(SETTINGS['bot_id']))
        print(
            f"Use this URL to invite the bot to your server: {new_link}")

    def check_bound_text():
        def permitted_text(ctx):
            if ctx.channel.id not in SETTINGS["bound_text_channels"]:
                raise UnpermittedChannel(
                    f"The bot is not bound to this text channel: {ctx.channel}")
            else:
                return True
        return commands.check(permitted_text)

    @bot.group()
    @check_bound_text()
    async def admin(ctx):
        if ctx.message.author.id not in SETTINGS["admins"]:
            await ctx.send(f"You are not an administrator of the bot, {ctx.message.author.mention}")
            raise NeedAdmin("Non-admin tried to execute...")
        if ctx.invoked_subcommand is None:
            await ctx.send(
                f"Invalid usage of command: use {SETTINGS['bot_prefix']}admin to prefix command."
            )

    @bot.command()
    @check_bound_text()
    async def adminlist(ctx):
        for admin in SETTINGS["admins"]:
            await ctx.send(ctx.guild.get_member(admin))

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
    async def add_bound_channel(ctx, channel: discord.TextChannel):
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
    async def scattertheweak(ctx):
        for dcmember in all_voice_members_guild(ctx):
            await ctx.send(f"You are weak, {dcmember}")
            await dcmember.move_to(
                random.choice(ctx.message.guild.voice_channels), reason="Was too weak."
            )

    @admin.command()
    @check_bound_text()
    async def summon(ctx, member: discord.Member):
        if member is None:
            await ctx.send(
                f"Missing argument, use `{SETTINGS['bot_prefix']}admin summonfucker <@user>`."
            )
        elif member.voice.channel is ctx.message.author.voice.channel:
            await ctx.send(f"They're already in your voice chat, you wank.")
        else:
            await member.move_to(ctx.message.author.voice.channel)

    @admin.command()
    @check_bound_text()
    async def snap(ctx):
        half_of_current_voice_list = ceil(
            len(all_voice_members_guild(ctx)) / 2
        )
        snapped_users = random.sample(
            all_voice_members_guild(ctx), half_of_current_voice_list
        )
        snapped_channel = discord.utils.get(
            ctx.message.guild.channels, name="The Soul Stone"
        )
        if os.path.exists("content/snap.gif"):
            await ctx.send(file=discord.File("content/snap.gif"))
            sleep(8)
            for member in snapped_users:
                print(f"Snapped {member.name}.")
                await member.move_to(snapped_channel, reason="was snapped.")
        else:
            for member in snapped_users:
                await ctx.send("You should have gone for the head.")
                await ctx.send("**SNAP!**")
                print(f"Snapped {member.name}.")
                await member.move_to(snapped_channel, reason="was snapped.")

    @bot.command()
    @check_bound_text()
    async def dumbass(ctx):
        """ Generates a LMGTFY link of the passed text. """
        msg_body = ctx.message.system_content.replace("^dumbass ", "")

        def url_encode(query):
            """ Encodes URL formatting for query. """
            encoded_query = urllib.parse.quote(str(query), safe='')
            return encoded_query

        base_url = "http://lmgtfy.com/?q=^QUERY^"
        lmgtfy_url = base_url.replace(
            "^QUERY^", url_encode(str(msg_body)))
        await ctx.send(lmgtfy_url)

    @admin.command()
    @check_bound_text()
    async def perms(ctx, member: discord.Member):
        """ Print the bot perms to the console. """
        user_roles = {role: boolean for role,
                      boolean in member.guild_permissions}
        role_embed = discord.Embed(title=f"User roles for {member}",
                                   description="",
                                   colour=0x00ff00)
        role_embed.add_field(
            name="Roles", value=f"{user_roles}", inline=True)
        await ctx.send(embed=role_embed)

    @bot.command()
    @check_bound_text()
    async def votes(ctx, channel: discord.TextChannel):
        """ Count the reactions in the channel to get a 'vote list'. """
        count = {}
        total = discord.Embed(title="**Vote Count**",
                              description="Votey lads",
                              color=0x00ff00)
        total.set_author(name=bot.user.name)
        total.set_thumbnail(url=bot.user.avatar_url)
        async for msg in channel.history(limit=200):
            if msg.author.id != bot.user.id:
                for reaction in msg.reactions:
                    count[msg.content] = reaction.count
                total.add_field(
                    name=f"{msg.content}",
                    value=f"Votes: {count.get(msg.content)}",
                    inline=True)
        total.add_field(name="**Highest voted**",
                        value=f"**{max(count, key=count.get)}**", inline=False)
        await channel.send(embed=total)

    bot.run(SETTINGS["bot_token"])


if __name__ == "__main__":
    main()
