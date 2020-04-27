""" Token parser """
import asyncio
import base64

import discord
from discord.ext import commands

from utils import checks


class TokenWorks(commands.Cog):
    """ This is for when silly people reveal their token. """

    def __init__(self, bot):
        self.bot = bot

    async def decode_tok(self, token: str) -> int:
        """ base 64 decode handler. """
        token_id = int(base64.b64decode(token))
        return token_id

    @commands.group()
    @checks.has_guild_permissions(manage_roles=True)
    async def token(self, ctx):
        """ Token primary command. """
        if not ctx.invoked_subcommand:
            return

    @token.command(name="i")
    async def token_info(self, ctx, *, _token: str):
        """ Use the token to get the information on the bot. """
        try:
            decoded_token = await self.decode_tok(_token.split(".")[0])
        except ValueError:
            return await ctx.send("This can't be decoded. Is it a valid token?")
        token_user = await self.bot.fetch_user(decoded_token)
        if not token_user:
            return await ctx.send("User ID doesn't work, sadly.")
        time = token_user.created_at.strftime("%d-%m-%Y %H:%M:%S")
        embed = discord.Embed(
            description=f"""
                            **Username**: `{token_user.name}`
                            **ID**: `{decoded_token}`
                            **Existed since**: `{time}`
                            **Bot**: `{token_user.bot}`
                        """)
        embed.set_thumbnail(url=token_user.avatar_url)
        client_info = InfoClient(loop=asyncio.get_event_loop())
        try:
            await client_info.start(_token)
        except (discord.LoginFailure, discord.ConnectionClosed, discord.HTTPException):
            await ctx.send(embed=embed)
            return token_user
        embed.add_field(name="Owner", value=f"{client_info.owner}")
        if client_info.team:
            team_list = [str(member) for member in client_info.team]
            embed.add_field(name="Owner", value="\n".join(team_list))
        await ctx.send(embed=embed)
        return token_user

    @token.command(name="w")
    async def token_warn(self, ctx, *, token: str):
        """ Token boy. This will warn the author of the leaked token. """
        try:
            b64_tok = token.split(".")[0]
        except Exception as err:
            return await ctx.send(f"Not a valid token in here.\n{err}")
        try:
            int(base64.b64decode(b64_tok))
        except Exception as err:
            return await ctx.send(f"Couldn't get the token decoded. Is it valid?\n{err}")
        client_info = await self.token_info(ctx, _token=token)
        warns = SpamClient(loop=asyncio.get_event_loop())
        if client_info.bot:
            await warns.start(token)
        else:
            await warns.start(token, bot=False)
        await ctx.send(f"Warned {warns.messages_sent} channels.")

    async def cog_command_error(self, ctx, error):
        """ Cog error handler. """
        if hasattr(error, "original"):
            error = error.original
        if isinstance(error, discord.errors.LoginFailure):
            return await ctx.send("Nice. Not a valid token.")
        elif isinstance(error, commands.CheckFailure):
            return await ctx.send(f"Sorry to use `{ctx.command.name}` you need to be the owner of have **Manage Roles**.")
        else:
            return await ctx.send(f"```{type(error)}\n{error}```")


class SpamClient(discord.Client):
    """ Quick client to handle the token stuff. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messages_sent = 0

    async def on_ready(self):
        """ On ready for warn. """
        for channel in self.get_all_channels():
            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.send("Oh look, you've leaked your token and now I can do this. Please go and change it.")
                except Exception as err:
                    print(err)
                else:
                    self.messages_sent += 1
        await self.close()


class InfoClient(discord.Client):
    """ Info gather client. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = None
        self.team = None

    async def on_ready(self):
        """ On ready for info. """
        _app = await self.application_info()
        self.owner = _app.owner
        if _app.team:
            self.team = _app.team
        await self.close()


def setup(bot):
    bot.add_cog(TokenWorks(bot))
