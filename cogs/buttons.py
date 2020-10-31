import asyncio
import io
import logging
import re

import discord
from discord.ext import commands, menus
from lru import LRU
from utils.paginator import RoboPages

log = logging.getLogger(__name__)


def can_use_spoiler():
    def predicate(ctx):
        if ctx.guild is None:
            raise commands.BadArgument('Cannot be used in private messages.')

        my_permissions = ctx.channel.permissions_for(ctx.guild.me)
        if not (my_permissions.read_message_history and my_permissions.manage_messages and my_permissions.add_reactions):
            raise commands.BadArgument('Need Read Message History, Add Reactions and Manage Messages '
                                       'to permission to use this. Sorry if I spoiled you.')
        return True
    return commands.check(predicate)


SPOILER_EMOJI_ID = 738038828928860269


class UrbanDictionaryPageSource(menus.ListPageSource):
    BRACKETED = re.compile(r'(\[(.+?)\])')

    def __init__(self, data):
        super().__init__(entries=data, per_page=1)

    def cleanup_definition(self, definition, *, regex=BRACKETED):
        def repl(m):
            word = m.group(2)
            return f'[{word}](http://{word.replace(" ", "-")}.urbanup.com)'

        ret = regex.sub(repl, definition)
        if len(ret) >= 2048:
            return ret[0:2000] + ' [...]'
        return ret

    async def format_page(self, menu, entry):
        maximum = self.get_max_pages()
        title = f'{entry["word"]}: {menu.current_page + 1} out of {maximum}' if maximum else entry['word']
        embed = discord.Embed(title=title, colour=0xE86222,
                              url=entry['permalink'])
        embed.set_footer(text=f'by {entry["author"]}')
        embed.description = self.cleanup_definition(entry['definition'])

        try:
            up, down = entry['thumbs_up'], entry['thumbs_down']
        except KeyError:
            pass
        else:
            embed.add_field(
                name='Votes', value=f'\N{THUMBS UP SIGN} {up} \N{THUMBS DOWN SIGN} {down}', inline=False)

        try:
            date = discord.utils.parse_time(entry['written_on'][0:-1])
        except (ValueError, KeyError):
            pass
        else:
            embed.timestamp = date

        return embed


class SpoilerCache:
    __slots__ = ('author_id', 'channel_id', 'title', 'text', 'attachments')

    def __init__(self, data):
        self.author_id = data['author_id']
        self.channel_id = data['channel_id']
        self.title = data['title']
        self.text = data['text']
        self.attachments = data['attachments']

    def has_single_image(self):
        return self.attachments and self.attachments[0].filename.lower().endswith(('.gif', '.png', '.jpg', '.jpeg'))

    def to_embed(self, bot):
        embed = discord.Embed(title=f'{self.title} Spoiler', colour=0x01AEEE)
        if self.text:
            embed.description = self.text

        if self.has_single_image():
            if self.text is None:
                embed.title = f'{self.title} Spoiler Image'
            embed.set_image(url=self.attachments[0].url)
            attachments = self.attachments[1:]
        else:
            attachments = self.attachments

        if attachments:
            value = '\n'.join(f'[{a.filename}]({a.url})' for a in attachments)
            embed.add_field(name='Attachments', value=value, inline=False)

        user = bot.get_user(self.author_id)
        if user:
            embed.set_author(
                name=str(user), icon_url=user.avatar_url_as(format='png'))

        return embed

    def to_spoiler_embed(self, ctx, storage_message):
        description = 'React with <:spoiler:430469957042831371> to reveal the spoiler.'
        embed = discord.Embed(
            title=f'{self.title} Spoiler', description=description)
        if self.has_single_image() and self.text is None:
            embed.title = f'{self.title} Spoiler Image'

        embed.set_footer(text=storage_message.id)
        embed.colour = 0x01AEEE
        embed.set_author(
            name=ctx.author, icon_url=ctx.author.avatar_url_as(format='png'))
        return embed


class SpoilerCooldown(commands.CooldownMapping):
    def __init__(self):
        super().__init__(commands.Cooldown(1, 10.0, commands.BucketType.user))

    def _bucket_key(self, tup):
        return tup

    def is_rate_limited(self, message_id, user_id):
        bucket = self.get_bucket((message_id, user_id))
        return bucket.update_rate_limit() is not None


