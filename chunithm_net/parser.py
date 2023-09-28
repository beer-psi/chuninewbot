# pyright: reportOptionalMemberAccess=false, reportOptionalSubscript=false
from typing import Optional, cast

from bs4 import BeautifulSoup, Tag

from .entities.enums import ClearType, Possession, Rank, SkillClass
from .entities.player_data import (
    Currency,
    Nameplate,
    Overpower,
    PlayerData,
    Rating,
    Team,
    UserAvatar,
)
from .entities.record import (
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
    parse_player_rating,
    parse_time,
)


def parse_player_card_and_avatar(soup: BeautifulSoup):
    if (e := soup.select_one(".player_chara img")) is not None:
        character = cast(str, e["src"])
    else:
        character = None

    name = soup.select_one(".player_name_in").get_text()
    lv = chuni_int(soup.select_one(".player_lv").get_text())

    team_name_elem = soup.select_one(".player_team_name")
    team_name = team_name_elem.get_text() if team_name_elem else None

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
        Possession.from_str(extract_last_part(possession_elem["style"]))  # type: ignore[reportGeneralTypeIssues]
        if possession_elem and possession_elem.has_attr("style")
        else Possession.NONE
    )

    classemblem_base_elem = soup.select_one(".player_classemblem_base img")
    emblem = (
        SkillClass(
            chuni_int(extract_last_part(classemblem_base_elem["src"]))  # type: ignore[reportGeneralTypeIssues]
        )
        if classemblem_base_elem and classemblem_base_elem.has_attr("src")
        else None
    )

    classemblem_top_elem = soup.select_one(".player_classemblem_top img")
    medal = (
        SkillClass(
            chuni_int(extract_last_part(classemblem_top_elem["src"]))  # type: ignore[reportGeneralTypeIssues]
        )
        if classemblem_top_elem and classemblem_top_elem.has_attr("src")
        else None
    )

    avatar_group = soup.select_one(".avatar_group")
    avatar = UserAvatar(
        base="https://new.chunithm-net.com/chuni-mobile/html/mobile/images/avatar_base.png",
        back=cast(str, avatar_group.select_one(".avatar_back img")["src"]),
        skinfoot_r=cast(str, avatar_group.select_one(".avatar_skinfoot_r img")["src"]),
        skinfoot_l=cast(str, avatar_group.select_one(".avatar_skinfoot_l img")["src"]),
        skin=cast(str, avatar_group.select_one(".avatar_skin img")["src"]),
        wear=cast(str, avatar_group.select_one(".avatar_wear img")["src"]),
        face=cast(str, avatar_group.select_one(".avatar_face img")["src"]),
        face_cover=cast(str, avatar_group.select_one(".avatar_faceCover img")["src"]),
        head=cast(str, avatar_group.select_one(".avatar_head img")["src"]),
        hand_r=cast(str, avatar_group.select_one(".avatar_hand_r img")["src"]),
        hand_l=cast(str, avatar_group.select_one(".avatar_hand_l img")["src"]),
        item_r=cast(str, avatar_group.select_one(".avatar_item_r img")["src"]),
        item_l=cast(str, avatar_group.select_one(".avatar_item_l img")["src"]),
    )

    return PlayerData(
        character=character,
        avatar=avatar,
        name=name,
        lv=lv,
        reborn=reborn,
        possession=possession,
        team=Team(name=team_name) if team_name else None,
        nameplate=Nameplate(content=nameplate_content, rarity=nameplate_rarity),
        rating=Rating(rating, max_rating),
        overpower=Overpower(overpower_value, overpower_progress),
        last_play_date=last_play_date,
        emblem=emblem,
        medal=medal,
    )


def parse_player_data(soup: BeautifulSoup) -> PlayerData:
    data = parse_player_card_and_avatar(soup)

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


def parse_basic_recent_record(record: Tag) -> RecentRecord:
    idx_elem = record.select_one("form input[name=idx]")
    if idx_elem is None:
        detailed = None
    else:
        idx = int(cast(str, idx_elem["value"]))
        token = cast(str, record.select_one("form input[name=token]")["value"])
        detailed = DetailedParams(idx, token)

    date = parse_time(
        (record.select_one(".play_datalist_date, .box_inner01")).get_text()
    )
    jacket_elem = record.select_one(".play_jacket_img img")
    if (jacket := cast(str | None, jacket_elem.get("data-original"))) is None:
        jacket = cast(str, jacket_elem["src"])
    jacket = jacket.split("/")[-1]
    track = int(record.select_one(".play_track_text").get_text().split(" ")[1])
    title = record.select_one(".play_musicdata_title").get_text()

    score = int(
        record.select_one(".play_musicdata_score_text").get_text().replace(",", "")
    )
    new_record = record.select_one(".play_musicdata_score_img") is not None

    if (rank_elem := record.select_one(".play_musicdata_icon")) is not None:
        rank, clear = get_rank_and_cleartype(rank_elem)
    else:
        rank = Rank.D
        clear = ClearType.FAILED

    return RecentRecord(
        detailed=detailed,
        track=track,
        date=date,
        title=title,
        jacket=jacket,
        difficulty=difficulty_from_imgurl(
            cast(str, record.select_one(".play_track_result img")["src"])
        ),
        score=score,
        rank=rank,
        clear=clear,
        new_record=new_record,
    )


def parse_music_record(
    soup: BeautifulSoup, detailed: Optional[DetailedParams] = None
) -> list[MusicRecord]:
    jacket = (
        str(elem["src"])
        if (elem := soup.select_one(".play_jacket_img img"))
        else ""
    )
    title = (
        elem.get_text(strip=True)
        if (
            elem := soup.select_one(
                ".play_musicdata_title, .play_musicdata_worldsend_title"
            )
        )
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
                detailed=detailed,
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
                            ".musicdata_score_num .text_b:-soup-contains(times), .music_box .block_icon_text span:not([class])"
                        )
                    )
                    is not None
                    else "0"
                ),
            )
        )
    return records


def parse_music_for_rating(soup: BeautifulSoup) -> list[Record]:
    records = []
    for x in soup.select("form:has(.w388.musiclist_box)"):
        if (score_elem := x.select_one(".play_musicdata_highscore .text_b")) is None:
            continue

        if (musicdata := x.select_one(".play_musicdata_icon")) is not None:
            rank, clear = get_rank_and_cleartype(musicdata)
        else:
            rank, clear = Rank.D, ClearType.FAILED

        div = x.select_one(".w388.musiclist_box")
        records.append(
            Record(
                detailed=DetailedParams(
                    idx=int(str(x.select_one("input[name=idx]")["value"])),
                    token=str(x.select_one("input[name=token]")["value"]),
                ),
                title=x.select_one(
                    ".music_title, .musiclist_worldsend_title"
                ).get_text(),
                difficulty=difficulty_from_imgurl(" ".join(div["class"])),
                score=chuni_int(score_elem.get_text()),
                rank=rank,
                clear=clear,
            )
        )
    return records


def parse_detailed_recent_record(soup: BeautifulSoup) -> DetailedRecentRecord:
    def get_judgement_count(class_name):
        return chuni_int(soup.select_one(class_name).get_text().replace(",", ""))

    def get_note_percentage(class_name):
        return float(soup.select_one(class_name).get_text().replace("%", "")) / 100

    record = DetailedRecentRecord.from_basic(
        parse_basic_recent_record(cast("Tag", soup.select_one(".frame01_inside")))
    )

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
        soup.select_one(".play_musicdata_skilleffect_text").get_text().replace("+", "")
    )
    return record
