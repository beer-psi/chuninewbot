import asyncio

import discord
from discord.ext import commands
from discord.ext.commands import Context

from api import ChuniNet
from api.enums import Difficulty
from bot import ChuniBot
from views.b30 import B30View
from views.recent import RecentRecordsView

from .botutils import UtilsCog


class RecordsCog(commands.Cog, name="Records"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = self.bot.get_cog("Utils")  # type: ignore

    @commands.command(name="recent", aliases=["rs"])
    async def recent(self, ctx: Context):
        """View your recent scores."""

        async with ctx.typing():
            clal = await self.utils.login_check(ctx)

            client = ChuniNet(clal)
            recent_scores = await client.recent_record()

            tasks = [self.utils.annotate_song(score) for score in recent_scores]
            recent_scores = await asyncio.gather(*tasks)

            view = RecentRecordsView(self.bot, recent_scores, client)
            view.message = await ctx.reply(
                embeds=view.format_score_page(view.items[0]),
                view=view,
                mention_author=False,
            )

    @commands.command("compare", aliases=["c"])
    async def compare(self, ctx: Context):
        """Compare your best score with the most recently posted score."""

        async with ctx.typing():
            clal = await self.utils.login_check(ctx)

            bot_messages = [
                message
                async for message in ctx.channel.history(limit=50)
                if message.author.id == self.bot.user.id
                and len(message.embeds) == 1
                and "Score of" in message.content
                and message.embeds[0].thumbnail.url is not None
                and "https://chunithm-net-eng.com/mobile/img/"
                in message.embeds[0].thumbnail.url
            ]
            if len(bot_messages) == 0:
                await ctx.reply("No recent scores found.", mention_author=False)
                return

            embed = bot_messages[0].embeds[0]
            thumbnail_filename = embed.thumbnail.url.split("/")[-1]
            difficulty = Difficulty.from_embed_color(embed.color.value)

            cursor = await self.bot.db.execute(
                "SELECT chunithm_id FROM chunirec_songs WHERE jacket = ?",
                (thumbnail_filename,),
            )
            song_id = await cursor.fetchone()
            if song_id is None:
                await ctx.reply("No song found.", mention_author=False)
                return

            song_id = song_id[0]

            async with ChuniNet(clal) as client:
                await client.authenticate()
                records = await client.music_record(song_id)

            if len(records) == 0:
                await ctx.reply(
                    "No scores found for this player.", mention_author=False
                )
                return

            records = [record for record in records if record.difficulty == difficulty]
            if len(records) == 0:
                await ctx.reply(
                    "No scores found on selected difficulty.", mention_author=False
                )
                return
            score = records[0]
            score = await self.utils.annotate_song(score)

            embed = (
                discord.Embed(
                    description=(
                        f"**{score.title}** [{score.difficulty} {score.internal_level if not score.unknown_const else score.level}]\n\n"
                        f"▸ {score.rank} ▸ {score.clear} ▸ {score.score}"
                    )
                )
                .set_author(
                    icon_url=ctx.author.display_avatar.url,
                    name=f"Top play for {ctx.author.display_name}",
                )
                .set_thumbnail(url=embed.thumbnail.url)
            )
            if score.play_rating is not None:
                embed.set_footer(
                    text=f"Play rating {score.play_rating:.2f}  •  {score.play_count} attempts"
                )

            await ctx.reply(
                embed=embed,
                mention_author=False,
            )

    @commands.command("best30", aliases=["b30"])
    async def best30(self, ctx: Context):
        """View top plays"""

        async with ctx.typing():
            clal = await self.utils.login_check(ctx)

            async with ChuniNet(clal) as client:
                best30 = await client.best30()
            
            tasks = [self.utils.annotate_song(score) for score in best30]
            best30 = await asyncio.gather(*tasks)


            view = B30View(best30)
            view.message = await ctx.reply(
                content=view.format_content(),
                embed=view.format_page(view.items[:view.per_page]),
                view=view,
                mention_author=False,
            )
    
    @commands.command("recent10", aliases=["r10"])
    async def recent10(self, ctx: Context):
        """View top recent plays"""

        async with ctx.typing():
            clal = await self.utils.login_check(ctx)

            async with ChuniNet(clal) as client:
                recent10 = await client.recent10()
            
            tasks = [self.utils.annotate_song(score) for score in recent10]
            recent10 = await asyncio.gather(*tasks)


            view = B30View(recent10)
            view.message = await ctx.reply(
                content=view.format_content(),
                embed=view.format_page(view.items[:view.per_page]),
                mention_author=False,
            )


async def setup(bot: ChuniBot):
    await bot.add_cog(RecordsCog(bot))
