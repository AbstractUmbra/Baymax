""" Todos cog! """
import datetime
import typing

import asyncpg
import discord
from discord.ext import commands, menus

from utils import db

class TodoTable(db.Table, table_name="todos"):
    id = db.PrimaryKeyColumn()

    owner_id = db.Column(db.Integer(big=True))
    content = db.Column(db.String)
    added_at = db.Column(db.Datetime)
    jump_url = db.Column(db.String)

class TodoPageSource(menus.ListPageSource):
    def __init__(self, data, embeds):
        self.data = data
        self.embeds = embeds
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        return self.embeds[entries]

class Todo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _gen_todos(self, records: typing.List[asyncpg.Record]) -> typing.List[discord.Embed]:
        descs = []
        list_of_records = [records[x:x+10] for x in range(0, len(records), 10)]
        for records in list_of_records:
            descs.append(discord.Embed(description="\n".join([f"[__`{record['id']}`__]({record['jump_url']}): {record['content']}" for record in records])))
        return descs

    @commands.group(invoke_without_command=True)
    async def todo(self, ctx, *, content: str = None):
        """ Todos! See the subcommands for more info. """
        if not ctx.invoked_subcommand:
            if not content:
                return await ctx.send_help(ctx.command)
            else:
                return await self.todo_add(ctx, content=content)


    @todo.command(name="list", cooldown_after_parsing=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def todo_list(self, ctx):
        """ A list of todos for you. """
        query  = """ SELECT * FROM todos WHERE owner_id = $1 LIMIT 100; """
        records = await self.bot.pool.fetch(query, ctx.author.id)

        if not records:
            return await ctx.send("You appear to have no active todos, look at how productive you are.")
        embeds = self._gen_todos(records) ##TODO monitor for errors?
        pages = menus.MenuPages(source=TodoPageSource(range(0, len(embeds)), embeds), delete_message_after=True)
        await pages.start(ctx)


    @commands.command(name="todos")
    async def alt_todo_list(self, ctx):
        return await self.todo_list(ctx)

    @todo.command(name="add")
    async def todo_add(self, ctx, *, content):
        """ Add me something to do later... """
        query = """ INSERT INTO todos (owner_id, content, added_at, jump_url) VALUES ($1, $2, $3, $4) RETURNING id; """
        succeed = await self.bot.pool.fetchrow(query, ctx.author.id, content, datetime.datetime.utcnow(), ctx.message.jump_url)
        if succeed['id']:
            return await ctx.send(f"{self.bot.emoji[True]}: created todo #__`{succeed['id']}`__ for you!", delete_after=3)

    @todo.command(name="delete", aliases=["remove", "Delete", "Remove", "bin"])
    async def todo_delete(self, ctx, todo_id: int):
        """ Delete my todo thanks, since I did it already. """
        query = """ DELETE FROM todos WHERE owner_id = $1 AND id = $2 RETURNING id; """
        success = await self.bot.pool.fetchrow(query, ctx.author.id, todo_id)
        if success['id']:
            return await ctx.send(f"Okay well done. I deleted todo #__`{success['id']}`__ for you.", delete_after=3)

    @todo.command(name="edit")
    async def todo_edit(self, ctx, todo_id: int, *, content):
        """ Edit my todo because I would like to change the wording or something. """
        owner_check = """ SELECT id, owner_id FROM todos WHERE owner_id = $1 AND id = $2; """
        owner = await self.bot.pool.fetchrow(owner_check, ctx.author.id, todo_id)
        if not owner or owner['owner_id'] != ctx.author.id:
            return await ctx.send("That doesn't seem to be your todo, or the ID is incorrect.")
        update_query = """ UPDATE todos SET content = $2, jump_url = $3 WHERE id = $1 RETURNING id; """
        success = await self.bot.pool.fetchrow(update_query, todo_id, content, ctx.message.jump_url)
        if success:
            return await ctx.send(f"Neat. So todo #__`{success['id']}`__ has been updated for you. Go be productive!", delete_after=3)

    @todo.command(name="info")
    async def todo_info(self, ctx, todo_id: int):
        """ Get a little extra info... """
        query = """ SELECT * FROM todos WHERE owner_id = $1 AND id = $2; """
        record = await self.bot.pool.fetchrow(query, ctx.author.id, todo_id)
        if not record:
            return await ctx.send("No record for by you with that ID. Is it correct?")
        embed = discord.Embed(title="Extra todo info")
        embed.description = f"{record['content']}\n[Message link!]({record['jump_url']})"
        embed.timestamp = record['added_at']
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        return await ctx.send(embed=embed)


    @todo.command(name="clear")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def todo_clear(self, ctx):
        """ Lets wipe 'em all! """
        query = """ DELETE FROM todos WHERE owner_id = $1; """
        confirm = await ctx.prompt("This will wipe your todos from my memory. Are you sure?")
        if not confirm:
            return
        await self.bot.pool.execute(query, ctx.author.id)
        return await ctx.message.add_reaction(self.bot.emoji[True])

    @todo_list.error
    @todo_clear.error
    async def todo_errors(self, ctx, error):
        """ Error handler for specific shit. """
        error = getattr(error, "original", error)
        if isinstance(error, commands.MaxConcurrencyReached):
            return await ctx.send("Whoa, I know you're eager but close your active list first!")
        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f"Goodness, didn't you just view try this? Try again in {error.retry_after:.2f} seconds.")

def setup(bot):
    bot.add_cog(Todo(bot))
