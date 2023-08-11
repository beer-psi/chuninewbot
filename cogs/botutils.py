from math import floor
from typing import TYPE_CHECKING, Optional, overload

from discord.ext import commands
from discord.ext.commands import Context
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.entities.enums import Rank
from api.entities.record import DetailedRecentRecord, MusicRecord, RecentRecord, Record
from database.models import Alias, Chart, Cookie, Prefix, Song
from update_db import update_db
from utils.calculation.overpower import (
    calculate_overpower_base,
    calculate_overpower_max,
)
from utils.calculation.rating import calculate_rating
from utils.types import (
    AnnotatedDetailedRecentRecord,
    AnnotatedMusicRecord,
    AnnotatedRecentRecord,
    SongSearchResult,
)

if TYPE_CHECKING:
    from bot import ChuniBot


class UtilsCog(commands.Cog, name="Utils"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot

    async def guild_prefix(self, ctx: Context) -> str:
        default_prefix: str = self.bot.cfg.get("DEFAULT_PREFIX", "c>")  # type: ignore
        if ctx.guild is None:
            return default_prefix

        return self.bot.prefixes.get(ctx.guild.id, default_prefix)

    async def login_check(self, ctx_or_id: Context | int) -> str:
        id = ctx_or_id if isinstance(ctx_or_id, int) else ctx_or_id.author.id
        clal = await self.fetch_cookie(id)
        if clal is None:
            raise commands.BadArgument(
                "You are not logged in. Please send `c>login` in my DMs to log in."
            )
        return clal

    async def fetch_cookie(self, id: int) -> str | None:
        async with AsyncSession(self.bot.engine) as session:
            stmt = select(Cookie).where(Cookie.discord_id == id)
            cookie = (await session.execute(stmt)).scalar_one_or_none()

        if cookie is None:
            return None

        return cookie.cookie

    @overload
    async def annotate_song(
        self, song: DetailedRecentRecord
    ) -> AnnotatedDetailedRecentRecord:
        ...

    @overload
    async def annotate_song(
        self, song: Record | MusicRecord
    ) -> MusicRecord | AnnotatedMusicRecord:
        ...

    @overload
    async def annotate_song(self, song: RecentRecord) -> AnnotatedRecentRecord:
        ...

    async def annotate_song(
        self, song: Record | MusicRecord | RecentRecord | DetailedRecentRecord
    ) -> MusicRecord | AnnotatedMusicRecord | AnnotatedRecentRecord | AnnotatedDetailedRecentRecord:
        async with AsyncSession(self.bot.engine) as session:
            if isinstance(song, Record) and not (
                isinstance(song, MusicRecord)
                or isinstance(song, DetailedRecentRecord)
                or isinstance(song, RecentRecord)
            ):
                if song.detailed is None:
                    raise Exception(
                        "Cannot fetch song details without song.detailed.idx"
                    )

                stmt = select(Song).where(Song.chunithm_id == song.detailed.idx)
                song_data = (await session.execute(stmt)).scalar_one_or_none()

                if song_data is None:
                    return MusicRecord.from_record(song)

                id = song_data.id

                annotated_song: AnnotatedMusicRecord = AnnotatedMusicRecord(
                    **song.__dict__, jacket=song_data.jacket
                )
                annotated_song.rank = Rank.from_score(song.score)
            else:
                stmt = select(Song).where(
                    (Song.title == song.title) & (Song.jacket == song.jacket)
                )
                song_data = (await session.execute(stmt)).scalar_one()

                id = song_data.id

                if isinstance(song, DetailedRecentRecord):
                    annotated_song = AnnotatedDetailedRecentRecord(**song.__dict__)
                elif isinstance(song, RecentRecord):
                    annotated_song = AnnotatedRecentRecord(**song.__dict__)
                else:
                    annotated_song = AnnotatedMusicRecord(**song.__dict__)

            stmt = select(Chart).where(
                (Chart.song_id == id)
                & (Chart.difficulty == song.difficulty.short_form())
            )
            chart_data = (await session.execute(stmt)).scalar_one_or_none()

        if chart_data is None:
            return annotated_song
        annotated_song.internal_level = chart_data.const

        level = chart_data.level
        annotated_song.level = str(floor(level)) + ("+" if level * 10 % 10 >= 5 else "")
        annotated_song.unknown_const = bool(chart_data.is_const_unknown)

        internal_level = (
            annotated_song.internal_level
            if annotated_song.internal_level != 0
            else level
        )

        annotated_song.play_rating = calculate_rating(song.score, internal_level)

        annotated_song.overpower_base = calculate_overpower_base(
            song.score, internal_level
        )
        annotated_song.overpower_max = calculate_overpower_max(internal_level)

        if (
            isinstance(annotated_song, AnnotatedDetailedRecentRecord)
            and chart_data.maxcombo != 0
        ):
            annotated_song.full_combo = chart_data.maxcombo

        return annotated_song

    async def find_song(
        self,
        query: str,
        *,
        guild_id: Optional[int] = None,
    ) -> tuple[Song, Alias | None, float]:
        """Finds the song that best matches a given query.

        Parameters
        ----------
        query: str
            The query to search for.
        guild_id: Optional[int]
            The ID of the guild to search for aliases in. If None, only global aliases are searched.

        Returns
        -------
        tuple[Song, Alias | None, float]
            The third item is the similarity of the matched song.
        """
        query = query.lower()
        async with AsyncSession(self.bot.engine) as session:
            stmt = (
                select(Song, Song.similarity(query).label("similarity"))  # type: ignore[reportGeneralTypeIssues]
                .order_by(text("similarity DESC"))
                .limit(1)
            )

            song, similarity = (await session.execute(stmt)).one()

            # similarity, id, chunithm_id, title, genre, artist, release, bpm, jacket = song
            alias: Alias | None = None
            if similarity < 0.9:
                guild_ids = [-1]
                if guild_id is not None:
                    guild_ids.append(guild_id)
                stmt = (
                    select(Alias, Alias.similarity(query).label("similarity"))  # type: ignore[reportGeneralTypeIssues]
                    .where(Alias.guild_id.in_(guild_ids))
                    .order_by(text("similarity DESC"))
                    .limit(1)
                )
                alias, similarity = (await session.execute(stmt)).one()

                stmt = select(Song).where(Song.id == alias.song_id)  # type: ignore
                song: Song = (await session.execute(stmt)).scalar_one()
        return song, alias, similarity

    # maimai and CHUNITHM NET goes under maintenance every day at 2:00 AM JST, so we update the DB then
    #
    # job is currently disabled until CHUNITHM SUN PLUS reaches international
    # @tasks.loop(time=time(hour=17, tzinfo=timezone.utc))
    async def update_chunirec_db(self):
        # Disable all commands while updating the DB
        for cmd in self.bot.walk_commands():
            cmd.enabled = False
        # await update_db(self.bot.db)
        # Re-enable all commands
        for cmd in self.bot.walk_commands():
            cmd.enabled = True


async def setup(bot: "ChuniBot"):
    await bot.add_cog(UtilsCog(bot))
