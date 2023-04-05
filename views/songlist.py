from urllib.parse import quote

import discord
import discord.ui
from discord.ext.commands import Context

from utils import yt_search_link

from .pagination import PaginationView


class SonglistView(PaginationView):
    # tuple is (title, difficulty)
    def __init__(self, ctx: Context, songs: list[tuple[str, str]]):
        super().__init__(ctx, items=songs, per_page=15)

    def format_songlist(
        self, songs: list[tuple[str, str]], start_index: int = 0
    ) -> discord.Embed:
        songlist = ""
        for idx, song in enumerate(songs):
            songlist += f"{idx + start_index + 1}. {song[0]} [[{song[1]}]]({yt_search_link(song[0], song[1])})\n"
        return discord.Embed(
            description=songlist,
        ).set_footer(text=f"Page {self.page + 1}/{self.max_index + 1}")

    async def callback(self, interaction: discord.Interaction):
        begin = self.page * self.per_page
        end = (self.page + 1) * self.per_page
        await interaction.response.edit_message(
            embed=self.format_songlist(self.items[begin:end], begin), view=self
        )
