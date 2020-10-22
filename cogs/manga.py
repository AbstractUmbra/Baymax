import datetime
from typing import Dict, List

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
        """. """
        self._id: str = payload.get("id")
        self.chapter_url: str = payload.get("link")
        self.manga_url: str = payload.get("mangalink")
        self._published_at: str = payload.get("published")
        self.summary: str = payload.get("summary")
        self.title: str = payload.get("title")

    @property
    def mangadex_id(self) -> int:
        return int(self._id.rsplit("/", 1)[1])

    @property
    def published_at(self) -> datetime.datetime:
        print(self._published_at)
        return datetime.datetime.strptime(self._published_at, "%a, %d %b %Y %H:%M:%S %z")


class Manga(commands.Cog):
    """ . """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rss_url = MANGADEX_RSS_BASE.format(bot.config.mangadex_key)
        self.rss_webhook = discord.Webhook.from_url(
            bot.config.mangadex_webhook, adapter=discord.AsyncWebhookAdapter(bot.session))
        self.rss_parser.start()

    def _gen_embed(self, entry: MangadexEntry) -> discord.Embed:
        embed = discord.Embed(colour=discord.Colour(0x000001))
        embed.title = entry.title
        embed.description = entry.summary
        embed.url = entry.chapter_url
        embed.add_field(name="Manga URL", value=f"[Here]({entry.manga_url})")
        embed.timestamp = entry.published_at
        embed.set_footer(text=entry.mangadex_id)

        return embed

    @tasks.loop(minutes=30)
    async def rss_parser(self):
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
            if mangadex_entry.mangadex_id in previous_ids:
                continue
            embed = self._gen_embed(mangadex_entry)
            await self.rss_webhook.send(embed=embed)
            processed_ids.append(mangadex_entry.mangadex_id)

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
        stats = self.bot.get_cog("Stats")
        if stats:
            await stats.webhook.send(str(error))

    def cog_unload(self):
        self.rss_parser.cancel()


def setup(bot: commands.Bot):
    bot.add_cog(Manga(bot))
