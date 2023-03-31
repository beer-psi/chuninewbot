from dataclasses import dataclass
from typing import Optional

import aiohttp
import aiosqlite
from dataclasses_json import dataclass_json

from bot import BOT_DIR, cfg


@dataclass_json
@dataclass
class ChunirecMeta:
    id: str
    title: str
    genre: str
    artist: str
    release: str
    bpm: int


@dataclass_json
@dataclass
class ChunirecDifficulty:
    level: float
    const: float
    maxcombo: int
    is_const_unknown: int


@dataclass_json
@dataclass
class ChunirecData:
    BAS: Optional[ChunirecDifficulty] = None
    ADV: Optional[ChunirecDifficulty] = None
    EXP: Optional[ChunirecDifficulty] = None
    MAS: Optional[ChunirecDifficulty] = None
    ULT: Optional[ChunirecDifficulty] = None
    WE: Optional[ChunirecDifficulty] = None


@dataclass_json
@dataclass
class ChunirecSong:
    meta: ChunirecMeta
    data: ChunirecData


async def main():
    async with aiohttp.ClientSession() as client:
        resp = await client.get(f"https://api.chunirec.net/2.0/music/showall.json?token={cfg['CHUNIREC_TOKEN']}&region=jp2")
        songs = ChunirecSong.schema().loads(await resp.text(), many=True)
    
    async with aiosqlite.connect(BOT_DIR / "database" / "database.sqlite3") as db:
        with (BOT_DIR / "database" / "schema.sql").open() as f:
            await db.executescript(f.read())
        
        inserted_songs = []
        inserted_charts = []
        for song in songs:
            inserted_songs.append((song.meta.id, song.meta.title, song.meta.genre, song.meta.artist, song.meta.release, song.meta.bpm))
            for difficulty in ["BAS", "ADV", "EXP", "MAS", "ULT", "WE"]:
                if (chart := getattr(song.data, difficulty)) is not None:
                    inserted_charts.append((song.meta.id, difficulty, chart.level, chart.const, chart.maxcombo, chart.is_const_unknown))
        await db.executemany("INSERT INTO chunirec_songs(id, title, genre, artist, release, bpm) VALUES(?, ?, ?, ?, ?, ?)", inserted_songs)
        await db.executemany("INSERT INTO chunirec_charts(song_id, difficulty, level, const, maxcombo, is_const_unknown) VALUES(?, ?, ?, ?, ?, ?)", inserted_charts)
        await db.commit()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
