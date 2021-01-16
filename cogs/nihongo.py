# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Union

if TYPE_CHECKING:
    from bot import Akane

import aiohttp
import discord
import pykakasi
from discord.ext import commands, menus
from utils.context import Context
from utils.formats import plural, to_codeblock
from utils.paginator import RoboPages

BASE_URL = "https://kanjiapi.dev/v1"
KANA = "あいうえおかきくけこがぎぐげごさしすせそざじずぜぞたちつてとだぢづでどなにぬねのはひふへほばびぶべぼぱぴぷぺぽまみむめもやゆよらりるれろわを"
JISHO_URL = "https://jisho.org/api/v1/search/words"
JISHO_REPLACEMENTS = {
    "english_definitions": "Definitions",
    "parts_of_speech": "Type",
    "tags": "Notes",
    "see_also": "See Also",
}


def _create_kakasi() -> pykakasi.kakasi:
    kakasi = pykakasi.kakasi()
    kakasi.setMode("H", "a")
    kakasi.setMode("K", "a")
    kakasi.setMode("J", "a")
    kakasi.setMode("s", True)
    return kakasi.getConverter()


@dataclass
class KanjiPayload:
    kanji: str
    grade: int
    stroke_count: int
    meanings: List[str]
    kun_readings: List[str]
    on_readings: List[str]
    name_readings: List[str]
    jlpt: int
    unicode: str
    heisig_en: str


@dataclass
class WordsPayload:
    variants: List[Dict[str, Union[str, List[str]]]]
    meanings: List[Dict[str, List[str]]]


@dataclass
class JishoPayload:
    attribution: Dict[str, Union[str, bool]]
    japanese: List[Dict[str, str]]
    jlpt: List[str]
    senses: List[Dict[str, List[str]]]
    slug: str
    tags: List[str]
    is_common: bool = False


def word_to_reading(stuff: List[Dict[str, str]]) -> List[str]:
    ret = []
    for item in stuff:
        if item.get("word"):
            hmm = (
                f"{item['word']} 【{item['reading']}】"
                if item.get("reading")
                else f"{item['word']}"
            )
            ret.append(hmm)
    return ret


class KanjiAPISource(menus.ListPageSource):
    def __init__(self, data, embeds):
        self.data = data
        self.embeds = embeds
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        embed = self.embeds[entries]
        return embed


