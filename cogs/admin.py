""" Cleanup Cog. """
import discord
from discord.ext import commands

from utils.settings import SETTINGS, save_settings
from utils.decorators import with_roles, in_channel


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

    @with_roles(*SETTINGS['admins'])
    @commands.command()
    async def perms(self, ctx, role: discord.Member = None):
        """ Print the passed user perms to the console. """
        if role is None:
            role = ctx.author
        user_roles = '\n'.join(
            perm for perm, value in role.guild_permissions if value)
        role_embed = discord.Embed(title=f"User roles for {role}",
                                   description=f"Server: {ctx.guild.name}",
                                   colour=role.colour)
        role_embed.set_author(icon_url=role.avatar_url, name=str(role))
        role_embed.add_field(
            name="\uFEFF", value=user_roles, inline=True)
        await ctx.author.send(embed=role_embed)

    @with_roles(*SETTINGS['admins'])
    @commands.command()
    async def add(self, ctx, role: discord.Role):
        """ Add a role to the admin list. """
        if role is None:
            await ctx.send(f"Invalid usage; use {SETTINGS[str(ctx.guild.id)]['bot_prefix']}"
                           "admin add <@user>.",
                           delete_after=5)
        elif role.id in SETTINGS[str(ctx.guild.id)]["admins"]:
            await ctx.send(f"User {role} is already an admin.",
                           delete_after=5)
        else:
            SETTINGS[str(ctx.guild.id)]["admins"].append(role.id)
            save_settings(SETTINGS)
            await ctx.send(f"{role} has been added to admin list.",
                           delete_after=5)

    @with_roles(*SETTINGS['admins'])
    @commands.command()
    async def remove(self, ctx, role: discord.Role):
        """ Remove a role from the admin list. """
        if role is None:
            await ctx.send(f"Missing argument use {SETTINGS[str(ctx.guild.id)]['bot_prefix']}"
                           "admin remove <@user>",
                           delete_after=5)
        elif role.id not in SETTINGS[str(ctx.guild.id)]["admins"]:
            await ctx.send("Admin not found in admin list.",
                           delete_after=5)
        else:
            SETTINGS[str(ctx.guild.id)]["admins"].remove(role.id)
            save_settings(SETTINGS)
            await ctx.send(f"{role} was removed from admin list.",
                           delete_after=5)

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

    @commands.command(hidden=True)
    async def summon(self, ctx, role: discord.Member):
        """ Summon a voice role to current executors voice channel. """
        if role is None:
            await ctx.send(
                f"Missing argument, use `{SETTINGS[str(ctx.guild.id)]['bot_prefix']}"
                f"admin summonfucker <@user>`.",
                delete_after=5
            )
        elif role.voice.channel is ctx.message.author.voice.channel:
            await ctx.send(f"They're already in your voice chat, you wank.",
                           delete_after=5)
        else:
            await role.move_to(ctx.message.author.voice.channel)

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
        except commands.ExtensionNotLoaded:
            self.bot.load_cog(cog_full)
        except Exception as err:
            await ctx.send(f"**`ERROR:`** {type(err).__name__} - {err}",
                           delete_after=10)
        else:
            await ctx.send(f"Reloaded Cog: {cog}.", delete_after=5)


def setup(bot):
    """ Cog setup function. """
    bot.add_cog(Admin(bot))
