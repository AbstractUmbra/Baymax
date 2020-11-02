import datetime
import traceback
from typing import Dict, List, NoReturn

import aiohttp
import discord
import feedparser
from discord.ext import commands, tasks
from utils import db

MANGADEX_RSS_BASE = "https://mangadex.org/rss/follows/{}"


class MangadexFeeds(db.Table, table_name="mangadex_feeds"):
    id = db.Column(db.Integer(big=True), primary_key=True)
    previous_ids = db.Column(db.Array(db.Integer))


class MangadexEntry:
    def __init__(self, payload: Dict):
        """ Data returns from the Mangadex API, just a generic object. """
        self._id: str = payload.get("id")
        self.chapter_url: str = payload.get("link")
        self.manga_url: str = payload.get("mangalink")
        self._published_at: str = payload.get("published")
        self.summary: str = payload.get("summary")
        self.title: str = payload.get("title")

    @property
    def manga_id(self) -> int:
        return int(self._id.rsplit("/", 1)[1])

    @property
    def published_at(self) -> datetime.datetime:
        return datetime.datetime.strptime(self._published_at, "%a, %d %b %Y %H:%M:%S %z")


class MangadexEmbed(discord.Embed):
    @classmethod
    def from_mangadex(cls, entry: MangadexEntry) -> "MangadexEmbed":
        """ Return a custom Embed based on a Mangadex entry. """

        embed = cls(colour=0xe91e63)
        embed.title = entry.title
        embed.description = entry.summary
        embed.url = entry.chapter_url
        embed.add_field(name="Manga URL", value=f"[Here]({entry.manga_url})")
        embed.timestamp = entry.published_at
        embed.set_footer(text=entry.manga_id)

        return embed


class Manga(commands.Cog):
    """ . """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rss_url = MANGADEX_RSS_BASE.format(bot.config.mangadex_key)
        self.rss_webhook = discord.Webhook.from_url(
            bot.config.mangadex_webhook, adapter=discord.AsyncWebhookAdapter(bot.session))
        self.rss_parser.start()

    @tasks.loop(minutes=30)
    async def rss_parser(self) -> NoReturn:
        """. """
        select_query = """ SELECT * FROM mangadex_feeds; """
        record = await self.bot.pool.fetchrow(select_query)

        previous_ids: List[int] = [_id for _id in record['previous_ids']]

        async with self.bot.session.get(self.rss_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response_text = await response.text()

        processed_ids: List[int] = []

        rss_data: Dict[str, List] = feedparser.parse(response_text)
        entries_data: List[Dict] = rss_data['entries']
        for entry in entries_data:
            mangadex_entry = MangadexEntry(entry)
            if mangadex_entry.manga_id in previous_ids:
                continue
            print(mangadex_entry.published_at.tzinfo)
            if ((datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)) - mangadex_entry.published_at).seconds < 2700:
                embed = MangadexEmbed.from_mangadex(mangadex_entry)
                await self.rss_webhook.send(embed=embed)
                processed_ids.append(mangadex_entry.manga_id)

        insert_query = """ UPDATE mangadex_feeds
                           SET previous_ids = $2
                           WHERE id = $1;
                       """

        all_ids_unique = set(previous_ids + processed_ids)
        all_ids = list(all_ids_unique)

        await self.bot.pool.execute(insert_query, 1, all_ids)

    @rss_parser.before_loop
    async def before_rss_parser(self):
        """ . """
        await self.bot.wait_until_ready()

    @rss_parser.error
    async def rss_parser_error(self, error):
        tb_str = "".join(traceback.format_exception(
            type(error), error, error.__traceback__, 4))
        stats = self.bot.get_cog("Stats")
        if stats:
            await stats.webhook.send(f"```py\n{tb_str}\n```")

    def cog_unload(self):
        self.rss_parser.cancel()


def setup(bot: commands.Bot):
    bot.add_cog(Manga(bot))
