import contextlib
from http.cookiejar import LWPCookieJar
import io
from typing import TYPE_CHECKING, Optional, TypeVar

from discord.ext import commands
from discord.ext.commands import Context
from rapidfuzz import fuzz, process
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from chunithm_net import ChuniNet
from chunithm_net.consts import (
    KEY_INTERNAL_LEVEL,
    KEY_LEVEL,
    KEY_OVERPOWER_BASE,
    KEY_OVERPOWER_MAX,
    KEY_PLAY_RATING,
    KEY_SONG_ID,
    KEY_TOTAL_COMBO,
)
from chunithm_net.models.record import (
    MusicRecord,
    Record,
)
from database.models import Alias, Chart, Cookie, Song
from utils.calculation.overpower import (
    calculate_overpower_base,
    calculate_overpower_max,
)
from utils.calculation.rating import calculate_rating
from utils.config import config
from utils.logging import logger
from utils.types import MissingDetailedParams

if TYPE_CHECKING:
    from bot import ChuniBot

T = TypeVar("T", bound=Record)


class CachedAlias:
    id: Optional[int] = None
    alias: str
    title: str
    song_id: int
    guild_id: Optional[int] = None

    def __init__(
        self,
        id: Optional[int],
        alias: str,
        title: str,
        song_id: int,
        guild_id: Optional[int],
    ) -> None:
        self.id = id
        self.alias = alias
        self.title = title
        self.song_id = song_id
        self.guild_id = guild_id


class UtilsCog(commands.Cog, name="Utils"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot
        self.alias_cache: list[CachedAlias] = []

    async def cog_load(self) -> None:
        return await self._reload_alias_cache()

    async def _reload_alias_cache(self) -> None:
        async with self.bot.begin_db_session() as session:
            stmt = select(Song).options(joinedload(Song.aliases))
            songs = (await session.execute(stmt)).scalars().unique()

        for song in songs:
            self.alias_cache.append(
                CachedAlias(None, song.title, song.title, song.id, -1)
            )

            for alias in song.aliases:
                self.alias_cache.append(
                    CachedAlias(
                        alias.rowid,
                        alias.alias,
                        song.title,
                        alias.song_id,
                        alias.guild_id,
                    )
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

    async def annotate_song(self, record: T) -> T:
        song_id = record.extras.get(KEY_SONG_ID)

        if song_id is None and not isinstance(record, MusicRecord):
            raise MissingDetailedParams

        async with self.bot.begin_db_session() as session:
            if song_id is None:
                if not isinstance(record, MusicRecord):
                    raise MissingDetailedParams

                jacket_filename = record.jacket.split("/")[-1]
                stmt = select(Song).where(
                    (Song.title == record.title) & (Song.jacket == jacket_filename)
                )
                song = (await session.execute(stmt)).scalar_one_or_none()
            else:
                stmt = select(Song).where(Song.id == song_id)
                song = (await session.execute(stmt)).scalar_one_or_none()

            if song is None:
                logger.warn(f"Missing song data for song title {record.title}")
                return record

            stmt = select(Chart).where(
                (Chart.song_id == song.id)
                & (Chart.difficulty == record.difficulty.short_form())
            )
            chart = (await session.execute(stmt)).scalar_one_or_none()

        if chart is None:
            logger.warn(
                f"Missing chart data for song ID {song.id}, difficulty {record.difficulty}"
            )
            return record

        record.extras[KEY_LEVEL] = chart.level

        if chart.const is None:
            try:
                internal_level = record.extras[KEY_INTERNAL_LEVEL] = float(
                    chart.level.replace("+", ".5")
                )
            except ValueError:
                internal_level = record.extras[KEY_INTERNAL_LEVEL] = 0
        else:
            internal_level = record.extras[KEY_INTERNAL_LEVEL] = chart.const

        record.extras[KEY_PLAY_RATING] = calculate_rating(record.score, internal_level)
        record.extras[KEY_OVERPOWER_BASE] = calculate_overpower_base(
            record.score, internal_level
        )
        record.extras[KEY_OVERPOWER_MAX] = calculate_overpower_max(internal_level)

        if chart.maxcombo is not None:
            record.extras[KEY_TOTAL_COMBO] = chart.maxcombo

        return record

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
        aliases = [
            x for x in self.alias_cache if x.guild_id == -1 or x.guild_id == guild_id
        ]
        (_, similarity, index) = process.extractOne(
            query,
            [x.alias for x in aliases],
            scorer=fuzz.QRatio,
            processor=str.lower,
        )
        matching_alias = aliases[index]

        async with self.bot.begin_db_session() as session:
            condition = Song.id == matching_alias.song_id

            if worlds_end:
                condition = (Song.title == matching_alias.title) & (
                    Song.genre == "WORLD'S END"
                )

            stmt = select(Song).where(condition)
            song = (await session.execute(stmt)).scalar_one_or_none()

            if matching_alias.id is not None:
                stmt = select(Alias).where(Alias.rowid == matching_alias.id)
                alias = (await session.execute(stmt)).scalar_one_or_none()
            else:
                alias = None

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
