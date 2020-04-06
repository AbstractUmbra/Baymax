""" Mick's quick stuffs. """
import datetime
import random
import textwrap

import discord
from discord.ext import commands

from utils import time, specialist


class Specialist(commands.Cog):
    """ Class designed for SpecialistTV channel. """

    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)

    @commands.group(aliases=['event', 'Event'])
    async def events(self, ctx):
        if not ctx.invoked_subcommand:
            return await ctx.send("This command requires a subcommand.")

    @events.command(aliases=['bfme', 'BFME', 'BFME2'], usage="<when>", invoke_without_command=True)
    async def bfme2(self, ctx, *, when: time.UserFriendlyTime(commands.clean_content, default="\u2026")):
        reminder = self.bot.get_cog("Reminder")
        if not reminder:
            return await ctx.send("Sorry, this functionality is currently unavailable.")
        message = await ctx.send("Placeholder")
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        timer = await reminder.create_timer(event_trigger, 'bfme2', ctx.author.id,
                                            ctx.channel.id,
                                            when.arg,
                                            connection=ctx.db,
                                            created=ctx.message.created_at,
                                            message_id=message.id)
        await reminder.create_timer(cancellation_trigger, 'event_check', ctx.author.id,
                                    ctx.channel.id,
                                    when.arg,
                                    connection=ctx.db,
                                    created=ctx.message.created_at,
                                    message_id=message.id)
        delta = time.human_timedelta(when.dt, source=timer.created_at)
        embed = discord.Embed(title="BFME2 Event Prep!",
                              colour=discord.Colour.gold())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Plan of action", value=f"{when.arg}")
        embed.add_field(
            name="When", value=f"{delta} | {when.dt.strftime('%d-%m-%Y %H:%M')}")
        embed.description = "Add a reaction to this post to join this event!"
        await message.edit(content="", embed=embed)
        return await ctx.message.delete()

    @events.command(aliases=['aoe', 'AOE', 'AOE2'], usage="<when>", invoke_without_command=True)
    async def aoe2(self, ctx, *, when: time.UserFriendlyTime(commands.clean_content, default="\u2026")):
        reminder = self.bot.get_cog("Reminder")
        if not reminder:
            return await ctx.send("Sorry, this functionality is currently unavailable.")
        message = await ctx.send("Placeholder")
        event_trigger = when.dt - datetime.timedelta(minutes=15)
        cancellation_trigger = when.dt - datetime.timedelta(hours=2)
        timer = await reminder.create_timer(event_trigger, 'aoe2', ctx.author.id,
                                            ctx.channel.id,
                                            when.arg,
                                            connection=ctx.db,
                                            created=ctx.message.created_at,
                                            message_id=message.id)
        await reminder.create_timer(cancellation_trigger, 'event_check', ctx.author.id,
                                    ctx.channel.id,
                                    when.arg,
                                    connection=ctx.db,
                                    created=ctx.message.created_at,
                                    message_id=message.id)
        delta = time.human_timedelta(when.dt, source=timer.created_at)
        embed = discord.Embed(title="AOE2 Event Prep!",
                              colour=discord.Colour.red())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Plan of action", value=f"{when.arg}")
        embed.add_field(
            name="When", value=f"{delta} | {when.dt.strftime('%d-%m-%Y %H:%M')}")
        embed.description = "Add a reaction to this post to join this event!"
        await message.edit(content="", embed=embed)
        return await ctx.message.delete()

    @events.command(name="list")
    async def events_list(self, ctx):
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

    @events.command(name="delete")
    async def events_delete(self, ctx, id: int):
        query = """DELETE FROM reminders
                   WHERE id = $1
                   AND extra #>> '{args,0}
                """
        status = await ctx.db.execute(query, str(ctx.author.id))
        if status = "DELETE 0":
            return await ctx.send("Could not delete event by that ID. Are you sure it's there and you're it's author?")
        return await ctx.send("Deleted event.")

    @commands.Cog.listener()
    async def on_event_check_timer_complete(self, event):
        author_id, channel_id, message = event.args

        try:
            channel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        guild_ = channel.guild.id if isinstance(
            channel, discord.TextChannel) else "@me"
        message_id = event.kwargs.get("message_id")
        prev_message = await channel.fetch_message(message_id)
        reacted_list = []
        for reaction in prev_message.reactions:
            reaction_flat = await reaction.users().flatten()
            for member in reaction_flat:
                if member.bot:
                    continue
                reacted_list.append(member)
        members = set([member.id for member in reacted_list])
        if len(members) < 3:
            await prev_message.delete()
            return await channel.send(f"The event for ***{message}*** has been cancelled due to lack of members!")

    @commands.Cog.listener()
    async def on_bfme_timer_complete(self, event):
        author_id, channel_id, message = event.args

        try:
            channel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            return

        guild_id = channel.guild.id if isinstance(
            channel, discord.TextChannel) else '@me'
        message_id = event.kwargs.get('message_id')
        prev_message = await channel.fetch_message(message_id)
        reacted_list = []
        for reaction in prev_message.reactions:
            reaction_flat = await reaction.users().flatten()
            for member in reaction_flat:
                if member.bot:
                    continue
                reacted_list.append(member)
        members = set([member.display_name for member in reacted_list])
        role = channel.guild.get_role(696496787447611412)
        embed = discord.Embed(title="**BFME 2 Event time**",
                              colour=discord.Colour.gold())
        event_author = channel.guild.get_member(author_id)
        embed.set_author(name=event_author.display_name,
                         icon_url=event_author.avatar_url)
        embed.set_image(
            url="https://download.hipwallpaper.com/desktop/1920/1080/66/33/HBOjoz.jpg")
        embed.add_field(name="Members that signed up",
                        value=", ".join(members))
        embed.description(random.choice(specialist.LOTR_QUOTES))
        await channel.send(role.mention, embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """ For when Member's join the guild. """
        if member.guild.id == 690566307409821697:
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
