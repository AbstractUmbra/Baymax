""" Mick's quick stuffs. """
import discord
from discord.ext import commands


class Specialist(commands.Cog):
    """ Class designed for SpecialistTV channel. """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """ For when Member's join the guild. """
        if member.guild.id == 690566307409821697:
            await member.guild.system_channel.send(
                f"Hey {member.mention} 👋. Welcome to **Specialist's Discord Server**."
                " Please take the time to read the <#690570977381318736> channel and"
                " feel free to chat to us and introduce yourself in <#690566308269391953>."
                " GL & HF!")
            role = member.guild.get_role(691298204918087691)
            await member.add_roles(role, reason="New member!", atomic=True)


def setup(bot):
    """ Cog setup time. """
    bot.add_cog(Specialist(bot))
