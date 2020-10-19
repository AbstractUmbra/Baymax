from discord import Message
from discord.ext import commands
from utils.config import Config

BMOJI = "\N{NEGATIVE SQUARED LATIN CAPITAL LETTER B}\N{VARIATION SELECTOR-16}"
#DUNSTON = 705500489248145459
DUNSTON = 364412422540361729
#BCHAN = 705501796159848541
BCHAN = 748996615502823616


class Dunston(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.b_words = Config("dunston_b.json")

    def b_replace(self, in_str: str):
        """ Replace the BMOJI. """
        return in_str.replace(BMOJI, "b")

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        """ Unique Bs only please. """
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.guild.id != DUNSTON:
            return
        if message.channel.id != BCHAN:
            return

        content = self.b_replace(message.content.lower())

        if not content.startswith(("b", BMOJI)):
            return await message.add_reaction("❌")

        words = self.b_words.get(message.guild.id) or []

        if content in words:
            return await message.add_reaction("❌")

        words.append(self.b_replace(content))

        await self.b_words.put(message.guild.id, sorted(set(words), reverse=True))


    @commands.Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
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
            return await after.add_reaction("❌")

        words.append(self.b_replace(content))

        await self.b_words.put(after.guild.id, sorted(set(words), reverse=True))


def setup(bot):
    bot.add_cog(Dunston(bot))
