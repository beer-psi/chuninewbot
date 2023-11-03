from typing import TYPE_CHECKING, Self

from discord.ext import commands
from discord.ext.commands import Context

from mithra_tercera.logger import create_log_ctx


if TYPE_CHECKING:
    from mithra_tercera import MithraTercera


logger = create_log_ctx(__name__)


class EventsCog(commands.Cog, name="Events"):
    def __init__(self: Self, bot: "MithraTercera") -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(  # noqa: PLR0911
        self: Self,
        ctx: Context,
        error: commands.errors.CommandInvokeError,
    ) -> None:
        if isinstance(error, commands.CommandNotFound):
            return

        exc = error
        while hasattr(exc, "original"):
            exc = exc.original  # type: ignore[reportGeneralTypeIssues]

        if isinstance(exc, commands.errors.CommandOnCooldown):
            await ctx.reply(
                f"You're too fast. Take a break for {exc.retry_after:.2f} seconds.",
                mention_author=False,
                delete_after=exc.retry_after,
            )
            return
        if isinstance(exc, commands.errors.ExpectedClosingQuoteError):
            await ctx.reply(
                "You're missing a quote somewhere. Perhaps you're using the wrong kind of quote (`\"` vs `”`)?",
                mention_author=False,
            )
            return
        if isinstance(exc, commands.errors.UnexpectedQuoteError):
            await ctx.reply(
                (
                    f"Unexpected quote mark, {exc.quote!r}, in non-quoted string. If this was intentional, "
                    "escape the quote with a backslash (\\\\)."
                ),
                mention_author=False,
            )
            return
        if isinstance(
            exc, (commands.errors.NotOwner, commands.errors.MissingPermissions)
        ):
            await ctx.reply("Insufficient permissions.", mention_author=False)
            return
        if isinstance(exc, commands.BadLiteralArgument):
            to_string = [repr(x) for x in exc.literals]
            if len(to_string) > 2:  # noqa: PLR2004
                fmt = "{}, or {}".format(", ".join(to_string[:-1]), to_string[-1])
            else:
                fmt = " or ".join(to_string)
            await ctx.reply(
                f"`{exc.param.displayed_name or exc.param.name}` must be one of {fmt}, received {exc.argument!r}",
                mention_author=False,
            )
            return
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
            await ctx.reply(str(error), mention_author=False)
            return

        logger.error(f"Exception in command {ctx.command}", exc_info=exc)
        await ctx.reply(
            "Something really terrible happened. The owner has been notified.\n",
            mention_author=False,
        )


async def setup(bot: "MithraTercera") -> None:
    await bot.add_cog(EventsCog(bot))
