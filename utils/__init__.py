import decimal
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import quote
from zoneinfo import ZoneInfo

from discord.ext.commands.view import StringView
from discord.utils import escape_markdown

if TYPE_CHECKING:
    from typing import Sequence, TypeVar

    from database.models import Alias, Song

    T = TypeVar("T", decimal.Decimal, float, str, int)


TOKYO_TZ = ZoneInfo("Asia/Tokyo")


def shlex_split(s: str) -> list[str]:
    view = StringView(s)
    result = []

    while not view.eof:
        view.skip_ws()
        if view.eof:
            break

        word = view.get_quoted_word()
        if word is None:
            break

        result.append(word)

    return result


def floor_to_ndp(number: "T", dp: int) -> "T":
    with decimal.localcontext() as ctx:
        ctx.rounding = decimal.ROUND_FLOOR
        return type(number)(round(decimal.Decimal(number), dp))


def round_to_nearest(number: "T", value: int) -> "T":
    digit_count = len(str(value))

    multiplier: int = 10**digit_count // value
    round_dp = -digit_count

    return type(number)(
        round(decimal.Decimal(number * multiplier), round_dp) / multiplier
    )


def did_you_mean_text(result: "Song | None", alias: "Alias | None") -> str:
    did_you_mean = ""
    if result is not None:
        did_you_mean = f"Did you mean **{escape_markdown(result.title)}**?"
        if alias is not None:
            did_you_mean = f"Did you mean **{escape_markdown(alias.alias)}** (for **{escape_markdown(result.title)}**)?"

    reply = f"No songs found. {did_you_mean}".strip()
    if did_you_mean:
        reply += "\n(You can also use `addalias <title> <alias>` to add the alias for this server.)"

    return reply


def yt_search_link(title: str, difficulty: str) -> str:
    if difficulty == "WE":
        difficulty = "WORLD'S END"
    return "https://www.youtube.com/results?search_query=" + quote(
        f"CHUNITHM {title} {difficulty}"
    )


def sdvxin_link(id: str, difficulty: str) -> str:
    if "ULT" not in difficulty and "WE" not in difficulty:
        if difficulty == "MAS":
            difficulty = "MST"
        elif difficulty == "BAS":
            difficulty = "BSC"
        return f"https://sdvx.in/chunithm/{id[:2]}/{id}{difficulty.lower()}.htm"

    difficulty = difficulty.replace("WE", "end")
    return f"https://sdvx.in/chunithm/{difficulty.lower()[:3]}/{id}{difficulty.lower()}.htm"


def release_to_chunithm_version(date: datetime) -> str:
    if (
        datetime(2015, 7, 16, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2016, 1, 21, tzinfo=TOKYO_TZ)
    ):
        return "CHUNITHM"
    if (
        datetime(2016, 2, 4, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2016, 7, 28, tzinfo=TOKYO_TZ)
    ):
        return "CHUNITHM PLUS"
    if (
        datetime(2016, 8, 25, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2017, 1, 26, tzinfo=TOKYO_TZ)
    ):
        return "AIR"
    if (
        datetime(2017, 2, 9, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2017, 8, 3, tzinfo=TOKYO_TZ)
    ):
        return "AIR PLUS"
    if (
        datetime(2017, 8, 24, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2018, 2, 22, tzinfo=TOKYO_TZ)
    ):
        return "STAR"
    if (
        datetime(2018, 3, 8, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2018, 10, 11, tzinfo=TOKYO_TZ)
    ):
        return "STAR PLUS"
    if (
        datetime(2018, 10, 25, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2019, 3, 20, tzinfo=TOKYO_TZ)
    ):
        return "AMAZON"
    if (
        datetime(2019, 4, 11, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2019, 10, 10, tzinfo=TOKYO_TZ)
    ):
        return "AMAZON PLUS"
    if (
        datetime(2019, 10, 24, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2020, 7, 2, tzinfo=TOKYO_TZ)
    ):
        return "CRYSTAL"
    if (
        datetime(2020, 7, 16, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2021, 1, 7, tzinfo=TOKYO_TZ)
    ):
        return "CRYSTAL PLUS"
    if (
        datetime(2021, 1, 21, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2021, 4, 28, tzinfo=TOKYO_TZ)
    ):
        return "PARADISE"
    if (
        datetime(2021, 5, 13, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2021, 10, 21, tzinfo=TOKYO_TZ)
    ):
        return "PARADISE LOST"
    if (
        datetime(2021, 11, 4, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2022, 4, 1, tzinfo=TOKYO_TZ)
    ):
        return "NEW"
    if (
        datetime(2022, 4, 14, tzinfo=TOKYO_TZ)
        <= date
        <= datetime(2022, 9, 29, tzinfo=TOKYO_TZ)
    ):
        return "NEW PLUS"
    return "SUN"
