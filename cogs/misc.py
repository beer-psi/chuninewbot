import subprocess
import sys
import time
from random import random
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import escape_markdown, oauth_url

from api import ChuniNet
from api.consts import JACKET_BASE
from api.enums import Difficulty
from bot import ChuniBot
from cogs.botutils import UtilsCog
from utils import floor_to_ndp, format_level, sdvxin_link, yt_search_link
from utils.rating_calculator import calculate_rating
from views.songlist import SonglistView


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
        """Calculate rating from score and chart constant.

        Parameters
        ----------
        score: int
            The score to calculate play rating from
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

        await ctx.reply(
            f"Calculation result: {sign}{floor_to_ndp(rating, 2)}", mention_author=False
        )

    @commands.hybrid_command("find")
    async def find(self, ctx: Context, query: float):
        """Find charts by chart constant.

        Parameters
        ----------
        query: float
            Chart constant to search for.
        """

        async with self.bot.db.execute(
            "SELECT songs.title, charts.difficulty, sdvxin.id AS sdvxin_id "
            "FROM chunirec_charts charts "
            "LEFT JOIN chunirec_songs songs ON charts.song_id = songs.id "
            "LEFT JOIN sdvxin ON charts.song_id = sdvxin.song_id AND charts.difficulty = sdvxin.difficulty "
            "WHERE const = ?",
            (query,),
        ) as cursor:
            charts = await cursor.fetchall()
        if not charts:
            await ctx.reply("No charts found.", mention_author=False)
            return

        results: list[tuple[str, str, str | None]] = []
        for chart in charts:
            title, difficulty, sdvxin_id = chart
            results.append((title, difficulty, sdvxin_id))

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

        async with ctx.typing():
            if count > 4 or count < 1:
                raise commands.BadArgument("Number of songs must be between 1 and 4.")
            
            # Check whether input is level or constant
            try:
                if level.find('+') != -1:
                    min_level = float(level.replace("+", ".5"))
                    max_level = float(level.replace("+", ".9"))
                elif level.find('.') == -1:
                    min_level = level + ".0"
                    max_level = level + ".4"
                else:
                    min_level = float(level)
                    max_level = float(level)
            except:
                raise commands.BadArgument("Please enter a valid level or chart constant.")

            async with self.bot.db.execute(
                "SELECT songs.title, songs.genre, songs.artist, songs.jacket, charts.difficulty, level, const, is_const_unknown, sdvxin.id AS sdvxin_id "
                "FROM chunirec_charts charts "
                "LEFT JOIN chunirec_songs songs ON charts.song_id = songs.id "
                "LEFT JOIN sdvxin ON charts.song_id = sdvxin.song_id AND charts.difficulty = sdvxin.difficulty "
                "WHERE const >= ? AND const <= ? "
                "ORDER BY random() "
                "LIMIT ?",
                (min_level, max_level, count),
            ) as cursor:
                charts = await cursor.fetchall()
            if not charts:
                await ctx.reply("No charts found.", mention_author=False)
                return

            embeds: list[discord.Embed] = []
            for chart in charts:
                (
                    title,
                    genre,
                    artist,
                    jacket,
                    difficulty,
                    lev,
                    const,
                    is_const_unknown,
                    sdvxin_id,
                ) = chart

                difficulty = Difficulty.from_short_form(difficulty)
                chart_level = format_level(lev)

                if sdvxin_id is not None:
                    url = sdvxin_link(sdvxin_id, difficulty.short_form())
                else:
                    url = yt_search_link(title, difficulty.short_form())

                embeds.append(
                    discord.Embed(
                        title=escape_markdown(title),
                        description=escape_markdown(artist),
                        color=difficulty.color(),
                    )
                    .set_thumbnail(url=f"{JACKET_BASE}/{jacket}")
                    .add_field(name="Category", value=genre)
                    .add_field(
                        name=str(difficulty),
                        value=f"[{chart_level}{f' ({const})' if not is_const_unknown else ''}]({url})",
                    )
                )
            await ctx.reply(embeds=embeds, mention_author=False)

    @commands.hybrid_command("recommend")
    async def recommend(self, ctx: Context, count: int = 3):
        """Get random chart recommendations with target scores based on your rating.

        Please note that recommended charts are generated randomly and are independent on your high scores.

        Parameters
        ----------
        count: int
            Number of charts to return. Must be between 1 and 4.
        """

        async with ctx.typing():
            if count > 4 or count < 1:
                raise commands.BadArgument("Number of songs must be between 1 and 4.")

            clal = await self.utils.login_check(ctx)
            async with ChuniNet(clal) as client:
                player_data = await client.player_data()
                max_rating = player_data.rating.max

                # Determine min-max const to recommend based on user rating. Formula is intentionally confusing.
                min_level = max_rating * 1.05 - 3.05
                max_level = max_rating * 0.85 + 0.95
                if min_level < 7:
                    min_level = 7
                if max_level < 14:
                    max_level += (14 - max_level) * 0.2
                if max_level < min_level + 1:
                    max_level = min_level + 1

                async with self.bot.db.execute(
                    "SELECT songs.title, songs.genre, songs.artist, songs.jacket, charts.difficulty, level, const, is_const_unknown, sdvxin.id AS sdvxin_id "
                    "FROM chunirec_charts charts "
                    "LEFT JOIN chunirec_songs songs ON charts.song_id = songs.id "
                    "LEFT JOIN sdvxin ON charts.song_id = sdvxin.song_id AND charts.difficulty = sdvxin.difficulty "
                    "WHERE const >= ? AND const <= ? "
                    "ORDER BY random() "
                    "LIMIT ?",
                    (min_level, max_level, count),
                ) as cursor:
                    charts = await cursor.fetchall()
                if not charts:
                    await ctx.reply("No charts found.", mention_author=False)
                    return

                embeds: list[discord.Embed] = []
                for chart in charts:
                    (
                        title,
                        genre,
                        artist,
                        jacket,
                        difficulty,
                        lev,
                        const,
                        is_const_unknown,
                        sdvxin_id,
                    ) = chart

                    difficulty = Difficulty.from_short_form(difficulty)
                    chart_level = format_level(lev)
                    rating_diff = max_rating - const

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
                    
                    target_rating = calculate_rating(target_score, const)

                    if sdvxin_id is not None:
                        url = sdvxin_link(sdvxin_id, difficulty.short_form())
                    else:
                        url = yt_search_link(title, difficulty.short_form())

                    embeds.append(
                        discord.Embed(
                            title=escape_markdown(title),
                            description=escape_markdown(artist),
                            color=difficulty.color(),
                        )
                        .set_thumbnail(url=f"{JACKET_BASE}/{jacket}")
                        .add_field(name="Category", value=genre)
                        .add_field(
                            name=str(difficulty),
                            value=f"[{chart_level}{f' ({const})' if not is_const_unknown else ''}]({url})",
                        )
                        .add_field(name="Target Score", value=f"{target_score} ({floor_to_ndp(target_rating, 2)})")
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

        if new_prefix is None:
            answer = self.bot.cfg.get("DEFAULT_PREFIX", "c>")
            async with self.bot.db.execute(
                "SELECT prefix FROM guild_prefix WHERE guild_id = ?", (ctx.guild.id,)
            ) as cursor:
                prefix = await cursor.fetchone()
            if prefix is not None:
                answer = prefix[0]
            await ctx.reply(f"Current prefix: `{answer}`", mention_author=False)
        else:
            permissions = ctx.author.guild_permissions  # type: ignore
            missing_permission = permissions.manage_guild != True
            if missing_permission:
                raise commands.MissingPermissions(["manage_guild"])

            await self.bot.db.execute(
                "INSERT INTO guild_prefix (guild_id, prefix) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET prefix = excluded.prefix",
                (ctx.guild.id, new_prefix),
            )
            await self.bot.db.commit()
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
