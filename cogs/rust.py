""" Rust Updates Cog. """
from datetime import datetime
import time
import functools

import aiohttp
import discord
from discord.ext import commands, tasks
import valve.source.a2s as a2s

from utils.rust_checks import load_rust_config, save_rust_config

RUST_CONFIG = load_rust_config("../config/rust-updates.json")


class Rust(commands.Cog):
    """ This class will return the update details for Rust as an embed. """

    def __init__(self, bot):
        self.bot = bot
        self.client_update.start()
        self.server_update.start()
        self.rust_cs = aiohttp.ClientSession()

    def cog_unload(self):
        self.client_update.cancel()
        self.server_update.cancel()

    @commands.command(hidden=True)
    async def dict_print(self, ctx):
        """ Print the Current Dict info. """
        dict_embed = discord.Embed(title="**Rust Dict Info**",
                                   color=0x00ff00)
        dict_embed.set_author(name=self.bot.user.name)
        dict_embed.set_thumbnail(url=self.bot.user.avatar_url)
        dict_embed.timestamp = datetime.now()
        for key, value in RUST_CONFIG.items():
            dict_embed.add_field(name=f"**{key}**",
                                 value=f"{value}",
                                 inline=True)
        await ctx.send(embed=dict_embed)

    def terminus_steam(self):
        """ Blocky - queries steam api. """
        term_address = ("51.89.25.157", 28015)
        player_list = []
        with a2s.ServerQuerier(address=term_address, timeout=20.0) as server:
            for player in server.players()["players"]:
                player_list.append(player["name"])
        return player_list

    @commands.command()
    async def terminus(self, ctx):
        """ Asyncy - posts embed about steam stats. """
        actual_func = functools.partial(self.terminus_steam)
        player_list = await self.bot.loop.run_in_executor(None, actual_func)
        player_embed = discord.Embed(title="**Current Terminus Playerlist**",
                                     color=0x00ff00)
        player_embed.set_author(name=ctx.author.name)
        player_embed.set_thumbnail(url=ctx.author.avatar_url)
        player_embed.timestamp = datetime.now()
        player_list_string = "\n".join(player for player in player_list)
        player_embed.add_field(name="Current Terminus Players",
                               value=f"{player_list_string}", inline=True)
        player_embed.add_field(name="Player count total",
                               value=len(player_list))
        await ctx.send(embed=player_embed, delete_after=10)

    @commands.command(hidden=True)
    async def manual_client_check(self, ctx):
        """ Manually post the client update details - tests if api works. """
        async with self.rust_cs.get("https://api.rust-servers.info/update/") as cli_update:
            details = await cli_update.json()
        cli_time = time.strftime(
            '%d-%m-%Y %H:%M', time.localtime(int(details['timestamp'])))
        await ctx.send(f"Client ID: {details['buildID']}", delete_after=10)
        return await ctx.send(f"Client TD: {cli_time}", delete_after=10)

    @commands.command(hidden=True)
    async def manual_server_check(self, ctx):
        """ Manually post the server update details - tests if api works. """
        async with self.rust_cs.get("https://api.rust-servers.info/update_server/") as srv_update:
            details = await srv_update.json()
        cli_time = time.strftime(
            '%d-%m-%Y %H:%M', time.localtime(int(details['timestamp'])))
        await ctx.send(f"Client ID: {details['buildID']}", delete_after=10)
        return await ctx.send(f"Client TD: {cli_time}", delete_after=10)

    @tasks.loop(minutes=5.0)
    async def client_update(self):
        """ Post the update. """
        # Get the update details first, returns json dict
        async with self.rust_cs.get("https://api.rust-servers.info/update/") as update:
            details = await update.json()
            epoch = details['timestamp']
            build_id = details['buildID']

        if build_id != RUST_CONFIG['build_id']:
            RUST_CONFIG["build_id"] = build_id

            # get the channel to send to.
            rust_channel = self.bot.get_channel(
                int(RUST_CONFIG["174702278673039360"]['channel']))

            update_embed = discord.Embed(title="Client update released!",
                                         color=0xb7410e)
            update_embed.set_author(name="Rust Update API")
            update_embed.set_thumbnail(
                url="https://pbs.twimg.com/profile_images/"
                "378800000826280720/8f9145eff97d162122af02fc1488c611_400x400.png")
            update_embed.timestamp = datetime.fromtimestamp(int(epoch))
            update_embed.add_field(name=f"Build ID",
                                   value=f"`{build_id}`",
                                   inline=True)
            await rust_channel.send("@here")
            await rust_channel.send(embed=update_embed)
        save_rust_config(RUST_CONFIG)

    @tasks.loop(minutes=5.0)
    async def server_update(self):
        """ Post the update. """
        # Get the update details first, returns json dict
        async with self.rust_cs.get("https://api.rust-servers.info/update_server/") as srv_update:
            details = await srv_update.json()
            epoch = details['timestamp']
            srv_build_id = details['buildID']

        if srv_build_id != RUST_CONFIG['srv_build_id']:
            RUST_CONFIG["srv_build_id"] = srv_build_id

            # get the channel to send to.
            rust_channel = self.bot.get_channel(
                int(RUST_CONFIG["174702278673039360"]['channel']))

            update_embed = discord.Embed(title="Server update released - WIPE HYPE",
                                         color=0xb7410e)
            update_embed.set_author(name="Rust Update API")
            update_embed.set_thumbnail(
                url="https://pbs.twimg.com/profile_images/"
                "378800000826280720/8f9145eff97d162122af02fc1488c611_400x400.png")
            update_embed.timestamp = datetime.fromtimestamp(int(epoch))
            update_embed.add_field(name=f"Server Build ID",
                                   value=f"`{srv_build_id}`",
                                   inline=True)
            await rust_channel.send("@here")
            await rust_channel.send(embed=update_embed)
        save_rust_config(RUST_CONFIG)

    @client_update.before_loop
    async def before_rust_client_update(self):
        """ Before task for client. """
        await self.bot.wait_until_ready()
        if self.rust_cs.closed:
            self.rust_cs = aiohttp.ClientSession()

    @client_update.after_loop
    async def after_rust_client_update(self):
        """ After task for client. """
        save_rust_config(RUST_CONFIG)
        # await self.rust_cs.close()

    @server_update.before_loop
    async def before_rust_server_update(self):
        """ Before task for server. """
        await self.bot.wait_until_ready()
        if self.rust_cs.closed:
            self.rust_cs = aiohttp.ClientSession()

    @server_update.after_loop
    async def after_rust_server_update(self):
        """ After task for server. """
        save_rust_config(RUST_CONFIG)
        # await self.rust_cs.close()


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Rust(bot))
