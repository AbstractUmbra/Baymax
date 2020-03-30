""" Basic 'get_streams' kinda deal. """
import datetime

import asyncpg
import discord
from discord.ext import commands, tasks

from utils import db
# datetime.datetime.strptime(stream_jsony['data'][0]['started_at'], '%Y-%m-%dT%H:%M:%SZ')


class TwitchTable(db.Table):
    id = db.PrimaryKeyColumn()

    guild_id = db.Column(db.Integer(big=True))
    channel_id = db.Column(db.Integer(big=True))
    streamer_name = db.Column(db.String)
    streamer_last_game = db.Column(db.String())
    streamer_last_datetime = db.Column(db.Datetime())


class Twitch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stream_endpoint = "https://api.twitch.tv/helix/streams"
        self.user_endpoint = "https://api.twitch.tv/helix/users"
        self.game_endpoint = "https://api.twitch.tv/helix/games"
        self.get_streamers.start()

    async def _get_streamers(self, name: str) -> asyncpg.Record:
        """ To get all streamers in the db. """
        query = """ SELECT * FROM twitchtable WHERE streamer_name = $1; """
        return await self.bot.pool.fetch(query, name)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def getdata(self, ctx, name: str):
        """ [DEBUG] - get debug data. """
        params = {"user_login": f"{name}"}

        async with self.bot.session.get(self.stream_endpoint, params=params, headers=self.bot.config.twitch_headers) as stream_resp:
            stream_jsony = await stream_resp.json()
        if not stream_jsony['data']:
            return await ctx.send("No stream.")
        async with self.bot.session.get(self.game_endpoint, params={
                "id": f"{stream_jsony['data'][0]['game_id']}"}, headers=self.bot.config.twitch_headers) as game_resp:
            game_jsony = await game_resp.json()
        async with self.bot.session.get(self.user_endpoint,
                                        params={
                                            "id": stream_jsony['data'][0]['user_id']},
                                        headers=self.bot.config.twitch_headers) as user_resp:
            user_jsony = await user_resp.json()
        embed = discord.Embed(title="Stream Debug Stats",
                              colour=discord.Colour.red())
        embed.add_field(name="Stream JSON",
                        value=f"```json\n{stream_jsony}```", inline=False)
        embed.add_field(name="Game JSON",
                        value=f"```json\n{game_jsony}```", inline=False)
        embed.add_field(name="User JSON",
                        value=f"```json\n{user_jsony}```", inline=False)
        embed.add_field(name="Current Secs",
                        value=f"{datetime.datetime.utcnow() - self._last_td}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def streamdb(self, ctx):
        query = """SELECT * FROM twitchtable;"""
        results = await self.bot.pool.fetch(query)
        for item in results:
            await ctx.send(f"{item['guild_id']} -> {item['channel_id']} -> {item['streamer_name']} -> {(datetime.datetime.utcnow() - item['streamer_last_datetime']).seconds}")

    @commands.command(name="add-streamer")
    async def add_streamer(self, ctx, name: str, channel: discord.TextChannel = None):
        """ Add a streamer to the database for polling. """
        channel = channel or ctx.channel
        results = await self._get_streamers(name)
        if results:
            return await ctx.send("This streamer is already monitored.")
        query = """ INSERT INTO twitchtable (guild_id, channel_id, streamer_name) VALUES ($1, $2, $3); """
        await self.bot.pool.execute(query, ctx.guild.id, channel.id, name)
        return await ctx.message.add_reaction(":TickYes:672157420574736386")

    @tasks.loop(minutes=5.0)
    async def get_streamers(self):
        """ [PROD] - Actual task. Runs nicely. """
        query = """ SELECT * FROM twitchtable; """
        results = await self.bot.pool.fetch(query)
        for item in results:
            guild = self.bot.get_guild(item['guild_id'])
            channel = guild.get_channel(item['channel_id'])
            async with self.bot.session.get(self.stream_endpoint,
                                            params={
                                                "user_login": f"{item['streamer_name']}"},
                                            headers=self.bot.config.twitch_headers) as resp:
                stream_json = await resp.json()
            if stream_json['data'] != []:
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
                                                    headers=self.bot.config.twitch_headers) as game_resp:
                        game_json = await game_resp.json()
                    async with self.bot.session.get(self.user_endpoint,
                                                    params={
                                                        "id": stream_json['data'][0]['user_id']},
                                                    headers=self.bot.config.twitch_headers) as user_resp:
                        user_json = await user_resp.json()
                    embed.set_author(name=stream_json['data'][0]['user_name'],
                                     icon_url=f"{user_json['data'][0]['profile_image_url']}")
                    embed.add_field(
                        name="Game", value=f"{game_json['data'][0]['name']}", inline=True)
                    embed.add_field(name="Viewers",
                                    value=f"{stream_json['data'][0]['viewer_count']}", inline=True)
                    embed.set_image(url=stream_json['data'][0]['thumbnail_url'].replace(
                        "{width}", "600").replace("{height}", "400"))
                    message = await channel.send(f"{item['streamer_name']} is now live https://twitch.tv/{item['streamer_name']}", embed=embed)
                insert_query = """ UPDATE twitchtable SET streamer_last_game = $1, streamer_last_datetime = $2 WHERE streamer_name = $3; """
                await self.bot.pool.execute(insert_query, self._last_game, message.created_at, item['streamer_name'])


def cog_unload(self):
    self.get_streamers.cancel()


def setup(bot):
    bot.add_cog(Twitch(bot))
