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

    @admin_check()
    @check_bound_text()
    @commands.command(hidden=True)
    async def spelling(self, ctx):
        """ Time to mess with vowels! >:D """
        vowels = "aeiouAEIOU"
        # Blacklist server admin.
        for member in ctx.guild.members:
            if member is ctx.guild.owner:
                continue
            original_name = member.display_name
            await ctx.send(f"Jumbling {member.display_name}'s name..", delete_after=10)
            # time to jumble...
            new_name = ""
            # Remove CFS Tag
            if "[𝓒𝓕𝓢] " in original_name:
                original_name = original_name.replace("[𝓒𝓕𝓢] ", "")
            # Take away non-utf8 cahracters.
            original_name = unidecode(original_name).replace(
                "[", "").replace("]", "")
            for char in f"{original_name}":
                if char in vowels:
                    new_name += choice(list(vowels))
                else:
                    new_name += char
            await member.edit(nick=new_name.capitalize(), reason="Cannot spell.")

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
            await ctx.send(f"Invalid usage; use {SETTINGS['bot_prefix']}admin add <@user>.")
        elif member.id in SETTINGS["admins"]:
            await ctx.send(f"User {member} is already an admin.")
        else:
            SETTINGS["admins"].append(member.id)
            save_settings(CONFIG_PATH)
            await ctx.send(f"{member} has been added to admin list.")

    @admin_check()
    @check_bound_text()
    @commands.command()
    async def remove(self, ctx, member: discord.Member):
        """ Remove a member from the admin list. """
        if member is None:
            await ctx.send(f"Missing argument use {SETTINGS['bot_prefix']}admin remove <@user>")
        elif member.id not in SETTINGS["admins"]:
            await ctx.send("Admin not found in admin list.")
        else:
            SETTINGS["admins"].remove(member.id)
            save_settings(CONFIG_PATH)
            await ctx.send(f"{member} was removed from admin list.")

    @admin_check()
    @check_bound_text()
    @commands.command()
    async def add_bound_channel(self, ctx, channel: discord.TextChannel):
        """ Add a text channel to be bound. """
        if channel is None:
            await ctx.send(
                f"Invalid usage, use {SETTINGS['bot_prefix']}admin add_channel <@text_channel>."
            )
        elif channel.id in SETTINGS["bound_text_channels"]:
            await ctx.send(f"Channel {channel} is already bot bound.")
        else:
            SETTINGS["bound_text_channels"].append(channel.id)
            save_settings(CONFIG_PATH)
            await ctx.send(f"{channel} has been added to the bound channel list.")

def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Admin(bot))
