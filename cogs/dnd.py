"""
The MIT License (MIT)

Copyright (c) 2020 AbstractUmbra

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
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

from datetime import datetime
from random import randint

import discord
from discord.ext import commands


class DND(commands.Cog):
    """ Do not disturb... Jk, it's Dungeons and Dragons. """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, ctx, diceroll):
        """ Dicerolls. """
        roll_counts = []
        str_roll_counts = []
        rolls, sides = diceroll.lower().split('d')
        rolls = int(rolls)
        sides = int(sides)
        if rolls > 20:
            return await ctx.send(f"There no way you're doing {rolls} rolls!\nPlease roll 20 times or less.")
        for _ in range(1, (int(rolls) + 1)):
            roll_counts.append(randint(1, int(sides)))
        for dice_roll in roll_counts:
            if int(sides) == 20 and dice_roll == 20:
                str_roll_counts.append("*20*")
            elif dice_roll == 1:
                str_roll_counts.append("*1*")
            else:
                str_roll_counts.append(str(dice_roll))
        roll_embed = discord.Embed(
            title=f"Dice roll: {str(diceroll)}", colour=discord.Colour(randint(0, 0xFFFFFF)))
        roll_embed.set_author(name=ctx.author.display_name,
                              icon_url=ctx.author.avatar_url)
        roll_embed.timestamp = datetime.utcnow()
        roll_embed.add_field(name="Rolls", value=", ".join(
            [roll for roll in str_roll_counts]))
        roll_embed.add_field(name="Total", value=str(sum(roll_counts)))
        await ctx.send(embed=roll_embed)


def setup(bot):
    """ Cog entrypoint. """
    bot.add_cog(DND(bot))
