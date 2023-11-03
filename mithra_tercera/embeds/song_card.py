from typing import Self
from urllib.parse import quote

import discord
from discord.utils import escape_markdown
from tortoise.exceptions import NoValuesFetched

from mithra_tercera.chunithm_net.constants import JACKET_BASE_URL
from mithra_tercera.db.models import Chart, Song
from mithra_tercera.logger import create_log_ctx
from mithra_tercera.utils.difficulty import DIFFICULTY_TO_EMOJI


logger = create_log_ctx(__name__)


def yt_search_link(song: Song, chart: Chart) -> str:
    diff = chart.difficulty if chart.difficulty != "WE" else f"WORLD'S END {chart.level}"

    # some songs like XL Techno -More Dance Remix- makes YouTube think that
    # we're trying to omit words.
    query = f"CHUNITHM {song.title} {diff}".replace("-", "")

    return f"https://youtube.com/results?search_query={quote(query)}"


class SongCardEmbed(discord.Embed):
    @staticmethod
    def _format_detailed_chart(chart: Chart, chart_view_url: str) -> str:
        link_text = f"Lv.{chart.level}"
        if chart.const is not None:
            link_text += f" ({chart.const:.1f})"

        desc = f"{DIFFICULTY_TO_EMOJI[chart.difficulty]} [{link_text}]({chart_view_url})"

        if chart.charter is not None:
            desc += f" Designer: {escape_markdown(chart.charter)}"

        maxcombo = chart.maxcombo or "-"
        tap = chart.tap or "-"
        hold = chart.hold or "-"
        slide = chart.slide or "-"
        air = chart.air or "-"
        flick = chart.flick or "-"
        desc += (
            f"\n**{maxcombo}** / {tap} / {hold} / {slide} / {air} / {flick}"
        )

        return desc

    @staticmethod
    def _format_chart(chart: Chart, chart_view_url: str) -> str:
        displayed_difficulty = "WORLD'S END" if chart.difficulty == "WE" else chart.difficulty[0]
        desc = f"[{displayed_difficulty}]({chart_view_url}) {chart.level}"

        if chart.const:
            desc += f" ({chart.const:.1f})"

        return desc

    def __init__(self: Self, song: Song, *, detailed: bool = False) -> None:
        super().__init__(
            title=song.title,
            color=discord.Color.yellow()
        )
        self.set_thumbnail(url=f"{JACKET_BASE_URL}/{song.jacket}")

        try:
            charts_by_difficulty = {x.difficulty: x for x in song.charts}
        except NoValuesFetched as e:
            logger.exception(
                (
                    "Related field `charts` was not loaded before passing to SongCardEmbed. "
                    'Call `await song.fetch_related("charts", "charts__sdvxin")` before passing to the embed.'
                ),
                exc_info=e
            )
            return

        self.description = (
            f"**Artist**: {escape_markdown(song.artist)}\n"
            f"**Category**: {song.genre}\n"
            f"**Version**: {song.displayed_version}\n"
            f"**BPM**: {song.bpm if song.bpm is not None else 'Unknown'}\n"
        )

        if len(song.charts) > 0:
            self.description += "\n**Level**:\n"
            if detailed:
                self.description += "**CHAIN** / TAP / HOLD / SLIDE / AIR / FLICK\n\n"

        chart_level_desc = []
        for difficulty in ("BAS", "ADV", "EXP", "MAS", "ULT", "WE"):
            chart = charts_by_difficulty.get(difficulty)

            if chart is None:
                continue

            try:
                # This is fine.
                url = chart.sdvxin.url if chart.sdvxin else yt_search_link(song, chart)  # type: ignore[]
            except NoValuesFetched as e:
                logger.exception(
                    (
                        "Related field `charts__sdvxin` was not loaded before passing to SongCardEmbed. "
                        'Call `await song.fetch_related("charts", "charts__sdvxin")` before passing to the embed.'
                    ),
                    exc_info=e
                )
                return

            chart_level_desc.append(
                SongCardEmbed._format_detailed_chart(chart, url)
                if detailed
                else SongCardEmbed._format_chart(chart, url)
            )

        self.description += ("\n" if detailed else " / ").join(chart_level_desc)
