""" Initting cogs. """
from collections import (
    defaultdict
)
from typing import (
    Tuple
)

from discord.ext import commands

from utils.logging_mixin import LoggingMixin


__all__ = ('BaseCog',)


class BaseCog(LoggingMixin, commands.Cog):
    """
    Base class for all cog files.  Inherits :class:LoggingMixin
    __init__ params:
        bot: RoboHz - The instance of the bot.

    Attributes:
        config_attrs: tuple - Names of attributes to fetch from the bot's
        settings.  When subclassing BaseCog, define this at the class level.
    """
    config_attrs: Tuple[str] = tuple()

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def init_db(self, sql):
        """Override this"""

    async def fetch(self):
        """
        Loads local attributes from the bot's settings
        """
        self.log_debug(f'Fetching {self.__class__.__name__}')
        async with self.bot.settings:
            for attr in self.config_attrs:
                self.log_debug(attr)
                try:
                    val = getattr(self.bot.settings, attr)
                except AttributeError:
                    continue
                if isinstance(val, list):
                    val = set(val)
                old_attr = getattr(self, attr)
                if isinstance(old_attr, defaultdict):
                    old_attr.clear()
                    old_attr.update(val)
                    val = old_attr
                setattr(self, attr, val)

    async def cog_before_invoke(self, ctx):
        await self.fetch()

    async def commit(self):
        """
        Commits local attributes to the bot's settings file
        """
        async with self.bot.settings as settings:
            for attr in self.config_attrs:
                self.log_debug(attr)
                val = getattr(self, attr)
                if isinstance(val, set):
                    val = list(val)
                setattr(settings, attr, val)

    async def cog_after_invoke(self, ctx):
        await self.commit()
