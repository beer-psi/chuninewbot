from typing import Sequence

import discord
from discord import Embed
from discord.ext.commands import Context

from ._pagination import PaginationView


class EmbedPaginationView(PaginationView):
    def __init__(self, ctx: Context, items: Sequence[Embed], per_page: int = 1):
        super().__init__(ctx, items, per_page)

    async def callback(self, interaction: discord.Interaction):
        begin = self.page * self.per_page
        end = (self.page + 1) * self.per_page
        await interaction.response.edit_message(embeds=self.items[begin:end], view=self)
