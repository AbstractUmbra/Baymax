"""
Robo-Hz Discord Bot
Copyright (C) 2020 AbstractUmbra

Robo-Hz is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Robo-Hz is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with Robo-Hz. If not, see <https://www.gnu.org/licenses/>.
"""

from math import ceil
import os
from random import choice, sample
from time import sleep
from urllib.parse import quote

import discord
from discord.ext import commands

from utils.members import all_voice_members_guild


class Memes(commands.Cog):
    """ Meme cog, fun shit goes here. """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def twist(self, ctx):
        """ Moves all voice members to a random VC. """
        for dcmember in all_voice_members_guild(ctx):
            await dcmember.move_to(
                choice(ctx.message.guild.voice_channels), reason="Was too weak."
            )

    @commands.command()
    async def snap(self, ctx):
        """ Snaps all the members. ;) """
        half_of_current_voice_list = ceil(
            len(all_voice_members_guild(ctx)) / 2
        )
        snapped_users = sample(
            all_voice_members_guild(ctx), half_of_current_voice_list
        )
        snapped_channel = discord.utils.get(
            ctx.message.guild.channels, name="The Soul Stone"
        )
        if os.path.exists("content/snap.gif"):
            await ctx.send(file=discord.File("content/snap.gif"), delete_after=16)
            sleep(8)
            for member in snapped_users:
                await member.move_to(snapped_channel, reason="was snapped.")
        else:
            for member in snapped_users:
                await ctx.send("You should have gone for the head.")
                await ctx.send("**SNAP!**")
                await member.move_to(snapped_channel, reason="was snapped.")

    @commands.command()
    async def spelling(self, ctx):
        """ Time to mess with some vowels. >:D """
        vowels = "aeiouAEIOU"
        # Blacklist server admin.
        for member in ctx.guild.members:
            if member is ctx.guild.owner:
                continue
            original_name = member.display_name
            # time to jumble...
            new_name = ""
            for char in f"{original_name}":
                if char in vowels:
                    new_name += choice(list(vowels))
                else:
                    new_name += char
            await member.edit(nick=new_name.capitalize())

    @commands.command()
    async def dumbass(self, ctx, *, search_param):
        """ Generates a LMGTFY link of the passed text. """
        def url_encode(query):
            """ Encodes URL formatting for query. """
            encoded_query = quote(str(query), safe='')
            return encoded_query

        clean_param = url_encode(search_param)
        url = f"http://lmgtfy.com/?q={clean_param}"
        await ctx.send(url)

    @commands.command()
    async def bobme(self, ctx, *, sentence):
        sentence = sentence.lower()
        new_sentence = ""
        i = True
        for char in sentence:
            if i:
                new_sentence += char.upper()
            else:
                new_sentence += char.lower()
            if char != " ":
                i = not i
        await ctx.send(new_sentence)
        return await ctx.message.delete(delay=3)


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Memes(bot))
