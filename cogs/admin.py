""" Cleanup Cog. """

from random import choice
from unidecode import unidecode

import discord
from discord.ext import commands
from bot import SETTINGS, CONFIG_PATH, check_bound_text, save_settings, admin_check


class Admin(commands.Cog):
    """ Admin only commands. """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def adminlist(self, ctx):
        """ Prints the admin list. """
        for admin in SETTINGS["admins"]:
            await ctx.send(ctx.guild.get_member(admin), delete_after=20)

    @admin_check()
    @check_bound_text()
    @commands.command()
    async def add(self, ctx, member: discord.Member):
        """ Add a member to the admin list. """
        if member is None:
            await ctx.send(f"Invalid usage; use {SETTINGS['bot_prefix']}admin add <@user>.",
                           delete_after=5)
        elif member.id in SETTINGS["admins"]:
            await ctx.send(f"User {member} is already an admin.",
                           delete_after=5)
        else:
            SETTINGS["admins"].append(member.id)
            save_settings(CONFIG_PATH)
            await ctx.send(f"{member} has been added to admin list.",
                           delete_after=5)

    @admin_check()
    @check_bound_text()
    @commands.command()
    async def remove(self, ctx, member: discord.Member):
        """ Remove a member from the admin list. """
        if member is None:
            await ctx.send(f"Missing argument use {SETTINGS['bot_prefix']}admin remove <@user>",
                           delete_after=5)
        elif member.id not in SETTINGS["admins"]:
            await ctx.send("Admin not found in admin list.",
                           delete_after=5)
        else:
            SETTINGS["admins"].remove(member.id)
            save_settings(CONFIG_PATH)
            await ctx.send(f"{member} was removed from admin list.",
                           delete_after=5)

    @admin_check()
    @check_bound_text()
    @commands.command()
    async def add_bound_channel(self, ctx, channel: discord.TextChannel):
        """ Add a text channel to be bound. """
        if channel is None:
            await ctx.send(
                f"Invalid usage, use {SETTINGS['bot_prefix']}admin add_channel <@text_channel>.",
                delete_after=5
            )
        elif channel.id in SETTINGS["bound_text_channels"]:
            await ctx.send(f"Channel {channel} is already bot bound.",
                           delete_after=5)
        else:
            SETTINGS["bound_text_channels"].append(channel.id)
            save_settings(CONFIG_PATH)
            await ctx.send(f"{channel} has been added to the bound channel list.",
                           elete_after=5)

    @admin_check()
    @check_bound_text()
    @commands.command(hidden=True)
    async def summon(self, ctx, member: discord.Member):
        """ Summon a voice member to current executors voice channel. """
        if member is None:
            await ctx.send(
                f"Missing argument, use `{SETTINGS['bot_prefix']}admin summonfucker <@user>`.",
                delete_after=5
            )
        elif member.voice.channel is ctx.message.author.voice.channel:
            await ctx.send(f"They're already in your voice chat, you wank.",
                           delete_after=5)
        else:
            await member.move_to(ctx.message.author.voice.channel)

    @admin_check()
    @commands.command(hidden=True, name="load")
    async def load_cog(self, ctx, *, cog: str):
        """ Load a cog module. """
        cog_full = f"cogs.{cog}"
        try:
            self.bot.load_extension(cog_full)
        except Exception as err:
            await ctx.send(f"**`ERROR:`** {type(err).__name__} - {err}",
                           delete_after=10)
        else:
            await ctx.send(f"Loaded Cog: {cog}.", delete_after=5)

    @admin_check()
    @commands.command(hidden=True, name="unload")
    async def unload_cog(self, ctx, *, cog: str):
        """ Unload a cog module. """
        cog_full = f"cogs.{cog}"
        try:
            self.bot.unload_extension(cog_full)
        except Exception as err:
            await ctx.send(f"**`ERROR:`** {type(err).__name__} - {err}",
                           delete_after=10)
        else:
            await ctx.send(f"Unloaded Cog: {cog}.", delete_after=5)

    @admin_check()
    @commands.command(hidden=True, name="reload")
    async def reload_cog(self, ctx, *, cog: str):
        """ Reload a cog module. """
        cog_full = f"cogs.{cog}"
        try:
            self.bot.unload_extension(cog_full)
            self.bot.load_extension(cog_full)
        except Exception as err:
            await ctx.send(f"**`ERROR:`** {type(err).__name__} - {err}",
                           delete_after=10)
        else:
            await ctx.send(f"Reloaded Cog: {cog}.", delete_after=5)


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Admin(bot))
