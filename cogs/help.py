import asyncio
from typing import Any, Dict, List, Mapping, Optional, Union

import discord
from discord.ext import commands, menus
from utils.paginator import RoboPages


class HelpSource(menus.ListPageSource):
    def __init__(self, data: range, embeds: List[discord.Embed]) -> None:
        self.data = data
        self.embeds = embeds
        super().__init__(data, per_page=1)

    async def format_page(self, menu: menus.Menu, page: int) -> discord.Embed:
        embed = self.embeds[page]
        return embed


class PaginatedHelpCommand(commands.HelpCommand):
    def __init__(self):
        self.verify_checks = True
        self.show_hidden = False
        super().__init__()

    async def recursive_command_format(self, command: commands.Command, *, indent=1, subc=0):
        yield (
            "" if indent == 1 else "├" if subc != 0 else "└"
        ) + f"`{command.qualified_name}`: {command.short_doc}"
        if isinstance(command, commands.Group):
            last = len(command.commands) - 1
            for _, command in enumerate(await self.filter_commands(command.commands, sort=True)):
                async for result in self.recursive_command_format(
                    command, indent=indent + 1, subc=last
                ):
                    yield result
                last -= 1

    async def format_commands(
        self,
        cog: commands.Cog,
        cmds: List[Union[commands.Group, commands.Command]],
        *,
        pages,
    ):
        if not cmds:
            return

        pg = commands.Paginator(max_size=2000, prefix="", suffix="")

        for command in cmds:
            try:
                await command.can_run(self.context)
            except (discord.Forbidden, commands.CheckFailure, commands.CommandError):
                continue
            else:
                async for line in self.recursive_command_format(command):
                    pg.add_line(line)

        for desc in pg.pages:
            embed = discord.Embed(
                colour=discord.Colour.blurple(),
                title=cog.qualified_name if cog else "Unsorted",
            )
            embed.description = (
                f"> {cog.description}\n{desc}" if cog else f"> No description\n{desc}"
            )
            embed.set_footer(
                text=f'Use "{self.clean_prefix}help <command>" for more information.'
            )
            pages.append(embed)

    async def send_bot_help(
        self,
        mapping: Mapping[commands.Cog, List[Union[commands.Group, commands.Command]]],
    ):
        pages = []

        for cog, cmds in mapping.items():
            cmds = await self.filter_commands(cmds, sort=True)
            await self.format_commands(cog, cmds, pages=pages)

        total = len(pages)
        for i, embed in enumerate(pages, start=1):
            embed.title = f"Page {i}/{total}: {embed.title}"

        pg = RoboPages(HelpSource(range(0, len(pages)), pages))
        await pg.start(self.context)

    async def send_cog_help(self, cog: commands.Cog):
        pages = []

        await self.format_commands(
            cog, await self.filter_commands(cog.get_commands(), sort=True), pages=pages
        )

        total = len(pages)
        for i, embed in enumerate(pages, start=1):
            embed.title = f"Page {i}/{total}: {embed.title}"

        pg = RoboPages(HelpSource(range(0, len(pages)), pages))
        await pg.start(self.context)

    async def send_group_help(self, group: commands.Group):
        try:
            await group.can_run(self.context)
        except (commands.CommandError, commands.CheckFailure):
            return await self.context.send(f'No command called "{group.name}" found.')
        if not group.commands:
            return await self.send_command_help(group)
        subs = "\n".join(f"`{c.qualified_name}`: {c.short_doc}" for c in group.commands)
        embed = discord.Embed(colour=discord.Colour.blurple())
        embed.title = f"{self.clean_prefix}{group.qualified_name} {group.signature}"
        embed.description = f"{group.help or ''}\n\n**Subcommands**\n\n{subs}"
        embed.set_footer(
            text=f'Use "{self.clean_prefix}help <command>" for more information.'
        )
        await self.context.send(embed=embed)

    async def send_command_help(self, command: commands.Command):
        try:
            await command.can_run(self.context)
        except (commands.CommandError, commands.CheckFailure):
            return await self.context.send(f'No command called "{command.name}" found.')
        embed = discord.Embed(colour=discord.Colour.blurple())
        embed.title = f"{self.clean_prefix}{command.qualified_name} {command.signature}"
        embed.description = command.help or "No help provided"
        embed.set_footer(
            text=f'Use "{self.clean_prefix}help <command>" for more information.'
        )
        await self.context.send(embed=embed)


class Help(commands.Cog):
    """
    Akane's help command!
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot._original_help_command = bot.help_command
        self.bot.help_command = PaginatedHelpCommand()
        self.bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self.bot._original_help_command


def setup(bot: commands.Bot):
    bot.add_cog(Help(bot))
