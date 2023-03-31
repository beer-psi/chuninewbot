from discord.ext import commands
from discord.ext.commands import Context

from bot import ChuniBot
from utils.rating_calculator import calculate_rating
from views.songlist import SonglistView

from .botutils import UtilsCog


class MiscCog(commands.Cog, name="Miscellaneous"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = self.bot.get_cog("Utils")  # type: ignore

    @commands.command("calculate", aliases=["calc"])
    async def calc(self, ctx: Context, score: int, chart_constant: float):
        """Calculate rating from score and chart constant."""

        if not 0 <= score <= 1010000:
            await ctx.reply(
                "Score must be between 0 and 1010000.", mention_author=False
            )
            return

        rating = calculate_rating(score, chart_constant)
        await ctx.reply(f"Calculation result: {rating:.2f}", mention_author=False)

    @commands.command("find")
    async def find(self, ctx: Context, query: float):
        """Find charts by chart constant."""

        cursor = await self.bot.db.execute(
            "SELECT song_id, difficulty FROM chunirec_charts WHERE const = ?", (query,)
        )
        charts = await cursor.fetchall()
        if not charts:
            await ctx.reply("No charts found.", mention_author=False)
            return

        # title and difficulty
        results: list[tuple[str, str]] = []
        for chart in charts:
            song_id = chart[0]
            cursor = await self.bot.db.execute(
                "SELECT title from chunirec_songs WHERE id = ?", (song_id,)
            )
            title = await cursor.fetchone()
            if title is None:
                continue
            results.append((title[0], chart[1]))

        print(results)
        view = SonglistView(results)
        view.message = await ctx.reply(
            embed=view.format_songlist(view.items[: view.per_page]),
            view=view,
            mention_author=False,
        )


async def setup(bot: ChuniBot) -> None:
    await bot.add_cog(MiscCog(bot))
