"""
The MIT License (MIT)

Copyright (c) 2020 AbstractUmbra

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import asyncio
import datetime
import random
import string
import textwrap

import discord
from discord.ext import commands

from utils import checks, specialist, time

SPTV_GUILD_ID = 690566307409821697


class Specialist(commands.Cog):
    """ Class designed for SpecialistTV channel. """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.image_urls = {
            "dow3": "https://i.imgur.com/kYGODxo.jpg",
            "swtor": "https://i.imgur.com/0wjY56D.png",
            "gtfo": "https://www.mkaugaming.com/wp-content/uploads/2020/03/2020-03-19_00078.jpg",
            "bfme2": "https://download.hipwallpaper.com/desktop/1920/1080/66/33/HBOjoz.jpg",
            "aoe2": "https://news.xbox.com/en-us/wp-content/uploads/sites/2/HERO-35.jpg?fit=1920%2C1080",
            "bf2": "https://media.contentapi.ea.com/content/dam/star-wars-battlefront-2/images/2020/02/featured-ajankloss-action.jpg.adapt.crop191x100.628p.jpg",
            "coh2": "https://hb.imgix.net/3d9954a268d7c9e03a5715e7a3d58a53ba823274.jpg?auto=compress,format&fit=crop&h=353&w=616&s=fc9540e6803dba1bb5fa1d14fafeacfa",
            "ih": "https://i.ytimg.com/vi/KRkrF4TUHmQ/maxresdefault.jpg"}

    def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.guild:
            return ctx.guild.id == 690566307409821697
        return False

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

    @commands.group(aliases=['Event'], hidden=True)
    @checks.mod_or_permissions(manage_message=True)
    async def event(self, ctx: commands.Context):
        """ Primary command for events. """
        if not ctx.invoked_subcommand:
            return await ctx.send("This command requires a subcommand.")

    @commands.command(name="events")
    @checks.mick_and_me()
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
        when.dt = when.dt - datetime.timedelta(hours=1)
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        role_str = "".join(random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5))
        role = await ctx.guild.create_role(name=f"BFME2-{role_str}", colour=discord.Colour(0xcbe029),
                                           reason="Event creation.", mentionable=False)
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
        embed.set_author(name=ctx.guild.owner.name,
                         icon_url=ctx.guild.owner.avatar_url)
        embed.set_thumbnail(url=ctx.author.avatar_url)
        embed.set_image(
            url=self.image_urls['bfme2'])
        embed.add_field(name="Plan of action",
                        value=f"{when.arg}", inline=False)
        embed.add_field(
            name="When", value=f"{(when.dt + datetime.timedelta(hours=1)).strftime('%d-%m-%Y %H:%M')}", inline=True)
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
        when.dt = when.dt - datetime.timedelta(hours=1)
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        role_str = "".join(random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5))
        role = await ctx.guild.create_role(name=f"AOE2-{role_str}", colour=discord.Colour(0xcbe029),
                                           reason="Event creation.", mentionable=False)
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
        embed.set_image(
            url=self.image_urls['aoe2'])
        embed.set_author(name=ctx.guild.owner.name,
                         icon_url=ctx.guild.owner.avatar_url)
        embed.add_field(name="Plan of action", value=f"{when.arg}")
        embed.add_field(
            name="When", value=f"{(when.dt + datetime.timedelta(hours=1)).strftime('%d-%m-%Y %H:%M')}")
        embed.description = "Add a reaction to this post to join this event!"
        await message.edit(content="", embed=embed)
        return await ctx.message.delete()

    @event.command(aliases=['bf', 'BF2', 'BF'], usage="<when>", invoke_without_command=True)
    async def bf2(self, ctx: commands.Context, *, when: time.UserFriendlyTime(commands.clean_content, default="\u2026")):
        """ Create an AOE2 event. """
        reminder = self.bot.get_cog("Reminder")
        if not reminder:
            return await ctx.send("Sorry, this functionality is currently unavailable.")
        message = await ctx.send("Placeholder")
        when.dt = when.dt - datetime.timedelta(hours=1)
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        role_str = "".join(random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5))
        role = await ctx.guild.create_role(name=f"BF2-{role_str}", colour=discord.Colour(0xcbe029),
                                           reason="Event creation.", mentionable=False)
        await reminder.create_timer(event_trigger, 'bf2', ctx.author.id,
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
        embed = discord.Embed(title="BF2 Event Prep!",
                              colour=discord.Colour.red())
        embed.set_image(
            url=self.image_urls['bf2'])
        embed.set_author(name=ctx.guild.owner.name,
                         icon_url=ctx.guild.owner.avatar_url)
        embed.add_field(name="Plan of action", value=f"{when.arg}")
        embed.add_field(
            name="When", value=f"{(when.dt + datetime.timedelta(hours=1)).strftime('%d-%m-%Y %H:%M')}")
        embed.description = "Add a reaction to this post to join this event!"
        await message.edit(content="", embed=embed)
        return await ctx.message.delete()

    @event.command(aliases=['coh', 'COH', 'COH2'], usage="<when>", invoke_without_command=True)
    async def coh2(self, ctx: commands.Context, *, when: time.UserFriendlyTime(commands.clean_content, default="\u2026")):
        """ Create a COH2 event. """
        reminder = self.bot.get_cog("Reminder")
        if not reminder:
            return await ctx.send("Sorry, this functionality is currently unavailable.")
        message = await ctx.send("Placeholder")
        when.dt = when.dt - datetime.timedelta(hours=1)
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        role_str = "".join(random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5))
        role = await ctx.guild.create_role(name=f"COH2-{role_str}", colour=discord.Colour(0xcbe029),
                                           reason="Event creation.", mentionable=False)
        await reminder.create_timer(event_trigger, 'coh2', ctx.author.id,
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
        embed = discord.Embed(title="COH2 Event Prep!",
                              colour=discord.Colour.red())
        embed.set_image(
            url=self.image_urls['coh2'])
        embed.set_author(name=ctx.guild.owner.name,
                         icon_url=ctx.guild.owner.avatar_url)
        embed.add_field(name="Plan of action", value=f"{when.arg}")
        embed.add_field(
            name="When", value=f"{(when.dt + datetime.timedelta(hours=1)).strftime('%d-%m-%Y %H:%M')}")
        embed.description = "Add a reaction to this post to join this event!"
        await message.edit(content="", embed=embed)
        return await ctx.message.delete()

    @event.command(aliases=['SWTOR'], usage="<when>", invoke_without_command=True)
    async def swtor(self, ctx: commands.Context, *, when: time.UserFriendlyTime(commands.clean_content, default="\u2026")):
        """ Create a SWTOR event. """
        reminder = self.bot.get_cog("Reminder")
        if not reminder:
            return await ctx.send("Sorry, this functionality is currently unavailable.")
        message = await ctx.send("Placeholder")
        when.dt = when.dt - datetime.timedelta(hours=1)
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        role_str = "".join(random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5))
        role = await ctx.guild.create_role(name=f"SWTOR-{role_str}", colour=discord.Colour(0xcbe029),
                                           reason="Event creation.", mentionable=False)
        await reminder.create_timer(event_trigger, 'swtor', ctx.author.id,
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
        embed = discord.Embed(title="SWTOR Event Prep!",
                              colour=discord.Colour.red())
        embed.set_image(
            url=self.image_urls['swtor'])
        embed.set_author(name=ctx.guild.owner.name,
                         icon_url=ctx.guild.owner.avatar_url)
        embed.add_field(name="Plan of action", value=f"{when.arg}")
        embed.add_field(
            name="When", value=f"{(when.dt + datetime.timedelta(hours=1)).strftime('%d-%m-%Y %H:%M')}")
        embed.description = "Add a reaction to this post to join this event!"
        await message.edit(content="", embed=embed)
        return await ctx.message.delete()

    @event.command(aliases=['GTFO'], usage="<when>", invoke_without_command=True)
    async def gtfo(self, ctx: commands.Context, *, when: time.UserFriendlyTime(commands.clean_content, default="\u2026")):
        """ Create a GTFO event. """
        reminder = self.bot.get_cog("Reminder")
        if not reminder:
            return await ctx.send("Sorry, this functionality is currently unavailable.")
        message = await ctx.send("Placeholder")
        when.dt = when.dt - datetime.timedelta(hours=1)
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        role_str = "".join(random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5))
        role = await ctx.guild.create_role(name=f"GTFO-{role_str}", colour=discord.Colour(0xcbe029),
                                           reason="Event creation.", mentionable=False)
        await reminder.create_timer(event_trigger, 'gtfo', ctx.author.id,
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
        embed = discord.Embed(title="GTFO Event Prep!",
                              colour=discord.Colour.red())
        embed.set_image(
            url=self.image_urls['gtfo'])
        embed.set_author(name=ctx.guild.owner.name,
                         icon_url=ctx.guild.owner.avatar_url)
        embed.add_field(name="Plan of action", value=f"{when.arg}")
        embed.add_field(
            name="When", value=f"{(when.dt + datetime.timedelta(hours=1)).strftime('%d-%m-%Y %H:%M')}")
        embed.description = "Add a reaction to this post to join this event!"
        await message.edit(content="", embed=embed)
        return await ctx.message.delete()

    @event.command(aliases=['DOW3'], usage="<when>", invoke_without_command=True)
    async def dow3(self, ctx: commands.Context, *, when: time.UserFriendlyTime(commands.clean_content, default="\u2026")):
        """ Create a GTFO event. """
        reminder = self.bot.get_cog("Reminder")
        if not reminder:
            return await ctx.send("Sorry, this functionality is currently unavailable.")
        message = await ctx.send("Placeholder")
        when.dt = when.dt - datetime.timedelta(hours=1)
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        role_str = "".join(random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5))
        role = await ctx.guild.create_role(name=f"DOW3-{role_str}", colour=discord.Colour(0xcbe029),
                                           reason="Event creation.", mentionable=False)
        await reminder.create_timer(event_trigger, 'dow3', ctx.author.id,
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
        embed = discord.Embed(title="DOW3 Event Prep!",
                              colour=discord.Colour.red())
        embed.set_image(
            url=self.image_urls['dow3'])
        embed.set_author(name=ctx.guild.owner.name,
                         icon_url=ctx.guild.owner.avatar_url)
        embed.add_field(name="Plan of action", value=f"{when.arg}")
        embed.add_field(
            name="When", value=f"{(when.dt + datetime.timedelta(hours=1)).strftime('%d-%m-%Y %H:%M')}")
        embed.description = "Add a reaction to this post to join this event!"
        await message.edit(content="", embed=embed)
        return await ctx.message.delete()

    @event.command(aliases=['ih', 'IH', 'ironharvest'], usage="<when>", invoke_without_command=True)
    async def iron_harvest(self, ctx: commands.Context, *, when: time.UserFriendlyTime(commands.clean_content, default="\u2026")):
        """ Create an Iron Harvest event. """
        reminder = self.bot.get_cog("Reminder")
        if not reminder:
            return await ctx.send("Sorry, this functionality is currently unavailable.")
        message = await ctx.send("Placeholder")
        when.dt = when.dt - datetime.timedelta(hours=1)
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        role_str = "".join(random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5))
        role = await ctx.guild.create_role(name=f"IH-{role_str}", colour=discord.Colour(0xcbe029),
                                           reason="Event creation.", mentionable=False)
        await reminder.create_timer(event_trigger, 'ih', ctx.author.id,
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
        embed = discord.Embed(title="Iron Harvest Event Prep!",
                              colour=discord.Colour.red())
        embed.set_image(
            url=self.image_urls['ih'])
        embed.set_author(name=ctx.guild.owner.name,
                         icon_url=ctx.guild.owner.avatar_url)
        embed.add_field(name="Plan of action", value=f"{when.arg}")
        embed.add_field(
            name="When", value=f"{(when.dt + datetime.timedelta(hours=1)).strftime('%d-%m-%Y %H:%M')}")
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
                   OR event = 'bf2'
                   OR event = 'coh2'
                   OR event = 'swtor'
                   OR event = 'gtfo'
                   OR event = 'dow3'
                   OR event = 'ih'
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
            role = channel.guild.get_role(record['extra']['kwargs']['role_id'])
            await role.delete()
        await message.delete()
        return await ctx.send("Deleted event.")

    # @commands.Cog.listener()
    # async def on_event_check_timer_complete(self, event):
    #     """ On 'event_check' complete. """
    #     _, channel_id, message = event.args

    #     try:
    #         channel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
    #     except discord.HTTPException:
    #         return

    #     message_id = event.kwargs.get("message_id")
    #     prev_message = await channel.fetch_message(int(message_id))
    #     reacted_list = await self.get_reacts(prev_message.reactions)
    #     members = {member.id for member in reacted_list}
    #     if len(members) < 3:
    #         await prev_message.clear_reactions()
    #         del_query = """DELETE FROM reminders
    #                     WHERE extra #>> '{kwargs,message_id}' = $1;
    #                     """
    #         await self.bot.pool.execute(del_query, str(event.kwargs['message_id']))
    #         return await prev_message.delete()

    @commands.Cog.listener()
    async def on_bfme2_timer_complete(self, event):
        """ On 'bfme2' timer complete. """
        author_id, channel_id, message = event.args

        try:
            channel: discord.TextChannel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        message_id: int = event.kwargs.get('message_id')
        prev_message: discord.Message = await channel.fetch_message(int(message_id))
        role: discord.Role = channel.guild.get_role(event.kwargs.get('role_id'))
        await role.edit(mentionable=True)
        reacted_list: list = await self.get_reacts(prev_message.reactions)
        member_names: set = {member.display_name for member in reacted_list}
        embed: discord.Embed = discord.Embed(title="**BFME 2 Event time**",
                              colour=discord.Colour.gold())
        event_author: discord.Member = channel.guild.get_member(author_id)
        embed.set_author(name=event_author.display_name,
                         icon_url=event_author.avatar_url)
        embed.set_image(
            url=self.image_urls['bfme2'])
        if member_names:
            embed.add_field(name="Members that signed up",
                            value=", ".join(member_names))
        embed.add_field(name="Plan of action",
                        value=f"{message}")
        embed.description = random.choice(specialist.LOTR_QUOTES)
        current_message: discord.Message = await channel.send(role.mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        await prev_message.delete()
        await asyncio.sleep(60)
        await role.delete()
        return await current_message.delete(delay=900)

    @commands.Cog.listener()
    async def on_aoe2_timer_complete(self, event):
        """ On 'aoe2' event timer complete. """
        author_id, channel_id, message = event.args

        try:
            channel: discord.TextChannel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        message_id: int = event.kwargs.get('message_id')
        prev_message: discord.Message = await channel.fetch_message(message_id)
        role: discord.Role = channel.guild.get_role(event.kwargs.get('role_id'))
        await role.edit(mentionable=True)
        reacted_list: list = await self.get_reacts(prev_message.reactions)
        member_names: set = set([member.display_name for member in reacted_list])
        embed: discord.Embed = discord.Embed(title="**AOE 2 Event time**",
                              colour=discord.Colour.red())
        event_author: discord.Member = channel.guild.get_member(author_id)
        embed.set_author(name=event_author.display_name,
                         icon_url=event_author.avatar_url)
        embed.set_image(
            url=self.image_urls['aoe2'])
        if member_names:
            embed.add_field(name="Members that signed up",
                            value=", ".join(member_names))
        embed.add_field(name="Plan of action",
                        value=f"{message}")
        embed.description = random.choice(specialist.AOE_QUOTES)
        current_message: discord.Message = await channel.send(role.mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        await prev_message.delete()
        await asyncio.sleep(60)
        await role.delete()
        return await current_message.delete(delay=900)

    @commands.Cog.listener()
    async def on_bf2_timer_complete(self, event):
        """ On 'bf2' event timer complete. """
        author_id, channel_id, message = event.args

        try:
            channel: discord.TextChannel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        message_id: int = event.kwargs.get('message_id')
        prev_message: discord.Message = await channel.fetch_message(message_id)
        role: discord.Role = channel.guild.get_role(event.kwargs.get('role_id'))
        await role.edit(mentionable=True)
        reacted_list: list = await self.get_reacts(prev_message.reactions)
        member_names: set = set([member.display_name for member in reacted_list])
        embed: discord.Embed = discord.Embed(title="**BF2 Event time**",
                              colour=discord.Colour.red())
        event_author: discord.Member = channel.guild.get_member(author_id)
        embed.set_author(name=event_author.display_name,
                         icon_url=event_author.avatar_url)
        embed.set_image(
            url=self.image_urls['bf2'])
        if member_names:
            embed.add_field(name="Members that signed up",
                            value=", ".join(member_names))
        embed.add_field(name="Plan of action",
                        value=f"{message}")
        embed.description = random.choice(specialist.BF2_QUOTES)
        current_message: discord.Message = await channel.send(role.mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        await prev_message.delete()
        await asyncio.sleep(60)
        await role.delete()
        return await current_message.delete(delay=900)

    @commands.Cog.listener()
    async def on_coh2_timer_complete(self, event):
        """ On 'aoe2' event timer complete. """
        author_id, channel_id, message = event.args

        try:
            channel: discord.TextChannel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        message_id: int = event.kwargs.get('message_id')
        prev_message: discord.Message = await channel.fetch_message(message_id)
        role: discord.Role = channel.guild.get_role(event.kwargs.get('role_id'))
        await role.edit(mentionable=True)
        reacted_list: list = await self.get_reacts(prev_message.reactions)
        member_names: set = set([member.display_name for member in reacted_list])
        embed: discord.Embed = discord.Embed(title="**COH 2 Event time**",
                              colour=discord.Colour.red())
        event_author: discord.Member = channel.guild.get_member(author_id)
        embed.set_author(name=event_author.display_name,
                         icon_url=event_author.avatar_url)
        embed.set_image(
            url=self.image_urls['coh2'])
        if member_names:
            embed.add_field(name="Members that signed up",
                            value=", ".join(member_names))
        embed.add_field(name="Plan of action",
                        value=f"{message}")
        embed.description = random.choice(specialist.COH2_QUOTES)
        current_message: discord.Message = await channel.send(role.mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        await prev_message.delete()
        await asyncio.sleep(60)
        await role.delete()
        return await current_message.delete(delay=900)

    @commands.Cog.listener()
    async def on_swtor_timer_complete(self, event):
        """ On 'swtor' event timer complete. """
        author_id, channel_id, message = event.args

        try:
            channel: discord.TextChannel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        message_id: int = event.kwargs.get('message_id')
        prev_message: discord.Message = await channel.fetch_message(message_id)
        role: discord.Role = channel.guild.get_role(event.kwargs.get('role_id'))
        await role.edit(mentionable=True)
        reacted_list: list = await self.get_reacts(prev_message.reactions)
        member_names: set = set([member.display_name for member in reacted_list])
        embed = discord.Embed(title="**SWTOR Event time**",
                              colour=discord.Colour.red())
        event_author: discord.Member = channel.guild.get_member(author_id)
        embed.set_author(name=event_author.display_name,
                         icon_url=event_author.avatar_url)
        embed.set_image(
            url=self.image_urls['swtor'])
        if member_names:
            embed.add_field(name="Members that signed up",
                            value=", ".join(member_names))
        embed.add_field(name="Plan of action",
                        value=f"{message}")
        embed.description = random.choice(specialist.SWTOR_QUOTES)
        current_message: discord.Message = await channel.send(role.mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        await prev_message.delete()
        await asyncio.sleep(60)
        await role.delete()
        return await current_message.delete(delay=900)

    @commands.Cog.listener()
    async def on_gtfo_timer_complete(self, event):
        """ On 'swtor' event timer complete. """
        author_id, channel_id, message = event.args

        try:
            channel: discord.TextChannel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        message_id: int = event.kwargs.get('message_id')
        prev_message: discord.Message = await channel.fetch_message(message_id)
        role: discord.Role = channel.guild.get_role(event.kwargs.get('role_id'))
        await role.edit(mentionable=True)
        reacted_list: list = await self.get_reacts(prev_message.reactions)
        member_names: set = set([member.display_name for member in reacted_list])
        embed: discord.Embed = discord.Embed(title="**GTFO Event time**",
                              colour=discord.Colour.red())
        event_author: discord.Member = channel.guild.get_member(author_id)
        embed.set_author(name=event_author.display_name,
                         icon_url=event_author.avatar_url)
        embed.set_image(
            url="https://www.mkaugaming.com/wp-content/uploads/2020/03/2020-03-19_00078.jpg")
        if member_names:
            embed.add_field(name="Members that signed up",
                            value=", ".join(member_names))
        embed.add_field(name="Plan of action",
                        value=f"{message}")
        current_message: discord.Message = await channel.send(role.mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        await prev_message.delete()
        await asyncio.sleep(60)
        await role.delete()
        return await current_message.delete(delay=900)

    @commands.Cog.listener()
    async def on_dow3_timer_complete(self, event):
        """ On 'dow3' event timer complete. """
        author_id, channel_id, message = event.args

        try:
            channel: discord.TextChannel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        message_id: int = event.kwargs.get('message_id')
        prev_message: discord.Message = await channel.fetch_message(message_id)
        role: discord.Role = channel.guild.get_role(event.kwargs.get('role_id'))
        await role.edit(mentionable=True)
        reacted_list: list = await self.get_reacts(prev_message.reactions)
        member_names: set = set([member.display_name for member in reacted_list])
        embed: discord.Embed = discord.Embed(title="**DOW3 Event time**",
                              colour=discord.Colour.red())
        event_author: discord.Member = channel.guild.get_member(author_id)
        embed.set_author(name=event_author.display_name,
                         icon_url=event_author.avatar_url)
        embed.set_image(
            url=self.image_urls['dow3'])
        if member_names:
            embed.add_field(name="Members that signed up",
                            value=", ".join(member_names))
        embed.add_field(name="Plan of action",
                        value=f"{message}")
        current_message: discord.Message = await channel.send(role.mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        await prev_message.delete()
        await asyncio.sleep(60)
        await role.delete()
        return await current_message.delete(delay=900)

    @commands.Cog.listener()
    async def on_ih_timer_complete(self, event):
        """ On 'dow3' event timer complete. """
        author_id, channel_id, message = event.args

        try:
            channel: discord.TextChannel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        message_id: int = event.kwargs.get('message_id')
        prev_message: discord.Message = await channel.fetch_message(message_id)
        role: discord.Role = channel.guild.get_role(event.kwargs.get('role_id'))
        await role.edit(mentionable=True)
        reacted_list: list = await self.get_reacts(prev_message.reactions)
        member_names: set = set([member.display_name for member in reacted_list])
        embed: discord.Embed = discord.Embed(title="**Iron Harvest Event time**",
                              colour=discord.Colour.red())
        event_author: discord.Member = channel.guild.get_member(author_id)
        embed.set_author(name=event_author.display_name,
                         icon_url=event_author.avatar_url)
        embed.set_image(
            url=self.image_urls['ih'])
        if member_names:
            embed.add_field(name="Members that signed up",
                            value=", ".join(member_names))
        embed.add_field(name="Plan of action",
                        value=f"{message}")
        current_message: discord.Message = await channel.send(role.mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        await prev_message.delete()
        await asyncio.sleep(60)
        await role.delete()
        return await current_message.delete(delay=900)

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
                   OR event = 'bf2'
                   OR event = 'coh2'
                   OR event = 'swtor'
                   OR event = 'gtfo'
                   OR event = 'dow3'
                   OR event = 'ih'
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
                   OR event = 'bf2'
                   OR event = 'coh2'
                   OR event = 'swtor'
                   OR event = 'gtfo'
                   OR event = 'dow3'
                   OR event = 'ih'
                """
        records = await self.bot.pool.fetch(query)
        for record in records:
            if int(record['extra']['args'][1]) == payload.channel_id:
                if int(record['extra']['kwargs']['message_id']) == payload.message_id:
                    role = guild.get_role(record['extra']['kwargs']['role_id'])
                    return await member.remove_roles(role)


def setup(bot):
    """ Cog setup time. """
    bot.add_cog(Specialist(bot))
