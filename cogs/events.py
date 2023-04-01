import logging

from discord.ext import commands
from discord.ext.commands import Context

from api.exceptions import ChuniNetException
from bot import ChuniBot


class EventsCog(commands.Cog, name="Events"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif (
            isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MaxConcurrencyReached)
            or isinstance(error, commands.NoPrivateMessage)
            or isinstance(error, commands.PrivateMessageOnly)
            or isinstance(error, ChuniNetException)
        ):
            await ctx.send(str(error), mention_author=False, delete_after=5)
        else:
            await ctx.send(
                "An error occurred while executing the command.",
                mention_author=False,
                delete_after=5,
            )
            logging.getLogger("discord").error(
                "Exception in command %s", ctx.command, exc_info=error
            )


async def setup(bot: ChuniBot):
    await bot.add_cog(EventsCog(bot))
