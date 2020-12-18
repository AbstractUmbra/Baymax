import asyncio
import datetime
import traceback
from collections import namedtuple

import discord
from discord.ext import commands, tasks
from jishaku.codeblocks import codeblock_converter

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

    def cog_unload(self):
        self.akane_task.cancel()

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

    @tasks.loop(hours=1)
    async def akane_task(self):
        now = datetime.datetime.utcnow()
        if nara := (now.hour >= 6 and now.hour < 18):
            start = datetime.time(hour=18)
        else:
            start = datetime.time(hour=6)

        if now.time() > start:
            now = now.date() + datetime.timedelta(hours=12)
        then = datetime.datetime.combine(now, start)

        await self.webhook_send(f"In task, waitingtil: {then}")
        self.bot.__akane_new = then

        await discord.utils.sleep_until(then)

        profile = self.akane_details[nara]

        name = profile.name
        path = profile.path

        await self.webhook_send(name)

        with open(path, "rb") as buffer:
            return await self.bot.user.edit(username=name, avatar=buffer.read())

    @akane_task.before_loop
    async def before_akane(self):
        await self.bot.wait_until_ready()

        new = datetime.datetime.utcnow()
        if nara := (new.hour >= 6 and new.hour < 18):
            new = new.replace(hour=18, minute=0, second=0)

        profile = self.akane_details[nara]

        name = profile.name
        path = profile.path
        await self.webhook_send(name)

        if (nara and self.bot.user.name != "Akane Dawn") or (
            not nara and self.bot.user.name != "Akane Dusk"
        ):
            with open(path, "rb") as buffer:
                await self.bot.user.edit(username=name, avatar=buffer.read())

        await self.webhook_send(f"waiting til: {new}")
        self.bot.__akane_new = new

        await discord.utils.sleep_until(new)

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
            embed.description = "".join(lines)
            await self.webhook_send(embed=embed)

    async def webhook_send(self, message: str = None, *, embed: discord.Embed = None):
        cog = self.bot.get_cog("Stats")
        if not cog:
            await asyncio.sleep(5)
            return await self.webhook_send(message, embed=embed)
        wh = cog.webhook
        await wh.send(message)


def setup(bot):
    bot.add_cog(Akane(bot))
