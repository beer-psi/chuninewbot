from datetime import datetime, timedelta, timezone

from bs4.element import ResultSet, Tag

from .enums import ClearType, Difficulty, Rank
from .record import DetailedParams, RecentRecord


def chuni_int(s: str) -> int:
    return int(s.replace(",", ""))


def parse_player_rating(soup: ResultSet[Tag]) -> float:
    rating = ""
    for x in soup:
        digit = x["src"].split("_")[-1].split(".")[0]
        if digit == "comma":
            rating += "."
        else:
            rating += digit[1]
    return float(rating)


def parse_time(time: str, format: str = "%Y/%m/%d %H:%M") -> datetime:
    return (datetime.strptime(time, format) - timedelta(hours=9)).replace(
        tzinfo=timezone.utc
    )  # JP time


def difficulty_from_imgurl(url: str) -> Difficulty:
    match url.split("_")[-1].split(".")[0]:
        case "basic":
            return Difficulty.BASIC
        case "advanced":
            return Difficulty.ADVANCED
        case "expert":
            return Difficulty.EXPERT
        case "master":
            return Difficulty.MASTER
        case "worldsend":
            return Difficulty.WORLDS_END

        case _:
            raise ValueError(f"Unknown difficulty: {url}")


def get_rank_and_cleartype(soup: Tag) -> tuple[Rank, ClearType]:
    rank_img_url = soup.select_one("img[src*=_rank_]")["src"]
    rank = Rank(int(rank_img_url.split("_")[-1].split(".")[0]))

    clear_type = (
        ClearType.CLEAR
        if soup.select_one("img[src*=clear]") is not None
        else ClearType.FAILED
    )
    if clear_type == ClearType.CLEAR:
        if soup.select_one("img[src*=fullcombo]") is not None:
            clear_type = ClearType.FULL_COMBO
        elif soup.select_one("img[src*=alljustice]") is not None:
            clear_type = ClearType.ALL_JUSTICE

    return rank, clear_type


def parse_basic_recent_record(record: Tag) -> RecentRecord:
    idx_elem = record.select_one("form input[name=idx]")
    if idx_elem is None:
        detailed = None
    else:
        idx = int(idx_elem["value"])
        token = record.select_one("form input[name=token]")["value"]
        detailed = DetailedParams(idx, token)

    date = parse_time(
        (record.select_one(".play_datalist_date, .box_inner01")).get_text()
    )
    jacket_elem = record.select_one(".play_jacket_img img")
    if (jacket := jacket_elem.get("data-original")) is None:
        jacket = jacket_elem["src"]
    track = int(record.select_one(".play_track_text").get_text().split(" ")[1])
    title = record.select_one(".play_musicdata_title").get_text()

    score = int(
        record.select_one(".play_musicdata_score_text").get_text().replace(",", "")
    )
    new_record = record.select_one(".play_musicdata_score_img") is not None
    rank, clear = get_rank_and_cleartype(record.select_one(".play_musicdata_icon"))

    return RecentRecord(
        detailed=detailed,
        track=track,
        date=date,
        title=title,
        jacket=jacket,
        difficulty=difficulty_from_imgurl(
            record.select_one(".play_track_result img")["src"]
        ),
        score=score,
        rank=rank,
        clear=clear,
        new_record=new_record,
    )
