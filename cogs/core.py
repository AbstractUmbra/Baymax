""" Core cog. """
from datetime import datetime
from inspect import getsourcelines
from os import path
from typing import Optional
import unicodedata

import discord
from discord.ext import commands

from utils import friendly_date
from utils.converters import CommandConverter
from utils.errors import (
    NotReady,
    BotIsIgnoringUser
)
from . import BaseCog


class Core(BaseCog):
    """ The core cog for RoboHz. """
    banlist = set()
    game = "r!help for help, fuckers."
    config_attrs = "banlist", "game"

    def __init__(self, bot):
        super().__init__(bot)

    async def bot_check(self, ctx: commands.Context):
        """ Check for bot readiness. """
        if not self.bot.is_ready():
            raise NotReady("The bot is not ready to process commands.")
        if not ctx.channel.permissions_for(ctx.me).send_messages:
            raise commands.BotMissingPermissions(['send_messages'])
        if isinstance(ctx.command, commands.Command) and await self.bot.is_owner(ctx.author):
            return True
        if ctx.author.id in self.banlist:
            raise BotIsIgnoringUser(f"I am ignoring {ctx.author}.")
        return True

    @commands.command(aliases=["reboot"])
    @commands.is_owner()
    async def kill(self, ctx: commands.Context):
        """ Restart the bot, owner only. """
        self.bot.reboot_after = ctx.invoked_with == "reboot"
        await ctx.send("Reboot to apply updates.")
        await self.bot.logout()

    @commands.command()
    async def charinfo(self, ctx, *, characters: str):
        """ Shows charinfo. """
        def to_string(char):
            digit = f"{ord(char):x}"
            name = unicodedata.name(char, "Name not found.")
            return f"`\\U{digit:>08}`: {name} - {char} " \
                "\N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>"
        msg = "\n".join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send("Output too long to display.")
        await ctx.send(msg)

    @commands.command()
    @commands.is_owner()
    async def ignore(self, ctx, person: discord.Member):
        """Ban a member"""
        self.banlist.add(person.id)
        await ctx.send(f"{person.display_name} is now banned from interacting with me.")

    @commands.command()
    @commands.is_owner()
    async def unignore(self, ctx, person: discord.Member):
        """Unban a member"""
        self.banlist.discard(person.id)
        await ctx.send(f"{person.display_name} is no longer banned from interacting with me.")

    @commands.command()
    async def about(self, ctx):
        """ Prints a quick about the bot. """
        member: discord.Member = ctx.guild.me
        roles = [r.name.replace('@', '@\u200b') for r in member.roles]
        shared = sum(g.get_member(ctx.author.id)
                     is not None for g in self.bot.guilds)
        embed = discord.Embed()
        embed.set_author(name=str(member))
        embed.add_field(name='ID', value=member.id, inline=False)
        embed.add_field(
            name='Guilds', value=f'{len(self.bot.guilds)} ({shared} shared)', inline=False)
        embed.add_field(name='Joined', value=friendly_date.human_timedelta(
            member.joined_at), inline=False)
        embed.add_field(name='Created', value=friendly_date.human_timedelta(
            member.created_at), inline=False)
        if roles:
            embed.add_field(name='Roles', value=', '.join(roles) if len(
                roles) < 10 else f'{len(roles)} roles', inline=False)
        embed.add_field(name='Source', value='https://github.com/64Hz/RoboHz')
        embed.add_field(name='Uptime',
                        value=f'{datetime.utcnow() - self.bot._alive_since}')
        if member.colour.value:
            embed.colour = member.colour
        if member.avatar:
            embed.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def source(self, ctx, *, command: Optional[CommandConverter]):
        """Links the source of the command. If command source cannot be retrieved,
        links the root of the bot's source tree."""
        url = 'https://github.com/64Hz/Robo-Hz'
        if command is not None:
            src = command.callback.__code__.co_filename
            module = command.callback.__module__.replace('.', path.sep)
            if module in src:
                lines, start = getsourcelines(command.callback)
                sourcefile = src[src.index(module):].replace('\\', '/')
                end = start + len(lines) - 1
                url = f'{url}/blob/master/{sourcefile}#L{start}-L{end}'
        await ctx.send(f'<{url}>')

    @BaseCog.listener()
    async def on_ready(self):
        """ On bot ready. """
        self.bot._alive_since = self.bot._alive_since or datetime.utcnow()

    @commands.command()
    async def uptime(self, ctx):
        """ Quick uptime. """
        date = friendly_date.human_timedelta(self.bot._alive_since)
        await ctx.send(f'Bot last rebooted {date}')


def setup(bot):
    """ Cog entrypoint. """
    bot.add_cog(Core(bot))
