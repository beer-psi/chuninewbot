from collections.abc import Sequence
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import Context

from ..components import ScoreCardEmbed
from .pagination import PaginationView

if TYPE_CHECKING:
    from chunithm_net.entities.player_data import PlayerData

    from ..types.annotated_records import AnnotatedMusicRecord


class CompareView(PaginationView):
    def __init__(
        self,
        ctx: Context,
        player_data: "PlayerData",
        items: Sequence["AnnotatedMusicRecord"],
        per_page: int = 1,
    ):
        self.player_data = player_data
        super().__init__(ctx, items, per_page)

    async def callback(self, interaction: discord.Interaction):
        score = self.items[self.page]
        await interaction.response.edit_message(embed=ScoreCardEmbed(score), view=self)
