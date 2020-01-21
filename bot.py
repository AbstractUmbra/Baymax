
""" Define bot here. """
from argparse import (
    ArgumentParser
)
from asyncio import (
    get_event_loop
)
from collections import (
    Counter
)
from io import (
    StringIO
)
from glob import (
    glob
)
import logging
from os import (
    path
)
from sys import (
    stderr
)
from traceback import (
    format_exc,
    format_exception
)
from aiohttp import (
    ClientResponseError,
    ClientSession
)
import discord
from discord.ext import commands

from utils.logging_mixin import LoggingMixin
from utils.mystbin import mystbin
from utils.settings import Settings
from utils.sql import connect
from utils.version import version


__all__ = ('RoboHz',)
__dir__ = path.dirname(__file__) or "."
__version__ = version


async def _command_prefix(bot, message):
    if message.guild is None:
        return ''
    if message.guild.id not in bot.guild_prefixes:
        async with bot.sql as sql:
            bot.guild_prefixes[message.guild.id] = await sql.get_prefix(bot, message)
    return bot.guild_prefixes[message.guild.id]


class RoboHz(LoggingMixin, commands.Bot):
    """ My actual Robo boy. """
    filter_excs = commands.CommandNotFound, commands.CheckFailure
    handle_excs = commands.UserInputError

    def __init__(self, settings_file, logfile, sqlfile, *, loop=None):
        # Load settings
        loop = get_event_loop() if loop is None else loop
        self.settings = Settings(settings_file, loop=loop)
        disabled_cogs = self.settings.disabled_cogs
        super().__init__(_command_prefix, case_insensitive=True,
                         loop=loop, activity=discord.Game(self.settings.game))
        self.guild_prefixes = {}
        self._sql = sqlfile
        self.session = ClientSession(loop=self.loop)
        self.spam_control = commands.CooldownMapping.from_cooldown(
            10, 12.0, commands.BucketType.user)

        # Set up logger
        self.logger.setLevel(
            logging.DEBUG if self.settings.debug else logging.INFO)
        handler = logging.FileHandler(logfile, mode='w')
        fmt = logging.Formatter(
            '%(asctime)s (PID:%(process)s) - %(levelname)s - %(message)s')
        handler.setFormatter(fmt)
        self.logger.addHandler(handler)

        # Load cogs
        dname = path.dirname(__file__) or '.'
        for cogfile in glob(f'{dname}/cogs/*.py'):
            if path.isfile(cogfile) and '__init__' not in cogfile:
                cogname = path.splitext(path.basename(cogfile))[0]
                if cogname not in disabled_cogs:
                    extn = f'cogs.{cogname}'
                    try:
                        self.load_extension(extn)
                    except commands.ExtensionNotFound:
                        self.logger.error(f"Unable to find cog: \"{cogname}\"")
                    except commands.ExtensionFailed:
                        self.logger.warning(
                            f"Failed to load cog: \"{cogname}\"")
                    else:
                        self.logger.info(f"Loaded cog: \"{cogname}\"")
                else:
                    self.logger.info(f"Skipping disabled cog: \"{cogname}\"")

        async def init_sql():
            async with self.sql as sql:
                await sql.db_init(self)

        self.loop.create_task(init_sql())

        # Reboot handler
        self.reboot_after = True

        # Alive
        self._alive_since = None

    @property
    def sql(self):
        """ Init my SQL pls. """
        return connect(self._sql, loop=self.loop)

    def run(self):
        """ Run the bot boy. """
        self.logger.info('Starting bot')
        token = self.settings.token
        super().run(token)

    async def logout(self):
        """ Close the bot boy. """
        self.logger.info('Logout request received')
        await self.close()

    @property
    def owner(self):
        """ Owner, me! """
        return self.get_user(self.owner_id)

    @property
    def exc_channel(self):
        """ Exception channel. """
        try:
            return self.get_channel(self.settings.exc_channel)
        except AttributeError:
            return None

    @property
    def command_error_emoji(self):
        """ Command error emoji. """
        return discord.utils.get(self.emojis, name=self.settings.error_emoji)


def main():
    """The main function that runs the bot. """
    parser = ArgumentParser()
    parser.add_argument('--settings', default='config/settings.json')
    parser.add_argument('--logfile', default='robobot.log')
    parser.add_argument('--sqlfile', default='data/db.sql')
    parser.add_argument('--version', action='store_true')
    args = parser.parse_args()
    if args.version:
        print(f'{path.basename(path.dirname(__file__))} v{version}')
        return

    bot = RoboHz(args.settings, args.logfile, args.sqlfile)

    @bot.event
    async def on_ready():
        invite_url = "https://discordapp.com/api/oauth2/authorize?client_id=^ID^&permissions=0&scope=bot".replace(
            "^ID^", str(bot.user.id))
        print(f'Logged in as {bot.user}: {bot.user.id}')
        print(f"Use this URL to invite your bot to guilds:-\n"
              f"\t{invite_url}")

    async def send_tb(traceb):
        channel = bot.exc_channel
        if channel is None:
            return
        if len(traceb) < 1990:
            await channel.send(f'```{traceb}```')
        else:
            try:
                url = await mystbin(traceb)
            except ClientResponseError:
                await channel.send('An error has occurred',
                                   file=discord.File(StringIO(traceb)),
                                   delete_after=60)
            else:
                await channel.send(f'An error has occurred: {url}', delete_after=60)

    @bot.event
    async def on_command_completion(ctx):
        """ When a command successfully completes. """
        if ctx.author.id != bot.owner_id:
            await ctx.message.delete(delay=5)

    @bot.event
    async def on_error(event, *args, **kwargs):
        err = format_exc()
        content = f'Ignoring exception in {event}\n{err})'
        print(content, file=stderr)
        await send_tb(content)

    async def handle_command_error(ctx: commands.Context, exc: RoboHz.handle_excs):
        if isinstance(exc, commands.MissingRequiredArgument):
            msg = f'`{exc.param}` is a required argument that is missing.'
        elif isinstance(exc, commands.TooManyArguments):
            msg = f'Too many arguments for `{ctx.command}`'
        elif isinstance(exc, (commands.BadArgument,
                              commands.BadUnionArgument,
                              commands.ArgumentParsingError)):
            msg = f'Got a bad argument for `{ctx.command}`'
        else:
            msg = f'An unhandled error {exc} has occurred'
        await ctx.send(f'{msg} {bot.command_error_emoji}', delete_after=10)

    @bot.event
    async def on_command_error(ctx: commands.Context, exc: Exception):
        if isinstance(exc, RoboHz.filter_excs):
            return

        if isinstance(exc, RoboHz.handle_excs):
            return await handle_command_error(ctx, exc)

        bot.log_tb(ctx, exc)
        exc = getattr(exc, 'original', exc)
        lines = ''.join(format_exception(
            exc.__class__, exc, exc.__traceback__))
        print(lines)
        lines = f'Ignoring exception in command {ctx.command}:\n{lines}'
        await send_tb(lines)

    bot.run()


if __name__ == '__main__':
    main()
