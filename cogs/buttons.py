"""
This utility and all contents are responsibly sourced from
RoboDanny discord bot and author
(https://github.com/Rapptz) | (https://github.com/Rapptz/RoboDanny)
RoboDanny licensing below:

The MIT License(MIT)

Copyright(c) 2015 Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files(the "Software"),
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

import logging
import re

import discord
from discord.ext import commands

from utils.paginator import Pages

LOG = logging.getLogger(__name__)


class UrbanDictionaryPages(Pages):
    """ UD Pages. """
    BRACKETED = re.compile(r'(\[(.+?)\])')

    def __init__(self, ctx, data):
        super().__init__(ctx, entries=data, per_page=1)

    def get_page(self, page):
        return self.entries[page - 1]

    def cleanup_definition(self, definition, *, regex=BRACKETED):
        """ Cleans up the returns for display. """
        def repl(msg):
            """ Replaces items where needed. """
            word = msg.group(2)
            return f'[{word}](http://{word.replace(" ", "-")}.urbanup.com)'

        ret = regex.sub(repl, definition)
        if len(ret) >= 2048:
            return ret[0:2000] + ' [...]'
        return ret

    def prepare_embed(self, entry, page, *, first=False):
        """ Tin. Prepares the embed. """
        if self.maximum_pages > 1:
            title = f'{entry["word"]}: {page} out of {self.maximum_pages}'
        else:
            title = entry['word']

        self.embed = embed = discord.Embed(
            colour=0xE86222, title=title, url=entry['permalink'])
        embed.set_footer(text=f'by {entry["author"]}')
        embed.description = self.cleanup_definition(entry['definition'])

        try:
            up_t, down = entry['thumbs_up'], entry['thumbs_down']
        except KeyError:
            pass
        else:
            embed.add_field(
                name='Votes',
                value=f'\N{THUMBS UP SIGN} {up_t} \N{THUMBS DOWN SIGN} {down}',
                inline=False)

        try:
            date = discord.utils.parse_time(entry['written_on'][0:-1])
        except (ValueError, KeyError):
            pass
        else:
            embed.timestamp = date


class Buttons(commands.Cog):
    """Buttons that make you feel."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def feedback(self, ctx, *, content: str):
        """Gives feedback about the bot.

        This is a quick way to request features or bug fixes
        without being in the bot's server.

        The bot will communicate with you via PM about the status
        of your request if possible.

        You can only request feedback once a minute.
        """

        embed = discord.Embed(title='Feedback', colour=0x738bd7)
        channel = self.bot.get_channel(695482983272022107)
        if channel is None:
            return

        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        embed.description = content
        embed.timestamp = ctx.message.created_at

        if ctx.guild is not None:
            embed.add_field(
                name='Server', value=f'{ctx.guild.name} (ID: {ctx.guild.id})', inline=False)

        embed.add_field(
            name='Channel', value=f'{ctx.channel} (ID: {ctx.channel.id})', inline=False)
        embed.set_footer(text=f'Author ID: {ctx.author.id}')

        await channel.send(embed=embed)
        await ctx.send(f'{ctx.tick(True)} Successfully sent feedback')

    @commands.command(name="pm")
    @commands.is_owner()
    async def _pm(self, ctx, user_id: int, *, content: str):
        """ PMs requested users. """
        user = self.bot.get_user(user_id)

        fmt = content + '\n\n*This is a DM sent because you had previously requested' \
                        ' feedback or I found a bug' \
                        ' in a command you used, I do not monitor this DM.*'
        try:
            await user.send(fmt)
        except:
            await ctx.send(f'Could not PM user by ID {user_id}.')
        else:
            await ctx.send('PM successfully sent.')

    @commands.command(name='urban')
    async def _urban(self, ctx, *, word):
        """Searches urban dictionary."""

        url = 'https://api.urbandictionary.com/v0/define'
        async with ctx.session.get(url, params={'term': word}, ssl=False) as resp:
            if resp.status != 200:
                return await ctx.send(f'An error occurred: {resp.status} {resp.reason}')

            js_ret = await resp.json()
            data = js_ret.get('list', [])
            if not data:
                return await ctx.send('No results found, sorry.')

        try:
            pages = UrbanDictionaryPages(ctx, data)
            await pages.paginate()
        except Exception as err:
            await ctx.send(err)


def setup(bot):
    """ Cog entrypoint. """
    bot.add_cog(Buttons(bot))
