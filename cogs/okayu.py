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

from jishaku.codeblocks import codeblock_converter

import discord
from discord.ext import commands


class Okayu(commands.Cog):
    """ Okayu admin commands. """
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="hello")
    async def hello(self, ctx: commands.Context):
        file = discord.File("static/okayu.jpg", filename="okayu.jpg")
        embed = discord.Embed(colour=self.bot.colour['dsc'])
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
