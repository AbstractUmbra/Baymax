"""
The MIT License (MIT)

Copyright (c) 2020 AbstractUmbra

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import datetime
import traceback
from collections import deque
from typing import Dict, List, Optional, Union

import asyncpg
import pytz

import discord
from discord.ext import commands, tasks
from utils import cache, db


class TooManyAlerts(Exception):
    """ There are too many twitch alerts for this guild. """


class InvalidBroadcaster(Exception):
    """ Wrong streamer. """

    def __init__(self, broadcaster, message="Invalid streamer"):
        self.broadcaster = broadcaster
        super().__init__(message)


class TwitchTable(db.Table):
    """ Create the twitch database table. """
    id = db.PrimaryKeyColumn()

    guild_id = db.Column(db.Integer(big=True))
    channel_id = db.Column(db.Integer(big=True))
    streamer_name = db.Column(db.String)
    streamer_last_game = db.Column(db.String())
    streamer_last_datetime = db.Column(db.Datetime())


class TwitchClipTable(db.Table):
    """ Creates the Clip table for storing clip following data. """
    id = db.PrimaryKeyColumn()

    guild_id = db.Column(db.Integer(big=True))
    channel_id = db.Column(db.Integer(big=True))
    broadcaster_id = db.Column(db.String())
    last_25_clips = db.Column(db.Array(db.String()))


class TwitchSecretTable(db.Table):
    """ Creates the database for storing the OAuth secret. """
    id = db.PrimaryKeyColumn()

    secret = db.Column(db.String)
    edited_at = db.Column(db.Datetime)
    expires_at = db.Column(db.Datetime)


class Twitch(commands.Cog):
    """ Twitch based stuff on discord! """

    def __init__(self, bot):
        """ Classic init function. """
        self.bot = bot
        self.oauth_get_endpoint = "https://id.twitch.tv/oauth2/token"
        self.stream_endpoint = "https://api.twitch.tv/helix/streams"
        self.user_endpoint = "https://api.twitch.tv/helix/users"
        self.game_endpoint = "https://api.twitch.tv/helix/games"
        self.clip_endpoint = "https://api.twitch.tv/helix/clips"
        self.get_streamers.start()
        self.get_clips.start()
        self.streamer_limit = 5

    async def _get_streamers(self, name: str, guild_id: int) -> List[asyncpg.Record]:
        """ To get all streamers in the db. """
        query = """ SELECT * FROM twitchtable WHERE streamer_name = $1 AND guild_id = $2; """
        return await self.bot.pool.fetch(query, name, guild_id)

    async def _get_clips(self, name: str, guild_id: int) -> List[asyncpg.Record]:
        """ To get all streamers in the db. """
        query = """ SELECT * FROM twitchcliptable WHERE streamer_name = $1 AND guild_id = $2; """
        return await self.bot.pool.fetch(query, name, guild_id)

    async def _refresh_oauth(self) -> None:
        """ Let's call this whenever we get locked out. """
        async with self.bot.session.post(self.oauth_get_endpoint,
                                         params=self.bot.config.twitch_oauth_headers) as oa_resp:
            oauth_json = await oa_resp.json()

        if "error" in oauth_json:
            stats = self.bot.get_cog("Stats")
            if not stats:
                raise commands.BadArgument("Twitch API is locking you out.")
            webhook = stats.webhook
            return await webhook.send("**Can't seem to refresh OAuth on the Twitch API.**")

        auth_token = oauth_json['access_token']
        expire_secs = int(oauth_json['expires_in'])

        query = """INSERT INTO twitchsecrettable (id, secret, edited_at, expires_at)
                   VALUES (1, $1, $2, $3)
                   ON CONFLICT (id)
                   DO UPDATE SET secret = $1, edited_at = $2, expires_at = $3;"""
        now = datetime.datetime.now()
        expire_date = datetime.datetime.now() + datetime.timedelta(seconds=expire_secs)
        return await self.bot.pool.execute(query, auth_token, now, expire_date)

    @cache.cache()
    async def _gen_headers(self) -> Dict:
        """ Let's use this to create the Headers. """
        base = self.bot.config.twitch_headers
        query = "SELECT secret from twitchsecrettable WHERE id = 1;"
        new_token_resp = await self.bot.pool.fetchrow(query)
        new_token = new_token_resp['secret']
        base['Authorization'] = f"Bearer {new_token}"
        return base

    async def _get_streamer_guilds(self, guild_id: int) -> List[asyncpg.Record]:
        """ Return records for matched guild_ids. """
        query = """ SELECT * FROM twitchtable WHERE guild_id = $1; """
        return await self.bot.pool.fetch(query, guild_id)

    async def _get_streamer_data(self, broadcaster: str) -> Dict:
        """ Helper to get the streamer data based on name. """
        headers = await self._gen_headers()
        async with self.bot.session.get(self.user_endpoint,
                                        headers=headers,
                                        params={"login": broadcaster}) as resp:
            broadcaster_data = await resp.json()
        return broadcaster_data['data'][0]

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """ Let's not post streamers to dead guilds. """
        streamer_query = """ DELETE FROM twitchtable WHERE guild_id = $1; """
        clip_query = """ DELETE FROM twitchcliptable WHERE guild_id = $1; """
        await self.bot.pool.execute(streamer_query, guild.id)
        await self.bot.pool.execute(clip_query, guild.id)

    @commands.group(invoke_without_command=True)
    async def twitch(self, ctx: commands.Context) -> Optional[discord.Message]:
        """ Twitch main command. """
        if not ctx.invoked_subcommand:
            return await ctx.send("You require more arguments for this command.")

    @twitch.command(hidden=True)
    @commands.is_owner()
    async def streamdb(self, ctx: commands.Context) -> discord.Message:
        """ Debug for me. """
        query = """SELECT * FROM twitchtable; """
        oauth_query = """ SELECT edited_at, expires_at FROM twitchsecrettable;"""
        clips_query = """ SELECT * FROM twitchcliptable; """
        results = await self.bot.pool.fetch(query)
        oauth_results = await self.bot.pool.fetchrow(oauth_query)
        clip_results = await self.bot.pool.fetch(clips_query)

        embed = discord.Embed(title="Streamer details",
                              colour=discord.Colour.blurple())
        embed.description = "\n".join(
            f"{item['guild_id']} -> <#{item['channel_id']}> -> {item['streamer_name']} -> {(datetime.datetime.utcnow() - item['streamer_last_datetime']).seconds}" for item in results)

        embed.description += "\n".join(
            f"{item['guild_id']} -> <#{item['channel_id']}> -> {item['broadcaster_id']}" for item in clip_results)

        embed.add_field(name="OAuth Edited at", value=oauth_results['edited_at'].strftime(
            "%d-%m-%Y %H:%M:%S"))

        embed.add_field(name="OAuth Expires at", value=oauth_results['expires_at'].strftime(
            "%d-%m-%Y %H:%M:%S"))

        await ctx.send(embed=embed)

    @twitch.command(name="add")
    @commands.has_guild_permissions(manage_channels=True)
    async def add_streamer(self, ctx: commands.Context, name: str, channel: discord.TextChannel = None) -> Union[discord.Reaction, discord.Message]:
        """ Add a streamer to the database for polling. """
        channel = channel or ctx.channel
        results = await self._get_streamers(name, ctx.guild.id)

        if results:
            return await ctx.send("This streamer is already monitored.")

        query = """ INSERT INTO twitchtable(guild_id, channel_id, streamer_name, streamer_last_datetime) VALUES($1, $2, $3, $4); """
        await self.bot.pool.execute(query, ctx.guild.id, channel.id, name, (datetime.datetime.utcnow() - datetime.timedelta(hours=3)))
        return await ctx.message.add_reaction(self.bot.emoji[True])

    @add_streamer.before_invoke
    async def stream_notification_check(self, ctx: commands.Context) -> None:
        """ We're gonna check if they have X streams already. """
        query = "SELECT * FROM twitchtable WHERE guild_id = $1;"
        results = await self.bot.pool.fetch(query, ctx.guild.id)

        if len(results) >= self.streamer_limit:
            raise TooManyAlerts(
                "There are too many alerts for this guild already configured.")

    @twitch.command(name="remove")
    @commands.has_guild_permissions(manage_channels=True)
    async def remove_streamer(self, ctx: commands.Context, name: str) -> Union[discord.Reaction, discord.Message]:
        """ Add a streamer to the database for polling. """
        results = await self._get_streamers(name, ctx.guild.id)
        if not results:
            return await ctx.send("This streamer is not in the monitored list.")

        query = """ DELETE FROM twitchtable WHERE streamer_name = $1; """
        await self.bot.pool.execute(query, name)
        return await ctx.message.add_reaction(self.bot.emoji[True])

    @twitch.command(name="clear")
    @commands.has_guild_permissions(manage_channels=True)
    async def clear_streams(self, ctx: commands.Context, channel: discord.TextChannel = None) -> Union[discord.Reaction, discord.Message]:
        """ Clears all streams for the context channel or passed channel. """
        channel = channel or ctx.channel
        query = "DELETE FROM twitchtable WHERE channel_id = $1 AND guild_id = $2;"
        confirm = await ctx.prompt(f"This will remove all streams notifications for {channel.mention}. Are you sure?", reacquire=False)

        if confirm:
            await self.bot.pool.execute(query, channel.id, ctx.guild.id)
            return await ctx.message.add_reaction(self.bot.emoji[True])

        return await ctx.message.add_reaction(self.bot.emoji[True])

    @twitch.group(name="clips", aliases=["clip"], invoke_without_command=True)
    async def twitch_clips(self, ctx):
        """ Main clip command. """
        if not ctx.invoked_subcommand:
            return await ctx.send_help(ctx.command)

    @twitch_clips.command(name="add")
    @commands.has_guild_permissions(manage_channels=True)
    async def add_clips(self, ctx: commands.Context, *, broadcaster: str) -> discord.Reaction:
        """ Add a clip section to monitor. """
        broadcaster_data = await self._get_streamer_data(broadcaster)
        if not broadcaster_data:
            raise InvalidBroadcaster(broadcaster)

        query = """INSERT INTO twitchcliptable (guild_id, channel_id, broadcaster_id, last_25_clips)
                   VALUES ($1, $2, $3, $4)
                """

        await self.bot.pool.execute(query, ctx.guild.id, ctx.channel.id, broadcaster_data['id'], [])
        return await ctx.message.add_reaction(self.bot.emoji[True])

    @twitch_clips.command(name="remove", aliases=["delete"])
    @commands.has_guild_permissions(manage_channels=True)
    async def remove_clips(self, ctx: commands.Context, *, broadcaster: str) -> discord.Reaction:
        """ Remove clips from monitoring. """
        broadcaster_data = await self._get_streamer_data(broadcaster)

        if not broadcaster_data:
            raise InvalidBroadcaster(broadcaster)

        query = """ DELETE FROM twitchcliptable
                    WHERE guild_id = $1
                    AND channel_id = $2
                    AND broadcaster_id = $3
                """
        await self.bot.pool.execute(query, ctx.guild.id, ctx.channel.id, broadcaster_data['id'])
        return await ctx.message.add_reaction(self.bot.emoji[True])

    @twitch_clips.command(name="clear")
    @commands.has_guild_permissions(manage_channels=True)
    async def clear_clips(self, ctx: commands.Context, channel: discord.TextChannel = None) -> discord.Reaction:
        """ Clear the clips, let's check for approval though. """
        channel = channel or ctx.channel
        response = await ctx.prompt(f"Are you sure you wish to clear the clip monitoring for {channel.mention}?")

        if not response:
            return

        query = """ DELETE FROM twitchcliptable
                    WHERE guild_id = $1
                    AND channel_id = $2
                """
        await self.bot.pool.execute(query, ctx.guild.id, channel.id)
        return await ctx.message.add_reaction(self.bot.emoji[True])

    @add_clips.before_invoke
    async def clip_notification_check(self, ctx: commands.Context) -> None:
        """ We're gonna check if they have X streams already. """
        query = "SELECT * FROM twitchcliptable WHERE guild_id = $1;"
        results = await self.bot.pool.fetch(query, ctx.guild.id)
        if len(results) >= self.streamer_limit:
            raise TooManyAlerts(
                "There are too many alerts for this guild already configured.")

    @add_streamer.error
    @remove_streamer.error
    @clear_streams.error
    @add_clips.error
    @remove_clips.error
    @clear_clips.error
    async def twitch_error(self, ctx: commands.Context, error: Exception) -> discord.Message:
        """ Local error handler for primary Twitch commands. """
        error = getattr(error, "original", error)
        if isinstance(error, commands.MissingPermissions):
            return await ctx.send("Doesn't look like you can manage channels there bub.")
        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.send("Doesn't look like I can manage channels here bub.")
        elif isinstance(error, TooManyAlerts):
            return await ctx.send("Sorry, you have too many alerts active in this guild for that type of monitoring.")
        elif isinstance(error, InvalidBroadcaster):
            return await ctx.send(f"{error.broadcaster} doesn't appear to be a valid streamer.")

    @tasks.loop(minutes=2.0)
    async def get_streamers(self) -> None:
        """ Task loop to get the active streamers in the db and post to specified channels. """
        headers = await self._gen_headers()
        query = """ SELECT * FROM twitchtable; """
        results = await self.bot.pool.fetch(query)

        for item in results:
            if not item['streamer_last_datetime']:
                item['streamer_last_datetime'] = (
                    datetime.datetime.utcnow() - datetime.timedelta(hours=3))
            guild: discord.Guild = self.bot.get_guild(item['guild_id'])
            channel: discord.TextChannel = guild.get_channel(
                item['channel_id'])

            if item['role_id']:
                role = guild.get_role(item['role_id'])

            async with self.bot.session.get(self.stream_endpoint,
                                            params={
                                                "user_login": f"{item['streamer_name']}"},
                                            headers=headers) as resp:
                stream_json = await resp.json()

            if "error" in stream_json:
                await self._refresh_oauth()
            if not stream_json['data']:
                continue

            current_stream = datetime.datetime.utcnow() - \
                item['streamer_last_datetime']

            if ((stream_json['data'][0]['title'] != item['streamer_last_game'])
                    or (current_stream.seconds >= 7200)):
                embed = discord.Embed(
                    title=f"{item['streamer_name']} is live with: {stream_json['data'][0]['title']}",
                    colour=discord.Colour.blurple(),
                    url=f"https://twitch.tv/{item['streamer_name']}")

                async with self.bot.session.get(self.game_endpoint,
                                                params={
                                                    "id": f"{stream_json['data'][0]['game_id']}"},
                                                headers=headers) as game_resp:
                    game_json = await game_resp.json()

                async with self.bot.session.get(self.user_endpoint,
                                                params={
                                                    "id": stream_json['data'][0]['user_id']},
                                                headers=headers) as user_resp:
                    user_json = await user_resp.json()

                embed.set_author(name=stream_json['data'][0]['user_name'])
                embed.set_thumbnail(
                    url=f"{user_json['data'][0]['profile_image_url']}")
                embed.add_field(
                    name="Game/Category", value=f"{game_json['data'][0]['name']}", inline=True)
                embed.add_field(name="Viewers",
                                value=f"{stream_json['data'][0]['viewer_count']}", inline=True)
                embed.set_image(url=stream_json['data'][0]['thumbnail_url'].replace(
                    "{width}", "600").replace("{height}", "400"))

                message = await channel.send(f"{role.mention if role else None}\n\n{item['streamer_name']} is now live!", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
                insert_query = """ UPDATE twitchtable SET streamer_last_game = $1, streamer_last_datetime = $2 WHERE streamer_name = $3; """
                await self.bot.pool.execute(insert_query, stream_json['data'][0]['title'], message.created_at, item['streamer_name'])

    @tasks.loop(minutes=2)
    async def get_clips(self) -> None:
        """ Let's check every 2 minutes for clips, eh? """
        headers = await self._gen_headers()
        query = """ SELECT * FROM twitchcliptable; """
        results = await self.bot.pool.fetch(query)

        for item in results:
            guild = self.bot.get_guild(item['guild_id'])
            channel = guild.get_channel(item['channel_id'])
            last_clips = item['last_25_clips'] or []
            clip_ids = deque(last_clips)

            async with self.bot.session.get(self.clip_endpoint,
                                            params={
                                                "broadcaster_id": item['broadcaster_id']},
                                            headers=headers) as resp:
                clips_json = await resp.json()

            if "error" in clips_json:
                await self._refresh_oauth()
            if not clips_json['data']:
                continue

            clip_data = clips_json['data']  # List of dicts
            clip_data = [
                c_dict for c_dict in clip_data if c_dict['id'] not in clip_ids]
            if not clip_data:
                continue

            for clip_dict in clip_data:
                # Now we have the real data.
                if len(clip_ids) >= 100:
                    clip_ids.popleft()

                clip_ids.append(clip_dict['id'])
                clip_author = clip_dict['creator_name']
                thumbnail = clip_dict['thumbnail_url']
                title = clip_dict['title']
                url = clip_dict['url']
                timestamp = datetime.datetime.strptime(
                    clip_dict['created_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.timezone("UTC"))
                broadcaster_name = clip_dict['broadcaster_name']

                embed = discord.Embed(
                    title=f"{broadcaster_name}'s new clip!", url=url)
                embed.set_thumbnail(url=thumbnail)
                embed.description = f"{title}\n\n- New clip created by {clip_author}."
                embed.timestamp = timestamp
                await channel.send(embed=embed)

            query = "UPDATE twitchcliptable SET last_25_clips = $1 WHERE broadcaster_id = $2 AND guild_id = $3 AND channel_id = $4;"
            await self.bot.pool.execute(query, list(clip_ids), item['broadcaster_id'], guild.id, channel.id)

    @get_streamers.before_loop
    @get_clips.before_loop
    async def twitch_before(self) -> None:
        """ Quickly before the loop... """
        await self.bot.wait_until_ready()

    @get_streamers.error
    @get_clips.error
    async def streamers_error(self, error) -> Union[discord.Message, str]:
        """ On task.loop exception. """
        stats = self.bot.get_cog("Stats")
        tb_str = "".join(traceback.format_exception(
            type(error), error, error.__traceback__, 4))

        if not stats:
            return tb_str

        webhook = stats.webhook
        embed = discord.Embed(title="Streamer error", colour=0xffffff)
        embed.description = f"```py\n{tb_str}```"
        embed.timestamp = datetime.datetime.utcnow()
        await webhook.send(embed=embed)


def cog_unload(self) -> None:
    """ When the cog is unloaded, we wanna kill the task. """
    self.get_streamers.cancel()
    self.get_clips.cancel()


def setup(bot: commands.Bot):
    """ Setup the cog & extension. """
    bot.add_cog(Twitch(bot))
