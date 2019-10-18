import discord
from discord.ext import commands

from utils.checks import check_bound_text


class Dicks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @check_bound_text()
    @commands.command()
    async def dick(self, dick: discord.Member):
        await dick.send("Thank you for your time in the server. You're now FUCKIN BOOTED.")
        return await dick.kick(reason="Is a dick.")


def setup(bot):
    bot.add_cog(Dicks(bot))