class KanjiEmbed(discord.Embed):
    @classmethod
    def from_kanji(cls, payload: KanjiPayload) -> "KanjiEmbed":
        embed = cls(title=payload.kanji, colour=discord.Colour(0xBF51B2))

        embed.add_field(
            name="(School) Grade learned:", value=f"**__{payload.grade}__**"
        )
        embed.add_field(name="Stroke count:", value=f"**__{payload.stroke_count}__**")
        embed.add_field(
            name="Kun Readings", value=("\n".join(payload.kun_readings) or "N/A")
        )
        embed.add_field(
            name="On Readings", value=("\n".join(payload.on_readings) or "N/A")
        )
        embed.add_field(
            name="Name Readings", value=("\n".join(payload.name_readings) or "N/A")
        )
        embed.add_field(name="Unicode", value=payload.unicode)
        embed.description = to_codeblock(
            ("\n".join(payload.meanings) or "N/A"), language=""
        )
        embed.set_footer(text=f"JLPT Grade: {payload.jlpt or 'N/A'}")

        return embed

    @classmethod
    def from_words(cls, character: str, payload: WordsPayload) -> "KanjiEmbed":
        embeds = []
        variants = payload.variants
        meanings = payload.meanings[0]
        for variant in variants:
            embed = cls(title=character, colour=discord.Colour(0x4AFAFC))

            embed.add_field(name="Written:", value=variant["written"])
            embed.add_field(name="Pronounced:", value=variant["pronounced"])
            priorities = (
                to_codeblock("".join(variant["priorities"]), language="")
                if variant["priorities"]
                else "N/A"
            )
            embed.add_field(name="Priorities:", value=priorities)
            for _ in range(3):
                embed.add_field(name="\u200b", value="\u200b")
            meaning = "\n".join(meanings["glosses"] or "N/A")
            embed.add_field(name="Kanji meaning(s):", value=meaning)

            embeds.append(embed)

        return embeds

    @classmethod
    def from_jisho(cls, query: str, payload: JishoPayload) -> "KanjiEmbed":
        embed = cls(title=f"Jisho data on {query}.", colour=discord.Colour(0x4AFAFC))

        attributions = []
        for key, value in payload.attribution.items():
            if value in (True, False):
                attributions.append(key.title())
            elif value:
                attributions.append(f"{key.title()}: {value}")

        if attributions:
            attributions_cb = to_codeblock(
                "\n".join(attributions), language="prolog", escape_md=False
            )
            embed.add_field(name="Attributions", value=attributions_cb, inline=False)

        jp = word_to_reading(payload.japanese)

        japanese = "\n\n".join(jp)
        embed.add_field(
            name="Writing 【Reading】",
            value=to_codeblock(japanese, language="prolog", escape_md=False),
            inline=False,
        )

        sense: Dict[str, List[Optional[str]]] = payload.senses[0]
        senses = ""
        links = ""
        embed.description = ""
        for key, value in sense.items():
            if key == "links":
                if value:
                    subdict = value[0]
                    links += f"[{subdict.get('text')}]({subdict.get('url')})\n"
                else:
                    continue
            else:
                if value:
                    senses += f"{JISHO_REPLACEMENTS.get(key, key).title()}: {', '.join(value)}\n"

        if senses:
            embed.description += to_codeblock(
                senses, language="prolog", escape_md=False
            )

        if links:
            embed.description += links

        embed.add_field(
            name="Is it common?",
            value=("Yes" if payload.is_common else "No"),
            inline=False,
        )

        if payload.jlpt:
            embed.add_field(name="JLPT Level", value=payload.jlpt[0], inline=False)

        embed.set_footer(text=f"Slug: {payload.slug}")

        return embed


