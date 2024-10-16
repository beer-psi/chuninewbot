from collections.abc import Sequence
from typing import TYPE_CHECKING

import discord
import discord.ui
from discord.ext.commands import Context

from chunithm_net.consts import KEY_INTERNAL_LEVEL, KEY_PLAY_RATING
from utils import floor_to_ndp
from utils.components import ScoreCardEmbed

from ._pagination import PaginationView

if TYPE_CHECKING:
    from chunithm_net.models.record import Record


class B30View(PaginationView):
    def __init__(
        self,
        ctx: Context,
        items: Sequence["Record"],
        per_page: int = 3,
        *,
        show_average: bool = True,
    ):
        super().__init__(ctx, items, per_page)

        self.average = floor_to_ndp(
            sum(item.extras[KEY_PLAY_RATING] for item in items) / len(items), 2
        )
        self.has_estimated_play_rating = any(
            item.extras.get(KEY_INTERNAL_LEVEL) is None for item in items
        )
        self.show_average = show_average

    def format_content(self) -> str:
        return (f"Average: **{self.average}**" if self.show_average else "") + (
            "\nPlay ratings marked with asterisks are estimated (due to lack of chart constants)."
            if self.has_estimated_play_rating
            else ""
        )

    def format_page(
        self, items: Sequence["Record"], start_index: int = 0
    ) -> Sequence[discord.Embed]:
        embeds: list[discord.Embed] = [
            ScoreCardEmbed(item, index=start_index + idx + 1, show_lamps=False)
            for idx, item in enumerate(items)
        ]
        embeds.append(
            discord.Embed(description=f"Page {self.page + 1}/{self.max_index + 1}")
        )
        return embeds

    async def callback(self, interaction: discord.Interaction):
        begin = self.page * self.per_page
        end = (self.page + 1) * self.per_page
        await interaction.response.edit_message(
            content=self.format_content(),
            embeds=self.format_page(self.items[begin:end], begin),
            view=self,
        )
