import discord
from discord.ext import commands
from utils.config import Config

BMOJI = "\N{NEGATIVE SQUARED LATIN CAPITAL LETTER B}\N{VARIATION SELECTOR-16}"
# DUNSTON = 705500489248145459
DUNSTON = 364412422540361729
# BCHAN = 705501796159848541
BCHAN = 748996615502823616


class Dunston(commands.Cog):
    """ Stuff relating to Dunston only. """

    def __init__(self, bot):
        self.bot = bot
        self.b_words = Config("dunston_b.json")
        self.cheater_cd = commands.CooldownMapping.from_cooldown(
            1, 10, commands.BucketType.user
        )

    def b_replace(self, in_str: str):
        """ Replace the BMOJI. """
        new_str = in_str.replace(BMOJI, "b")
        new_str = new_str.strip("\u200b")
        return new_str

    async def cheater(self, cheater_message: discord.Message):
        bucket = self.cheater_cd.get_bucket(cheater_message)
        retry = bucket.update_rate_limit()

        if retry:
            return
        else:
            await cheater_message.channel.send(
                f"{cheater_message.author} is a filthy cheater."
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """ Unique Bs only please. """
        if message.channel.id != BCHAN:
            return
        if message.author.bot:
            return

        content = self.b_replace(message.content.lower())

        if not content.startswith(("b", BMOJI)):
            return await message.add_reaction("❌")

        words = self.b_words.get(message.guild.id) or []

        if content in words:
            try:
                await message.add_reaction("❌")
                return
            except discord.Forbidden:
                return await self.cheater(message)

        words.append(self.b_replace(content))

        await self.b_words.put(message.guild.id, sorted(set(words), reverse=True))

    @commands.Cog.listener()
    async def on_message_edit(self, _: discord.Message, after: discord.Message):
        if after.author.bot:
            return
        if not after.guild:
            return
        if after.guild.id != DUNSTON:
            return
        if after.channel.id != BCHAN:
            return

        content = self.b_replace(after.content.lower())

        if not content.startswith(("b", BMOJI)):
            return await after.add_reaction("❌")

        words = self.b_words.get(after.guild.id) or []

        if content in words:
            try:
                await after.add_reaction("❌")
                return
            except discord.Forbidden:
                return await self.cheater(after)

        words.append(self.b_replace(content))

        await self.b_words.put(after.guild.id, sorted(set(words), reverse=True))


def setup(bot):
    bot.add_cog(Dunston(bot))
