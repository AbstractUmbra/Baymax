""" Automod cog file. """
from asyncio import TimeoutError as AsynTimeOut
import typing

import asyncpg
import discord
from discord.ext import commands

from utils import db, cache


class AutoRoleError(commands.CheckFailure):
    pass


def requires_autoroles():
    async def pred(ctx):
        if not ctx.guild:
            return False

        cog = ctx.bot.get_cog("AutoRoles")

        ctx.autoroles = await cog.get_autoroles_config(ctx.guild.id)
        if ctx.autoroles.channel is None:
            raise AutoRoleError(
                "\N{WARNING SIGN} Autoroles have not been set up for this guild.")

        return True
    return commands.check(pred)


class AutoRolesConfig:
    __slots__ = ("bot", "id", "channel_id", "message_id")

    def __init__(self, *, guild_id, bot, record=None):
        self.id = guild_id
        self.bot = bot

        if record:
            self.channel_id = record['channel_id']
            self.message_id = record['message_id']

    @property
    def channel(self):
        guild = self.bot.get_guild(self.id)
        return guild and guild.get_channel(self.channel_id)


class AutoRolesConfigTable(db.Table, table_name="autoroles_config"):
    id = db.PrimaryKeyColumn()

    guild_id = db.Column(db.Integer(big=True), index=True)
    channel_id = db.Column(db.Integer(big=True))
    message_id = db.Column(db.Integer(big=True))


class AutoRolesTable(db.Table, table_name="autoroles"):
    id = db.PrimaryKeyColumn()

    guild_id = db.Column(db.Integer(big=True), index=True)
    role_id = db.Column(db.Integer(big=True))
    role_emoji = db.Column(db.String)
    approval_req = db.Column(db.Boolean)
    approval_channel_id = db.Column(db.Integer(big=True))


