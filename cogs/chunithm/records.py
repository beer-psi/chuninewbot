import contextlib
import itertools
from argparse import ArgumentError
from typing import TYPE_CHECKING, Literal, Optional, cast

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import escape_markdown
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from chunithm_net.consts import (
    INTERNATIONAL_JACKET_BASE,
    JACKET_BASE,
    KEY_INTERNAL_LEVEL,
    KEY_OVERPOWER_BASE,
    KEY_OVERPOWER_MAX,
    KEY_PLAY_RATING,
)
from chunithm_net.models.enums import Difficulty, Genres, Rank
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
            recents = await client.recent_record()

            if len(recents) == 0:
                await ctx.reply(
                    f"No recent scores found for {userinfo.name}.", mention_author=False
                )
                return

            hydrated_recents = await self.utils.hydrate_records(recents)

            view = RecentRecordsView(
                ctx, self.bot, hydrated_recents, client, ctxmgr, userinfo
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
                try:
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
                except discord.errors.Forbidden as e:
                    msg = (
                        "Bot requires the Read Message History permission to fetch recent scores. "
                        f"Alternatively, run `{ctx.prefix}compare` while replying to the score you want to compare."
                    )
                    raise commands.CheckFailure(msg) from e

                if len(messages) == 0:
                    msg = "No recent scores found."
                    raise commands.BadArgument(msg)

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

            records = await self.utils.hydrate_records(records)

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

    @commands.hybrid_command("scores")
    @app_commands.describe(
        query="Song title to search for. You don't have to be exact; try things out!",
        user="Check scores of this Discord user. Yourself, if not provided.",
    )
    @app_commands.autocomplete(query=song_title_autocomplete)
    async def scores(
        self,
        ctx: Context,
        user: Optional[discord.User | discord.Member] = None,
        *,
        query: str,
    ):
        """Get a player's scores for a specific song."""
        async with ctx.typing(), self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            guild_id = ctx.guild.id if ctx.guild else None
            result = await self.utils.find_songs(
                query, guild_id=guild_id, load_charts=True
            )

            if result.similarity < SIMILARITY_THRESHOLD:
                return await ctx.reply(
                    did_you_mean_text(result.songs[0], result.matched_alias),
                    mention_author=False,
                )

            songs = [x for x in result.songs if x.available]

            if len(songs) > 1:
                options = []

                for i, x in enumerate(songs):
                    if x.genre == "WORLD'S END":
                        title = f"{x.title} [{x.charts[0].level}]"
                    else:
                        title = x.title

                    options.append((title, i))
                view = SelectToCompareView(
                    options=options,
                    placeholder="Select a song...",
                )
                select_message = await ctx.reply(
                    "Multiple songs were found. Select one:",
                    view=view,
                    mention_author=False,
                )

                await view.wait()

                if view.value is None:
                    await select_message.edit(
                        content="Timed out before selecting a song.", view=None
                    )
                    return None

                song = songs[int(view.value)]
            elif len(songs) > 0:
                song = songs[0]
                select_message = None
            else:
                msg = f"No songs currently available in CHUNITHM International matches the search criteria. Closest match was **{escape_markdown(result.songs[0].title)}**."
                raise commands.BadArgument(msg)

            userinfo = await client.authenticate()
            records = await client.music_record(song.id)

            if len(records) == 0:
                await ctx.reply(
                    f"No records found for {userinfo.name} on **{escape_markdown(song.title)}**.",
                    mention_author=False,
                )
                return None

            records = await self.utils.hydrate_records(records)

            view = CompareView(ctx, userinfo, records)

            if select_message is None:
                view.message = await ctx.reply(
                    content=f"Top play for {userinfo.name}",
                    embed=ScoreCardEmbed(view.items[view.page]),
                    view=view,
                    mention_author=False,
                )
            else:
                view.message = await select_message.edit(
                    content=f"Top play for {userinfo.name}",
                    embed=ScoreCardEmbed(view.items[view.page]),
                    view=view,
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
            best30 = await self.utils.hydrate_records(best30)

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
            recent10 = await self.utils.hydrate_records(recent10)

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
        sort="Sort records by a criteria (default rating).",
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
        sort: Literal["rating", "score", "overpower", "overpower %"] = "rating",
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

            records = await self.utils.hydrate_records(records)

            if sort == "rating":
                records.sort(
                    reverse=True,
                    key=lambda x: (
                        x.extras.get(KEY_PLAY_RATING),
                        x.score,
                        x.extras.get(KEY_OVERPOWER_BASE),
                    ),
                )
            elif sort == "score":
                records.sort(
                    reverse=True,
                    key=lambda x: (
                        x.score,
                        x.extras.get(KEY_PLAY_RATING),
                        x.extras.get(KEY_OVERPOWER_BASE),
                    ),
                )
            elif sort == "overpower":
                records.sort(
                    reverse=True,
                    key=lambda x: (
                        x.extras.get(KEY_OVERPOWER_BASE),
                        x.extras.get(KEY_PLAY_RATING),
                        x.score,
                    ),
                )
            elif sort == "overpower %":
                records.sort(
                    reverse=True,
                    key=lambda x: (
                        x.extras[KEY_OVERPOWER_BASE] / x.extras[KEY_OVERPOWER_MAX],
                        x.extras.get(KEY_OVERPOWER_BASE),
                        x.extras.get(KEY_PLAY_RATING),
                        x.score,
                    ),
                )
            else:
                msg = f"Invalid sort type {sort}. Expected one of score, rating, overpower, overpower %."
                raise commands.BadArgument(msg)

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
        `-s`: Choose a metric to sort scores by. Supported options are `score`, `rating`, `op`, `op_percent`.

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
        `c>top @player -r sss -d mas`: View @player's best scores for SSS rank on MASTER difficulty.
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

        def sort_type(arg: str) -> str:
            if arg not in {
                "score",
                "rating",
                "op",
                "op_percent",
                "overpower",
                "overpower_percent",
            }:
                msg = "Invalid sort type. Expected one of score, rating, op, op_percent, overpower, overpower_percent."
                raise ValueError(msg)

            return arg

        parser = DiscordArguments()
        parser.add_argument("-d", "--difficulty", type=difficulty, required=False)
        parser.add_argument("-s", "--sort", type=sort_type, required=False)

        group = parser.add_mutually_exclusive_group()
        group.add_argument("-g", "--genre", type=genre, required=False)
        group.add_argument("-r", "--rank", type=rank, required=False)

        try:
            args, rest = await parser.parse_known_intermixed_args(shlex_split(query))
        except ArgumentError as e:
            raise commands.BadArgument(str(e)) from e

        if (args.genre or args.rank) and not args.difficulty:
            msg = "Must specify a difficulty when searching by genre or rank."
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
        internal_level: float | None = None

        if str_level:
            # Three accepted use cases, "14", "14+" and "14.9"
            msg = "Invalid level."

            if "." in str_level and str_level.replace(".", "", 1).isdigit():
                internal_level = float(str_level)
                level = str(int(internal_level))

                if internal_level * 10 % 10 >= 5:
                    level += "+"
            elif str_level[-1] == "+" and str_level[:-1].isdigit():
                if int(str_level[:-1]) not in range(7, 15):
                    raise commands.BadArgument(msg)

                level = str_level
            elif str_level.isdigit():
                if int(str_level) not in range(1, 16):
                    raise commands.BadArgument(msg)

                level = str_level
            else:
                raise commands.BadArgument(msg)

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

            records = await self.utils.hydrate_records(records)

            if args.sort is None or args.sort == "rating":
                records.sort(
                    reverse=True,
                    key=lambda x: (
                        x.extras.get(KEY_PLAY_RATING),
                        x.score,
                        x.extras.get(KEY_OVERPOWER_BASE),
                    ),
                )
            elif args.sort == "score":
                records.sort(
                    reverse=True,
                    key=lambda x: (
                        x.score,
                        x.extras.get(KEY_PLAY_RATING),
                        x.extras.get(KEY_OVERPOWER_BASE),
                    ),
                )
            elif args.sort in {"overpower", "op"}:
                records.sort(
                    reverse=True,
                    key=lambda x: (
                        x.extras.get(KEY_OVERPOWER_BASE),
                        x.extras.get(KEY_PLAY_RATING),
                        x.score,
                    ),
                )
            elif args.sort in {"overpower_percent", "op_percent"}:
                records.sort(
                    reverse=True,
                    key=lambda x: (
                        x.extras[KEY_OVERPOWER_BASE] / x.extras[KEY_OVERPOWER_MAX],
                        x.extras.get(KEY_OVERPOWER_BASE),
                        x.extras.get(KEY_PLAY_RATING),
                        x.score,
                    ),
                )
            else:
                msg = f"Invalid sort type {args.sort}. Expected one of score, rating, op, op_percent, overpower, overpower_percent."
                raise commands.BadArgument(msg)

            if internal_level is not None:
                records = [
                    r
                    for r in records
                    if r.extras.get(KEY_INTERNAL_LEVEL) == internal_level
                ]

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
