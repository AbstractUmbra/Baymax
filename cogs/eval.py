from discord.ext import commands
import io
import textwrap
import traceback
from asyncio.subprocess import PIPE
from contextlib import redirect_stdout
from utils.mystbin import mystbin

import aiohttp

# To expose to eval
import asyncio
import discord
import re
import datetime
from collections import Counter

from . import BaseCog


class Eval(BaseCog):
    _last_result = None

    def __init__(self, bot):
        super().__init__(bot)
        self._running_evals = {}
        self._running_shells = {}

    async def cog_check(self, ctx):
        if ctx.author != self.bot.owner:
            raise commands.NotOwner
        return True

    @staticmethod
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def mask_token(self, value):
        return value.replace(self.bot.http.token, '{TOKEN}')

    @staticmethod
    async def try_add_reaction(message, emoji):
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            pass

    @staticmethod
    def format_tb(exc):
        if exc:
            return ''.join(traceback.format_exception(exc.__class__, exc, exc.__traceback__))
        return ''

    async def format_embed_value(self, embed, name, content):
        if content not in ('', None):
            content = format(content)
            content = self.mask_token(content)
            if len(content) >= 1000:
                try:
                    value = await mystbin(content)
                except aiohttp.ClientResponseError:
                    return discord.File(io.StringIO(content), f'{name}.txt')
            else:
                value = f'```{content}```'
            embed.add_field(name=name, value=value)

    async def send_eval_result(self, ctx, exc, title_ok, title_failed, **values):
        errored = exc is not None
        title = title_failed if errored else title_ok
        color = discord.Color.red() if errored else discord.Color.green()
        embed = discord.Embed(title=title, color=color)
        files = [await self.format_embed_value(embed, name, content) for name, content in values.items()]
        await self.try_add_reaction(ctx.message, '❌' if errored else '✅')
        await ctx.send(embed=embed)
        for file in files:
            if file is not None:
                await ctx.send(file=file)

    @commands.has_any_role(262403103054102528, 337723529837674496, 534447855608266772)
    @commands.group(name='eval', invoke_without_command=True)
    async def eval_cmd(self, ctx, *, body):
        """Evaluates a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        try:
            to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        exc = None
        ret = None
        async with ctx.typing():
            try:
                with redirect_stdout(stdout):
                    fut = func()
                    wait = asyncio.create_task(
                        asyncio.wait_for(fut, 60, loop=self.bot.loop))
                    self._running_evals[ctx.channel.id] = wait
                    ret = await wait
            except Exception as e:
                exc = e
            finally:
                self._running_evals.pop(ctx.channel.id, None)
            await self.send_eval_result(
                ctx,
                exc,
                'Eval completed successfully',
                'Process cancelled' if isinstance(
                    exc, asyncio.CancelledError) else 'An exception has occurred',
                ret=ret,
                stdout=stdout.getvalue(),
                traceback=self.format_tb(exc)
            )

    @eval_cmd.command(name='cancel')
    async def eval_cancel(self, ctx):
        fut = self._running_evals.get(ctx.channel.id)
        if fut is None:
            await ctx.send(f'No running eval {self.bot.command_error_emoji}', delete_after=10)
        else:
            fut.cancel()

    @commands.group(name='shell', invoke_without_command=True)
    async def shell_cmd(self, ctx, *, body):
        """Evaluates a shell script"""

        body = self.cleanup_code(body)
        stdout = b''
        stderr = b''

        process = await asyncio.create_subprocess_shell(body, stdout=PIPE, stderr=PIPE, loop=self.bot.loop)
        exc = None
        async with ctx.typing():
            try:
                fut = process.communicate()
                wait = asyncio.create_task(
                    asyncio.wait_for(fut, 60, loop=self.bot.loop))
                self._running_shells[ctx.channel.id] = wait
                stdout, stderr = await wait
            except Exception as e:
                exc = e
            finally:
                self._running_shells.pop(ctx.channel.id, None)

            if process.returncode is not None:
                exc_title = 'An exception has occurred'
            elif isinstance(exc, asyncio.CancelledError):
                exc_title = 'Process cancelled'
            else:
                exc_title = 'Request timed out'
            await self.send_eval_result(
                ctx,
                exc,
                f'Process exited successfully',
                exc_title,
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                traceback=self.format_tb(exc)
            )

    @shell_cmd.command(name='cancel')
    async def shell_cancel(self, ctx):
        fut = self._running_shells.get(ctx.channel.id)
        if fut is None:
            await ctx.send(f'No running shell {self.bot.command_error_emoji}', delete_after=10)
        else:
            fut.cancel()


def setup(bot):
    bot.add_cog(Eval(bot))
