from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context
from PIL import Image, ImageDraw

from api import ChuniNet
from views.profile import ProfileView

if TYPE_CHECKING:
    from bot import ChuniBot
    from cogs.botutils import UtilsCog


@dataclass
class DrawCoordinates:
    sx: int = 0
    sy: int = 0
    dx_offset: int = 0
    dy: int = 0
    width: int = 0
    height: int = 0
    rotate: int = 0


AVATAR_COORDS = {
    "skinfoot_r": DrawCoordinates(
        sy=204,
        dx_offset=84,
        dy=260,
        width=42,
        height=52,
    ),
    "skinfoot_l": DrawCoordinates(
        sx=42,
        sy=204,
        dx_offset=147,
        dy=260,
        width=42,
        height=52,
    ),
    "skin": DrawCoordinates(
        dx_offset=72,
        dy=73,
        width=128,
        height=204,
    ),
    "wear": DrawCoordinates(
        dx_offset=7,
        dy=86,
        width=258,
        height=218,
    ),
    "face": DrawCoordinates(
        dx_offset=107,
        dy=80,
        width=58,
        height=64,
    ),
    "face_cover": DrawCoordinates(dx_offset=78, dy=76, width=116, height=104),
    "head": DrawCoordinates(
        width=200,
        height=150,
        dx_offset=37,
        dy=8,
    ),
    "hand_r": DrawCoordinates(
        width=36,
        height=72,
        dx_offset=52,
        dy=158,
    ),
    "hand_l": DrawCoordinates(
        width=36,
        height=72,
        dx_offset=184,
        dy=158,
    ),
    "item_r": DrawCoordinates(width=100, height=272, dx_offset=9, dy=30, rotate=-5),
    "item_l": DrawCoordinates(
        sx=100, width=100, height=272, dx_offset=163, dy=30, rotate=5
    ),
}


class ProfileCog(commands.Cog, name="Profile"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot
        self.utils: "UtilsCog" = self.bot.get_cog("Utils")  # type: ignore

    @commands.hybrid_command(name="avatar")
    async def avatar(
        self, ctx: Context, *, user: Optional[discord.User | discord.Member] = None
    ):
        """View your CHUNITHM avatar."""
        async with ctx.typing():
            clal = await self.utils.login_check(ctx if user is None else user.id)

            async with ChuniNet(clal) as client:
                basic_data = await client.authenticate()
                avatar_urls = basic_data.avatar

                async with client.session.get(avatar_urls.base) as resp:
                    avatar = Image.open(BytesIO(await resp.read()))
                    avatar = avatar.crop((0, 20, avatar.width, avatar.height))
                async with client.session.get(avatar_urls.back) as resp:
                    back = Image.open(BytesIO(await resp.read()))

                base_x = int((avatar.width - back.width) / 2)
                avatar.paste(back, (base_x, 25), back)

                for name, coords in AVATAR_COORDS.items():
                    url = getattr(avatar_urls, name)
                    async with client.session.get(url) as resp:
                        image = Image.open(BytesIO(await resp.read()))
                    crop = image.crop(
                        (
                            coords.sx,
                            coords.sy,
                            coords.sx + coords.width,
                            coords.sy + coords.height,
                        )
                    ).rotate(coords.rotate, expand=True, resample=Image.BICUBIC)
                    avatar.paste(crop, (base_x + coords.dx_offset, coords.dy), crop)

            with BytesIO() as buffer:
                avatar.save(buffer, "png", optimize=True)
                buffer.seek(0)

                await ctx.reply(
                    content=f"Avatar of {basic_data.name}",
                    file=discord.File(buffer, filename="avatar.png"),
                    mention_author=False,
                )

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
                    level = f"{player_data.reborn}⭐ + {level}"

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
                    .set_thumbnail(url=player_data.character)
                    .set_footer(
                        text=f"Last played on {player_data.last_play_date.strftime('%Y-%m-%d')}"
                    )
                )

                view = ProfileView(ctx, player_data)
                view.message = await ctx.reply(
                    embed=embed,
                    view=view if user is None else None,  # type: ignore
                    mention_author=False,
                )
    
    @commands.hybrid_command(name="rename")
    async def rename(self, ctx: Context, new_name: str):
        async with ctx.typing():
            clal = await self.utils.login_check(ctx.author.id)

            async with ChuniNet(clal) as client:
                await client.authenticate()
                try:
                    if await client.change_player_name(new_name):
                        await ctx.reply("Your username has been changed.", mention_author=False)
                    else:
                        await ctx.reply("There was an error changing your username.", mention_author=False)
                except ValueError as e:
                    raise commands.BadArgument(str(e))
                


async def setup(bot: "ChuniBot"):
    await bot.add_cog(ProfileCog(bot))
