import asyncio
import binascii
import re
from base64 import b64decode
from textwrap import dedent

import yarl

import discord
from discord.ext import commands
from utils.time import hf_time


class GithubError(commands.CommandError):
    pass


TOKEN_REGEX = re.compile(
    r'[a-zA-Z0-9_-]{23,28}\.[a-zA-Z0-9_-]{6,7}\.[a-zA-Z0-9_-]{27}')

EXAMPLE_TOKENS = [
    "MjM4NDk0NzU2NTIxMzc3Nzky.CunGFQ.wUILz7z6HoJzVeq6pyHPmVgQgV4",
    "NDc4NDM3MTAxMTIyMjI0MTI4.Dn8zSw.CWORjs-4vMJAbZmSZVEpBYJ3g3E",
]
RDADDY = 80528701850124288

def validate_token(token):
    try:
        # Just check if the first part validates as a user ID
        (user_id, _, _) = token.split('.')
        user_id = int(b64decode(user_id, validate=True))
    except (ValueError, binascii.Error):
        return False
    else:
        return True

class Token(commands.Cog):
    """ For handling and parsing tokens. """

    def __init__(self, bot):
        self.bot = bot
        self._req_lock = asyncio.Lock(loop=self.bot.loop)

    async def github_request(self, method, url, *, params=None, data=None, headers=None):
        hdrs = {
            'Accept': 'application/vnd.github.inertia-preview+json',
            'User-Agent': 'Baymax Discord.py Bot',
            'Authorization': f'token {self.bot.config.github_token}'
        }

        req_url = yarl.URL('https://api.github.com') / url

        if headers is not None and isinstance(headers, dict):
            hdrs.update(headers)

        await self._req_lock.acquire()
        try:
            async with self.bot.session.request(method, req_url, params=params, json=data, headers=hdrs) as r:
                remaining = r.headers.get('X-Ratelimit-Remaining')
                js = await r.json()
                if r.status == 429 or remaining == '0':
                    # wait before we release the lock
                    delta = discord.utils._parse_ratelimit_header(r)
                    await asyncio.sleep(delta)
                    self._req_lock.release()
                    return await self.github_request(method, url, params=params, data=data, headers=headers)
                elif 300 > r.status >= 200:
                    return js
                else:
                    raise GithubError(js['message'])
        finally:
            if self._req_lock.locked():
                self._req_lock.release()

    async def create_gist(self, content, *, description: str = None, filename: str = None, public: bool = True):
        headers = {"Accept": "application/vnd.github.v3+json"}
        filename = filename or "output.txt"
        data = {
            "public": public,
            "files": {
                filename: {
                    "content": content
                }
            }
        }
        if description:
            data['description'] = description

        js = await self.github_request("POST", "gists", data=data, headers=headers)
        return js['html_url']

    @commands.Cog.listener()
    async def on_message(self, message):
        if getattr(message.guild, "id", None) == 336642139381301249:
            return
        if message.author.id == RDADDY:
            return
        tokens = [token for token in TOKEN_REGEX.findall(
                    message.content) if validate_token(token) and token not in EXAMPLE_TOKENS]
        if tokens and message.author.id != self.bot.user.id:
            url =  await self.create_gist('\n'.join(tokens), description='Invalidating a token.')
            embed = discord.Embed(description=f"Located token(s) have now been [invalidated]({url}).", colour=discord.Colour(0x000001))
            return await message.channel.send(embed=embed)

    @commands.group(invoke_without_command=True, aliases=["t"])
    async def token(self, ctx, *, token) -> discord.Message:
        """ Invalidate a token manually. """
        if ctx.invoked_subcommand:
            pass
        if not validate_token(token):
            raise ValueError
        url = await self.create_gist(token, description="Invalidating a token.")
        embed = discord.Embed(colour=discord.Colour(0x000001))
        embed.description = f"Token now [invalidated]({url})."
        await ctx.send(embed=embed)

    @token.command(aliases=["p"])
    async def parse(self, ctx, *, token):
        """ Parse a token and return details. """
        if not validate_token(token):
            raise ValueError
        enc_id = token.split(".")
        # We only care about the user id, so yeah, index.
        enc_id = enc_id[0]
        enc_id = b64decode(enc_id)
        user_id = int(enc_id.decode("utf-8"))

        user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        if not user:
            return ctx.send("Not a valid token.")
        url = await self.create_gist(token, description="Invalidating a token.")
        msg = f"""
        ```prolog
        User ID         : {user.id}
        User Created At : {hf_time(user.created_at)}
        Bot             : {user.bot}
        ```
        """

        embed = discord.Embed()
        embed.title = "Token details:"
        embed.description = f"{dedent(msg)}\nIt has also been [invalidated]({url})."
        embed.set_footer(text=user.name, icon_url=user.avatar_url)
        await ctx.send(embed=embed)

    @parse.error
    async def token_parsing_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, ValueError):
            return await ctx.send(f"`{ctx.kwargs['token'].split('.')[0]}` doesn't seem to be a valid token encoding.")


def setup(bot):
    bot.add_cog(Token(bot))
