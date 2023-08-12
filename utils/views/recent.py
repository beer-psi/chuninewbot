from collections.abc import Sequence
from typing import AsyncContextManager
from typing import TYPE_CHECKING

import discord.ui
from discord.ext.commands import Context

from bot import ChuniBot

from ..components import ScoreCardEmbed
from .pagination import PaginationView

if TYPE_CHECKING:
    from chunithm_net import ChuniNet
    from chunithm_net.entities.player_data import PlayerData

    from ..types.annotated_records import AnnotatedRecentRecord


def split_scores_into_credits(
    scores: Sequence["AnnotatedRecentRecord"],
) -> Sequence[Sequence["AnnotatedRecentRecord"]]:
    credits = []
    current_credit = []
    for score in scores:
        current_credit.append(score)
        if score.track == 1:
            credits.append(current_credit)
            current_credit = []
    return credits


class RecentRecordsView(PaginationView):
    def __init__(
        self,
        ctx: Context,
        bot: "ChuniBot",
        scores: Sequence["AnnotatedRecentRecord"],
        chuni_client: "ChuniNet",
        chuni_client_manager: AsyncContextManager["ChuniNet"],
        userinfo: "PlayerData",
    ):
        super().__init__(ctx, items=split_scores_into_credits(scores), per_page=1)

        self.chuni_client = chuni_client
        self.chuni_client_manager = chuni_client_manager

        self.userinfo = userinfo
        self.page = 0
        self.max_index = len(self.items) - 1

        self.utils: UtilsCog = bot.get_cog("Utils")  # type: ignore

        self._dropdown_options = [
            discord.SelectOption(
                label=f"{idx + 1}. {score.title} - {score.difficulty}",
                value=f"{score.detailed.idx}",
            )
            for (idx, score) in enumerate(scores)
            if score.detailed is not None
        ]
        self.dropdown.options = self._dropdown_options[:25]

    async def on_timeout(self):
        await self.chuni_client_manager.__aexit__(None, None, None)
        return await super().on_timeout()

    def format_score_page(
        self, scores: Sequence["AnnotatedRecentRecord"]
    ) -> Sequence[discord.Embed]:
        embeds: list[discord.Embed] = [ScoreCardEmbed(score) for score in scores]
        embeds.append(
            discord.Embed(description=f"Page {self.page + 1}/{self.max_index + 1}")
        )
        return embeds

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embeds=self.format_score_page(self.items[self.page]), view=self
        )

    @discord.ui.button(label="26-50")
    async def switch_to_26_50(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if button.label == "26-50":
            self.dropdown.options = self._dropdown_options[25:]
            button.label = "1-25"
        else:
            self.dropdown.options = self._dropdown_options[:25]
            button.label = "26-50"
        await interaction.response.edit_message(view=self)

    @discord.ui.select(placeholder="Select a score", row=1)
    async def dropdown(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        await interaction.response.defer()

        idx = int(select.values[0])
        score = await self.chuni_client.detailed_recent_record(idx)
        score = await self.utils.annotate_song(score)
        await interaction.channel.send(
            content=f"Score of {self.userinfo.name}",
            embed=ScoreCardEmbed(score),
        )
