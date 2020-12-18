from typing import Any, Dict, List, Optional, Union

import discord
from discord.ext import commands
from utils.context import Context


class Testing(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_check(self, ctx: Context):
        return ctx.author.id == self.bot.owner_id

    @commands.command()
    async def test(
        self,
        ctx: commands.Context,
        emoji: Union[discord.Emoji, discord.PartialEmoji, str],
    ):
        await ctx.send(emoji)
        await ctx.message.add_reaction(emoji)


def setup(bot: commands.Bot):
    bot.add_cog(Testing(bot))
