from math import floor
from datetime import time, timezone

import aiohttp
from async_lru import alru_cache
from discord.ext import commands, tasks

from bot import ChuniBot
from update_chunirec import ChunirecSong
from api.record import RecentRecord, DetailedRecentRecord
from utils.rating_calculator import calculate_rating


class UtilsCog(commands.Cog, name="Utils"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot

    @alru_cache(maxsize=256)
    async def fetch_cookie(self, id: int) -> str | None:
        cursor = await self.bot.db.execute(
            "SELECT cookie FROM cookies WHERE discord_id = ?", (id,)
        )
        clal = await cursor.fetchone()
        if clal is None:
            return None

        return clal[0]
    
    async def annotate_song(self, song: RecentRecord | DetailedRecentRecord):
        cursor = await self.bot.db.execute("SELECT * FROM chunirec_songs WHERE title = ?", (song.title,))
        song_data = await cursor.fetchone()
        if song_data is None:
            return
        id = song_data[0]

        cursor = await self.bot.db.execute("SELECT * FROM chunirec_charts WHERE song_id = ? AND difficulty = ?", (id, song.difficulty.short_form()))
        chart_data = await cursor.fetchone()
        if chart_data is None:
            return
        song.internal_level = chart_data[4]
        
        level = chart_data[3]
        song.level = str(floor(level)) + ("+" if level * 10 % 10 >= 5 else "")
        song.unknown_const = bool(chart_data[6])

        if not song.unknown_const:
            song.play_rating = calculate_rating(song.score, song.internal_level)

        if isinstance(song, DetailedRecentRecord) and chart_data[5] != 0:
            song.full_combo = chart_data[5]
    

    @tasks.loop(time=time(hour=3, minute=10, tzinfo=timezone.utc))
    async def update_chunirec_db(self):
        async with aiohttp.ClientSession() as client:
            resp = await client.get(f"https://api.chunirec.net/2.0/music/showall.json?token={self.bot.cfg['CHUNIREC_TOKEN']}&region=jp2")
            songs = ChunirecSong.schema().loads(await resp.text(), many=True)
        
        inserted_songs = []
        inserted_charts = []
        for song in songs:
            inserted_songs.append((song.meta.id, song.meta.title, song.meta.genre, song.meta.artist, song.meta.release, song.meta.bpm))
            for difficulty in ["BAS", "ADV", "EXP", "MAS", "ULT", "WE"]:
                if (chart := getattr(song.data, difficulty)) is not None:
                    inserted_charts.append((song.meta.id, difficulty, chart.level, chart.const, chart.maxcombo, chart.is_const_unknown))
        await self.bot.db.executemany("INSERT INTO chunirec_songs(id, title, genre, artist, release, bpm) VALUES(?, ?, ?, ?, ?, ?)", inserted_songs)
        await self.bot.db.executemany("INSERT INTO chunirec_charts(song_id, difficulty, level, const, maxcombo, is_const_unknown) VALUES(?, ?, ?, ?, ?, ?)", inserted_charts)
        await self.bot.db.commit()


async def setup(bot: ChuniBot):
    await bot.add_cog(UtilsCog(bot))
