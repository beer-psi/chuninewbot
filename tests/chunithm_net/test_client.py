import string
from pathlib import Path
from random import choices

import pytest
from aioresponses import aioresponses as original_aioresponses
from multidict import CIMultiDict

from chunithm_net import ChuniNet
from chunithm_net.entities.enums import Possession
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
    with (BASE_DIR / "assets" / "player_data.html").open("rb") as f:
        aioresponses.get(
            "https://chunithm-net-eng.com/mobile/home/playerData",
            status=200,
            body=f.read(),
        )

    async with ChuniNet(clal, user_id=user_id, token=token) as client:
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
