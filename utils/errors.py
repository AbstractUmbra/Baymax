from discord.ext.commands import (
    BadArgument,
    CheckFailure
)


__all__ = (
    'BadGameArgument',
    'CommandBannedInGuild',
    'NotEnoughOptions',
    'TooManyOptions',
    'ReactionIntegrityError',
    'NotPollOwner',
    'NoPollFound',
    'NotInitialized',
    'AlreadyInitialized',
    'ReactionAlreadyRegistered',
    'RoleOrEmojiNotFound',
    'InitializationInvalid',
    'NotReady',
    'BotIsIgnoringUser'
)


class BadGameArgument(BadArgument):
    pass


class CommandBannedInGuild(CheckFailure):
    pass


class NotEnoughOptions(ValueError):
    pass


class TooManyOptions(ValueError):
    pass


class ReactionIntegrityError(ValueError):
    pass


class NotPollOwner(ValueError):
    pass


class NoPollFound(KeyError):
    pass


class NotInitialized(Exception):
    pass


class AlreadyInitialized(Exception):
    pass


class InitializationInvalid(Exception):
    pass


class ReactionAlreadyRegistered(Exception):
    pass


class RoleOrEmojiNotFound(Exception):
    pass


class NotReady(CheckFailure):
    pass


class BotIsIgnoringUser(CheckFailure):
    pass
