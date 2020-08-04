"""
This utility and all contents are responsibly sourced from
RoboDanny discord bot and author
(https://github.com/Rapptz) | (https://github.com/Rapptz/RoboDanny)
RoboDanny licensing below:

The MIT License(MIT)

Copyright(c) 2015 Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files(the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import random as rng
from collections import Counter
from typing import Optional

from discord.ext import commands

from utils.formats import plural


class RNG(commands.Cog):
    """Utilities that provide pseudo-RNG."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True)
    async def random(self, ctx):
        """Displays a random thing you request."""
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Incorrect random subcommand passed. Try {ctx.prefix}help random')

    @random.command()
    async def tag(self, ctx):
        """Displays a random tag.

        A tag showing up in this does not get its usage count increased.
        """
        tags = self.bot.get_cog('Tags')
        if tags is None:
            return await ctx.send('Tag commands currently disabled.')

        tag = await tags.get_random_tag(ctx.guild, connection=ctx.db)
        if tag is None:
            return await ctx.send('This server has no tags.')

        await ctx.send(f'Random tag found: {tag["name"]}\n{tag["content"]}')

    @random.command()
    async def mode(self, ctx):
        """Displays a random Splatoon mode."""
        mode = rng.choice(['Turf War', 'Splat Zones',
                           'Clam Blitz', 'Rainmaker', 'Tower Control'])
        await ctx.send(mode)

    @random.command()
    async def number(self, ctx, minimum=0, maximum=100):
        """Displays a random number within an optional range.

        The minimum must be smaller than the maximum and the maximum number
        accepted is 1000.
        """

        maximum = min(maximum, 1000)
        if minimum >= maximum:
            await ctx.send('Maximum is smaller than minimum.')
            return

        await ctx.send(rng.randint(minimum, maximum))

    @commands.command()
    async def choose(self, ctx, *choices: commands.clean_content):
        """Chooses between multiple choices.

        To denote multiple choices, you should use double quotes.
        """
        if len(choices) < 2:
            return await ctx.send('Not enough choices to pick from.')

        await ctx.send(rng.choice(choices))

    @commands.command()
    async def choosebestof(self, ctx, times: Optional[int], *choices: commands.clean_content):
        """Chooses between multiple choices N times.

        To denote multiple choices, you should use double quotes.

        You can only choose up to 10001 times and only the top 10 results are shown.
        """
        if len(choices) < 2:
            return await ctx.send('Not enough choices to pick from.')

        if times is None:
            times = (len(choices) ** 2) + 1

        times = min(10001, max(1, times))
        results = Counter(rng.choice(choices) for i in range(times))
        builder = []
        if len(results) > 10:
            builder.append('Only showing top 10 results...')
        for index, (elem, count) in enumerate(results.most_common(10), start=1):
            builder.append(
                f'{index}. {elem} ({plural(count):time}, {count/times:.2%})')

        await ctx.send('\n'.join(builder))


def setup(bot):
    bot.add_cog(RNG(bot))