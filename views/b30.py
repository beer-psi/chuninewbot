import discord
import discord.ui
from discord.ext.commands import Context

from api import MusicRecord

from .pagination import PaginationView


class B30View(PaginationView):
    def __init__(self, ctx: Context, items: list[MusicRecord], per_page: int = 3):
        super().__init__(ctx, items, per_page)
        self.average = sum(item.play_rating for item in items) / len(items)
        self.has_estimated_play_rating = any(item.unknown_const for item in items)

    def format_content(self) -> str:
        return f"Average: **{self.average:.2f}**" + (
            "\nPlay ratings marked with asterisks are estimated (due to lack of chart constants)."
            if self.has_estimated_play_rating
            else ""
        )

    def format_page(
        self, items: list[MusicRecord], start_index: int = 0
    ) -> list[discord.Embed]:
        embeds = []
        for idx, item in enumerate(items):
            embeds.append(
                discord.Embed(
                    description=f"▸ {item.rank} ▸ {item.score} ▸ **{item.play_rating:.2f}{'' if not item.unknown_const else '*'}**\n",
                    color=item.difficulty.color(),
                )
                .set_author(
                    name=f"{idx + start_index + 1}. {item.title} [{item.displayed_difficulty}]"
                )
                .set_thumbnail(url=item.full_jacket_url())
            )
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
