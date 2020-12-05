import logging
import re

import discord
from discord.ext import commands, menus
from utils.paginator import RoboPages

log = logging.getLogger(__name__)


class UrbanDictionaryPageSource(menus.ListPageSource):
    BRACKETED = re.compile(r"(\[(.+?)\])")

    def __init__(self, data):
        super().__init__(entries=data, per_page=1)

    def cleanup_definition(self, definition, *, regex=BRACKETED):
        def repl(m):
            word = m.group(2)
            return f'[{word}](http://{word.replace(" ", "-")}.urbanup.com)'

        ret = regex.sub(repl, definition)
        if len(ret) >= 2048:
            return ret[0:2000] + " [...]"
        return ret

    async def format_page(self, menu, entry):
        maximum = self.get_max_pages()
        title = (
            f'{entry["word"]}: {menu.current_page + 1} out of {maximum}'
            if maximum
            else entry["word"]
        )
        embed = discord.Embed(title=title, colour=0xE86222, url=entry["permalink"])
        embed.set_footer(text=f'by {entry["author"]}')
        embed.description = self.cleanup_definition(entry["definition"])

        try:
            up, down = entry["thumbs_up"], entry["thumbs_down"]
        except KeyError:
            pass
        else:
            embed.add_field(
                name="Votes",
                value=f"\N{THUMBS UP SIGN} {up} \N{THUMBS DOWN SIGN} {down}",
                inline=False,
            )

        try:
            date = discord.utils.parse_time(entry["written_on"][0:-1])
        except (ValueError, KeyError):
            pass
        else:
            embed.timestamp = date

        return embed


class Urban(commands.Cog):
    """ A cog purely for Urban dictionary definitions. """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="urban")
    async def _urban(self, ctx, *, word):
        """Searches urban dictionary."""

        url = "http://api.urbandictionary.com/v0/define"
        async with ctx.session.get(url, params={"term": word}) as resp:
            if resp.status != 200:
                return await ctx.send(f"An error occurred: {resp.status} {resp.reason}")

            js = await resp.json()
            data = js.get("list", [])
            if not data:
                return await ctx.send("No results found, sorry.")

        pages = RoboPages(UrbanDictionaryPageSource(data))
        try:
            await pages.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)


def setup(bot):
    bot.add_cog(Urban(bot))
