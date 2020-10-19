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

import textwrap
from datetime import datetime

from aiohttp import ContentTypeError
from currency_converter import CurrencyConverter

import discord
from discord.ext import commands
from utils import db, cache, time


class Feeds(db.Table):
    id = db.PrimaryKeyColumn()
    channel_id = db.Column(db.Integer(big=True))
    role_id = db.Column(db.Integer(big=True))
    name = db.Column(db.String)

class PypiObject:
    """ Pypi objects. """

    def __init__(self, pypi_dict):
        self.module_name = pypi_dict['info']['name']
        self.module_author = pypi_dict['info']['author']
        self.module_author_email = pypi_dict['info']['author_email'] or None
        self.module_licese = pypi_dict['info']['license'] or "No license specified on PyPi."
        self.module_minimum_py = pypi_dict['info']['requires_python'] or "No minimum version specified."
        self.module_latest_ver = pypi_dict['info']['version']
        self.release_time = pypi_dict['releases'][str(
            self.module_latest_ver)][0]['upload_time']
        self.module_description = pypi_dict['info']['summary'] or None
        self.pypi_urls = pypi_dict['info']['project_urls']
        self.raw_classifiers = pypi_dict['info']['classifiers'] or None

    @property
    def urls(self) -> str:
        return self.pypi_urls or "No URLs listed."

    @property
    def minimum_ver(self) -> str:
        return discord.utils.escape_markdown(self.module_minimum_py)

    @property
    def classifiers(self) -> str:
        if self.raw_classifiers:
            new = textwrap.shorten("\N{zwsp}".join(
                self.raw_classifiers), width=300)
            return "\n".join(new.split("\N{zwsp}"))

    @property
    def description(self) -> str:
        if self.module_description:
            return textwrap.shorten(self.module_description, width=300)
        return None

    @property
    def release_datetime(self) -> datetime:
        return time.hf_time(datetime.fromisoformat(self.release_time))


class External(commands.Cog):
    """ External API stuff. """

    def __init__(self, bot):
        self.bot = bot
        self.headers = {"User-Agent": "Baymax Discord bot."}
        self.currency_conv = CurrencyConverter()

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def pypi(self, ctx, *, package_name: str):
        """ Searches PyPi for a Package. """
        async with self.bot.session.get(f"https://pypi.org/pypi/{package_name}/json", headers=self.headers) as pypi_resp:
            pypi_json = await pypi_resp.json()
        pypi_details = PypiObject(pypi_json)

        embed = discord.Embed(title=f"{pypi_details.module_name} on PyPi",
                              colour=discord.Colour(0x000000))
        embed.set_author(name=pypi_details.module_author)
        embed.description = pypi_details.description

        if pypi_details.module_author_email:
            embed.add_field(name="Author Contact",
                            value=f"[Email]({pypi_details.module_author_email})")

        embed.add_field(name="Latest released ver",
                        value=pypi_details.module_latest_ver, inline=True)
        embed.add_field(name="Released at",
                        value=pypi_details.release_datetime, inline=True)
        embed.add_field(name="Supported Python version(s)",
                        value=pypi_details.minimum_ver, inline=False)

        if isinstance(pypi_details.urls, str):
            urls = pypi_details.urls
        elif isinstance(pypi_details.urls, dict):
            urls = "\n".join(
                [f"[{key}]({value})" for key, value in pypi_details.urls.items()])

        embed.add_field(name="Relevant URLs", value=urls)
        embed.add_field(
            name="License", value=pypi_details.module_licese)

        if pypi_details.raw_classifiers:
            print(pypi_details.raw_classifiers)
            embed.add_field(name="Classifiers",
                            value=pypi_details.classifiers, inline=False)

        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        return await ctx.send(embed=embed)

    @commands.command()
    async def currency(self, ctx, amount: int, source: str, dest: str):
        """ Currency converter. """
        source = source.upper()
        dest = dest.upper()
        new_amount = self.currency_conv.convert(amount, source, dest)
        prefix = "$" if dest.endswith("D") else ""
        await ctx.send(f"{prefix}{round(new_amount, 2)}")

    @pypi.error
    async def pypi_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, ContentTypeError):
            error.handled = True
            return await ctx.send("That package doesn't exist on PyPi.")

    @cache.cache()
    async def get_feeds(self, channel_id, *, connection=None):
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

        if len(feeds) == 0:
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

        role = await ctx.guild.create_role(name=name, permissions=discord.Permissions.none())
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

        if len(records) == 0:
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
        feeds = await self.get_feeds(ctx.channel.id)
        if len(feeds) == 0:
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
        mentions = discord.AllowedMentions(roles=[role])
        await ctx.send(f'{role.mention}: {content}'[:2000], allowed_mentions=mentions)

        # then make the role unmentionable
        await role.edit(mentionable=False)


def setup(bot):
    """ Cog entrypoint. """
    bot.add_cog(External(bot))
