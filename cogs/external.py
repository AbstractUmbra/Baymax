from datetime import datetime
import textwrap

import discord
from discord.ext import commands


class PypiObject:
    """ Pypi objects. """

    def __init__(self, pypi_dict):
        self.module_name = pypi_dict['info']['name']
        self.module_author = pypi_dict['info']['author']
        self.module_author_email = pypi_dict['info']['author_email'] or None
        self.module_licese = pypi_dict['info']['license'] or "No license specified on PyPi."
        self.module_minimum_py = pypi_dict['info']['requires_python'] or "No minimum version specified."
        self.module_latest_ver = pypi_dict['info']['version']
        self.release_time = pypi_dict['releases'][str(
            self.module_latest_ver)][0]['upload_time']
        self.module_description = pypi_dict['info']['summary'] or None
        self.urls = pypi_dict['info']['project_urls']
        self.raw_classifiers = pypi_dict['info']['classifiers'] or None

    @property
    def minimum_ver(self) -> str:
        return discord.utils.escape_markdown(self.module_minimum_py)

    @property
    def classifiers(self) -> str:
        if self.raw_classifiers:
            new = textwrap.shorten("\N{zwsp}".join(
                self.raw_classifiers), width=300)
            return "\n".join(new.split("\N{zwsp}"))

    @property
    def description(self) -> str:
        if self.module_description:
            return textwrap.shorten(self.module_description, width=300)
        return None

    @property
    def release_datetime(self) -> datetime:
        datetime_obj = datetime.fromisoformat(self.release_time)
        if datetime_obj.day in [1, 21, 31]:
            date_modif = "st"
        elif datetime_obj.day in [2, 22]:
            date_modif = "nd"
        elif datetime_obj.day in [3, 23]:
            date_modif = "rd"
        else:
            date_modif = "th"
        return datetime_obj.strftime(f"%A %B %-d{date_modif} @ %H:%M UTC")


class External(commands.Cog):
    """ External API stuff. """

    def __init__(self, bot):
        self.bot = bot
        self.headers = {"User-Agent": "Robo-Hz Discord bot."}

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def pypi(self, ctx, *, package_name: str):
        """ Searches PyPi for a Package. """
        async with self.bot.session.get(f"https://pypi.org/pypi/{package_name}/json", headers=self.headers) as pypi_resp:
            pypi_json = await pypi_resp.json()
        pypi_details = PypiObject(pypi_json)
        embed = discord.Embed(title=f"{pypi_details.module_name} on PyPi",
                              colour=discord.Colour(0x000000))
        embed.set_author(name=pypi_details.module_author)
        embed.description = pypi_details.description
        if pypi_details.module_author_email:
            embed.add_field(name="Author Contact",
                            value=f"[Email]({pypi_details.module_author_email})")
        embed.add_field(name="Latest released ver",
                        value=pypi_details.module_latest_ver, inline=True)
        embed.add_field(name="Released at",
                        value=pypi_details.release_datetime, inline=True)
        embed.add_field(name="Minimum Python ver",
                        value=pypi_details.minimum_ver, inline=False)
        urls = "\n".join(
            [f"[{key}]({value})" for key, value in pypi_details.urls.items()])
        embed.add_field(name="Relevant URLs", value=urls)
        embed.add_field(
            name="License", value=pypi_details.module_licese)
        if pypi_details.raw_classifiers:
            print(pypi_details.raw_classifiers)
            embed.add_field(name="Classifiers",
                            value=pypi_details.classifiers, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        return await ctx.send(embed=embed)


def setup(bot):
    """ Cog entrypoint. """
    bot.add_cog(External(bot))
