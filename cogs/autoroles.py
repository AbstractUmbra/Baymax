""" Automod cog file. """
from asyncio import TimeoutError as AsynTimeOut

import discord
from discord.ext import commands

from utils.settings import SETTINGS


class AutoRoles(commands.Cog):
    """ AutoRoles Cog. """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """ On reaction_add for live data. """
        guild = self.bot.get_guild(payload.guild_id)
        owner = discord.utils.get(guild.members, id=155863164544614402)
        user = discord.utils.get(guild.members, id=payload.user_id)
        league_role = discord.utils.get(guild.roles, name="League")
        rust_role = discord.utils.get(guild.roles, name="Rust")
        ark_role = discord.utils.get(guild.roles, name="Arkers")
        conan_role = discord.utils.get(guild.roles, name="Exiles")
        if payload.message_id == 656140119643783178:
            if payload.emoji.id == 534488771614474250:
                await user.add_roles(
                    league_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 656150077831774218:
                await user.add_roles(
                    rust_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 656163950475608076:
                await user.add_roles(
                    ark_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 656164554597728315:
                await user.add_roles(
                    conan_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 656166040149164032:
                await owner.send(f"{user.name} from {guild.name} has requested Plex access."
                                 "Please manually approve this for them.")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """ On reaction_remove for live data. """
        guild = self.bot.get_guild(payload.guild_id)
        #owner = discord.utils.get(guild.members, id=155863164544614402)
        user = discord.utils.get(guild.members, id=payload.user_id)
        league_role = discord.utils.get(guild.roles, name="League")
        rust_role = discord.utils.get(guild.roles, name="Rust")
        ark_role = discord.utils.get(guild.roles, name="Arkers")
        conan_role = discord.utils.get(guild.roles, name="Exiles")
        plex_role = discord.utils.get(guild.roles, name="Plexybois")
        if payload.message_id == 656140119643783178:
            if payload.emoji.id == 534488771614474250:
                await user.remove_roles(
                    league_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656150077831774218:
                await user.remove_roles(
                    rust_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656163950475608076:
                await user.remove_roles(
                    ark_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656164554597728315:
                await user.remove_roles(
                    conan_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656166040149164032:
                await user.remove_roles(
                    plex_role,
                    reason="AutoRole remove",
                    atomic=True
                )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """ When a new member joins. """
        new_user_role = discord.utils.get(
            member.guild.roles, id=SETTINGS[str(member.guild.id)]['base_role']
        )

        def check(reaction, user):
            return user == member and str(reaction.emoji) == "👍"

        message = await member.send(
            f"Add '👍' reaction to solemly swear you'll be up to no good in {member.guild.name}."
        )
        await message.add_reaction("👍")

        try:
            _, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
        except AsynTimeOut:
            await member.send("Get fucked you didn't promise fast enough.")
        else:
            await member.send("Mischief managed.")
            await member.add_roles(new_user_role, reason="Server welcome.", atomic=True)


def setup(bot):
    """ Cog setup. """
    bot.add_cog(AutoRoles(bot))
