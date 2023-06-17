import discord
from discord.ext.commands import Context
from discord.utils import escape_markdown

from api.player_data import PlayerData
from api.record import MusicRecord
from utils import floor_to_ndp
from utils.ranks import rank_icon

from .pagination import PaginationView


class CompareView(PaginationView):
    def __init__(
        self,
        ctx: Context,
        player_data: PlayerData,
        items: list[MusicRecord],
        per_page: int = 1,
    ):
        self.player_data = player_data
        super().__init__(ctx, items, per_page)

    def format_embed(self, score: MusicRecord) -> discord.Embed:
        embed = (
            discord.Embed(
                description=(
                    f"**{escape_markdown(score.title)}** [{score.displayed_difficulty}]\n\n"
                    f"▸ {rank_icon(score.rank)} ▸ {score.clear} ▸ {score.score}"
                ),
                color=score.difficulty.color(),
            )
            .set_author(
                icon_url=self.ctx.author.display_avatar.url,
                name=f"Top play for {self.player_data.name}",
            )
            .set_thumbnail(url=score.full_jacket_url())
        )
        if score.play_rating is not None:
            embed.set_footer(
                text=f"Play rating {floor_to_ndp(score.play_rating, 2)}  •  {score.play_count} attempts"
            )
        return embed

    async def callback(self, interaction: discord.Interaction):
        score = self.items[self.page]
        await interaction.response.edit_message(
            embed=self.format_embed(score), view=self
        )
