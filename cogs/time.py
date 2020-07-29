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

import random
from datetime import datetime

import discord
import pytz
from discord.ext import commands, menus

from utils import db


class TZMenuSource(menus.ListPageSource):
    """ Okay let's make it embeds, I guess. """

    def __init__(self, data, embeds):
        self.data = data
        self.embeds = embeds
        super().__init__(data, per_page=1)

    async def format_page(self, menu, page):
        """ Format each page. """
        return self.embeds[page]


class TimeTable(db.Table, table_name="tz_store"):
    """ Create the table for timezones. Make it unique per user, per guild. """

    id = db.PrimaryKeyColumn()

    user_id = db.Column(db.Integer(big=True))
    guild_id = db.Column(db.Integer(big=True))
    tz = db.Column(db.String, unique=True)

    @classmethod
    def create_table(cls, *, exists_ok=True):
        """ Unique index for tzs. """
        statement = super().create_table(exists_ok=exists_ok)

        sql = "CREATE UNIQUE INDEX IF NOT EXISTS timezone_uniq_idx ON tz_store (guild_id, user_id);"
        return statement + '\n' + sql


class Time(commands.Cog):
    """ Time cog for fun time stuff. """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        query = "DELETE FROM tz_store WHERE guild_id = $1;"
        return await self.bot.pool.execute(query, guild.id)

    def _gen_tz_embeds(self,
                       requester: str,
                       iterable: list):
        embeds = []

        for item in iterable:
            embed = discord.Embed(
                title="Timezone lists",
                colour=discord.Colour.green()
            )
            embed.description = "\n".join(item)
            fmt = f"Page {iterable.index(item)+1}/{len(iterable)}"
            embed.set_footer(text=f"{fmt} | Requested by: {requester}")
            embeds.append(embed)
        return embeds

    def _verify_tz(self, v_timezone: str) -> str:
        lower_tzs = [pt_timezone.lower() for pt_timezone in pytz.all_timezones]
        if v_timezone.lower() not in lower_tzs:
            return None
        idx = lower_tzs.index(v_timezone.lower())
        v_timezone = pytz.all_timezones[idx]
        return v_timezone

    def _curr_tz_time(self, curr_timezone: str, *, ret_datetime: bool = False):
        """ We assume it's a good tz here. """
        timezone = pytz.timezone(curr_timezone)
        dt_obj = datetime.now(timezone)
        if ret_datetime:
            return dt_obj
        if dt_obj.day in [1, 21, 31]:
            date_modif = "st"
        elif dt_obj.day in [2, 22]:
            date_modif = "nd"
        elif dt_obj.day in [3, 23]:
            date_modif = "rd"
        else:
            date_modif = "th"
        return dt_obj.strftime(f"%A %-d{date_modif} of %B %Y @ %H:%M %Z%z")

    @commands.command(aliases=['tz'])
    async def timezone(self, ctx: commands.Context, *, timezone: str = None) -> discord.Message:
        """ This will return the time in a specified timezone. """
        if not timezone:
            timezone = random.choice(pytz.all_timezones)
        timezone = self._verify_tz(timezone)
        if not timezone:
            return await ctx.send("This doesn't seem like a valid timezone.")
        embed = discord.Embed(
            title=f"Current time in {timezone}",
            description=f"{self._curr_tz_time(timezone, ret_datetime=False)}"
        )
        embed.set_footer(text=f"Requested by: {ctx.author}")
        embed.timestamp = datetime.utcnow()
        return await ctx.send(embed=embed)

    @commands.command(aliases=['tzs'])
    @commands.cooldown(1, 15, commands.BucketType.channel)
    async def timezones(self, ctx: commands.Context):
        """ List all possible timezones... """
        tz_list = [pytz.all_timezones[x:x+15]
                   for x in range(0, len(pytz.all_timezones), 15)]
        embeds = self._gen_tz_embeds(str(ctx.author), tz_list)
        pages = menus.MenuPages(source=TZMenuSource(range(0, 40), embeds))
        await pages.start(ctx)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def time(self, ctx: commands.Context, *, member: discord.Member = None):
        """ Let's look at storing member's tz. """
        if ctx.invoked_subcommand:
            pass
        member = member or ctx.author
        query = """SELECT *
                   FROM tz_store
                   WHERE user_id = $1
                   AND guild_id = $2;
                """
        result = await self.bot.pool.fetchrow(query, member.id, ctx.guild.id)
        if not result:
            return await ctx.send(f"No timezone for {member} set.")
        member_timezone = result['tz']
        current_time = self._curr_tz_time(member_timezone, ret_datetime=False)
        embed = discord.Embed(
            title=f"Time for {member}",
            description=f"```py\n{current_time}```"
        )
        embed.set_footer(text=member_timezone)
        embed.timestamp = datetime.utcnow()
        return await ctx.send(embed=embed)

    @time.command(name="set")
    @commands.guild_only()
    async def _set(self, ctx, *, set_timezone: str):
        """ Add your time zone, with a warning about public info. """
        set_timezone = self._verify_tz(set_timezone)
        if not set_timezone:
            return await ctx.send("This doesn't appear to be a valid timezone.")
        query = """ INSERT INTO tz_store (user_id, guild_id, tz)
                    VALUES ($1, $2, $3)
                    ON CONFLICT ON CONSTRAINT unique_guild_user
                    DO UPDATE SET tz = $3;
                """
        confirm = await ctx.prompt("This will make your timezone public in this guild, confirm?",
                                   reacquire=False)
        if not confirm:
            return
        await self.bot.pool.execute(query, ctx.author.id, ctx.guild.id, set_timezone)
        return await ctx.message.add_reaction(self.bot.emoji[True])

    @time.command(name="remove")
    @commands.guild_only()
    async def _remove(self, ctx):
        """ Remove your timezone from this guild. """
        query = "DELETE FROM tz_store WHERE user_id = $1 and guild_id = $2;"
        await self.bot.pool.execute(query, ctx.author.id, ctx.guild.id)
        return await ctx.message.add_reaction(self.bot.emoji[True])

    @time.command(name="clear")
    async def _clear(self, ctx):
        """ Clears your timezones from all guilds. """
        query = "DELETE FROM tz_store WHERE user_id = $1;"
        confirm = await ctx.prompt("Are you sure you wish to purge your timezone from all guilds?")
        if not confirm:
            return
        await self.bot.pool.execute(query, ctx.author.id)
        return await ctx.message.add_reaction(self.bot.emoji[True])

    async def time_error(self, ctx, error):
        """ Quick error handling for timezones. """
        error = getattr(error, "original", error)
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send("How am I supposed to do this if you don't supply the timezone?")


def setup(bot):
    """ Cog entrypoint. """
    bot.add_cog(Time(bot))
