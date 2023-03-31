import asyncio

import discord
from discord.ext import commands
from discord.ext.commands import Context

from api import ChuniNet
from bot import ChuniBot
from views.recent import RecentRecordsView

from .botutils import UtilsCog


class CommandsCog(commands.Cog, name="Commands"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = self.bot.get_cog("Utils")  # type: ignore

    @commands.command("login")
    async def login(self, ctx: Context, clal: str):
        if not isinstance(ctx.channel, discord.channel.DMChannel):
            await ctx.send("Please use this command in a DM.")
            try:
                await ctx.message.delete()
            except discord.errors.Forbidden:
                pass
            return

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

    @commands.command(name="chunithm", aliases=["chuni"])
    async def chunithm(self, ctx: Context):
        async with ctx.typing():
            clal = await self.utils.fetch_cookie(ctx.author.id)
            if clal is None:
                await ctx.send(
                    "You are not logged in. Please use `!login <cookie>` in DMs to log in."
                )
                return

            async with ChuniNet(clal) as client:
                player_data = await client.player_data()

                description = (
                    f"▸ **Level**: {player_data.lv}\n"
                    f"▸ **Rating**: {player_data.rating.current}\n"
                    f"▸ **Peak Rating**: {player_data.rating.max}\n"
                    f"▸ **OVER POWER**: {player_data.overpower.value} ({player_data.overpower.progress * 100:.2f}%)\n"
                    f"▸ **Playcount**: {player_data.playcount}\n"
                )

                embed = (
                    discord.Embed(description=description)
                    .set_author(name=f"CHUNITHM profile for {player_data.name}")
                    .set_thumbnail(url=player_data.avatar)
                    .set_footer(
                        text=f"Last played on {player_data.last_play_date.strftime('%Y-%m-%d')}"
                    )
                )

                await ctx.send(embed=embed)

    @commands.command(name="recent", aliases=["rs"])
    async def recent(self, ctx: Context):
        async with ctx.typing():
            clal = await self.utils.fetch_cookie(ctx.author.id)
            if clal is None:
                await ctx.send(
                    "You are not logged in. Please use `!login <cookie>` in DMs to log in."
                )
                return

            client = ChuniNet(clal)
            recent_scores = await client.recent_record()

            tasks = [self.utils.annotate_song(score) for score in recent_scores]
            await asyncio.gather(*tasks)
            
            view = RecentRecordsView(self.bot, recent_scores, client)
            view.message = await ctx.send(embeds=view.format_score_page(view.scores[0]), view=view)


async def setup(bot: ChuniBot):
    await bot.add_cog(CommandsCog(bot))
