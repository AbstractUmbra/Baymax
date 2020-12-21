# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Union

if TYPE_CHECKING:
    from bot import Akane

import aiohttp
import discord
import pykakasi
from discord.ext import commands, menus
from utils.context import Context
from utils.formats import to_codeblock
from utils.paginator import RoboPages

BASE_URL = "https://kanjiapi.dev/v1"


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
                    f"{embed.footer.text} :: {real_embeds.index(embed)}/{len(real_embeds)}"
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
    async def nihongo_error(self, ctx: commands.Context, error: Exception):
        error = getattr(error, "original", error)

        if isinstance(error, aiohttp.ContentTypeError):
            return await ctx.send("You appear to have passed an invalid *kanji*.")


def setup(bot):
    bot.add_cog(Nihongo(bot))
