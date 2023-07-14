import logging
import traceback
from typing import TYPE_CHECKING, cast

import aiohttp
import discord
from discord import Webhook
from discord.ext import commands
from discord.ext.commands import Context

from api.exceptions import (
    ChuniNetException,
    InvalidTokenException,
    MaintenanceException,
)

if TYPE_CHECKING:
    from discord.ext.commands.errors import CommandInvokeError

    from bot import ChuniBot


class EventsCog(commands.Cog, name="Events"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: "CommandInvokeError"):
        if isinstance(error, commands.CommandNotFound):
            return

        exc = error.original
        if isinstance(exc, MaintenanceException):
            return await ctx.reply(
                "CHUNITHM-NET is currently undergoing maintenance. Please try again later.",
                mention_author=False,
            )
        elif isinstance(exc, InvalidTokenException):
            return await ctx.reply(
                f"Your CHUNITHM-NET cookie is invalid. Please use `c>login` in DMs to log in.\nDetailed error: {error.original}",
                mention_author=False,
            )
        elif isinstance(exc, ChuniNetException):
            return await ctx.reply(
                "An error occurred while communicating with CHUNITHM-NET. Please try again later (or re-login).",
                mention_author=False,
            )
        elif isinstance(exc, commands.errors.ExpectedClosingQuoteError):
            return await ctx.reply(
                "You're missing a quote somewhere. Perhaps you're using the wrong kind of quote (`\"` vs `”`)?",
                mention_author=False,
            )
        elif isinstance(exc, commands.errors.CheckFailure) and ctx.command and ctx.command.name == "bu":
            return await ctx.reply(f"đm {ctx.author.mention}", mention_author=False)
        elif (
            isinstance(exc, commands.BadArgument)
            or isinstance(exc, commands.BadUnionArgument)
            or isinstance(exc, commands.MissingRequiredArgument)
            or isinstance(exc, commands.MissingPermissions)
            or isinstance(exc, commands.BotMissingPermissions)
            or isinstance(exc, commands.MaxConcurrencyReached)
            or isinstance(exc, commands.NoPrivateMessage)
            or isinstance(exc, commands.PrivateMessageOnly)
        ):
            await ctx.reply(str(error), mention_author=False)
        else:
            await ctx.reply(
                f"An error occurred while executing the command.",
                mention_author=False,
            )
            logging.getLogger("discord").error(
                "Exception in command %s", ctx.command, exc_info=exc
            )
            if webhook_url := self.bot.cfg.get("ERROR_REPORTING_WEBHOOK"):
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


async def setup(bot: "ChuniBot"):
    await bot.add_cog(EventsCog(bot))
