import string
from datetime import timedelta
from pathlib import Path
from random import choices

import pytest
from aioresponses import aioresponses as original_aioresponses
from multidict import CIMultiDict

from chunithm_net import ChuniNet
from chunithm_net.entities.enums import ClearType, Difficulty, Genres, Possession, Rank
from chunithm_net.exceptions import (
    ChuniNetError,
    InvalidTokenException,
    MaintenanceException,
)

BASE_DIR = Path(__file__).parent


@pytest.fixture
def aioresponses():
    with original_aioresponses() as aior:
        yield aior


@pytest.fixture
def clal():
    return "".join(choices(string.ascii_lowercase + string.digits, k=64))


@pytest.fixture
def user_id():
    return "".join(choices(string.digits, k=15))


@pytest.fixture
def token():
    return "".join(choices("abcdef" + string.digits, k=32))


@pytest.mark.asyncio
async def test_client_throws_chuninet_errors(
    aioresponses: original_aioresponses, clal: str, user_id: str, token: str
):
    aioresponses.get(
        "https://chunithm-net-eng.com/mobile/home",
        status=302,
        headers={"Location": "https://chunithm-net-eng.com/mobile/error"},
    )

    with (BASE_DIR / "assets" / "100001.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/error",
            body=f.read(),
            content_type="text/html; charset=UTF-8",
            status=200,
        )

    with pytest.raises(ChuniNetError, match="Error code 100001: An error coccured."):
        async with ChuniNet(clal, user_id=user_id, token=token) as client:
            await client.authenticate()

    aioresponses.assert_called_once_with("https://chunithm-net-eng.com/mobile/home")


@pytest.mark.asyncio
async def test_client_throws_token_errors(
    aioresponses: original_aioresponses, clal: str
):
    aioresponses.get(
        "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/",
        status=200,
    )

    with pytest.raises(
        InvalidTokenException, match="Invalid cookie. Received status code was 200"
    ):
        async with ChuniNet(clal) as client:
            await client.validate_cookie()

    aioresponses.assert_called_once()


@pytest.mark.asyncio
async def test_client_throws_no_userid_cookie(
    aioresponses: original_aioresponses, clal: str
):
    aioresponses.get(
        "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/",
        status=302,
        headers={"Location": f"https://chunithm-net-eng.com/mobile/?ssid={clal}"},
    )

    aioresponses.get(
        f"https://chunithm-net-eng.com/mobile/?ssid={clal}",
        status=302,
        headers={"Location": "https://chunithm-net-eng.com/mobile/home/"},
    )

    with (BASE_DIR / "assets" / "logged_in_homepage.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home/",
            status=200,
            body=f.read(),
            content_type="text/html; charset=UTF-8",
        )

    # This was supposed to be a success but aioresponses doesn't mock
    # the cookie jar so this is the best we can do
    with pytest.raises(InvalidTokenException, match="No userId cookie found"):
        async with ChuniNet(clal) as client:
            await client.authenticate()

    aioresponses.assert_any_call(
        "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/"
    )
    aioresponses.assert_any_call(f"https://chunithm-net-eng.com/mobile/?ssid={clal}")


