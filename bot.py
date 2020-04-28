""" RoboHz - my love. """
from collections import Counter, deque
import datetime
import logging
import json
import sys
import traceback

import aiohttp
import discord
from discord.ext import commands

from utils import context
from utils.config import Config
import config


DESCRIPTION = """
Hello! I am a bot written by Revan#0640 to provide some nice utilities.
"""

LOGGER = logging.getLogger(__name__)

COGS = (
    'jishaku',
    'cogs.admin',
    'cogs.autoroles',
    'cogs.buttons',
    'cogs.config',
    'cogs.dnd',
    'cogs.emoji',
    'cogs.funhouse',
    'cogs.google',
    'cogs.memes',
    'cogs.meta',
    'cogs.mod',
    'cogs.reminders',
    'cogs.specialist',
    'cogs.stats',
    'cogs.tags',
    'cogs.twitch',
)


def _prefix_callable(bot, msg):
    user_id = bot.user.id
    base = [f'<@!{user_id}> ', f'<@{user_id}> ']
    if msg.guild is None:
        base.append('!')
        base.append('?')
    else:
        base.extend(bot.prefixes.get(msg.guild.id, ['?', '!']))
    return base


class RoboHz(commands.AutoShardedBot):
    """ The actual robot himself! """

    def __init__(self):
        super().__init__(command_prefix=_prefix_callable,
                         description=DESCRIPTION,
                         pm_help=None,
                         help_attrs=dict(hidden=True),
                         heartbeat_timeout=150.0,
                         activity=discord.Game(
                             name="r!help for help, fuckers."),
                         status=discord.Status.online)

        self.client_id = config.client_id
        self.session = aiohttp.ClientSession(loop=self.loop)

        self._prev_events = deque(maxlen=10)

        # guild_id: list
        self.prefixes = Config('prefixes.json')

        # guild_id and user_id mapped to True
        # these are users and guilds globally blacklisted
        # from using the bot
        self.blacklist = Config('blacklist.json')

        # in case of even further spam, add a cooldown mapping
        # for people who excessively spam commands
        self.spam_control = commands.CooldownMapping.from_cooldown(
            10, 12.0, commands.BucketType.user)

        # A counter to auto-ban frequent spammers
        # Triggering the rate limit 5 times in a row will auto-ban the user from the bot.
        self._auto_spam_count = Counter()

        for extension in COGS:
            try:
                self.load_extension(extension)
            except:
                print(
                    f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

    async def on_socket_response(self, msg):
        """ Websocket responses. """
        self._prev_events.append(msg)

    async def on_command_error(self, ctx, error):
        """ When a command errors out. """
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
                traceback.print_tb(original.__traceback__)
                print(f'{original.__class__.__name__}: {original}',
                      file=sys.stderr)
        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.send(error)

    def get_guild_prefixes(self, guild, *, local_inject=_prefix_callable):
        """ Get prefixes per guild. """
        proxy_msg = discord.Object(id=None)
        proxy_msg.guild = guild
        return local_inject(self, proxy_msg)

    def get_raw_guild_prefixes(self, guild_id):
        """ The raw prefixes. """
        return self.prefixes.get(guild_id, ['r!', '^'])

    async def set_guild_prefixes(self, guild, prefixes):
        """ Set the prefixes. """
        if not prefixes:
            await self.prefixes.put(guild.id, [])
        elif len(prefixes) > 10:
            raise RuntimeError('Cannot have more than 10 custom prefixes.')
        else:
            await self.prefixes.put(guild.id, sorted(set(prefixes), reverse=True))

    async def add_to_blacklist(self, object_id):
        """ Add object to blacklist. """
        await self.blacklist.put(object_id, True)

    async def remove_from_blacklist(self, object_id):
        """ Remove object from blacklist. """
        try:
            await self.blacklist.remove(object_id)
        except KeyError:
            pass

    async def on_ready(self):
        """ When the websocket reports ready. """
        if not hasattr(self, "uptime"):
            self.uptime = datetime.datetime.utcnow()

        print(f'Ready: {self.user} (ID: {self.user.id})')

    async def on_resumed(self):
        """ When the websocket resumes a connection. """
        print('Resumed...')

    @property
    def stat_webhook(self):
        """ Get webhook stats. """
        wh_id, wh_token = self.config.stat_webhook
        hook = discord.Webhook.partial(
            id=wh_id, token=wh_token, adapter=discord.AsyncWebhookAdapter(self.session))
        return hook

    def log_spammer(self, ctx, message, retry_after, *, autoblock=False):
        """ Deals with events that spam the log. """
        guild_name = getattr(ctx.guild, 'name', 'No Guild (DMs)')
        guild_id = getattr(ctx.guild, 'id', None)
        fmt = 'User %s (ID %s) in guild %r (ID %s) spamming, retry_after: %.2fs'
        LOGGER.warning(fmt, message.author, message.author.id,
                       guild_name, guild_id, retry_after)
        if not autoblock:
            return

        webhook = self.stat_webhook
        embed = discord.Embed(title='Auto-blocked Member', colour=0xDDA453)
        embed.add_field(
            name='Member', value=f'{message.author} (ID: {message.author.id})', inline=False)
        embed.add_field(name='Guild Info',
                        value=f'{guild_name} (ID: {guild_id})', inline=False)
        embed.add_field(
            name='Channel Info', value=f'{message.channel} (ID: {message.channel.id}', inline=False)
        embed.timestamp = datetime.datetime.utcnow()
        return webhook.send(embed=embed)

    async def process_commands(self, message):
        """ Bot's process command override. """
        ctx = await self.get_context(message, cls=context.Context)

        if ctx.command is None:
            return

        if ctx.author.id in self.blacklist:
            return

        if ctx.guild is not None and ctx.guild.id in self.blacklist:
            return

        bucket = self.spam_control.get_bucket(message)
        current = message.created_at.replace(
            tzinfo=datetime.timezone.utc).timestamp()
        retry_after = bucket.update_rate_limit(current)
        author_id = message.author.id
        if retry_after and author_id != self.owner_id:
            self._auto_spam_count[author_id] += 1
            if self._auto_spam_count[author_id] >= 5:
                await self.add_to_blacklist(author_id)
                del self._auto_spam_count[author_id]
                await self.log_spammer(ctx, message, retry_after, autoblock=True)
            else:
                self.log_spammer(ctx, message, retry_after)
            return
        else:
            self._auto_spam_count.pop(author_id, None)

        try:
            await self.invoke(ctx)
        finally:
            # Just in case we have any outstanding DB connections
            await ctx.release()

    async def on_message(self, message):
        """ Fires when a message is received. """
        if message.author.bot:
            return
        await self.process_commands(message)

    async def on_guild_join(self, guild):
        """ When the bot joins a guild. """
        if guild.id in self.blacklist:
            await guild.leave()

    async def close(self):
        """ When the bot closes. """
        await super().close()
        await self.session.close()

    def run(self):
        """ Run my roboboy please. """
        try:
            super().run(config.token, reconnect=True)
        finally:
            with open('prev_events.log', 'w', encoding='utf-8') as file_path:
                for data in self._prev_events:
                    try:
                        last_log = json.dumps(
                            data, ensure_ascii=True, indent=4)
                    except:
                        file_path.write(f'{data}\n')
                    else:
                        file_path.write(f'{last_log}\n')

    @property
    def config(self):
        """ Bot's config. """
        return __import__('config')
