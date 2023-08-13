import re
from dataclasses import dataclass
from html import unescape
from typing import Optional

import aiohttp
from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
from bs4.element import Comment
from dataclasses_json import dataclass_json
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot import BOT_DIR, cfg
from database.models import Alias, Base, Chart, SdvxinChartView, Song


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
    "7a561ab609a0629d": {  # Trackless wilderness【狂】
        "id": "8227",
        "catname": "ORIGINAL",
        "title": "Trackless wilderness",
        "we_kanji": "狂",
        "we_star": "7",
        "image": "629be924b3383e08.jpg",
    },
    "e6605126a95c4c8d": {  # Trrricksters!!【狂】
        "id": "8228",
        "catname": "ORIGINAL",
        "title": "Trrricksters!!",
        "we_kanji": "狂",
        "we_star": "9",
        "image": "7615de9e9eced518.jpg",
    },
    "c2d66153dca3823f": {
        "id": "8025",
        "catname": "イロドリミドリ",
        "title": "Help me, あーりん！",
        "we_kanji": "嘘",
        "we_star": "5",
        "image": "c1ff8df1757fedf4.jpg",
    },
    "2678230924ec08dd": {
        "id": "8078",
        "catname": "イロドリミドリ",
        "title": "あねぺったん",
        "we_kanji": "嘘",
        "we_star": "7",
        "image": "a6889b8a729210be.jpg",
    },
    "7252bf5ea6ff6294": {
        "id": "8116",
        "catname": "イロドリミドリ",
        "title": "イロドリミドリ杯花映塚全一決定戦公式テーマソング『ウソテイ』",
        "we_kanji": "嘘",
        "we_star": "7",
        "image": "43bd6cbc31e4c02c.jpg",
    },
}
for idx, random in enumerate(
    # Random WE, A through F
    [
        ("d8b8af2016eec2f0", "97af9ed62e768d73.jpg"),
        ("5a0bc7702113a633", "fd4a488ed2bc67d8.jpg"),
        ("948e0c4b67f4269d", "ce911dfdd8624a7c.jpg"),
        ("56e583c091b4295c", "6a3201f1b63ff9a3.jpg"),
        ("49794fec968b90ba", "d43ab766613ba19e.jpg"),
        ("b9df9d9d74b372d9", "4a359278c6108748.jpg"),
    ]
):
    random_id, random_image = random
    MANUAL_MAPPINGS[random_id] = {
        "id": str(8244 + idx),
        "catname": "VARIETY",
        "title": "Random",
        "we_kanji": f"分{chr(65 + idx)}",
        "we_star": "5",
        "image": random_image,
    }

WORLD_END_REGEX = re.compile(r"【(.{1,2})】$", re.MULTILINE)


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


async def update_aliases(async_session: async_sessionmaker[AsyncSession]):
    async with aiohttp.ClientSession() as client, async_session() as session, session.begin():
        resp = await client.get(
            "https://github.com/lomotos10/GCM-bot/raw/main/data/aliases/en/chuni.tsv"
        )
        aliases = [x.split("\t") for x in (await resp.text()).splitlines()]

        inserted_aliases = []
        for alias in aliases:
            if len(alias) < 2:
                continue
            title = alias[0]

            song = (
                await session.execute(
                    select(Song)
                    # Limit to non-WE entries. WE entries are redirected to
                    # their non-WE respectives when song-searching anyways.
                    .where((Song.title == title) & (Song.chunithm_id < 8000))
                )
            ).scalar_one_or_none()
            if song is None:
                continue

            inserted_aliases.extend(
                [
                    dict(alias=x, guild_id=-1, song_id=song.id, owner_id=None)
                    for x in alias[1:]
                ]
            )

        insert_statement = insert(Alias).values(inserted_aliases)
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[Alias.alias, Alias.guild_id],
            set_={"song_id": insert_statement.excluded.song_id},
        )
        await session.execute(upsert_statement)


