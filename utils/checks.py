""" Utils addon - checks. """
import datetime
from typing import Callable, Iterable

from discord.ext.commands import (BucketType, Cog, Command,
                                  CommandOnCooldown, Context, Cooldown, CooldownMapping)


def with_role_check(ctx: Context, *role_ids: int) -> bool:
    """ Returns True if the author has any one of the roles in role_ids. """
    if not ctx.guild:  # means it's a DM.
        return False

    for role in ctx.author.roles:
        if role.id in role_ids:
            return True

    return False


def without_role_check(ctx: Context, *role_ids: int) -> bool:
    """ Returns true if the user does not have any of the roles in role_ids. """
    if not ctx.guild:  # Means it's a DM.
        return False

    author_roles = [role.id for role in ctx.author.roles]
    return all(role not in author_roles for role in role_ids)


def in_channel_check(ctx: Context, *channel_ids: int) -> bool:
    """ Checks if the command was executed in a specific list of channels. """
    return ctx.channel.id in channel_ids


def cooldown_with_role_bypass(rate: int, per: float, btype: BucketType = BucketType.default, *,
                              bypass_roles: Iterable[int]) -> Callable:
    """ This applies a cooldown to commands, allows users with specific roles to bypass them. """
    bypass = set(bypass_roles)

    # Cooldown logic handler
    buckets = CooldownMapping(Cooldown(rate, per, btype))

    # We call this after the command has been parsed/read but before it has been invoked.
    # This is to ensure the end user isn't a twat and doesn't mess up input.
    async def predicate(cog: Cog, ctx: Context) -> None:
        nonlocal bypass, buckets

        if any(role.id in bypass for role in ctx.author.roles):
            return

        # Cooldown logic time
        current = ctx.message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
        bucket = buckets.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit(current)
        if retry_after:
            raise CommandOnCooldown(bucket, retry_after)

        def wrapper(command: Command) -> Command:
            if not isinstance(command, Command):
                raise TypeError("`cooldown_with_role_bypass` must be applied after the command "
                                "decorator. It has to be ABOVE the command decorator in the code.")
            command._before_invoke = predicate
            return command
        return wrapper
