""" Cleanup Cog. """

import discord
from discord.ext import commands

from utils.checks import admin_check


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


class Cleanup(commands.Cog):
    """ Cleanup """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg):
        """ If Groovy messages, bin it. """
        if msg.content.startswith("-") or msg.author.id == 234395307759108106:
            await msg.delete(delay=3)

    @commands.command()
    async def music_cleanup(self, ctx, count: int = 100):
        """ Perform the music cleanup - bins all of 'Groovy' messages. """
        if count > 300:
            await ctx.send(f"Fuck you, no more than 300 messages to clean.")
        else:
            deleted = await ctx.channel.purge(limit=count, check=is_groovy_command)
            await ctx.channel.send(
                f"Deleted {len(deleted)} music bot messages from {ctx.channel.mention}",
                delete_after=5
            )

    @admin_check()
    @commands.command(aliases=["purge"])
    async def prune(self, ctx, count: int, channel: discord.TextChannel = None):
        """ Prune a channel. """
        if count > 100:
            await ctx.send("Sorry, you cannot purge more than 100 messages at a time.")
        else:
            count += 1
            if channel is None:
                channel = ctx.channel
            deleted = await channel.purge(limit=count, check=is_pinned)
            await channel.send(
                f"Deleted {len(deleted)} messages from {channel.mention}", delete_after=5
            )


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Cleanup(bot))
