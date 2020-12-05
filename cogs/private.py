import asyncio
import datetime
import re
from enum import Enum
from typing import Optional, Union

from discord import (AsyncWebhookAdapter, AuditLogAction, AuditLogEntry,
                     CategoryChannel, Colour, Embed, Guild, Member, Message,
                     Object, TextChannel, User, VoiceChannel, Webhook)
from discord.abc import GuildChannel
from discord.ext import commands

DPY_GUILD_ID = 336642139381301249
BLOCK_RE = re.compile(
    r"(?:Temp)?block By [^#]+#\d{4} \(ID: (\d+)\)(?: until (.*))?", re.IGNORECASE
)
MUTE_RE = re.compile(
    r"([^#]+#\d{4} \(ID: (\d+)\):(.*))?(Action done by [^#]+#\d{4} \(ID: (\d+)\))?",
    re.IGNORECASE,
)
# 2nd or 5th index, attempt both?


class ModActions(Enum):
    """ Small Enum for actions. """

    banned = 1
    kicked = 2
    unbanned = 3
    muted = 4
    helpblocked = 5


class Private(commands.Cog):
    """ Private Cog. Listeners and memes. """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.colours = {
            ModActions.banned: 0xFFFFFE,
            ModActions.kicked: 0x767774,
            ModActions.unbanned: 0x000001,
            ModActions.muted: 0xC95E71,
            ModActions.helpblocked: 0x9E9F9D,
        }
        self.webhooks = [
            Webhook.from_url(
                bot.config.silly_webhook, adapter=AsyncWebhookAdapter(self.bot.session)
            ),
            Webhook.from_url(
                bot.config.dunston_webhook,
                adapter=AsyncWebhookAdapter(self.bot.session),
            ),
        ]

    async def cog_check(self, ctx):  # pylint: disable=W0236
        """ All commands are owner only. """
        return await self.bot.is_owner(ctx.author)

    async def find_block(
        self,
        *,
        guild: Guild,
        channel: GuildChannel,
        action: AuditLogAction,
        debug: bool = False,
    ) -> Optional[AuditLogEntry]:
        if debug:
            await self.bot.get_user(self.bot.owner_id).send("find_start")
        async for entry in guild.audit_logs(action=action, limit=3):
            if entry.target.id == channel.id:
                # help 1 entry
                if not getattr(entry, "reason", None):
                    continue  # no reason | not a helpblock
                if not bool(re.match(r"\b(temp)?block\b", entry.reason.lower())):
                    continue  # no match to tempblock / block. Usually means an unblock or manual removal
                if debug:
                    await self.bot.get_user(self.bot.owner_id).send("find_done")
                    return entry
                else:
                    if (datetime.datetime.utcnow() - entry.created_at).seconds <= 30:
                        return entry

    def gen_embed(
        self,
        event: ModActions,
        *,
        member: Union[Member, User],
        entry: AuditLogEntry,
        **kwargs,
    ):
        """ Gen the embed for the events. """
        helper = kwargs.get("helper", None)
        expires = kwargs.get("expires", False)
        reason = kwargs.get("reason", None)
        mod = kwargs.get("mod", None)
        colour = kwargs.get("colour", None)

        author = helper or mod or entry.user

        colour = colour or Colour(self.colours[event])

        embed = Embed(title=f"D.py {event.name}", colour=colour)
        embed.description = f"{member.name} was {event.name} from dpy."
        embed.set_author(name=author.name, icon_url=author.avatar_url)

        if event is not ModActions.helpblocked:
            embed.add_field(
                name=f"{event.name} by:".capitalize(), value=entry.user, inline=False
            )

        embed.add_field(
            name="Reason", value=reason or entry.reason or "None", inline=False
        )

        if mod:
            embed.add_field(name="Moderator:", value=str(mod), inline=False)
        if helper:
            embed.add_field(name="Helper:", value=helper, inline=False)
        if expires:
            embed.description = (
                f"{embed.description}\nPlease see the timestamp for expiration."
            )
            embed.timestamp = expires

        embed.set_footer(
            text=f"{member.name} | {member.id}", icon_url=(member.avatar_url or None)
        )

        return embed

    @commands.Cog.listener()
    async def on_member_ban(self, guild: Guild, person: Union[User, Member]):
        """ When someone in dpy get banned. """
        if guild.id != DPY_GUILD_ID:
            return
        real_entry = False
        await asyncio.sleep(3)
        async for entry in guild.audit_logs(action=AuditLogAction.ban, limit=5):
            if entry.target.id == person.id:
                real_entry = entry
                break
        if not real_entry:
            return
        embed = self.gen_embed(ModActions.banned, member=person, entry=real_entry)
        await self.bot.get_user(self.bot.owner_id).send(embed=embed)
        for wh in self.webhooks:
            await wh.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        """ When someone in dpy gets kicked! """
        if member.guild.id != DPY_GUILD_ID:
            return
        real_entry = False
        await asyncio.sleep(3)
        async for entry in member.guild.audit_logs(action=AuditLogAction.kick, limit=5):
            if entry.target.id == member.id:
                if (entry.created_at - datetime.datetime.utcnow()).seconds >= 10:
                    real_entry = entry
                    break
        if not real_entry:
            return
        embed = self.gen_embed(ModActions.kicked, member=member, entry=real_entry)
        await self.bot.get_user(self.bot.owner_id).send(embed=embed)
        for wh in self.webhooks:
            await wh.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: Guild, person: User):
        """ When someone in dpy get banned. """
        if guild.id != DPY_GUILD_ID:
            return
        real_entry = False
        await asyncio.sleep(3)
        async for entry in guild.audit_logs(action=AuditLogAction.unban, limit=5):
            if entry.target.id == person.id:
                real_entry = entry
                break
        if not real_entry:
            return
        embed = self.gen_embed(ModActions.unbanned, member=person, entry=real_entry)
        await self.bot.get_user(self.bot.owner_id).send(embed=embed)
        for wh in self.webhooks:
            await wh.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self,
        before: Union[VoiceChannel, TextChannel, CategoryChannel],
        after: Union[VoiceChannel, TextChannel, CategoryChannel],
        *,
        debug: bool = False,
    ) -> Message:
        """ Someone is help blocked. """
        if before.id != 381965515721146390:
            # not help1
            return

        real_entry = None
        new_overwrite_for = None

        await asyncio.sleep(3)  # to allow the audit log to actually... create.

        if debug:
            await self.bot.get_user(self.bot.owner_id).send("main start")
        real_entry = await self.find_block(
            guild=before.guild,
            channel=after,
            action=AuditLogAction.overwrite_update,
            debug=debug,
        ) or await self.find_block(
            guild=before.guild,
            channel=after,
            action=AuditLogAction.overwrite_create,
            debug=debug,
        )

        if not real_entry:
            if debug:
                await self.bot.get_user(self.bot.owner_id).send("no entry")
            return

        new_overwrite_for = (
            real_entry.extra if isinstance(real_entry.extra, Member) else None
        )

        if not new_overwrite_for:
            # entries return no accurate search
            await self.bot.get_user(self.bot.owner_id).send(
                f"failed:\nEntry: {real_entry}\nMember target: {new_overwrite_for}."
            )
            return

        if not before.guild.get_member(new_overwrite_for.id):
            return

        reason_expanded = BLOCK_RE.search(real_entry.reason)

        if reason_expanded:
            helper = self.bot.get_user(int(reason_expanded[1]))
            expires = (
                datetime.datetime.strptime(reason_expanded[2], "%Y-%m-%d %H:%M:%S.%f")
                if reason_expanded[2]
                else None
            )
            embed = self.gen_embed(
                ModActions.helpblocked,
                member=new_overwrite_for,
                entry=real_entry,
                helper=helper,
                expires=expires,
            )
            await self.bot.get_user(self.bot.owner_id).send(embed=embed)
            for wh in self.webhooks:
                await wh.send(embed=embed)
        else:
            fmt = real_entry.reason
            await self.bot.get_user(self.bot.owner_id).send(
                f"reason_expanded failed {fmt}"
            )

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member) -> Message:
        """ When someone gets muted. """
        if before.guild.id != DPY_GUILD_ID:
            return
        if before.roles == after.roles:
            return

        if after._roles.has(570243756130041876) and not before._roles.has(
            570243756130041876
        ):
            # Muted
            await asyncio.sleep(3)

            real_entry = None
            async for entry in after.guild.audit_logs(
                action=AuditLogAction.member_role_update, limit=15
            ):
                reason = getattr(entry, "reason", "No reason") or "No reason"
                if entry.target.id == after.id and "self-mute" not in reason.lower():
                    real_entry = entry
                    break

            if not real_entry:
                return

            reason_expanded = MUTE_RE.search(real_entry.reason)
            mod_id = None
            mod_reason = None
            if reason_expanded:
                if bool(reason_expanded[5]):
                    mod_id = reason_expanded[5]
                    mod_reason = "No reason"
                else:
                    mod_id = reason_expanded[2]
                    if reason_expanded[3]:
                        mod_reason = reason_expanded[3].lstrip()
                    else:
                        mod_reason = "Member was previously muted."
            if not mod_id and not mod_reason:
                return

            mod = self.bot.get_user(int(mod_id))
            embed = self.gen_embed(
                ModActions.muted,
                member=after,
                entry=real_entry,
                mod=mod,
                reason=mod_reason,
            )
            await self.bot.get_user(self.bot.owner_id).send(embed=embed)
            for wh in self.webhooks:
                await wh.send(embed=embed)


def setup(bot):
    bot.add_cog(Private(bot))
