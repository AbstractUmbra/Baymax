import re

import discord
from discord.ext import commands

BRO_RE = re.compile(r"^bro\?$")
GAMING_RE = re.compile(r"^\"gaming\"$")


class Campfire(commands.Cog):
    """ Utils for the campfire. """

    def __init__(self, bot: commands.Command):
        self.bot = bot
        self._campfire_cd = commands.CooldownMapping.from_cooldown(
            rate=3, per=10.0, type=commands.BucketType.user)

    def strip(self, content: str) -> str:
        return content.strip("\u200b")

    async def cheater(self, cheater_message: discord.Message) -> None:
        bucket = self._campfire_cd.get_bucket(cheater_message)
        retry = bucket.update_rate_limit()

        if retry:
            return
        else:
            await cheater_message.channel.send(f"{cheater_message.author.mention} is a fucking cheater.")

    @commands.Cog.listener("on_message")
    @commands.Cog.listener("on_message_edit")
    async def message_memes(self, before: discord.Message, after: discord.Message = None) -> None:
        if not before.guild or not before.guild.id == 766520806289178646:
            return
        if before.author.bot:
            return

        message = after or before
        channel = message.channel
        content = self.strip(message.content.lower())
        if channel.id == 767194578833899561:
            if not bool(re.match(BRO_RE, content)):
                try:
                    await message.add_reaction("❌")
                except discord.Forbidden:
                    return await self.cheater(message)

        elif channel.id == 767194602972905473:
            if not bool(re.match(GAMING_RE, content)):
                try:
                    await before.add_reaction("❌")
                except discord.Forbidden:
                    return await self.cheater(message)

def setup(bot: commands.Bot):
    bot.add_cog(Campfire(bot))
