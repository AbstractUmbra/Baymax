""" Utils addon - Members. """

from itertools import chain


def all_voice_members_guild(ctx):
    """ Gets all the members currently in a voice channel. """
    guild_vms = list(chain.from_iterable(
        [member for member in [ch.members for ch in ctx.guild.voice_channels]]))
    return guild_vms
