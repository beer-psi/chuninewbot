from asyncio import TimeoutError
from secrets import SystemRandom
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
        self.random = SystemRandom()

    @commands.hybrid_command(
        name="logout",
        description="Logs you out of the bot.",
    )
    async def logout(self, ctx: Context):
        async with self.bot.db.execute(
            "DELETE FROM cookies WHERE discord_id = ?", (ctx.author.id,)
        ):
            await self.bot.db.commit()
        await ctx.reply("Successfully logged out.", mention_author=False)

    async def _verify_and_login(self, id: int, clal: str) -> Optional[Exception]:
        if clal.startswith("clal="):
            clal = clal[5:]

        async with ChuniNet(clal) as client:
            try:
                await client.validate_cookie()
                async with self.bot.db.execute(
                    "INSERT INTO cookies VALUES (?, ?) ON CONFLICT(discord_id) DO UPDATE SET cookie=excluded.cookie",
                    (id, clal),
                ):
                    await self.bot.db.commit()
                return
            except Exception as e:
                return e

    @commands.hybrid_command("login")
    async def login(self, ctx: Context, clal: Optional[str] = None):
        """Link with your CHUNITHM-NET account.

        Parameters
        ----------
        clal: str
            The `clal` cookie from CHUNITHM-NET. Run this command without arguments to get instructions.
        """

        channel = ctx.channel

        if not isinstance(ctx.channel, discord.channel.DMChannel):
            please_delete_message = ""
            if clal is not None:
                try:
                    await ctx.message.delete()
                except discord.errors.Forbidden:
                    please_delete_message = "Please delete the original command, as people can use the cookie to access your CHUNITHM-NET profile."

            channel = (
                ctx.author.dm_channel
                if ctx.author.dm_channel
                else await ctx.author.create_dm()
            )

            await ctx.send(
                f"Login instructions have been sent to your DMs. {please_delete_message}"
                "(please **enable Privacy Settings -> Direct Messages** if you haven't received it.)"
            )

        if clal is not None:
            if (e := await self._verify_and_login(ctx.author.id, clal)) is None:
                return await channel.send("Successfully logged in.")
            else:
                raise commands.BadArgument(f"Invalid cookie: {e}")

        passcode = str(self.random.randrange(1000, 10000))
        embed = discord.Embed(
            title="How to login",
            description=(
                "Log in to your account on [CHUNITHM-NET](https://chunthm-net-eng.com).\n"
                "**Please do so in an incognito window!** Not doing so may cause the account to be logged out unexpectedly.\n"
                "\n"
                f"Then enter [this webpage](https://lng-tgk-aime-gw.am-all.net/common_auth/?otp={passcode}). You should see a `Not Found` error.\n"
                "Open developer tools (Ctrl + Shift + I or F12) and paste this into the console:\n"
                "```js\n"
                "(function(d){c=(n)=>Object.fromEntries(d.cookie.split(';').map(c=>c.split('=')))[n];confirm(`Paste this in the bot's DMs:\\nc>login ${c('clal')}\\nPress OK to copy.`)&&navigator.clipboard.writeText(`c>login ${c('clal')}`)})(document)\n"
                "```\n"
                "(This cookie cannot access your Aime account! It can only be used to login to CHUNITHM-NET.)\n"
                f"In case the website asks for a passcode, type {passcode} and select OK.\n"
            ),
        )
        if ctx.channel == channel:
            msg = await ctx.reply(embed=embed, mention_author=False)
        else:
            msg = await channel.send(embed=embed)

        def check(otp: str, _: str):
            return otp == passcode

        try:
            _, clal = await self.bot.wait_for(
                "chunithm_login", check=check, timeout=120
            )
            if (e := await self._verify_and_login(ctx.author.id, clal)) is None:  # type: ignore
                await msg.edit(
                    embed=discord.Embed(
                        title="Successfully logged in",
                        description="You can now use the bot's CHUNITHM-NET commands.",
                    )
                )
            else:
                await msg.edit(
                    embed=discord.Embed(
                        title="Failed to login",
                        description=f"Invalid cookie: {e}",
                    )
                )
        except TimeoutError:
            await msg.edit(
                embed=discord.Embed(
                    title="Login session timed out",
                    description="Please use `c>login` to restart the login process.",
                )
            )


async def setup(bot: ChuniBot) -> None:
    await bot.add_cog(AuthCog(bot))
