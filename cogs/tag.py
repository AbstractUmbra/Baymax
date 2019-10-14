""" Cog - Tag. """
from os import path
from json import load

import discord
from discord.ext import commands

from utils.checks import check_bound_text

PATH = path.join(path.dirname(__file__))
TAG_PATH = path.join(PATH, "../config/tags.json")
if path.exists(TAG_PATH):
    with open(TAG_PATH) as tag_file:
        TAG = load(tag_file)


class Tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @check_bound_text()
    @commands.command()
    async def tag(self, ctx, tag_name: str, channel: discord.VoiceChannel = None):
        """ Play a tag... hopefully!. """
        if channel is None:
            channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()

        if TAG.get(f"{tag_name}") is None:
            return await ctx.send(f"Unable to locate tag: {tag_name}.")
        tag_path = path.join(PATH, f"../content/tags/{tag_name}.mp3")
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(tag_path))
        ctx.voice_client.play(source, after=lambda e: print(
            "Player error: %s" % e) if e else None)

        await ctx.send(f"Playing {tag_name} tag.", delete_after=5)

    @check_bound_text()
    @commands.command()
    async def dc(self, ctx):
        """ Disconnect voice. """
        await ctx.voice_client.disconnect()


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Tag(bot))
