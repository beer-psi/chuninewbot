import asyncio
import contextlib
import itertools
from argparse import ArgumentError
from types import SimpleNamespace
from typing import TYPE_CHECKING, Optional, cast

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from chunithm_net.consts import INTERNATIONAL_JACKET_BASE, JACKET_BASE
from chunithm_net.entities.enums import Difficulty, Genres, Rank
from database.models import SongJacket
from utils import did_you_mean_text, shlex_split
from utils.argparse import DiscordArguments
from utils.components import ScoreCardEmbed
from utils.constants import SIMILARITY_THRESHOLD
from utils.views import B30View, CompareView, RecentRecordsView, SelectToCompareView

if TYPE_CHECKING:
    from bot import ChuniBot
    from cogs.autocompleters import AutocompletersCog
    from cogs.botutils import UtilsCog


class RecordsCog(commands.Cog, name="Records"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot
        self.utils: "UtilsCog" = self.bot.get_cog("Utils")  # type: ignore[reportGeneralTypeIssues]
        self.autocompleters: "AutocompletersCog" = self.bot.get_cog("Autocompleters")  # type: ignore[reportGeneralTypeIssues]

    @commands.hybrid_command(name="recent", aliases=["rs"])
    async def recent(
        self, ctx: Context, *, user: Optional[discord.User | discord.Member] = None
    ):
        """View your recent scores.

        Parameters
        ----------
        user: Optional[discord.User | discord.Member]
            The user to view recent scores for. Defaults to the author.
        """

        async with ctx.typing():
            ctxmgr = self.utils.chuninet(ctx if user is None else user.id)
            client = await ctxmgr.__aenter__()
            userinfo = await client.authenticate()
            recent_scores = await client.recent_record()

            tasks = [self.utils.annotate_song(score) for score in recent_scores]
            recent_scores = await asyncio.gather(*tasks)

            view = RecentRecordsView(
                ctx, self.bot, recent_scores, client, ctxmgr, userinfo
            )
            view.message = await ctx.reply(
                content=f"Most recent credits for {userinfo.name}:",
                embeds=view.format_score_page(view.items[0]),
                view=view,
                mention_author=False,
            )

    @commands.hybrid_command("compare", aliases=["c"])
    async def compare(
        self, ctx: Context, *, user: Optional[discord.User | discord.Member] = None
    ):
        """Compare your best score with another score.

        By default, it's the most recently posted score. You can reply to another
        user's score to compare with that instead. If there are multiple scores in
        said message, you will be prompted to select one.

        Parameters
        ----------
        user: Optional[discord.User | discord.Member]
            The user to compare with. Defaults to the author.
        """

        async with ctx.typing(), self.bot.begin_db_session() as session, self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            if ctx.message.reference is not None:
                message = await ctx.channel.fetch_message(
                    cast(int, ctx.message.reference.message_id)
                )
            else:
                messages = [
                    x
                    async for x in ctx.channel.history(limit=50)
                    if x.author == self.bot.user
                    and any(
                        e.thumbnail.url is not None
                        and (
                            JACKET_BASE in e.thumbnail.url
                            or INTERNATIONAL_JACKET_BASE in e.thumbnail.url
                        )
                        for e in x.embeds
                    )
                ]
                message = messages[0]

            thumbnail_urls = []
            for e in message.embeds:
                if e.thumbnail.url is not None:
                    thumbnail_urls.append(e.thumbnail.url)
                elif e.image.url is not None:
                    thumbnail_urls.append(e.image.url)

            if len(thumbnail_urls) == 0:
                msg = "The message replied to does not contain any charts/scores."
                raise commands.BadArgument(msg)

            sql = (
                select(SongJacket)
                .where(SongJacket.jacket_url.in_(thumbnail_urls))
                .options(joinedload(SongJacket.song))
            )
            jackets = (await session.execute(sql)).scalars().all()

            if len(jackets) == 0:
                await ctx.reply("No song found.", mention_author=False)
                return

            if len(jackets) > 1:
                view = SelectToCompareView(
                    [(x.song.title, i) for i, x in enumerate(jackets)]
                )
                compare_message = await ctx.reply(
                    "Select a score to compare with:", view=view, mention_author=False
                )

                await view.wait()

                if view.value is None:
                    await compare_message.edit(
                        content="Timed out before selecting a score.", view=None
                    )
                    return

                jacket = jackets[int(view.value)]
                song = jacket.song
            else:
                compare_message = None
                jacket = jackets[0]
                song = jacket.song

            song.raise_if_not_available()

            embed = next(
                x
                for x in message.embeds
                if jacket.jacket_url in {x.thumbnail.url, x.image.url}
            )
            userinfo = await client.authenticate()
            records = await client.music_record(song.id)

            if len(records) == 0:
                await ctx.reply(
                    f"No records found for {userinfo.name}.", mention_author=False
                )
                return

            futures = [self.utils.annotate_song(record) for record in records]
            records = await asyncio.gather(*futures)

            page = 0
            try:
                # intentionally passing an invalid color so it throws and keep the page at 0
                difficulty = Difficulty.from_embed_color(
                    embed.color.value if embed.color else 0  # type: ignore[attr-defined]
                )
                page = next(
                    (
                        i
                        for i, record in enumerate(records)
                        if record.difficulty == difficulty
                    ),
                    0,
                )
            except ValueError:
                pass

            view = CompareView(ctx, userinfo, records)
            view.page = page

            if compare_message is not None:
                view.message = compare_message
                await compare_message.edit(
                    content=f"Top play for {userinfo.name}",
                    embed=ScoreCardEmbed(view.items[view.page]),
                    view=view,
                )
                return
            view.message = await ctx.reply(
                content=f"Top play for {userinfo.name}",
                embed=ScoreCardEmbed(view.items[view.page]),
                view=view,
                mention_author=False,
            )
            return

    async def song_title_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.autocompleters.song_title_autocomplete(interaction, current)

    @app_commands.command(name="scores", description="Get scores for a specific song.")
    @app_commands.describe(
        query="Song title to search for. You don't have to be exact; try things out!",
        user="Check scores of this Discord user. Yourself, if not provided.",
        worlds_end="Search for WORLD'S END songs instead of standard songs.",
    )
    @app_commands.autocomplete(query=song_title_autocomplete)
    async def scores_slash(
        self,
        interaction: "discord.Interaction[ChuniBot]",
        query: str,
        *,
        user: Optional[discord.User | discord.Member] = None,
        worlds_end: bool = False,
    ):
        if user is not None:
            query = f"{user.mention} {query}"
        if worlds_end:
            query += " -we"

        ctx = await Context.from_interaction(interaction)
        return await self.scores(ctx, query=query)

    @commands.command("scores")
    async def scores(
        self,
        ctx: Context,
        *,
        query: str,
    ):
        """**Get a user's scores for a song.
        If no user is specified, your scores will be shown.**

        **Parameters:**
        `username`: Discord username of the player. Yourself, if not provided.
        `query`: Song title to search for.
        `-we`: Search for WORLD'S END songs instead of standard songs (no param).
        """
        args = SimpleNamespace(worlds_end=False, query=[])

        argv = shlex_split(query)
        for arg in argv:
            if arg in ["-we", "--worlds-end"]:
                args.worlds_end = True
            else:
                args.query.append(arg)

        user = None
        query = " ".join(args.query)
        for converter in [commands.MemberConverter, commands.UserConverter]:
            try:
                user = await converter().convert(ctx, args.query[0])
                query = " ".join(args.query[1:])
            # We need to iterate over all converters, so PERF203 does not
            # apply here.
            except commands.BadArgument:  # noqa: PERF203
                pass

        async with ctx.typing(), self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            guild_id = ctx.guild.id if ctx.guild else None
            song, alias, similarity = await self.utils.find_song(
                query, guild_id=guild_id, worlds_end=args.worlds_end
            )
            if song is None or similarity < SIMILARITY_THRESHOLD:
                return await ctx.reply(
                    did_you_mean_text(song, alias), mention_author=False
                )

            song.raise_if_not_available()

            userinfo = await client.authenticate()

            records = await client.music_record(song.id)

            if len(records) == 0:
                await ctx.reply(
                    f"No records found for {userinfo.name}.", mention_author=False
                )
                return None

            futures = [self.utils.annotate_song(record) for record in records]
            records = await asyncio.gather(*futures)

            view = CompareView(ctx, userinfo, records)
            view.message = await ctx.reply(
                content=f"Top play for {userinfo.name}",
                embed=ScoreCardEmbed(view.items[view.page]),
                view=view,
                mention_author=False,
            )
            return None

    @commands.hybrid_command("best30", aliases=["b30"])
    async def best30(
        self, ctx: Context, *, user: Optional[discord.User | discord.Member] = None
    ):
        """View top plays

        Parameters
        ----------
        user: Optional[discord.User | discord.Member]
            The user to get scores for.
        """

        async with ctx.typing(), self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            best30 = await client.best30()

            tasks = [self.utils.annotate_song(score) for score in best30]
            best30 = await asyncio.gather(*tasks)

            view = B30View(ctx, best30)
            view.message = await ctx.reply(
                content=view.format_content(),
                embeds=view.format_page(view.items[: view.per_page]),
                view=view,
                mention_author=False,
            )

    @commands.hybrid_command("recent10", aliases=["r10"])
    async def recent10(
        self, ctx: Context, *, user: Optional[discord.User | discord.Member] = None
    ):
        """View top recent plays

        Parameters
        ----------
        user: Optional[discord.User | discord.Member]
            The user to get scores for.
        """

        async with ctx.typing(), self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            recent10 = await client.recent10()

            tasks = [self.utils.annotate_song(score) for score in recent10]
            recent10 = await asyncio.gather(*tasks)

            view = B30View(ctx, recent10)
            view.message = await ctx.reply(
                content=view.format_content(),
                embeds=view.format_page(view.items[: view.per_page]),
                view=view,
                mention_author=False,
            )

    @app_commands.command(name="top", description="View your best scores for a level.")
    @app_commands.describe(
        level="Level (from 1 to 15) to search for.",
        difficulty="Difficulty to search for.",
        genre="Genre to search for.",
        rank="Rank to search for.",
    )
    @app_commands.choices(
        level=[
            *[app_commands.Choice(name=str(i), value=str(i)) for i in range(1, 7)],
            *itertools.chain.from_iterable(
                [
                    (
                        app_commands.Choice(name=f"{i}", value=f"{i}"),
                        app_commands.Choice(name=f"{i}+", value=f"{i}+"),
                    )
                    for i in range(7, 15)
                ]
            ),
            app_commands.Choice(name="15", value="15"),
        ],
        difficulty=[
            app_commands.Choice(name=str(x), value=x.value)
            for x in Difficulty.__members__.values()
        ],  # type: ignore[reportGeneralTypeIssues]
        genre=[
            app_commands.Choice(name=str(x), value=x.value)
            for x in Genres.__members__.values()
        ],  # type: ignore[reportGeneralTypeIssues]
        rank=[
            app_commands.Choice(name=str(x), value=x.value)
            for x in Rank.__members__.values()
        ],  # type: ignore[reportGeneralTypeIssues]
    )
    async def top_slash(
        self,
        interaction: "discord.Interaction[ChuniBot]",
        *,
        user: Optional[discord.User | discord.Member] = None,
        level: Optional[str] = None,
        difficulty: Optional[Difficulty] = None,
        genre: Optional[Genres] = None,
        rank: Optional[Rank] = None,
    ):
        await interaction.response.defer()

        if (genre or rank) and not difficulty:
            return await interaction.followup.send(
                "Difficulty must be set if genre or rank is set."
            )

        async with self.utils.chuninet(
            interaction.user.id if user is None else user.id
        ) as client:
            records = await client.music_record_by_folder(
                level=level, genre=genre, difficulty=difficulty, rank=rank
            )
            assert records is not None

            if len(records) == 0:
                return await interaction.followup.send("No scores found.")

            tasks = [self.utils.annotate_song(score) for score in records]
            records = await asyncio.gather(*tasks)
            records.sort(key=lambda x: (x.play_rating, x.score), reverse=True)

            ctx = await Context.from_interaction(interaction)
            view = B30View(ctx, records, show_average=False)
            view.message = await ctx.reply(
                content=view.format_content(),
                embeds=view.format_page(view.items[: view.per_page]),
                view=view,
            )
            return None

    @commands.command("top")
    async def top(
        self,
        ctx: Context,
        *,
        query: str,
    ):
        """
        **View your best scores for a level.**

        **Parameters:**
        `user`: Discord username of the player. Yourself, if not provided.
        `level`: Level (from 1 to 15) to search for.
        `-d`: Difficulty to search for. Must be one of `EASY`, `ADVANCED`, `EXPERT`, `MASTER`, `ULTIMA`, or `WE` if specified.
        `-g`: Genre to search for. Must be one of `POPS&ANIME`, `niconico`, `Touhou Project`, `ORIGINAL`, `VARIETY`, `Irodorimidori`, or `Gekimai`, if specified.
        `-r`: Rank to search for. Anywhere between "S" and "SSS+" (inclusive), if specified.

        Genre and rank cannot be set at the same time. If genre or rank is set, difficulty must also be set.

        If multiple parameters are set, they will be applied in order of:
        - level
        - genre + difficulty
        - rank + difficulty
        - difficulty

        **Examples:**
        `c>top 14+`: View your best scores for level 14+
        `c>top -d mas`: View your best scores for MASTER difficulty
        `c>top -g original -d ultima`: View your best scores for ULTIMA difficulty in the ORIGINAL folder
        `c>top @player -r sss`: View @player's best scores for SSS rank.
        """

        def genre(arg: str) -> Genres:
            genre = None
            genre_lower = arg.lower()
            if genre_lower.startswith("pops"):
                genre = Genres.POPS_AND_ANIME
            elif genre_lower.startswith("nico"):
                genre = Genres.NICONICO
            elif genre_lower.startswith(("touhou", "toho", "東方")):
                genre = Genres.TOUHOU_PROJECT
            elif genre_lower.startswith(("original", "chunithm")):
                genre = Genres.ORIGINAL
            elif genre_lower.startswith("variety"):
                genre = Genres.VARIETY
            elif genre_lower.startswith("irodori"):
                genre = Genres.IRODORIMIDORI
            elif genre_lower.startswith(("geki", "ゲキ")):
                genre = Genres.GEKIMAI
            else:
                msg = "Invalid genre."
                raise ValueError(msg)

            return genre

        def difficulty(arg: str) -> Difficulty:
            if arg.upper().startswith("WORLD"):
                return Difficulty.WORLDS_END
            return Difficulty.from_short_form(arg.upper()[:3])

        def rank(arg: str) -> Rank:
            return Rank[arg.upper().replace("+", "p")]

        parser = DiscordArguments()
        parser.add_argument("-d", "--difficulty", nargs="?", type=difficulty)

        group = parser.add_mutually_exclusive_group()
        group.add_argument("-g", "--genre", nargs="?", type=genre)
        group.add_argument("-r", "--rank", nargs="?", type=rank)

        try:
            args, rest = await parser.parse_known_intermixed_args(shlex_split(query))
        except ArgumentError as e:
            raise commands.BadArgument(str(e)) from e

        if (args.genre or args.rank) and not args.difficulty:
            msg = "Difficulty must be set if genre or rank is set."
            raise commands.BadArgument(msg)

        user = None
        str_level = None
        if len(rest) > 0:
            for converter in [commands.MemberConverter, commands.UserConverter]:
                with contextlib.suppress(commands.BadArgument):
                    user = await converter().convert(ctx, rest[0])
                    str_level = rest[1] if len(rest) > 1 else None
                    break

        if str_level is None:
            str_level = rest[0] if len(rest) > 0 else None

        level = None
        if str_level:
            msg = "Invalid level."

            try:
                if str_level[-1] == "+":
                    numeric_level = int(str_level.zfill(3)[:-1])
                else:
                    numeric_level = int(str_level[0:2])
            except ValueError:
                raise commands.BadArgument(msg) from None

            if str_level[-1] == "+" and numeric_level not in range(7, 15):
                raise commands.BadArgument(msg)
            if numeric_level not in range(1, 16):
                raise commands.BadArgument(msg)

            level = str_level

        async with ctx.typing(), self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            records = await client.music_record_by_folder(
                level=level,
                genre=args.genre,
                difficulty=args.difficulty,
                rank=args.rank,
            )
            assert records is not None

            if len(records) == 0:
                return await ctx.reply("No scores found.", mention_author=False)

            tasks = [self.utils.annotate_song(score) for score in records]
            records = await asyncio.gather(*tasks)
            records.sort(key=lambda x: (x.play_rating, x.score), reverse=True)

            view = B30View(ctx, records, show_average=False)
            view.message = await ctx.reply(
                content=view.format_content(),
                embeds=view.format_page(view.items[: view.per_page]),
                view=view,
                mention_author=False,
            )
            return None


async def setup(bot: "ChuniBot"):
    await bot.add_cog(RecordsCog(bot))
