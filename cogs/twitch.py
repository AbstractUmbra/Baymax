""" Basic 'get_streams' kinda deal. """
import datetime

import discord
from discord.ext import commands, tasks


class Twitch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_game = None
        self._last_td = datetime.datetime.utcnow()
        self.get_streamers.start()

    @commands.command()
    @commands.is_owner()
    async def getdata(self, ctx):
        """ [DEBUG] - get debug data. """
        url = "https://api.twitch.tv/helix/streams"
        params = {"user_login": "speciaiisttv"}

        async with self.bot.session.get(url, params=params, headers=self.headers) as resp:
            jsony = await resp.json()
        await ctx.send(f"```json\n{jsony}```")

    @tasks.loop(minutes=5.0)
    async def get_streamers(self):
        """ [PROD] - Actual task. Runs nicely. """
        channel = self.bot.get_channel(690571015134380043)
        async with self.bot.session.get("https://api.twitch.tv/helix/streams", params={"user_login": "speciaiisttv"}, headers=self.bot.config.twitch_headers) as resp:
            stream_json = await resp.json()
        if stream_json['data'] != []:
            current_stream = datetime.datetime.utcnow() - self._last_td
            if stream_json['data'][0]['title'] == self._last_game or current_stream.seconds >= 3600:
                return
            self._last_game = stream_json['data'][0]['title']
            self._last_td = datetime.datetime.utcnow()
            embed = discord.Embed(
                title=f"Specialist is live with: {stream_json['data'][0]['title']}", colour=discord.Colour.blurple(), url="https://twitch.tv/speciaiisttv")
            async with self.bot.session.get("https://api.twitch.tv/helix/games", params={
                    "id": f"{stream_json['data'][0]['game_id']}"}, headers=self.bot.config.twitch_headers) as game_resp:
                game_json = await game_resp.json()
            async with self.bot.session.get("https://api.twitch.tv/helix/users", params={"id": stream_json['data'][0]['user_id']}, headers=self.bot.config.twitch_headers) as user_resp:
                user_json = await user_resp.json()
            embed.set_author(name=stream_json['data'][0]['user_name'],
                             icon_url=f"{user_json['data'][0]['profile_image_url']}")
            embed.add_field(
                name="Game", value=f"{game_json['data'][0]['name']}", inline=True)
            embed.add_field(name="Viewers",
                            value=f"{stream_json['data'][0]['viewer_count']}", inline=True)
            embed.set_image(url=stream_json['data'][0]['thumbnail_url'].replace(
                "{width}", "600").replace("{height}", "400"))
            await channel.send(embed=embed)


def cog_unload(self):
    self.get_streamers.cancel()


def setup(bot):
    bot.add_cog(Twitch(bot))
