import logging
import json
import os
import sys
import random
from math import ceil
from asyncio import sleep

import discord
from discord.ext import commands
from discord.ext.commands import Bot
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
        "bot_token": "1234567890",
        "admins": [],
        "bound_text_channels": [],
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

    bot = Bot(command_prefix=bot_prefix)

    @bot.event
    async def on_command_error(error, ctx):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, "on_error"):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await bot.send_message(
                ctx.message.channel,
                "error: Command '{0.clean_context}' requires additional arguments.".format(
                    ctx.message)
            )
        elif isinstance(error, commands.CommandNotFound):
            await bot.send_message(
                ctx.message.channel,
                "error: Command '{0.clean_context}' is not found.".format(
                    ctx.message),
            )
        elif isinstance(error, NeedAdmin):
            await bot.send_message(
                ctx.message.channel,
                "error: Command '{0.clean_context}' requires admin privileges, loser.".format(
                    ctx.message),
            )
        else:
            await bot.send_message(
                ctx.message.channel, "Error caught. Type: {}".format(
                    str(error))
            )

    @bot.event
    async def on_ready():
        await bot.change_presence(
            game=discord.Game(name="Welcome to the Dark Side.")
        )
        print("Logged in as: {}".format(bot.user.name))

    @bot.group(pass_context=True)
    async def admin(ctx):
        if ctx.message.author.id not in admin_list:
            raise NeedAdmin("You are not an administrator of the bot.")
        if ctx.invoked.subcommand is None:
            await bot.say("Invalid usage of command: use {}admin to prefix command.".format(bot_prefix))

    @admin.command(pass_context=True)
    async def add(ctx, arg):
        print("add(ctx, arg)")

        if arg is None:
            await bot.say("Invalid usage; use {}admin add <@user>.".format(bot_prefix))
        elif check_id_format(arg):
            new_admin_id = strip_dc_id(arg)

            if new_admin_id in admin_list:
                await bot.say("User {} is already an admin.".format(arg))
            else:
                admin_list.append(new_admin_id)
                save_settings(CONFIG_PATH)
                await bot.say("{} has been added to admin list.".format(arg))
        else:
            await bot.say("Invalid usage; use {}admin add <@user>".format(bot_prefix))

    @admin.command(pass_context=True)
    async def remove(ctx, arg):
        print("remove(ctx, arg)")
        if arg is None:
            await bot.say("Missing argument use {}admin remove <@user>'".format(bot_prefix))
        elif check_id_format(arg):
            remove_admin_id = strip_dc_id(arg)

            if remove_admin_id not in admin_list:
                await bot.say("Admin not found in admin list.")
            else:
                admin_list.remove(remove_admin_id)
                save_settings(CONFIG_PATH)
                await bot.say("{} was removed from admin list.".format(arg))
        else:
            await bot.say("Invalid usage, use {}admin remove <@user>".format(bot_prefix))

    @admin.command(pass_context=True)
    async def adminlist(ctx):
        for admin in admin_list:
            await bot.say(dc_int_id(admin))

    @admin.command(pass_context=True)
    async def scattertheweak(ctx):
        voice_channels = []
        for server in bot.servers:
            for channel in server.channels:
                if not isinstance(channel.type, int):
                    if channel.type.value == 2:
                        voice_channels.append(channel)
            static_member_list = copy_local_voice_users(ctx)

            for member in static_member_list:
                await bot.say("You are weak, {}".format(dc_int_id(member.id)))
                await bot.move_member(member, random.choice(voice_channels))

    @admin.command(pass_context=True)
    async def whatadick(ctx):
        if "dick" not in SETTINGS:
            SETTINGS["dick"] = 194176688668540929
            dick_user = SETTINGS["dick"]
            save_settings(CONFIG_PATH)
        else:
            dick_user = SETTINGS["dick"]
        await bot.say("Honestly, you're a bit of a dick {}".format(dc_int_id(dick_user)))
        await bot.ban(dick_user)

    @admin.command(pass_context=True)
    async def SNAP(ctx):
        current_voice_list = copy_local_voice_users(ctx)
        half_of_current_voice_list = ceil(len(current_voice_list) / 2)
        snapped_users = random.sample(
            current_voice_list, half_of_current_voice_list)
        snapped_channel = discord.utils.get(
            ctx.message.server.channels, name="The Soul Stone"
        )

        await bot.say("You should have gone for the head.")
        await bot.say("**SNAP!**")
        for member in snapped_users:
            await bot.move_member(member, snapped_channel)

    async def list_servers():
        await bot.wait_until_ready()
        while not bot.is_closed:
            print("Current servers:")
            for server in bot.servers:
                print(server.name)
            await sleep(200)

    bot.loop.create_task(list_servers())
    bot.run(bot_token)


if __name__ == "__main__":
    main()