@pytest.mark.asyncio
async def test_client_reauthenticates_on_error(
    aioresponses: original_aioresponses, clal: str, user_id: str, token: str
):
    new_user_id = "".join(choices(string.digits, k=15))
    new_token = "".join(choices("abcdef" + string.digits, k=32))

    aioresponses.get(
        "https://chunithm-net-eng.com/mobile/home",
        status=302,
        headers={"Location": "https://chunithm-net-eng.com/mobile/error"},
    )

    with (BASE_DIR / "assets" / "200004.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/error",
            body=f.read(),
            content_type="text/html; charset=UTF-8",
            status=200,
        )

    aioresponses.get(
        "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/",
        status=302,
        headers={"Location": f"https://chunithm-net-eng.com/mobile/?ssid={clal}"},
    )

    aioresponses.get(
        f"https://chunithm-net-eng.com/mobile/?ssid={clal}",
        status=302,
        headers=CIMultiDict(
            [
                ("Location", "https://chunithm-net-eng.com/mobile/home/"),
                (
                    "Set-Cookie",
                    f"_t={new_token}; expires=Thu, 11-Aug-2033 13:09:40 GMT; Max-Age=315360000; path=/; SameSite=Strict",
                ),
                (
                    "Set-Cookie",
                    f"userId={new_user_id}; path=/; secure; HttpOnly; SameSite=Lax",
                ),
            ]
        ),
    )

    with (BASE_DIR / "assets" / "logged_in_homepage.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home/",
            status=200,
            body=f.read(),
            content_type="text/html; charset=UTF-8",
        )

    async with ChuniNet(clal, user_id=user_id, token=token) as client:
        await client.authenticate()

    aioresponses.assert_any_call("https://chunithm-net-eng.com/mobile/home")
    aioresponses.assert_any_call(
        "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/"
    )


@pytest.mark.asyncio
async def test_client_handles_failed_reauthentication(
    aioresponses: original_aioresponses,
    clal: str,
    user_id: str,
    token: str,
):
    aioresponses.get(
        "https://chunithm-net-eng.com/mobile/home",
        status=302,
        headers={"Location": "https://chunithm-net-eng.com/mobile/"},
    )

    with (BASE_DIR / "assets" / "stupid_way_to_redirect.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/", status=200, body=f.read()
        )

    aioresponses.get(
        "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/",
        status=200,
    )

    with pytest.raises(
        InvalidTokenException, match="Invalid cookie. Received status code was 200"
    ):
        async with ChuniNet(clal, user_id=user_id, token=token) as client:
            await client.authenticate()


@pytest.mark.asyncio
async def test_client_throws_when_on_maintenance(
    aioresponses: original_aioresponses,
    clal: str,
    user_id: str,
    token: str,
):
    aioresponses.get(
        "https://chunithm-net-eng.com/mobile/home",
        status=503,
    )

    with pytest.raises(MaintenanceException):
        async with ChuniNet(clal, user_id=user_id, token=token) as client:
            await client.authenticate()


@pytest.mark.asyncio
async def test_client_parses_homepage(
    aioresponses: original_aioresponses,
    clal: str,
    user_id: str,
    token: str,
):
    with (BASE_DIR / "assets" / "logged_in_homepage.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home",
            status=200,
            body=f.read(),
        )

    async with ChuniNet(clal, user_id=user_id, token=token) as client:
        user_data = await client.authenticate()

    assert user_data.possession == Possession.NONE

    assert (
        user_data.character
        == "https://chunithm-net-eng.com/mobile/img/2c20c7ac326c1a9d.png"
    )
    assert user_data.name == "ＢｏＡｎｈＤＬＢ"  # noqa: RUF001

    assert (
        user_data.avatar.base
        == "https://new.chunithm-net.com/chuni-mobile/html/mobile/images/avatar_base.png"
    )
    assert (
        user_data.avatar.back
        == "https://chunithm-net-eng.com/mobile/img/5a278974114ddee5.png"
    )
    assert (
        user_data.avatar.skinfoot_r
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_Skin.png"
    )
    assert (
        user_data.avatar.skinfoot_l
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_Skin.png"
    )
    assert (
        user_data.avatar.skin
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_Skin.png"
    )
    assert (
        user_data.avatar.wear
        == "https://chunithm-net-eng.com/mobile/img/db379cd92224154d.png"
    )
    assert (
        user_data.avatar.face
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_Face.png"
    )
    assert (
        user_data.avatar.face_cover
        == "https://chunithm-net-eng.com/mobile/img/be8557845eead739.png"
    )
    assert (
        user_data.avatar.head
        == "https://chunithm-net-eng.com/mobile/img/e037354ed1e270d5.png"
    )
    assert (
        user_data.avatar.hand_r
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_RightHand.png"
    )
    assert (
        user_data.avatar.hand_l
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_LeftHand.png"
    )
    assert (
        user_data.avatar.item_r
        == "https://chunithm-net-eng.com/mobile/img/7beb8b81b2077bb9.png"
    )
    assert (
        user_data.avatar.item_l
        == "https://chunithm-net-eng.com/mobile/img/7beb8b81b2077bb9.png"
    )

    assert user_data.reborn == 0
    assert user_data.lv == 11

    assert user_data.last_play_date.year == 2023
    assert user_data.last_play_date.month == 8
    assert user_data.last_play_date.day == 4
    assert user_data.last_play_date.hour == 18
    assert user_data.last_play_date.minute == 34
    assert user_data.last_play_date.tzinfo is not None
    assert user_data.last_play_date.tzinfo.utcoffset(
        user_data.last_play_date
    ) == timedelta(seconds=32400)

    assert user_data.overpower.value == pytest.approx(4878.18)
    assert user_data.overpower.progress == pytest.approx(0.0568)

    assert user_data.rating.current == pytest.approx(15.10)
    assert user_data.rating.max == pytest.approx(15.13)

    assert user_data.emblem is None
    assert user_data.medal is None


