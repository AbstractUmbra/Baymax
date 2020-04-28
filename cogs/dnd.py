"""
Robo-Hz Discord Bot
Copyright (C) 2020 64Hz

Robo-Hz is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Robo-Hz is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with Robo-Hz. If not, see <https://www.gnu.org/licenses/>.
"""

from datetime import datetime
from random import choice, randint

import discord
from discord.ext import commands


class DND(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, ctx, diceroll):
        """ Dicerolls. """
        roll_counts = []
        str_roll_counts = []
        rolls, sides = diceroll.lower().split('d')
        if rolls > 20:
            return await ctx.send(f"There no way you're doing {rolls} rolls!\nPlease roll 20 times or less.")
        for roll in range(1, int(rolls) + 1):
            roll_counts.append(randint(1, int(sides)))
        for x in roll_counts:
            if int(sides) == 20 and x == 20:
                str_roll_counts.append("*20*")
            elif x == 1:
                str_roll_counts.append("*1*")
            else:
                str_roll_counts.append(str(x))
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
    bot.add_cog(DND(bot))
