import discord
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter


class Okayu(commands.Cog):
    """ Okayu specific commands. """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="hello")
    async def hello(self, ctx: commands.Context):
        """ Say hello to Okayu-sama. """
        file = discord.File("static/okayu.jpg", filename="okayu.jpg")
        embed = discord.Embed(colour=self.bot.colour["dsc"])
        embed.set_image(url="attachment://okayu.jpg")
        await ctx.send(f"モグ モグ!\n\n{self.bot.description}", embed=embed, file=file)

    @commands.group(invoke_without_command=True)
    async def okayu(self, ctx: commands.Context):
        """ This is purely for subcommands. """

    @okayu.command()
    @commands.is_owner()
    async def core(self, ctx: commands.Context, *, body: codeblock_converter):
        """ Directly evaluate Okayu core code. """
        jsk = self.bot.get_command("jishaku python")
        await jsk(ctx, argument=body)

    @okayu.command()
    @commands.is_owner()
    async def system(self, ctx: commands.Context, *, body: codeblock_converter):
        """ Directly evaluate Okayu system code. """
        jsk = self.bot.get_command("jishaku shell")
        await jsk(ctx, argument=body)

    @okayu.command(aliases=["sauce"])
    @commands.is_owner()
    async def source(self, ctx: commands.Context, *, command: str):
        """ Show Okayu system code. """
        jsk = self.bot.get_command("jishaku source")
        await jsk(ctx, command_name=command)

    @okayu.command(aliases=["debug"])
    @commands.is_owner()
    async def diagnose(self, ctx: commands.Context, *, command_name: str):
        """ Diagnose Okayu features. """
        jsk = self.bot.get_command("jishaku debug")
        await jsk(ctx, command_string=command_name)

    @okayu.command()
    @commands.is_owner()
    async def sleep(self, ctx):
        """ Okayu naptime. """
        await ctx.send("さようなら!")
        await self.bot.logout()


def setup(bot):
    bot.add_cog(Okayu(bot))
