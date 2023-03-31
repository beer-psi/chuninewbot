import discord
from discord.ext import commands
from discord.ext.commands import Context

from api import ChuniNet
from bot import ChuniBot

from .botutils import UtilsCog


class AuthCog(commands.Cog, name="Auth"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = self.bot.get_cog("Utils")  # type: ignore

    @commands.command("logout")
    async def logout(self, ctx: Context):
        await self.bot.db.execute(
            "DELETE FROM cookies WHERE user_id = ?", (ctx.author.id,)
        )
        await self.bot.db.commit()
        self.utils.fetch_cookie.cache_invalidate(self.utils, ctx.author.id)
        await ctx.reply("Successfully logged out.", mention_author=False)

    @commands.command("login")
    async def login(self, ctx: Context, clal: str):
        if not isinstance(ctx.channel, discord.channel.DMChannel):
            await ctx.send("Please use this command in a DM.")
            try:
                await ctx.message.delete()
            except discord.errors.Forbidden:
                pass
            return

        if clal.startswith("clal="):
            clal = clal[5:]

        async with ChuniNet(clal) as client:
            try:
                await client.validate_cookie()
                await self.bot.db.execute(
                    "INSERT INTO cookies VALUES (?, ?)", (ctx.author.id, clal)
                )
                await self.bot.db.commit()
                await ctx.send("Successfully logged in.")
            except Exception as e:
                await ctx.send(f"Invalid cookie: {e}")
                return


async def setup(bot: ChuniBot) -> None:
    await bot.add_cog(AuthCog(bot))