@pytest.mark.asyncio
async def test_client_parses_playerdata(
    aioresponses: original_aioresponses,
    clal: str,
    user_id: str,
    token: str,
):
    with (BASE_DIR / "assets" / "logged_in_homepage.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home",
            status=200,
            body=f.read(),
        )

    with (BASE_DIR / "assets" / "player_data.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home/playerData",
            status=200,
            body=f.read(),
        )

    async with ChuniNet(clal, user_id=user_id, token=token) as client:
        await client.authenticate()
        user_data = await client.player_data()

    assert user_data.possession == Possession.NONE

    assert (
        user_data.character
        == "https://chunithm-net-eng.com/mobile/img/2c20c7ac326c1a9d.png"
    )
    assert user_data.name == "ＢｏＡｎｈＤＬＢ"  # noqa: RUF001

    assert (
        user_data.avatar.base
        == "https://new.chunithm-net.com/chuni-mobile/html/mobile/images/avatar_base.png"
    )
    assert (
        user_data.avatar.back
        == "https://chunithm-net-eng.com/mobile/img/5a278974114ddee5.png"
    )
    assert (
        user_data.avatar.skinfoot_r
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_Skin.png"
    )
    assert (
        user_data.avatar.skinfoot_l
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_Skin.png"
    )
    assert (
        user_data.avatar.skin
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_Skin.png"
    )
    assert (
        user_data.avatar.wear
        == "https://chunithm-net-eng.com/mobile/img/db379cd92224154d.png"
    )
    assert (
        user_data.avatar.face
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_Face.png"
    )
    assert (
        user_data.avatar.face_cover
        == "https://chunithm-net-eng.com/mobile/img/be8557845eead739.png"
    )
    assert (
        user_data.avatar.head
        == "https://chunithm-net-eng.com/mobile/img/e037354ed1e270d5.png"
    )
    assert (
        user_data.avatar.hand_r
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_RightHand.png"
    )
    assert (
        user_data.avatar.hand_l
        == "https://chunithm-net-eng.com/mobile/images/avatar/CHU_UI_Avatar_Tex_LeftHand.png"
    )
    assert (
        user_data.avatar.item_r
        == "https://chunithm-net-eng.com/mobile/img/7beb8b81b2077bb9.png"
    )
    assert (
        user_data.avatar.item_l
        == "https://chunithm-net-eng.com/mobile/img/7beb8b81b2077bb9.png"
    )

    assert user_data.reborn == 0
    assert user_data.lv == 11

    assert user_data.last_play_date.year == 2023
    assert user_data.last_play_date.month == 8
    assert user_data.last_play_date.day == 4
    assert user_data.last_play_date.hour == 18
    assert user_data.last_play_date.minute == 34
    assert user_data.last_play_date.tzinfo is not None
    assert user_data.last_play_date.tzinfo.utcoffset(
        user_data.last_play_date
    ) == timedelta(seconds=32400)

    assert user_data.playcount == 70

    assert user_data.overpower.value == pytest.approx(4878.18)
    assert user_data.overpower.progress == pytest.approx(0.0568)

    assert user_data.rating.current == pytest.approx(15.10)
    assert user_data.rating.max == pytest.approx(15.13)

    assert user_data.currency is not None
    assert user_data.currency.owned == 133500
    assert user_data.currency.total == 136000

    assert user_data.friend_code == "1234567890123"

    assert user_data.emblem is None
    assert user_data.medal is None


