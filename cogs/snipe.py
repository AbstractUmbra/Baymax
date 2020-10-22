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

import asyncio
import datetime
import difflib
import typing

import discord
from asyncpg import Record
from discord.ext import commands, menus, tasks

from utils import cache, db, formats

class RequiresSnipe(commands.CheckFailure):
    """ Requires snipe configured. """

class SnipePageSource(menus.ListPageSource):
    def __init__(self, data, embeds):
        self.data = data
        self.embeds = embeds
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        return self.embeds[entries]


class SnipeDeleteTable(db.Table, table_name="snipe_deletes"):
    id = db.PrimaryKeyColumn()

    user_id = db.Column(db.Integer(big=True))
    guild_id = db.Column(db.Integer(big=True))
    channel_id = db.Column(db.Integer(big=True))
    message_id = db.Column(db.Integer(big=True))
    message_content = db.Column(db.String())
    attachment_urls = db.Column(db.Array(db.String()), nullable=True)
    delete_time = db.Column(db.Integer(big=True))


class SnipeEditTable(db.Table, table_name="snipe_edits"):
    id = db.PrimaryKeyColumn()

    user_id = db.Column(db.Integer(big=True))
    guild_id = db.Column(db.Integer(big=True))
    channel_id = db.Column(db.Integer(big=True))
    message_id = db.Column(db.Integer(big=True))
    before_content = db.Column(db.String())
    after_content = db.Column(db.String())
    edited_time = db.Column(db.Integer(big=True))
    jump_url = db.Column(db.String)

class SnipeConfigTable(db.Table, table_name="snipe_config"):
    id = db.Column(db.Integer(big=True), primary_key=True)

    blacklisted_channels = db.Column(db.Array(db.Integer(big=True)))
    blacklisted_members = db.Column(db.Array(db.Integer(big=True)))

class SnipeConfig:
    __slots__ = ('bot', 'guild_id', 'record', 'channel_ids', 'member_ids')

    def __init__(self, *, guild_id, bot, record=None):
        self.guild_id = guild_id
        self.bot = bot
        self.record = record

        if record:
            self.channel_ids = record['blacklisted_channels']
            self.member_ids = record['blacklisted_members']
        else:
            self.channel_ids = []
            self.member_ids = []

    @property
    def configured(self):
        guild = self.bot.get_guild(self.guild_id)
        if self.record:
            return guild and self.record


def requires_snipe():
    async def predicate(ctx):
        if not ctx.guild:
            return

        cog = ctx.bot.get_cog("Snipe")

        ctx.snipe_conf = await cog.get_snipe_config(ctx.guild.id, connection=ctx.db)
        if ctx.snipe_conf.configured is None:
            raise RequiresSnipe("Sniping not set up.")

        return True
    return commands.check(predicate)

