""" Token parser """
import asyncio
import base64
from typing import Union

import discord
from discord.ext import commands


class TokenWorks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def decode_tok(self, token: str) -> int:
        token_id = int(base64.b64decode(token))
        return token_id

    @commands.group(hidden=True, invoke_without_command=True)
    async def token(self, ctx):
        if not ctx.invoked_subcommand:
            return

    @token.command(name="i")
    async def token_info(self, ctx, *, _token: str):
        decoded_token = await self.decode_tok(_token.split(".")[0])
        token_user = await self.bot.fetch_user(decoded_token)
        if not token_user:
            return await ctx.send("User ID doesn't work, sadly.")
        time = token_user.created_at.strftime("%d-%m-%Y %H:%M:%S")
        client_info = InfoClient(loop=asyncio.get_event_loop())
        await client_info.start(_token)
        embed = discord.Embed(
            description=f"""
                            **Username**: `{token_user.name}`
                            **ID**: `{decoded_token}`
                            **Existed since**: `{time}`
                            **Bot**: `{token_user.bot}`
                        """)
        embed.add_field(name="Owner", value=f"{client_info.owner}")
        if client_info.team:
            team_list = [str(member) for member in client_info.team]
            embed.add_field(name="Owner", value="\n".join(team_list))
        embed.set_thumbnail(url=token_user.avatar_url)
        await ctx.send(embed=embed)

    @token.command(name="w")
    async def token_warn(self, ctx, *, token: str):
        try:
            b64_tok = token.split(".")[0]
        except Exception as err:  # TODO Find exception
            return await ctx.send(f"Not a valid token in here.\n{err}")
        try:
            token_user_id = int(base64.b64decode(b64_tok))
        except Exception as err:  # TODO Find exception
            return await ctx.send(f"Couldn't get the token decoded. Is it valid?\n{err}")
        await self.token_info(ctx, _token=token_user_id)
        warns = SpamClient(loop=asyncio.get_event_loop())
        await warns.start(token)
        await ctx.send(f"Warned {warns.messages_sent} channels.")

    @token_warn.error
    async def tk_error(self, ctx, error):
        if hasattr(error, "original"):
            error = error.original
        if isinstance(error, discord.errors.LoginFailure):
            await ctx.send("Nice. Not a valid token.")

    @token_info.error
    async def tk_info_error(self, ctx, error):
        if hasattr(error, "original"):
            error = error.original
        if isinstance(error, discord.errors.LoginFailure):
            await ctx.send("Nice. Not a valid token.")


class SpamClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messages_sent = 0

    async def on_ready(self):
        # channel stuff
        for channel in self.get_all_channels():
            try:
                await channel.send("CHANGE YOUR FUCKING TOKEN.")
            except Exception as err:
                print(err)
            else:
                self.messages_sent += 1
        await self.close()


class InfoClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = None
        self.team = None

    async def on_ready(self):
        _app = await self.application_info()
        self.owner = _app.owner
        if _app.team:
            self.team = _app.team
        await self.close()


def setup(bot):
    bot.add_cog(TokenWorks(bot))