class Nihongo(commands.Cog):
    """The description for Nihongo goes here."""

    def __init__(self, bot: Akane):
        self.bot = bot
        self.converter = _create_kakasi()

    @commands.command()
    async def romaji(self, ctx: Context, *, text: commands.clean_content):
        """ Sends the Romaji version of passed Kana. """
        ret = await self.bot.loop.run_in_executor(None, self.converter.do, text)
        await ctx.send(ret)

    @commands.group(name="kanji", aliases=["かんじ", "漢字"], invoke_without_command=True)
    async def kanji(self, ctx: Context, character: str):
        """ Return data on a single Kanji from the KanjiDev API. """
        if len(character) > 1:
            raise commands.BadArgument("Only one Kanji please.")
        url = f"{BASE_URL}/kanji/{character}"

        async with self.bot.session.get(url) as response:
            data = await response.json()

        kanji_data = KanjiPayload(**data)

        embed = KanjiEmbed.from_kanji(kanji_data)

        menu = RoboPages(KanjiAPISource(range(0, 1), [embed]))
        await menu.start(ctx)

    @kanji.command(name="words")
    async def words(self, ctx: Context, character: str):
        """ Return the words a Kanji is used in, or in conjuction with. """
        if len(character) > 1:
            raise commands.BadArgument("Only one Kanji please.")
        url = f"{BASE_URL}/words/{character}"

        async with self.bot.session.get(url) as response:
            data = await response.json()

        words_data = [WordsPayload(**payload) for payload in data]
        embeds = [KanjiEmbed.from_words(character, kanji) for kanji in words_data]
        real_embeds = [embed for sublist in embeds for embed in sublist]

        fixed_embeds = [
            embed.set_footer(
                text=(
                    f"{embed.footer.text} :: {real_embeds.index(embed) + 1}/{len(real_embeds)}"
                    if embed.footer.text
                    else f"{real_embeds.index(embed) + 1}/{len(real_embeds)}"
                )
            )
            for embed in real_embeds
        ]

        menu = RoboPages(
            KanjiAPISource(range(0, len(fixed_embeds)), fixed_embeds),
            delete_message_after=False,
            clear_reactions_after=False,
        )
        await menu.start(ctx)

    @kanji.error
    @words.error
    async def nihongo_error(self, ctx: Context, error: Exception):
        error = getattr(error, "original", error)

        if isinstance(error, aiohttp.ContentTypeError):
            return await ctx.send("You appear to have passed an invalid *kanji*.")

    @commands.command()
    async def jisho(self, ctx: Context, *, query: str):
        """ Query the Jisho api with your kanji/word. """
        async with self.bot.session.get(
            JISHO_URL, params={"keyword": query}
        ) as response:
            if response.status == 200:
                data = (await response.json())["data"]
            else:
                raise commands.BadArgument("Not a valid query for Jisho.")
            if not data:
                raise commands.BadArgument("Not a valid query for Jisho.")

            jisho_data = [JishoPayload(**payload) for payload in data]
            embeds = [KanjiEmbed.from_jisho(query, item) for item in jisho_data]

            fixed_embeds = [
                embed.set_footer(
                    text=(
                        f"{embed.footer.text} :: {embeds.index(embed) + 1}/{len(embeds)}"
                        if embed.footer.text
                        else f"{embeds.index(embed) + 1}/{len(embeds)}"
                    )
                )
                for embed in embeds
            ]

            menu = RoboPages(
                KanjiAPISource(range(0, len(fixed_embeds)), fixed_embeds),
                delete_message_after=False,
                clear_reactions_after=False,
            )
            await menu.start(ctx)

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def kanarace(self, ctx: Context, amount: int = 10):
        """Kana racing.

        This command will send a string of Kana of [amount] length.
        Please type and send this Kana in the same channel to qualify.

        There are anti-cheating methods implemented so copying and pasting will not qualify.
        """

        if not 1 <= amount <= 50:
            return await ctx.send(
                f"Please specify between 1 and 50 kana, not {amount}."
            )

        await ctx.send("Kana-racing begins in 5 seconds.")
        await asyncio.sleep(5)

        randomized_kana = "".join(random.choices(KANA, k=amount))
        anti_cheat = "".join(
            char + "\N{ZWSP}" * (idx % random.randint(1, 3))
            for idx, char in enumerate(randomized_kana)
        )

        initial = await ctx.send(anti_cheat)

        winners = dict()

        is_ended = asyncio.Event()

        timeout = False

        while not is_ended.is_set():
            done, pending = await asyncio.wait(
                [
                    self.bot.wait_for(
                        "message",
                        check=lambda m: m.channel == ctx.channel
                        and m.content == randomized_kana
                        and not m.author.bot
                        and m.author not in winners.keys(),
                    ),
                    is_ended.wait(),
                ],
                return_when=asyncio.FIRST_COMPLETED,
                # timeout=time,
            )
            for task in pending:
                task.cancel()

            # if not done:
            #     return await ctx.send("There are no winners.")

            result = done.pop().result()
            if isinstance(result, discord.Message):
                message = result
            else:
                break

            try:
                await message.delete()
            except discord.Forbidden:
                try:
                    await message.add_reaction(self.bot.emoji[True])
                except discord.Forbidden:
                    pass

            winners[message.author] = (
                message.created_at - initial.created_at
            ).total_seconds()

            if not timeout:
                timeout = not timeout

                async def ender():
                    await asyncio.sleep(10)
                    is_ended.set()

                await ctx.send(
                    f"{message.author.mention} wins! Other participants have 10 seconds to finish."
                )
                self.bot.loop.create_task(ender())

        embed = discord.Embed(
            title=f"{plural(len(winners)):Winner}", colour=discord.Colour.random()
        )
        embed.description = "\n".join(
            f"{idx}: {person.mention} - {time:.4f} seconds for {amount / time * 12:.2f}WPM"
            for idx, (person, time) in enumerate(winners.items(), start=1)
        )

        await ctx.send(embed=embed)

    @kanarace.error
    async def race_error(self, ctx: Context, error: Exception):
        if isinstance(error, asyncio.TimeoutError):
            return await ctx.send("Kanarace has no winners!", delete_after=5.0)


def setup(bot):
    bot.add_cog(Nihongo(bot))
