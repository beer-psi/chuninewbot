from http import HTTPStatus
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup
from yarl import URL

from .player_data import PlayerData, Overpower, Nameplate, Rating, Currency
from .record import RecentRecord, DetailedRecentRecord, Judgements, NoteType, Skill
from .utils import (
    parse_basic_recent_record,
    parse_time,
    parse_player_rating,
)


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
            self.session.cookie_jar.update_cookies(
                {"userId": str(user_id)}, self.base
            )
        if token is not None:
            self.session.cookie_jar.update_cookies(
                {"_t": token}, self.base
            )

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        await self.session.close()
    
    @property
    def user_id(self):
        return self.session.cookie_jar.filter_cookies(self.base).get("userId").value
    
    @property
    def token(self):
        return self.session.cookie_jar.filter_cookies(self.base).get("_t").value

    async def validate_cookie(self):
        async with self.session.get(self.AUTH_URL, allow_redirects=False) as req:
            if req.status != HTTPStatus.FOUND:
                raise Exception(
                    f"Invalid cookie. Received status code was {req.status}"
                )
            return req.headers["Location"]

    async def _authenticate(self):
        uid_redemption_url = await self.validate_cookie()
        async with self.session.get(uid_redemption_url) as req:
            if req.status == HTTPStatus.SERVICE_UNAVAILABLE:
                raise Exception("Service under maintenance")
            if self.session.cookie_jar.filter_cookies(self.base).get("userId") is None:
                raise Exception("Invalid cookie")

    async def _request(self, endpoint: str, method="GET", **kwargs):
        if self.session.cookie_jar.filter_cookies(self.base).get("userId") is None:
            await self._authenticate()

        response = await self.session.request(method, self.base / endpoint, **kwargs)
        if response.cookies.get("_t") is None:
            soup = BeautifulSoup(await response.text(), "html.parser")
            err = soup.select(".block.text_l .font_small")
            raise Exception(
                f"The server returned an error: {err[1].get_text() if err else ''}"
            )
        return response

    async def player_data(self):
        resp = await self._request("mobile/home/playerData")
        soup = BeautifulSoup(await resp.text(), "html.parser")

        avatar = soup.select_one(".player_chara_info img")["src"]

        name = soup.select_one(".player_name_in").get_text()
        lv = int(soup.select_one(".player_lv").get_text())

        nameplate_content = soup.select_one(".player_honor_text").get_text()
        nameplate_rarity = (
            soup.select_one(".player_honor_short")["style"].split("_")[-1].split(".")[0]
        )

        rating = parse_player_rating(soup.select(".player_rating_num_block img"))
        max_rating = float(soup.select_one(".player_rating_max").get_text())

        overpower = soup.select_one(".player_overpower_text").get_text().split(" ")
        overpower_value = float(overpower[0])
        overpower_progress = (
            float(overpower[1].replace("(", "").replace(")", "").replace("%", "")) / 100
        )

        last_play_date_str = soup.select_one(".player_lastplaydate_text").get_text()
        last_play_date = parse_time(last_play_date_str)

        owned_currency = int(
            soup.select_one(".user_data_point .user_data_text")
            .get_text()
            .replace(",", "")
        )
        total_currency = int(
            soup.select_one(".user_data_total_point .user_data_text")
            .get_text()
            .replace(",", "")
        )
        playcount = int(
            soup.select_one(".user_data_play_count .user_data_text").get_text()
        )

        return PlayerData(
            avatar,
            name,
            lv,
            playcount,
            last_play_date,
            overpower=Overpower(overpower_value, overpower_progress),
            nameplate=Nameplate(nameplate_content, nameplate_rarity),
            rating=Rating(rating, max_rating),
            currency=Currency(owned_currency, total_currency),
        )

    async def recent_record(self) -> list[RecentRecord]:
        resp = await self._request("mobile/record/playlog")
        soup = BeautifulSoup(await resp.text(), "html.parser")

        web_records = soup.select(".frame02.w400")
        return [parse_basic_recent_record(record) for record in web_records]

    async def detailed_recent_record(self, idx: int, token: Optional[str] = None):
        def get_judgement_count(class_name):
            return int(
                soup.select_one(class_name).get_text().replace(",", "")
            )
        
        def get_note_percentage(class_name):
            return float(
                soup.select_one(class_name).get_text().replace("%", "")
            ) / 100

        resp = await self._request(
            "mobile/record/playlog/sendPlaylogDetail/",
            method="POST",
            data={
                "idx": idx,
                "token": self.token,
            },
        )
        soup = BeautifulSoup(await resp.text(), "html.parser")
        record = DetailedRecentRecord.from_basic(
            parse_basic_recent_record(soup.select_one(".frame01_inside"))
        )
        record.idx = idx

        record.max_combo = int(
            soup.select_one(".play_data_detail_maxcombo_block").get_text()
        )

        jcrit = get_judgement_count(".text_critical.play_data_detail_judge_text")
        justice = get_judgement_count(".text_justice.play_data_detail_judge_text")
        attack = get_judgement_count(".text_attack.play_data_detail_judge_text")
        miss = get_judgement_count(".text_miss.play_data_detail_judge_text")
        record.judgements = Judgements(jcrit, justice, attack, miss)

        tap = get_note_percentage(".text_tap_red.play_data_detail_notes_text")
        hold = get_note_percentage(".text_hold_yellow.play_data_detail_notes_text")
        slide = get_note_percentage(".text_slide_blue.play_data_detail_notes_text")
        air = get_note_percentage(".text_air_green.play_data_detail_notes_text")
        flick = get_note_percentage(".text_flick_skyblue.play_data_detail_notes_text")
        record.note_type = NoteType(tap, hold, slide, air, flick)

        record.character = soup.select_one(".play_data_chara_name").get_text()

        skill_name = soup.select_one(".play_data_skill_name").get_text()
        skill_grade = int(soup.select_one(".play_data_skill_grade").get_text())
        record.skill = Skill(skill_name, skill_grade)

        record.skill_result = int(
            soup.select_one(".play_musicdata_skilleffect_text")
            .get_text()
            .replace("+", "")
            .replace(",", "")
        )
        return record
