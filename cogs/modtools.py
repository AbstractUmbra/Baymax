""" ModTools cog. """

import asyncio
import logging
import sqlite3
import tempfile
import traceback

import discord
from discord.ext import commands

from utils.converters import CommandConverter
from . import BaseCog


class ToLower(str):
    """ Lowers arguments to lowercase. """
    @classmethod
    async def convert(cls, ctx, argument):
        """ Converter for lowercase. """
        arg = await commands.clean_content().convert(ctx, argument)
        return arg.lower()


async def filter_history(channel, **kwargs):
    """ history filter. """
    check = kwargs.pop('check', lambda m: True)
    limit = kwargs.pop('limit', None)
    count = 0
    async for message in channel.history(limit=None, **kwargs):
        if check(message):
            yield message
            count += 1
            if count == limit:
                break


class ModTools(BaseCog):
    """ ModTools cog. """
    prefix = 'r!'
    game = 'r!help'
    disabled_commands = set()
    disabled_cogs = set()
    debug = False
    config_attrs = 'prefix', 'game', 'disabled_commands', 'disabled_cogs', 'debug'

    def __init__(self, bot):
        super().__init__(bot)
        for name in list(self.disabled_commands):
            cmd = self.bot.get_command(name)
            if cmd:
                cmd.enabled = False
            else:
                self.disabled_commands.discard(name)

    async def init_db(self, sql):
        await sql.execute(
            "create table if not exists prefixes "
            "(guild integer not null primary key, prefix text not null default \"r!\")"
        )

    def cog_unload(self):
        for name in list(self.disabled_commands):
            cmd = self.bot.get_command(name)
            if cmd:
                cmd.enabled = True
            else:
                self.disabled_commands.discard(name)

    async def cog_check(self, ctx: commands.Context):
        if not await self.bot.is_owner(ctx.author):
            raise commands.NotOwner('You do not own this bot')
        return True

    @commands.has_any_role(262403103054102528, 337723529837674496, 534447855608266772)
    @commands.group(case_insensitive=True)
    async def admin(self, ctx):
        """Commands for the admin console"""

    @commands.has_any_role(262403103054102528, 337723529837674496, 534447855608266772)
    @admin.group(case_insensitive=True)
    async def display(self, ctx):
        """Commands to manage the bot's appearance"""

    @display.command(name='nick')
    @commands.bot_has_permissions(change_nickname=True)
    async def change_nick(self, ctx: commands.Context, *, nickname: commands.clean_content = None):
        """Change or reset the bot's nickname"""

        await ctx.me.edit(nick=nickname)
        await ctx.send('OwO')

    @display.command(name='game')
    async def change_game(self, ctx: commands.Context, *, game: str = None):
        """Change or reset the bot's presence"""

        game = game or f'{ctx.prefix}help'
        activity = discord.Game(game)
        await self.bot.change_presence(activity=activity)
        self.game = game
        await ctx.send(f'I\'m now playing {game}')

    @display.command(name='avatar')
    @commands.check(lambda ctx: len(ctx.message.attachments) == 1)
    async def change_avatar(self, ctx: commands.Context):
        """ Change the bot's avatar. """
        with tempfile.TemporaryFile() as tmp:
            await ctx.message.attachments[0].save(tmp)
            await self.bot.user.edit(avatar=tmp.read())
        await ctx.message.add_reaction('✔')

    @admin.command(name="id")
    async def get_channel_id(self, ctx, channel: discord.TextChannel = None):
        """ List the ID of a passed channel or current channel. """
        if channel is None:
            channel = ctx.channel
        await ctx.send(f"{channel.name}: `{channel.id}`", delete_after=20)

    @admin.command(name="ids")
    async def get_all_ids(self, ctx):
        """ prints all IDs in an embed. """
        texties = ctx.guild.text_channels
        voicies = ctx.guild.voice_channels
        texties_string = "\n".join(
            f"{chann.name}: {chann.id}" for chann in texties)
        voicies_string = "\n".join(
            f"{chann.name}: {chann.id}" for chann in voicies)
        id_embed = discord.Embed(title=f"IDs for {ctx.guild.name}",
                                 description="List of all IDs.",
                                 colour=ctx.author.colour)
        id_embed.set_author(icon_url=self.bot.user.avatar_url,
                            name=self.bot.user.name)
        id_embed.add_field(name="Text Channels",
                           value=f"{texties_string}", inline=True)
        id_embed.add_field(name="Voice Channels",
                           value=f"{voicies_string}", inline=True)
        await ctx.author.send(embed=id_embed)

    @admin.command()
    async def perms(self, ctx, role: discord.Member = None):
        """ Print the passed user perms to the console. """
        if role is None:
            role = ctx.author
        user_roles = '\n'.join(
            perm for perm, value in role.guild_permissions if value)
        role_embed = discord.Embed(title=f"User roles for {role}",
                                   description=f"Server: {ctx.guild.name}",
                                   colour=role.colour)
        role_embed.set_author(icon_url=role.avatar_url, name=str(role))
        role_embed.add_field(
            name="\uFEFF", value=user_roles, inline=True)
        await ctx.author.send(embed=role_embed)

    @admin.command(hidden=True)
    @commands.has_any_role(262403103054102528, 337723529837674496, 534447855608266772)
    async def summon(self, ctx, member: discord.Member):
        """ Summon a voice member to current executors voice channel. """
        if member.voice.channel is ctx.message.author.voice.channel:
            await ctx.send(f"They're already in your voice chat, you wank.",
                           delete_after=5)
        else:
            await member.move_to(ctx.message.author.voice.channel)

    @admin.command(name='sql')
    async def call_sql(self, ctx, *, script):
        """Run arbitrary sql command"""
        async with self.bot.sql as sql:
            await sql.executescript(script)
        await ctx.send('Script successfully executed')

    @call_sql.error
    async def sql_error(self, ctx, exc):
        """ On sql error. """
        if isinstance(exc, sqlite3.Error):
            traceb = traceback.format_exc(limit=3)
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name='Traceback', value=f'```{traceb}```')
            await ctx.send('The script failed with an error (check your syntax?)', embed=embed)
        self.log_tb(ctx, exc)

    @admin.command(name='oauth')
    async def send_oauth(self, ctx: commands.Context):
        """Sends the bot's OAUTH token."""
        await self.bot.owner.send(self.bot.http.token)
        await ctx.message.add_reaction('✅')

    @admin.group(name='command', )
    async def admin_cmd(self, ctx: commands.Context):
        """Manage bot commands"""

    @admin_cmd.command(name='disable')
    async def disable_command(self, ctx: commands.Context, *, cmd: CommandConverter):
        """Disable a command"""
        if cmd.name in self.disabled_commands:
            await ctx.send(f'{cmd} is already disabled')
        else:
            self.disabled_commands.add(cmd.name)
            cmd.enabled = False
            await ctx.message.add_reaction('✅')

    @admin_cmd.command(name='enable')
    async def enable_command(self, ctx: commands.Context, *, cmd: CommandConverter):
        """Enable a command"""
        if cmd.name in self.disabled_commands:
            self.disabled_commands.discard(cmd.name)
            cmd.enabled = True
            await ctx.message.add_reaction('✅')
        else:
            await ctx.send(f'{cmd} is already enabled')

    @admin_cmd.error
    async def admin_cmd_error(self, ctx: commands.Context, exc: Exception):
        """ On error with admin commands. """
        if isinstance(exc, commands.ConversionError):
            await ctx.send(f'Command "{exc.original.args[0]}" not found')

    @admin.group()
    async def cog(self, ctx):
        """Manage bot cogs"""

    async def git_pull(self, ctx):
        """ Update the bot. """
        async with ctx.typing():
            fut = await asyncio.create_subprocess_shell('git pull', loop=self.bot.loop)
            await fut.wait()
        return fut.returncode == 0

    @cog.command(name='disable')
    async def disable_cog(self, ctx, *cogs: ToLower):
        """Disable cogs"""
        for cog in cogs:
            if cog == self.__class__.__name__.lower():
                await ctx.send(f'Cannot unload the {cog} cog!!')
                continue
            if cog in self.disabled_cogs:
                await ctx.send(f'BaseCog "{cog}" already disabled')
                continue
            try:
                await self.bot.loop.run_in_executor(
                    None,
                    self.bot.unload_extension,
                    f'cogs.{cog}')
            except Exception as err:
                await ctx.send(f'Failed to unload cog "{cog}" ({err})')
            else:
                await ctx.send(f'Unloaded cog "{cog}"')
                self.disabled_cogs.add(cog)

    @cog.command(name='enable')
    async def enable_cog(self, ctx, *cogs: ToLower):
        """Enable cogs"""
        await self.git_pull(ctx)
        for cog in cogs:
            if cog not in self.disabled_cogs:
                await ctx.send(f'BaseCog "{cog}" already enabled or does not exist')
                continue
            try:
                await self.bot.loop.run_in_executor(None, self.bot.load_extension, f"cogs.{cog}")
            except discord.ClientException as err:
                await ctx.send(f'Failed to load cog: "{cog}" ({err})', delete_after=5)
            else:
                await ctx.send(f'Loaded cog: "{cog}"', delete_after=5)
                self.disabled_cogs.discard(cog)

    @cog.command(name='reload')
    async def reload_cog(self, ctx: commands.Context, *cogs: ToLower):
        """Reload cogs"""
        await self.git_pull(ctx)
        for cog in cogs:
            extn = f'cogs.{cog}'
            if extn in self.bot.extensions:
                try:
                    await self.bot.loop.run_in_executor(None, self.bot.reload_extension, extn)
                except discord.ClientException as err:
                    if cog == self.__class__.__name__.lower():
                        name_title = cog.title().replace('_', '')
                        await ctx.send(
                            f'Could not reload: {cog}. {name_title} will be unavailable. ({err})',
                            delete_after=5)
                    else:
                        self.disabled_cogs.add(cog)
                        await ctx.send(
                            f'Could not reload: {cog}, so it shall be disabled ({err})',
                            delete_after=5)
                else:
                    await ctx.send(f'Reloaded cog {cog}')
            else:
                await ctx.send(f'Cog {cog} not loaded, use {self.load_cog.qualified_name} instead')

    @cog.command(name='load')
    async def load_cog(self, ctx: commands.Context, *cogs: ToLower):
        """Load cogs that aren't already loaded"""

        await self.git_pull(ctx)
        for cog in cogs:
            if cog in self.disabled_cogs:
                await ctx.send(f'BaseCog: "{cog}" is disabled!')
                continue
            async with ctx.typing():
                try:
                    await self.bot.loop.run_in_executor(
                        None,
                        self.bot.load_extension,
                        f"cogs.{cog}")
                except discord.ClientException as err:
                    await ctx.send(f'Could not load: {cog}: {err}', delete_after=5)
                else:
                    await ctx.send(f'Loaded cog: {cog}', delete_after=5)

    @admin.command(name='debug')
    async def toggle_debug(self, ctx):
        """Toggle debug mode"""

        self.debug = not self.debug
        await ctx.send(f'Set debug mode to {"on" if self.debug else "off"}')

    @admin.command(name='log', aliases=['logs'])
    async def send_log(self, ctx):
        """DM the logfile to the bot's owner"""

        handler = discord.utils.find(lambda h: isinstance(
            h, logging.FileHandler), self.bot.logger.handlers)
        if handler is None:
            await ctx.send('No log file handler is registered')
        else:
            await ctx.author.send(file=discord.File(handler.baseFilename))
            await ctx.message.add_reaction('✅')

    @admin.command(name='prefix')
    async def change_prefix(self, ctx, prefix='r!'):
        """Update the bot's command prefix"""

        async with self.bot.sql as sql:
            await sql.set_prefix(ctx.guild, prefix)
        self.bot.guild_prefixes[ctx.guild.id] = prefix
        await ctx.message.add_reaction('✅')

    @cog.command(name='list')
    async def list_cogs(self, ctx):
        """ List all cogs. """
        await ctx.send('```\n' + '\n'.join(self.bot.cogs) + '\n```')

    async def cog_command_error(self, ctx, error):
        """ On command error. """
        await ctx.message.add_reaction('❌')
        await ctx.send(f'**{error.__class__.__name__}**: {error}', delete_after=10)
        self.log_tb(ctx, error)

    @commands.command(name='cl')
    async def fast_cog_load(self, ctx, *cogs: ToLower):
        """ Quickly load a cog. """
        await ctx.invoke(self.load_cog, *cogs)

    @commands.command(name='cr')
    async def fast_cog_reload(self, ctx, *cogs: ToLower):
        """ Quckly reload a cog. """
        await ctx.invoke(self.reload_cog, *cogs)


def setup(bot):
    """ Cog setup. """
    bot.add_cog(ModTools(bot))
