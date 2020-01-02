""" Core cog. """
from . import BaseCog

class Core(BaseCog):
    """ The core cog for RoboHz. """
    banlist = set()
    game = "r!help for help, fuckers."
    config_attrs = "banlist", "game"

    async def bot_check(self, ctx: commands.Context):
        """ Check for bot readiness. """
        if not self.bot.is_ready():
            # Raise thing.
        if not 