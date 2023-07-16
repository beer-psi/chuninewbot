from datetime import datetime, timedelta, timezone
from typing import Optional, cast

from bs4.element import ResultSet, Tag

from .enums import ClearType, Difficulty, Rank


def chuni_int(s: str) -> int:
    return int(s.replace(",", ""))


def get_attribute(soup: Optional[Tag], attr: str) -> str | list[str]:
    if soup is None:
        return ""
    if (ret := soup.get(attr, "")) is None:
        return ""
    return ret


def get_text(soup: Optional[Tag]) -> str:
    if soup is None:
        return ""
    return soup.get_text()


def parse_player_rating(soup: ResultSet[Tag]) -> float:
    rating = ""
    for x in soup:
        digit = cast(str, x["src"]).split("_")[-1].split(".")[0]
        if digit == "comma":
            rating += "."
        else:
            rating += digit[1]
    return float(rating)


def parse_time(time: str, format: str = "%Y/%m/%d %H:%M") -> datetime:
    return (datetime.strptime(time, format) - timedelta(hours=9)).replace(
        tzinfo=timezone.utc
    )  # JP time


def extract_last_part(url: str) -> str:
    return url.split("_")[-1].split(".")[0]


def difficulty_from_imgurl(url: str) -> Difficulty:
    match extract_last_part(url):
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
        case "ultima":
            return Difficulty.ULTIMA
        case "ultimate":
            return Difficulty.ULTIMA

        case _:
            raise ValueError(f"Unknown difficulty: {url}")


def get_rank_and_cleartype(soup: Tag) -> tuple[Rank, ClearType]:
    if (rank_img_elem := soup.select_one("img[src*=_rank_]")) is not None:
        rank_img_url = cast(str, rank_img_elem["src"])
        rank = Rank(int(rank_img_url.split("_")[-1].split(".")[0]))
    else:
        rank = Rank.D

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
