""" Rust Updates Cog. """
import time

import discord
import aiohttp
from discord.ext import commands, tasks

from utils.rust_checks import save_rust_config, RUST_CONFIG


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
            return
        else:
            RUST_CONFIG["build_id"] = build_id
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
        async with self.rust_cs.get("https://api.rust-servers.info/update-server/") as srv_update:
                details = await srv_update.json()
                print(f"details: {details}")
                epoch = details['timestamp']
                srv_build_id = details['buildID']

        if srv_build_id == RUST_CONFIG['srv_build_id']:
            return
        else:
            RUST_CONFIG["srv_build_id"] = srv_build_id
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
        await self.bot.wait_until_ready()
        if self.rust_cs.closed:
            self.rust_cs = aiohttp.ClientSession()

    @rust_client_update.after_loop
    async def after_rust_client_update(self):
        await self.rust_cs.close()

    @rust_server_update.before_loop
    async def before_rust_server_update(self):
        await self.bot.wait_until_ready()
        if self.rust_cs.closed:
            self.rust_cs = aiohttp.ClientSession()

    @rust_server_update.after_loop
    async def after_rust_server_update(self):
        await self.rust_cs.close()


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Rust(bot))
