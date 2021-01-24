from typing import Any, Dict, List, Optional, Union

import discord
from discord.ext import commands
from utils.context import Context


class Testing(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_check(self, ctx: Context):
        return ctx.author.id == self.bot.owner_id


    @commands.group()
    async def test(self, ctx):
        await ctx.send(self.test.commands)

    @test.command()
    async def test1(self, ctx):
        ...


def setup(bot: commands.Bot):
    bot.add_cog(Testing(bot))
