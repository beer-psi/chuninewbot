from abc import abstractmethod
from math import ceil

import discord.ui
from discord import Interaction
from discord.ext.commands import Context


class PaginationView(discord.ui.View):
    message: discord.Message

    def __init__(self, ctx: Context, items: list, per_page: int = 5):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.items = items
        self.page = 0
        self.per_page = per_page
        self.max_index = ceil(len(self.items) / per_page) - 1

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user == self.ctx.author    

    async def on_timeout(self) -> None:
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True
        await self.message.edit(view=self)

    def toggle_buttons(self):
        self.to_first_page.disabled = self.to_previous_page.disabled = self.page == 0
        self.to_next_page.disabled = self.to_last_page.disabled = (
            self.page == self.max_index
        )

    async def update(self, interaction: discord.Interaction):
        self.toggle_buttons()
        await self.callback(interaction)

    @abstractmethod
    async def callback(self, interaction: discord.Interaction):
        ...

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
