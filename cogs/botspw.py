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

import json
import logging
import typing

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

DISCORD_BOTS_API = 'https://discord.bots.gg/api/v1'


class BotsPW(commands.Cog):
    """Cog for updating bots.discord.pw bot information."""

    def __init__(self, bot):
        self.bot = bot

    async def update(self):
        guild_count = len(self.bot.guilds)

        payload = json.dumps({
            'guildCount': guild_count,
            'shardCount': len(self.bot.shards)
        })

        headers = {
            'authorization': self.bot.bots_key,
            'content-type': 'application/json'
        }

        url = f'{DISCORD_BOTS_API}/bots/{self.bot.user.id}/stats'
        async with self.bot.session.post(url, data=payload, headers=headers) as resp:
            log.info(f'DBots statistics returned {resp.status} for {payload}')

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.update()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.update()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.update()

    @commands.command()
    async def dbl(self, ctx, target_bot: typing.Union[discord.Member, int]):
        """ Get a bot's info from DBL. """


def setup(bot):
    bot.add_cog(BotsPW(bot))
