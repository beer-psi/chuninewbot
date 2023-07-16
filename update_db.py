import re
from dataclasses import dataclass
from html import unescape
from typing import Optional

import aiohttp
import aiosqlite
from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
from bs4.element import Comment
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


@dataclass_json
@dataclass
class ZetarakuSong:
    title: str
    imageName: str


@dataclass_json
@dataclass
class ZetarakuChunithmData:
    songs: list[ZetarakuSong]


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

MANUAL_MAPPINGS: dict[str, dict[str, str]] = {
    "1bc5d471609c4d10": {
        "id": "8166",
        "catname": "ORIGINAL",
        "image": "0511952ab823d845.jpg",
    },
    "7a561ab609a0629d": {
        "id": "8227",
        "catname": "ORIGINAL",
        "image": "168de844aeef254b.jpg",
    },
    "e6605126a95c4c8d": {
        "id": "8228",
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
        "id": str(8244 + idx),
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


async def update_aliases(db: aiosqlite.Connection):
    async with aiohttp.ClientSession() as client:
        resp = await client.get(
            "https://github.com/lomotos10/GCM-bot/raw/main/data/aliases/en/chuni.tsv"
        )
        aliases = [x.split("\t") for x in (await resp.text()).splitlines()]

    inserted_aliases = []
    for alias in aliases:
        if len(alias) < 2:
            continue
        title = alias[0]
        async with db.execute(
            "SELECT id FROM chunirec_songs WHERE title = ?", (title,)
        ) as cursor:
            song_id = await cursor.fetchone()
        if song_id is None:
            continue
        inserted_aliases.extend([(x, song_id[0]) for x in alias[1:]])
    await db.executemany(
        "INSERT INTO aliases (alias, guild_id, song_id) VALUES (?, -1, ?)"
        "ON CONFLICT (alias, guild_id) DO UPDATE SET song_id = excluded.song_id",
        inserted_aliases,
    )
    await db.commit()


async def update_sdvxin(db: aiosqlite.Connection):
    categories = [
        "pops",
        "niconico",
        "toho",
        "variety",
        "irodorimidori",
        "gekimai",
        "original",
        "ultima",
    ]
    difficulties = {
        "B": "BAS",
        "A": "ADV",
        "E": "EXP",
        "M": "MAS",
        "U": "ULT",
        "W": "WE",
    }
    title_mapping = {
        "めいど・うぃず・どらごんず": "めいど・うぃず・どらごんず♥",
        "失礼しますが、RIP": "失礼しますが、RIP♡",
        "Ray ?はじまりのセカイ?": "Ray ―はじまりのセカイ― (クロニクルアレンジver.)",
        "ラブって?ジュエリー♪えんじぇる☆ブレイク！！": "ラブって♡ジュエリー♪えんじぇる☆ブレイク！！",
        "Daydream cafe": "Daydream café",
        "多重未来のカルテット": "多重未来のカルテット -Quartet Theme-",
        "崩壊歌姫": "崩壊歌姫 -disruptive diva-",
        "Seyana": "Seyana. ～何でも言うことを聞いてくれるアカネチャン～",
        "ECHO-": "ECHO",
        "Little ”Sister” Bitch": 'Little "Sister" Bitch',
        "ナイト・オブ・ナイツ (かめりあ’s“": "ナイト・オブ・ナイツ (かめりあ’s“ワンス・アポン・ア・ナイト”Remix)",
        "Pump": "Pump!n",
        "チルノおかん": "チルノおかんのさいきょう☆バイブスごはん",
        "キュアリアス光吉古牌　?祭?": "キュアリアス光吉古牌　－祭－",
        "Yet Another ''drizzly rain''": "Yet Another ”drizzly rain”",
        "DAZZLING SEASON": "DAZZLING♡SEASON",
        "Super Lovely": "Super Lovely (Heavenly Remix)",
        "Mass Destruction (''P3'' + ''P3F'' ver.)": 'Mass Destruction ("P3" + "P3F" ver.)',
        "ouroboros": "ouroboros -twin stroke of the end-",
        "In The Blue Sky ’01": "In The Blue Sky '01",
        "Aventyr": "Äventyr",
        "Reach for the Stars": "Reach For The Stars",
        "”STAR”T": '"STAR"T',
        "一世嬉遊曲": "一世嬉遊曲‐ディヴェルティメント‐",
        "光線チューニング～なずな": "光線チューニング ～なずな妄想海フェスイメージトレーニングVer.～",
        "ウソテイ": "イロドリミドリ杯花映塚全一決定戦公式テーマソング『ウソテイ』",
        "ＧＯ！ＧＯ！ラブリズム ～あーりん書類審査通過記念Ver.～": "ＧＯ！ＧＯ！ラブリズム♥ ～あーりん書類審査通過記念Ver.～",
        "Session High": "Session High⤴",
        "Help,me あーりん！": "Help me, あーりん！",
        "私の中の幻想的世界観": "私の中の幻想的世界観及びその顕現を想起させたある現実での出来事に関する一考察",
        "GRANDIR": "GRÄNDIR",
        "AstroNotes.": "AstrøNotes.",
        "まっすぐ→→→ストリーム!": "まっすぐ→→→ストリーム！",
        "GranFatalite": "GranFatalité",
        "Excalibur": "Excalibur ～Revived resolution～",
        "DON’T STOP ROCKIN’ ～[O_O] MIX～": "D✪N’T ST✪P R✪CKIN’ ～[✪_✪] MIX～",
        "L'epilogue": "L'épilogue",
        "Give me Love?": "Give me Love♡",
        "Athlete Killer ”Meteor”": 'Athlete Killer "Meteor"',
        "萌豚功夫大乱舞": "萌豚♥功夫♥大乱舞",
        "Jorqer": "Jörqer",
        "Walzer fur das Nichts": "Walzer für das Nichts",
        "Solstand": "Solstånd",
        "男装女形表裏一体発狂小娘": "男装女形表裏一体発狂小娘の詐称疑惑と苦悩と情熱。",
        "NYAN-NYA, More! ラブシャイン、Chu?": "NYAN-NYA, More! ラブシャイン、Chu♥",
        "今ぞ崇め奉れ☆オマエらよ！！～姫の秘メタル渇望～": "今ぞ♡崇め奉れ☆オマエらよ！！～姫の秘メタル渇望～",
        "砂漠のハンティングガール": "砂漠のハンティングガール♡",
    }
    # sdvx.in ID, song_id, difficulty
    inserted_data: list[tuple[str, str, str]] = []
    limiter = AsyncLimiter(3, 1)
    async with limiter, aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=600)
    ) as client:
        for category in categories:
            resp = await client.get(f"https://sdvx.in/chunithm/sort/{category}.htm")
            soup = BeautifulSoup(await resp.text(), "lxml")

            table = soup.select_one("table:has(td.tbgl)")
            if table is None:
                print(f"Could not find table for category {category}")
                continue
            scripts = table.select("script[src]")
            for script in scripts:
                title = next(
                    (str(x) for x in script.next_elements if isinstance(x, Comment)),
                    None,
                )
                if title is None:
                    continue
                title = title_mapping.get(title, unescape(title))
                sdvx_in_id = str(script["src"]).split("/")[-1][
                    :5
                ]  # FIXME: dont assume the ID is always 5 digits
                async with db.execute(
                    "SELECT id FROM chunirec_songs WHERE title = ?", (title,)
                ) as cursor:
                    song_id = await cursor.fetchone()
                if song_id is None:
                    print(f"Could not find song with title {title}")
                    continue

                script_resp = await client.get(f"https://sdvx.in{script['src']}")
                script_data = await script_resp.text()

                for line in script_data.splitlines():
                    if not line.startswith(f"var LV{sdvx_in_id}"):
                        continue

                    key, value = line.split("=", 1)
                    difficulty = difficulties[key[-1]]
                    value_soup = BeautifulSoup(
                        value.removeprefix('"').removesuffix('";'), "lxml"
                    )
                    if value_soup.select_one("a") is None:
                        continue
                    inserted_data.append((sdvx_in_id, song_id[0], difficulty))
    await db.executemany(
        "INSERT INTO sdvxin (id, song_id, difficulty) VALUES (?, ?, ?)"
        "ON CONFLICT (id, difficulty) DO NOTHING",
        inserted_data,
    )
    await db.commit()


