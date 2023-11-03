from typing import TYPE_CHECKING, Self

from discord.ext import commands
from discord.ext.commands import Context

from mithra_tercera.db.models import Cookie

if TYPE_CHECKING:
    from mithra_tercera import MithraTercera


class AuthenticationCog(commands.Cog, name="Authentication"):
    def __init__(self: Self, bot: "MithraTercera") -> None:
        self.bot = bot

    @commands.hybrid_command(name="logout")
    async def logout(self: Self, ctx: Context, *, invalidate: bool = False) -> None:
        """Logs you out of the bot.

        Parameters
        ----------
        invalidate: bool
            Signs out from CHUNITHM-NET, making the token unusable.
        """
        msg = "Successfully logged out."

        async with ctx.typing():
            rows_deleted = await Cookie.filter(user_id=ctx.author.id).delete()
            if rows_deleted == 0:
                msg = "You were not logged in. Logged you out anyways, just in case."

        await ctx.reply(msg, mention_author=False)
