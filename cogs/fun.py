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
import json
import textwrap
from string import ascii_lowercase

import discord
from discord.ext import commands, tasks

from utils import db, formats, lang


class StatisticsTable(db.Table, table_name="statistics"):
    id = db.PrimaryKeyColumn()
    message_deletes = db.Column(db.Integer(big=True))
    bulk_message_deletes = db.Column(db.Integer(big=True))
    message_edits = db.Column(db.Integer(big=True))
    bans = db.Column(db.Integer(big=True))
    unbans = db.Column(db.Integer(big=True))
    channel_deletes = db.Column(db.Integer(big=True))
    channel_creates = db.Column(db.Integer(big=True))
    command_count = db.Column(db.Integer(big=True))

class Fun(commands.Cog):
    """ Some fun stuff, not fleshed out yet. """
    def __init__(self, bot):
        self.bot = bot
        self.lock = asyncio.Lock()
        self.message_deletes = 0
        self.bulk_message_deletes = 0
        self.message_edits = 0
        self.bans = 0
        self.unbans = 0
        self.channel_deletes = 0
        self.channel_creates = 0
        self.command_count = 0
        self.bulk_update.start()


    @commands.command()
    async def iexist(self, ctx):
        return await ctx.send("https://www.youtube.com/watch?v=h0QqXurjzD8")

    @commands.group(invoke_without_command=True, skip_extra=False)
    async def abt(self, ctx, *, tr_input: str):
        """ I love this language. """
        new_str = ""
        br = True
        for char in tr_input:
            if char == "~":
                br = not br
            elif br and (char.lower() in ascii_lowercase):
                new_str += lang.ab_charmap.get(char.lower())
            else:
                new_str += char
        return await ctx.send(new_str.replace("~", "").capitalize())

    @abt.command(name="r", aliases=["reverse"])
    async def abt_reverse(self, ctx, *, tr_input: str):
        """ Uno reverse. """
        new_str = ""
        br = True
        for char in tr_input:
            if char == "~":
                br = not br
            if br and (char.lower() in ascii_lowercase):
                new_str += [key for key,
                            val in lang.ab_charmap.items() if val == char.lower()][0]
            else:
                new_str += char
        await ctx.send(new_str.replace("~", "").capitalize())


    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        async with self.lock:
            self.message_deletes += 1

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        async with self.lock:
            self.bulk_message_deletes += 1

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        async with self.lock:
            self.message_edits += 1

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        async with self.lock:
            self.bans += 1

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        async with self.lock:
            self.unbans += 1

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        async with self.lock:
            self.channel_deletes += 1

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        async with self.lock:
            self.channel_creates += 1

    @commands.Cog.listener()
    async def on_command(self, ctx):
        async with self.lock:
            self.command_count += 1

    @tasks.loop(minutes=10)
    async def bulk_update(self):
        await self.bot.wait_until_ready()
        query = """ UPDATE statistics
                    SET message_deletes = message_deletes + $1,
                    bulk_message_deletes = bulk_message_deletes + $2,
                    message_edits = message_edits + $3,
                    bans = bans + $4,
                    unbans = unbans + $5,
                    channel_deletes = channel_deletes + $6,
                    channel_creates = channel_creates + $7,
                    command_count = command_count + $8
                    WHERE id = 1;
                """
        async with self.lock:
            await self.bot.pool.execute(query, self.message_deletes, self.bulk_message_deletes, self.message_edits, self.bans, self.unbans, self.channel_deletes, self.channel_creates, self.command_count)
            self.message_deletes = 0
            self.bulk_message_deletes = 0
            self.message_edits = 0
            self.bans = 0
            self.unbans = 0
            self.channel_deletes = 0
            self.channel_creates = 0
            self.command_count = 0

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def statistics(self, ctx):
        query = "SELECT * FROM statistics LIMIT 1;"
        stat_record = await self.bot.pool.fetchrow(query)
        message_deletes = stat_record['message_deletes'] + self.message_deletes
        bulk_message_deletes = stat_record['bulk_message_deletes'] + \
            self.bulk_message_deletes
        message_edits = stat_record['message_edits'] + self.message_edits
        bans = stat_record['bans'] + self.bans
        unbans = stat_record['unbans'] + self.unbans
        channel_deletes = stat_record['channel_deletes'] + self.channel_deletes
        channel_creates = stat_record['channel_creates'] + self.channel_creates
        command_count = stat_record['command_count'] + self.command_count
        embed = discord.Embed(title="Penumbra Stats")
        embed.description = "Hello! Since 6th of July, 2020, I have witnessed the following events."
        message_str = f"""
        ```prolog
        Message Deletes      : {message_deletes:,}
        Bulk Message Deletes : {bulk_message_deletes:,}
        Message Edits        : {message_edits:,}
        ```
        """
        guild_str = f"""
        ```prolog
        Banned Members       : {bans:,}
        Unbanned Members     : {unbans:,}
        Channel Creation     : {channel_creates:,}
        Channel Deletion     : {channel_deletes:,}
        ```
        """
        embed.add_field(name="**Messages**", value=textwrap.dedent(message_str), inline=False)
        embed.add_field(name="**Guilds**", value=textwrap.dedent(guild_str), inline=False)
        embed.set_footer(text=f"I have also run {command_count:,} commands!")
        await ctx.send(embed=embed)

    @commands.command(name="msgraw", aliases=["msgr", "rawm"])
    async def raw_message(self, ctx, message_id: int):
        """ Quickly return the raw content of the specific message. """
        try:
            msg = await ctx.bot.http.get_message(ctx.channel.id, message_id)
        except discord.NotFound:
            raise commands.BadArgument(f"Message with the ID of {message_id} cannot be found in {ctx.channel.mention}.")

        await ctx.send(f"```json\n{formats.clean_triple_backtick(formats.escape_invis_chars(json.dumps(msg, indent=2, ensure_ascii=False, sort_keys=True)))}\n```")



def setup(bot):
    bot.add_cog(Fun(bot))
