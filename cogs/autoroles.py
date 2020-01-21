""" Automod cog file. """
from asyncio import TimeoutError as AsynTimeOut

import discord
from discord.ext import commands

from . import BaseCog


def mod_approval_check(reaction, user, mod_role):
    """ Approval for moderator status. """
    if str(reaction.emoji) == "👍":
        return ((mod_role in user.roles or
                 user.id == 155863164544614402)
                and reaction.message.channel.id == 656204288271319064)
    elif str(reaction.emoji) == "👎":
        if (reaction.message.channel.id == 656204288271319064
                and mod_role in user.roles):
            return True
    return False


def dnd_approval_check(reaction, user, dnd_role):
    """ Approval for DnD chat. """
    if str(reaction.emoji) == "👍":
        return ((dnd_role in user.roles or
                 user.id == 155863164544614402)
                and reaction.message.channel.id == 460536968565227550)
    elif str(reaction.emoji) == "👎":
        if (reaction.message.channel.id == 460536968565227550
                and dnd_role in user.roles):
            return True
    return False


class AutoRoles(BaseCog):
    """ AutoRoles Cog. """

    def cog_check(self, ctx):
        if not ctx.guild:
            return False
        return True

    def __init__(self, bot):
        super().__init__(bot)
        self.ark_role = None
        self.conan_role = None
        self.dnd_role = None
        self.league_role = None
        self.mod_role = None
        self.new_user_role = None
        self.plex_role = None
        self.rust_role = None
        self.drg_role = None
        self.mhw_role = None

        self.dnd_channel = None
        self.mod_channel = None
        self.request_channel = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(self.bot.guilds[0].id)
        self.request_channel = self.bot.get_channel(656139436651839488)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """ On reaction_add for live data. """
        guild = self.bot.get_guild(payload.guild_id)
        owner = guild.get_member(155863164544614402)
        user = discord.utils.get(guild.members, id=payload.user_id)
        if payload.message_id == 656140119643783178:
            if payload.emoji.id == 534488771614474250:
                self.league_role = guild.get_role(563098367329173509)
                await user.add_roles(
                    self.league_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 656150077831774218:
                self.rust_role = guild.get_role(656148297957900288)
                await user.add_roles(
                    self.rust_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 656163950475608076:
                self.ark_role = guild.get_role(558417863694614537)
                await user.add_roles(
                    self.ark_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 656164554597728315:
                self.conan_role = guild.get_role(638376237575831553)
                await user.add_roles(
                    self.conan_role,
                    reason="AutoRole",
                    atomic=True
                )
            elif payload.emoji.id == 665263107022782484:
                self.drg_role = guild.get_role(665263294763761684)
                await user.add_roles(
                    self.drg_role,
                    reason="Autorole",
                    atomic=True
                )
            elif payload.emoji.id == 667049791305547801:
                self.mhw_role = guild.get_role(667050135263641614)
                await user.add_roles(
                    self.mhw_role,
                    reason="Autorole",
                    atomic=True
                )
            elif payload.emoji.id == 656166040149164032:
                await owner.send(f"{user.name} from {guild.name} has requested Plex access. "
                                 "Please manually approve this for them.")
            elif payload.emoji.id == 656178696385986560:
                self.dnd_role = guild.get_role(460536832635961374)
                self.dnd_channel = self.bot.get_channel(460536968565227550)
                message = await self.dnd_channel.send(
                    f"{user.name} has requested to join the Bear Trap. "
                    "Reaction approval is required.")
                await message.add_reaction("👍")
                await message.add_reaction("👎")

                try:
                    reaction, react_member = await self.bot.wait_for(
                        "reaction_add", timeout=28800.0, check=dnd_approval_check)
                except AsynTimeOut:
                    await self.dnd_channel.send(
                        f"Approval for {user} not gained within 24 hours. "
                        f"Cancelling request.", delete_after=10
                    )
                    return await message.delete()
                else:
                    if reaction.emoji == "👎":
                        await self.dnd_channel.send(
                            f"Approval for {user.name} has been rejected.", delete_after=5)  #
                        request_message = await self.request_channel.fetch_message(
                            656140119643783178)
                        await request_message.remove_reaction(payload.emoji, user)
                    else:
                        await user.add_roles(
                            self.dnd_role,
                            reason=f"Member approval by {react_member.name}.",
                            atomic=True)
                    return await message.delete()
            elif payload.emoji.id == 656203981655375887:
                self.mod_role = guild.get_role(315825729373732867)
                self.mod_channel = self.bot.get_channel(656204288271319064)
                message = await self.mod_channel.send(
                    f"{user.name} has requested to become an Moderator. "
                    "Reaction approval is required.")
                await message.add_reaction("👍")
                await message.add_reaction("👎")

                try:
                    reaction, react_member = await self.bot.wait_for(
                        "reaction_add", timeout=28800.0, check=mod_approval_check)
                except AsynTimeOut:
                    await self.mod_channel.send(
                        f"Approval for {user} not gained within 24 hours. "
                        "Cancelling request.", delete_after=10
                    )
                    return await message.delete()
                else:
                    if reaction.emoji == "👎":
                        await self.mod_channel.send(
                            f"Approval for {user.name} has been rejected.", delete_after=5)
                        request_message = await self.request_channel.fetch_message(
                            656140119643783178)
                        await request_message.remove_reaction(payload.emoji, user)
                    else:
                        await user.add_roles(
                            self.mod_role,
                            reason=f"Member approval by {react_member.name}.",
                            atomic=True)
                    return await message.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """ On reaction_remove for live data. """
        guild = self.bot.get_guild(payload.guild_id)
        user = discord.utils.get(guild.members, id=payload.user_id)
        if payload.message_id == 656140119643783178:
            if payload.emoji.id == 534488771614474250:
                await user.remove_roles(
                    self.league_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656150077831774218:
                await user.remove_roles(
                    self.rust_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656163950475608076:
                await user.remove_roles(
                    self.ark_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656164554597728315:
                await user.remove_roles(
                    self.conan_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 665263107022782484:
                await user.remove_roles(
                    self.drg_role,
                    reason="Autorole",
                    atomic=True
                )
            elif payload.emoji.id == 667049791305547801:
                await user.remove_roles(
                    self.mhw_role,
                    reason="Autorole",
                    atomic=True
                )
            elif payload.emoji.id == 656166040149164032:
                await user.remove_roles(
                    self.plex_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656178696385986560:
                await user.remove_roles(
                    self.dnd_role,
                    reason="AutoRole remove",
                    atomic=True
                )
            elif payload.emoji.id == 656203981655375887:
                await user.remove_roles(
                    self.mod_role,
                    reason="AutoRole remove",
                    atomic=True
                )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """ When a new member joins. """
        def check(reaction, user):
            return user == member and str(reaction.emoji) == "👍"

        self.new_user_role = member.guild.get_role(174703372631277569)
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
            await member.add_roles(self.new_user_role, reason="Server welcome.", atomic=True)


def setup(bot):
    """ Cog setup. """
    bot.add_cog(AutoRoles(bot))
