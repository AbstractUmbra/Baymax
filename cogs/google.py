"""
This code and all contents are responsibly sourced from
chr1sBot discord bot and author
(https://github.com/crrapi) | (https://github.com/crrapi/chr1sBot)
chr1sbot licensing below:

chr1sBot Discord Bot

Copyright(C) 2020 crrapi

chr1sBot is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

chr1sBot is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with chr1sBot. If not, see < https: // www.gnu.org/licenses/>.
"""

import time
import async_cse
import discord
from discord.ext import commands, menus


class GoogleMenuSource(menus.ListPageSource):
    """ Format discord.ext.menus for Google searches. """

    def __init__(self, data, embeds):
        self.data = data
        self.embeds = embeds
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        """ Format each page correctly. """
        return self.embeds[entries]


class Google(commands.Cog):
    """ Google cog for Robo-Hz. """

    def __init__(self, bot):
        self.bot = bot
        self.google = async_cse.Search(self.bot.config.google_key)

    def cog_unload(self):
        self.bot.loop.create_task(self.google.close())

    def _gen_embeds(self, responses, footer, images):
        embeds = []
        for resp in responses:
            embed = discord.Embed(
                title=resp.title,
                description=resp.description,
                colour=discord.Colour.red(),
                url=resp.url
            )
            if images:
                embed.set_image(url=resp.image_url)
            else:
                if resp.image_url != resp.url:
                    embed.set_thumbnail(url=resp.image_url)
            fmt = f"Result {responses.index(resp)}/{len(responses)-1}"
            embed.set_footer(text=f"{fmt} | {footer}")
            embeds.append(embed)
        return embeds

    async def _perform_search(self, ctx, query, images):
        try:
            start = time.time()
            if ctx.channel.is_nsfw():
                safesearch = "off"
                resp = await self.google.search(query, safesearch=False, image_search=images)
            else:
                safesearch = "on"
                resp = await self.google.search(query, safesearch=True, image_search=images)
        except async_cse.NoResults:
            return await ctx.send("No results found. :-(")
        except (async_cse.NoMoreRequests, async_cse.APIError) as err:
            return await ctx.send(f"An error occurred during Google operation: {err}")
        else:
            end = time.time()
            footer = f"{end - start:.2f}s | SafeSearch is {safesearch}."
            return self._gen_embeds(resp, footer, images)

    @commands.group(name="google", invoke_without_command=True, aliases=["g", "search"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def _google(self, ctx, *, query: str):
        """ Searches google for stuff, wooo. """
        embeds = await self._perform_search(ctx, query, images=False)
        pages = menus.MenuPages(source=GoogleMenuSource(
            range(1, 10), embeds), clear_reactions_after=True)
        await pages.start(ctx)

    @_google.command(aliases=["i", "pics"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def _image(self, ctx, *, query: str):
        """ Searches for images instead. """
        embeds = await self._perform_search(ctx, query, images=True)
        pages = menus.MenuPages(source=GoogleMenuSource(
            range(1, 10), embeds), clear_reactions_after=True)
        await pages.start(ctx)

    @_google.error
    async def google_err_handler(self, ctx, error):
        """ local error hadnler for google. """
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"On cooldown for you for another {error.retry_after:.2f} seconds.")


def setup(bot):
    """ Cog entrypoint. """
    bot.add_cog(Google(bot))
