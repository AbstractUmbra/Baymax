""" Automod cog file. """
from asyncio import TimeoutError as AsynTimeOut

import discord
from discord.ext import commands

from utils.settings import SETTINGS


def mod_approval_check(reaction, user):
    """ Approval for moderator status. """
    guild = user.guild
    mod_role = discord.utils.get(guild.roles, id=315825729373732867)
    return ((mod_role in user.roles or
             user.id == 155863164544614402)
            and str(reaction.emoji) == "👍"
            and reaction.message.channel.id == 656204288271319064)


def dnd_approval_check(reaction, user):
    """ Approval for DnD chat. """
    guild = user.guild
    mod_role = discord.utils.get(guild.roles, id=460536832635961374)
    return ((mod_role in user.roles or
             user.id == 155863164544614402)
            and str(reaction.emoji) == "👍"
            and reaction.message.channel.id == 460536968565227550)


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
        if payload.message_id == 656140119643783178:
            if payload.emoji.id == 534488771614474250:
                league_role = discord.utils.get(guild.roles, name="League")
                await user.add_roles(
                    league_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 656150077831774218:
                rust_role = discord.utils.get(guild.roles, name="Rust")
                await user.add_roles(
                    rust_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 656163950475608076:
                ark_role = discord.utils.get(guild.roles, name="Arkers")
                await user.add_roles(
                    ark_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 656164554597728315:
                conan_role = discord.utils.get(guild.roles, name="Exiles")
                await user.add_roles(
                    conan_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 656166040149164032:
                await owner.send(f"{user.name} from {guild.name} has requested Plex access. "
                                 "Please manually approve this for them.")
            elif payload.emoji.id == 656178696385986560:
                dnd_channel = discord.utils.get(
                    guild.channels, id=460536968565227550)
                dnd_role = discord.utils.get(
                    guild.roles, id=460536832635961374)
                message = await dnd_channel.send(
                    f"{user.name} has requested to join the Bear Trap. "
                    "Reaction approval is required.")
                await message.add_reaction("👍")

                try:
                    _, react_member = await self.bot.wait_for(
                        "reaction_add", timeout=28800.0, check=dnd_approval_check)
                except AsynTimeOut:
                    await dnd_channel.send(
                        f"Approval for {user} not gained within 24 hours. "
                        f"Cancelling request.", delete_after=10
                    )
                    return await message.delete()
                else:
                    await user.add_roles(
                        dnd_role,
                        reason=f"Member approval by {react_member.name}.",
                        atomic=True)
                    return await message.delete()
            elif payload.emoji.id == 656203981655375887:
                mod_channel = discord.utils.get(
                    guild.channels, id=656204288271319064)
                mod_role = discord.utils.get(
                    guild.roles, id=315825729373732867)
                message = await mod_channel.send(
                    f"{user.name} has requested to become an Moderator. "
                    "Reaction approval is required.")
                await message.add_reaction("👍")

                try:
                    _, react_member = await self.bot.wait_for(
                        "reaction_add", timeout=28800.0, check=mod_approval_check)
                except AsynTimeOut:
                    await mod_channel.send(
                        f"Approval for {user} not gained within 24 hours. "
                        "Cancelling request.", delete_after=10
                    )
                    return await message.delete()
                else:
                    await user.add_roles(
                        mod_role,
                        reason=f"Moderator approved by {react_member.name}.",
                        atomic=True)
                    return await message.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """ On reaction_remove for live data. """
        guild = self.bot.get_guild(payload.guild_id)
        user = discord.utils.get(guild.members, id=payload.user_id)
        if payload.message_id == 656140119643783178:
            if payload.emoji.id == 534488771614474250:
                league_role = discord.utils.get(
                    guild.roles, id=563098367329173509)
                await user.remove_roles(
                    league_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656150077831774218:
                rust_role = discord.utils.get(
                    guild.roles, id=656148297957900288)
                await user.remove_roles(
                    rust_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656163950475608076:
                ark_role = discord.utils.get(
                    guild.roles, id=558417863694614537)
                await user.remove_roles(
                    ark_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656164554597728315:
                conan_role = discord.utils.get(
                    guild.roles, id=638376237575831553)
                await user.remove_roles(
                    conan_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656166040149164032:
                plex_role = discord.utils.get(
                    guild.roles, id=456897532128395265)
                await user.remove_roles(
                    plex_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656178696385986560:
                dnd_role = discord.utils.get(
                    guild.roles, id=460536832635961374)
                await user.remove_roles(
                    dnd_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656203981655375887:
                mod_role = discord.utils.get(
                    guild.roles, id=315825729373732867)
                await user.remove_roles(
                    mod_role,
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
