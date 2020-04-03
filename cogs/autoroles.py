""" Automod cog file. """
from asyncio import TimeoutError as AsynTimeOut
import typing

import asyncpg
import discord
from discord.ext import commands

from utils import db, cache


class AutoRoleError(commands.CheckFailure):
    """ Autorole error class. """


def requires_autoroles():
    """ Autorole decorator check. """
    async def pred(ctx):
        """ Quick predicate, returns boolean. """
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
    """ Generic config object - dataclass. """
    __slots__ = ("bot", "id", "channel_id", "message_id")

    def __init__(self, *, guild_id, bot, record=None):
        self.id = guild_id
        self.bot = bot

        if record:
            self.channel_id = record['channel_id']
            self.message_id = record['message_id']

    @property
    def channel(self):
        """ Returns the discord.TextChannel we use for config. """
        guild = self.bot.get_guild(self.id)
        return guild and guild.get_channel(self.channel_id)


class AutoRolesConfigTable(db.Table, table_name="autoroles_config"):
    """ Creates the config table. """
    id = db.PrimaryKeyColumn()

    guild_id = db.Column(db.Integer(big=True), index=True)
    channel_id = db.Column(db.Integer(big=True))
    message_id = db.Column(db.Integer(big=True))


class AutoRolesTable(db.Table, table_name="autoroles"):
    """ Creates the autoroles table. """
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
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return
        autorole_deets = await self.get_autoroles(payload.guild_id)
        if not autorole_deets:
            return
        autorole_config = await self.get_autoroles_config(payload.guild_id)
        if not autorole_config:
            return
        if payload.channel_id != autorole_config.channel.id:
            return
        if member.guild.owner_id == member.id:
            # guild owner
            return await autorole_config.channel.send("Can't edit the guild owner lmao.", delete_after=3)
        reaction_message = await autorole_config.channel.fetch_message(autorole_config.message_id)
        if getattr(payload.emoji, "id") is not None:
            for record in autorole_deets:
                try:
                    int(record['role_emoji'])
                except ValueError:
                    continue
                else:
                    if int(record['role_emoji']) == payload.emoji.id:
                        rrole_record = record
                        break
        else:
            for record in autorole_deets:
                if str(record['role_emoji']) == str(payload.emoji):
                    rrole_record = record
                    break
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
                    await approval_channel.send(f"Approval for {member.name} has been rejected by {react_member.name}.", delete_after=5)
                    await reaction_message.remove_reaction(payload.emoji, member)
                    return await message.delete(delay=5)
                elif str(reaction.emoji) == "👍":
                    await member.add_roles(requested_role, reason=f"Autorole - approved by {member.name}", atomic=True)
                    return await message.delete(delay=5)
        else:
            return await member.add_roles(requested_role, reason="Autorole", atomic=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """ On reaction_remove for live data. """
        if not payload.guild_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return
        autorole_deets = await self.get_autoroles(payload.guild_id)
        if not autorole_deets:
            return
        autorole_config = await self.get_autoroles_config(payload.guild_id)
        if payload.channel_id != autorole_config.channel.id:
            return
        if member.guild.owner_id == member.id:
            # guild owner
            return await autorole_config.channel.send("Can't edit the guild owner lmao.", delete_after=3)
        reaction_message = await autorole_config.channel.fetch_message(autorole_config.message_id)
        if getattr(payload.emoji, "id") is not None:
            for record in autorole_deets:
                try:
                    int(record['role_emoji'])
                except ValueError:
                    continue
                else:
                    if int(record['role_emoji']) == payload.emoji.id:
                        rrole_record = record
                        break
        else:
            for record in autorole_deets:
                if str(record['role_emoji']) == str(payload.emoji):
                    rrole_record = record
                    break
        deleting_role = guild.get_role(rrole_record['role_id'])
        await member.remove_roles(deleting_role)
        return await reaction_message.remove_reaction(payload.emoji, member)

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
        current_config = await self.get_autoroles_config(ctx.guild.id)
        message_channel = current_config.channel
        message = await message_channel.fetch_message(current_config.message_id)
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
        await message.add_reaction(emoji)
        return await ctx.send("\N{OK HAND SIGN}")

    @requires_autoroles()
    @reactrole.command(name="remove")
    async def rrole_remove(self, ctx, record_id: int = None):
        """ Remove a reaction role configuration. """
        if not record_id:
            await ctx.send("You have not provided a record id to delete.")
            return await self.rrole_list(ctx)
        query = """ SELECT guild_id FROM autoroles WHERE id = $1; """
        results = await ctx.db.fetchrow(query, record_id)
        if results['guild_id'] != ctx.guild.id:
            return await ctx.send("Invalid autoroles ID. It must belong to your ")
        delete_query = """DELETE FROM autoroles WHERE id = $1 RETURNING role_id, role_emoji;"""
        deletion = await ctx.db.fetchrow(delete_query, record_id)
        if deletion:
            role = ctx.guild.get_role(deletion['role_id'])
            await ctx.send(f"Deleted the entry {record_id} for role: {role.name}.")
        else:
            return await ctx.send("Invalid record ID.")
        current_config = await self.get_autoroles_config(ctx.guild.id)
        channel = current_config.channel
        message = await channel.fetch_message(current_config.message_id)
        emoji = deletion['role_emoji']
        try:
            emoji = await ctx.guild.fetch_emoji(int(emoji))
        except ValueError:
            # it's a string...
            pass
        return await message.remove_reaction(emoji, ctx.me)

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
        for _id, _, role_id, role_emoji, approval, approval_channel in rrole_stuff:
            role = ctx.guild.get_role(role_id)
            try:
                role_emoji = int(role_emoji)
                emoji = self.bot.get_emoji(role_emoji)
            except ValueError:
                emoji = role_emoji
            if approval:
                channel = ctx.guild.get_channel(approval_channel)
                embed.add_field(name=f"{_id} - {role.name}",
                                value=f"{emoji} | approval in: {channel.mention}", inline=False)
            else:
                embed.add_field(name=f"{_id} - {role.name}",
                                value=f"{emoji}", inline=False)

        return await ctx.send(embed=embed)


def setup(bot):
    """ Cog setup. """
    bot.add_cog(AutoRoles(bot))
