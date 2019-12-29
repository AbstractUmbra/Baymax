""" Utils addon - decorators. """
from asyncio import Lock
from functools import wraps
from typing import Callable, Container
from weakref import WeakValueDictionary

from discord import Colour, Embed
from discord.ext import commands
from discord.ext.commands import CheckFailure, Cog, Context

from utils.checks import with_role_check, without_role_check


class InChannelCheckFailure(CheckFailure):
    """ Raised when a check fails for a message being sent in a whitelisted channel. """

    def __init__(self, *channels: int):
        self.channels = channels
        channels_str = ", ".join(f"<#{ch_id}>" for ch_id in channels)
        super().__init__(
            f"Sorry, but you may only use this command within {channels_str}")


def in_channel(
        *channels: int,
        hidden_channels: Container[int] = None,
        bypass_roles: Container[int] = None
) -> Callable:
    """
    Checks the message is in a whitelisted channel or optionally has a bypass role.
    Hidden channels are channels which will not be displayed in the error message.
    """
    hidden_channels = hidden_channels or []
    bypass_roles = bypass_roles or []

    def predicate(ctx: Context) -> bool:
        """ In-channel checker predication. """
        if ctx.channel.id in channels or ctx.channel.id in hidden_channels:
            return True

        if bypass_roles:
            if any(role.id in bypass_roles for role in ctx.author.roles):
                return True

        raise InChannelCheckFailure(*channels)
    return commands.check(predicate)


def with_roles(*role_ids: int) -> Callable:
    """ Returns True if the user has any of the roles in role_ids. """
    async def predicate(ctx: Context) -> bool:
        return with_role_check(ctx, *role_ids)
    return commands.check(predicate)


def without_roles(*role_ids: int) -> Callable:
    """ Returns True if the user does not have any of the roles in role_ids. """
    async def predicate(ctx: Context) -> bool:
        return without_role_check(ctx, *role_ids)
    return commands.check(predicate)