class AutoRoles(commands.Cog):
    """ AutoRoles Cog. """

    def cog_check(self, ctx):
        if not ctx.guild:
            return False
        return True

    def __init__(self, bot):
        self.bot = bot

    @cache.cache()
    async def get_autoroles_config(self, guild_id: int, *, connection=None) -> AutoRolesConfig:
        """ Gets the guild config from postgres. """
        connection = connection or self.bot.pool
        query = """SELECT *
                   FROM autoroles_config
                   WHERE guild_id = $1
                """
        results = await connection.fetchrow(query, guild_id)
        print(results)
        return AutoRolesConfig(guild_id=guild_id, bot=self.bot, record=results)

    async def get_autoroles(self, guild_id: int, *, connection=None) -> asyncpg.Record:
        """ Gets the autoroles for the current guild. """
        connection = connection or self.bot.pool
        query = """SELECT *
                   FROM autoroles
                   WHERE guild_id = $1
                """
        return await connection.fetch(query, guild_id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """ On reaction_add for live data. """
        rrole_record = None  # placeholder
        if not payload.guild_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        autorole_deets = await self.get_autoroles(payload.guild_id)
        if not autorole_deets:
            return
        autorole_config = await self.get_autoroles_config(payload.guild_id)
        if not autorole_config:
            return
        if payload.channel_id != autorole_config.channel.id:
            return
        reaction_message = await autorole_config.channel.fetch_message(autorole_config.message_id)
        member = guild.get_member(payload.user_id)
        if hasattr(payload.emoji, "id"):
            for record in autorole_deets:
                if int(record['role_emoji']) == payload.emoji.id:
                    rrole_record = record
        else:
            for record in autorole_deets:
                if str(record['role_emoji']) == str(payload.emoji):
                    rrole_record = record
        requested_role = guild.get_role(rrole_record['role_id'])
        if rrole_record['approval_req']:
            approval_channel = guild.get_channel(
                rrole_record['approval_channel_id'])
            message = await approval_channel.send(f"{member.name} has requested access to the {requested_role.mention} role. Do you accept?")
            await message.add_reaction("👍")
            await message.add_reaction("👎")

            def check(reaction, user):
                """ Approval check. """
                return reaction.message.channel.id == approval_channel.id and requested_role in user.roles

            print("hitting try")
            try:
                reaction, react_member = await self.bot.wait_for(
                    "reaction_add", timeout=28800.0, check=check)
            except AsynTimeOut:
                await approval_channel.send(
                    f"Approval for {member.name} not gained within 24 hours. "
                    f"Cancelling request.", delete_after=10)
                return await message.delete()
            else:
                if str(reaction.emoji) == "👎":
                    print("neet")
                    await approval_channel.send(f"Approval for {member.name} has been rejected by {react_member.name}.", delete_after=5)
                    return await reaction_message.remove_reaction(payload.emoji, member)
                elif str(reaction.emoji) == "👍":
                    print("yeet")
                    await member.add_roles(requested_role, reason=f"Autorole - approved by {member.name}", atomic=True)
                    return await message.delete(delay=5)
        else:
            return await member.add_roles(requested_role, reason="Autorole", atomic=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """ On reaction_remove for live data. """

    @commands.group(invoke_without_command=True, aliases=["rr"])
    async def reactrole(self, ctx):
        """ Time for some react roles! """
        if not ctx.invoked_subcommand:
            return await self.rrole_list(ctx)

    @reactrole.command(name="config")
    async def rrole_config(self, ctx, message: discord.Message):
        """ Configure this guilds reaction roles. """
        query = """INSERT INTO autoroles_config (guild_id, channel_id, message_id)
                   VALUES ($1, $2, $3)
                """
        await ctx.db.execute(query, ctx.guild.id, message.channel.id, message.id)
        await ctx.message.add_reaction("\N{OK HAND SIGN}")

    @requires_autoroles()
    @commands.has_guild_permissions(manage_roles=True)
    @reactrole.command(name="add")
    async def rrole_add(self,
                        ctx,
                        role: discord.Role,
                        emoji: typing.Union[discord.Emoji, discord.PartialEmoji, str],
                        approval_channel: typing.Optional[discord.TextChannel]):
        """ Add a reaction role for this guild. """
        current_autoroles = await self.get_autoroles(ctx.guild.id)
        roles = [record['role_id'] for record in current_autoroles]
        emojis = [record['role_emoji'] for record in current_autoroles]
        if role.id in roles:
            return await ctx.send("\N{CROSS MARK} This role is already set up for autoroles.")
        if isinstance(emoji, str):
            if emoji in emojis:
                return await ctx.send("\N{CROSS MARK} This emoji is already set up for autoroles.")
        elif isinstance(emoji, (discord.Emoji, discord.PartialEmoji)):
            if not hasattr(emoji, "guild_id"):
                return await ctx.send("You must use an emoji that belongs to this guild, if custom.")
            if str(emoji.id) in emojis:
                return await ctx.send("\N{CROSS MARK} This emoji is already set up for autoroles.")
        if approval_channel:
            query = """INSERT INTO autoroles (guild_id, role_id, role_emoji, approval_req, approval_channel_id)
                    VALUES ($1, $2, $3, $4, $5)
                    """
            if isinstance(emoji, str):
                await ctx.db.execute(query, ctx.guild.id, role.id, emoji, True, approval_channel.id)
            elif isinstance(emoji, discord.Emoji):
                await ctx.db.execute(query, ctx.guild.id, role.id, str(emoji.id), True, approval_channel.id)
            elif isinstance(emoji, discord.PartialEmoji):
                await ctx.db.execute(query, ctx.guild.id, role.id, str(emoji.id), True, approval_channel.id)
        else:
            query = """INSERT INTO autoroles(guild_id, role_id, role_emoji, approval_req)
                    VALUES($1, $2, $3, $4)
                    """
            if isinstance(emoji, str):
                await ctx.db.execute(query, ctx.guild.id, role.id, emoji, False)
            elif isinstance(emoji, discord.Emoji):
                if not emoji.guild_id == ctx.guild.id:
                    return await ctx.send("You must use an emoji that belongs to this guild, if custom.")
                await ctx.db.execute(query, ctx.guild.id, role.id, str(emoji.id), False)
            elif isinstance(emoji, discord.PartialEmoji):
                await ctx.db.execute(query, ctx.guild.id, role.id, str(emoji.id), False)
        return await ctx.send("\N{OK HAND SIGN}")

    @requires_autoroles()
    @reactrole.command(name="remove")
    async def rrole_remove(self, ctx, record_id=None):
        """ Remove a reaction role configuration. """
        if not record_id:
            await ctx.send("You have not provided a record id to delete.")
            self.rrole_list(ctx)

    @requires_autoroles()
    @commands.has_guild_permissions(manage_roles=True)
    @reactrole.command(name="list")
    async def rrole_list(self, ctx):
        """ List the reactions roles for this guild. """
        query = "SELECT * FROM autoroles WHERE guild_id = $1;"
        rrole_stuff = await ctx.db.fetch(query, ctx.guild.id)
        if not rrole_stuff:
            return await ctx.send("This guild has no reaction roles set up.")
        embed = discord.Embed(title="Guild ReactRoles",
                              colour=discord.Colour.blurple())
        for _id, _, role_id, role_emoji, _, _ in rrole_stuff:
            role = ctx.guild.get_role(role_id)
            emoji = self.bot.get_emoji(role_emoji)
            embed.add_field(name=f"{_id} - {role.name}",
                            value=f"{emoji}", inline=False)
        return await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """ When a new member joins. """
        def check(reaction, user):
            return user == member and str(reaction.emoji) == "👍"

        new_user_role = member.guild.get_role(174703372631277569)
        try:
            message = await member.send(
                f"Add '👍' reaction to solemly swear you'll be up to no good in {member.guild.name}."
            )
            await message.add_reaction("👍")
        except discord.Forbidden:
            return await member.add_roles(new_user_role, reason="Fucker has no DMs", atomic=True)

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
