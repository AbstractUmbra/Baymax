import asyncio
import datetime
import traceback
from collections import namedtuple

import discord
from discord.ext import commands, tasks
from jishaku.codeblocks import codeblock_converter
from utils.formats import to_codeblock

ProfileState = namedtuple("ProfileState", "path name")


class Akane(commands.Cog):
    """ Akane specific commands. """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.akane_task.start()
        self.akane_details = {
            False: ProfileState("static/Dusk.png", "Akane Dusk"),
            True: ProfileState("static/Dawn.jpg", "Akane Dawn"),
        }
        self.akane_time = datetime.datetime.utcnow()
        self.akane_next = None

    def cog_unload(self):
        self.akane_task.cancel()

    async def meme(self):
        dt = datetime.datetime.utcnow()
        while True:
            if nara := dt.hour >= 6 and dt.hour < 18:
                dt.replace(hour=18, minute=0, second=0, microsecond=0)
            else:
                dt.replace(hour=6, minute=0, second=0, microsecond=0)
            await discord.utils.sleep_until(dt)
            self.bot.dispatch("dawn" if nara else "dusk")
            dt += datetime.timedelta(hours=12, seconds=1)

    @commands.command(name="hello")
    async def hello(self, ctx: commands.Context):
        """ Say hello to Akane. """
        now = datetime.datetime.utcnow()
        time = now.hour >= 6 and now.hour < 18
        path = self.akane_details[time].path

        file = discord.File(path, filename="akane.jpg")
        embed = discord.Embed(colour=self.bot.colour["dsc"])
        embed.set_image(url="attachment://akane.jpg")
        embed.description = f"Hello, I am {self.akane_details[time].name}, written by Umbra#0009.\n\nYou should see my other side~"

        await ctx.send(embed=embed, file=file)

    @commands.group(invoke_without_command=True)
    async def akane(self, ctx: commands.Context):
        """ This is purely for subcommands. """

    @akane.command()
    @commands.is_owner()
    async def core(self, ctx: commands.Context, *, body: codeblock_converter):
        """ Directly evaluate Akane core code. """
        jsk = self.bot.get_command("jishaku python")
        await jsk(ctx, argument=body)

    @akane.command()
    @commands.is_owner()
    async def system(self, ctx: commands.Context, *, body: codeblock_converter):
        """ Directly evaluate Akane system code. """
        jsk = self.bot.get_command("jishaku shell")
        await jsk(ctx, argument=body)

    @akane.command(aliases=["sauce"])
    @commands.is_owner()
    async def source(self, ctx: commands.Context, *, command: str):
        """ Show Akane system code. """
        jsk = self.bot.get_command("jishaku source")
        await jsk(ctx, command_name=command)

    @akane.command(aliases=["debug"])
    @commands.is_owner()
    async def diagnose(self, ctx: commands.Context, *, command_name: str):
        """ Diagnose akane features. """
        jsk = self.bot.get_command("jishaku debug")
        await jsk(ctx, command_string=command_name)

    @akane.command()
    @commands.is_owner()
    async def sleep(self, ctx):
        """ Akane naptime. """
        await ctx.send("さようなら!")
        await self.bot.logout()

    @tasks.loop(minutes=5)
    async def akane_task(self):
        now = datetime.datetime.utcnow()
        light = now.hour >= 6 and now.hour < 18
        start = datetime.time(hour=(18 if light else 6))

        if now.time() > start:
            now = now + datetime.timedelta(hours=12)
        then = datetime.datetime.combine(now.date(), start)

        profile = self.akane_details[light]
        name = profile.name
        path = profile.path

        if now > self.akane_time:
            with open(path, "rb") as buffer:
                await self.webhook_send(f"Performing change to: {name}")
                await self.bot.user.edit(username=name, avatar=buffer.read())
                self.akane_time = then

        await self.webhook_send(f"In task, now: {then}")
        self.akane_next = then

    @akane_task.before_loop
    async def before_akane(self):
        await self.bot.wait_until_ready()

        now = datetime.datetime.utcnow()
        light = now.hour >= 6 and now.hour < 18
        start = datetime.time(hour=(18 if light else 6))

        if now.time() > start:
            now = now + datetime.timedelta(hours=12)
        then = datetime.datetime.combine(now.date(), start)

        profile = self.akane_details[light]
        name = profile.name
        path = profile.path
        await self.webhook_send(name)

        if (light and self.bot.user.name != "Akane Dawn") or (
            not light and self.bot.user.name != "Akane Dusk"
        ):
            with open(path, "rb") as buffer:
                await self.webhook_send(f"Drift - changing to: {name}.")
                await self.bot.user.edit(username=name, avatar=buffer.read())

        self.akane_time = then
        await self.webhook_send(f"Before task: waiting until {then}.")
        await discord.utils.sleep_until(then)

    @akane_task.error
    async def akane_error(self, error: Exception):
        error = getattr(error, "original", error)

        if isinstance(error, discord.HTTPException):
            await self.webhook_send("You are ratelimited on profile edits.")
            self.akane_task.cancel()
            self.akane_task.start()
        else:
            embed = discord.Embed(title="Akane Error", colour=discord.Colour.red())
            lines = traceback.format_exception(
                type(error), error, error.__traceback__, 4
            )
            embed.description = to_codeblock("".join(lines))
            await self.webhook_send(embed=embed)

    async def webhook_send(
        self, message: str = "Error", *, embed: discord.Embed = None
    ):
        cog = self.bot.get_cog("Stats")
        if not cog:
            await asyncio.sleep(5)
            return await self.webhook_send(message, embed=embed)
        wh = cog.webhook
        await wh.send(message, embed=embed)


def setup(bot):
    bot.add_cog(Akane(bot))
