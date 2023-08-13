import logging
import traceback
from typing import TYPE_CHECKING, cast

import aiohttp
import discord
from discord import Webhook, app_commands
from discord.ext import commands
from discord.ext.commands import Context

from chunithm_net.exceptions import (
    ChuniNetException,
    InvalidTokenException,
    MaintenanceException,
)

if TYPE_CHECKING:
    from bot import ChuniBot


class EventsCog(commands.Cog, name="Events"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: Context,
        error: commands.errors.CommandInvokeError,
    ):
        if isinstance(error, commands.CommandNotFound):
            return None

        if isinstance(error, commands.errors.HybridCommandError):
            exc = error.original
            if isinstance(exc, app_commands.errors.CommandInvokeError):
                try:
                    exc = error.original
                except AttributeError:
                    exc = error
        else:
            try:
                exc = error.original
            except AttributeError:
                exc = error

        logging.getLogger("discord").error(
            "Exception in command %s", ctx.command, exc_info=exc
        )

        if isinstance(exc, MaintenanceException):
            return await ctx.reply(
                "CHUNITHM-NET is currently undergoing maintenance. Please try again later.",
                mention_author=False,
            )
        if isinstance(exc, InvalidTokenException):
            message = (
                "CHUNITHM-NET cookie is invalid. Please use `c>login` in DMs to log in."
            )
            if self.bot.dev:
                message += f"\nDetailed error: {exc}"
            return await ctx.reply(message, mention_author=False)
        if isinstance(exc, ChuniNetException):
            message = "An error occurred while communicating with CHUNITHM-NET. Please try again later (or re-login)."
            if self.bot.dev:
                message += f"\nDetailed error: {exc}"
            return await ctx.reply(message, mention_author=False)

        if isinstance(exc, commands.errors.CommandOnCooldown):
            return await ctx.reply(
                f"You're too fast. Take a break for {exc.retry_after:.2f} seconds.",
                mention_author=False,
                delete_after=exc.retry_after,
            )
        if isinstance(exc, commands.errors.ExpectedClosingQuoteError):
            return await ctx.reply(
                "You're missing a quote somewhere. Perhaps you're using the wrong kind of quote (`\"` vs `”`)?",
                mention_author=False,
            )
        if isinstance(
            exc, (commands.errors.NotOwner, commands.errors.MissingPermissions)
        ):
            return await ctx.reply("Insufficient permissions.", mention_author=False)
        if isinstance(
            exc,
            (
                commands.BadArgument,
                commands.BadUnionArgument,
                commands.MissingRequiredArgument,
                commands.MissingPermissions,
                commands.BotMissingPermissions,
                commands.MaxConcurrencyReached,
                commands.NoPrivateMessage,
                commands.PrivateMessageOnly,
            ),
        ):
            return await ctx.reply(str(error), mention_author=False)

        await ctx.reply(
            "An error occurred while executing the command.",
            mention_author=False,
        )

        if webhook_url := self.bot.cfg.bot.error_reporting_webhook:
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(webhook_url, session=session)

                content = (
                    f"## Exception in command {ctx.command}\n\n"
                    "```python\n"
                    f"{''.join(traceback.format_exception(exc))}"
                    "```"
                )
                await webhook.send(
                    username=cast(discord.ClientUser, self.bot.user).display_name,
                    avatar_url=cast(
                        discord.ClientUser, self.bot.user
                    ).display_avatar.url,
                    content=content,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                return None
        return None


async def setup(bot: "ChuniBot"):
    await bot.add_cog(EventsCog(bot))
