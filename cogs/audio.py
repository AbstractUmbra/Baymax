""" Cog - Audio. """
from os import path
from json import load
import asyncio
import traceback
from sys import stderr
from functools import partial
from itertools import islice
from async_timeout import timeout

import discord
from discord.ext import commands

import youtube_dl

from utils.checks import check_bound_text
from utils.exceptions import InvalidVoiceChannel, VoiceConnectionError

# -----
# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

FFMPEG_OPTIONS = {
    'before_options': '-nostdin',
    'options': '-vn'
}

YTDL = youtube_dl.YoutubeDL(YTDL_OPTIONS)


class YTDLSource(discord.PCMVolumeTransformer):
    """ YTDL Configure wooo. """

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.url = data.get('url')

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=False):
        """ Create audio source. """
        loop = loop or asyncio.get_event_loop()

        to_run = partial(YTDL.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        await ctx.send(f'```ini\n[Added {data["title"]} to the Queue.]\n```', delete_after=15)

        if download:
            source = YTDL.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'],
                    'requester': ctx.author,
                    'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(YTDL.extract_info,
                         url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)
# ------


PATH = path.join(path.dirname(__file__))
TAG_PATH = path.join(PATH, "../config/tags.json")
if path.exists(TAG_PATH):
    with open(TAG_PATH) as tag_file:
        TAG = load(tag_file)


class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop,
        which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog',
                 'queue', 'next', 'current', 'now_playing', 'volume')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.now_playing = None  # Now playing message
        self.volume = .5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as err:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{err}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(
                source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.now_playing = await self._channel.send(
                f'**Now Playing:** `{source.title}` requested by `{source.requester}`')
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song...
                await self.now_playing.delete()
            except discord.HTTPException:
                pass

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self._cog.cleanup(guild))


