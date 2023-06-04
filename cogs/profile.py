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
    async def chunithm(
        self, ctx: Context, *, user: Optional[discord.User | discord.Member] = None
    ):
        """View your CHUNITHM profile."""

        async with ctx.typing():
            clal = await self.utils.login_check(ctx if user is None else user.id)

            async with ChuniNet(clal) as client:
                player_data = await client.player_data()

                level = str(player_data.lv)
                if player_data.reborn > 0:
                    level += f" ({player_data.reborn}⭐)"

                class_ = ""
                if player_data.medal is not None:
                    class_ += f"Class {player_data.medal}"
                if player_data.emblem is not None:
                    class_ += f", cleared all of class {player_data.emblem}"
                if len(class_) > 0:
                    class_ += "."

                description = (
                    f"{class_}\n"
                    f"▸ **Level**: {level}\n"
                    f"▸ **Rating**: {player_data.rating.current} (MAX {player_data.rating.max})\n"
                    f"▸ **OVER POWER**: {player_data.overpower.value} ({player_data.overpower.progress * 100:.2f}%)\n"
                    f"▸ **Playcount**: {player_data.playcount}\n"
                )

                embed = (
                    discord.Embed(
                        title=player_data.name,
                        description=description,
                        color=player_data.possession.color(),
                    )
                    .set_author(name=player_data.nameplate.content)
                    .set_thumbnail(url=player_data.avatar)
                    .set_footer(
                        text=f"Last played on {player_data.last_play_date.strftime('%Y-%m-%d')}"
                    )
                )

                view = ProfileView(ctx, player_data)
                view.message = await ctx.reply(
                    embed=embed,
                    view=view if user is None else None,
                    mention_author=False,
                )


async def setup(bot: ChuniBot):
    await bot.add_cog(ProfileCog(bot))