async def update_sdvxin(async_session: async_sessionmaker[AsyncSession]):
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
    inserted_data: list[dict] = []
    limiter = AsyncLimiter(3, 1)
    async with limiter, aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=600)
    ) as client, async_session() as session, session.begin():
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

                song = (
                    await session.execute(
                        select(Song)
                        # Limit to non-WE charts. WE charts have their own section.
                        .where((Song.title == title) & (Song.chunithm_id < 8000))
                    )
                ).scalar_one_or_none()
                if song is None:
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
                    inserted_data.append(
                        dict(id=sdvx_in_id, song_id=song.id, difficulty=difficulty)
                    )

        stmt = insert(SdvxinChartView).values(inserted_data).on_conflict_do_nothing()
        await session.execute(stmt)


async def update_db(async_session: async_sessionmaker[AsyncSession]):
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
            return

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
            dict(
                id=song.meta.id,
                chunithm_id=chunithm_id,
                # Don't use song.meta.title
                title=chunithm_song["title"],
                chunithm_catcode=chunithm_catcode,
                genre=song.meta.genre,
                artist=song.meta.artist,
                release=song.meta.release,
                bpm=None if song.meta.bpm == 0 else song.meta.bpm,
                jacket=jacket,
                zetaraku_jacket=zetaraku_jacket,
            )
        )
        for difficulty in ["BAS", "ADV", "EXP", "MAS", "ULT"]:
            if (chart := getattr(song.data, difficulty)) is not None:
                if 0 < chart.level <= 9.5:
                    chart.const = chart.level
                    chart.is_const_unknown = 0

                inserted_charts.append(
                    dict(
                        song_id=song.meta.id,
                        difficulty=difficulty,
                        level=str(chart.level).replace(".5", "+").replace(".0", ""),
                        const=None if chart.is_const_unknown == 1 else chart.const,
                        maxcombo=chart.maxcombo if chart.maxcombo != 0 else None,
                    )
                )

        if (chart := getattr(song.data, "WE")) is not None:
            we_stars = ""
            for _ in range(-1, int(chunithm_song["we_star"]), 2):
                we_stars += "☆"
            inserted_charts.append(
                dict(
                    song_id=song.meta.id,
                    difficulty="WE",
                    level=chunithm_song["we_kanji"] + we_stars,
                    const=None,
                    maxcombo=chart.maxcombo if chart.maxcombo != 0 else None,
                )
            )

    async with async_session() as session, session.begin():
        insert_statement = insert(Song).values(inserted_songs)
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[Song.id],
            set_=dict(
                title=insert_statement.excluded.title,
                chunithm_catcode=insert_statement.excluded.chunithm_catcode,
                genre=insert_statement.excluded.genre,
                artist=insert_statement.excluded.artist,
                release=insert_statement.excluded.release,
                bpm=insert_statement.excluded.bpm,
                jacket=insert_statement.excluded.jacket,
                zetaraku_jacket=insert_statement.excluded.zetaraku_jacket,
            ),
        )
        await session.execute(upsert_statement)

        insert_statement = insert(Chart).values(inserted_charts)
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[Chart.song_id, Chart.difficulty],
            set_=dict(
                level=insert_statement.excluded.level,
                const=insert_statement.excluded.const,
                maxcombo=insert_statement.excluded.maxcombo,
            ),
        )
        await session.execute(upsert_statement)


# async def update_cc_from_data(db: aiosqlite.Connection, music_paths: list[Path]):
#     inserted_charts = []

#     for music_path in music_paths:
#         for item in music_path.iterdir():
#             tree = ElementTree.parse(item / "Music.xml")
#             root = tree.getroot()

#             chunithm_id = int(root.find("./name/id").text)
#             async with db.execute(
#                 "SELECT id FROM chunirec_songs WHERE chunithm_id = ?",
#                 (chunithm_id,),
#             ) as cursor:
#                 song = await cursor.fetchone()

#             if song is None:
#                 print(f"Could not find song with chunithm_id {chunithm_id}")
#                 continue

#             charts = await db.execute_fetchall("SELECT * FROM chunirec_charts WHERE song_id = ?", (song[0],))
#             for chart in zip(charts, root.findall("./fumens/MusicFumenData[enable='true']")):
#                 pass


async def main():
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///" + str(BOT_DIR / "database" / "database.sqlite3")
    )
    async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await update_db(async_session)
    await update_aliases(async_session)
    await update_sdvxin(async_session)

    await engine.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