class Buttons(commands.Cog):
    """Buttons that make you feel."""

    def __init__(self, bot):
        self.bot = bot
        self._spoiler_cache = LRU(128)
        self._spoiler_cooldown = SpoilerCooldown()

    async def redirect_post(self, ctx, title, text):
        storage = self.bot.get_guild(
            705500489248145459).get_channel(772045165049020416)

        supported_attachments = (
            '.png', '.jpg', '.jpeg', '.webm', '.gif', '.mp4', '.txt')
        if not all(attach.filename.lower().endswith(supported_attachments) for attach in ctx.message.attachments):
            raise RuntimeError(
                f'Unsupported file in attachments. Only {", ".join(supported_attachments)} supported.')

        files = []
        total_bytes = 0
        eight_mib = 8 * 1024 * 1024
        for attach in ctx.message.attachments:
            async with ctx.session.get(attach.url) as resp:
                if resp.status != 200:
                    continue

                content_length = int(resp.headers.get('Content-Length'))

                # file too big, skip it
                if (total_bytes + content_length) > eight_mib:
                    continue

                total_bytes += content_length
                fp = io.BytesIO(await resp.read())
                files.append(discord.File(fp, filename=attach.filename))

            if total_bytes >= eight_mib:
                break

        # on mobile, messages that are deleted immediately sometimes persist client side
        await asyncio.sleep(0.2, loop=self.bot.loop)
        await ctx.message.delete()
        data = discord.Embed(title=title)
        if text:
            data.description = text

        data.set_author(name=ctx.author.id)
        data.set_footer(text=ctx.channel.id)

        try:
            message = await storage.send(embed=data, files=files)
        except discord.HTTPException as e:
            raise RuntimeError(
                f'Sorry. Could not store message due to {e.__class__.__name__}: {e}.') from e

        to_dict = {
            'author_id': ctx.author.id,
            'channel_id': ctx.channel.id,
            'attachments': message.attachments,
            'title': title,
            'text': text
        }

        cache = SpoilerCache(to_dict)
        return message, cache

    async def get_spoiler_cache(self, channel_id, message_id):
        try:
            return self._spoiler_cache[message_id]
        except KeyError:
            pass

        storage = self.bot.get_guild(
            182325885867786241).get_channel(430229522340773899)

        # slow path requires 2 lookups
        # first is looking up the message_id of the original post
        # to get the embed footer information which points to the storage message ID
        # the second is getting the storage message ID and extracting the information from it
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return None

        try:
            original_message = await channel.fetch_message(message_id)
            storage_message_id = int(original_message.embeds[0].footer.text)
            message = await storage.fetch_message(storage_message_id)
        except:
            # this message is probably not the proper format or the storage died
            return None

        data = message.embeds[0]
        to_dict = {
            'author_id': int(data.author.name),
            'channel_id': int(data.footer.text),
            'attachments': message.attachments,
            'title': data.title,
            'text': None if not data.description else data.description
        }
        cache = SpoilerCache(to_dict)
        self._spoiler_cache[message_id] = cache
        return cache

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.emoji.id != SPOILER_EMOJI_ID:
            return

        user = self.bot.get_user(payload.user_id)
        if not user or user.bot:
            return

        if self._spoiler_cooldown.is_rate_limited(payload.message_id, payload.user_id):
            return

        cache = await self.get_spoiler_cache(payload.channel_id, payload.message_id)
        embed = cache.to_embed(self.bot)
        await user.send(embed=embed)

    @commands.command()
    @can_use_spoiler()
    async def spoiler(self, ctx, title, *, text=None):
        """Marks your post a spoiler with a title.

        Once your post is marked as a spoiler it will be
        automatically deleted and the bot will DM those who
        opt-in to view the spoiler.

        The only media types supported are png, gif, jpeg, mp4,
        and webm.

        Only 8MiB of total media can be uploaded at once.
        Sorry, Discord limitation.

        To opt-in to a post's spoiler you must click the reaction.
        """

        if len(title) > 100:
            return await ctx.send('Sorry. Title has to be shorter than 100 characters.')

        try:
            storage_message, cache = await self.redirect_post(ctx, title, text)
        except Exception as e:
            return await ctx.send(str(e))

        spoiler_message = await ctx.send(embed=cache.to_spoiler_embed(ctx, storage_message))
        self._spoiler_cache[spoiler_message.id] = cache
        await spoiler_message.add_reaction(':spoiler:430469957042831371')

    @commands.command(name='urban')
    async def _urban(self, ctx, *, word):
        """Searches urban dictionary."""

        url = 'http://api.urbandictionary.com/v0/define'
        async with ctx.session.get(url, params={'term': word}) as resp:
            if resp.status != 200:
                return await ctx.send(f'An error occurred: {resp.status} {resp.reason}')

            js = await resp.json()
            data = js.get('list', [])
            if not data:
                return await ctx.send('No results found, sorry.')

        pages = RoboPages(UrbanDictionaryPageSource(data))
        try:
            await pages.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)


def setup(bot):
    bot.add_cog(Buttons(bot))
