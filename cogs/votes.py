""" Voting Cog. """

from heapq import nlargest
import asyncio

import discord
from discord.ext import commands


def to_emoji(char):
    base = 0x1f1e6
    return chr(base + char)

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
    @commands.guild_only()
    async def poll(self, ctx, *, question):
        """Interactively creates a poll with the following question.
        To vote, use reactions!
        """

        # a list of messages to delete when we're all done
        messages = [ctx.message]
        answers = []

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel and len(msg.content) <= 100

        for i in range(20):
            messages.append(await ctx.send(f'Say poll option or {ctx.prefix}cancel to publish poll.'))

            try:
                entry = await self.bot.wait_for('message', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                break

            messages.append(entry)
            if entry.clean_content.startswith(f'{ctx.prefix}cancel'):
                break

            answers.append((to_emoji(i), entry.clean_content))

        try:
            await ctx.channel.delete_messages(messages)
        except:
            pass  # oh well

        answer = '\n'.join(
            f'{keycap}: {content}' for keycap, content in answers)
        actual_poll = await ctx.send(f'{ctx.author} asks: {question}\n\n{answer}')
        for emoji, _ in answers:
            await actual_poll.add_reaction(emoji)

    @poll.error
    async def poll_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send('Missing the question.')


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Voting(bot))
