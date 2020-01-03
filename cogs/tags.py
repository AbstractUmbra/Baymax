""" Text Tags! """
from asyncio import TimeoutError as AsynTOut
from os import path as fpath
from json import load, dump

from discord import Embed
from discord.ext import commands

from . import BaseCog

PATH = fpath.join(fpath.dirname(__file__))
TAGS_PATH = fpath.join(PATH, "../config/tags.json")


def load_tags(tags_path=TAGS_PATH):
    """ Loads the tag json... db soon. """
    if fpath.exists(tags_path):
        with open(tags_path) as tags_file:
            tags = load(tags_file)
    else:
        print(f"No tags.json found at {tags_path}.")
    return tags


def save_tags(tags: dict, tags_path=TAGS_PATH):
    """ Save tags in json file. """
    with open(tags_path, "w+") as tags_file:
        dump(tags, tags_file, indent=4)


TAGS = load_tags()


class TagName(commands.clean_content):
    """ Tag Names. """

    def __init__(self, *, lower=False):
        super().__init__()
        self.lower = lower

    async def convert(self, ctx, argument):
        converted = await super().convert(ctx, argument)
        lower = converted.lower().strip()

        if not lower:
            raise commands.BadArgument("Missing tag name.")
        if len(lower) > 100:
            raise commands.BadArgument("Tag name is a max of 100 chars.")

        first_word, _, _ = lower.partition(" ")

        root = ctx.bot.get_command('tag')
        if first_word in root.all_commands:
            raise commands.BadArgument("This tag starts with a reserved word.")
        return converted if not self.lower else lower


class Tags(BaseCog):
    """ Tags! Text only though. """

    def __init__(self, bot):
        super().__init__(bot)

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx, *, name):
        """ Tags text for later retrieval. """

        try:
            tag = TAGS[str(name)]
        except KeyError:
            return await ctx.send(f"This tag: {name} does not exist.")

        return await ctx.send(tag)

    @tag.command(aliases=['add'])
    async def create(self, ctx, name, *, content: commands.clean_content):
        """ Creates a new tag! """
        try:
            TAGS[name] = content
        except Exception as err:
            await ctx.send(err)
        finally:
            save_tags(TAGS)
        return await ctx.send(f"Tag {name} has been created!")

    @tag.command(ignore_extra=False)
    async def make(self, ctx):
        """ Walks you through making a tag interactively. """
        messages = []
        await ctx.send("What would you like the tag name to be?", delete_after=10)
        converter = TagName()
        original = ctx.message

        def check(msg):
            return msg.author == ctx.author and ctx.channel == msg.channel

        try:
            name = await self.bot.wait_for("message", timeout=30.0, check=check)
        except AsynTOut:
            return await ctx.send("You took too long.",
                                  delete_after=3)
        messages.append(name)

        try:
            ctx.message = name
            name = await converter.convert(ctx, name.content)
        except commands.BadArgument as err:
            return await ctx.send(f"{err}. Redo the command \"{ctx.prefix}tag make\" to retry.",
                                  delete_after=3)
        finally:
            ctx.message = original

        await ctx.send(f"Awesome. Now what about `{name}`'s content? \n"
                       f"**{ctx.prefix}abort will cancel this process.**",
                       delete_after=10)

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)
        except AsynTOut:
            return await ctx.send("You took too long.", delete_after=3)
        messages.append(msg)

        if msg.content == f"{ctx.prefix}abort":
            return await ctx.send("Aborting.", delete_after=3)
        elif msg.content:
            clean_content = await commands.clean_content().convert(ctx, msg.content)
        else:
            clean_content = msg.content

        if msg.attachments:
            clean_content = f"{clean_content}\n{msg.attachments[0].url}"

        try:
            TAGS[name] = clean_content
        finally:
            await ctx.send(f"Tag: {name} has been created.", delete_after=5)
            save_tags(TAGS)
        for item in messages:
            await item.delete(delay=60)

    @tag.command()
    async def list(self, ctx):
        """ list all tags! """
        tags_l = []
        tag_embed = Embed(
            title="**Tag List**",
            colour=0x00ff00)
        for name in TAGS.keys():
            tags_l.append(name)
        tags_str = "\n".join(tag for tag in tags_l)
        tag_embed.add_field(name="Current tags!",
                            value=tags_str, inline=False)
        tag_embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=tag_embed, delete_after=10)


def setup(bot):
    """ Cog setup. """
    bot.add_cog(Tags(bot))
