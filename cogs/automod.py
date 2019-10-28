import discord
from discord.ext import commands

from utils.checks import check_bound_text
from utils.automod_checks import BAN_USERS


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """ Perma ban dicks. """
        if member.id in BAN_USERS.keys():
            await member.send("Absolute cuntstain.")
            await member.ban(reason="Absolute cuntstain.")

    @check_bound_text()
    @commands.command(hidden=True)
    async def autoban(self, ctx, member: discord.Member):
        BAN_USERS[member.display_name] = member.id
        await member.send("Absolutely cuntstain.")
        await member.ban(reason="Absolutely cuntstain.")

    @check_bound_text()
    @commands.command(hidden=True)
    async def dickkick(self, ctx, dick: discord.Member):
        await dick.send("Thank you for your time in the server. You're now FUCKIN BOOTED.")
        return await dick.kick(reason="Is a dick.")


def setup(bot):
    bot.add_cog(AutoMod(bot))
