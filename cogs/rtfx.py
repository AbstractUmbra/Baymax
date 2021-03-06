"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import inspect
import io
import os
import re
import sys
import zlib
from textwrap import dedent
from typing import TYPE_CHECKING

import asyncpg
import discord
from discord.ext import commands, menus, tasks

from utils import fuzzy
from utils.context import Context
from utils.formats import to_codeblock

RTFS = (
    "discord",
    "discord.ext.commands",
    "discord.ext.tasks",
    "discord.ext.menus",
    "asyncpg",
)

if TYPE_CHECKING:
    from bot import Akane


class BadSource(commands.CommandError):
    pass


class SourceConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> str:
        args = argument.split(".")
        top_level = args[0]
        if top_level in ("commands", "menus", "tasks"):
            top_level = f"discord.ext.{top_level}"

        if top_level not in RTFS:
            raise BadSource(f"`{top_level}` is not an allowed sourceable module.")

        recur = sys.modules[top_level]

        if len(args) == 1:
            return inspect.getsource(recur)

        for item in args[1:]:
            if item == "":
                raise BadSource("Don't even try.")

            recur = inspect.getattr_static(recur, item, None)

            if recur is None:
                raise BadSource(f"{argument} is not a valid module path.")

        if isinstance(recur, property):
            recur = recur.fget

        return inspect.getsource(recur)


class SphinxObjectFileReader:
    """A Sphinx file reader."""

    # Inspired by Sphinx's InventoryFileReader
    BUFSIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = io.BytesIO(buffer)

    def readline(self):
        return self.stream.readline().decode("utf-8")

    def skipline(self):
        self.stream.readline()

    def read_compressed_chunks(self):
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
            if len(chunk) == 0:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self):
        buf = b""
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b"\n")
            while pos != -1:
                yield buf[:pos].decode("utf-8")
                buf = buf[pos + 1 :]
                pos = buf.find(b"\n")


