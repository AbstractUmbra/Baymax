""" A simple and fun discord bot. """
import logging
from time import sleep
import json
import os
import sys
from random import choice, sample
import traceback
from math import ceil
import itertools
import urllib.parse
from heapq import nlargest
from unidecode import unidecode

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


    @admin_check()
    @check_bound_text()
    async def scattertheweak(ctx):
        for dcmember in all_voice_members_guild(ctx):
            await ctx.send(f"You are weak, {dcmember}")
            await dcmember.move_to(
                choice(ctx.message.guild.voice_channels), reason="Was too weak."
            )

    @admin_check()
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

    @admin_check()
    @check_bound_text()
    async def snap(ctx):
        half_of_current_voice_list = ceil(
            len(all_voice_members_guild(ctx)) / 2
        )
        snapped_users = sample(
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

    @admin_check()
    @check_bound_text()
    async def spelling(ctx):
        vowels = "aeiouAEIOU"
        # Blacklist server admin.
        for member in ctx.guild.members:
            if member is ctx.guild.owner:
                continue
            original_name = member.display_name
            await ctx.send(f"Jumbling {member.display_name}'s name..", delete_after=10)
            # time to jumble...
            new_name = ""
            # Remove CFS Tag
            if "[𝓒𝓕𝓢] " in original_name:
                original_name = original_name.replace("[𝓒𝓕𝓢] ", "")
            # Take away non-utf8 cahracters.
            original_name = unidecode(original_name).replace(
                "[", "").replace("]", "")
            for char in f"{original_name}":
                if char in vowels:
                    new_name += choice(list(vowels))
                else:
                    new_name += char
            await member.edit(nick=new_name.capitalize(), reason="Cannot spell.")

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

    @bot.command()
    async def votes(ctx, channel: discord.TextChannel = None):
        """ Count the reactions in the channel to get a 'vote list'. """
        if channel is None:
            channel = ctx.channel
        count = {}
        total = discord.Embed(title="**Vote Count**",
                              color=0x00ff00)
        total.set_author(name=bot.user.name)
        total.set_thumbnail(url=bot.user.avatar_url)
        async for msg in channel.history(limit=50):
            if msg.author.id != bot.user.id and not msg.content.startswith("^"):
                if msg.reactions is None:
                    count[msg.content] = 0
                    continue
                for reaction in msg.reactions:
                    count[msg.content] = reaction.count
                total.add_field(
                    name=f"{msg.content}",
                    value=f"Votes: {count.get(msg.content)}",
                    inline=True)
        count_list = nlargest(5, count, key=count.get)
        count_string = "\n".join(item for item in count_list)
        total.add_field(name="**Highest voted**",
                        value=f"**{count_string}**", inline=False)
        to_pin = await channel.send(embed=total)
        await to_pin.pin()

    # Load these two, make the others extra.
    bot.load_extension("cogs.admin")
    bot.load_extension("cogs.cleanup")

    bot.run(SETTINGS["bot_token"])


if __name__ == "__main__":
    main()
