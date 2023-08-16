from http import HTTPStatus
from typing import TYPE_CHECKING, Optional

import aiohttp
from bs4 import BeautifulSoup
from yarl import URL

from .consts import PLAYER_NAME_ALLOWED_SPECIAL_CHARACTERS
from .entities.enums import Difficulty, Genres, Rank
from .entities.record import DetailedParams, MusicRecord, RecentRecord, Record
from .exceptions import ChuniNetError, InvalidTokenException, MaintenanceException
from .parser import (
    parse_basic_recent_record,
    parse_detailed_recent_record,
    parse_music_for_rating,
    parse_music_record,
    parse_player_card_and_avatar,
    parse_player_data,
)

if TYPE_CHECKING:
    from chunithm_net.entities.player_data import PlayerData

__all__ = ["ChuniNet"]


class ChuniNet:
    AUTH_URL = "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/"

    def __init__(
        self,
        clal: str,
        *,
        user_id: Optional[str] = None,
        token: Optional[str] = None,
        base: Optional[URL] = None,
    ) -> None:
        if base is None:
            self.base = URL("https://chunithm-net-eng.com")
        else:
            self.base = base
        self.clal = clal

        self.session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())
        self.session.cookie_jar.update_cookies(
            {"clal": clal}, URL("https://lng-tgk-aime-gw.am-all.net")
        )

        if user_id is not None:
            self.session.cookie_jar.update_cookies({"userId": user_id}, self.base)
        if token is not None:
            self.session.cookie_jar.update_cookies({"_t": token}, self.base)

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        await self.session.close()

    async def close(self):
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

    def clear_cookies(self):
        self.session.cookie_jar.clear_domain(self.base.host or "chunithm-net-eng.com")

    async def validate_cookie(self):
        async with self.session.get(self.AUTH_URL, allow_redirects=False) as req:
            if req.status != HTTPStatus.FOUND:
                msg = f"Invalid cookie. Received status code was {req.status}"
                raise InvalidTokenException(msg)
            return req.headers["Location"]

    async def authenticate(self) -> "PlayerData":
        if self.user_id is not None:
            try:
                # In some cases, the site token is refreshed automatically.
                resp = await self._request("mobile/home/")
            except ChuniNetError as e:
                # In other cases, the token is invalidated and a relogin is required.
                # Error code for when site token is invalidated
                if e.code != 200004:
                    raise
                uid_redemption_url = await self.validate_cookie()
                resp = await self.session.get(uid_redemption_url)
        else:
            uid_redemption_url = await self.validate_cookie()
            resp = await self.session.get(uid_redemption_url)

        if resp.status == HTTPStatus.SERVICE_UNAVAILABLE:
            msg = "Service under maintenance"
            raise MaintenanceException(msg)
        if self.session.cookie_jar.filter_cookies(self.base).get("userId") is None:
            msg = "Invalid cookie: No userId cookie found"
            raise InvalidTokenException(msg)

        return parse_player_card_and_avatar(BeautifulSoup(await resp.text(), "lxml"))

    async def _request(self, endpoint: str, method="GET", **kwargs):
        if self.user_id is None:
            await self.authenticate()

        response = await self.session.request(method, self.base / endpoint, **kwargs)
        # We could be here because the client attempted to reauthenticate
        # but the clal was invalid.
        if response.url.path == "/mobile/" and self.AUTH_URL in (await response.text()):
            self.clear_cookies()
            await self.authenticate()
            return await self._request(endpoint, method, **kwargs)

        if response.url.path.startswith("/mobile/error"):
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
        return parse_detailed_recent_record(soup)

    async def music_record(self, idx: int) -> list[MusicRecord]:
        if idx >= 8000:
            return await self._worlds_end_music_record(idx)

        resp = await self._request(
            "mobile/record/musicGenre/sendMusicDetail/",
            method="POST",
            data={
                "idx": idx,
                "token": self.token,
            },
        )
        soup = BeautifulSoup(await resp.text(), "lxml")
        return parse_music_record(soup, DetailedParams(idx, self.token or ""))

    async def _worlds_end_music_record(self, idx: int) -> list[MusicRecord]:
        resp = await self._request(
            "mobile/record/worldsEndList/sendWorldsEndDetail/",
            method="POST",
            data={
                "idx": idx,
                "token": self.token,
            },
        )
        soup = BeautifulSoup(await resp.text(), "lxml")
        return parse_music_record(soup, DetailedParams(idx, self.token or ""))

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
        level: Optional[str] = None,
        genre: Optional[Genres] = None,
        rank: Optional[Rank] = None,
        difficulty: Optional[Difficulty] = None,
    ) -> list[Record]:
        """Get records for all songs matching specific criteria.

        CHUNITHM-NET only supports level, genre and rank search, so if multiple
        criteria are specified, they are applied in order of:
        - difficulty if difficulty is `Difficulty.WORLDS_END`
        - level
        - genre + difficulty
        - rank + difficulty
        - difficulty

        Parameters
        ----------
        level: Optional[str]
            Song level to filter by. Between 1 and 15. From level 7 to 14, can be
            suffixed with "+".
        genre: Optional[Genres]
            Genre to filter by. If this is set, `difficulty` must also be set.
        rank: Optional[Rank]
            Rank to filter by. If this is set, `difficulty` must also be set.
        difficulty: Optional[Difficulty]
            Difficulty to filter by.

        Returns
        -------
        list[Record]: List of records matching the criteria.

        Exceptions
        ----------
        ValueError:
            When genre/rank is specified but difficulty is not set, or when no
            criteria is provided.
        """
        if difficulty == Difficulty.WORLDS_END:
            resp = await self._request("mobile/record/worldsEndList")
        elif level is not None:
            plus_level = level[-1] == "+"
            level_num = int(level[:-1] if plus_level else level)
            level_value = (
                level_num - 1 + max(0, level_num - 7) + (1 if plus_level else 0)
            )

            resp = await self._request(
                "mobile/record/musicLevel/sendSearch/",
                method="POST",
                data={
                    "level": str(level_value),
                    "token": self.token,
                },
            )
        elif genre is not None:
            if difficulty is None:
                msg = "Difficulty cannot be None when genre is specified"
                raise ValueError(msg)

            resp = await self._request(
                f"mobile/record/musicGenre/send{str(difficulty).capitalize()}",
                method="POST",
                data={
                    "genre": genre.value,
                    "token": self.token,
                },
            )
        elif rank is not None:
            if difficulty is None:
                msg = "Difficulty cannot be None when genre is specified"
                raise ValueError(msg)

            value = rank.value
            if value < Rank.S.value:
                value = 7

            resp = await self._request(
                f"mobile/record/musicRank/send{str(difficulty).capitalize()}",
                method="POST",
                data={
                    "rank": str(rank.value),
                    "token": self.token,
                },
            )
        elif difficulty is not None:
            resp = await self._request(
                f"mobile/record/musicGenre/send{str(difficulty).capitalize()}",
                method="POST",
                data={
                    "genre": "99",
                    "token": self.token,
                },
            )
        else:
            msg = "No search criteria specified"
            raise ValueError(msg)

        soup = BeautifulSoup(await resp.text(), "lxml")
        return parse_music_for_rating(soup)

    async def change_player_name(self, new_name: str) -> bool:
        if len(new_name) > 8 or len(new_name) < 1:
            msg = "Player name must be between 1 and 8 characters"
            raise ValueError(msg)
        if any(
            not (
                c in PLAYER_NAME_ALLOWED_SPECIAL_CHARACTERS
                or c.isdigit()
                or (c.isalpha() and c.isascii())
                or c.isspace()
            )
            for c in new_name
        ):
            msg = "Player name contains invalid characters"
            raise ValueError(msg)

        resp = await self._request(
            "mobile/home/userOption/updateUserName/update/",
            method="POST",
            data={
                "userName": new_name,
                "token": self.token,
            },
            headers={
                "Referer": str(self.base / "mobile/home/userOption/updateUserName"),
            },
        )
        return resp.url.path == "/mobile/home/userOption/"
