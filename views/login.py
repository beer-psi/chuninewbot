import discord
from discord import Embed, Interaction
from discord.ext.commands import Context

from .pagination import PaginationView


class LoginFlowView(PaginationView):
    def __init__(self, ctx: Context, code: int):
        items = [
            (
                "**Step 1:**\n"
                "Log into [CHUNITHM-NET](https://chunithm-net-eng.com) in an incognito/private window.\n"
                "(right click and copy link on desktop, long press and copy link on mobile)"
            ),
            (
                "**Step 2**:\n"
                "Copy [this link](https://lng-tgk-aime-gw.am-all.net/common_auth/?ssid=9326) and paste it in the current incognito window.\n"
                'The website should display "Not Found".'
            ),
            (
                "**Step 3**:\n"
                "Open the developer console (F12), paste in this code and press enter:\n"
                "```js\n"
                "\n"
                "```\n"
                "This script cannot access your cab data! It can only be used to access CHUNITHM-NET.\n"
                "\n"
                f"In case the script asks for a code, enter **{code}**."
            ),
        ]

        super().__init__(ctx, items, 1)

    def format_embed(self, item: str) -> Embed:
        return Embed(
            title="How to login",
            description=item,
        )

    async def callback(self, interaction: Interaction):
        description = self.items[self.page]
        await interaction.response.edit_message(
            embed=self.format_embed(description), view=self
        )
