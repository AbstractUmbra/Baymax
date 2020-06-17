import asyncio
import datetime
import difflib
import textwrap
import typing

import discord
from discord.ext import commands, menus, tasks
from asyncpg import Record

from utils import db, formats


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

    @commands.Cog.listener()
    async def on_guild_leave(self, guild):
        query = """ DELETE FROM snipe_edits WHERE guild_id = $1;
                    DELETE FROM snipe_deletes WHERE guild_id = $1;
                """
        return await self.bot.pool.execute(query, guild.id)

    def _gen_delete_embeds(self, records: typing.List[Record]) -> typing.List[discord.Embed]:
        embeds = []
        for record in records:
            channel = self.bot.get_channel(record['channel_id'])
            author = self.bot.get_user(record['user_id'])
            embed = discord.Embed()
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

    def _gen_edit_embeds(self, records: typing.List[Record]) -> typing.List[discord.Embed]:
        embeds = []
        for record in records:
            channel = self.bot.get_channel(record['channel_id'])
            author = self.bot.get_user(record['user_id'])
            jump = record['jump_url']
            embed = discord.Embed()
            embed.set_author(name=author.name, icon_url=author.avatar_url)
            embed.title = f"Edited in {channel.name}"
            diff_text = self.get_diff(
                record['before_content'], record['after_content'])
            if len(diff_text) > 2048:
                embed.description = f"Diff is too large, here's the before:\n```{record['before_content']}```"
            else:
                embed.description = formats.format_codeblock(
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
    @commands.group(name="snipe", aliases=["s"], invoke_without_command=True)
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def show_snipes(self, ctx, amount: int = 5, channel: discord.TextChannel = None):
        """ Select the last 20 snipes from this channel. """
        # let's check that amount is an int, clear inputs
        if not isinstance(amount, int):
            return await ctx.send("Fuck off.")
        if channel:
            if not ctx.author.guild_permissions.manage_messages:
                return await ctx.send("Sorry, you need to have 'Manage Messages' to view another channel.")
        query = "SELECT * FROM snipe_deletes WHERE guild_id = $2 AND channel_id = $3 ORDER BY id DESC LIMIT $1;"
        results = await self.bot.pool.fetch(query, amount, ctx.guild.id, ctx.channel.id)
        dict_results = [dict(result) for result in results]
        local_snipes = [
            snipe for snipe in self.snipe_deletes if snipe['channel_id'] == ctx.channel.id]
        full_results = dict_results + local_snipes
        full_results = sorted(
            full_results, key=lambda d: d['delete_time'], reverse=True)[:amount]
        embeds = self._gen_delete_embeds(full_results)
        if not embeds:
            return await ctx.send("No snipes for this channel.")
        pages = menus.MenuPages(
            source=SnipePageSource(range(0, amount), embeds), delete_message_after=True)
        await pages.start(ctx)

    @commands.guild_only()
    @show_snipes.command(name="edits", aliases=["e"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def show_edit_snipes(self, ctx, amount: int = 5, channel: discord.TextChannel = None):
        """ Edit snipes, default of 20. Must have manage_messages to choose a different channel. """
        # let's check that amount is an int, clear inputs
        if not isinstance(amount, int):
            return await ctx.send("Fuck off.")
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
        embeds = self._gen_edit_embeds(full_results)
        if not embeds:
            return await ctx.send("No edit snipes for this channel.")
        pages = menus.MenuPages(
            source=SnipePageSource(range(0, amount), embeds), delete_message_after=True)
        await pages.start(ctx)

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


def setup(bot):
    bot.add_cog(Snipe(bot))
