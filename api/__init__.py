from http import HTTPStatus
from typing import TYPE_CHECKING, Optional, cast

import aiohttp
from bs4 import BeautifulSoup
from yarl import URL

from .enums import Possession, SkillClass, Rank, ClearType
from .exceptions import ChuniNetError, InvalidTokenException, MaintenanceException
from .player_data import Currency, Nameplate, Overpower, PlayerData, Rating, UserAvatar
from .record import (
    DetailedParams,
    DetailedRecentRecord,
    Judgements,
    MusicRecord,
    NoteType,
    RecentRecord,
    Record,
    Skill,
)
from .utils import (
    chuni_int,
    difficulty_from_imgurl,
    extract_last_part,
    get_rank_and_cleartype,
    parse_basic_recent_record,
    parse_player_rating,
    parse_time,
)

if TYPE_CHECKING:
    from bs4.element import Tag


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

            return self._parse_player_card_and_avatar(BeautifulSoup(await req.text(), "lxml"))

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

    def _parse_player_card_and_avatar(self, soup: BeautifulSoup):
        character = cast(str, soup.select_one(".player_chara_info img")["src"])

        name = soup.select_one(".player_name_in").get_text()
        lv = chuni_int(soup.select_one(".player_lv").get_text())

        nameplate_content = soup.select_one(".player_honor_text").get_text()
        nameplate_rarity = (
            str(soup.select_one(".player_honor_short")["style"])
            .split("_")[-1]
            .split(".")[0]
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

        reborn_elem = soup.select_one(".player_reborn")
        reborn = chuni_int(reborn_elem.get_text()) if reborn_elem else 0

        possession_elem = soup.select_one(".box_playerprofile")
        possession = (
            Possession.from_str(
                extract_last_part(possession_elem["style"])  # type: ignore
            )
            if possession_elem and possession_elem.has_attr("style")
            else Possession.NONE
        )

        classemblem_base_elem = soup.select_one(".player_classemblem_base img")
        emblem = (
            SkillClass(
                chuni_int(extract_last_part(classemblem_base_elem["src"]))  # type: ignore
            )
            if classemblem_base_elem and classemblem_base_elem.has_attr("src")
            else None
        )

        classemblem_top_elem = soup.select_one(".player_classemblem_top img")
        medal = (
            SkillClass(
                chuni_int(extract_last_part(classemblem_top_elem["src"]))  # type: ignore
            )
            if classemblem_top_elem and classemblem_top_elem.has_attr("src")
            else None
        )

        avatar_group = soup.select_one(".avatar_group")
        avatar = UserAvatar(
            base="https://new.chunithm-net.com/chuni-mobile/html/mobile/images/avatar_base.png",
            back=avatar_group.select_one(".avatar_back img")["src"],
            skinfoot_r=avatar_group.select_one(".avatar_skinfoot_r img")["src"],
            skinfoot_l=avatar_group.select_one(".avatar_skinfoot_l img")["src"],
            skin=avatar_group.select_one(".avatar_skin img")["src"],
            wear=avatar_group.select_one(".avatar_wear img")["src"],
            face=avatar_group.select_one(".avatar_face img")["src"],
            face_cover=avatar_group.select_one(".avatar_faceCover img")["src"],
            head=avatar_group.select_one(".avatar_head img")["src"],
            hand_r=avatar_group.select_one(".avatar_hand_r img")["src"],
            hand_l=avatar_group.select_one(".avatar_hand_l img")["src"],
            item_r=avatar_group.select_one(".avatar_item_r img")["src"],
            item_l=avatar_group.select_one(".avatar_item_l img")["src"],
        )

        return PlayerData(
            character=character,
            avatar=avatar,
            name=name,
            lv=lv,
            reborn=reborn,
            possession=possession,
            nameplate=Nameplate(content=nameplate_content, rarity=nameplate_rarity),
            rating=Rating(rating, max_rating),
            overpower=Overpower(overpower_value, overpower_progress),
            last_play_date=last_play_date,
            emblem=emblem,
            medal=medal,
        )

    async def player_data(self):
        resp = await self._request("mobile/home/playerData")
        soup = BeautifulSoup(await resp.text(), "lxml")

        data = self._parse_player_card_and_avatar(soup)

        owned_currency = chuni_int(
            soup.select_one(".user_data_point .user_data_text").get_text()
        )
        total_currency = chuni_int(
            soup.select_one(".user_data_total_point .user_data_text").get_text()
        )
        data.currency = Currency(owned_currency, total_currency)

        playcount = chuni_int(
            soup.select_one(".user_data_play_count .user_data_text").get_text()
        )
        data.playcount = playcount

        data.friend_code = soup.select_one(
            ".user_data_friend_code .user_data_text span:not(.font_90)"
        ).get_text()

        return data

    async def recent_record(self) -> list[RecentRecord]:
        resp = await self._request("mobile/record/playlog")
        soup = BeautifulSoup(await resp.text(), "lxml")

        web_records = soup.select(".frame02.w400")
        return [parse_basic_recent_record(record) for record in web_records]

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

        jacket = (
            str(elem["src"]).split("/")[-1]
            if (elem := soup.select_one(".play_jacket_img img"))
            else ""
        )
        title = (
            elem.get_text()
            if (elem := soup.select_one(".play_musicdata_title"))
            else ""
        )
        records = []
        for block in soup.select(".music_box"):
            if (musicdata := block.select_one(".play_musicdata_icon")) is not None:
                rank, clear = get_rank_and_cleartype(musicdata)
            else:
                rank, clear = Rank.D, ClearType.FAILED
            records.append(
                MusicRecord(
                    title=title,
                    jacket=jacket,
                    difficulty=difficulty_from_imgurl(" ".join(block["class"])),
                    score=chuni_int(
                        elem.get_text()
                        if (elem := block.select_one(".musicdata_score_num .text_b"))
                        is not None
                        else "0"
                    ),
                    rank=rank,
                    clear=clear,
                    play_count=chuni_int(
                        elem.get_text().replace("times", "")
                        if (
                            elem := block.select_one(
                                ".musicdata_score_num .text_b:-soup-contains(times)"
                            )
                        )
                        is not None
                        else "0"
                    ),
                )
            )
        return records

    def _parse_music_for_rating(self, soup: BeautifulSoup) -> list[Record]:
        return [
            Record(
                detailed=DetailedParams(
                    idx=int(str(x.select_one("input[name=idx]")["value"])),
                    token=str(x.select_one("input[name=token]")["value"]),
                ),
                title=x.select_one(".music_title").get_text(),
                difficulty=difficulty_from_imgurl(" ".join(x["class"])),
                score=chuni_int(
                    x.select_one(".play_musicdata_highscore .text_b").get_text()
                ),
            )
            for x in soup.select(".w388.musiclist_box")
        ]

    async def best30(self) -> list[Record]:
        resp = await self._request("mobile/home/playerData/ratingDetailBest/")
        soup = BeautifulSoup(await resp.text(), "lxml")

        return self._parse_music_for_rating(soup)

    async def recent10(self) -> list[Record]:
        resp = await self._request("mobile/home/playerData/ratingDetailRecent/")
        soup = BeautifulSoup(await resp.text(), "lxml")

        return self._parse_music_for_rating(soup)

    async def detailed_recent_record(self, idx: int):
        def get_judgement_count(class_name):
            return chuni_int(soup.select_one(class_name).get_text().replace(",", ""))

        def get_note_percentage(class_name):
            return float(soup.select_one(class_name).get_text().replace("%", "")) / 100

        resp = await self._request(
            "mobile/record/playlog/sendPlaylogDetail/",
            method="POST",
            data={
                "idx": idx,
                "token": self.token,
            },
        )
        soup = BeautifulSoup(await resp.text(), "lxml")
        record = DetailedRecentRecord.from_basic(
            parse_basic_recent_record(cast("Tag", soup.select_one(".frame01_inside")))
        )
        record.idx = idx

        record.max_combo = chuni_int(
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
        skill_grade = chuni_int(soup.select_one(".play_data_skill_grade").get_text())
        record.skill = Skill(skill_name, skill_grade)

        record.skill_result = chuni_int(
            soup.select_one(".play_musicdata_skilleffect_text")
            .get_text()
            .replace("+", "")
        )
        return record
