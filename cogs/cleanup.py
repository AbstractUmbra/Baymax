""" Cleanup Cog. """

import discord
from discord.ext import commands

from . import BaseCog


def is_groovy_command(msg):
    """ Is it a Groovy command? """
    if msg.content.startswith("-") or msg.author.id == 234395307759108106:
        return True
    return False


def is_pinned(msg):
    """ Is it a pinned command? """
    if msg.pinned:
        return False
    return True


def robo_self(msg):
    """ Is the author RoboHz? """
    if msg.author.id == 565095015874035742:
        if not msg.pinned:
            return True
    elif msg.content.startswith("r!"):
        if not msg.pinned:
            return True
    return False


class Cleanup(BaseCog):
    """ Cleanup """

    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_message(self, msg):
        """ If Groovy messages, bin it. """
        if msg.content.startswith("-") or msg.author.id == 234395307759108106:
            await msg.delete(delay=3)

    @commands.has_any_role(262403103054102528, 337723529837674496, 534447855608266772)
    @commands.command()
    async def roboclean(self, ctx, count: int = 100, channel: discord.TextChannel = None):
        """ Cleans RoboHz commands if they get stuck. """
        if channel is None:
            channel = ctx.channel
        deleted = await channel.purge(limit=(count + 1), check=robo_self)
        await channel.send(
            f"Deleted {len(deleted) - 1} Robo-Hz messages from {channel.mention}", delete_after=5
        )

    @commands.has_any_role(262403103054102528, 337723529837674496, 534447855608266772)
    @commands.command(aliases=["purge"])
    async def prune(self, ctx, count: int = 100, channel: discord.TextChannel = None):
        """ Prune a channel. """
        if ctx.author.id != 155863164544614402:
            if count > 100:
                await ctx.send("Sorry, you cannot purge more than 100 messages at a time.")
        else:
            if channel is None:
                channel = ctx.channel
            deleted = await channel.purge(limit=(count+1), check=is_pinned)
            await channel.send(
                f"Deleted {len(deleted) - 1} messages from {channel.mention}", delete_after=5
            )


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Cleanup(bot))
