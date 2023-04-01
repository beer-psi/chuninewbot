from datetime import time, timezone
from math import floor
from typing import overload

from async_lru import alru_cache
from discord.ext import commands, tasks
from discord.ext.commands import Context

from api.enums import Rank
from api.record import DetailedRecentRecord, MusicRecord, Record
from bot import ChuniBot
from update_db import update_db
from utils.rating_calculator import calculate_rating


class UtilsCog(commands.Cog, name="Utils"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot

    async def login_check(self, ctx: Context) -> str:
        clal = await self.fetch_cookie(ctx.author.id)
        if clal is None:
            raise commands.BadArgument(
                "You are not logged in. Please use `!login <cookie>` in DMs to log in."
            )
        return clal

    @alru_cache()
    async def fetch_cookie(self, id: int) -> str | None:
        cursor = await self.bot.db.execute(
            "SELECT cookie FROM cookies WHERE discord_id = ?", (id,)
        )
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
            cursor = await self.bot.db.execute(
                "SELECT id FROM chunirec_songs WHERE chunithm_id = ?",
                (song.detailed.idx,),
            )
            song_data = await cursor.fetchone()
            if song_data is None:
                return MusicRecord.from_record(song)
            id = song_data[0]
            _song: MusicRecord = MusicRecord.from_record(song)

            _song.rank = Rank.from_score(song.score)
        else:
            cursor = await self.bot.db.execute(
                "SELECT id FROM chunirec_songs WHERE title = ? AND jacket = ?",
                (song.title, song.jacket.split("/")[-1]),
            )
            song_data = await cursor.fetchone()
            if song_data is None:
                return song
            id = song_data[0]
            _song = song

        cursor = await self.bot.db.execute(
            "SELECT level, const, maxcombo, is_const_unknown FROM chunirec_charts WHERE song_id = ? AND difficulty = ?",
            (id, song.difficulty.short_form()),
        )
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
        return _song

    # maimai and CHUNITHM NET goes under maintenance every day at 2:00 AM JST, so we update the DB then
    @tasks.loop(time=time(hour=17, tzinfo=timezone.utc))
    async def update_chunirec_db(self):
        # Disable all commands while updating the DB
        for cmd in self.bot.walk_commands():
            cmd.enabled = False
        await update_db(self.bot.db)
        # Re-enable all commands
        for cmd in self.bot.walk_commands():
            cmd.enabled = True


async def setup(bot: ChuniBot):
    await bot.add_cog(UtilsCog(bot))
