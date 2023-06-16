from discord import Embed, Interaction
from discord.ext.commands import Context

from .pagination import PaginationView


class LoginFlowView(PaginationView):
    SCRIPT = "javascript:void(function(d){var s=d.createElement('script');s.src='https://gistcdn.githack.com/beerpiss/0eb8d3e50ae753388a6d4a4af5678a2e/raw/1d1ca5c7b8322d44fea7c1406e37de0675514460/login.js' + '?t=' + Math.floor(Date.now()/60000);d.body.append(s)}(document))\n"

    def __init__(self, ctx: Context, code: str):
        items = [
            (
                "**Step 1:**\n"
                "Log into [CHUNITHM-NET](https://chunithm-net-eng.com) in an incognito/private window.\n"
                "(right click and copy link on desktop, long press and copy link on mobile)"
            ),
            (
                "**Step 2**:\n"
                f"Copy [this link](https://lng-tgk-aime-gw.am-all.net/common_auth/?otp={code}) and paste it in the current incognito window.\n"
                'The website should display "Not Found".'
            ),
            (
                "**Step 3**:\n\n"
                "**Desktop users:**\n"
                "Copy the script above and paste it in your browser's developer console (Ctrl + Shift + I or F12).\n\n"
                "**Mobile users:**\n"
                "1. Long press the message above and select \"Copy Text\".\n"
                "2. Create a bookmark in your browser and paste the copied text in the URL field.\n"
                "3. Run the bookmark.\n\n"
                "This script cannot access your Aime account! It can only access CHUNITHM-NET.\n"
                "\n"
                f"If the website asks for a passcode, enter **{code}** and select OK."
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
            content=self.SCRIPT if self.page == 2 else None, embed=self.format_embed(description), view=self
        )
