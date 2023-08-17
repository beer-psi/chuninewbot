from typing import Optional

from discord.components import SelectOption
from discord.interactions import Interaction
from discord.ui import Select, View, select


class SelectToCompareView(View):
    def __init__(
        self, options: list[tuple[str, int]], *, timeout: Optional[float] = 120
    ):
        super().__init__(timeout=timeout)
        self.value = None
        self.select.options = [SelectOption(label=k, value=str(v)) for k, v in options]

    async def on_timeout(self) -> None:
        self.select.disabled = True
        self.clear_items()
        self.stop()

    @select(placeholder="Select a score...")
    async def select(self, interaction: Interaction, select: Select):
        await interaction.response.edit_message(content="Please wait...", view=None)
        self.value = select.values[0]
        self.stop()
