from http import HTTPStatus
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup
from yarl import URL

from .enums import Difficulty, Genres, Rank
from .exceptions import ChuniNetError, InvalidTokenException, MaintenanceException
from .parser import (
    parse_basic_recent_record,
    parse_detailed_recent_record,
    parse_music_for_rating,
    parse_music_record,
    parse_player_card_and_avatar,
    parse_player_data,
)
from .record import MusicRecord, RecentRecord, Record


class ChuniNet:
    AUTH_URL = "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/"

    def __init__(
        self,
        clal: str,
        user_id: Optional[int] = None,
        token: Optional[str] = None,
        base: URL = URL("https://chunithm-net-eng.com"),
    ) -> None:
        self.base = base
        self.clal = clal

        self.session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())
        self.session.cookie_jar.update_cookies(
            {"clal": clal}, URL("https://lng-tgk-aime-gw.am-all.net")
        )

        if user_id is not None:
            self.session.cookie_jar.update_cookies({"userId": str(user_id)}, self.base)
        if token is not None:
            self.session.cookie_jar.update_cookies({"_t": token}, self.base)

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        await self.session.close()

    @property
    def user_id(self):
        cookie = self.session.cookie_jar.filter_cookies(self.base).get("userId")
        if cookie is None:
            return None
        return cookie.value

    @property
    def token(self):
        cookie = self.session.cookie_jar.filter_cookies(self.base).get("_t")
        if cookie is None:
            return None
        return cookie.value

    async def validate_cookie(self):
        async with self.session.get(self.AUTH_URL, allow_redirects=False) as req:
            if req.status != HTTPStatus.FOUND:
                raise InvalidTokenException(
                    f"Invalid cookie. Received status code was {req.status}"
                )
            return req.headers["Location"]

    async def authenticate(self):
        uid_redemption_url = await self.validate_cookie()
        async with self.session.get(uid_redemption_url) as req:
            if req.status == HTTPStatus.SERVICE_UNAVAILABLE:
                raise MaintenanceException("Service under maintenance")
            if self.session.cookie_jar.filter_cookies(self.base).get("userId") is None:
                raise InvalidTokenException("Invalid cookie: No userId cookie found")

            return parse_player_card_and_avatar(BeautifulSoup(await req.text(), "lxml"))

    async def _request(self, endpoint: str, method="GET", **kwargs):
        if self.session.cookie_jar.filter_cookies(self.base).get("userId") is None:
            await self.authenticate()

        response = await self.session.request(method, self.base / endpoint, **kwargs)
        if response.url.path == "/mobile/error/":
            soup = BeautifulSoup(await response.text(), "lxml")
            err = soup.select(".block.text_l .font_small")

            errcode = int(err[0].get_text().split(":")[1])
            description = err[1].get_text() if len(err) > 1 else ""
            raise ChuniNetError(errcode, description)
        return response

    async def player_data(self):
        resp = await self._request("mobile/home/playerData")
        soup = BeautifulSoup(await resp.text(), "lxml")
        return parse_player_data(soup)

    async def recent_record(self) -> list[RecentRecord]:
        resp = await self._request("mobile/record/playlog")
        soup = BeautifulSoup(await resp.text(), "lxml")

        web_records = soup.select(".frame02.w400")
        return [parse_basic_recent_record(record) for record in web_records]

    async def detailed_recent_record(self, idx: int):
        resp = await self._request(
            "mobile/record/playlog/sendPlaylogDetail/",
            method="POST",
            data={
                "idx": idx,
                "token": self.token,
            },
        )
        soup = BeautifulSoup(await resp.text(), "lxml")
        return parse_detailed_recent_record(idx, soup)

    async def music_record(self, idx: int) -> list[MusicRecord]:
        resp = await self._request(
            "mobile/record/musicGenre/sendMusicDetail/",
            method="POST",
            data={
                "idx": idx,
                "token": self.token,
            },
        )
        soup = BeautifulSoup(await resp.text(), "lxml")
        return parse_music_record(soup)

    async def best30(self) -> list[Record]:
        resp = await self._request("mobile/home/playerData/ratingDetailBest/")
        soup = BeautifulSoup(await resp.text(), "lxml")

        return parse_music_for_rating(soup)

    async def recent10(self) -> list[Record]:
        resp = await self._request("mobile/home/playerData/ratingDetailRecent/")
        soup = BeautifulSoup(await resp.text(), "lxml")

        return parse_music_for_rating(soup)

    async def music_record_by_folder(
        self,
        *,
        difficulty: Optional[Difficulty] = None,
        genre: Optional[Genres] = None,
        rank: Optional[Rank] = None,
        level: Optional[str] = None,
    ) -> list[Record] | None:
        if difficulty is not None or genre is not None or rank is not None:
            raise NotImplementedError

        if level is None:
            return

        plus_level = level[-1] == "+"
        level_num = int(level[:-1] if plus_level else level)
        level_value = level_num - 1 + max(0, level_num - 7) + (1 if plus_level else 0)

        resp = await self._request(
            "mobile/record/musicLevel/sendSearch/",
            method="POST",
            data={
                "level": str(level_value),
                "token": self.token,
            },
        )
        soup = BeautifulSoup(await resp.text(), "lxml")
        return parse_music_for_rating(soup)
