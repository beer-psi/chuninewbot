from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context

from api import ChuniNet
from bot import ChuniBot
from cogs.botutils import UtilsCog


class AuthCog(commands.Cog, name="Auth"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = self.bot.get_cog("Utils")  # type: ignore

    @commands.hybrid_command(
        name="logout",
        description="Logs you out of the bot.",
    )
    async def logout(self, ctx: Context):
        async with self.bot.db.execute(
            "DELETE FROM cookies WHERE discord_id = ?", (ctx.author.id,)
        ):
            await self.bot.db.commit()
        self.utils.fetch_cookie.cache_invalidate(self.utils, ctx.author.id)
        await ctx.reply("Successfully logged out.", mention_author=False)

    @commands.hybrid_command("login")
    async def login(self, ctx: Context, clal: Optional[str] = None):
        """Link with your CHUNITHM-NET account.
        
        Parameters
        ----------
        clal: str
            The `clal` cookie from CHUNITHM-NET. Run this command without arguments to get instructions.
        """

        if not isinstance(ctx.channel, discord.channel.DMChannel):
            please_delete_message = ""
            if clal is not None:
                try:
                    await ctx.message.delete()
                except discord.errors.Forbidden:
                    please_delete_message = " Please also delete your message, as people can use the cookie to access your CHUNITHM-NET."

            raise commands.PrivateMessageOnly(
                "This command can only be used in private messages."
                + please_delete_message
            )

        if clal is None:
            embed = discord.Embed(
                title="How to login",
                description=(
                    "**Step 1**\n"
                    "Log in to your account on [CHUNITHM-NET](https://chunthm-net-eng.com).\n"
                    "**Please do so in an incognito window!** Not doing so may cause the account to be logged out unexpectedly.\n"
                    "\n"
                    "Then enter [this webpage](https://lng-tgk-aime-gw.am-all.net/common_auth/). You should see a `Not Found` error.\n"
                    "Open developer tools (Ctrl + Shift + I or F12) and paste this into the console:\n"
                    "```js\n"
                    "(function(d){c=(n)=>Object.fromEntries(d.cookie.split(';').map(c=>c.split('=')))[n];confirm(`Paste this in the bot's DMs:\\nc>login ${c('clal')}\\nPress OK to copy.`)&&navigator.clipboard.writeText(`c>login ${c('clal')}`)})(document)\n"
                    "```\n"
                    "(This cookie cannot access your Aime account! It can only be used to login to CHUNITHM-NET.)\n\n"
                    "**Step 2**\n"
                    "Send `c>login <cookie>` without the angled brackets.\n"
                    "\n"
                    "If the cookie is undefined, or if there is extra data after `;`, please logout then login and try again.\n"
                ),
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if clal.startswith("clal="):
            clal = clal[5:]

        async with ChuniNet(clal) as client:
            try:
                await client.validate_cookie()
                async with self.bot.db.execute(
                    "INSERT INTO cookies VALUES (?, ?) ON CONFLICT(discord_id) DO UPDATE SET cookie=excluded.cookie",
                    (ctx.author.id, clal),
                ):
                    await self.bot.db.commit()
                await ctx.send("Successfully logged in.")
            except Exception as e:
                raise commands.BadArgument(f"Invalid cookie: {e}")


async def setup(bot: ChuniBot) -> None:
    await bot.add_cog(AuthCog(bot))