async def update_db(db: aiosqlite.Connection):
    async with aiohttp.ClientSession() as client:
        resp = await client.get(
            f"https://api.chunirec.net/2.0/music/showall.json?token={cfg['CHUNIREC_TOKEN']}&region=jp2"
        )
        chuni_resp = await client.get(
            "https://chunithm.sega.jp/storage/json/music.json"
        )
        zetaraku_resp = await client.get(
            "https://dp4p6x0xfi5o9.cloudfront.net/chunithm/data.json"
        )
        songs = ChunirecSong.schema().loads(await resp.text(), many=True)  # type: ignore
        chuni_songs: list[dict[str, str]] = await chuni_resp.json()
        zetaraku_songs: ZetarakuChunithmData = ZetarakuChunithmData.from_json(await zetaraku_resp.text())  # type: ignore

    inserted_songs = []
    inserted_charts = []
    for song in songs:
        chunithm_id = -1
        chunithm_catcode = -1
        jacket = ""
        chunithm_song: dict[str, str] = {}
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
                    (
                        x
                        for x in chuni_songs
                        if normalize_title(x["title"])
                        == normalize_title(song.meta.title, True)
                        and normalize_title(x["artist"])
                        == normalize_title(song.meta.artist)
                    ),
                    {},
                )
                jacket = chunithm_song.get("image")
            except StopIteration:
                pass

        zetaraku_song = next(
            (
                x
                for x in zetaraku_songs.songs
                if normalize_title(x.title) == normalize_title(song.meta.title)
            ),
            None,
        )
        if zetaraku_song is not None:
            zetaraku_jacket = zetaraku_song.imageName
        else:
            zetaraku_jacket = ""

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
                zetaraku_jacket,
            )
        )
        for difficulty in ["BAS", "ADV", "EXP", "MAS", "ULT", "WE"]:
            if (chart := getattr(song.data, difficulty)) is not None:
                if chart.level <= 9.5:
                    chart.const = chart.level
                    chart.is_const_unknown = 0

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
        "INSERT INTO chunirec_songs(id, chunithm_id, title, chunithm_catcode, genre, artist, release, bpm, jacket, zetaraku_jacket) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        "ON CONFLICT(id) DO UPDATE SET title=excluded.title,chunithm_catcode=excluded.chunithm_catcode,genre=excluded.genre,artist=excluded.artist,release=excluded.release,bpm=excluded.bpm,jacket=excluded.jacket,zetaraku_jacket=excluded.zetaraku_jacket",
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
        with (BOT_DIR / "database" / "schema.sql").open() as f:
            await db.executescript(f.read())
        await update_db(db)
        # await update_aliases(db)
        # await update_sdvxin(db)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
