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
                 image_link: str = None,
                 video_link: str = None,
                 self_text: str = None,
                 comment_count: int = None):
        """ Hrm. """
        self.url = url
        self.subreddit = f"/r/{subreddit}"
        self.title = title
        self.upvotes = int(upvotes)

        self.image_link = image_link
        self.video_link = video_link
        self.self_text = self_text
        self.comment_count = int(comment_count) if comment_count else 0


class Reddit(commands.Cog):
    """ For Reddit based queries. """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.headers = {"User-Agent": "Robo-Hz Discord bot"}

    def _gen_embeds(self, iterable: list) -> typing.List[discord.Embed]:
        """ Generate many embeds from the top 10 posts on each subreddit. """
        embeds = []
        for item in iterable:
            embed = discord.Embed(
                title=item.title,
                description=item.self_text,
                colour=discord.Colour.red(),
                url=item.url)
            if item.image_link:
                embed.set_image(url=item.image_link)
            if item.video_link:
                embed.add_field(
                    name="Video", value=f"[Click me!]({item.video_link})", inline=False)
            embed.add_field(name="Upvotes", value=item.upvotes, inline=True)
            embed.add_field(name="Total comments", value=item.comment_count)
            fmt = f"Result {iterable.index(item)}/{len(iterable)-1}"
            embed.set_footer(text=f"{fmt} | {item.subreddit}")
            embeds.append(embed)
        return embeds

    async def _perform_search(self, subreddit: str, sort_by: str):
        """ Performs the search for queries with aiohttp. Returns 10 items. """
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
            if idx == 12:
                break
            _short = post_data['data']
            if _short['stickied']:
                idx += 1
                continue
            url = f"https://reddit.com/{_short['permalink']}"
            title = _short['title']
            upvotes = _short['ups']
            comments = _short['num_comments']
            image_url = _short['url'] if _short['url'].endswith(
                common_img_exts) else None
            if "v.redd.it" in _short['url']:
                video_url = _short['media']['reddit_video']['fallback_url']
                image_url = _short['thumbnail']
            subreddit_pages.append(SubredditPost(
                url, subreddit, title, upvotes, image_link=image_url, video_link=video_url, self_text=self_text, comment_count=comments))
            idx += 1
        return self._gen_embeds(subreddit_pages)

    @commands.group(name="reddit")
    @commands.cooldown(5, 300, commands.BucketType.user)
    async def _reddit(self, ctx: commands.Context, subreddit: str, sort_by: str = "hot"):
        """ Main Reddit command, subcommands to be added. """
        embeds = await self._perform_search(subreddit, sort_by)
        pages = menus.MenuPages(source=SubredditPageSource(
            range(1, 10), embeds), clear_reactions_after=True)
        await pages.start(ctx)


def setup(bot):
    """ Cog entrypoint. """
    bot.add_cog(Reddit(bot))