class Snipe(commands.Cog):
    """ Sniping cog. """

    def __init__(self, bot):
        self.bot = bot
        self.snipe_deletes = []
        self.snipe_edits = []
        self._snipe_lock = asyncio.Lock(loop=bot.loop)
        self.snipe_delete_update.start()
        self.snipe_edit_update.start()

    def cog_unload(self):
        self.snipe_delete_update.stop()
        self.snipe_edit_update.stop()

    async def cog_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, RequiresSnipe):
            return await ctx.send("Seems this guild isn't configured for snipes. It is an opt-in basis.\nHave a moderator/admin run `snipe setup`.")

    @commands.Cog.listener()
    async def on_guild_leave(self, guild):
        query = """ DELETE FROM snipe_edits WHERE guild_id = $1;
                    DELETE FROM snipe_deletes WHERE guild_id = $1;
                """
        return await self.bot.pool.execute(query, guild.id)

    @cache.cache()
    async def get_snipe_config(self, guild_id, *, connection=None):
        connection = connection or self.bot.pool
        query = """ SELECT * FROM snipe_config WHERE id=$1 """
        record = await connection.fetchrow(query, guild_id)
        return SnipeConfig(guild_id=guild_id, bot=self.bot, record=record)

    def _gen_delete_embeds(self, records: typing.List[Record]) -> typing.List[discord.Embed]:
        embeds = []
        for record in records:
            channel = self.bot.get_channel(record['channel_id'])
            author = self.bot.get_user(record['user_id'])
            embed = discord.Embed()
            if not author:
                embed.set_author(name="A deleted user...")
            else:
                embed.set_author(name=author.name, icon_url=author.avatar_url)
            embed.title = f"Deleted from {channel.name}"
            embed.description = f"```\n{record['message_content']}```" if record['message_content'] else None
            if record['attachment_urls']:
                embed.set_image(url=record['attachment_urls'][0])
                if len(record['attachment_urls']) > 1:
                    for item in record['attachment_urls'][1:]:
                        embed.add_field(name="Attachment",
                                        value=f"[link]({item})")
            fmt = f"Result {records.index(record)+1}/{len(records)}"
            embed.set_footer(text=f"{fmt} | Author ID: {author.id}")
            embed.timestamp = datetime.datetime.utcfromtimestamp(
                record['delete_time'])
            embeds.append(embed)
        return embeds

    async def _gen_edit_embeds(self, records: typing.List[Record]) -> typing.List[discord.Embed]:
        embeds = []
        for record in records:
            channel = self.bot.get_channel(record['channel_id'])
            author = self.bot.get_user(record['user_id']) or await self.bot.fetch_user(record['user_id'])
            jump = record['jump_url']
            embed = discord.Embed()
            if not author:
                embed.set_author(name="A deleted user...")
            else:
                embed.set_author(name=author.name, icon_url=author.avatar_url)
            embed.title = f"Edited in {channel.name}"
            diff_text = self.get_diff(
                record['before_content'], record['after_content'])
            if len(diff_text) > 2048:
                url = await self.bot.mb_client.post(diff_text, syntax="diff")
                embed.description = f"Diff is too large, so I put it on [MystB.in]({url})."
            else:
                embed.description = formats.to_codeblock(
                    diff_text, language="diff") if diff_text else None
            fmt = f"Result {records.index(record)+1}/{len(records)}"
            embed.set_footer(text=f"{fmt} | Author ID: {author.id}")
            embed.add_field(name="Jump to this message",
                            value=f"[Here!]({jump})")
            embed.timestamp = datetime.datetime.fromtimestamp(
                record['edited_time'])
            embeds.append(embed)
        return embeds

    def get_diff(self, before, after):
        before_content = f'{before}\n'.splitlines(keepends=True)
        after_content = f'{after}\n'.splitlines(keepends=True)
        return ''.join(difflib.ndiff(before_content, after_content))

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return
        if not message.content and not message.attachments:
            return
        if message.author.id == 565095015874035742:
            return
        config = await self.get_snipe_config(message.guild.id)
        if not config.configured:
            return
        if message.author.id in config.member_ids:
            return
        if message.channel.id in config.channel_ids:
            return
        delete_time = datetime.datetime.now().replace(microsecond=0).timestamp()
        a_id = message.author.id
        g_id = message.guild.id
        c_id = message.channel.id
        m_id = message.id
        m_content = message.content
        attachs = [
            attachment.proxy_url for attachment in message.attachments if message.attachments]
        async with self._snipe_lock:
            self.snipe_deletes.append({
                "user_id": a_id,
                "guild_id": g_id,
                "channel_id": c_id,
                "message_id": m_id,
                "message_content": m_content,
                "attachment_urls": attachs,
                "delete_time": int(delete_time),
            })

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild:
            return
        if not before.content:
            return
        if before.content == after.content:
            return
        if before.author.id == 565095015874035742:
            return
        config = await self.get_snipe_config(before.guild.id)
        if not config.configured:
            return
        if before.author.id in config.member_ids:
            return
        if before.channel.id in config.channel_ids:
            return
        edited_time = after.edited_at or datetime.datetime.now()
        edited_time = edited_time.replace(microsecond=0).timestamp()
        a_id = after.author.id
        g_id = after.guild.id
        c_id = after.channel.id
        m_id = after.id
        before_content = before.content
        after_content = after.content
        async with self._snipe_lock:
            self.snipe_edits.append({
                "user_id": a_id,
                "guild_id": g_id,
                "channel_id": c_id,
                "message_id": m_id,
                "before_content": before_content,
                "after_content": after_content,
                "edited_time": int(edited_time),
                "jump_url": after.jump_url
            })

    @commands.guild_only()
    @commands.group(name="snipe", aliases=["s"], invoke_without_command=True, cooldown_after_parsing=True)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @requires_snipe()
    async def show_snipes(self, ctx, amount: int = 5, channel: discord.TextChannel = None):
        """ Select the last N snipes from this channel. """
        if channel:
            if not ctx.author.guild_permissions.manage_messages:
                return await ctx.send("Sorry, you need to have 'Manage Messages' to view another channel.")
            if channel.is_nsfw() and not ctx.channel.is_nsfw():
                return await ctx.send("No peeping NSFW stuff in here you dirty boi/gurl.")
        channel = channel or ctx.channel
        query = "SELECT * FROM snipe_deletes WHERE guild_id = $2 AND channel_id = $3 ORDER BY id DESC LIMIT $1;"
        results = await self.bot.pool.fetch(query, amount, ctx.guild.id, channel.id)
        dict_results = [dict(result) for result in results] if results else []
        local_snipes = [snipe for snipe in self.snipe_deletes if snipe['channel_id'] == channel.id]
        full_results = dict_results + local_snipes
        if not full_results:
            return await ctx.send("No snipes for this channel.")
        full_results = sorted(
            full_results, key=lambda d: d['delete_time'], reverse=True)[:amount]
        embeds = self._gen_delete_embeds(full_results)
        pages = menus.MenuPages(
            source=SnipePageSource(range(0, amount), embeds), delete_message_after=True)
        await pages.start(ctx)

    @commands.has_guild_permissions(manage_messages=True)
    @show_snipes.command(name="setup")
    async def set_up_snipe(self, ctx):
        """ Opts in to the snipe capabilities of Baymax. Requires Manage Messages. """
        self.get_snipe_config.invalidate(self, ctx.guild.id)

        config = await self.get_snipe_config(ctx.guild.id, connection=ctx.db)
        query = """ INSERT INTO snipe_config (id, blacklisted_channels, blacklisted_members)
                    VALUES ($1, $2, $3)
                """
        if not config.record:
            await ctx.db.execute(query, ctx.guild.id, [], [])
            await ctx.message.add_reaction(self.bot.emoji[True])
        else:
            await ctx.send("You're already enabled for snipes. Did you mean to disable it?")
        self.get_snipe_config.invalidate(self, ctx.guild.id)

    @commands.has_guild_permissions(manage_messages=True)
    @show_snipes.command(name="destroy", aliases=["desetup"])
    async def snipe_desetup(self, ctx):
        """ remove the ability to snipe here. """
        query = """ DELETE FROM snipe_config WHERE id = $1; """
        config = await self.get_snipe_config(ctx.guild.id, connection=ctx.db)
        if not config.configured:
            return await ctx.send("Sniping is not enabled for this guild.")
        confirm = await ctx.prompt("This will delete all data stored from this guild from my snipes. Are you sure?")
        if not confirm:
            return await ctx.message.add_reaction(self.bot.emoji[False])
        await self.bot.pool.execute(query, ctx.guild.id)
        self.get_snipe_config.invalidate(self, ctx.guild.id)
        await ctx.message.add_reaction(self.bot.emoji[True])


    @show_snipes.command(name="optout", aliases=["out", "disable"])
    @requires_snipe()
    async def snipe_optout(self, ctx, entity: typing.Union[discord.Member, discord.TextChannel] = None):
        """ Let's toggle it for this channel / member / self. """
        config = await self.get_snipe_config(ctx.guild.id, connection=ctx.db)
        if isinstance(entity, (discord.Member, discord.TextChannel)):
            if not ctx.author.guild_permissions.manage_messages:
                raise commands.MissingPermissions(["manage_messages"])
        entity = entity or ctx.author
        if entity.id in config.channel_ids or entity.id in config.member_ids:
            return await ctx.send(f"{entity.name} is already opted out of sniping.")
        if isinstance(entity, discord.Member):
            query = """ UPDATE snipe_config
                        SET blacklisted_members = blacklisted_members || $2
                        WHERE id = $1;
                    """
        elif isinstance(entity, discord.TextChannel):
            query = """ UPDATE snipe_config
                        SET blacklisted_channels = blacklisted_channels || $2
                        WHERE id = $1;
                    """
        await self.bot.pool.execute(query, ctx.guild.id, [entity.id])
        self.get_snipe_config.invalidate(self, ctx.guild.id)
        await ctx.message.add_reaction(self.bot.emoji[True])

    @show_snipes.command(name="optin", aliases=["in", "enable"], usage="[member/channel] (defaults to self.)")
    @requires_snipe()
    async def snipe_optin(self, ctx, entity: typing.Union[discord.Member, discord.TextChannel] = None):
        """ Let's toggle it for this channel / member / self. """
        config = await self.get_snipe_config(ctx.guild.id, connection=ctx.db)
        if isinstance(entity, (discord.Member, discord.TextChannel)):
            if not ctx.author.guild_permissions.manage_messages:
                raise commands.MissingPermissions(["manage_messages"])
        entity = entity or ctx.author
        if not entity.id in config.channel_ids and not entity.id in config.member_ids:
            return await ctx.send(f"{entity.name} is currently not opted out of sniping.")
        if isinstance(entity, discord.Member):
            query = """ UPDATE snipe_config
                        SET blacklisted_members = array_remove(blacklisted_members, $2)
                        WHERE id = $1;
                    """
        elif isinstance(entity, discord.TextChannel):
            query = """ UPDATE snipe_config
                        SET blacklisted_channels = array_remove(blacklisted_channels, $2)
                        WHERE id = $1;
                    """
        await self.bot.pool.execute(query, ctx.guild.id, entity.id)
        self.get_snipe_config.invalidate(self, ctx.guild.id)
        await ctx.message.add_reaction(self.bot.emoji[True])


    @commands.guild_only()
    @show_snipes.command(name="edits", aliases=["e"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    @requires_snipe()
    async def show_edit_snipes(self, ctx, amount: int = 5, channel: discord.TextChannel = None):
        """ Edit snipes, shows the last N from. Must have manage_messages to choose a different channel. """
        # let's check that amount is an int, clear inputs
        if channel:
            if not ctx.author.guild_permissions.manage_messages:
                return await ctx.send("Sorry, you need to have 'Manage Messages' to view another channel.")
        channel = channel or ctx.channel
        query = "SELECT * FROM snipe_edits WHERE guild_id = $2 AND channel_id = $3 ORDER BY id DESC LIMIT $1;"
        results = await self.bot.pool.fetch(query, amount, ctx.guild.id, channel.id)
        dict_results = [dict(result) for result in results]
        local_snipes = [
            snipe for snipe in self.snipe_edits if snipe['channel_id'] == channel.id]
        full_results = dict_results + local_snipes
        full_results = sorted(
            full_results, key=lambda d: d['edited_time'], reverse=True)[:amount]
        embeds = await self._gen_edit_embeds(full_results)
        if not embeds:
            return await ctx.send("No edit snipes for this channel.")
        pages = menus.MenuPages(
            source=SnipePageSource(range(0, amount), embeds), delete_message_after=True)
        await pages.start(ctx)

    @show_snipes.command(name="clear", aliases=["remove", "delete"], hidden=True)
    @commands.has_guild_permissions(manage_messages=True)
    @requires_snipe()
    async def _snipe_clear(self, ctx, target: typing.Union[discord.Member, discord.TextChannel]):
        """
        Remove all data stored on snipes, including edits for the target Member or TextChannel.
        Must have the 'manage_messages' permission to do this.
        """
        member = False
        channel = False
        if isinstance(target, discord.Member):
            deletes = "DELETE FROM snipe_deletes WHERE guild_id = $1 and user_id = $2;"
            edits = "DELETE FROM snipe_edits WHERE guild_id = $1 and user_id = $2;"
            member = True
        elif isinstance(target, discord.TextChannel):
            deletes = "DELETE FROM snipe_deletes WHERE guild_id = $1 and channel_id = $2;"
            edits = "DELETE FROM snipe_edits WHERE guild_id = $1 and channel_id = $2;"
            channel = True
        else:
            # Shouldn't happen...
            return
        confirm = await ctx.prompt("This is a destructive action and non-recoverable. Are you sure?")
        if not confirm:
            return
        await self.bot.pool.execute(deletes, ctx.guild.id, target.id)
        await self.bot.pool.execute(edits, ctx.guild.id, target.id)
        for item in self.snipe_deletes:
            if member:
                if item['user_id'] == target.id:
                    self.snipe_deletes.remove(item)
            elif channel:
                if item['channel_id'] == target.id:
                    self.snipe_deletes.remove(item)

        return await ctx.message.add_reaction(self.bot.emoji[True])

    @tasks.loop(minutes=1)
    async def snipe_delete_update(self):
        """ Batch updates for the snipes. """
        await self.bot.wait_until_ready()
        query = """
                INSERT INTO snipe_deletes (user_id, guild_id, channel_id, message_id, message_content, attachment_urls, delete_time)
                SELECT x.user_id, x.guild_id, x.channel_id, x.message_id, x.message_content, x.attachment_urls, x.delete_time
                FROM jsonb_to_recordset($1::jsonb) AS
                x(user_id BIGINT, guild_id BIGINT, channel_id BIGINT, message_id BIGINT, message_content TEXT, attachment_urls TEXT[], delete_time BIGINT)
                """

        async with self._snipe_lock:
            await self.bot.pool.execute(query, self.snipe_deletes)
            self.snipe_deletes.clear()

    @tasks.loop(minutes=1)
    async def snipe_edit_update(self):
        """ Batch updates for the snipes. """
        await self.bot.wait_until_ready()
        query = """
                INSERT INTO snipe_edits (user_id, guild_id, channel_id, message_id, before_content, after_content, edited_time, jump_url)
                SELECT x.user_id, x.guild_id, x.channel_id, x.message_id, x.before_content, x.after_content, x.edited_time, x.jump_url
                FROM jsonb_to_recordset($1::jsonb) AS
                x(user_id BIGINT, guild_id BIGINT, channel_id BIGINT, message_id BIGINT, before_content TEXT, after_content TEXT, edited_time BIGINT, jump_url TEXT)
                """

        async with self._snipe_lock:
            await self.bot.pool.execute(query, self.snipe_edits)
            self.snipe_edits.clear()

    @show_snipes.error
    @show_edit_snipes.error
    async def snipe_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f"Ha! Snipes are on cooldown for {error.retry_after:.02f}s.")

def setup(bot):
    bot.add_cog(Snipe(bot))
