from typing import TYPE_CHECKING

from discord.ext import commands
from discord.ext.commands import Context

if TYPE_CHECKING:
    from bot import ChuniBot


class FluffCog(commands.Cog, name="Fluff"):
    def __init__(self) -> None:
        super().__init__()

    @commands.command("unny")
    async def cunny(self, ctx: Context):
        """😭"""

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
            "https://cdn.discordapp.com/attachments/1041530799704526961/1110813221008441375/uohhhroll.gif",
            mention_author=False,
        )

    @commands.command("bu")
    async def bu(self, ctx: Context):
        """🛐"""

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
            "https://cdn.discordapp.com/emojis/1093540495818502164.gif",
            mention_author=False,
        )


async def setup(bot: "ChuniBot"):
    await bot.add_cog(FluffCog())
