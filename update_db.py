import re
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


CHUNITHM_CATCODES = {
    "POPS & ANIME": 0,
    "POPS&ANIME": 0,
    "niconico": 2,
    "東方Project": 3,
    "VARIETY": 6,
    "イロドリミドリ": 7,
    "ゲキマイ": 9,
    "ORIGINAL": 5,
}

MANUAL_MAPPINGS = {
    "1bc5d471609c4d10": {
        "id": 8166,
        "catname": "ORIGINAL",
        "image": "0511952ab823d845.jpg",
    },
    "7a561ab609a0629d": {
        "id": 8227,
        "catname": "ORIGINAL",
        "image": "168de844aeef254b.jpg",
    },
    "e6605126a95c4c8d": {
        "id": 8228,
        "catname": "ORIGINAL",
        "image": "1195656064a159f0.jpg",
    },
}
for idx, random in enumerate(
    [
        "d8b8af2016eec2f0",
        "5a0bc7702113a633",
        "948e0c4b67f4269d",
        "56e583c091b4295c",
        "49794fec968b90ba",
        "b9df9d9d74b372d9",
    ]
):
    MANUAL_MAPPINGS[random] = {
        "id": 8244 + idx,
        "catname": "VARIETY",
        "image": "ca580486c86bd49b.jpg",
    }

WORLD_END_REGEX = re.compile(r"【.{1,2}】$", re.MULTILINE)


def normalize_title(title: str, remove_we_kanji: bool = False) -> str:
    title = (
        title.lower()
        .replace(" ", " ")
        .replace("　", " ")
        .replace(" ", " ")
        .replace("：", ":")
        .replace("（", "(")
        .replace("）", ")")
        .replace("！", "!")
        .replace("？", "?")
        .replace("`", "'")
        .replace("’", "'")
        .replace("”", '"')
        .replace("“", '"')
        .replace("～", "~")
        .replace("－", "-")
        .replace("＠", "@")
    )
    if remove_we_kanji:
        title = WORLD_END_REGEX.sub("", title)
    return title


async def update_db(db: aiosqlite.Connection):
    async with aiohttp.ClientSession() as client:
        resp = await client.get(
            f"https://api.chunirec.net/2.0/music/showall.json?token={cfg['CHUNIREC_TOKEN']}&region=jp2"
        )
        chuni_resp = await client.get(
            "https://chunithm.sega.jp/storage/json/music.json"
        )
        songs = ChunirecSong.schema().loads(await resp.text(), many=True)
        chuni_songs = await chuni_resp.json()

    with (BOT_DIR / "database" / "schema.sql").open() as f:
        await db.executescript(f.read())

    inserted_songs = []
    inserted_charts = []
    for song in songs:
        chunithm_id = -1
        chunithm_catcode = -1
        jacket = ""
        try:
            if song.meta.id in MANUAL_MAPPINGS:
                chunithm_song = MANUAL_MAPPINGS[song.meta.id]
            elif song.data.WE is None:
                chunithm_song = next(
                    x
                    for x in chuni_songs
                    if normalize_title(x["title"]) == normalize_title(song.meta.title)
                    and CHUNITHM_CATCODES[x["catname"]]
                    == CHUNITHM_CATCODES[song.meta.genre]
                )
            else:
                chunithm_song = next(
                    x
                    for x in chuni_songs
                    if normalize_title(f"{x['title']}【{x['we_kanji']}】")
                    == normalize_title(song.meta.title)
                )
            chunithm_id = int(chunithm_song["id"])
            chunithm_catcode = int(CHUNITHM_CATCODES[chunithm_song["catname"]])
            jacket = chunithm_song["image"]
        except StopIteration:
            print(f"Couldn't find {song.meta}")

        if not jacket:
            try:
                chunithm_song = next(
                    x
                    for x in chuni_songs
                    if normalize_title(x["title"])
                    == normalize_title(song.meta.title, True)
                    and normalize_title(x["artist"])
                    == normalize_title(song.meta.artist)
                )
                jacket = chunithm_song["image"]
            except StopIteration:
                pass

        inserted_songs.append(
            (
                song.meta.id,
                chunithm_id,
                song.meta.title,
                chunithm_catcode,
                song.meta.genre,
                song.meta.artist,
                song.meta.release,
                song.meta.bpm,
                jacket,
            )
        )
        for difficulty in ["BAS", "ADV", "EXP", "MAS", "ULT", "WE"]:
            if (chart := getattr(song.data, difficulty)) is not None:
                inserted_charts.append(
                    (
                        song.meta.id,
                        difficulty,
                        chart.level,
                        chart.const,
                        chart.maxcombo,
                        chart.is_const_unknown,
                    )
                )
    await db.executemany(
        "INSERT INTO chunirec_songs(id, chunithm_id, title, chunithm_catcode, genre, artist, release, bpm, jacket) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)"
        "ON CONFLICT(id) DO UPDATE SET title=excluded.title,chunithm_catcode=excluded.chunithm_catcode,genre=excluded.genre,artist=excluded.artist,release=excluded.release,bpm=excluded.bpm,jacket=excluded.jacket",
        inserted_songs,
    )
    await db.executemany(
        "INSERT INTO chunirec_charts(song_id, difficulty, level, const, maxcombo, is_const_unknown) VALUES(?, ?, ?, ?, ?, ?)"
        "ON CONFLICT(song_id, difficulty) DO UPDATE SET level=excluded.level,const=excluded.const,maxcombo=excluded.maxcombo,is_const_unknown=excluded.is_const_unknown",
        inserted_charts,
    )
    await db.commit()


async def main():
    async with aiosqlite.connect(BOT_DIR / "database" / "database.sqlite3") as db:
        await update_db(db)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
