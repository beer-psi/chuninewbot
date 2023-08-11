from collections.abc import Sequence

import discord
import discord.ui
from discord.ext.commands import Context
from discord.utils import escape_markdown

from utils import sdvxin_link, yt_search_link

from .pagination import PaginationView


class SonglistView(PaginationView):
    # tuple is (title, difficulty, sdvx.in id)
    def __init__(self, ctx: Context, songs: Sequence[tuple[str, str, str | None]]):
        super().__init__(ctx, items=songs, per_page=15)

    def format_songlist(
        self, songs: Sequence[tuple[str, str, str | None]], start_index: int = 0
    ) -> discord.Embed:
        songlist = ""
        for idx, song in enumerate(songs):
            url = (
                sdvxin_link(song[2], song[1])
                if song[2]
                else yt_search_link(song[0], song[1])
            )
            songlist += f"{idx + start_index + 1}. {escape_markdown(song[0])} [[{song[1]}]]({url})\n"
        return discord.Embed(
            description=songlist,
        ).set_footer(text=f"Page {self.page + 1}/{self.max_index + 1}")

    async def callback(self, interaction: discord.Interaction):
        begin = self.page * self.per_page
        end = (self.page + 1) * self.per_page
        await interaction.response.edit_message(
            embed=self.format_songlist(self.items[begin:end], begin), view=self
        )