class Audio(commands.Cog):
    """ Audio cog. """

    __slots__ = ('bot', 'players')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild):
        """ Cleanup audio. """
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    async def __local_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send('Error connecting to Voice Channel. '
                           'Please make sure you are in a valid channel or provide me with one')

        print('Ignoring exception in command {}:'.format(
            ctx.command), file=stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=stderr)

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    @commands.command(aliases=['connect'])
    async def join(self, ctx, *, channel: discord.VoiceChannel = None):
        """Connect to voice.
        Parameters
        ------------
        channel: discord.VoiceChannel [Optional]
            The channel to connect to. If a channel is not specified,
                an attempt to join the voice channel you are in
                    will be made.
        This command also handles moving the bot to different channels.
        """
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise InvalidVoiceChannel(
                    'No channel to join. Please either specify a valid channel or join one.')

        voice_client = ctx.voice_client

        if voice_client:
            if voice_client.channel.id == channel.id:
                return
            try:
                await voice_client.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(
                    f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(
                    f'Connecting to channel: <{channel}> timed out.')

        await ctx.send(f'Connected to: **{channel}**', delete_after=20)

    @check_bound_text()
    @commands.command()
    async def play(self, ctx, *, search: str):
        """Request a song and add it to the queue.
        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search and retrieve a song.
        Parameters
        ------------
        search: str [Required]
            The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """
        await ctx.trigger_typing()

        voice_client = ctx.voice_client

        if not voice_client:
            await ctx.invoke(self.join)

        player = self.get_player(ctx)

        # If download is False, source will be a dict which to be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=False)

        await player.queue.put(source)

    @check_bound_text()
    @commands.command()
    async def pause(self, ctx):
        """Pause the currently playing song."""
        voice_client = ctx.voice_client

        if not voice_client or not voice_client.is_playing():
            return await ctx.send('I am not currently playing anything!', delete_after=20)
        elif voice_client.is_paused():
            return

        voice_client.pause()
        await ctx.send(f'**`{ctx.author}`**: Paused the song!')

    @check_bound_text()
    @commands.command()
    async def resume(self, ctx):
        """Resume the currently paused song."""
        voice_client = ctx.voice_client

        if not voice_client or not voice_client.is_connected():
            return await ctx.send('I am not currently playing anything!', delete_after=20)
        elif not voice_client.is_paused():
            return

        voice_client.resume()
        await ctx.send(f'**`{ctx.author}`**: Resumed the song!')

    @check_bound_text()
    @commands.command()
    async def skip(self, ctx):
        """Skip the song."""
        voice_client = ctx.voice_client

        if not voice_client or not voice_client.is_connected():
            return await ctx.send('I am not currently playing anything!', delete_after=20)

        if voice_client.is_paused():
            pass
        elif not voice_client.is_playing():
            return

        voice_client.stop()
        await ctx.send(f'**`{ctx.author}`**: Skipped the song!')

    @check_bound_text()
    @commands.command(aliases=['q', 'playlist'])
    async def queue(self, ctx):
        """Retrieve a basic queue of upcoming songs."""
        voice_client = ctx.voice_client

        if not voice_client or not voice_client.is_connected():
            return await ctx.send('I am not currently connected to voice!', delete_after=20)

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send('There are currently no more queued songs.', delete_after=3)

        # Grab up to 5 entries from the queue...
        upcoming = list(islice(player.queue._queue, 0, 5))

        fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
        embed = discord.Embed(
            title=f'Upcoming - Next {len(upcoming)}', description=fmt)

        await ctx.send(embed=embed)

    @check_bound_text()
    @commands.command()
    async def currentsong(self, ctx):
        """Display information about the currently playing song."""
        voice_client = ctx.voice_client

        if not voice_client or not voice_client.is_connected():
            return await ctx.send('I am not currently connected to voice!', delete_after=20)

        player = self.get_player(ctx)
        if not player.current:
            return await ctx.send('I am not currently playing anything!', delete_after=5)

        try:
            # Remove our previous now_playing message.
            await player.now_playing.delete()
        except discord.HTTPException:
            pass

        player.now_playing = await ctx.send(
            f"** Now Playing: ** `{voice_client.source.title}`"
            " requested by `{voice_client.source.requester}`",
            delete_after=5)

    @check_bound_text()
    @commands.command(aliases=['vol'])
    async def volume(self, ctx, *, vol: float):
        """Change the player volume.
        Parameters
        ------------
        volume: float or int [Required]
            The volume to set the player to in percentage. This must be between 1 and 100.
        """
        voice_client = ctx.voice_client

        if not voice_client or not voice_client.is_connected():
            return await ctx.send('I am not currently connected to voice!', delete_after=20)

        if not 0 < vol < 101:
            return await ctx.send('Please enter a value between 1 and 100.', delete_after=5)

        player = self.get_player(ctx)

        if voice_client.source:
            voice_client.source.volume = vol / 100

        player.volume = vol / 100
        await ctx.send(f'**`{ctx.author}`**: Set the volume to **{vol}%**', delete_after=5)

    @check_bound_text()
    @commands.command()
    async def stop(self, ctx):
        """Stop the currently playing song and destroy the player.
        !Warning!
            This will destroy the player assigned to your guild
                also deleting any queued songs and settings.
        """
        voice_client = ctx.voice_client

        if not voice_client or not voice_client.is_connected():
            return await ctx.send('I am not currently playing anything!', delete_after=20)

        await self.cleanup(ctx.guild)

    @check_bound_text()
    @commands.command()
    async def tag(self, ctx, tag_name: str = None):
        """ Play a tag... hopefully!. """
        if tag_name is None or tag_name == "list":
            tag_embed = discord.Embed(title="**Tag List**",
                                      color=0x00ff00)
            tag_embed.set_author(name=self.bot.user.name)
            tag_embed.set_thumbnail(url=self.bot.user.avatar_url)
            tag_list = "\n".join(tag for tag in TAG.keys())
            tag_embed.add_field(name="**Current Tags**",
                                value=f"{tag_list}", inline=True)
            return await ctx.channel.send(embed=tag_embed, delete_after=15)
        if TAG.get(f"{tag_name}") is None:
            return await ctx.send(f"Unable to locate tag: {tag_name}", delete_after=10)

        await ctx.trigger_typing()
        voice_client = ctx.voice_client

        if not voice_client:
            await ctx.invoke(self.join)

        player = self.get_player(ctx)

        source = await YTDLSource.create_source(
            ctx, TAG.get(f"{tag_name}"), loop=self.bot.loop, download=False)

        await player.queue.put(source)

    @tag.before_invoke
    async def ensure_voice(self, ctx):
        """ Ensures a voice client exists. """
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
