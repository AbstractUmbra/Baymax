""" SQL Util. """

from asyncio import (
    get_event_loop
)
from glob import glob
from shutil import (
    copy as shcopy
)
from sqlite3 import (
    connect as sqconnect
)
import time

import aiosqlite

class Sql(aiosqlite.Connection):
    default_bag = (
        ('happily jumped into the bag!',),
        ('reluctantly clambored into the bag.',),
        ('turned away!',),
        ('let out a cry in protest!',)
    )

    def __init__(self, database, *, loop=None, **kwargs):
        def connector():
            return sqconnect(database, **kwargs)

        loop = loop or get_event_loop()
        super().__init__(connector, loop=loop)
        self.database = database

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.commit()
        await super().__aexit__(exc_type, exc_val, exc_tb)

    async def db_init(self, bot):
        for cog in bot.cogs.values():
            await cog.init_db(self)

    async def db_clear(self):
        await self.execute("drop table if exists prefixes")

    async def backup_db(self):
        curtime = int(time.time())
        dbbak = f'{self.database}.{curtime:d}.bak'
        return await self._loop.run_in_executor(None, shcopy, self.database, dbbak)

    async def restore_db(self, idx):
        files = glob(f'{self.database}.*.bak')
        if not files:
            return None
        files.sort(reverse=True)
        dbbak = files[(idx - 1) % len(files)]
        await self._loop.run_in_executor(shcopy, dbbak, self.database)
        return dbbak

    async def get_prefix(self, bot, message):
        cur = await self.execute("select prefix from prefixes where guild = ?", (message.guild.id,))
        try:
            prefix, = await cur.fetchone()
        except TypeError:
            await self.set_prefix(message.guild, prefix=bot.settings.prefix)
            prefix = bot.settings.prefix
        return prefix

    async def set_prefix(self, guild, prefix='r!'):
        await self.execute(
            "replace into prefixes (guild, prefix) values (?, ?)", (guild.id, prefix))


def connect(database, *, loop=None, **kwargs):
    """Create and return a connection proxy to the sqlite database."""
    return Sql(database, loop=loop, **kwargs)
