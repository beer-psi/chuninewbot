from typing import TYPE_CHECKING, Optional

import discord
from discord.utils import escape_markdown

from chunithm_net.consts import JACKET_BASE
from chunithm_net.entities.enums import Difficulty
from utils import sdvxin_link, yt_search_link
from utils.calculation.rating import calculate_rating

if TYPE_CHECKING:
    from database.models import Chart


class ChartCardEmbed(discord.Embed):
    def __init__(self, chart: "Chart", *, target_score: Optional[int] = None) -> None:
        difficulty = Difficulty.from_short_form(chart.difficulty)

        super().__init__(
            title=chart.song.title,
            color=difficulty.color(),
            description=escape_markdown(chart.song.artist),
        )

        self.set_thumbnail(url=f"{JACKET_BASE}/{chart.song.jacket}")

        self.add_field(
            name="Category",
            value=chart.song.genre,
        )

        difficulty_display = chart.level
        if chart.const is not None:
            difficulty_display += f" ({chart.const})"

        difficulty_link = yt_search_link(chart.song.title, chart.difficulty)
        if chart.sdvxin_chart_view is not None:
            difficulty_link = sdvxin_link(chart.sdvxin_chart_view.id, chart.difficulty)

        self.add_field(
            name=str(difficulty), value=f"[{difficulty_display}]({difficulty_link})"
        )

        if target_score is not None:
            field_value = str(target_score)

            if chart.const is not None:
                target_rating = calculate_rating(target_score, chart.const)
                field_value += f" ({target_rating:.2f})"

            self.add_field(
                name="Target Score",
                value=field_value,
            )
