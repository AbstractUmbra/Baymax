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

import argparse
import json
import shlex
from collections import namedtuple

import discord
from discord.ext import commands, menus

from utils import cache, db

class BlacklistedGelbooru(commands.CommandError):
    """ Error raised when you request a blacklisted tag. """
    def __init__(self, tags: set):
        self.blacklisted_tags = tags
        self.blacklist_tags_fmt = " | ".join(list(tags))
        super().__init__("Bad Bootu tags.")

    def __str__(self):
        return f"Found blacklisted tags in query: `{self.blacklist_tags_fmt}`."

class GelbooruConfigTable(db.Table, table_name="gelbooru_config"):
    """ Database ORM fun. """
    guild_id = db.Column(db.Integer(big=True), primary_key=True)

    blacklist = db.Column(db.Array(db.String()))

class GelbooruConfig:
    """ Config object per guild. """
    def __init__(self, *, guild_id: int, bot: commands.Bot, record = None):
        self.guild_id = guild_id
        self.bot = bot
        self.record = record

        if record:
            self.blacklist = record['blacklist']
        else:
            self.blacklist = []

Gelbooru = namedtuple("Gelbooru", "api_key user_id endpoint")

RATING = {"e": "explicit", "q": "questionable", "s": "safe"}

def campfire_only():
    """ Private guild only check. """
    def predicate(ctx: commands.Context):
        if not ctx.guild:
            return False
        return ctx.guild.id in [766520806289178646, 705500489248145459, 174702278673039360] or ctx.author.id == ctx.bot.owner_id
    return commands.check(predicate)

class GelbooruPageSource(menus.ListPageSource):
    """ Page source for Menus. """
    def __init__(self, data, embeds):
        self.data = data
        self.embeds = embeds
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        return self.embeds[entries]

class GelbooruEntry:
    """ Quick object namespace. """
    def __init__(self, payload: dict):
        """ . """
        self.image = True if (payload['width'] != 0) else False
        self.source = payload.get("source")
        self.gb_id = payload.get("id")
        self.rating = RATING.get(payload.get("rating"))
        self.score = payload.get("score")
        self.url = payload.get("file_url")
        self.raw_tags = payload.get("tags")

    @property
    def tags(self):
        return self.raw_tags.split(" ")

