
""" Memes Cog. """

import os
from random import choice, sample
from math import ceil
from time import sleep
from urllib.parse import quote

from unidecode import unidecode

import discord
from discord.ext import commands

from utils.members import all_voice_members_guild
from . import BaseCog

class Memes(BaseCog):
    """ Meme cog, fun shit goes here. """
    def __init__(self, bot):
        super().__init__(bot)

    @commands.has_any_role(262403103054102528, 337723529837674496, 534447855608266772)
    @commands.command()
    async def twist(self, ctx):
        """ Moves all voice members to a random VC. """
        for dcmember in all_voice_members_guild(ctx):
            await ctx.send(f"You are weak, {dcmember}",
                           delete_after=5)
            await dcmember.move_to(
                choice(ctx.message.guild.voice_channels), reason="Was too weak."
            )

    @commands.has_any_role(262403103054102528, 337723529837674496, 534447855608266772)
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
                print(f"Snapped {member.name}.")
                await member.move_to(snapped_channel, reason="was snapped.")
        else:
            for member in snapped_users:
                await ctx.send("You should have gone for the head.")
                await ctx.send("**SNAP!**")
                print(f"Snapped {member.name}.")
                await member.move_to(snapped_channel, reason="was snapped.")

    @commands.has_any_role(262403103054102528, 337723529837674496, 534447855608266772)
    @commands.command()
    async def spelling(self, ctx):
        """ Time to mess with some vowels. >:D """
        vowels = "aeiouAEIOU"
        # Blacklist server admin.
        for member in ctx.guild.members:
            if member is ctx.guild.owner:
                continue
            original_name = member.display_name
            await ctx.send(f"Jumbling {member.display_name}'s name..", delete_after=10)
            # time to jumble...
            new_name = ""
            # Remove CFS Tag
            if "[𝓒𝓕𝓢] " in original_name:
                original_name = original_name.replace("[𝓒𝓕𝓢] ", "")
            # Take away non-utf8 cahracters.
            original_name = unidecode(original_name).replace(
                "[", "").replace("]", "")
            for char in f"{original_name}":
                if char in vowels:
                    new_name += choice(list(vowels))
                else:
                    new_name += char
            await member.edit(nick=new_name.capitalize(), reason="Cannot spell.")

    @commands.command()
    async def dumbass(self, ctx):
        """ Generates a LMGTFY link of the passed text. """
        msg_body = ctx.message.system_content.replace("^dumbass ", "")

        def url_encode(query):
            """ Encodes URL formatting for query. """
            encoded_query = quote(str(query), safe='')
            return encoded_query

        base_url = "http://lmgtfy.com/?q=^QUERY^"
        lmgtfy_url = base_url.replace(
            "^QUERY^", url_encode(str(msg_body)))
        await ctx.send(lmgtfy_url)

    @commands.command()
    async def emojipls(self, ctx, emoji):
        """ Returns the char of emoji. """
        for g_emoji in ctx.guild.emojis:
            if str(g_emoji) == emoji:
                await ctx.send(f"{g_emoji} | {g_emoji.id}", delete_after=20)


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Memes(bot))
