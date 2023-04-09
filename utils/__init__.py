from datetime import datetime
from urllib.parse import quote

from discord.utils import escape_markdown

from .types import SongSearchResult


def format_level(level: float) -> str:
    return str(level).replace(".0", "").replace(".5", "+")


def did_you_mean_text(result: SongSearchResult) -> str:
    did_you_mean = f"**{escape_markdown(result.title)}**"
    if result.alias is not None:
        did_you_mean = f"**{escape_markdown(result.alias)}** (for {did_you_mean})"
    return f"No songs found. Did you mean {did_you_mean}?"


def yt_search_link(title: str, difficulty: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote(
        f"{title} {difficulty}"
    )


def sdvxin_link(id: str, difficulty: str) -> str:
    if "ULT" not in difficulty and "WE" not in difficulty:
        if difficulty == "MAS":
            difficulty = "MST"
        elif difficulty == "BAS":
            difficulty = "BSC"
        return f"https://sdvx.in/chunithm/{id[:2]}/{id}{difficulty.lower()}.htm"
    else:
        difficulty = difficulty.replace("WE", "end")
        return f"https://sdvx.in/chunithm/{difficulty.lower()[:3]}/{id}{difficulty.lower()}.htm"


def release_to_chunithm_version(date: datetime) -> str:
    if datetime(2015, 7, 16) <= date <= datetime(2016, 1, 21):
        return "CHUNITHM"
    if datetime(2016, 2, 4) <= date <= datetime(2016, 7, 28):
        return "CHUNITHM PLUS"
    if datetime(2016, 8, 25) <= date <= datetime(2017, 1, 26):
        return "AIR"
    if datetime(2017, 2, 9) <= date <= datetime(2017, 8, 3):
        return "AIR PLUS"
    if datetime(2017, 8, 24) <= date <= datetime(2018, 2, 22):
        return "STAR"
    if datetime(2018, 3, 8) <= date <= datetime(2018, 10, 11):
        return "STAR PLUS"
    if datetime(2018, 10, 25) <= date <= datetime(2019, 3, 20):
        return "AMAZON"
    if datetime(2019, 4, 11) <= date <= datetime(2019, 10, 10):
        return "AMAZON PLUS"
    if datetime(2019, 10, 24) <= date <= datetime(2020, 7, 2):
        return "CRYSTAL"
    if datetime(2020, 7, 16) <= date <= datetime(2021, 1, 7):
        return "CRYSTAL PLUS"
    if datetime(2021, 1, 21) <= date <= datetime(2021, 4, 28):
        return "PARADISE"
    if datetime(2021, 5, 13) <= date <= datetime(2021, 10, 21):
        return "PARADISE LOST"
    if datetime(2021, 11, 4) <= date <= datetime(2022, 4, 1):
        return "NEW"
    if datetime(2022, 4, 14) <= date <= datetime(2022, 9, 29):
        return "NEW PLUS"
    return "SUN"
