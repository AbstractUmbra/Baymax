from datetime import datetime
import random

import discord
from discord.ext import commands, menus
import pytz

from utils import db


class TZMenuSource(menus.ListPageSource):
    """ Okay let's make it embeds, I guess. """

    def __init__(self, data, embeds):
        self.data = data
        self.embeds = embeds
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        """ Format each page. """
        return self.embeds[entries]


class TimeTable(db.Table, table_name="tz_store"):
    id = db.PrimaryKeyColumn()

    user_id = db.Column(db.Integer(big=True))
    guild_id = db.Column(db.Integer(big=True))
    tz = db.Column(db.String, unique=True)


class Time(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

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

    def _verify_tz(self, tz: str) -> str:
        lower_tzs = [tz.lower() for tz in pytz.all_timezones]
        if tz.lower() not in lower_tzs:
            return None
        idx = lower_tzs.index(tz.lower())
        tz = pytz.all_timezones[idx]
        return tz

    def _curr_tz_time(self, tz: str, *, dt: bool = False):
        """ We assume it's a good tz here. """
        timezone = pytz.timezone(tz)
        dt_obj = datetime.now(timezone)
        if dt:
            return dt_obj
        if dt_obj.day in [1, 21, 31]:
            date_modif = "st"
        elif dt_obj.day in [2, 22]:
            date_modif = "nd"
        elif dt_obj.day in [3, 23]:
            date_modif = "rd"
        else:
            date_modif = "th"
        return dt_obj.strftime(f"%A %d{date_modif} of %B %Y @ %H:%M %Z%z")

    @commands.command(aliases=['tz'])
    async def timezone(self, ctx: commands.Context, *, tz: str = None) -> discord.Message:
        """ This will return the time in a specified timezone. """
        if not tz:
            tz = random.choice(pytz.all_timezones)
        tz = self._verify_tz(tz)
        if not tz:
            return await ctx.send("This doesn't seem like a valid timezone.")
        embed = discord.Embed(
            title=f"Current time in {tz}",
            description=f"{self._curr_tz_time(tz, dt=False)}"
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
    async def time(self, ctx: commands.Context, member: discord.Member = None):
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
            return await ctx.send("It seems they haven't set a timezone.")
        tz = result['tz']
        current_time = self._curr_tz_time(tz, dt=False)
        embed = discord.Embed(
            title=f"Time for {member}",
            description=f"```py\n{current_time}```"
        )
        return await ctx.send(embed=embed)

    @time.command(name="set")
    @commands.guild_only()
    async def _set(self, ctx, *, tz: str):
        """ Add your time zone, with a warning about public info. """
        tz = self._verify_tz(tz)
        if not tz:
            return await ctx.send("This doesn't appear to be a valid timezone.")
        query = """ INSERT INTO tz_store (user_id, guild_id, tz)
                    VALUES ($1, $2, $3)
                    ON CONFLICT ON CONSTRAINT unique_guild_user
                    DO UPDATE SET tz = $3;
                """
        confirm = await ctx.prompt("This will make your timezone public in this guild, are you sure?",
                                   reacquire=False)
        if not confirm:
            return
        await self.bot.pool.execute(query, ctx.author.id, ctx.guild.id, tz)
        return await ctx.message.add_reaction("<:TickYes:672157420574736386>")

    @time.command(name="remove")
    @commands.guild_only()
    async def _remove(self, ctx):
        """ Remove your timezone from this guild. """
        query = "DELETE FROM tz_store WHERE user_id = $1 and guild_id = $2;"
        await self.bot.pool.execute(query, ctx.author.id, ctx.guild.id)
        return await ctx.message.add_reaction("<:TickYes:672157420574736386>")

    @time.command(name="clear")
    async def _clear(self, ctx):
        """ Clears your timezones from all guilds. """
        query = "DELETE FROM tz_store WHERE user_id = $1;"
        confirm = await ctx.prompt("Are you sure you wish to purge your timezone from all guilds?")
        if not confirm:
            return
        await self.bot.pool.execute(query, ctx.author.id)
        return await ctx.message.add_reaction("<:TickYes:672157420574736386>")

    async def time_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send("How am I supposed to do this if you don't supply the timezone?")


def setup(bot):
    bot.add_cog(Time(bot))