@pytest.mark.asyncio
async def test_client_parses_playlog(
    aioresponses: original_aioresponses,
    clal: str,
    user_id: str,
    token: str,
):
    with (BASE_DIR / "assets" / "logged_in_homepage.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home",
            status=200,
            body=f.read(),
        )

    with (BASE_DIR / "assets" / "playlog.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/record/playlog",
            status=200,
            body=f.read(),
        )

    async with ChuniNet(clal, user_id=user_id, token=token) as client:
        records = await client.recent_record()

    assert len(records) == 50

    record = records[0]

    assert record.detailed is not None
    assert record.detailed.idx == 40
    assert record.detailed.token == "b9bcc1acf740be4b59d7b21673a3b7ca"

    assert record.title == "Air"
    assert record.difficulty == Difficulty.MASTER
    assert record.score == 950592

    assert record.rank == Rank.AAA
    assert record.clear == ClearType.FAILED

    assert record.jacket == "db15d5b7aefaa672.jpg"

    assert record.play_count is None

    assert record.track == 4

    assert record.date.year == 2023
    assert record.date.month == 8
    assert record.date.day == 4
    assert record.date.hour == 18
    assert record.date.minute == 33
    assert record.date.tzinfo is not None
    assert record.date.tzinfo.utcoffset(record.date) == timedelta(seconds=32400)

    assert record.new_record is True


@pytest.mark.asyncio
async def test_client_parses_detailed_playlog(
    aioresponses: original_aioresponses,
    clal: str,
    user_id: str,
    token: str,
):
    with (BASE_DIR / "assets" / "logged_in_homepage.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home",
            status=200,
            body=f.read(),
        )

    aioresponses.post(
        "https://chunithm-net-eng.com/mobile/record/playlog/sendPlaylogDetail",
        status=302,
        headers={
            "Location": "https://chunithm-net-eng.com/mobile/record/playlogDetail"
        },
    )

    with (BASE_DIR / "assets" / "playlog_detail.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/record/playlogDetail",
            status=200,
            body=f.read(),
        )

    async with ChuniNet(clal, user_id=user_id, token=token) as client:
        await client.authenticate()
        record = await client.detailed_recent_record(40)

    assert record.detailed is not None
    assert record.detailed.idx == 317
    assert record.detailed.token == "b9bcc1acf740be4b59d7b21673a3b7ca"

    assert record.title == "Air"
    assert record.difficulty == Difficulty.MASTER
    assert record.score == 950592

    assert record.rank == Rank.AAA
    assert record.clear == ClearType.FAILED

    assert record.jacket == "db15d5b7aefaa672.jpg"

    assert record.play_count is None

    assert record.track == 4

    assert record.date.year == 2023
    assert record.date.month == 8
    assert record.date.day == 4
    assert record.date.hour == 18
    assert record.date.minute == 33
    assert record.date.tzinfo is not None
    assert record.date.tzinfo.utcoffset(record.date) == timedelta(seconds=32400)

    assert record.new_record is True

    assert record.character == "光"

    assert record.skill.name == "キャンペーンブースト"
    assert record.skill.grade == 1
    assert record.skill_result == 0

    assert record.max_combo == 292

    assert record.judgements.jcrit == 1430
    assert record.judgements.justice == 282
    assert record.judgements.attack == 76
    assert record.judgements.miss == 68

    assert record.note_type.tap == pytest.approx(0.9344)
    assert record.note_type.hold == pytest.approx(0.9911)
    assert record.note_type.slide == pytest.approx(0.9821)
    assert record.note_type.air == pytest.approx(0.9873)
    assert record.note_type.flick == pytest.approx(0.9957)


