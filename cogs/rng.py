import random
import re
from collections import Counter
from typing import Dict, List, Optional, Union

import discord
from discord.ext import commands
from utils.formats import plural, to_codeblock

DICE_RE = re.compile(r"^(?P<rolls>\d+)[d|D](?P<die>\d+)$")


class DiceRoll(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Dict[str, Union[int, List[int]]]:
        search = DICE_RE.fullmatch(argument)
        if not search:
            raise commands.BadArgument(
                "Dice roll doesn't seem valid, please use it in the format of `2d20`."
            )

        search = search.groupdict()
        rolls = int(search["rolls"])
        die = int(search["die"])

        if not (0 < rolls < 15 or 0 < die < 1000):
            raise commands.BadArgument(
                f"The Die or amount of Rolls cannot be less than 1 or exceed 15/1000. Roll `{argument}` is invalid."
            )

        totals = random.choices(range(1, die), k=rolls)

        return {"rolls": rolls, "die": die, "totals": totals}


class RNG(commands.Cog):
    """Utilities that provide pseudo-RNG."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True)
    async def random(self, ctx):
        """Displays a random thing you request."""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                f"Incorrect random subcommand passed. Try {ctx.prefix}help random"
            )

    @random.command()
    async def tag(self, ctx):
        """Displays a random tag.

        A tag showing up in this does not get its usage count increased.
        """
        tags = self.bot.get_cog("Tags")
        if tags is None:
            return await ctx.send("Tag commands currently disabled.")

        tag = await tags.get_random_tag(ctx.guild, connection=ctx.db)
        if tag is None:
            return await ctx.send("This server has no tags.")

        await ctx.send(f'Random tag found: {tag["name"]}\n{tag["content"]}')

    @random.command()
    async def number(self, ctx, minimum=0, maximum=100):
        """Displays a random number within an optional range.

        The minimum must be smaller than the maximum and the maximum number
        accepted is 1000.
        """

        maximum = min(maximum, 1000)
        if minimum >= maximum:
            await ctx.send("Maximum is smaller than minimum.")
            return

        await ctx.send(random.randint(minimum, maximum))

    @commands.command()
    async def choose(self, ctx, *choices: commands.clean_content):
        """Chooses between multiple choices.

        To denote multiple choices, you should use double quotes.
        """
        if len(choices) < 2:
            return await ctx.send("Not enough choices to pick from.")

        await ctx.send(random.choice(choices))

    @commands.command()
    async def choosebestof(
        self, ctx, times: Optional[int], *choices: commands.clean_content
    ):
        """Chooses between multiple choices N times.

        To denote multiple choices, you should use double quotes.

        You can only choose up to 10001 times and only the top 10 results are shown.
        """
        if len(choices) < 2:
            return await ctx.send("Not enough choices to pick from.")

        if times is None:
            times = (len(choices) ** 2) + 1

        times = min(10001, max(1, times))
        results = Counter(random.choice(choices) for i in range(times))
        builder = []
        if len(results) > 10:
            builder.append("Only showing top 10 results...")
        for index, (elem, count) in enumerate(results.most_common(10), start=1):
            builder.append(f"{index}. {elem} ({plural(count):time}, {count/times:.2%})")

        await ctx.send("\n".join(builder))

    @commands.command()
    async def roll(self, ctx: commands.Context, *dice: DiceRoll):
        """ Roll DnD die! """
        if len(dice) >= 25:
            return await ctx.send("No more than 25 rolls per invoke, please.")

        embed = discord.Embed(title="Rolls", colour=discord.Colour.random())

        for i in dice:
            fmt = ""
            total = i["totals"]
            die = i["die"]
            rolls = i["rolls"]
            # split = [total[x:x+5] for x in range(0, len(total), 5)]

            builder = []
            roll_sum = 0
            for count, roll in enumerate(total, start=1):
                builder.append(f"{count}: {roll}")
                roll_sum += roll
            fmt += "\n".join(builder)
            fmt += f"\nSum: {roll_sum}\n"

            embed.add_field(
                name=f"{rolls}d{die}", value=to_codeblock(fmt, language="prolog")
            )

        # embed.description = to_codeblock(fmt, language="prolog")
        embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar_url)

        await ctx.send(embed=embed)

    @roll.error
    async def roll_error(self, ctx: commands.Context, error: BaseException):
        error = getattr(error, "original", error)

        if isinstance(error, commands.BadArgument):
            return await ctx.send(error, delete_after=5)


def setup(bot):
    bot.add_cog(RNG(bot))
