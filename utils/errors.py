""" Errors util. """
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
    """ Bad game argument. """


class CommandBannedInGuild(CheckFailure):
    """ Banned guild issued a command. """


class NotEnoughOptions(ValueError):
    """ Not enough options. """


class TooManyOptions(ValueError):
    """ Too many options. """


class ReactionIntegrityError(ValueError):
    """ Reaction integrity error. """


class NotPollOwner(ValueError):
    """ Not a poll owner. """


class NoPollFound(KeyError):
    """ No poll found. """


class NotInitialized(Exception):
    """ Not yet initialized. """


class AlreadyInitialized(Exception):
    """ Already initialized. """


class InitializationInvalid(Exception):
    """ Initialization invalid. """


class ReactionAlreadyRegistered(Exception):
    """ Reactions already registered. """


class RoleOrEmojiNotFound(Exception):
    """ Role or Emoji not found. """


class NotReady(CheckFailure):
    """ Not ready yet. """


class BotIsIgnoringUser(CheckFailure):
    """ Bot is ignoring you. """
