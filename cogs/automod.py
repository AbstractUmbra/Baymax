""" Automod cog file. """

import discord
from discord.ext import commands

from utils.settings import SETTINGS
from utils.decorators import with_roles, in_channel
from utils.automod_checks import save_bans, save_mute, BANNED_USERS, MUTED_USERS


class AutoMod(commands.Cog):
    """ Automod Cog. """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """ Perma ban dicks. """
        if member.id in BANNED_USERS.values():
            await member.send("Absolute cuntstain.")
            await member.ban(reason="Absolute cuntstain.")

    @commands.Cog.listener()
    async def on_message(self, msg):
        """ Mute someone. """
        if msg.author.id in MUTED_USERS.values():
            return await msg.delete()

    @with_roles(*SETTINGS['admins'])
    @in_channel(*SETTINGS['whitelisted_channels'])
    @commands.command(hidden=True)
    async def mute(self, ctx, member: discord.Member):
        """ Mute a user - delete ANY message they send. """
        MUTED_USERS[member.display_name] = member.id
        save_mute(MUTED_USERS)
        await ctx.author.send(f"{member.display_name} added to mute list.")

    @with_roles(*SETTINGS['admins'])
    @in_channel(*SETTINGS['whitelisted_channels'])
    @commands.command(hidden=True)
    async def unmute(self, ctx, member: discord.Member):
        """ Mute a user - delete ANY message they send. """
        for name, user_id in MUTED_USERS.items():
            if member.id == user_id:
                unmute_me = name
                break
        MUTED_USERS.pop(str(unmute_me), None)
        await ctx.author.send(f"{member.display_name} removed from the mute list.")
        save_mute(MUTED_USERS)

    @with_roles(*SETTINGS['admins'])
    @in_channel(*SETTINGS['whitelisted_channels'])
    @commands.command(hidden=True)
    async def autoban(self, ctx, member: discord.Member):
        """ Add user to autoban - as soon as they join they are autobanned. """
        BANNED_USERS[member.display_name] = member.id
        await ctx.author.send(f"{member.display_name} added to the ban list.")
        save_bans(BANNED_USERS)
        await member.send("Absolutely cuntstain.")
        await member.ban(reason="Absolutely cuntstain.")

    @in_channel(*SETTINGS['whitelisted_channels'])
    @commands.command(hidden=True)
    async def listmutes(self, ctx):
        """ Send author a list of muted. """
        for member in MUTED_USERS.keys():
            await ctx.author.send(f"User {member} in {ctx.guild.name} is muted.")

    @in_channel(*SETTINGS['whitelisted_channels'])
    @commands.command(hidden=True)
    async def listbans(self, ctx):
        """ Send author a list of bans. """
        for member in BANNED_USERS.keys():
            await ctx.author.send(f"User {member} in {ctx.guild.name} is autobanned.")


def setup(bot):
    """ Cog setup. """
    bot.add_cog(AutoMod(bot))
