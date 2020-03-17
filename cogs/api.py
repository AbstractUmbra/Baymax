""" API Stuff. -Code- """
import io
import re
import os
import zlib

import discord
from discord.ext import commands
import lxml.etree as etree

from utils import db, fuzzy, cache, time


def can_use_block():
    """ Those that can use the block func. """
    def predicate(ctx):
        if ctx.guild is None:
            return False

        guild_id = ctx.guild.id
        if guild_id == 174702278673039360:
            return ctx.channel.permissions_for(ctx.author).manage_roles
        return False
    return commands.check(predicate)


class Feeds(db.Table):
    """ Subclasses table to do shit. """
    id = db.PrimaryKeyColumn()
    channel_id = db.Column(db.Integer(big=True))
    role_id = db.Column(db.Integer(big=True))
    name = db.Column(db.String)


class RTFM(db.Table):
    """ Subclasses table to do shit. """
    id = db.PrimaryKeyColumn()
    user_id = db.Column(db.Integer(big=True), unique=True, index=True)
    count = db.Column(db.Integer, default=1)


class SphinxObjectFileReader:
    """ To grab Sphinx objects. """
    # Inspired by Sphinx's InventoryFileReader
    BUFSIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = io.BytesIO(buffer)

    def readline(self):
        """ Reads a line from a Sphinx object. """
        return self.stream.readline().decode('utf-8')

    def skipline(self):
        """ Skips a line. """
        self.stream.readline()

    def read_compressed_chunks(self):
        """ Chunks can come in a zlib comp. """
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
            if not chunk:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self):
        """ Read the zlib comp lines. """
        buf = b''
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b'\n')
            while pos != -1:
                yield buf[:pos].decode('utf-8')
                buf = buf[pos + 1:]
                pos = buf.find(b'\n')


class BotUser(commands.Converter):
    """ D.py converter for BotUsers. """
    async def convert(self, ctx, argument):
        if not argument.isdigit():
            raise commands.BadArgument('Not a valid bot user ID.')
        try:
            user = await ctx.bot.fetch_user(argument)
        except discord.NotFound:
            raise commands.BadArgument('Bot user not found (404).')
        except discord.HTTPException as err:
            raise commands.BadArgument(f'Error fetching bot user: {err}')
        else:
            if not user.bot:
                raise commands.BadArgument('This is not a bot.')
            return user


