import logging
import json
import os
import sys
import random
from math import ceil

import discord
from discord.ext import commands
import discord.utils

# Set logging
logging.basicConfig(level=logging.INFO)

# Constants
CONFIG_PATH = "config/bot.json"

# Settings section
# Save Settings


def save_settings(config):
    with open(config, "w") as write_config_file:
        json.dump(SETTINGS, write_config_file, indent=4)


# Load Settings
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH) as read_config_file:
        SETTINGS = json.load(read_config_file)
else:
    print("No settings file exists at {}. Using defaults.".format(CONFIG_PATH))
    SETTINGS = {
        "bot_token": 1234567890,
        "admins": [],
        "bound_text_channels": [],
        "server_id": 1324567890,
    }

    with open(CONFIG_PATH, "w+"):
        json.dump(SETTINGS, CONFIG_PATH)


class NeedAdmin(Exception):
    pass


# Helpful functions - ID based.
# Get Discord ID based on int - grabbed by adding \ before @'ing a member.
def dc_int_id(dcid):
    return "<@!" + dcid + ">"


def strip_dc_id(dcid):
    return dcid[3:1]


def check_id_format(idstr):
    return idstr[:3] == "<@!" and idstr[-1:] == ">"


# Grab voice users in authors voice channel:
def copy_local_voice_users(ctx):
    return ctx.message.author.voice.voice_channel.voice_members.copy()


def main():
    if "bot_token" in SETTINGS:
        if SETTINGS["bot_token"] != 1234567890:
            bot_token = SETTINGS["bot_token"]
        else:
            bot_token = input("Please input your bot token here: ")
            SETTINGS["bot_token"] = bot_token
            save_settings(CONFIG_PATH)
    else:
        sys.exit("'bot_token' not found in bot config: {}".format(CONFIG_PATH))

    if "admins" not in SETTINGS:
        # defaults to Revan#1793
        SETTINGS["admins"] = [155863164544614402]
        admin_list = SETTINGS["admins"]
        save_settings(CONFIG_PATH)
    else:
        admin_list = SETTINGS["admins"]

    if "bound_text_channels" not in SETTINGS:
        # defaults to "main-chat-woooo" in "No Swimming Server"
        SETTINGS["bound_text_channels"] = [565093633468923906]
        bound_text_channels = SETTINGS["bound_text_channels"]
        save_settings(CONFIG_PATH)
    else:
        bound_text_channels = SETTINGS["bound_text_channels"]
    print("Currently  bound to these text channels: {}".format(bound_text_channels))

    if "bot_prefix" not in SETTINGS:
        # defaults to "^"
        SETTINGS["bot_prefix"] = ("^")
        bot_prefix = SETTINGS["bot_prefix"]
        save_settings(CONFIG_PATH)
    else:
        bot_prefix = SETTINGS["bot_prefix"]
    print("Currently bot prefix is: {}".format(bot_prefix))

    if "server_id" not in SETTINGS:
        # defaults to 1234567890
        SETTINGS["server_id"] = 1234567890
        save_settings(CONFIG_PATH)
    else:
        server_id = SETTINGS["server_id"]

    client = discord.Client(command_prefix=bot_prefix)

 ################ ALL BELOW HERE IS WRONG ####################

    @client.event
    async def on_command_error(ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, "on_error"):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.message.channel.send(
                "error: Command '{0.clean_context}' requires additional arguments.".format(
                    ctx.message)
            )
        elif isinstance(error, commands.CommandNotFound):
            await ctx.message.channel.send(
                "error: Command '{0.clean_context}' is not found.".format(
                    ctx.message),
            )
        elif isinstance(error, NeedAdmin):
            await ctx.message.channel.send(
                "error: Command '{0.clean_context}' requires admin privileges, loser.".format(
                    ctx.message),
            )
        else:
            await ctx.message.channel.send(
                "Error caught. Type: {}".format(
                    str(error))
            )

    @client.event
    async def on_ready(ctx):
        await client.change_presence(
            activity=discord.Game(name="Welcome to the Dark Side."), status=discord.Status.idle
        )
        print("Logged in as: {}".format(client.user.name))

        main_guild = discord.Client.fetch_guild(ctx, server_id)
        print(main_guild.name)

    @client.group()
    async def admin(ctx):
        if ctx.message.author.id not in admin_list:
            raise NeedAdmin("You are not an administrator of the bot.")
        if ctx.invoked.subcommand is None:
            await ctx.send("Invalid usage of command: use {}admin to prefix command.".format(bot_prefix))

    @admin.command()
    async def add(ctx, arg):
        print("add(ctx, arg)")

        if arg is None:
            await ctx.send("Invalid usage; use {}admin add <@user>.".format(bot_prefix))
        elif check_id_format(arg):
            new_admin_id = strip_dc_id(arg)

            if new_admin_id in admin_list:
                await ctx.send("User {} is already an admin.".format(arg))
            else:
                admin_list.append(new_admin_id)
                save_settings(CONFIG_PATH)
                await ctx.send("{} has been added to admin list.".format(arg))
        else:
            await ctx.send("Invalid usage; use {}admin add <@user>".format(bot_prefix))

    @admin.command()
    async def remove(ctx, arg):
        print("remove(ctx, arg)")
        if arg is None:
            await ctx.send("Missing argument use {}admin remove <@user>'".format(bot_prefix))
        elif check_id_format(arg):
            remove_admin_id = strip_dc_id(arg)

            if remove_admin_id not in admin_list:
                await ctx.send("Admin not found in admin list.")
            else:
                admin_list.remove(remove_admin_id)
                save_settings(CONFIG_PATH)
                await ctx.send("{} was removed from admin list.".format(arg))
        else:
            await ctx.send("Invalid usage, use {}admin remove <@user>".format(bot_prefix))

    @admin.command()
    async def adminlist(ctx):
        for admin in admin_list:
            await ctx.send(dc_int_id(admin))

    @admin.command()
    async def scattertheweak(ctx):
        for member in copy_local_voice_users(ctx):
            await ctx.send("You are weak, {}".format(dc_int_id(member.id)))
            await member.move_to(random.choice(discord.Guild.voice_channels), reason="Was too weak.")

    @admin.command()
    async def whatadick(ctx):
        if "dick" not in SETTINGS:
            SETTINGS["dick"] = 194176688668540929
            dick_user = SETTINGS["dick"]
            save_settings(CONFIG_PATH)
        else:
            dick_user = SETTINGS["dick"]
        await ctx.send("Honestly, you're a bit of a dick {}".format(dc_int_id(dick_user)))
        await dick_user.ban()

    @admin.command()
    async def SNAP(ctx):
        current_voice_list = copy_local_voice_users(ctx)
        half_of_current_voice_list = ceil(len(current_voice_list) / 2)
        snapped_users = random.sample(
            current_voice_list, half_of_current_voice_list)
        snapped_channel = discord.utils.get(
            ctx.message.server.channels, name="The Soul Stone"
        )

        await ctx.send("You should have gone for the head.")
        await ctx.send("**SNAP!**")
        for member in snapped_users:
            await member.move_to(snapped_channel, reason="was snapped.")

    client.run(bot_token)


if __name__ == "__main__":
    main()
