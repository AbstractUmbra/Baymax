""" Cleanup Cog. """
from asyncio import TimeoutError as AsynTimeOut

import discord
from discord.ext import commands

from utils.settings import SETTINGS, save_settings
from utils.checks import admin_check, check_bound_text


class Admin(commands.Cog):
    """ Admin only commands. """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="id")
    async def get_channel_id(self, ctx, channel: discord.TextChannel = None):
        """ List the ID of a passed channel or current channel. """
        if channel is None:
            channel = ctx.channel
        await ctx.send(f"{channel.name}: `{channel.id}`", delete_after=20)

    @commands.command(name="ids")
    async def get_all_ids(self, ctx):
        """ prints all IDs in an embed. """
        texties = ctx.guild.text_channels
        voicies = ctx.guild.voice_channels
        texties_string = "\n".join(
            f"{chann.name}: {chann.id}" for chann in texties)
        voicies_string = "\n".join(
            f"{chann.name}: {chann.id}" for chann in voicies)
        id_embed = discord.Embed(title=f"IDs for {ctx.guild.name}",
                                 description="List of all IDs.",
                                 colour=ctx.author.colour)
        id_embed.set_author(icon_url=self.bot.user.avatar_url,
                            name=self.bot.user.name)
        id_embed.add_field(name="Text Channels",
                           value=f"{texties_string}", inline=True)
        id_embed.add_field(name="Voice Channels",
                           value=f"{voicies_string}", inline=True)
        await ctx.author.send(embed=id_embed)

    @commands.command()
    async def adminlist(self, ctx):
        """ Prints the admin list. """
        for admin in SETTINGS[str(ctx.guild.id)]["admins"]:
            await ctx.send(ctx.guild.get_member(admin), delete_after=20)

    @check_bound_text()
    @commands.command()
    async def perms(self, ctx, member: discord.Member = None):
        """ Print the passed user perms to the console. """
        if member is None:
            member = ctx.author
        user_roles = '\n'.join(
            perm for perm, value in member.guild_permissions if value)
        role_embed = discord.Embed(title=f"User roles for {member}",
                                   description=f"Server: {ctx.guild.name}",
                                   colour=member.colour)
        role_embed.set_author(icon_url=member.avatar_url, name=str(member))
        role_embed.add_field(
            name="\uFEFF", value=user_roles, inline=True)
        await ctx.author.send(embed=role_embed)

    @admin_check()
    @check_bound_text()
    @commands.command()
    async def add(self, ctx, member: discord.Member):
        """ Add a member to the admin list. """
        if member is None:
            await ctx.send(f"Invalid usage; use {SETTINGS[str(ctx.guild.id)]['bot_prefix']}"
                           "admin add <@user>.",
                           delete_after=5)
        elif member.id in SETTINGS[str(ctx.guild.id)]["admins"]:
            await ctx.send(f"User {member} is already an admin.",
                           delete_after=5)
        else:
            SETTINGS[str(ctx.guild.id)]["admins"].append(member.id)
            save_settings(SETTINGS)
            await ctx.send(f"{member} has been added to admin list.",
                           delete_after=5)

    @admin_check()
    @check_bound_text()
    @commands.command()
    async def remove(self, ctx, member: discord.Member):
        """ Remove a member from the admin list. """
        if member is None:
            await ctx.send(f"Missing argument use {SETTINGS[str(ctx.guild.id)]['bot_prefix']}"
                           "admin remove <@user>",
                           delete_after=5)
        elif member.id not in SETTINGS[str(ctx.guild.id)]["admins"]:
            await ctx.send("Admin not found in admin list.",
                           delete_after=5)
        else:
            SETTINGS[str(ctx.guild.id)]["admins"].remove(member.id)
            save_settings(SETTINGS)
            await ctx.send(f"{member} was removed from admin list.",
                           delete_after=5)

    @admin_check()
    @check_bound_text()
    @commands.command()
    async def add_bound_channel(self, ctx, channel: discord.TextChannel):
        """ Add a text channel to be bound. """
        if channel is None:
            await ctx.send(
                f"Invalid usage, use {SETTINGS[str(ctx.guild.id)]['bot_prefix']}"
                "admin add_channel <@text_channel>.",
                delete_after=5
            )
        elif channel.id in SETTINGS[str(ctx.guild.id)]["bound_text_channels"]:
            await ctx.send(f"Channel {channel} is already bot bound.",
                           delete_after=5)
        else:
            SETTINGS[str(ctx.guild.id)]["bound_text_channels"].append(
                channel.id)
            save_settings(SETTINGS)
            await ctx.send(f"{channel} has been added to the bound channel list.",
                           delete_after=5)

    @admin_check()
    @check_bound_text()
    @commands.command(hidden=True)
    async def summon(self, ctx, member: discord.Member):
        """ Summon a voice member to current executors voice channel. """
        if member is None:
            await ctx.send(
                f"Missing argument, use `{SETTINGS[str(ctx.guild.id)]['bot_prefix']}"
                f"admin summonfucker <@user>`.",
                delete_after=5
            )
        elif member.voice.channel is ctx.message.author.voice.channel:
            await ctx.send(f"They're already in your voice chat, you wank.",
                           delete_after=5)
        else:
            await member.move_to(ctx.message.author.voice.channel)

    @admin_check()
    @commands.command(hidden=True, name="load")
    async def load_cog(self, ctx, *, cog: str):
        """ Load a cog module. """
        cog_full = f"cogs.{cog}"
        try:
            self.bot.load_extension(cog_full)
        except Exception as err:
            await ctx.send(f"**`ERROR:`** {type(err).__name__} - {err}",
                           delete_after=10)
        else:
            await ctx.send(f"Loaded Cog: {cog}.", delete_after=5)

    @admin_check()
    @commands.command(hidden=True, name="unload")
    async def unload_cog(self, ctx, *, cog: str):
        """ Unload a cog module. """
        cog_full = f"cogs.{cog}"
        try:
            self.bot.unload_extension(cog_full)
        except Exception as err:
            await ctx.send(f"**`ERROR:`** {type(err).__name__} - {err}",
                           delete_after=10)
        else:
            await ctx.send(f"Unloaded Cog: {cog}.", delete_after=5)

    @commands.command(hidden=True, name="reload")
    async def reload_cog(self, ctx, *, cog: str):
        """ Reload a cog module. """
        cog_full = f"cogs.{cog}"
        try:
            self.bot.reload_extension(cog_full)
        except Exception as err:
            await ctx.send(f"**`ERROR:`** {type(err).__name__} - {err}",
                           delete_after=10)
        else:
            await ctx.send(f"Reloaded Cog: {cog}.", delete_after=5)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """ When a new member joins. """
        new_user_role = discord.utils.get(
            member.guild.roles, id=SETTINGS[str(member.guild.id)]['base_role']
        )

        def check(reaction, user):
            return user == member and str(reaction.emoji) == "👍"

        await member.send(
            f"Add '👍' reaction to solemly swear you'll be up to no good in {member.guild.name}."
        )
        try:
            _, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
        except AsynTimeOut:
            await member.send("Get fucked you didn't promise fast enough.")
        else:
            await member.send("Mischief managed.")
            await member.add_roles(new_user_role, reason="Server welcome.", atomic=True)


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Admin(bot))
