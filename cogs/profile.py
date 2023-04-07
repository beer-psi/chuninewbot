from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context

from api import ChuniNet
from bot import ChuniBot
from cogs.botutils import UtilsCog
from views.profile import ProfileView


class ProfileCog(commands.Cog, name="Profile"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = self.bot.get_cog("Utils")  # type: ignore

    @commands.hybrid_command(name="chunithm", aliases=["chuni", "profile"])
    async def chunithm(self, ctx: Context, user: Optional[discord.User] = None):
        """View your CHUNITHM profile."""

        async with ctx.typing():
            clal = await self.utils.login_check(ctx if user is None else user.id)

            async with ChuniNet(clal) as client:
                player_data = await client.player_data()

                description = (
                    f"▸ **Level**: {player_data.lv}\n"
                    f"▸ **Rating**: {player_data.rating.current} (MAX {player_data.rating.max})\n"
                    f"▸ **OVER POWER**: {player_data.overpower.value} ({player_data.overpower.progress * 100:.2f}%)\n"
                    f"▸ **Playcount**: {player_data.playcount}\n"
                )

                embed = (
                    discord.Embed(title=player_data.name, description=description)
                    .set_author(name=player_data.nameplate.content)
                    .set_thumbnail(url=player_data.avatar)
                    .set_footer(
                        text=f"Last played on {player_data.last_play_date.strftime('%Y-%m-%d')}"
                    )
                )

                view = ProfileView(ctx, player_data)
                view.message = await ctx.reply(
                    embed=embed,
                    view=view,
                    mention_author=False,
                )


async def setup(bot: ChuniBot):
    await bot.add_cog(ProfileCog(bot))
