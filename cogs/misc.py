import subprocess
import sys
import time
from decimal import Decimal
from random import random
from typing import Optional, Sequence

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import escape_markdown, oauth_url
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from chunithm_net import ChuniNet
from chunithm_net.consts import JACKET_BASE
from chunithm_net.entities.enums import Difficulty
from bot import ChuniBot
from cogs.botutils import UtilsCog
from database.models import Chart, Prefix
from utils import floor_to_ndp, format_level, sdvxin_link, yt_search_link
from utils.calculation.overpower import (
    calculate_overpower_base,
    calculate_overpower_max,
)
from utils.calculation.rating import calculate_rating, calculate_score_for_rating
from utils.views.songlist import SonglistView


class MiscCog(commands.Cog, name="Miscellaneous"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = self.bot.get_cog("Utils")  # type: ignore

    @commands.command("treesync", hidden=True)
    @commands.is_owner()
    async def treesync(self, ctx: Context, guild_id: Optional[int] = None):
        """Syncs the slash command tree."""

        guild = discord.Object(id=guild_id) if guild_id is not None else None
        if guild is not None:
            self.bot.tree.copy_global_to(guild=guild)
        await self.bot.tree.sync(guild=guild)
        await ctx.message.add_reaction("✅")

    @commands.hybrid_command("source", aliases=["src"])
    async def source(self, ctx: Context):
        """Get the source code for this bot."""

        reply = (
            "https://tenor.com/view/metal-gear-rising-metal-gear-rising-revengeance-senator-armstrong-revengeance-i-made-it-the-fuck-up-gif-25029602"
            if random() < 0.1
            else "<https://github.com/beerpiss/chuninewbot>"
        )

        await ctx.reply(reply, mention_author=False)

    @commands.hybrid_command("invite")
    async def invite(self, ctx: Context):
        """Invite this bot to your server!"""

        permissions = discord.Permissions(
            read_messages=True,
            send_messages=True,
            send_messages_in_threads=True,
            manage_messages=True,
            read_message_history=True,
        )

        await ctx.reply(oauth_url(self.bot.user.id, permissions=permissions), mention_author=False)  # type: ignore

    @commands.hybrid_command("status")
    async def status(self, ctx: Context):
        """View the bot's status."""

        try:
            revision = (
                subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                .stdout.decode("utf-8")
                .replace("\n", "")
            )
        except FileNotFoundError:
            revision = "unknown"
        if not revision:
            revision = "unknown"

        summary = [
            f"chuninewbot revision `{revision}`",
            f"discord.py `{discord.__version__}`",
            f"Python `{sys.version}` on `{sys.platform}`",
            "",
            f"Online since <t:{int(self.bot.launch_time)}:R>",
            "",
            f"This bot can see {len(self.bot.guilds)} guild(s) and {len(self.bot.users)} user(s).",
            f"Average websocket latency: {round(self.bot.latency * 1000, 2)}ms",
        ]

        await ctx.reply("\n".join(summary), mention_author=False)

    @commands.hybrid_command("ping")
    async def ping(self, ctx: Context):
        start = time.perf_counter()
        message = await ctx.send("Ping...")
        end = time.perf_counter()
        duration = (end - start) * 1000
        await message.edit(
            content=(
                f"Pong! Took {duration:.2f}ms\n"
                f"Websocket latency: {round(self.bot.latency * 1000, 2)}ms"
            )
        )

    @commands.hybrid_command("calculate", aliases=["calc"])
    async def calc(
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
            raise commands.BadArgument("Score must be between 0 and 1010000.")

        if chart_constant is not None and chart_constant <= 0:
            raise commands.BadArgument("Chart constant must be greater than 0.")

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
                res += f"\nOVER POWER:"
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
            Set the display mode.
            ・`default` (Display rating information only)
            ・`full` (Display all information)
            ・`AJ` (Display OP information for ALL JUSTICE only)
        """

        if chart_constant < 1 or chart_constant > 16:
            raise commands.BadArgument("Chart constant must be between 1.0 and 16.0")

        mode = mode.lower()
        if mode == "full":
            separator = "----------------------------------------------"
            res = f"```  Score |  Rate |      OP | OP (FC) | OP (AJ)\n{separator}"
            scores = [
                1009900,
                1009500,
                1009000,
                1008500,
                1008000,
                1007500,
                1007000,
                1006500,
                1006000,
                1005500,
                1005000,
                1004000,
                1003000,
                1002000,
                1001000,
                1000000,
                997500,
                995000,
                992500,
                990000,
                987500,
                985000,
                982500,
                980000,
                977500,
                975000,
                970000,
                960000,
                950000,
                925000,
                900000,
            ]
        elif mode == "aj":
            separator = "-------------------------"
            res = f"```  Score |         OP (AJ)\n{separator}"
            scores = [
                1009950,
                1009900,
                1009850,
                1009800,
                1009750,
                1009700,
                1009650,
                1009600,
                1009550,
                1009500,
                1009400,
                1009300,
                1009200,
                1009100,
                1009000,
            ]
        else:
            separator = "---------------"
            res = f"```  Score |  Rate\n{separator}"
            scores = [
                1009000,
                1008500,
                1008000,
                1007500,
                1007000,
                1006500,
                1006000,
                1005500,
                1005000,
                1004000,
                1003000,
                1002000,
                1001000,
                1000000,
                997500,
                995000,
                992500,
                990000,
                987500,
                985000,
                982500,
                980000,
                977500,
                975000,
                970000,
                960000,
                950000,
                925000,
                900000,
            ]

        overpower_max = calculate_overpower_max(chart_constant)
        if mode == "full":
            rating = calculate_rating(1010000, chart_constant)
            res += f"\n1010000 | {floor_to_ndp(rating, 2):>5} |       - |       - | 100.00%"
        elif mode == "aj":
            rating = calculate_rating(1010000, chart_constant)
            res += f"\n1010000 | {overpower_max:>5.2f} = 100.00%"

        for score in scores:
            rating = calculate_rating(score, chart_constant)
            overpower_base = calculate_overpower_base(score, chart_constant)
            if score >= 1000000:
                overpower = overpower_base + Decimal(1)
                overpower_aj = f"{floor_to_ndp(overpower / overpower_max * 100, 2)}%"
            else:
                overpower_aj = "     -"

            if rating > 0:
                res += "\n"
                if mode == "full":
                    overpower = overpower_base + Decimal(0.5)
                    overpower_fc = (
                        f"{floor_to_ndp(overpower / overpower_max * 100, 2)}%"
                    )
                    overpower_non_fc = (
                        f"{floor_to_ndp(overpower_base / overpower_max * 100, 2)}%"
                    )
                    res += f"{score:>7} | {floor_to_ndp(rating, 2):>5.2f} | {overpower_non_fc:>7} | {overpower_fc:>7} | {overpower_aj:>7}"
                    if (
                        score == 1009000
                        or score == 1007500
                        or score == 1005000
                        or score == 1000000
                        or score == 990000
                        or score == 975000
                    ):
                        res += f"\n{separator}"
                elif mode == "aj":
                    # AJ means scores are above 1m => overpower is defined
                    res += f"{score:>7} | {overpower:>5.2f} = {overpower_aj:>7}"  # type: ignore[reportUnboundVariable]
                else:
                    res += f"{score:>7} | {floor_to_ndp(rating, 2):>5.2f}"
                    if (
                        score == 1007500
                        or score == 1005000
                        or score == 1000000
                        or score == 990000
                        or score == 975000
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
            raise commands.BadArgument("Play rating must be between 1.00 and 17.55.")

        res = "```Const |   Score\n---------------"
        chart_constant = floor_to_ndp(rating - 3, 0)
        if chart_constant < 1:
            chart_constant = 1
        while chart_constant <= rating and chart_constant <= 15.4:
            required_score = calculate_score_for_rating(rating, chart_constant)
            if required_score >= 975000:
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

    @commands.hybrid_command("find")
    async def find(self, ctx: Context, level: str):
        """Find charts by level or chart constant.

        Parameters
        ----------
        query: float
            Chart constant to search for.
        """

        stmt = select(Chart).options(
            joinedload(Chart.song), joinedload(Chart.sdvxin_chart_view)
        )
        try:
            if "." in level:
                query_level = float(level)
                stmt = stmt.where(Chart.const == query_level)
            else:
                query_level = float(level.replace("+", ".5"))
                stmt = stmt.where(Chart.level == query_level)
        except ValueError:
            raise commands.BadArgument("Please enter a valid level or chart constant.")

        async with ctx.typing(), self.bot.begin_db_session() as session:
            charts: Sequence[Chart] = (await session.execute(stmt)).scalars().all()

            if len(charts) == 0:
                await ctx.reply("No charts found.", mention_author=False)
                return

            results: list[tuple[str, str, str | None]] = []
            for chart in charts:
                results.append(
                    (
                        chart.song.title,
                        chart.difficulty,
                        chart.sdvxin_chart_view.id if chart.sdvxin_chart_view else None,
                    )
                )

            view = SonglistView(ctx, results)
            view.message = await ctx.reply(
                embed=view.format_songlist(view.items[: view.per_page]),
                view=view,
                mention_author=False,
            )

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
                raise commands.BadArgument("Number of songs must be between 1 and 4.")

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
                    query_level = float(level.replace("+", ".5"))
                    stmt = stmt.where(Chart.level == query_level)
            except ValueError:
                raise commands.BadArgument(
                    "Please enter a valid level or chart constant."
                )

            charts: Sequence[Chart] = (await session.execute(stmt)).scalars().all()

            if len(charts) == 0:
                await ctx.reply("No charts found.", mention_author=False)
                return

            embeds: list[discord.Embed] = []
            for chart in charts:
                difficulty = Difficulty.from_short_form(chart.difficulty)
                chart_level = format_level(chart.level)

                if chart.sdvxin_chart_view is not None:
                    url = sdvxin_link(
                        chart.sdvxin_chart_view.id, difficulty.short_form()
                    )
                else:
                    url = yt_search_link(chart.song.title, difficulty.short_form())

                embeds.append(
                    discord.Embed(
                        title=escape_markdown(chart.song.title),
                        description=escape_markdown(chart.song.artist),
                        color=difficulty.color(),
                    )
                    .set_thumbnail(url=f"{JACKET_BASE}/{chart.song.jacket}")
                    .add_field(name="Category", value=chart.song.genre)
                    .add_field(
                        name=str(difficulty),
                        value=f"[{chart_level}{f' ({chart.const})' if not chart.is_const_unknown else ''}]({url})",
                    )
                )
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
                raise commands.BadArgument("Number of songs must be between 1 and 4.")

            if max_rating is None:
                clal = await self.utils.login_check(ctx)
                async with ChuniNet(clal) as client:
                    player_data = await client.player_data()
                    max_rating = player_data.rating.max

                    if max_rating is None:
                        raise commands.BadArgument(
                            "No rating data found. Please play a song first."
                        )

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
                difficulty = Difficulty.from_short_form(chart.difficulty)
                chart_level = format_level(chart.level)
                rating_diff = max_rating - chart.const

                # if-else intentionally used to ensure State-of-the-Art Shitcode compliance
                if rating_diff < 0.10:
                    target_score = 975_000
                elif rating_diff < 0.30:
                    target_score = 980_000
                elif rating_diff < 0.50:
                    target_score = 985_000
                elif rating_diff < 0.70:
                    target_score = 990_000
                elif rating_diff < 0.90:
                    target_score = 995_000
                elif rating_diff < 1.10:
                    target_score = 1_000_000
                elif rating_diff < 1.35:
                    target_score = 1_002_500
                elif rating_diff < 1.60:
                    target_score = 1_005_000
                elif rating_diff < 1.80:
                    target_score = 1_006_000
                elif rating_diff < 2.00:
                    target_score = 1_007_000
                elif rating_diff < 2.10:
                    target_score = 1_007_500
                elif rating_diff < 2.15:
                    target_score = 1_008_000
                elif rating_diff < 2.20:
                    target_score = 1_008_500
                else:
                    target_score = 1_009_000

                target_rating = calculate_rating(target_score, chart.const)

                if chart.sdvxin_chart_view is not None:
                    url = sdvxin_link(
                        chart.sdvxin_chart_view.id, difficulty.short_form()
                    )
                else:
                    url = yt_search_link(chart.song.title, difficulty.short_form())

                embeds.append(
                    discord.Embed(
                        title=escape_markdown(chart.song.title),
                        description=escape_markdown(chart.song.artist),
                        color=difficulty.color(),
                    )
                    .set_thumbnail(url=f"{JACKET_BASE}/{chart.song.jacket}")
                    .add_field(name="Category", value=chart.song.genre)
                    .add_field(
                        name=str(difficulty),
                        value=f"[{chart_level}{f' ({chart.const})' if not chart.is_const_unknown else ''}]({url})",
                    )
                    .add_field(
                        name="Target Score",
                        value=f"{target_score} ({floor_to_ndp(target_rating, 2)})",
                    )
                )
            await ctx.reply(embeds=embeds, mention_author=False)

    @commands.hybrid_command("prefix")
    @commands.guild_only()
    async def prefix(self, ctx: Context, new_prefix: Optional[str] = None):
        """Get or set the prefix for this server.

        Permissions
        -----------
        Only users with the Manage Guild permission can set the prefix.

        Parameters
        ----------
        new_prefix: Optional[str]
            New prefix to set. If not provided, the current prefix will be shown.
        """

        # discord.TextChannel should have an associated guild
        assert ctx.guild is not None

        async with ctx.typing():
            if new_prefix is None:
                answer = await self.utils.guild_prefix(ctx)
                await ctx.reply(f"Current prefix: `{answer}`", mention_author=False)
            else:
                permissions = ctx.author.guild_permissions  # type: ignore
                missing_permission = permissions.manage_guild != True
                if missing_permission:
                    raise commands.MissingPermissions(["manage_guild"])

                default_prefix: str = self.bot.cfg.get("DEFAULT_PREFIX", "c>")  # type: ignore
                async with self.bot.begin_db_session() as session, session.begin():
                    if new_prefix == default_prefix:
                        stmt = delete(Prefix).where(Prefix.guild_id == ctx.guild.id)
                        await session.execute(stmt)
                        del self.bot.prefixes[ctx.guild.id]
                    else:
                        prefix = Prefix(guild_id=ctx.guild.id, prefix=new_prefix)
                        await session.merge(prefix)
                        self.bot.prefixes[ctx.guild.id] = new_prefix

                await ctx.reply(f"Prefix set to `{new_prefix}`", mention_author=False)

    @commands.command("privacy")
    async def privacy(self, ctx: Context):
        """Everything you need to know about this bot's privacy-related information."""

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
            "https://cdn.discordapp.com/emojis/1091440450122022972.webp?quality=lossless",
            mention_author=False,
        )


async def setup(bot: ChuniBot) -> None:
    await bot.add_cog(MiscCog(bot))
