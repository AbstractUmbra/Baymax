""" Utils addon - Checks. """

from discord.ext import commands
from utils.settings import SETTINGS
from utils.exceptions import UnpermittedChannel, NotAnAdmin


def admin_check():
    """ Checks the executing user is in the Admin list. """
    def predicate(ctx):
        if ctx.message.author.id not in SETTINGS[str(ctx.guild.id)]["admins"]:
            raise NotAnAdmin(
                f"You are not an admin of {ctx.guild}: {ctx.guild.id}.")
        return True
    return commands.check(predicate)


def check_bound_text():
    """ Checks the channel executing from is in the whitelist. """
    def permitted_text(ctx):
        if ctx.channel.id not in SETTINGS[str(ctx.guild.id)]["bound_text_channels"]:
            ctx.invoke(ctx.message.delete())
            raise UnpermittedChannel(
                f"The bot is not bound to this text channel: {ctx.channel}")
        else:
            return True
    return commands.check(permitted_text)
