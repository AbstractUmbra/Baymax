import datetime
import re

import discord
from discord.ext import commands

CAMPFIRE_ID = 766520806289178646
BRO_RE = re.compile(r"^bro\?$")
GAMING_RE = re.compile(r"^\"gaming\"$")


class Campfire(commands.Cog):
    """ Utils for the campfire. """

    def __init__(self, bot: commands.Command):
        self.bot = bot
        self._campfire_cd = commands.CooldownMapping.from_cooldown(
            rate=3, per=10.0, type=commands.BucketType.user
        )

    def strip(self, content: str) -> str:
        return content.strip("\u200b")

    async def cheater(self, cheater_message: discord.Message) -> None:
        bucket = self._campfire_cd.get_bucket(cheater_message)
        retry = bucket.update_rate_limit()

        if retry:
            return
        else:
            await cheater_message.channel.send(
                f"{cheater_message.author.mention} is a fucking cheater."
            )

    @commands.Cog.listener("on_message")
    @commands.Cog.listener("on_message_edit")
    async def message_memes(
        self, before: discord.Message, after: discord.Message = None
    ) -> None:
        if not before.guild or not before.guild.id == CAMPFIRE_ID:
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

    # Bonfire
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == CAMPFIRE_ID:
            if member.bot:
                return await member.add_roles(discord.Object(id=766522043143290900))
            return await member.add_roles(discord.Object(id=766525464092868628))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id != CAMPFIRE_ID:
            return
        now = datetime.datetime.utcnow()
        channel = self.bot.get_channel(784907406164754463)
        embed = discord.Embed(title="Member left", colour=discord.Colour(0x000001))
        embed.set_author(name=member.name, icon_url=member.avatar_url)
        embed.add_field(name="Left at:", value=now)
        embed.timestamp = now
        await channel.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Campfire(bot))
