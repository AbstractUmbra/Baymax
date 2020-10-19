import argparse
import json
import shlex
import traceback
from collections import namedtuple

import discord
from discord.ext import commands, menus

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
    def __init__(self, data, embeds):
        self.data = data
        self.embeds = embeds
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        return self.embeds[entries]

class GelbooruEntry:
    def __init__(self, payload: dict):
        """ . """
        self.image = True if (payload['width'] != 0) else False
        self.source = payload.get("source")
        self.gb_id = payload.get("id")
        self.rating = RATING.get(payload.get("rating"))
        self.score = payload.get("score")
        self.url = payload.get("file_url")

class Lewd(commands.Cog):
    """ . """

    def __init__(self, bot):
        self.bot = bot
        self.gelbooru_config = Gelbooru(
            bot.config.gelbooru_api['api_key'], bot.config.gelbooru_api['user_id'], "https://gelbooru.com/index.php?page=dapi&s=post&q=index")

    def _gen_embeds(self, payloads: list):
        embeds = []

        for item in payloads:
            new_item = GelbooruEntry(item)
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


    @commands.command(hidden=True, usage="<flags>+")
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
        except Exception as err:
            return await ctx.send(f"Parsing your args failed: {err}")

        predicates = []

        if real_args.limit:
            predicates.append(real_args.limit)
            aiohttp_params.update({"limit": int(real_args.limit)})
        if real_args.pid:
            predicates.append(real_args.pid)
            aiohttp_params.update({"pid": real_args.pid})
        if real_args.tags:
            predicates.append(real_args.tags)
            aiohttp_params.update({"tags": " ".join(real_args.tags)})
        if real_args.cid:
            predicates.append(real_args.cid)
            aiohttp_params.update({"cid", real_args.cid})
        try:
            async with self.bot.session.get(self.gelbooru_config.endpoint, params=aiohttp_params) as resp:
                data = await resp.text()
                json_data = json.loads(data)
                nsfw = ctx.channel.is_nsfw()
                new_json_data = []
                for gb_dict in json_data:
                    if gb_dict['rating'] in ("q", "e") and not nsfw:
                        continue
                    else:
                        new_json_data.append(gb_dict)
        except Exception as err:
            tb_lines = "".join(traceback.format_exception(
                type(err), err, err.__traceback__, 4))
            paste = await self.bot.mb_client.post(tb_lines, syntax="python")
            await ctx.send(f" Gelbooru get returned an error: {paste}")

        embeds = self._gen_embeds(new_json_data)
        pages = menus.MenuPages(source=GelbooruPageSource(range(0, 30), embeds), delete_message_after=True)
        await pages.start(ctx)


def setup(bot):
    bot.add_cog(Lewd(bot))