@pytest.mark.asyncio
async def test_client_parses_music_record(
    aioresponses: original_aioresponses,
    clal: str,
    user_id: str,
    token: str,
):
    with (BASE_DIR / "assets" / "logged_in_homepage.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home",
            status=200,
            body=f.read(),
        )

    aioresponses.post(
        "https://chunithm-net-eng.com/mobile/record/musicGenre/sendMusicDetail",
        status=302,
        headers={"Location": "https://chunithm-net-eng.com/mobile/record/musicDetail"},
    )

    with (BASE_DIR / "assets" / "music_record.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/record/musicDetail",
            status=200,
            body=f.read(),
        )

    async with ChuniNet(clal, user_id=user_id, token=token) as client:
        await client.authenticate()
        records = await client.music_record(428)

    assert len(records) == 2

    assert records[0].detailed is not None
    assert records[1].detailed is not None

    assert records[0].detailed.idx == records[1].detailed.idx == 428

    assert records[0].title == records[1].title == "Aleph-0"

    assert records[0].difficulty == Difficulty.EXPERT
    assert records[1].difficulty == Difficulty.MASTER

    assert records[0].score == 1005037
    assert records[1].score == 988818

    assert records[0].rank == Rank.SSp
    assert records[1].rank == Rank.S

    assert records[0].clear == ClearType.CLEAR
    assert records[1].clear == ClearType.CLEAR

    assert records[0].jacket == records[1].jacket == "986a1c6047f3033e.jpg"

    assert records[0].play_count == records[1].play_count == 2


@pytest.mark.asyncio
async def test_clients_parses_we_music_record(
    aioresponses: original_aioresponses,
    clal: str,
    user_id: str,
    token: str,
):
    with (BASE_DIR / "assets" / "logged_in_homepage.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home",
            status=200,
            body=f.read(),
        )

    aioresponses.post(
        "https://chunithm-net-eng.com/mobile/record/worldsEndList/sendWorldsEndDetail",
        status=302,
        headers={
            "Location": "https://chunithm-net-eng.com/mobile/record/worldsEndDetail"
        },
    )

    with (BASE_DIR / "assets" / "worlds_end_music_record.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/record/worldsEndDetail",
            status=200,
            body=f.read(),
        )

    async with ChuniNet(clal, user_id=user_id, token=token) as client:
        await client.authenticate()
        records = await client.music_record(8218)

    assert len(records) == 1

    record = records[0]
    assert record.detailed is not None
    assert record.detailed.idx == 8218

    assert record.title == "BLUE ZONE"

    assert record.difficulty == Difficulty.WORLDS_END

    assert record.score == 953506

    assert record.rank == Rank.AAA

    assert record.clear == ClearType.CLEAR

    assert record.jacket == "2640e526c59188fc.jpg"

    assert record.play_count == 1


