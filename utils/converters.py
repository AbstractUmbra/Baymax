""" Converters utils. """
import re

import discord
from discord.ext import commands

from .errors import BadGameArgument


__all__ = (
    'CommandConverter',
    'DiceRollConverter',
    'AliasedRoleConverter',
    'BoardCoords',
)


class CommandConverter(commands.Converter):
    """ Create a quick command converter. """
    async def convert(self, ctx: commands.Context, argument):
        cmd = ctx.bot.get_command(argument)
        if cmd is None:
            raise commands.CommandNotFound(argument)
        return cmd


class DiceRollConverter(commands.Converter):
    """ Create a quick dice roll converter. """
    _pattern = re.compile(r'(?P<count>\d+)?(d(?P<sides>\d+))?')

    async def convert(self, ctx, argument):
        match = self._pattern.match(argument)
        if match is None:
            raise ValueError
        count = int(match['count'] or 1)
        sides = int(match['sides'] or 6)
        assert 1 <= count <= 200 and 2 <= sides <= 100
        return count, sides


class AliasedRoleConverter(commands.Converter):
    """ Create a quick aliased role converter. """
    async def convert(self, ctx, argument):
        role_id = ctx.cog.roles.get(
            str(ctx.guild.id), {}).get(argument.lower())
        if role_id is None:
            raise commands.BadArgument(
                f'No alias "{argument}" has been registered to a role')
        return discord.utils.get(ctx.guild.roles, id=role_id)


class BoardCoords(commands.Converter):
    """ Create a quick board converter. """
    def __init__(self, minx=1, maxx=5, miny=1, maxy=5):
        super().__init__()
        self.minx = minx
        self.maxx = maxx
        self.miny = miny
        self.maxy = maxy

    async def convert(self, ctx, argument):
        if isinstance(argument, tuple):
            return argument
        try:
            argument = argument.lower()
            if argument.startswith(tuple('abcde')):
                yaxis = ord(argument[0]) - 0x60
                xaxis = int(argument[1])
            else:
                yaxis, xaxis = map(int, argument.split())
            assert self.minx <= xaxis <= self.maxx and self.miny <= yaxis <= self.maxy
            return xaxis - 1, yaxis - 1
        except (ValueError, AssertionError) as err:
            raise BadGameArgument from err
