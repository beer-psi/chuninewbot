from urllib.parse import quote

import discord
import discord.ui

from .pagination import PaginationView


class SonglistView(PaginationView):
    # tuple is (title, difficulty)
    def __init__(self, songs: list[tuple[str, str]]):
        super().__init__(items=songs, per_page=15)

    def yt_search_query(self, song: tuple[str, str]) -> str:
        return quote(f"CHUNITHM {song[0]} {song[1]}")

    def format_songlist(
        self, songs: list[tuple[str, str]], start_index: int = 0
    ) -> discord.Embed:
        songlist = ""
        for idx, song in enumerate(songs):
            songlist += f"{idx + start_index + 1}. {song[0]} [[{song[1]}]](https://www.youtube.com/results?search_query={self.yt_search_query(song)})\n"
        return discord.Embed(
            description=songlist,
        ).set_footer(text=f"Page {self.page + 1}/{self.max_index + 1}")

    async def callback(self, interaction: discord.Interaction):
        begin = self.page * self.per_page
        end = (self.page + 1) * self.per_page
        await interaction.response.edit_message(
            embed=self.format_songlist(self.items[begin:end], begin), view=self
        )
