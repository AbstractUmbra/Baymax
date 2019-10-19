""" Utils addon - Exceptions. """
from discord.ext import commands


class NotAnAdmin(Exception):
    """ Exception for Not an admin of Server bot. """


class UnpermittedChannel(Exception):
    """ Exception for an unpermitted text channel. """


class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""
