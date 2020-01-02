import discord
from discord.ext import commands
import re
from .errors import BadGameArgument


__all__ = (
    'CommandConverter',
    'DiceRollConverter',
    'AliasedRoleConverter',
    'BoardCoords',
    'EspeakParamsConverter'
)


class CommandConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument):
        cmd = ctx.bot.get_command(argument)
        if cmd is None:
            raise commands.CommandNotFound(argument)
        return cmd


class DiceRollConverter(commands.Converter):
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
    async def convert(self, ctx, argument):
        role_id = ctx.cog.roles.get(
            str(ctx.guild.id), {}).get(argument.lower())
        if role_id is None:
            raise commands.BadArgument(
                f'No alias "{argument}" has been registered to a role')
        return discord.utils.get(ctx.guild.roles, id=role_id)


class BoardCoords(commands.Converter):
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
                y = ord(argument[0]) - 0x60
                x = int(argument[1])
            else:
                y, x = map(int, argument.split())
            assert self.minx <= x <= self.maxx and self.miny <= y <= self.maxy
            return x - 1, y - 1
        except (ValueError, AssertionError) as e:
            raise BadGameArgument from e
