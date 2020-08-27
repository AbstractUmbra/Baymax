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

import discord
from discord.ext import commands


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
        channel = self.bot.get_channel(705501796159848541)
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

    @commands.command(name="pm", hidden=True)
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


def setup(bot):
    """ Cog entrypoint. """
    bot.add_cog(Buttons(bot))