class API(commands.Cog):
    """Discord API exclusive things."""

    def __init__(self, bot):
        self.bot = bot
        self.issue = re.compile(r'##(?P<number>[0-9]+)')
        self._recently_blocked = set()

    def parse_object_inv(self, stream, url):
        """ Parse object inventory. """
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result = {}

        # first line is version info
        inv_version = stream.readline().rstrip()

        if inv_version != '# Sphinx inventory version 2':
            raise RuntimeError('Invalid objects.inv file version.')

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]

        # next line says if it's a zlib header
        line = stream.readline()
        if 'zlib' not in line:
            raise RuntimeError(
                'Invalid objects.inv file, not z-lib compatible.')

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(
            r'(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)')
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, _, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(':')
            if directive == 'py:module' and name in result:
                # From the Sphinx Repository:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue

            # Most documentation pages have a label
            if directive == 'std:doc':
                subdirective = 'label'

            if location.endswith('$'):
                location = location[:-1] + name

            key = name if dispname == '-' else dispname
            prefix = f'{subdirective}:' if domain == 'std' else ''

            if projname == 'discord.py':
                key = key.replace('discord.ext.commands.',
                                  '').replace('discord.', '')

            result[f'{prefix}{key}'] = os.path.join(url, location)

        return result

    async def build_rtfm_lookup_table(self, page_types):
        """ Build the RTFM lookup table. """
        rtfm_cache = {}
        for key, page in page_types.items():
            async with self.bot.session.get(page + '/objects.inv') as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        'Cannot build rtfm lookup table, try again later.')

                stream = SphinxObjectFileReader(await resp.read())
                rtfm_cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = rtfm_cache

    async def do_rtfm(self, ctx, key, obj):
        """ Do the RTFM command. """
        page_types = {
            'latest': 'https://discordpy.readthedocs.io/en/latest',
            'latest-jp': 'https://discordpy.readthedocs.io/ja/latest',
            'python': 'https://docs.python.org/3',
            'python-jp': 'https://docs.python.org/ja/3',
        }

        if obj is None:
            await ctx.send(page_types[key])
            return

        if not hasattr(self, '_rtfm_cache'):
            await ctx.trigger_typing()
            await self.build_rtfm_lookup_table(page_types)

        obj = re.sub(
            r'^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)', r'\1', obj)

        if key.startswith('latest'):
            # point the abc.Messageable types properly:
            quirk = obj.lower()
            for name in dir(discord.abc.Messageable):
                if name[0] == '_':
                    continue
                if quirk == name:
                    obj = f'abc.Messageable.{name}'
                    break

        rtfm_cache = list(self._rtfm_cache[key].items())

        matches = fuzzy.finder(
            obj, rtfm_cache, key=lambda t: t[0], lazy=False)[:8]

        embed = discord.Embed(colour=discord.Colour.blurple())
        if not matches:
            return await ctx.send('Could not find anything. Sorry.')

        embed.description = '\n'.join(
            f'[`{key}`]({url})' for key, url in matches)
        await ctx.send(embed=embed)

    def transform_rtfm_language_key(self, ctx, prefix):
        """ Transform rtfm to language variants. """
        if ctx.guild is not None:
            if ctx.channel.id == 174702278673039360:
                return prefix + '-jp'
        return prefix

    @commands.group(aliases=['rtfd'], invoke_without_command=True)
    async def rtfm(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity.

        Events, objects, and functions are all supported through a
        a cruddy fuzzy algorithm.
        """
        key = self.transform_rtfm_language_key(ctx, 'latest')
        await self.do_rtfm(ctx, key, obj)

    @rtfm.command(name='jp')
    async def rtfm_jp(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity (Japanese)."""
        await self.do_rtfm(ctx, 'latest-jp', obj)

    @rtfm.command(name='python', aliases=['py'])
    async def rtfm_python(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a Python entity."""
        key = self.transform_rtfm_language_key(ctx, 'python')
        await self.do_rtfm(ctx, key, obj)

    @rtfm.command(name='py-jp', aliases=['py-ja'])
    async def rtfm_python_jp(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a Python entity (Japanese)."""
        await self.do_rtfm(ctx, 'python-jp', obj)

    async def _member_stats(self, ctx, member, total_uses):
        """ Grab my member starts. """
        embed = discord.Embed(title='RTFM Stats')
        embed.set_author(name=str(member), icon_url=member.avatar_url)

        query = 'SELECT count FROM rtfm WHERE user_id=$1;'
        record = await ctx.db.fetchrow(query, member.id)

        if record is None:
            count = 0
        else:
            count = record['count']

        embed.add_field(name='Uses', value=count)
        embed.add_field(name='Percentage',
                        value=f'{count/total_uses:.2%} out of {total_uses}')
        embed.colour = discord.Colour.blurple()
        await ctx.send(embed=embed)

    @rtfm.command()
    async def stats(self, ctx, *, member: discord.Member = None):
        """Tells you stats about the ?rtfm command."""
        query = 'SELECT SUM(count) AS total_uses FROM rtfm;'
        record = await ctx.db.fetchrow(query)
        total_uses = record['total_uses']

        if member is not None:
            return await self._member_stats(ctx, member, total_uses)

        query = 'SELECT user_id, count FROM rtfm ORDER BY count DESC LIMIT 10;'
        records = await ctx.db.fetch(query)

        output = []
        output.append(f'**Total uses**: {total_uses}')

        # first we get the most used users
        if records:
            output.append(f'**Top {len(records)} users**:')

            for rank, (user_id, count) in enumerate(records, 1):
                user = self.bot.get_user(user_id)
                if rank != 10:
                    output.append(f'{rank}\u20e3 {user}: {count}')
                else:
                    output.append(f'\N{KEYCAP TEN} {user}: {count}')

        await ctx.send('\n'.join(output))

    def library_name(self, channel):
        """ Library name quick convert. """
        # language_<name>
        name = channel.name
        index = name.find('_')
        if index != -1:
            name = name[index + 1:]
        return name.replace('-', '.')

    def get_block_channel(self, guild, channel):
        """ Get the active block channel. """
        if channel.id == 174702278673039360:
            return guild.get_channel(174702278673039360)
        return [channel]

    @commands.command()
    @can_use_block()
    async def block(self, ctx, *, member: discord.Member):
        """Blocks a user from your channel."""

        reason = f'Block by {ctx.author} (ID: {ctx.author.id})'

        channels = self.get_block_channel(ctx.guild, ctx.channel)

        try:
            for channel in channels:
                await channel.set_permissions(
                    member,
                    send_messages=False,
                    add_reactions=False,
                    reason=reason)
        except:
            await ctx.send('\N{THUMBS DOWN SIGN}')
        else:
            await ctx.send('\N{THUMBS UP SIGN}')

    @commands.command()
    @can_use_block()
    async def tempblock(self, ctx, duration: time.FutureTime, *, member: discord.Member):
        """Temporarily blocks a user from your channel.

        The duration can be a a short time form, e.g. 30d or a more human
        duration such as "until thursday at 3PM" or a more concrete time
        such as "2017-12-31".

        Note that times are in UTC.
        """

        reminder = self.bot.get_cog('Reminder')
        if reminder is None:
            return await ctx.send(
                'Sorry, this functionality is currently unavailable. Try again later?')

        channels = self.get_block_channel(ctx.guild, ctx.channel)
        timer = await reminder.create_timer(duration.dt, 'tempblock', ctx.guild.id, ctx.author.id,
                                            ctx.channel.id, member.id,
                                            connection=ctx.db,
                                            created=ctx.message.created_at)

        reason = f'Tempblock by {ctx.author} (ID: {ctx.author.id}) until {duration.dt}'

        try:
            for channel in channels:
                await channel.set_permissions(
                    member,
                    send_messages=False,
                    add_reactions=False,
                    reason=reason)
        except:
            await ctx.send('\N{THUMBS DOWN SIGN}')
        else:
            await ctx.send(
                f'Blocked {member}: {time.human_timedelta(duration.dt, source=timer.created_at)}.')

    @commands.Cog.listener()
    async def on_tempblock_timer_complete(self, timer):
        """ Custom event for timer - when it completes. """
        guild_id, mod_id, channel_id, member_id = timer.args

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            # RIP
            return

        channel = guild.get_channel(channel_id)
        if channel is None:
            # RIP x2
            return

        to_unblock = guild.get_member(member_id)
        if to_unblock is None:
            # RIP x3
            return

        moderator = guild.get_member(mod_id)
        if moderator is None:
            try:
                moderator = await self.bot.fetch_user(mod_id)
            except:
                # request failed somehow
                moderator = f'Mod ID {mod_id}'
            else:
                moderator = f'{moderator} (ID: {mod_id})'
        else:
            moderator = f'{moderator} (ID: {mod_id})'

        reason = f'Automatic unblock from timer made on {timer.created_at} by {moderator}.'

        for chann in self.get_block_channel(guild, channel):
            try:
                await chann.set_permissions(to_unblock,
                                            send_messages=None,
                                            add_reactions=None,
                                            reason=reason)
            except:
                pass

    @cache.cache()
    async def get_feeds(self, channel_id, *, connection=None):
        """ Get active channel feeds. """
        con = connection or self.bot.pool
        query = 'SELECT name, role_id FROM feeds WHERE channel_id=$1;'
        feeds = await con.fetch(query, channel_id)
        return {f['name']: f['role_id'] for f in feeds}

    @commands.group(name='feeds', invoke_without_command=True)
    @commands.guild_only()
    async def _feeds(self, ctx):
        """Shows the list of feeds that the channel has.

        A feed is something that users can opt-in to
        to receive news about a certain feed by running
        the `sub` command (and opt-out by doing the `unsub` command).
        You can publish to a feed by using the `publish` command.
        """

        feeds = await self.get_feeds(ctx.channel.id)

        if not feeds:
            await ctx.send('This channel has no feeds.')
            return

        names = '\n'.join(f'- {r}' for r in feeds)
        await ctx.send(f'Found {len(feeds)} feeds.\n{names}')

    @_feeds.command(name='create')
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def feeds_create(self, ctx, *, name: str):
        """Creates a feed with the specified name.

        You need Manage Roles permissions to create a feed.
        """

        name = name.lower()

        if name in ('@everyone', '@here'):
            return await ctx.send('That is an invalid feed name.')

        query = 'SELECT role_id FROM feeds WHERE channel_id=$1 AND name=$2;'

        exists = await ctx.db.fetchrow(query, ctx.channel.id, name)
        if exists is not None:
            await ctx.send('This feed already exists.')
            return

        # create the role
        if ctx.guild.id == 174702278673039360:
            role_name = self.library_name(ctx.channel) + ' ' + name
        else:
            role_name = name

        role = await ctx.guild.create_role(name=role_name, permissions=discord.Permissions.none())
        query = 'INSERT INTO feeds (role_id, channel_id, name) VALUES ($1, $2, $3);'
        await ctx.db.execute(query, role.id, ctx.channel.id, name)
        self.get_feeds.invalidate(self, ctx.channel.id)
        await ctx.send(f'{ctx.tick(True)} Successfully created feed.')

    @_feeds.command(name='delete', aliases=['remove'])
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def feeds_delete(self, ctx, *, feed: str):
        """Removes a feed from the channel.

        This will also delete the associated role so this
        action is irreversible.
        """

        query = 'DELETE FROM feeds WHERE channel_id=$1 AND name=$2 RETURNING *;'
        records = await ctx.db.fetch(query, ctx.channel.id, feed)
        self.get_feeds.invalidate(self, ctx.channel.id)

        if not records:
            return await ctx.send('This feed does not exist.')

        for record in records:
            role = discord.utils.find(
                lambda r: r.id == record['role_id'], ctx.guild.roles)
            if role is not None:
                try:
                    await role.delete()
                except discord.HTTPException:
                    continue

        await ctx.send(f'{ctx.tick(True)} Removed feed.')

    async def do_subscription(self, ctx, feed, action):
        """ Perform a subscription. """
        feeds = await self.get_feeds(ctx.channel.id)
        if not feeds:
            await ctx.send('This channel has no feeds set up.')
            return

        if feed not in feeds:
            await ctx.send(f'This feed does not exist.\nValid feeds: {", ".join(feeds)}')
            return

        role_id = feeds[feed]
        role = discord.utils.find(lambda r: r.id == role_id, ctx.guild.roles)
        if role is not None:
            await action(role)
            await ctx.message.add_reaction(ctx.tick(True).strip('<:>'))
        else:
            await ctx.message.add_reaction(ctx.tick(False).strip('<:>'))

    @commands.command()
    @commands.guild_only()
    async def sub(self, ctx, *, feed: str):
        """Subscribes to the publication of a feed.

        This will allow you to receive updates from the channel
        owner. To unsubscribe, see the `unsub` command.
        """
        await self.do_subscription(ctx, feed, ctx.author.add_roles)

    @commands.command()
    @commands.guild_only()
    async def unsub(self, ctx, *, feed: str):
        """Unsubscribe to the publication of a feed.

        This will remove you from notifications of a feed you
        are no longer interested in. You can always sub back by
        using the `sub` command.
        """
        await self.do_subscription(ctx, feed, ctx.author.remove_roles)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def publish(self, ctx, feed: str, *, content: str):
        """Publishes content to a feed.

        Everyone who is subscribed to the feed will be notified
        with the content. Use this to notify people of important
        events or changes.
        """
        feeds = await self.get_feeds(ctx.channel.id)
        feed = feed.lower()
        if feed not in feeds:
            await ctx.send('This feed does not exist.')
            return

        role = discord.utils.get(ctx.guild.roles, id=feeds[feed])
        if role is None:
            fmt = 'Uh.. a fatal error occurred here. The role associated with ' \
                  'this feed has been removed or not found. ' \
                  'Please recreate the feed.'
            await ctx.send(fmt)
            return

        # delete the message we used to invoke it
        try:
            await ctx.message.delete()
        except:
            pass

        # make the role mentionable
        await role.edit(mentionable=True)

        # then send the message..
        await ctx.send(f'{role.mention}: {content}'[:2000])

        # then make the role unmentionable
        await role.edit(mentionable=False)

    async def refresh_faq_cache(self):
        """ Refreshes the FAQ cache. """
        self.faq_entries = {}
        base_url = 'https://discordpy.readthedocs.io/en/latest/faq.html'
        async with self.bot.session.get(base_url) as resp:
            text = await resp.text(encoding='utf-8')

            root = etree.fromstring(text, etree.HTMLParser())
            nodes = root.findall(
                ".//div[@id='questions']/ul[@class='simple']/li/ul//a")
            for node in nodes:
                self.faq_entries[''.join(node.itertext()).strip(
                )] = base_url + node.get('href').strip()

    @commands.command()
    async def faq(self, ctx, *, query: str = None):
        """Shows an FAQ entry from the discord.py documentation"""
        if not hasattr(self, 'faq_entries'):
            await self.refresh_faq_cache()

        if query is None:
            return await ctx.send('https://discordpy.readthedocs.io/en/latest/faq.html')

        matches = fuzzy.extract_matches(
            query, self.faq_entries, scorer=fuzzy.partial_ratio, score_cutoff=40)
        if not matches:
            return await ctx.send('Nothing found...')

        paginator = commands.Paginator(suffix='', prefix='')
        for key, _, value in matches:
            paginator.add_line(f'**{key}**\n{value}')
        page = paginator.pages[0]
        await ctx.send(page)


def setup(bot):
    """ Cog entrypoint. """
    bot.add_cog(API(bot))