@pytest.mark.asyncio
async def test_client_parses_music_for_rating(
    aioresponses: original_aioresponses,
    clal: str,
    user_id: str,
    token: str,
):
    with (BASE_DIR / "assets" / "logged_in_homepage.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home",
            status=200,
            body=f.read(),
        )

    with (BASE_DIR / "assets" / "best30.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home/playerData/ratingDetailBest",
            status=200,
            body=f.read(),
        )

    with (BASE_DIR / "assets" / "recent10.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home/playerData/ratingDetailRecent",
            status=200,
            body=f.read(),
        )

    async with ChuniNet(clal, user_id=user_id, token=token) as client:
        await client.authenticate()
        best30 = await client.best30()
        recent10 = await client.recent10()

    assert len(best30) == 30
    assert best30[0].detailed is not None
    assert best30[0].detailed.idx == 428
    assert best30[0].detailed.token == "b9bcc1acf740be4b59d7b21673a3b7ca"

    assert best30[0].title == "Aleph-0"
    assert best30[0].score == 1005037
    assert best30[0].difficulty == Difficulty.EXPERT

    assert len(recent10) == 10
    assert recent10[0].detailed is not None
    assert recent10[0].detailed.idx == 2340
    assert recent10[0].detailed.token == "b9bcc1acf740be4b59d7b21673a3b7ca"

    assert recent10[0].title == "To：Be Continued"  # noqa: RUF001
    assert recent10[0].score == 1000449
    assert recent10[0].difficulty == Difficulty.EXPERT


@pytest.mark.asyncio
async def test_client_parses_music_record_by_folder(
    aioresponses: original_aioresponses,
    clal: str,
    user_id: str,
    token: str,
):
    with (BASE_DIR / "assets" / "logged_in_homepage.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home",
            status=200,
            body=f.read(),
            repeat=True,
        )

    with (BASE_DIR / "assets" / "music_record_by_level_folder.html").open("rb") as f:
        aioresponses.post(
            "https://chunithm-net-eng.com/mobile/record/musicLevel/sendSearch",
            status=200,
            body=f.read(),
        )

    with pytest.raises(NotImplementedError):
        async with ChuniNet(clal, user_id=user_id, token=token) as client:
            await client.authenticate()
            await client.music_record_by_folder(difficulty=Difficulty.EXPERT)

    with pytest.raises(NotImplementedError):
        async with ChuniNet(clal, user_id=user_id, token=token) as client:
            await client.authenticate()
            await client.music_record_by_folder(genre=Genres.VARIETY)

    with pytest.raises(NotImplementedError):
        async with ChuniNet(clal, user_id=user_id, token=token) as client:
            await client.authenticate()
            await client.music_record_by_folder(rank=Rank.S)

    async with ChuniNet(clal, user_id=user_id, token=token) as client:
        await client.authenticate()

        assert await client.music_record_by_folder(level=None) is None

        records = await client.music_record_by_folder(level="14")

    assert records is not None
    assert len(records) == 34

    assert records[0].detailed is not None
    assert records[0].detailed.idx == 2184
    assert records[0].detailed.token == "b9bcc1acf740be4b59d7b21673a3b7ca"

    assert records[0].title == "ENDYMION"
    assert records[0].score == 992633
    assert records[0].difficulty == Difficulty.EXPERT

    assert records[0].rank == Rank.Sp
    assert records[0].clear == ClearType.CLEAR


@pytest.mark.asyncio
async def test_client_can_rename(
    aioresponses: original_aioresponses,
    clal: str,
    user_id: str,
    token: str,
):
    with (BASE_DIR / "assets" / "logged_in_homepage.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home",
            status=200,
            body=f.read(),
            repeat=True,
        )

    aioresponses.post(
        "https://chunithm-net-eng.com/mobile/home/userOption/updateUserName/update",
        status=302,
        headers={"Location": "https://chunithm-net-eng.com/mobile/home/userOption/"},
    )

    aioresponses.get(
        "https://chunithm-net-eng.com/mobile/home/userOption/",
        status=200,
    )

    async with ChuniNet(clal, user_id=user_id, token=token) as client:
        await client.authenticate()

        with pytest.raises(
            ValueError, match="Player name must be between 1 and 8 characters"
        ):
            await client.change_player_name("")
        with pytest.raises(
            ValueError, match="Player name must be between 1 and 8 characters"
        ):
            await client.change_player_name("123456789")
        with pytest.raises(ValueError, match="Player name contains invalid characters"):
            await client.change_player_name("あいうえお")

        assert await client.change_player_name("new name") is True
