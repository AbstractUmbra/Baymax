import discord
from discord.ext import commands

from utils import db


class WelcomeTable(db.Table, table_name="welcome_config"):
    guild_id = db.Column(db.Integer(big=True), index=False,
                         primary_key=True)
    welcome_channel = db.Column(db.Integer(big=True))
    welcome_message = db.Column(db.String)


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """ On member joins... let's check for a welcome message. """
        query = "SELECT * FROM welcome_config WHERE guild_id = $1"
        results = await self.bot.pool.fetchrow(query, member.guild.id)
        if not results:
            return
        channel = member.guild.get_channel(results['welcome_channel'])
        return await channel.send(f"Hey {member.mention}\n\n{results['welcome_message']}")

    @commands.group(name="welcome", invoke_without_command=True)
    async def welcome_group(self, ctx, channel: discord.TextChannel, *, message: str):
        """ Group. If no subcommand then create a welcome message. """
        if ctx.invoked_subcommand:
            pass
        channel = channel or ctx.channel
        query = """INSERT INTO welcome_config (guild_id, welcome_channel, welcome_message)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (guild_id)
                   DO UPDATE SET welcome_channel = $2, welcome_message = $3
                """
        await self.bot.pool.execute(query, ctx.guild.id, channel.id, message)
        return await ctx.send(f"Done. Set up welcome messages in {channel.mention}.")

    @welcome_group.command(name="remove", aliases=["clear", "prune"])
    async def welcome_remove(self, ctx):
        """ Command. Let's remove their welcome messages. """
        query = "DELETE FROM welcome_config WHERE guild_id = $1"
        await self.bot.pool.execute(query, ctx.guild.id)
        return await ctx.message.add_reaction("<:TickYes:672157420574736386>")

    @welcome_group.command(name="query")
    async def welcome_query(self, ctx):
        """ Command. Let's have a look at your active help message. """
        query = "SELECT * FROM welcome_config WHERE guild_id = $1"
        record = await self.bot.pool.fetchrow(query, ctx.guild.id)
        channel = ctx.guild.get_channel(record['welcome_channel'])
        if not channel:
            return await ctx.send("It seems the welcome channel has been deleted.")
        return await ctx.send(f"Message is being sent to {channel.mention}. Message is:\n\n{record['welcome_message']}")

    @commands.command()
    async def iexist(self, ctx):
        return await ctx.send("https://www.youtube.com/watch?v=h0QqXurjzD8")


def setup(bot):
    bot.add_cog(Welcome(bot))
