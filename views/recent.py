from math import floor

import discord.ui

from api import ChuniNet
from bot import ChuniBot
from api.record import RecentRecord, DetailedRecentRecord
from cogs.botutils import UtilsCog


def split_scores_into_credits(scores: list[RecentRecord]) -> list[list[RecentRecord]]:
    credits = []
    current_credit = []
    for score in scores:
        current_credit.append(score)
        if score.track == 1:
            credits.append(current_credit)
            current_credit = []
    return credits


class RecentRecordsView(discord.ui.View):
    message: discord.Message

    def __init__(self, bot: ChuniBot, scores: list[RecentRecord], chuni_client: ChuniNet):
        super().__init__(timeout=120)
        self.chuni_client = chuni_client
        self.scores = split_scores_into_credits(scores)
        self.page = 0
        self.max_index = len(self.scores) - 1

        self.utils: UtilsCog = bot.get_cog("Utils")  # type: ignore

        self.dropdown.options = [
            discord.SelectOption(label=f"{idx + 1}. {score.title} - {score.difficulty}", value=f"{score.detailed.idx}")
            for (idx, score) in enumerate(scores)
        ][:25]

    async def on_timeout(self) -> None:
        await self.chuni_client.session.close()
        for item in self.children:
            if isinstance(item, discord.ui.Button) or isinstance(item, discord.ui.Select):
                item.disabled = True
        await self.message.edit(view=self)
        
    def format_score_page(self, scores: list[RecentRecord]) -> list[discord.Embed]:
        embeds = []
        for score in scores:
            embed = (
                discord.Embed(
                    description=f"**{score.title} [{score.difficulty} {score.internal_level if not score.unknown_const else score.level}]**\n\n▸ {score.rank} ▸ {score.clear} ▸ {score.score}",
                    timestamp=score.date,
                )
                    .set_author(name=f"TRACK {score.track}")
                    .set_thumbnail(url=score.jacket)
            )
            if score.play_rating is not None:
                embed.set_footer(text=f"Rating {score.play_rating:.2f}")
            embeds.append(embed)

        embeds.append(
            discord.Embed(description=f"Page {self.page + 1}/{self.max_index + 1}")
        )
        return embeds

    def format_detailed_score_page(self, score: DetailedRecentRecord) -> discord.Embed:
        embed = (
            discord.Embed(
                description=(
                    f"**{score.title} [{score.difficulty} {score.internal_level if not score.unknown_const else score.level}]**\n\n"
                    f"▸ {score.rank} ▸ {score.clear} ▸ {score.score} ▸ x{score.max_combo}{f'/{score.full_combo}' if score.full_combo else ''}\n"
                    f"▸ CRITICAL {score.judgements.jcrit}/JUSTICE {score.judgements.justice}/ATTACK {score.judgements.attack}/MISS {score.judgements.miss}\n"
                    f"▸ TAP {score.note_type.tap * 100:.2f}%/HOLD {score.note_type.hold * 100:.2f}%/SLIDE {score.note_type.slide * 100:.2f}%/AIR {score.note_type.air * 100:.2f}%/FLICK {score.note_type.flick * 100:.2f}%"
                ),
                timestamp=score.date,
            )
                .set_author(name=f"TRACK {score.track}")
                .set_thumbnail(url=score.jacket)
        )
        if score.play_rating is not None:
            embed.set_footer(text=f"Rating {score.play_rating:.2f}")
        return embed

    def toggle_buttons(self):
        self.to_first_page.disabled = self.to_previous_page.disabled = self.page == 0
        self.to_next_page.disabled = self.to_last_page.disabled = (
            self.page == self.max_index
        )

    async def update(self, interaction: discord.Interaction):
        self.toggle_buttons()
        await interaction.response.edit_message(
            embeds=self.format_score_page(self.scores[self.page]), view=self
        )

    @discord.ui.button(label="<<", style=discord.ButtonStyle.grey, disabled=True)
    async def to_first_page(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        self.page = 0
        await self.update(interaction)

    @discord.ui.button(label="<", style=discord.ButtonStyle.grey, disabled=True)
    async def to_previous_page(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        self.page -= 1
        await self.update(interaction)

    @discord.ui.button(label=">", style=discord.ButtonStyle.grey)
    async def to_next_page(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        self.page += 1
        await self.update(interaction)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.grey)
    async def to_last_page(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        self.page = self.max_index
        await self.update(interaction)
    
    @discord.ui.select(placeholder="Select a score", row=1)
    async def dropdown(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()

        idx = int(select.values[0])
        score = await self.chuni_client.detailed_recent_record(idx)
        await self.utils.annotate_song(score)
        await interaction.channel.send(embed=self.format_detailed_score_page(score))
        

