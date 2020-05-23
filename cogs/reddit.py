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

import typing
from textwrap import shorten

import discord
from discord.ext import commands, menus


class SubredditPageSource(menus.ListPageSource):
    """ For discord.ext.menus to format Subreddit queries. """

    def __init__(self, data, embeds):
        self.data = data
        self.embeds = embeds
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        """ Format each page entry. """
        return self.embeds[entries]


class SubredditPost:
    """ Let's try and create a generic object for a subreddit return... """

    def __init__(self,
                 subreddit_dict: dict,
                 *,
                 video_link: str,
                 image_link: str):
        """ Hrm. """
        self.url = f"https://reddit.com/{subreddit_dict['permalink']}"
        self.resp_url = subreddit_dict['url']
        self.subreddit = subreddit_dict['subreddit_name_prefixed']
        self.title = shorten(subreddit_dict['title'], width=200)
        self.upvotes = int(subreddit_dict['ups'])
        self.text = shorten(subreddit_dict.get('selftext', None), width=2000)
        self.nsfw = subreddit_dict.get('over_18', False)
        self.thumbnail = subreddit_dict.get('thumbnail', None)
        self.comment_count = subreddit_dict.get('num_comments', 0)
        self.author = f"/u/{subreddit_dict['author']}"
        self.video_link = video_link
        self.image_link = image_link


class Reddit(commands.Cog):
    """ For Reddit based queries. """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.headers = {"User-Agent": "Robo-Hz Discord bot"}

    def _gen_embeds(self,
                    requester: str,
                    iterable: list) -> typing.List[discord.Embed]:
        """ Generate many embeds from the top 10 posts on each subreddit. """
        embeds = []

        for item in iterable:
            embed = discord.Embed(
                title=item.title,
                description=item.text,
                colour=discord.Colour.red(),
                url=item.url)

            embed.set_author(name=item.author)

            if item.image_link:
                embed.set_image(url=item.image_link)

            if item.video_link:
                embed.add_field(
                    name="Video", value=f"[Click me!]({item.video_link})", inline=False)

            embed.add_field(name="Upvotes", value=item.upvotes, inline=True)
            embed.add_field(name="Total comments", value=item.comment_count)
            fmt = f"Result {iterable.index(item)+1}/{len(iterable)}"
            embed.set_footer(
                text=f"{fmt} | {item.subreddit} | Requested by: {requester}")

            embeds.append(embed)

        return embeds[:15]

    async def _perform_search(self,
                              requester: str,
                              channel: discord.TextChannel,
                              subreddit: str,
                              sort_by: str):
        """ Performs the search for queries with aiohttp. Returns 10 items. """
        async with self.bot.session.get(
                f"https://reddit.com/r/{subreddit}/about.json",
                headers=self.headers) as subr_top_resp:
            subr_deets = await subr_top_resp.json()

        if 'data' not in subr_deets:
            raise commands.BadArgument("Subreddit not found.")
        if subr_deets['data'].get('over18', None) and not channel.is_nsfw():
            raise commands.NSFWChannelRequired(channel)

        params = {"t": "all" if sort_by == "top" else ""}

        async with self.bot.session.get(
                f"https://reddit.com/r/{subreddit}/{sort_by}.json",
                headers=self.headers, params=params) as subr_resp:
            subreddit_json = await subr_resp.json()

        subreddit_pages = []
        common_img_exts = (".jpg", ".jpeg", ".png", ".gif")

        idx = 0
        for post_data in subreddit_json['data']['children']:
            image_url = None
            video_url = None

            if idx == 20:
                break

            _short = post_data['data']
            if _short['stickied'] or (_short['over_18'] and not channel.is_nsfw()):
                idx += 1
                continue

            image_url = _short['url'] if _short['url'].endswith(
                common_img_exts) else None
            if "v.redd.it" in _short['url']:
                image_url = _short['thumbnail']
                video_teriary = _short.get('media', None)
                if video_teriary:
                    video_url = _short['url']
                else:
                    continue

            subreddit_pages.append(SubredditPost(
                _short,
                image_link=image_url,
                video_link=video_url))
            idx += 1

        return self._gen_embeds(requester, subreddit_pages[:10])

    @commands.command(name="reddit")
    @commands.cooldown(5, 300, commands.BucketType.user)
    async def _reddit(self, ctx: commands.Context, subreddit: str, sort_by: str = "hot"):
        """ Main Reddit command, subcommands to be added. """
        subreddit = subreddit.strip("/r/")
        embeds = await self._perform_search(str(ctx.author), ctx.channel, subreddit, sort_by)
        if not embeds:
            raise commands.BadArgument("Bad subreddit.", subreddit)
        pages = menus.MenuPages(source=SubredditPageSource(
            range(0, 10), embeds))
        await pages.start(ctx)

    @ _reddit.error
    async def reddit_error(self, ctx, error):
        """ Local Error handler for reddit command. """
        error = getattr(error, "original", error)
        if isinstance(error, commands.NSFWChannelRequired):
            return await ctx.send("This ain't an NSFW channel.")
        elif isinstance(error, commands.BadArgument):
            msg = ("There seems to be no Reddit posts to show, common cases are:\n"
                   "- Not a real subreddit.\n")
            return await ctx.send(msg)


def setup(bot):
    """ Cog entrypoint. """
    bot.add_cog(Reddit(bot))