class Lewd(commands.Cog):
    """ Lewd cog. """

    def __init__(self, bot):
        self.bot = bot
        self.gelbooru_config = Gelbooru(
            bot.config.gelbooru_api['api_key'], bot.config.gelbooru_api['user_id'], "https://gelbooru.com/index.php?page=dapi&s=post&q=index")

    async def cog_command_error(self, ctx, error):
        error = getattr(error, "original", error)

        if isinstance(error, BlacklistedGelbooru):
            return await ctx.send(error)
        elif isinstance(error, commands.BadArgument):
            return await ctx.send(error)

    @cache.cache()
    async def get_gelbooru_config(self, guild_id, *, connection=None):
        connection = connection or self.bot.pool
        query = """ SELECT * FROM gelbooru_config WHERE guild_id = $1; """
        record = await connection.fetchrow(query, guild_id)
        return GelbooruConfig(guild_id=guild_id, bot=self.bot, record=record)

    def _gen_embeds(self, payloads: list, config: GelbooruConfig):
        embeds = []
        blacklisted_tags = config.blacklist

        for item in payloads:
            new_item = GelbooruEntry(item)

            # blacklist check
            set_blacklist = set(blacklisted_tags)
            set_tags = set(new_item.tags)
            if set_blacklist & set_tags:
                continue

            embed = discord.Embed(colour=discord.Colour(0x000001))

            if new_item.image:
                embed.set_image(url=new_item.url)
            else:
                # video
                embed.add_field(name="Video - Source:-", value=f"[Click here!]({new_item.url})")

            fmt = f"ID: {new_item.gb_id} | Rating: {new_item.rating.capitalize()}"
            embed.set_footer(text=fmt)

            if new_item.source:
                embed.add_field(name="Source:", value=new_item.source)

            embeds.append(embed)

        return embeds


    @commands.group(hidden=True, usage="<flags>+ | subcommand", invoke_without_command=True)
    @campfire_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def gelbooru(self, ctx: commands.Context, *, params: str):
        """This command uses a flag style syntax.
        The following options are valid.

        `+t | ++tags`: The tags to search Gelbooru for. `*`
        `+l | ++limit`: The limit of the amount of posts to search for, limits to 30 max.
        `+p | ++pid`: Page ID to search. Handy when posts begin to repeat.
        `+c | ++cid`: Change ID of the post to search for(?)

        `*` denotes it is a mandatory argument.
        """
        aiohttp_params = self.bot.config.gelbooru_api
        aiohttp_params.update({"json": 1})
        parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False, prefix_chars="+")
        parser.add_argument("+l", "++limit", type=int, default=30)
        parser.add_argument("+p", "++pid", type=int)
        parser.add_argument("+t", "++tags", nargs="+", required=True)
        parser.add_argument("+c", "++cid", type=int)
        try:
            real_args = parser.parse_args(shlex.split(params))
        except SystemExit as fuck:
            raise commands.BadArgument("Your flags could not be parsed.") from fuck
        except Exception as err:
            await ctx.send(f"Parsing your args failed: {err}")
            return

        current_config = await self.get_gelbooru_config(ctx.guild.id)

        if real_args.limit:
            aiohttp_params.update({"limit": int(real_args.limit)})
        if real_args.pid:
            aiohttp_params.update({"pid": real_args.pid})
        if real_args.tags:
            lowered_tags = [tag.lower() for tag in real_args.tags]
            tags_set = set(lowered_tags)
            blacklist_set = set(current_config.blacklist)
            if tags_set & blacklist_set:
                raise BlacklistedGelbooru((tags_set & blacklist_set))
            aiohttp_params.update({"tags": " ".join(lowered_tags)})
        if real_args.cid:
            aiohttp_params.update({"cid", real_args.cid})

        new_json_data = []

        async with self.bot.session.get(self.gelbooru_config.endpoint, params=aiohttp_params) as resp:
            data = await resp.text()
            json_data = json.loads(data)
            nsfw = ctx.channel.is_nsfw()
            for gb_dict in json_data:
                if gb_dict['rating'] in ("q", "e") and not nsfw:
                    continue
                else:
                    new_json_data.append(gb_dict)

        if not new_json_data:
            raise commands.BadArgument("The specified query returned no results.")

        embeds = self._gen_embeds(new_json_data, current_config)
        pages = menus.MenuPages(source=GelbooruPageSource(range(0, 30), embeds), delete_message_after=True)
        await pages.start(ctx)

    @gelbooru.group(invoke_without_command=True)
    @campfire_only()
    @commands.has_permissions(manage_messages=True)
    async def blacklist(self, ctx: commands.Context):
        """ Blacklist management for gelbooru command. """

    @blacklist.command()
    @campfire_only()
    @commands.has_permissions(manage_messages=True)
    async def add(self, ctx: commands.Context, *, tags: str):
        """ Add an item to the blacklist. """
        query = """ INSERT INTO gelbooru_config (guild_id, blacklist)
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id)
                    DO UPDATE SET blacklist = gelbooru_config.blacklist || $2;
                """
        list_tags = tags.split(" ")
        iterable = [(ctx.guild.id, [tag.lower()]) for tag in list_tags]
        try:
            await self.bot.pool.executemany(query, iterable)
        finally:
            self.get_gelbooru_config.invalidate()
            await ctx.message.add_reaction(self.bot.emoji[True])

    @blacklist.command()
    @campfire_only()
    @commands.has_permissions(manage_messages=True)
    async def remove(self, ctx: commands.Context, *, tags: str):
        """ Remove an item from the blacklist. """
        query = """ UPDATE gelbooru_config
                    SET blacklist = array_remove(gelbooru_config.blacklist, $2)
                    WHERE guild_id = $1;
                """
        tags = tags.split(" ")
        iterable = [(ctx.guild.id, tag) for tag in tags]
        try:
            await self.bot.pool.executemany(query, iterable)
        finally:
            self.get_gelbooru_config.invalidate()
            await ctx.message.add_reaction(self.bot.emoji[True])


def setup(bot):
    bot.add_cog(Lewd(bot))
