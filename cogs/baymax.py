import discord
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter

class Baymax(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["fistbump"])
    async def boop(self, ctx: commands.Context):
        """ Boops to you. """
        embed = discord.Embed()
        file = discord.File("./static/boop.gif", filename="fistbump.gif")
        embed.set_image(url="attachment://fistbump.gif")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def hello(self, ctx: commands.Context):
        embed = discord.Embed()
        file = discord.File("./static/hello.gif", filename="hello.gif")
        embed.set_image(url="attachment://hello.gif")
        await ctx.send("Hi, I'm Baymax. Umbra#0009 created me.", file=file, embed=embed)

    @commands.group(invoke_without_command=True)
    async def baymax(self, ctx: commands.Context):
        """ This is purely for subcommands. """

    @baymax.command()
    @commands.is_owner()
    async def core(self, ctx: commands.Context, *, body: codeblock_converter):
        """ Directly evaluate Baymax core code. """
        jsk = self.bot.get_command("jishaku python")
        await jsk(ctx, argument=body)

    @baymax.command()
    @commands.is_owner()
    async def system(self, ctx: commands.Context, *, body: codeblock_converter):
        """ Directly evaluate Baymax system code. """
        jsk = self.bot.get_command("jishaku shell")
        await jsk(ctx, argument=body)

    @baymax.command(aliases=["sauce"])
    @commands.is_owner()
    async def source(self, ctx: commands.Context, *, command: str):
        """ Show Baymax system code. """
        jsk = self.bot.get_command("jishaku source")
        await jsk(ctx, command_name=command)

    @baymax.command(aliases=["debug"])
    @commands.is_owner()
    async def diagnose(self, ctx: commands.Context, *, command_name: str):
        """ Diagnose Baymax features. """
        jsk = self.bot.get_command("jishaku debug")
        await jsk(ctx, command_string=command_name)

def setup(bot):
    bot.add_cog(Baymax(bot))
