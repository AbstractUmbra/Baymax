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

    @commands.group(hidden=True)
    async def token(self, ctx):
        """ Token primary command. """
        if not ctx.invoked_subcommand:
            return

    @token.command(name="i", aliases=["info", "information"])
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
            team_list = [str(member) for member in client_info.team.members]
            embed.add_field(name="Owner", value="\n".join(team_list))
        await ctx.send(embed=embed)
        return token_user


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
