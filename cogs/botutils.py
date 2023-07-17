from datetime import datetime
from math import floor
from typing import TYPE_CHECKING, Optional, overload

from discord.ext import commands
from discord.ext.commands import Context

from api.enums import Rank
from api.record import DetailedRecentRecord, MusicRecord, Record
from update_db import update_db
from utils.overpower_calculator import calculate_overpower_base, calculate_overpower_max
from utils.rating_calculator import calculate_rating
from utils.types import SongSearchResult

if TYPE_CHECKING:
    from bot import ChuniBot


class UtilsCog(commands.Cog, name="Utils"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot

    async def guild_prefix(self, ctx: Context) -> str:
        if ctx.guild is None:
            return self.bot.cfg.get("DEFAULT_PREFIX", "c>")  # type: ignore

        async with self.bot.db.execute(
            "SELECT prefix FROM guild_prefix WHERE guild_id = ?", (ctx.guild.id,)
        ) as cursor:
            prefix = await cursor.fetchone()
        return prefix[0] if prefix is not None else self.bot.cfg.get("DEFAULT_PREFIX", "c>")  # type: ignore

    async def login_check(self, ctx_or_id: Context | int) -> str:
        id = ctx_or_id if isinstance(ctx_or_id, int) else ctx_or_id.author.id
        clal = await self.fetch_cookie(id)
        if clal is None:
            raise commands.BadArgument(
                "You are not logged in. Please send `c>login` in my DMs to log in."
            )
        return clal

    async def fetch_cookie(self, id: int) -> str | None:
        async with self.bot.db.execute(
            "SELECT cookie FROM cookies WHERE discord_id = ?", (id,)
        ) as cursor:
            clal = await cursor.fetchone()
        if clal is None:
            return None

        return clal[0]

    @overload
    async def annotate_song(self, song: DetailedRecentRecord) -> DetailedRecentRecord:
        ...

    @overload
    async def annotate_song(self, song: Record | MusicRecord) -> MusicRecord:
        ...

    async def annotate_song(
        self, song: Record | MusicRecord | DetailedRecentRecord
    ) -> MusicRecord | DetailedRecentRecord:
        if isinstance(song, Record) and not (
            isinstance(song, MusicRecord) or isinstance(song, DetailedRecentRecord)
        ):
            if song.detailed is None:
                raise Exception("Cannot fetch song details without song.detailed.idx")
            async with self.bot.db.execute(
                "SELECT id, jacket FROM chunirec_songs WHERE chunithm_id = ?",
                (song.detailed.idx,),
            ) as cursor:
                song_data = await cursor.fetchone()
            if song_data is None:
                return MusicRecord.from_record(song)
            id = song_data[0]

            _song: MusicRecord = MusicRecord.from_record(song)
            _song.jacket = song_data[1]
            _song.rank = Rank.from_score(song.score)
        else:
            async with self.bot.db.execute(
                "SELECT id FROM chunirec_songs WHERE title = ? AND jacket = ?",
                (song.title, song.jacket),
            ) as cursor:
                song_data = await cursor.fetchone()
            if song_data is None:
                return song
            id = song_data[0]
            _song = song

        async with self.bot.db.execute(
            "SELECT level, const, maxcombo, is_const_unknown FROM chunirec_charts WHERE song_id = ? AND difficulty = ?",
            (id, song.difficulty.short_form()),
        ) as cursor:
            chart_data = await cursor.fetchone()
        if chart_data is None:
            return _song
        _song.internal_level = chart_data[1]

        level = chart_data[0]
        _song.level = str(floor(level)) + ("+" if level * 10 % 10 >= 5 else "")
        _song.unknown_const = bool(chart_data[3])

        _song.play_rating = calculate_rating(
            song.score, _song.internal_level if _song.internal_level != 0 else level
        )

        if isinstance(_song, DetailedRecentRecord) and chart_data[2] != 0:
            _song.full_combo = chart_data[2]

        _song.overpower_base = calculate_overpower_base(
            song.score, _song.internal_level if _song.internal_level != 0 else level
        )
        _song.overpower_max = calculate_overpower_max(
            _song.internal_level if _song.internal_level != 0 else level
        )

        return _song

    async def find_song(
        self, query: str, *, guild_id: Optional[int] = None
    ) -> SongSearchResult:
        """Finds the song that best matches a given query.

        Parameters
        ----------
        query: str
            The query to search for.
        guild_id: Optional[int]
            The ID of the guild to search for aliases in. If None, only global aliases are searched.

        Returns
        -------
        SongSearchResult
        """

        async with self.bot.db.execute(
            "SELECT jwsim(lower(title), ?) AS similarity, id, chunithm_id, title, genre, artist, release, bpm, jacket "
            "FROM chunirec_songs "
            "ORDER BY similarity DESC "
            "LIMIT 1",
            (query.lower(),),
        ) as cursor:
            song = await cursor.fetchone()
        assert song is not None

        similarity, id, chunithm_id, title, genre, artist, release, bpm, jacket = song
        alias = None
        if similarity < 0.9:
            where_clause = "WHERE aliases.guild_id = -1 "
            if guild_id is not None:
                where_clause += "OR aliases.guild_id = :guild_id "
            async with self.bot.db.execute(
                "SELECT jwsim(lower(aliases.alias), :query) AS similarity, id, chunithm_id, title, genre, artist, release, bpm, jacket, aliases.alias "
                "FROM chunirec_songs "
                "LEFT JOIN aliases ON aliases.song_id = chunirec_songs.id "
                + where_clause
                + "ORDER BY similarity DESC "
                "LIMIT 1",
                {"query": query.lower(), "guild_id": guild_id},
            ) as cursor:
                song = await cursor.fetchone()
            assert song is not None
            (
                similarity,
                id,
                chunithm_id,
                title,
                genre,
                artist,
                release,
                bpm,
                jacket,
                alias,
            ) = song
        return SongSearchResult(
            similarity=similarity,
            id=id,
            chunithm_id=chunithm_id,
            title=title,
            genre=genre,
            artist=artist,
            release=datetime.strptime(release, "%Y-%m-%d"),
            bpm=bpm,
            jacket=jacket,
            alias=alias,
        )

    # maimai and CHUNITHM NET goes under maintenance every day at 2:00 AM JST, so we update the DB then
    #
    # job is currently disabled until CHUNITHM SUN PLUS reaches international
    # @tasks.loop(time=time(hour=17, tzinfo=timezone.utc))
    async def update_chunirec_db(self):
        # Disable all commands while updating the DB
        for cmd in self.bot.walk_commands():
            cmd.enabled = False
        await update_db(self.bot.db)
        # Re-enable all commands
        for cmd in self.bot.walk_commands():
            cmd.enabled = True


async def setup(bot: "ChuniBot"):
    await bot.add_cog(UtilsCog(bot))
