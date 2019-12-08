""" Voting Cog. """

from heapq import nlargest

import discord
from discord.ext import commands


class Voting(commands.Cog):
    """ Voting cog. """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def votecount(self, ctx, channel: discord.TextChannel = None):
        """ Count the reactions in the channel to get a 'vote list'. """
        if channel is None:
            channel = ctx.channel
        count = {}
        total = discord.Embed(title="**Vote Count**",
                              color=0x00ff00)
        total.set_author(name=self.bot.user.name)
        total.set_thumbnail(url=self.bot.user.avatar_url)
        async for msg in channel.history(limit=50):
            if not msg.reactions:
                #count[msg.content] = None
                continue
            if msg.author.id != self.bot.user.id and not msg.content.startswith("^"):
                for reaction in msg.reactions:
                    if reaction.count is not None:
                        count[msg.content] = reaction.count
                total.add_field(
                    name=f"{msg.content}",
                    value=f"Votes: {count.get(msg.content)}",
                    inline=True)
        count_list = nlargest(5, count, key=count.get)
        count_string = "\n".join(item for item in count_list)
        total.add_field(name="**Highest voted**",
                        value=f"**{count_string}**", inline=True)
        to_pin = await channel.send(embed=total)
        await to_pin.pin()

    @commands.command(hidden=True)
    async def new_votecount(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel
        async for msg in channel.history(limit=50):
            

def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Voting(bot))
