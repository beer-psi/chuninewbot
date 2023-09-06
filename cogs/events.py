import traceback
from typing import TYPE_CHECKING, cast

import aiohttp
import discord
from discord import Webhook
from discord.ext import commands
from discord.ext.commands import Context

from chunithm_net.exceptions import (
    ChuniNetException,
    InvalidTokenException,
    MaintenanceException,
)
from utils.config import config
from utils.logging import logger

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

        exc = error.original
        while hasattr(exc, "original"):
            exc = exc.original  # type: ignore[reportGeneralTypeIssues]

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
        if isinstance(exc, commands.errors.UnexpectedQuoteError):
            return await ctx.reply(
                (
                    f"Unexpected quote mark, {exc.quote!r}, in non-quoted string. If this was intentional, "
                    "escape the quote with a backslash (\\\\)."
                ),
                mention_author=False,
            )
        if isinstance(
            exc, (commands.errors.NotOwner, commands.errors.MissingPermissions)
        ):
            return await ctx.reply("Insufficient permissions.", mention_author=False)
        if isinstance(exc, commands.BadLiteralArgument):
            to_string = [repr(x) for x in exc.literals]
            if len(to_string) > 2:
                fmt = "{}, or {}".format(", ".join(to_string[:-1]), to_string[-1])
            else:
                fmt = " or ".join(to_string)
            return await ctx.reply(
                f"`{exc.param.displayed_name or exc.param.name}` must be one of {fmt}, received {exc.argument!r}",
                mention_author=False,
            )
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

        logger.error("Exception in command %s", ctx.command, exc_info=exc)
        await ctx.reply(
            (
                "Something really terrible happened. "
                f"The owner <@{self.bot.owner_id}> has been notified.\n"
                "Please try again in a couple of hours."
            ),
            mention_author=False,
        )

        if webhook_url := config.bot.error_reporting_webhook:
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(webhook_url, session=session)

                content = (
                    f"## Exception in command {ctx.command}\n\n"
                    "```python\n"
                    f"{(''.join(traceback.format_exception(exc)))[-1961 + len(str(ctx.command)):]}"
                    "```"
                )

                client_user = cast(discord.ClientUser, self.bot.user)
                await webhook.send(
                    username=client_user.display_name,
                    avatar_url=client_user.display_avatar.url,
                    content=content,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
        return None


async def setup(bot: "ChuniBot"):
    await bot.add_cog(EventsCog(bot))
