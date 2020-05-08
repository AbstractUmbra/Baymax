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
                 url: str,
                 subreddit: str,
                 title: str,
                 upvotes: int,
                 *,
                 nsfw: bool = False,
                 image_link: str = None,
                 video_link: str = None,
                 self_text: str = None,
                 comment_count: int = None,
                 author: str = None):
        """ Hrm. """
        self.url = url
        self.subreddit = f"/r/{subreddit}"
        self.title = title
        self.upvotes = int(upvotes)

        self.nsfw = nsfw
        self.image_link = image_link
        self.video_link = video_link
        self.self_text = self_text
        self.comment_count = int(comment_count) if comment_count else 0
        self.author = f"/u/{author}"


class Reddit(commands.Cog):
    """ For Reddit based queries. """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.headers = {"User-Agent": "Robo-Hz Discord bot"}

    def _gen_embeds(self, requester: str, iterable: list, nsfw_channel: bool) -> typing.List[discord.Embed]:
        """ Generate many embeds from the top 10 posts on each subreddit. """
        embeds = []

        for item in iterable:
            if item.nsfw and not nsfw_channel:
                continue

            embed = discord.Embed(
                title=item.title,
                description=item.self_text,
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
            fmt = f"Result {iterable.index(item)}/{len(iterable)-1}"
            embed.set_footer(
                text=f"{fmt} | {item.subreddit} | Requested by: {requester}")

            embeds.append(embed)

        return embeds

    async def _perform_search(self, requester: str, channel: discord.TextChannel, subreddit: str, sort_by: str):
        """ Performs the search for queries with aiohttp. Returns 10 items. """
        async with self.bot.session.get(
                f"https://reddit.com/r/{subreddit}/about.json", headers=self.headers) as subr_top_resp:
            subr_deets = await subr_top_resp.json()

        if subr_deets['data'].get('over18', None) and not channel.is_nsfw():
            raise commands.NSFWChannelRequired(channel)

        async with self.bot.session.get(
                f"https://reddit.com/r/{subreddit}/{sort_by}.json", headers=self.headers) as subr_resp:
            subreddit_json = await subr_resp.json()

        subreddit_pages = []
        common_img_exts = (".jpg", ".jpeg", ".png", ".gif", ".webm")

        idx = 0
        for post_data in subreddit_json['data']['children']:
            image_url = None
            video_url = None
            self_text = None

            if idx == 20:
                break

            _short = post_data['data']
            if _short['stickied']:
                idx += 1
                continue
            url = f"https://reddit.com/{_short['permalink']}"
            author = _short['author']
            title = _short['title']
            upvotes = _short['ups']
            comments = _short['num_comments']
            nsfw = _short['over_18'] if _short['over_18'] else False
            self_text = _short['selftext']
            if len(self_text) > 2000:
                self_text = f"{self_text[:2000]}..."
            image_url = _short['url'] if _short['url'].endswith(
                common_img_exts) else None
            if "v.redd.it" in _short['url']:
                video_url = _short['media']['reddit_video']['fallback_url']
                image_url = _short['thumbnail']
            subreddit_pages.append(SubredditPost(
                url, subreddit, title, upvotes, nsfw=nsfw, image_link=image_url, video_link=video_url, self_text=self_text, comment_count=comments, author=author))
            idx += 1

        return self._gen_embeds(requester, subreddit_pages, channel.is_nsfw())

    @commands.command(name="reddit")
    @commands.cooldown(5, 300, commands.BucketType.user)
    async def _reddit(self, ctx: commands.Context, subreddit: str, sort_by: str = "hot"):
        """ Main Reddit command, subcommands to be added. """
        subreddit = subreddit.strip("/r/")
        embeds = await self._perform_search(str(ctx.author), ctx.channel, subreddit, sort_by)
        if not embeds:
            raise commands.BadArgument("Bad subreddit.", subreddit)
        pages = menus.MenuPages(source=SubredditPageSource(
            range(1, 10), embeds), clear_reactions_after=True)
        await pages.start(ctx)

    @_reddit.error
    async def reddit_error(self, ctx, error):
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
