"""
Robo-Hz Discord Bot
Copyright (C) 2020 64Hz

Robo-Hz is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Robo-Hz is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with Robo-Hz. If not, see <https://www.gnu.org/licenses/>.
"""

import io

import discord
from discord.ext import commands
import googletrans

from utils import checks


class Funhouse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def cat(self, ctx):
        """Gives you a random cat."""
        async with ctx.session.get('https://api.thecatapi.com/v1/images/search') as resp:
            if resp.status != 200:
                return await ctx.send('No cat found :(')
            js = await resp.json()
            await ctx.send(embed=discord.Embed(title='Random Cat').set_image(url=js[0]['url']))

    @commands.command(hidden=True)
    async def dog(self, ctx):
        """Gives you a random dog."""
        async with ctx.session.get('https://random.dog/woof') as resp:
            if resp.status != 200:
                return await ctx.send('No dog found :(')

            filename = await resp.text()
            url = f'https://random.dog/{filename}'
            filesize = ctx.guild.filesize_limit if ctx.guild else 8388608
            if filename.endswith(('.mp4', '.webm')):
                async with ctx.typing():
                    async with ctx.session.get(url) as other:
                        if other.status != 200:
                            return await ctx.send('Could not download dog video :(')

                        if int(other.headers['Content-Length']) >= filesize:
                            return await ctx.send(f'Video was too big to upload... See it here: {url} instead.')

                        fp = io.BytesIO(await other.read())
                        await ctx.send(file=discord.File(fp, filename=filename))
            else:
                await ctx.send(embed=discord.Embed(title='Random Dog').set_image(url=url))

    @commands.command(hidden=True)
    async def translate(self, ctx, *, message: commands.clean_content):
        """Translates a message to English using Google translate."""

        loop = self.bot.loop

        try:
            ret = await loop.run_in_executor(None, self.trans.translate, message)
        except Exception as e:
            return await ctx.send(f'An error occurred: {e.__class__.__name__}: {e}')

        embed = discord.Embed(title='Translated', colour=0x4284F3)
        src = googletrans.LANGUAGES.get(ret.src, '(auto-detected)').title()
        dest = googletrans.LANGUAGES.get(ret.dest, 'Unknown').title()
        embed.add_field(name=f'From {src}', value=ret.origin, inline=False)
        embed.add_field(name=f'To {dest}', value=ret.text, inline=False)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Funhouse(bot))
