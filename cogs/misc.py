import asyncio
import sys
import time
from random import random
from typing import TYPE_CHECKING, Literal, Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context, Greedy
from discord.utils import oauth_url
from sqlalchemy import delete

from bot import ChuniBot
from database.models import Prefix

if TYPE_CHECKING:
    from cogs.botutils import UtilsCog


class MiscCog(commands.Cog, name="Miscellaneous"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: "UtilsCog" = self.bot.get_cog("Utils")  # type: ignore[reportGeneralTypeIssues]

    @commands.command("treesync", hidden=True, invoke_without_command=True)
    @commands.is_owner()
    async def sync(
        self,
        ctx: Context,
        guilds: Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:  # noqa: PERF203
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    @commands.hybrid_command("source", aliases=["src"])
    async def source(self, ctx: Context):
        """Get the source code for this bot."""

        reply = (
            "https://tenor.com/view/metal-gear-rising-metal-gear-rising-revengeance-senator-armstrong-revengeance-i-made-it-the-fuck-up-gif-25029602"
            if random() < 0.1
            else "<https://github.com/beerpiss/chuninewbot>"
        )

        await ctx.reply(reply, mention_author=False)

    @commands.hybrid_command("invite")
    async def invite(self, ctx: Context):
        """Invite this bot to your server!"""

        permissions = discord.Permissions(
            read_messages=True,
            send_messages=True,
            send_messages_in_threads=True,
            manage_messages=True,
            read_message_history=True,
        )

        await ctx.reply(oauth_url(self.bot.user.id, permissions=permissions), mention_author=False)  # type: ignore[reportGeneralTypeIssues]

    @commands.hybrid_command("status")
    async def status(self, ctx: Context):
        """View the bot's status."""

        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "rev-parse",
                "--short",
                "HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            revision = stdout.decode("utf-8").replace("\n", "")
        except FileNotFoundError:
            revision = "unknown"
        if not revision:
            revision = "unknown"

        summary = [
            f"chuninewbot revision `{revision}`",
            f"discord.py `{discord.__version__}`",
            f"Python `{sys.version}` on `{sys.platform}`",
            "",
            f"Online since <t:{int(self.bot.launch_time)}:R>",
            "",
            f"This bot can see {len(self.bot.guilds)} guild(s) and {len(self.bot.users)} user(s).",
            f"Average websocket latency: {round(self.bot.latency * 1000, 2)}ms",
        ]

        await ctx.reply("\n".join(summary), mention_author=False)

    @commands.hybrid_command("ping")
    async def ping(self, ctx: Context):
        start = time.perf_counter()
        message = await ctx.send("Ping...")
        end = time.perf_counter()
        duration = (end - start) * 1000
        await message.edit(
            content=(
                f"Pong! Took {duration:.2f}ms\n"
                f"Websocket latency: {round(self.bot.latency * 1000, 2)}ms"
            )
        )

    @commands.hybrid_command("prefix")
    @commands.guild_only()
    async def prefix(self, ctx: Context, new_prefix: Optional[str] = None):
        """Get or set the prefix for this server.

        Permissions
        -----------
        Only users with the Manage Guild permission can set the prefix.

        Parameters
        ----------
        new_prefix: Optional[str]
            New prefix to set. If not provided, the current prefix will be shown.
        """

        # discord.TextChannel should have an associated guild
        assert ctx.guild is not None

        async with ctx.typing():
            if new_prefix is None:
                answer = await self.utils.guild_prefix(ctx)
                await ctx.reply(f"Current prefix: `{answer}`", mention_author=False)
            else:
                permissions = ctx.author.guild_permissions  # type: ignore[reportGeneralTypeIssues]
                missing_permission = permissions.manage_guild is not True
                if missing_permission:
                    raise commands.MissingPermissions(["manage_guild"])

                default_prefix: str = self.bot.cfg.bot.default_prefix
                async with self.bot.begin_db_session() as session, session.begin():
                    if new_prefix == default_prefix:
                        stmt = delete(Prefix).where(Prefix.guild_id == ctx.guild.id)
                        await session.execute(stmt)
                        del self.bot.prefixes[ctx.guild.id]
                    else:
                        prefix = Prefix(guild_id=ctx.guild.id, prefix=new_prefix)
                        await session.merge(prefix)
                        self.bot.prefixes[ctx.guild.id] = new_prefix

                await ctx.reply(f"Prefix set to `{new_prefix}`", mention_author=False)

    @commands.command("privacy")
    async def privacy(self, ctx: Context):
        """Everything you need to know about this bot's privacy-related information."""

        if (
            ctx.message.reference is not None
            and ctx.message.reference.message_id is not None
        ):
            reference = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )
        else:
            reference = ctx.message

        await reference.reply(
            "https://cdn.discordapp.com/emojis/1091440450122022972.webp?quality=lossless",
            mention_author=False,
        )


async def setup(bot: ChuniBot) -> None:
    await bot.add_cog(MiscCog(bot))
