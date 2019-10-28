""" Automod cog file. """

import discord
from discord.ext import commands

from utils.checks import check_bound_text
from utils.automod_checks import save_bans, save_mute, BANNED_USERS, MUTED_USERS

class AutoMod(commands.Cog):
    """ Automod Cog. """
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """ Perma ban dicks. """
        if member.id in BANNED_USERS.keys():
            await member.send("Absolute cuntstain.")
            await member.ban(reason="Absolute cuntstain.")

    @commands.Cog.listener()
    async def on_message(self, msg):
        """ Mute someone. """
        if msg.author.id in MUTED_USERS:
            return await msg.delete()

    @check_bound_text()
    @commands.command(hidden=True)
    async def mute(self, ctx, member: discord.Member):
        MUTED_USERS[member.display_name] = member.id
        save_mute(MUTED_USERS)
        print(f"{member.display_name} added to mute list.")

    @check_bound_text()
    @commands.command(hidden=True)
    async def autoban(self, ctx, member: discord.Member):
        BANNED_USERS[member.display_name] = member.id
        save_bans(BANNED_USERS)
        await member.send("Absolutely cuntstain.")
        await member.ban(reason="Absolutely cuntstain.")

    @check_bound_text()
    @commands.command(hidden=True)
    async def listmutes(self, ctx):
        for member in MUTED_USERS.keys():
            await ctx.author.send(f"User {member} in {ctx.guild.name} is muted.")

    @check_bound_text()
    @commands.command(hidden=True)
    async def listbans(self, ctx):
        for member in BANNED_USERS.keys():
            await ctx.author.send(f"User {member} in {ctx.guild.name} is autobanned.")

    @check_bound_text()
    @commands.command(hidden=True)
    async def dickkick(self, ctx, dick: discord.Member):
        await dick.send("Thank you for your time in the server. You're now FUCKIN BOOTED.")
        return await dick.kick(reason="Is a dick.")


def setup(bot):
    bot.add_cog(AutoMod(bot))
