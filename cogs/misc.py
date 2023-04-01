from urllib.parse import quote

import discord
from discord.ext import commands
from discord.ext.commands import Context

from bot import ChuniBot
from api.enums import Difficulty
from utils.rating_calculator import calculate_rating
from views.songlist import SonglistView

from cogs.botutils import UtilsCog


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

        view = SonglistView(results)
        view.message = await ctx.reply(
            embed=view.format_songlist(view.items[: view.per_page]),
            view=view,
            mention_author=False,
        )

    @commands.command("random")
    async def random(self, ctx: Context, level: str, count: int = 3):
        """Get random charts based on level."""

        async with ctx.typing():
            if count > 4 or count < 1:
                raise commands.BadArgument("Number of songs must be between 1 and 4.")

            try:
                query_level = float(level.replace("+", ".5"))
            except:
                raise commands.BadArgument("Invalid level provided.")

            cursor = await self.bot.db.execute(
                "SELECT song_id, difficulty, level, const, maxcombo, is_const_unknown FROM chunirec_charts WHERE level = ? OR const = ? ORDER BY random() LIMIT ?",
                (query_level, query_level, count),
            )
            charts = await cursor.fetchall()
            if not charts:
                await ctx.reply("No charts found.", mention_author=False)
                return

            embeds: list[discord.Embed] = []
            for chart in charts:
                difficulty = Difficulty.from_short_form(chart[1])
                level = str(chart[2]).replace(".5", "+").replace(".0", "")
                cursor = await self.bot.db.execute(
                    "SELECT title, genre, artist, jacket FROM chunirec_songs WHERE id = ?",
                    (chart[0],),
                )
                song = await cursor.fetchone()
                if song is None:
                    continue

                embeds.append(
                    discord.Embed(
                        title=song[0],
                        description=song[2],
                        color=difficulty.color(),
                    )
                    .set_thumbnail(
                        url=f"https://chunithm-net-eng.com/mobile/img/{song[3]}"
                    )
                    .add_field(name="Category", value=song[1])
                    .add_field(
                        name=str(difficulty),
                        value=f"[{level}{f' ({chart[3]})' if not chart[5] else ''}](https://www.youtube.com/results?search_query={quote(f'CHUNITHM {song[0]} {difficulty}')})",
                    )
                )
            await ctx.reply(embeds=embeds, mention_author=False)


async def setup(bot: ChuniBot) -> None:
    await bot.add_cog(MiscCog(bot))
