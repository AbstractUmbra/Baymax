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
import typing

import asyncpg
import discord
from discord.ext import commands, tasks
import pytz

from utils import db


class TooManyAlerts(commands.CommandError):
    """ There are too many twitch alerts for this guild. """


class TwitchTable(db.Table):
    """ Create the twitch database table. """
    id = db.PrimaryKeyColumn()

    guild_id = db.Column(db.Integer(big=True))
    channel_id = db.Column(db.Integer(big=True))
    streamer_name = db.Column(db.String)
    streamer_last_game = db.Column(db.String())
    streamer_last_datetime = db.Column(db.Datetime())


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
        self.get_streamers.start()
        self.streamer_limit = 5

    async def _get_streamers(self, name: str, guild_id: int) -> asyncpg.Record:
        """ To get all streamers in the db. """
        query = """ SELECT * FROM twitchtable WHERE streamer_name = $1 AND guild_id = $2; """
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

    async def _gen_headers(self) -> dict:
        """ Let's use this to create the Headers. """
        base = self.bot.config.twitch_headers
        query = "SELECT secret from twitchsecrettable WHERE id = 1;"
        new_token_resp = await self.bot.pool.fetchrow(query)
        new_token = new_token_resp['secret']
        base['Authorization'] = f"Bearer {new_token}"
        return base

    async def _get_streamer_guilds(self, guild_id: int) -> asyncpg.Record:
        """ Return records for matched guild_ids. """
        query = """ SELECT * FROM twitchtable WHERE guild_id = $1; """
        return await self.bot.pool.fetch(query, guild_id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """ Let's not post streamers to dead guilds. """
        records = await self._get_streamer_guilds(guild.id)
        if records:
            query = """ DELETE FROM twitchtable WHERE guild_id = $1; """
            await self.bot.pool.execute(query, guild.id)

    @commands.group(invoke_without_command=True)
    async def twitch(self, ctx: commands.Context) -> discord.Message:
        """ Twitch main command. """
        if not ctx.invoked_subcommand:
            return await ctx.send("You require more arguments for this command.")

    @twitch.command(hidden=True)
    @commands.is_owner()
    async def streamdb(self, ctx: commands.Context) -> discord.Message:
        """ Debug for me. """
        query = """SELECT * FROM twitchtable; """
        oauth_query = """ SELECT edited_at, expires_at FROM twitchsecrettable;"""
        results = await self.bot.pool.fetch(query)
        oauth_results = await self.bot.pool.fetchrow(oauth_query)
        embed = discord.Embed(title="Streamer details",
                              colour=discord.Colour.blurple())
        embed.description = "\n".join(
            f"{item['guild_id']} -> <#{item['channel_id']}> -> {item['streamer_name']} -> {(datetime.datetime.utcnow() - item['streamer_last_datetime']).seconds}" for item in results)
        embed.add_field(name="OAuth Edited at", value=oauth_results['edited_at'].strftime(
            "%d-%m-%Y %H:%M:%S"))
        embed.add_field(name="OAuth Expires at", value=oauth_results['expires_at'].strftime(
            "%d-%m-%Y %H:%M:%S"))
        await ctx.send(embed=embed)

    @twitch.command(name="add")
    @commands.has_guild_permissions(manage_channels=True)
    async def add_streamer(self, ctx, name: str, channel: discord.TextChannel = None) -> typing.Union[discord.Reaction, discord.Message]:
        """ Add a streamer to the database for polling. """
        channel = channel or ctx.channel
        results = await self._get_streamers(name, ctx.guild.id)
        if results:
            return await ctx.send("This streamer is already monitored.")
        query = """ INSERT INTO twitchtable(guild_id, channel_id, streamer_name, streamer_last_datetime) VALUES($1, $2, $3, $4); """
        await self.bot.pool.execute(query, ctx.guild.id, channel.id, name, (datetime.datetime.utcnow() - datetime.timedelta(hours=3)))
        return await ctx.message.add_reaction(":TickYes:672157420574736386")

    @add_streamer.before_invoke
    async def notification_check(self, ctx):
        """ We're gonna check if they have X streams already. """
        query = "SELECT * FROM twitchtable WHERE guild_id = $1;"
        results = await self.bot.pool.fetch(query, ctx.guild.id)
        if len(results) >= self.streamer_limit:
            raise TooManyAlerts(
                "There are too many alerts for this guild already configured.")

    @twitch.command(name="remove")
    @commands.has_guild_permissions(manage_channels=True)
    async def remove_streamer(self, ctx, name: str) -> typing.Union[discord.Reaction, discord.Message]:
        """ Add a streamer to the database for polling. """
        results = await self._get_streamers(name, ctx.guild.id)
        if not results:
            return await ctx.send("This streamer is not in the monitored list.")
        query = """ DELETE FROM twitchtable WHERE streamer_name = $1; """
        await self.bot.pool.execute(query, name)
        return await ctx.message.add_reaction(":TickYes:672157420574736386")

    @twitch.command(name="clear")
    @commands.has_guild_permissions(manage_channels=True)
    async def clear_streams(self, ctx, channel: discord.TextChannel = None) -> typing.Union[discord.Reaction, discord.Message]:
        """ Clears all streams for the context channel or passed channel. """
        channel = channel or ctx.channel
        query = "DELETE FROM twitchtable WHERE channel_id = $1 AND guild_id = $2;"
        confirm = await ctx.prompt("This will remove all streams notifications for the specified channel. Are you sure?", reacquire=False)
        if confirm:
            await self.bot.pool.execute(query, channel.id, ctx.guild.id)
            return await ctx.message.add_reaction(":TickYes:672157420574736386")
        return await ctx.message.add_reaction(":TickNo:672157388823986187")

    @clear_streams.error
    @remove_streamer.error
    @add_streamer.error
    async def twitch_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, commands.MissingPermissions):
            return await ctx.send("Doesn't look like you can manage channels there bub.")
        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.send("Doesn't look like I can manage channels here bub.")
        elif isinstance(error, TooManyAlerts):
            return await ctx.send("Sorry, you have too many alerts active in this guild.")

    @tasks.loop(minutes=5.0)
    async def get_streamers(self) -> None:
        """ Task loop to get the active streamers in the db and post to specified channels. """
        await self.bot.wait_until_ready()
        try:
            headers = await self._gen_headers()
            query = """ SELECT * FROM twitchtable; """
            results = await self.bot.pool.fetch(query)
            for item in results:
                if not item['streamer_last_datetime']:
                    item['streamer_last_datetime'] = (
                        datetime.datetime.utcnow() - datetime.timedelta(hours=3))
                guild = self.bot.get_guild(item['guild_id'])
                channel = guild.get_channel(item['channel_id'])
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
                    cur_time = datetime.datetime.strptime(
                        f"{stream_json['data'][0]['started_at']}", "%Y-%m-%dT%H:%M:%SZ")
                    localtime = cur_time.replace(tzinfo=pytz.timezone(
                        "Europe/London")).astimezone(tz=None)
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
                    embed.set_footer(
                        text=f"Stream started at: {localtime.strftime('%b %d %Y - %H:%M')} | Currently: {datetime.datetime.now().strftime('%b %d %Y - %H:%M')}")
                    message = await channel.send(f"{item['streamer_name']} is now live!", embed=embed)
                    insert_query = """ UPDATE twitchtable SET streamer_last_game = $1, streamer_last_datetime = $2 WHERE streamer_name = $3; """
                    await self.bot.pool.execute(insert_query, stream_json['data'][0]['title'], message.created_at, item['streamer_name'])
        except Exception:
            traceback.print_exc()

    @get_streamers.after_loop
    async def streamers_error(self):
        """ On task.loop exception. """
        if self.get_streamers.failed():
            stats = self.bot.get_cog("Stats")
            if not stats:
                return traceback.print_exc()
            webhook = stats.webhook
            embed = discord.Embed(title="Streamer error", colour=0xffffff)
            embed.description = f"```py\n{self.get_streamers.exception()}```"
            embed.timestamp = datetime.datetime.utcnow()
            await webhook.send(embed=embed)


def cog_unload(self):
    """ When the cog is unloaded, we wanna kill the task. """
    self.get_streamers.cancel()


def setup(bot):
    """ Setup the cog & extension. """
    bot.add_cog(Twitch(bot))
