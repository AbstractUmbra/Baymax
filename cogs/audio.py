""" Cog - Audio. """
from os import path
from json import load
import asyncio

import discord
from discord.ext import commands

import youtube_dl

from utils.checks import check_bound_text

# -----
# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    # bind to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'options': '-vn'
}

YTDL = youtube_dl.YoutubeDL(YTDL_OPTIONS)


class YTDLSource(discord.PCMVolumeTransformer):
    """ YTDL Configure wooo. """

    def __init__(self, source, *, data, volume=0.5):
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
# ------


PATH = path.join(path.dirname(__file__))
TAG_PATH = path.join(PATH, "../config/tags.json")
if path.exists(TAG_PATH):
    with open(TAG_PATH) as tag_file:
        TAG = load(tag_file)


class Audio(commands.Cog):
    """ Audio cog. """

    def __init__(self, bot):
        self.bot = bot

    @check_bound_text()
    @commands.command()
    async def join(self, ctx):
        """ Join voice. """
        channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    @check_bound_text()
    @commands.command()
    async def dc(self, ctx):
        """ Disconnect voice. """
        await ctx.voice_client.disconnect()

    @check_bound_text()
    @commands.command()
    async def volume(self, ctx, volume: int):
        """ Set's the player volume. """
        if ctx.voice_client is None:
            return await ctx.send("I am not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%.", delete_after=3)

    @commands.command()
    async def tag(self, ctx, tag_name: str = None):
        """ Play a tag... hopefully!. """
        if tag_name is None or tag_name is "list":
            tag_embed = discord.Embed(title="**Tag List**",
                                      color=0x00ff00)
            tag_embed.set_author(name=self.bot.user.name)
            tag_embed.set_thumbnail(url=self.bot.user.avatar_url)
            tag_list = "\n".join(tag for tag in TAG.keys())
            tag_embed.add_field(name="**Current Tags**",
                                value=f"{tag_list}", inline=True)
            return await ctx.channel.send(embed=tag_embed, delete_after=15)
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
    async def youtube(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print(
                "Player error: %s" % e) if e else None)

        await ctx.send(f"Now playing: {player.title}")

    @tag.before_invoke
    @youtube.before_invoke
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


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Audio(bot))
