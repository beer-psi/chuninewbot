from typing import Optional

import discord.ui
from discord import Interaction
from discord.ext.commands import Context

from api.player_data import PlayerData


class ProfileView(discord.ui.View):
    message: discord.Message

    def __init__(self, ctx: Context, profile: PlayerData, *, timeout: Optional[float] = 120):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.profile = profile

    async def on_timeout(self) -> None:
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True  # type: ignore
        await self.message.edit(view=self)

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        return interaction.user == self.ctx.author
    
    @discord.ui.button(label="Show friend code")
    async def show_hide_friend_code(self, interaction: Interaction, button: discord.ui.Button):
        if button.label == "Show friend code":
            button.label = "Hide friend code"
            await interaction.response.edit_message(content=f"Friend code: {self.profile.friend_code}", view=self)
        else:
            button.label = "Show friend code"
            await interaction.response.edit_message(content="_ _", view=self)
