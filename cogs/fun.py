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
import math
import re
import textwrap
from string import ascii_lowercase

import discord
import googletrans
from discord.ext import commands, tasks
from utils import db, lang

ABT_REG = "~([a-zA-Z]+)~"

MENTION_CHANNEL_ID = 722930330897743894
DM_CHANNEL_ID = 722930296756109322


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
        self.pepe = {'up': "<:pepePoint_up:728347439391572000>",
                     'down': "<:pepePoint_down:728347439571927122>",
                     'left': "<:pepePoint_left:728347439387377737>",
                     'right': "<:pepePoint:728347439903277056>"}
        self.translator = googletrans.Translator()

    @commands.group(invoke_without_command=True, skip_extra=False)
    async def abt(self, ctx, *, content: commands.clean_content):
        """ I love this language. """
        keep = re.findall(ABT_REG, content)

        def trans(m):
            get = m.group(0)
            if get.isupper():
                return lang.ab_charmap[get.lower()].upper()
            return lang.ab_charmap[get]
        repl = re.sub("[a-zA-Z]", trans, content)
        fin = re.sub(ABT_REG, lambda m: keep.pop(0), repl)
        await ctx.send(fin)

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

    @commands.command(hidden=True)
    async def translate(self, ctx, *, message: commands.clean_content):
        """Translates a message to English using Google translate."""

        loop = self.bot.loop

        try:
            ret = await loop.run_in_executor(None, self.translator.translate, message)
        except Exception as e:
            return await ctx.send(f'An error occurred: {e.__class__.__name__}: {e}')

        embed = discord.Embed(title='Translated', colour=0x000001)
        src = googletrans.LANGUAGES.get(ret.src, '(auto-detected)').title()
        dest = googletrans.LANGUAGES.get(ret.dest, 'Unknown').title()
        embed.add_field(name=f'From {src}', value=ret.origin, inline=False)
        embed.add_field(name=f'To {dest}', value=ret.text, inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        async with self.lock:
            self.message_deletes += 1

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id in (self.bot.user.id, self.bot.owner_id):
            return
        if self.bot.user in message.mentions:
            channel = self.bot.get_channel(MENTION_CHANNEL_ID)
            embed = discord.Embed(title="Baymax was mentioned!")
            embed.set_author(name=message.author.name,
                             icon_url=message.author.avatar_url)
            embed.description = f"{message.content}\n\n[Jump!]({message.jump_url})"
            embed.timestamp = message.created_at
            await channel.send(embed=embed)
        elif not message.guild:
            channel = self.bot.get_channel(DM_CHANNEL_ID)
            embed = discord.Embed(title="Baymax was DM'd.")
            embed.set_author(name=message.author.name,
                             icon_url=message.author.avatar_url)
            embed.description = f"{message.content})"
            embed.timestamp = message.created_at
            await channel.send(embed=embed)

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

        embed = discord.Embed(title="Baymax Stats")
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
        embed.add_field(name="**Messages**",
                        value=textwrap.dedent(message_str), inline=False)
        embed.add_field(name="**Guilds**",
                        value=textwrap.dedent(guild_str), inline=False)
        embed.set_footer(text=f"I have also run {command_count:,} commands!")

        await ctx.send(embed=embed)

    @commands.command()
    async def point(self, ctx, member: discord.Member):
        """ Point. """
        length = 1 + len(member.display_name)
        x_length = math.ceil(math.ceil(length/2) * 0.9)
        msg = f"""
        {self.pepe['down']}{self.pepe['down']*x_length}{self.pepe['down']}
        {self.pepe['right']}{member.mention}{self.pepe['left']}
        {self.pepe['up']}{self.pepe['up']*x_length}{self.pepe['up']}
        """
        await ctx.send(textwrap.dedent(msg))


def setup(bot):
    bot.add_cog(Fun(bot))
