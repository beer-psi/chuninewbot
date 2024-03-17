import contextlib
from http.cookiejar import LWPCookieJar
import io
from typing import TYPE_CHECKING, Optional, overload

from discord.ext import commands
from discord.ext.commands import Context
from sqlalchemy import select, text, update
from sqlalchemy.orm import joinedload

from chunithm_net import ChuniNet
from chunithm_net.entities.enums import Rank
from chunithm_net.entities.record import (
    DetailedRecentRecord,
    MusicRecord,
    RecentRecord,
    Record,
)
from database.models import Alias, Chart, Cookie, Song
from utils import get_jacket_url
from utils.calculation.overpower import (
    calculate_overpower_base,
    calculate_overpower_max,
)
from utils.calculation.rating import calculate_rating
from utils.config import config
from utils.logging import logger
from utils.types import (
    AnnotatedDetailedRecentRecord,
    AnnotatedMusicRecord,
    AnnotatedRecentRecord,
    MissingDetailedParams,
)

if TYPE_CHECKING:
    from bot import ChuniBot


class UtilsCog(commands.Cog, name="Utils"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot
        self.alias_cache = []

    async def cog_load(self) -> None:
        await self._populate_alias_cache()

    async def _populate_alias_cache(self) -> None:
        async with self.bot.begin_db_session() as session:
            sql = select(Song).options(joinedload(Song.aliases))
            results = (await session.execute(sql)).scalars().all()

        self.alias_cache.clear()

        for song in results:
            self.alias_cache.append(
                {"alias": song.title, "guild_id": -1, "song_id": song.id}
            )

            for alias in song.aliases:
                self.alias_cache.append(
                    {
                        "alias": alias.alias,
                        "guild_id": alias.guild_id,
                        "song_id": alias.song_id,
                    }
                )

    async def guild_prefix(self, ctx: Context) -> str:
        default_prefix: str = config.bot.default_prefix
        if ctx.guild is None:
            return default_prefix

        return self.bot.prefixes.get(ctx.guild.id, default_prefix)

    async def login_check(self, ctx_or_id: Context | int) -> LWPCookieJar:
        id = ctx_or_id if isinstance(ctx_or_id, int) else ctx_or_id.author.id
        clal = await self.fetch_cookie(id)
        if clal is None:
            msg = "You are not logged in. Please send `c>login` in my DMs to log in."
            raise commands.BadArgument(msg)
        return clal

    async def fetch_cookie(self, id: int) -> LWPCookieJar | None:
        async with self.bot.begin_db_session() as session:
            stmt = select(Cookie).where(Cookie.discord_id == id)
            cookie = (await session.execute(stmt)).scalar_one_or_none()

        if cookie is None:
            return None

        jar = LWPCookieJar()
        jar._really_load(  # type: ignore[reportAttributeAccessIssue]
            io.StringIO(cookie.cookie), "?", ignore_discard=False, ignore_expires=False
        )

        return jar

    @contextlib.asynccontextmanager
    async def chuninet(self, ctx_or_id: Context | int):
        id = ctx_or_id if isinstance(ctx_or_id, int) else ctx_or_id.author.id
        jar = await self.login_check(ctx_or_id)

        session = ChuniNet(jar)
        try:
            yield session
        finally:
            async with self.bot.begin_db_session() as db_session:
                await db_session.execute(
                    update(Cookie)
                    .where(Cookie.discord_id == id)
                    .values(cookie=f"#LWP-Cookies-2.0\n{jar.as_lwp_str()}")
                )
                await db_session.commit()

            await session.close()

    @overload
    async def annotate_song(
        self, song: DetailedRecentRecord
    ) -> AnnotatedDetailedRecentRecord:
        ...

    @overload
    async def annotate_song(self, song: RecentRecord) -> AnnotatedRecentRecord:
        ...

    @overload
    async def annotate_song(self, song: Record | MusicRecord) -> AnnotatedMusicRecord:
        ...

    async def annotate_song(
        self, song: Record | MusicRecord | RecentRecord | DetailedRecentRecord
    ) -> AnnotatedMusicRecord | AnnotatedRecentRecord | AnnotatedDetailedRecentRecord:
        async with self.bot.begin_db_session() as session:
            if isinstance(song, Record) and not isinstance(
                song, (MusicRecord, DetailedRecentRecord, RecentRecord)
            ):
                if song.detailed is None:
                    raise MissingDetailedParams

                stmt = select(Song).where(Song.id == song.detailed.idx)
                song_data = (await session.execute(stmt)).scalar_one_or_none()

                if song_data is None:
                    logger.warn(f"Missing song data for song ID {song.detailed.idx}")
                    return AnnotatedMusicRecord(**song.__dict__)

                id = song_data.id

                annotated_song: AnnotatedMusicRecord = AnnotatedMusicRecord(
                    **song.__dict__, jacket=get_jacket_url(song_data)
                )
                annotated_song.rank = Rank.from_score(song.score)
            else:
                stmt = select(Song)
                if song.detailed is None or isinstance(song, RecentRecord):
                    jacket_filename = song.jacket.split("/")[-1]
                    stmt = stmt.where(
                        (Song.title == song.title) & (Song.jacket == jacket_filename)
                    )
                else:
                    stmt = stmt.where(Song.id == song.detailed.idx)

                song_data = (await session.execute(stmt)).scalar_one_or_none()

                if isinstance(song, DetailedRecentRecord):
                    annotated_song = AnnotatedDetailedRecentRecord(**song.__dict__)
                elif isinstance(song, RecentRecord):
                    annotated_song = AnnotatedRecentRecord(**song.__dict__)
                else:
                    annotated_song = AnnotatedMusicRecord(**song.__dict__)

                if song_data is None:
                    if song.detailed is None or isinstance(song, RecentRecord):
                        logger.warn(
                            f"Missing song data for song title {song.title} with jacket {song.jacket}"
                        )
                    else:
                        logger.warn(
                            f"Missing song data for song ID {song.detailed.idx}"
                        )
                    return annotated_song

                id = song_data.id

            stmt = select(Chart).where(
                (Chart.song_id == id)
                & (Chart.difficulty == song.difficulty.short_form())
            )
            chart_data = (await session.execute(stmt)).scalar_one_or_none()

        if chart_data is None:
            return annotated_song
        annotated_song.internal_level = chart_data.const

        annotated_song.level = chart_data.level

        try:
            numeric_level = float(chart_data.level.replace("+", ".5"))
        except ValueError:
            numeric_level = 0

        internal_level = (
            annotated_song.internal_level
            if annotated_song.internal_level is not None
            else numeric_level
        )

        annotated_song.play_rating = calculate_rating(song.score, internal_level)

        annotated_song.overpower_base = calculate_overpower_base(
            song.score, internal_level
        )
        annotated_song.overpower_max = calculate_overpower_max(internal_level)

        if isinstance(annotated_song, AnnotatedDetailedRecentRecord):
            annotated_song.full_combo = chart_data.maxcombo

        return annotated_song

    async def find_song(
        self,
        query: str,
        *,
        guild_id: Optional[int] = None,
        worlds_end: bool = False,
    ) -> tuple[Song | None, Alias | None, float]:
        """Finds the song that best matches a given query.

        Parameters
        ----------
        query: str
            The query to search for.
        guild_id: Optional[int]
            The ID of the guild to search for aliases in. If None, only global aliases are searched.
        worlds_end: bool
            Whether to search for WORLD'S END charts, instead of normal charts.

        Returns
        -------
        tuple[Song, Alias | None, float]
            The third item is the similarity of the matched song.
        """
        async with self.bot.begin_db_session() as session:
            stmt = (
                select(Song, Song.similarity(query).label("similarity"))  # type: ignore[reportGeneralTypeIssues]
                .order_by(text("similarity DESC"))
                .limit(1)
            )

            if worlds_end:
                stmt = stmt.where(Song.genre == "WORLD'S END")

            result = (await session.execute(stmt)).one_or_none()

            if result is None:
                return None, None, 0.0

            song, similarity = result

            # similarity, id, chunithm_id, title, genre, artist, release, bpm, jacket = song
            alias: Alias | None = None
            if similarity < 90:
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

                stmt = select(Song).where(Song.id == alias.song_id)  # type: ignore[reportGeneralTypeIssues]
                song: Song | None = (await session.execute(stmt)).scalar_one()

                if worlds_end:
                    stmt = (
                        select(Song)
                        .where(
                            (Song.title == song.title) & (Song.genre == "WORLD'S END")
                        )
                        .limit(1)
                    )
                    song: Song | None = (
                        await session.execute(stmt)
                    ).scalar_one_or_none()
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