class RTFX(commands.Cog):
    def __init__(self, bot: Akane):
        self.bot = bot

    def parse_object_inv(self, stream, url):
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result = {}

        # first line is version info
        inv_version = stream.readline().rstrip()

        if inv_version != "# Sphinx inventory version 2":
            raise RuntimeError("Invalid objects.inv file version.")

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]

        # next line says if it's a zlib header
        line = stream.readline()
        if "zlib" not in line:
            raise RuntimeError("Invalid objects.inv file, not z-lib compatible.")

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(":")
            if directive == "py:module" and name in result:
                # From the Sphinx Repository:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue

            # Most documentation pages have a label
            if directive == "std:doc":
                subdirective = "label"

            if location.endswith("$"):
                location = location[:-1] + name

            key = name if dispname == "-" else dispname
            prefix = f"{subdirective}:" if domain == "std" else ""

            if projname == "discord.py":
                key = key.replace("discord.ext.commands.", "").replace("discord.", "")

            result[f"{prefix}{key}"] = os.path.join(url, location)

        return result

    async def build_rtfm_lookup_table(self, page_types):
        cache = {}
        for key, page in page_types.items():
            _ = cache[key] = {}
            async with self.bot.session.get(page + "/objects.inv") as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        "Cannot build rtfm lookup table, try again later."
                    )

                stream = SphinxObjectFileReader(await resp.read())
                cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx, key, obj):
        page_types = {
            "discord.py": "https://discordpy.readthedocs.io/en/latest",
            "discord.py-jp": "https://discordpy.readthedocs.io/ja/latest",
            "python": "https://docs.python.org/3",
            "python-jp": "https://docs.python.org/ja/3",
            "asyncpg": "https://magicstack.github.io/asyncpg/current",
            "aiohttp": "https://docs.aiohttp.org/en/stable",
        }

        if obj is None:
            await ctx.send(page_types[key])
            return

        if not hasattr(self, "_rtfm_cache"):
            await ctx.trigger_typing()
            await self.build_rtfm_lookup_table(page_types)

        obj = re.sub(r"^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)", r"\1", obj)

        if key.startswith("discord."):
            # point the abc.Messageable types properly:
            q = obj.lower()
            for name in dir(discord.abc.Messageable):
                if name[0] == "_":
                    continue
                if q == name:
                    obj = f"abc.Messageable.{name}"
                    break

        cache = list(self._rtfm_cache[key].items())

        matches = fuzzy.finder(obj, cache, key=lambda t: t[0], lazy=False)

        e = discord.Embed(colour=self.bot.colour["dsc"])
        if not matches:
            return await ctx.send("Could not find anything. Sorry.")
        e.title = f"RTFM for __**`{key}`**__: {obj}"
        e.description = "\n".join(f"[`{key}`]({url})" for key, url in matches[:8])
        e.set_footer(text=f"{len(matches)} possible results.")
        await ctx.send(embed=e)

    @commands.group(aliases=["rtfd"], invoke_without_command=True)
    async def rtfm(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity.

        Events, objects, and functions are all supported through a
        a cruddy fuzzy algorithm.
        """
        await self.do_rtfm(ctx, "discord.py", obj)

    @rtfm.command(name="jp")
    async def rtfm_jp(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity (Japanese)."""
        await self.do_rtfm(ctx, "discord.py-jp", obj)

    @rtfm.command(name="python", aliases=["py"])
    async def rtfm_python(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a Python entity."""
        await self.do_rtfm(ctx, "python", obj)

    @rtfm.command(name="py-jp", aliases=["py-ja"])
    async def rtfm_python_jp(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a Python entity (Japanese)."""
        await self.do_rtfm(ctx, "python-jp", obj)

    @rtfm.command(name="asyncpg")
    async def rtfm_asyncpg(self, ctx, *, obj: str = None):
        """Gives you the documentation link for an `asyncpg` entity."""
        await self.do_rtfm(ctx, "asyncpg", obj)

    @rtfm.command(name="twitchio")
    async def rtfm_twitchio(self, ctx, *, obj: str = None):
        """Gives you the documentation link for a `twitchio` entity."""
        await self.do_rtfm(ctx, "twitchio", obj)

    @rtfm.command(name="aiohttp")
    async def rtfm_aiohttp(self, ctx, *, obj: str = None):
        """Gives you the documentation link for an `aiohttp` entity."""
        await self.do_rtfm(ctx, "aiohttp", obj)

    @rtfm.command(name="wavelink")
    async def rtfm_wavelink(self, ctx, *, obj: str = None):
        """Gives you the documentation link for a `Wavelink` entity."""
        await self.do_rtfm(ctx, "wavelink", obj)

    @rtfm.command(name="flask")
    async def rtfm_flask(self, ctx, *, obj: str = None):
        """Gives you the documentation link for a `Wavelink` entity."""
        await self.do_rtfm(ctx, "flask", obj)

    async def _member_stats(self, ctx, member, total_uses):
        e = discord.Embed(title="RTFM Stats")
        e.set_author(name=str(member), icon_url=member.avatar_url)

        query = "SELECT count FROM rtfm WHERE user_id=$1;"
        record = await ctx.db.fetchrow(query, member.id)

        if record is None:
            count = 0
        else:
            count = record["count"]

        e.add_field(name="Uses", value=count)
        e.add_field(
            name="Percentage", value=f"{count/total_uses:.2%} out of {total_uses}"
        )
        e.colour = self.bot.colour["dsc"]
        await ctx.send(embed=e)

    @commands.command(name="rtfs")
    async def rtfs(self, ctx: Context, *, target: SourceConverter = None) -> None:
        if target is None:
            return await ctx.send(
                embed=discord.Embed(
                    title="Available sources of rtfs", description="\n".join(RTFS)
                )
            )

        target = dedent(target)

        if len(target) >= 1990:
            paste = await ctx.bot.mb_client.post(target, syntax="py")
            return await ctx.send(paste.url)

        await ctx.send(to_codeblock(target, language="py", escape_md=False))

    @rtfs.error
    async def rtfs_error(self, ctx: Context, error: commands.CommandError) -> None:
        error = getattr(error, "original", error)

        await ctx.send(str(error))


def setup(bot):
    bot.add_cog(RTFX(bot))
