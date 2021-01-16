import asyncio

import discord
from discord.ext import menus
from discord.ext.commands import Paginator as CommandPaginator


class RoboPages(menus.MenuPages, inherit_buttons=False):
    def __init__(self, source, *args, **kwargs):
        super().__init__(source=source, check_embeds=True, *args, **kwargs)

    async def finalize(self, timed_out):
        try:
            if timed_out:
                await self.message.clear_reactions()
            else:
                await self.message.delete()
        except discord.HTTPException:
            pass

    def _skip_when(self):
        return self.source.get_max_pages() <= 2

    def _skip_when_short(self):
        return self.source.get_max_pages() <= 1

    @menus.button(
        "<:LL:785744371453919243>", position=menus.First(0), skip_if=_skip_when
    )
    async def rewind(self, payload: discord.RawReactionActionEvent):
        await self.show_page(0)

    @menus.button(
        "<:L_:785744338487214104>", position=menus.First(1), skip_if=_skip_when_short
    )
    async def back(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(self.current_page - 1)

    @menus.button("<:Stop:785018971119157300>", position=menus.First(2))
    async def stop_menu(self, payload: discord.RawReactionActionEvent):
        self.stop()

    @menus.button(
        "<:R_:785744271579414528>", position=menus.Last(0), skip_if=_skip_when_short
    )
    async def forward(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(self.current_page + 1)

    @menus.button(
        "<:RR:785742013089185812>", position=menus.Last(1), skip_if=_skip_when
    )
    async def ff(self, payload: discord.RawReactionActionEvent):
        print("fuck")
        await self.show_page(self._source.get_max_pages() - 1)

    @menus.button(
        "<:1234:787170360013225996>", position=menus.Last(2), skip_if=_skip_when
    )
    async def jump_to(self, payload):
        m = await self.message.channel.send("Which page would you like to go to?")
        try:
            n = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == self.ctx.author
                and m.channel == self.ctx.channel
                and m.content.isdigit(),
                timeout=30,
            )
        except asyncio.TimeoutError:
            return
        else:
            await self.show_page(int(n.content))
        finally:
            await m.delete()
            try:
                await n.delete()
            except discord.Forbidden:
                pass


class FieldPageSource(menus.ListPageSource):
    """A page source that requires (field_name, field_value) tuple items."""

    def __init__(self, entries, *, per_page=12):
        super().__init__(entries, per_page=per_page)
        self.embed = discord.Embed(colour=discord.Colour.blurple())

    async def format_page(self, menu, entries):
        self.embed.clear_fields()
        self.embed.description = discord.Embed.Empty

        for key, value in entries:
            self.embed.add_field(name=key, value=value, inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            text = (
                f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)"
            )
            self.embed.set_footer(text=text)

        return self.embed


class TextPageSource(menus.ListPageSource):
    def __init__(self, text, *, prefix="```", suffix="```", max_size=2000):
        pages = CommandPaginator(prefix=prefix, suffix=suffix, max_size=max_size - 200)
        for line in text.split("\n"):
            pages.add_line(line)

        super().__init__(entries=pages, per_page=1)

    async def format_page(self, menu, content):
        maximum = self.get_max_pages()
        if maximum > 1:
            return f"{content}\nPage {menu.current_page + 1}/{maximum}"
        return content


class SimplePageSource(menus.ListPageSource):
    def __init__(self, entries, *, per_page=12):
        super().__init__(entries, per_page=per_page)
        self.initial_page = True

    async def format_page(self, menu, entries):
        pages = []
        for index, entry in enumerate(entries, start=menu.current_page * self.per_page):
            pages.append(f"{index + 1}. {entry}")

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = (
                f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)"
            )
            menu.embed.set_footer(text=footer)

        if self.initial_page and self.is_paginating():
            pages.append("")
            pages.append("Confused? React with \N{INFORMATION SOURCE} for more info.")
            self.initial_page = False

        menu.embed.description = "\n".join(pages)
        return menu.embed


class SimplePages(RoboPages):
    """A simple pagination session reminiscent of the old Pages interface.

    Basically an embed with some normal formatting.
    """

    def __init__(self, entries, *, per_page=12):
        super().__init__(SimplePageSource(entries, per_page=per_page))
        self.embed = discord.Embed(colour=discord.Colour.blurple())
