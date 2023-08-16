import itertools
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Sequence

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from sqlalchemy import select, text
from sqlalchemy.orm import joinedload

from chunithm_net.entities.enums import Rank
from database.models import Chart
from utils import did_you_mean_text, floor_to_ndp, round_to_nearest
from utils.calculation.overpower import (
    calculate_overpower_base,
    calculate_overpower_max,
)
from utils.calculation.rating import calculate_rating, calculate_score_for_rating
from utils.components import ChartCardEmbed

if TYPE_CHECKING:
    from bot import ChuniBot
    from cogs.botutils import UtilsCog
    from cogs.search import SearchCog


class ToolsCog(commands.Cog, name="Tools"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot
        self.utils: "UtilsCog" = self.bot.get_cog("Utils")  # type: ignore[reportGeneralTypeIssues]
        self.search_cog: "SearchCog" = self.bot.get_cog("Search")  # type: ignore[reportGeneralTypeIssues]

    @commands.hybrid_command("calculate", aliases=["calc"])
    async def calculate(
        self, ctx: Context, score: int, chart_constant: Optional[float] = None
    ):
        """Calculate rating and over power from score and chart constant.

        Parameters
        ----------
        score: int
            The score to calculate play rating and over power from
        chart_constant: float
            Chart constant of the chart. Use the `info` command to find this.
        """

        if not 0 <= score <= 1010000:
            msg = "Score must be between 0 and 1010000."
            raise commands.BadArgument(msg)

        if chart_constant is not None and chart_constant <= 0:
            msg = "Chart constant must be greater than 0."
            raise commands.BadArgument(msg)

        if chart_constant is None:
            rating = calculate_rating(score, 0)
        else:
            rating = calculate_rating(score, chart_constant)

        sign = ""
        if chart_constant is None and rating > 0:
            sign = "+"

        res = f"Rating: {sign}{floor_to_ndp(rating, 2)}"
        if chart_constant is not None:
            overpower_max = calculate_overpower_max(chart_constant)
            if score == 1010000:
                res += f"\nOVER POWER: {floor_to_ndp(overpower_max, 2)} / {floor_to_ndp(overpower_max, 2)} (100.00%)"
            elif score < 500000:
                res += f"\nOVER POWER: 0.00 / {floor_to_ndp(overpower_max, 2)} (0.00%)"
            else:
                overpower_base = calculate_overpower_base(score, chart_constant)
                res += "\nOVER POWER:"
                if score >= 1000000:
                    overpower = overpower_base + Decimal(1)
                    res += f"\n• AJ: {floor_to_ndp(overpower, 2)} / {floor_to_ndp(overpower_max, 2)} ({floor_to_ndp(overpower / overpower_max * 100, 2)}%)"
                overpower = overpower_base + Decimal(0.5)
                res += f"\n• FC: {floor_to_ndp(overpower, 2)} / {floor_to_ndp(overpower_max, 2)} ({floor_to_ndp(overpower / overpower_max * 100, 2)}%)"
                res += f"\n• Non-FC: {floor_to_ndp(overpower_base, 2)} / {floor_to_ndp(overpower_max, 2)} ({floor_to_ndp(overpower_base / overpower_max * 100, 2)}%)"

        await ctx.reply(res, mention_author=False)

    @commands.hybrid_command("const", aliases=["constant"])
    async def const(self, ctx: Context, chart_constant: float, mode: str = "default"):
        """Calculate rating and over power achieved with various scores based on chart constant.

        Parameters
        ----------
        chart_constant: float
            Chart constant of the chart. Use the `info` command to find this.
        mode: str
            Sets the display mode: `default` (Display rating information only) / `AJ` (Display OP information for ALL JUSTICE only)
        """

        if chart_constant < 1 or chart_constant > 16:
            msg = "Chart constant must be between 1.0 and 16.0"
            raise commands.BadArgument(msg)

        mode = mode.lower()
        if mode == "aj":
            separator = "-------------------------"
            res = f"```  Score |         OP (AJ)\n{separator}"
            scores = [1009950]
            scores.extend(
                itertools.chain(
                    range(1009900, 1009450, -50),  # 1009500..=1009900
                    range(1009400, 1008900, -100),  # 1009000..=1009400
                )
            )
        else:
            separator = "---------------"
            res = f"```  Score |  Rate\n{separator}"
            scores = [1009900]
            scores.extend(
                itertools.chain(
                    range(1009500, 1004500, -500),  # 1005000..=1009900
                    range(1004000, 999000, -1000),  # 1000000..=1004000
                    range(997500, 972500, -2500),  # 975000..=997500
                    range(970000, 940000, -10000),  # 950000..=970000
                    range(925000, 875000, -25000),  # 900000..=925000
                )
            )
        overpower_max = calculate_overpower_max(chart_constant)
        if mode == "aj":
            rating = calculate_rating(1010000, chart_constant)
            res += f"\n1010000 | {overpower_max:>5.2f} = 100.00%"

        for score in scores:
            rating = calculate_rating(score, chart_constant)
            overpower_base = calculate_overpower_base(score, chart_constant)
            if score >= Rank.SS.min_score:
                overpower = overpower_base + Decimal(1)
                overpower_aj = f"{floor_to_ndp(overpower / overpower_max * 100, 2)}%"
            else:
                overpower_aj = "     -"

            if rating > 0:
                res += "\n"
                if mode == "aj":
                    # AJ means scores are above 1m => overpower is defined
                    res += f"{score:>7} | {overpower:>5.2f} = {overpower_aj:>7}"  # type: ignore[reportUnboundVariable]
                else:
                    res += f"{score:>7} | {floor_to_ndp(rating, 2):>5.2f}"
                    if (
                        score == Rank.SSS.min_score
                        or score == Rank.SSp.min_score
                        or score == Rank.SS.min_score
                        or score == Rank.Sp.min_score
                        or score == Rank.S.min_score
                    ):
                        res += f"\n{separator}"

        res += "```"

        await ctx.reply(res, mention_author=False)

    @commands.hybrid_command("rating")
    async def rating(self, ctx: Context, rating: float):
        """Calculate score required to achieve the specified play rating.

        Parameters
        ----------
        rating: float
            Play rating you want to achieve
        """

        if not 1 <= rating <= 17.55:
            msg = "Play rating must be between 1.00 and 17.55."
            raise commands.BadArgument(msg)

        res = "```Const |   Score\n---------------"
        chart_constant = floor_to_ndp(rating - 3, 0)
        if chart_constant < 1:
            chart_constant = 1
        while chart_constant <= rating and chart_constant <= 15.4:
            required_score = calculate_score_for_rating(rating, chart_constant)
            if required_score is not None and required_score >= Rank.S.min_score:
                res += (
                    f"\n {chart_constant:>4.1f} | {floor_to_ndp(required_score, 0):>7}"
                )
            if chart_constant >= 10:
                chart_constant += 0.1
            elif chart_constant >= 7:
                chart_constant += 0.5
            else:
                chart_constant += 1
        res += "```"

        await ctx.reply(res, mention_author=False)

    @commands.hybrid_command("random")
    async def random(self, ctx: Context, level: str, count: int = 3):
        """Get random charts based on level or chart constant.

        Parameters
        ----------
        level: str
            Level to search for. Can be level (13+) or chart constant (13.5).
        count: int
            Number of charts to return. Must be between 1 and 4.
        """

        async with ctx.typing(), self.bot.begin_db_session() as session:
            if count > 4 or count < 1:
                msg = "Number of songs must be between 1 and 4."
                raise commands.BadArgument(msg)

            # Check whether input is level or constant
            stmt = (
                select(Chart)
                .order_by(text("RANDOM()"))
                .limit(count)
                .options(joinedload(Chart.song), joinedload(Chart.sdvxin_chart_view))
            )
            try:
                if "." in level:
                    query_level = float(level)
                    stmt = stmt.where(Chart.const == query_level)
                else:
                    stmt = stmt.where(Chart.level == level)
            except ValueError:
                msg = "Please enter a valid level or chart constant."
                raise commands.BadArgument(msg) from None

            charts: Sequence[Chart] = (await session.execute(stmt)).scalars().all()

            if len(charts) == 0:
                await ctx.reply("No charts found.", mention_author=False)
                return

            embeds: list[discord.Embed] = [ChartCardEmbed(chart) for chart in charts]
            await ctx.reply(embeds=embeds, mention_author=False)

    @commands.hybrid_command("recommend")
    async def recommend(
        self, ctx: Context, count: int = 3, max_rating: Optional[float] = None
    ):
        """Get random chart recommendations with target scores based on your rating.

        Please note that recommended charts are generated randomly and are independent of your high scores.

        Parameters
        ----------
        count: int
            Number of charts to return. Must be between 1 and 4.
        max_rating: Optional[float]
            Your maximum rating. If not provided, your rating will be fetched from CHUNITHM-NET,
            assuming you're logged in.
        """

        async with ctx.typing(), self.bot.begin_db_session() as session:
            if count > 4 or count < 1:
                msg = "Number of songs must be between 1 and 4."
                raise commands.BadArgument(msg)

            if max_rating is None:
                async with self.utils.chuninet(ctx) as client:
                    basic_player_data = await client.authenticate()
                    max_rating = basic_player_data.rating.max

                    if max_rating is None:
                        msg = "No rating data found. Please play a song first."
                        raise commands.BadArgument(msg)

            # Determine min-max const to recommend based on user rating. Formula is intentionally confusing.
            min_level = max_rating * 1.05 - 3.05
            max_level = max_rating * 0.85 + 0.95
            if min_level < 7:
                min_level = 7
            if max_level < 14:
                max_level += (14 - max_level) * 0.2
            if max_level < min_level + 1:
                max_level = min_level + 1

            stmt = (
                select(Chart)
                .where((Chart.const >= min_level) & (Chart.const <= max_level))
                .order_by(text("RANDOM()"))
                .limit(count)
                .options(joinedload(Chart.song), joinedload(Chart.sdvxin_chart_view))
            )

            charts: Sequence[Chart] = (await session.execute(stmt)).scalars().all()
            if len(charts) == 0:
                await ctx.reply("No charts found.", mention_author=False)
                return

            embeds: list[discord.Embed] = []
            for chart in charts:
                assert chart.const is not None

                target_score = calculate_score_for_rating(max_rating, chart.const)
                if target_score is None:
                    target_score = 1_009_000
                elif 0 <= target_score < 1_000_000:
                    target_score = round_to_nearest(target_score, 5000)
                elif target_score < 1_006_000:
                    target_score = round_to_nearest(target_score, 2500)
                elif target_score < 1_008_500:
                    target_score = round_to_nearest(target_score, 1000)
                elif target_score < 1_009_000:
                    target_score = round_to_nearest(target_score, 500)

                embeds.append(ChartCardEmbed(chart, target_score=target_score))
            await ctx.reply(embeds=embeds, mention_author=False)

    async def song_title_autocomplete(
        self, _: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.search_cog.song_title_autocomplete(_, current)

    @commands.hybrid_command("border")
    @app_commands.autocomplete(query=song_title_autocomplete)
    async def border(self, ctx: Context, difficulty: str, *, query: str):
        """Display the number of permissible JUSTICE, ATTACK and MISS to achieve specific ranks on a chart.

        The values are based on realistic JUSTICE:ATTACK:MISS ratios and are for reference only.
        In terms of scoring, the score decrease from 1 ATTACK is equivalent to 51 JUSTICE, and 1 MISS is equivalent to 101 JUSTICE.

        Parameters
        ----------
        difficulty: str
            Chart difficulty to search for (BAS/ADV/EXP/MAS/ULT).
        query: str
            Song title to search for. You don't have to be exact; try things out!
        """

        async with ctx.typing(), self.bot.begin_db_session() as session:
            guild_id = ctx.guild.id if ctx.guild else None
            song, alias, similarity = await self.utils.find_song(
                query, guild_id=guild_id, worlds_end=False
            )
            if song is None or similarity < 0.9:
                return await ctx.reply(
                    did_you_mean_text(song, alias), mention_author=False
                )

            stmt = (
                select(Chart)
                .where(
                    (Chart.song == song) & (Chart.difficulty == difficulty[:3].upper())
                )
                .limit(1)
                .options(joinedload(Chart.song), joinedload(Chart.sdvxin_chart_view))
            )

            charts: Sequence[Chart] = (await session.execute(stmt)).scalars().all()
            if len(charts) == 0:
                await ctx.reply(
                    "No charts found. Make sure you specified a valid chart difficulty (BAS/ADV/EXP/MAS/ULT).",
                    mention_author=False,
                )
                return None

            embeds: list[discord.Embed] = [
                ChartCardEmbed(chart, border=True) for chart in charts
            ]

            await ctx.reply(embeds=embeds, mention_author=False)
            return None


async def setup(bot: "ChuniBot"):
    await bot.add_cog(ToolsCog(bot))
