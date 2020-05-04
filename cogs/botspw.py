import json
import logging

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


def setup(bot):
    bot.add_cog(BotsPW(bot))
