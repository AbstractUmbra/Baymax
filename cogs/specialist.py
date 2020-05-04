"""
Robo-Hz Discord Bot
Copyright (C) 2020 64Hz

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
import asyncio
import datetime
import random
import string
import textwrap

import discord
from discord.ext import commands

from utils import checks, time, specialist

SPTV_GUILD_ID = 690566307409821697


class Specialist(commands.Cog):
    """ Class designed for SpecialistTV channel. """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild.id == 690566307409821697

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> discord.Message:
        """ This is a cog error handler. """
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)

    async def get_reacts(self, reaction_list: list) -> list:
        """ Returns a flattened list of all users who reacted. """
        reacted_list = []
        for reaction in reaction_list:
            reaction_flat = await reaction.users().flatten()
            for member in reaction_flat:
                if member.bot:
                    continue
                reacted_list.append(member)
        return reacted_list

    async def member_in_multiple(self, member: discord.Member, event_type: str):
        """ Non-generic. Checks if member is in multiple gaming event for same type. """
        query = """SELECT *
                   FROM reminders
                   WHERE event = $1
                """
        records = await self.bot.pool.fetch(query, event_type)
        count = 0
        for record in records:
            channel = member.guild.get_channel(int(record['extra']['args'][1]))
            event_message = await channel.fetch_message(int(record['extra']['kwargs']['message_id']))
            reacts = await self.get_reacts(event_message.reactions)
            if member in reacts:
                count += 1
        if count > 1:
            return True
        return False

    @commands.group(invoke_without_command=True, aliases=["Specialist"], hidden=True)
    async def specialist(self, ctx: commands.Context):
        """ Top level command for SpecialistTV commands. See the help for more details on subcommands! """
        if not ctx.invoked_subcommand:
            await ctx.send("This command requires a subcommand!")
            return await ctx.send_help("specialist")

    @specialist.command(hidden=True)
    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.user)
    async def announcements(self, ctx: commands.Context):
        """ Toggles announcement notification. """
        role = ctx.guild.get_role(696916589248774174)
        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
        else:
            await ctx.author.add_roles(role)
        return await ctx.message.add_reaction("\N{OK HAND SIGN}")

    @announcements.error
    async def announce_error(self, ctx: commands.Context, error: Exception):
        """ Local error handler for command. """
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f"Sorry this command is currently on cooldown for you. Try again in {error.seconds} seconds.")

    @commands.group(aliases=['Event'], hidden=True)
    @checks.mod_or_permissions(manage_message=True)
    async def event(self, ctx: commands.Context):
        """ Primary command for events. """
        if not ctx.invoked_subcommand:
            return await ctx.send("This command requires a subcommand.")

    @commands.command(name="events")
    async def event_list(self, ctx: commands.Context):
        """ Shortcut to event list. """
        return await self.events_list(ctx)

    @event.command(aliases=['bfme', 'BFME', 'BFME2'], usage="<when>", invoke_without_command=True)
    async def bfme2(self, ctx: commands.Context, *, when: time.UserFriendlyTime(commands.clean_content, default="\u2026")):
        """ Create a BFME2 event. """
        reminder = self.bot.get_cog("Reminder")
        if not reminder:
            return await ctx.send("Sorry, this functionality is currently unavailable.")
        message = await ctx.send("Placeholder")
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        role = ctx.guild.create_role("".join(random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5)),
                                     colour=discord.Colour(0x7a6d42),
                                     reason="Event creation.")
        await reminder.create_timer(event_trigger, 'bfme2', ctx.author.id,
                                    ctx.channel.id,
                                    when.arg,
                                    connection=ctx.db,
                                    created=ctx.message.created_at,
                                    message_id=message.id,
                                    role_id=role.id)
        await reminder.create_timer(cancellation_trigger, 'event_check', ctx.author.id,
                                    ctx.channel.id,
                                    when.arg,
                                    connection=ctx.db,
                                    created=ctx.message.created_at,
                                    message_id=message.id,
                                    role_id=role.id)
        embed = discord.Embed(title="BFME2 Event Prep!",
                              colour=discord.Colour.gold())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url=ctx.author.avatar_url)
        embed.set_image(
            url="https://download.hipwallpaper.com/desktop/1920/1080/66/33/HBOjoz.jpg")
        embed.add_field(name="Plan of action",
                        value=f"{when.arg}", inline=False)
        embed.add_field(
            name="When", value=f"{when.dt.strftime('%d-%m-%Y %H:%M')}", inline=True)
        embed.add_field(name="Game install details:",
                        value="Can be found [here](https://forums.revora.net/topic/105190-bfme1bfme2rotwk-games-download-installation-guide/).", inline=False)
        embed.add_field(name="How to invite to Discord:",
                        value="Just give anyone who wants to join [this link](https://discord.gg/RJrmTjP).", inline=True)
        embed.description = "Add a reaction to this post to join this event!"
        await message.edit(content="", embed=embed)
        return await ctx.message.delete()

    @event.command(aliases=['aoe', 'AOE', 'AOE2'], usage="<when>", invoke_without_command=True)
    async def aoe2(self, ctx: commands.Context, *, when: time.UserFriendlyTime(commands.clean_content, default="\u2026")):
        """ Create an AOE2 event. """
        reminder = self.bot.get_cog("Reminder")
        if not reminder:
            return await ctx.send("Sorry, this functionality is currently unavailable.")
        message = await ctx.send("Placeholder")
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        role = ctx.guild.create_role("".join(random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5)),
                                     colour=discord.Colour(0x702d2d),
                                     reason="Event creation.")
        await reminder.create_timer(event_trigger, 'aoe2', ctx.author.id,
                                    ctx.channel.id,
                                    when.arg,
                                    connection=ctx.db,
                                    created=ctx.message.created_at,
                                    message_id=message.id,
                                    role_id=role.id)
        await reminder.create_timer(cancellation_trigger, 'event_check', ctx.author.id,
                                    ctx.channel.id,
                                    when.arg,
                                    connection=ctx.db,
                                    created=ctx.message.created_at,
                                    message_id=message.id,
                                    role_id=role.id)
        embed = discord.Embed(title="AOE2 Event Prep!",
                              colour=discord.Colour.red())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Plan of action", value=f"{when.arg}")
        embed.add_field(
            name="When", value=f"{when.dt.strftime('%d-%m-%Y %H:%M')}")
        embed.description = "Add a reaction to this post to join this event!"
        await message.edit(content="", embed=embed)
        return await ctx.message.delete()

    @event.command(name="list")
    async def events_list(self, ctx: commands.Context):
        """ Send a list of events. """
        query = """SELECT id, expires, event, extra #>> '{args,2}'
                   FROM reminders
                   WHERE event = 'bfme2'
                   OR event = 'aoe2'
                   AND extra #>> '{args,0}' = $1
                   ORDER BY expires
                   LIMIT 10;
                """
        records = await ctx.db.fetch(query, str(ctx.author.id))

        if len(records) == 0:
            return await ctx.send("No currently awaiting events.")

        embed = discord.Embed(colour=discord.Colour.green(), title="Events")

        if len(records) == 10:
            embed.set_footer(text="Only showing up to 10 reminders.")
        else:
            embed.set_footer(
                text=f"{len(records)} reminder{'s' if len(records) > 1 else ''}")

        for _id, expires, event, message in records:
            shorten = textwrap.shorten(message, width=512)
            embed.add_field(
                name=f"{_id}: In {time.human_timedelta(expires)}", value=f"`{event.upper()}`: {shorten}", inline=False)
        await ctx.send(embed=embed)

    @event.command(name="delete")
    async def events_delete(self, ctx: commands.Context, record_id: int):
        """ Delete a specific event that the author owns. """
        query = """DELETE FROM reminders
                   WHERE id = $1
                   AND extra #>> '{args,0}' = $2
                   RETURNING event, extra;
                """
        event_check_query = """DELETE FROM reminders
                               WHERE extra #>> '{kwargs,message_id}' = $1
                            """
        records = await ctx.db.fetch(query, record_id, str(ctx.author.id))
        if not records:
            return await ctx.send("Could not delete event by that ID. Are you sure it's there and you're it's author?")
        message_deets = {int(record['extra']['args'][1]): str(
            record['extra']['kwargs']['message_id']) for record in records}
        for chan_id, m_id in message_deets.items():
            channel = self.bot.get_channel(chan_id)
            message = await channel.fetch_message(m_id)
            await ctx.db.execute(event_check_query, str(message.id))
        for record in records:
            if record['event'] == "event_check":
                continue
            await message.clear_reactions()
        return await ctx.send("Deleted event.")

    @commands.Cog.listener()
    async def on_event_check_timer_complete(self, event):
        """ On 'event_check' complete. """
        _, channel_id, message = event.args

        try:
            channel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        message_id = event.kwargs.get("message_id")
        prev_message = await channel.fetch_message(int(message_id))
        reacted_list = await self.get_reacts(prev_message.reactions)
        members = {member.id for member in reacted_list}
        if len(members) < 3:
            await prev_message.clear_reactions()
            del_query = """DELETE FROM reminders
                        WHERE extra #>> '{kwargs,message_id}' = $1;
                        """
            await self.bot.pool.execute(del_query, str(event.kwargs['message_id']))
            return await prev_message.edit(content=f"The event for ***{message}*** has been cancelled due to lack of members!", embed=None)

    @commands.Cog.listener()
    async def on_bfme2_timer_complete(self, event):
        """ On 'bfme2' timer complete. """
        author_id, channel_id, message = event.args

        try:
            channel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        message_id = event.kwargs.get('message_id')
        prev_message = await channel.fetch_message(int(message_id))
        role = channel.guild.get_role(event.kwargs.get('role_id'))
        reacted_list = await self.get_reacts(prev_message.reactions)
        member_names = {member.display_name for member in reacted_list}
        embed = discord.Embed(title="**BFME 2 Event time**",
                              colour=discord.Colour.gold())
        event_author = channel.guild.get_member(author_id)
        embed.set_author(name=event_author.display_name,
                         icon_url=event_author.avatar_url)
        embed.set_image(
            url="https://download.hipwallpaper.com/desktop/1920/1080/66/33/HBOjoz.jpg")
        if member_names:
            embed.add_field(name="Members that signed up",
                            value=", ".join(member_names))
        embed.add_field(name="Plan of action",
                        value=f"{message}")
        embed.description = random.choice(specialist.LOTR_QUOTES)
        await channel.send(role.mention, embed=embed)
        await asyncio.sleep(60)
        return await role.delete()

    @commands.Cog.listener()
    async def on_aoe2_timer_complete(self, event):
        """ On 'aoe2' event timer complete. """
        author_id, channel_id, message = event.args

        try:
            channel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        message_id = event.kwargs.get('message_id')
        prev_message = await channel.fetch_message(message_id)
        role = event.kwargs.get('role_id')
        reacted_list = await self.get_reacts(prev_message.reactions)
        member_names = set([member.display_name for member in reacted_list])
        embed = discord.Embed(title="**AOE 2 Event time**",
                              colour=discord.Colour.red())
        event_author = channel.guild.get_member(author_id)
        embed.set_author(name=event_author.display_name,
                         icon_url=event_author.avatar_url)
        embed.set_image(
            url="https://news.xbox.com/en-us/wp-content/uploads/sites/2/HERO-35.jpg?fit=1920%2C1080")
        if member_names:
            embed.add_field(name="Members that signed up",
                            value=", ".join(member_names))
        embed.add_field(name="Plan of action",
                        value=f"{message}")
        embed.description = random.choice(specialist.AOE_QUOTES)
        await channel.send(role.mention, embed=embed)
        await asyncio.sleep(60)
        return await role.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """ Let's give event go-ers a role! """
        if not payload.guild_id:
            return
        if payload.guild_id != SPTV_GUILD_ID:
            return
        guild = self.bot.get_guild(payload.guild_id)
        member = payload.member or guild.get_member(payload.user_id)
        if member.bot:
            return
        query = """SELECT *
                   FROM reminders
                   WHERE event = 'bfme2'
                   OR event = 'aoe2'
                """
        records = await self.bot.pool.fetch(query)
        for record in records:
            if int(record['extra']['args'][1]) == payload.channel_id:
                if int(record['extra']['kwargs']['message_id']) == payload.message_id:
                    role = guild.get_role(record['extra']['kwargs']['role_id'])
                    return await member.add_roles(role, reason="Event sign up.")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """ Chickens out of the event. """
        if not payload.guild_id:
            return
        if payload.guild_id != SPTV_GUILD_ID:
            return
        guild = self.bot.get_guild(payload.guild_id)
        member = payload.member or guild.get_member(payload.user_id)
        if member.bot:
            return
        query = """SELECT *
                   FROM reminders
                   WHERE event = 'bfme2'
                   OR event = 'aoe2'
                """
        records = await self.bot.pool.fetch(query)
        for record in records:
            if int(record['extra']['args'][1]) == payload.channel_id:
                if int(record['extra']['kwargs']['message_id']) == payload.message_id:
                    role = guild.get_role(record['extra']['kwargs']['role_id'])
                    return await member.remove_roles(role)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """ For when Members join the guild. """
        if member.guild.id == SPTV_GUILD_ID:
            await member.guild.system_channel.send(
                f"Hey {member.mention} 👋. Welcome to **Specialist's Discord Server**."
                " Please take the time to read the <#690570977381318736> channel and"
                " feel free to chat to us and introduce yourself in <#690566308269391953>."
                " GL & HF!")
            role = member.guild.get_role(691298204918087691)
            await member.add_roles(role, reason="New member!", atomic=True)


def setup(bot):
    """ Cog setup time. """
    bot.add_cog(Specialist(bot))
