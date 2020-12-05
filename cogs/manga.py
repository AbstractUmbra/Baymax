import datetime
import traceback
from collections import defaultdict
from typing import Any, Dict, List, Optional

import aiohttp
import attrdict
import discord
import feedparser
from discord.ext import commands, tasks

MANGADEX_RSS_BASE = "https://mangadex.org/rss/follows/{}"
MANGADEX_API_BASE = "https://mangadex.org/api/"
MANGADEX_BASE = "https://mangadex.org"


class MangadexAPIResponse:
    def __init__(self, payload: Dict):
        """ Data response from the Mangadex API. """
        self._chapters: Optional[Dict[str, Dict[str, Any]]] = payload.get(
            "chapter"
        )  # private because not gonna use... yet?
        self.group: Optional[Dict[str, Dict[str, str]]] = payload.get("group")
        self.manga: attrdict.AttrDict = attrdict.AttrDict(payload["manga"])
        self.status: Optional[str] = payload.get("status")

    @property
    def name(self) -> str:
        return self.manga.title

    @property
    def artist(self) -> str:
        return self.manga.artist

    @property
    def author(self) -> str:
        return self.manga.author

    @property
    def cover(self) -> str:
        return f"{MANGADEX_BASE}{self.manga.cover_url}"

    @property
    def alt_covers(self) -> List[str]:
        return [f"{MANGADEX_BASE}{alt_cover}" for alt_cover in self.manga.covers]

    @property
    def alt_names(self) -> List[str]:
        return self.manga.alt_names

    @property
    def hentai(self) -> bool:
        return bool(self.manga.hentai)

    @property
    def lang_name(self) -> str:
        return self.manga.lang_name

    @property
    def last_updated(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.manga.last_updated)


class MangadexRSSEntry:
    def __init__(self, payload: Dict):
        """ Data returns from the Mangadex RSS feed, just a generic object. """
        self._id: str = payload.get("id")
        self.chapter_url: str = f"{payload.get('link')}/"
        self.manga_url: str = payload.get("mangalink")
        self._published_at: str = payload.get("published")
        self.summary: str = payload.get("summary")
        self.title: str = payload.get("title")

    @property
    def manga_id(self) -> int:
        return int(self._id.rsplit("/", 1)[1])

    @property
    def published_at(self) -> datetime.datetime:
        return datetime.datetime.strptime(
            self._published_at, "%a, %d %b %Y %H:%M:%S %z"
        )


class MangadexEmbed(discord.Embed):
    @classmethod
    def from_rss(cls, entry: MangadexRSSEntry) -> "MangadexEmbed":
        """ Return a custom Embed based on a Mangadex RSS entry. """

        embed = cls(colour=0xE91E63)
        embed.title = entry.title
        embed.description = entry.summary
        embed.url = entry.chapter_url
        embed.add_field(name="Manga URL", value=f"[Here]({entry.manga_url}/)")
        embed.timestamp = entry.published_at
        embed.set_footer(text=entry.manga_id)

        return embed

    @classmethod
    def from_api(cls, mango: str, entry: MangadexAPIResponse) -> "MangadexEmbed":
        """ Returns a custom Embed based on a Mangadex API entry. """

        alt_covers = " | ".join(
            [f"[{index}]({url})" for index, url in enumerate(entry.alt_covers, start=1)]
        )

        embed = cls(colour=0xD50158)
        embed.title = entry.name
        embed.url = f"https://mangadex.org/title/{mango}/"
        embed.set_author(name=entry.author)
        embed.set_image(url=entry.cover)
        embed.set_footer(text="Last updated:")
        embed.timestamp = entry.last_updated
        embed.add_field(name="Artist", value=entry.artist or "Not listed.")
        embed.add_field(name="Hentai", value=("Yes" if entry.hentai else "No"))
        embed.add_field(name="Language of origin", value=entry.lang_name.capitalize())
        embed.add_field(name="Alternate names", value="\n".join(entry.alt_names))
        embed.add_field(name="Alternate cover URLs", value=alt_covers or "N/A")

        return embed


class Manga(commands.Cog):
    """ . """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rss_url = MANGADEX_RSS_BASE.format(bot.config.mangadex_key)
        self.rss_webhook = discord.Webhook.from_url(
            bot.config.mangadex_webhook,
            adapter=discord.AsyncWebhookAdapter(bot.session),
        )
        self._cache = defaultdict(set)
        self.rss_parser.start()

    @commands.command()
    async def mangadex(self, ctx: commands.Context, *, mangadex_id: int):
        try:
            response = await self.bot.session.get(
                f"{MANGADEX_API_BASE}manga/{mangadex_id}"
            )
            data = await response.json()
        except Exception as err:  # TODO get real exc
            raise commands.BadArgument("Provided Mangadex ID is invalid.") from err

        mangadex_entry = MangadexAPIResponse(data)

        embed = MangadexEmbed.from_api(mangadex_id, mangadex_entry)
        await ctx.send(embed=embed)

    @tasks.loop(minutes=30)
    async def rss_parser(self):
        """. """
        async with self.bot.session.get(
            self.rss_url, timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            response_text = await response.text()

        rss_data: Dict[str, List] = feedparser.parse(response_text)
        entries_data: List[Dict] = rss_data["entries"]

        for entry in entries_data:
            mangadex_entry = MangadexRSSEntry(entry)
            manga_td = (
                datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
            ) - mangadex_entry.published_at

            if manga_td.total_seconds() < 2700:
                if mangadex_entry.manga_id in self._cache[mangadex_entry.title]:
                    return
                embed = MangadexEmbed.from_rss(mangadex_entry)
                await self.rss_webhook.send(embed=embed)
                self._cache[mangadex_entry.title].add(mangadex_entry.manga_id)

    @rss_parser.before_loop
    async def before_rss_parser(self):
        """ . """
        await self.bot.wait_until_ready()

    @rss_parser.error
    async def rss_parser_error(self, error):
        tb_str = "".join(
            traceback.format_exception(type(error), error, error.__traceback__, 4)
        )
        stats = self.bot.get_cog("Stats")
        if stats:
            await stats.webhook.send(f"```py\n{tb_str}\n```")

    def cog_unload(self):
        self.rss_parser.cancel()


def setup(bot: commands.Bot):
    bot.add_cog(Manga(bot))
