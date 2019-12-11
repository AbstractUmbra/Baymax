""" Rust Updates Cog. """
from datetime import datetime
import time

import aiohttp
import discord
from discord.ext import commands, tasks

from utils.rust_checks import load_rust_config, save_rust_config

RUST_CONFIG = load_rust_config("../config/rust-updates.json")


class Rust(commands.Cog):
    """ This class will return the update details for Rust as an embed. """

    def __init__(self, bot):
        self.bot = bot
        self.rust_client_update.start()
        self.rust_server_update.start()
        self.rust_cs = aiohttp.ClientSession()

    def cog_unload(self):
        self.rust_client_update.cancel()
        self.rust_server_update.cancel()

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
    async def rust_client_update(self):
        """ Post the update. """
        # Get the update details first, returns json dict
        async with self.rust_cs.get("https://api.rust-servers.info/update/") as update:
            details = await update.json()
            epoch = details['timestamp']
            build_id = details['buildID']

        if build_id == RUST_CONFIG['build_id']:
            # No update since last check
            pass
        else:
            RUST_CONFIG["build_id"] = build_id

        RUST_CONFIG["last_client_update_check"] = datetime.now().strftime(
            "%d-%m-%Y %H:%M")
        save_rust_config(RUST_CONFIG)

        # get the channel to send to.
        rust_channel = self.bot.get_channel(
            int(RUST_CONFIG["174702278673039360"]['channel']))

        actual_time = time.strftime(
            "%d-%m-%Y %H:%M", time.localtime(int(epoch)))

        update_embed = discord.Embed(title="Client update released!",
                                     color=0xb7410e)
        update_embed.set_author(name="Rust Update API")
        update_embed.set_thumbnail(
            url="https://pbs.twimg.com/profile_images/"
            "378800000826280720/8f9145eff97d162122af02fc1488c611_400x400.png")
        update_embed.add_field(name=f"Build ID",
                               value=f"{build_id}",
                               inline=True)
        update_embed.add_field(name="Released at",
                               value=f"{actual_time}",
                               inline=True)
        return await rust_channel.send(embed=update_embed)

    @tasks.loop(minutes=5.0)
    async def rust_server_update(self):
        """ Post the update. """
        # Get the update details first, returns json dict
        async with self.rust_cs.get("https://api.rust-servers.info/update_server/") as srv_update:
            details = await srv_update.json()
            epoch = details['timestamp']
            srv_build_id = details['buildID']

        if srv_build_id == RUST_CONFIG['srv_build_id']:
            pass
        else:
            RUST_CONFIG["srv_build_id"] = srv_build_id

        RUST_CONFIG["last_srv_update_check"] = datetime.now().strftime(
            "%d-%m-%Y %H:%M")
        save_rust_config(RUST_CONFIG)

        # get the channel to send to.
        rust_channel = self.bot.get_channel(
            int(RUST_CONFIG["174702278673039360"]['channel']))

        actual_time = time.strftime(
            "%d-%m-%Y %H:%M", time.localtime(int(epoch)))

        update_embed = discord.Embed(title="Server update released - WIPE HYPE",
                                     color=0xb7410e)
        update_embed.set_author(name="Rust Update API")
        update_embed.set_thumbnail(
            url="https://pbs.twimg.com/profile_images/"
            "378800000826280720/8f9145eff97d162122af02fc1488c611_400x400.png")
        update_embed.add_field(name=f"Server Build ID",
                               value=f"{srv_build_id}",
                               inline=True)
        update_embed.add_field(name="Released at",
                               value=f"{actual_time}",
                               inline=True)
        return await rust_channel.send(embed=update_embed)

    @rust_client_update.before_loop
    async def before_rust_client_update(self):
        """ Before task for client. """
        await self.bot.wait_until_ready()
        if self.rust_cs.closed:
            self.rust_cs = aiohttp.ClientSession()

    @rust_client_update.after_loop
    async def after_rust_client_update(self):
        """ After task for client. """
        await self.rust_cs.close()
        RUST_CONFIG = load_rust_config("../config/rust-updates.json")

    @rust_server_update.before_loop
    async def before_rust_server_update(self):
        """ Before task for server. """
        await self.bot.wait_until_ready()
        if self.rust_cs.closed:
            self.rust_cs = aiohttp.ClientSession()

    @rust_server_update.after_loop
    async def after_rust_server_update(self):
        """ After task for server. """
        await self.rust_cs.close()
        RUST_CONFIG = load_rust_config("../config/rust-updates.json")


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Rust(bot))
