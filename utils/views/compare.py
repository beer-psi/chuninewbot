from collections.abc import Sequence
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import Context

from utils.components import ScoreCardEmbed

from ._pagination import PaginationView

if TYPE_CHECKING:
    from chunithm_net.models.player_data import PlayerData
    from chunithm_net.models.record import MusicRecord


class CompareView(PaginationView):
    def __init__(
        self,
        ctx: Context,
        player_data: "PlayerData",
        items: Sequence["MusicRecord"],
        per_page: int = 1,
    ):
        self.player_data = player_data
        super().__init__(ctx, items, per_page)

    async def callback(self, interaction: discord.Interaction):
        score = self.items[self.page]
        await interaction.response.edit_message(embed=ScoreCardEmbed(score), view=self)
