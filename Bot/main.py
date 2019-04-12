""" A simple and fun discord bot. """
import logging
from time import sleep
import json
import os
import sys
import random
import traceback
from math import ceil
import asyncio

import discord
from discord.ext import commands
import discord.utils
import youtube_dl

# Set logging
logging.basicConfig(level=logging.INFO)

# Supress youtube dl errors for usage
youtube_dl.utils.bug_reports_message = lambda: ''

YTDL_FORMAT_OPTIONS = {
    'format': "bestaudio/best",
    'outtmpl': "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'options': '-vn'
}

# Constants
CONFIG_PATH = "config/bot.json"
YTDL = youtube_dl.YoutubeDL(YTDL_FORMAT_OPTIONS)


def save_settings(config):
    """ Save settings in a passed config file. """
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
        "bot_description": "A generic use bot for fun, games and memes.",
    }

    with open(CONFIG_PATH, "w+"):
        json.dump(SETTINGS, CONFIG_PATH)


class NeedAdmin(Exception):
    """ Exception for the requirement of admin privs. """


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.3):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: YTDL.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else YTDL.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """ Joins a voice channel. """
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect

    @commands.command()
    async def play(self, ctx, *, query):
        """ Plays a file from local FS. """
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print(
            "Player error: %s" % e) if e else None)
        await ctx.send("Now playing: {}".format(query))

    @commands.command()
    async def yt(self, ctx, *, url):
        """ Plays from a URL, that YTDL supports. """
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print(
                "Player rror: %s" % e) if e else None)
        await ctx.send("Now playing: {}".format(player.title))

    @commands.command()
    async def stream(self, ctx, *, url):
        """ Streams from a url (same as yt but doesn't download). """
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(
                "Player error: %s" % e) if e else None)
        await ctx.send("Now playing: {}".format(player.title))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """ Changes the player's volume. """
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")
        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changes volume to {}%".format(volume))

    @commands.command()
    async def stop(self, ctx):
        """ Stops the current voice channel and client. """
        if ctx.voice_client is None:
            return await ctx.send("Not actually playing anything...")
        else:
            await ctx.voice_client.disconnect()

    @play.before_invoke
    @yt.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError(
                    "Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


def main():
    """ Run the bot woooooo """
    if "bot_token" not in SETTINGS:
        bot_token = input("Please input your bot token here: ")
        SETTINGS["bot_token"] = bot_token
        save_settings(CONFIG_PATH)
    else:
        bot_token = SETTINGS["bot_token"]

    if "admins" not in SETTINGS:
        # defaults to Revan#1793
        SETTINGS["admins"] = [155863164544614402]
        save_settings(CONFIG_PATH)

    if "bound_text_channels" not in SETTINGS:
        # defaults to "main-chat-woooo" in "No Swimming Server"
        SETTINGS["bound_text_channels"] = [565093633468923906]
        try:
            bound_text_channels = SETTINGS["bound_text_channels"]
        except KeyError as kerr:
            print("Error located: {}. No key for 'bound_text_channels'.".format(kerr))
        save_settings(CONFIG_PATH)
    else:
        bound_text_channels = SETTINGS["bound_text_channels"]
    print("Currently bound to these text channels: {}".format(bound_text_channels))

    if "bot_prefix" not in SETTINGS:
        # defaults to "^"
        SETTINGS["bot_prefix"] = ("^")
        try:
            bot_prefix = SETTINGS["bot_prefix"]
        except KeyError as kerr:
            print("Error located: {}. No key found for 'bot_prefix'.".format(kerr))
        save_settings(CONFIG_PATH)
    else:
        bot_prefix = SETTINGS["bot_prefix"]
    print("Current bot prefix is: {}".format(bot_prefix))

    if "bot_description" not in SETTINGS:
        # defaults to "blah Blah"
        SETTINGS["bot_description"] = "Blah Blah"
        try:
            bot_description = SETTINGS["bot_description"]
        except KeyError as kerr:
            print("Error located: {}. No key found for 'bot_description'.".format(kerr))
        save_settings(CONFIG_PATH)
    else:
        bot_description = SETTINGS["bot_description"]

        if "dick" not in SETTINGS:
            # defaults to a dickhead tbh
            SETTINGS["dick"] = 194176688668540929
            save_settings(CONFIG_PATH)

    bot = commands.Bot(command_prefix=bot_prefix, description=bot_description)

 ################ ALL BELOW HERE IS WRONG ####################

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
                "error: Command '{}' requires additional arguments.".format(
                    ctx.message)
            )
        elif isinstance(error, commands.CommandNotFound):
            await ctx.author.send(
                "error: Command '{}' is not found.".format(
                    ctx.message),
            )
        elif isinstance(error, NeedAdmin):
            await ctx.author.send(
                "error: Command '{}' requires admin privileges, loser.".format(
                    ctx.message),
            )
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send(
                "error: Command '{}' This command cannot be used as it is disabled.".format(
                    ctx.message),
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
            await ctx.author.send(
                "Error caught. Type: {}".format(
                    str(error))
            )

    @bot.event
    async def on_ready():
        await bot.change_presence(
            activity=discord.Game(name="Welcome to the Dark Side."), status=discord.Status.online
        )
        print("Logged in as: {}: {}".format(bot.user.name, bot.user.id))

    @bot.group()
    async def admin(ctx):
        if ctx.message.author.id not in SETTINGS["admins"]:
            raise NeedAdmin("You are not an administrator of the bot.")
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid usage of command: use {}admin to prefix command."
                           .format(bot_prefix))

    @admin.command()
    async def add(ctx, member: discord.Member):
        if member is None:
            await ctx.send("Invalid usage; use {}admin add <@user>.".format(bot_prefix))
        elif member.id in SETTINGS["admins"]:
            await ctx.send("User {} is already an admin.".format(member))
        else:
            SETTINGS["admins"].append(member.id)
            save_settings(CONFIG_PATH)
            await ctx.send("{} has been added to admin list.".format(member))

    @admin.command()
    async def remove(ctx, member: discord.Member):
        if member is None:
            await ctx.send("Missing argument use {}admin remove <@user>'".format(bot_prefix))
        elif member.id not in SETTINGS["admins"]:
            await ctx.send("Admin not found in admin list.")
        else:
            SETTINGS["admins"].remove(member.id)
            save_settings(CONFIG_PATH)
            await ctx.send("{} was removed from admin list.".format(member))

    @admin.command()
    async def adminlist(ctx):
        for admin in SETTINGS["admins"]:
            await ctx.send(ctx.guild.get_member(admin))

    @admin.command()
    async def scattertheweak(ctx):
        voice_channels = []
        for guild in bot.guilds:
            voice_channels.extend(guild.voice_channels)
            for channel in voice_channels:
                print("Voice Channel: {}".format(channel))
                for dcmember in channel.members:
                    print("\t Member of channel: {}".format(dcmember))
                    await ctx.send("You are weak, {}".format(dcmember))
                    await dcmember.move_to(random.choice(voice_channels), reason="Was too weak.")

    @admin.command()
    async def whatadick(ctx):
        current_dick_user = ctx.guild.get_member(SETTINGS["dick"])
        if current_dick_user is None:
            await ctx.send("The dick wasn't found on this server.")
        else:
            await ctx.send("Honestly, you're a bit of a dick {}".format(current_dick_user.mention))
            await ctx.guild.ban(discord.Object(id=int(SETTINGS["dick"])))

    @admin.command()
    async def SNAP(ctx):
        current_voice_list = ctx.message.author.voice.channel.members.copy()
        half_of_current_voice_list = ceil(len(current_voice_list) / 2)
        snapped_users = random.sample(
            current_voice_list, half_of_current_voice_list)
        snapped_channel = discord.utils.get(
            ctx.message.guild.channels, name="The Soul Stone"
        )

        if os.path.exists("content/snap.gif"):
            snapimg = discord.File("content/snap.gif")
            await ctx.send(file=snapimg)
            sleep(5)
            for member in snapped_users:
                print("Snapped {}".format(member.name))
                await member.move_to(snapped_channel, reason="was snapped.")
        else:
            for member in snapped_users:
                await ctx.send("You should have gone for the head.")
                await ctx.send("**SNAP!**")
                print("Snapped {}".format(member.name))
                await member.move_to(snapped_channel, reason="was snapped.")

    bot.add_cog(Music(bot))
    bot.run(bot_token)


if __name__ == "__main__":
    main()
