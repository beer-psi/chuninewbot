import asyncio
import contextlib
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context
from PIL import Image

from chunithm_net.exceptions import ChuniNetError
from utils.views.profile import ProfileView

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


def render_avatar(items: dict[str, bytes]) -> BytesIO:
    avatar = Image.open(BytesIO(items["base"]))

    # crop out the USER AVATAR text at the top
    avatar = avatar.crop((0, 20, avatar.width, avatar.height))

    back = Image.open(BytesIO(items["back"]))

    base_x = int((avatar.width - back.width) / 2)
    avatar.paste(back, (base_x, 25), back)

    for name, coords in AVATAR_COORDS.items():
        image = Image.open(BytesIO(items[name]))
        crop = image.crop(
            (
                coords.sx,
                coords.sy,
                coords.sx + coords.width,
                coords.sy + coords.height,
            )
        ).rotate(coords.rotate, expand=True, resample=Image.BICUBIC)
        avatar.paste(crop, (base_x + coords.dx_offset, coords.dy), crop)

    buffer = BytesIO()
    avatar.save(buffer, "png", optimize=True)
    buffer.seek(0)
    return buffer


class ProfileCog(commands.Cog, name="Profile"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot
        self.utils: "UtilsCog" = self.bot.get_cog("Utils")  # type: ignore[reportGeneralTypeIssues]

    @commands.hybrid_command(name="avatar")
    async def avatar(
        self, ctx: Context, *, user: Optional[discord.User | discord.Member] = None
    ):
        """View your CHUNITHM avatar."""
        async with ctx.typing(), self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            basic_data = await client.authenticate()
            avatar_urls = basic_data.avatar

            async def task(url):
                resp = await client.session.get(url)
                async with contextlib.aclosing(resp) as resp:
                    return await resp.aread()

            tasks = [
                task(avatar_urls.base),
                task(avatar_urls.back),
            ]
            tasks.extend(task(getattr(avatar_urls, name)) for name in AVATAR_COORDS)
            results = await asyncio.gather(*tasks)
            items: dict[str, bytes] = dict(
                zip(
                    ["base", "back", *AVATAR_COORDS],
                    results,
                )
            )

        buffer = await asyncio.to_thread(render_avatar, items)
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

        async with ctx.typing(), self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            player_data = await client.player_data()

            optional_data: list[str] = []
            if player_data.team is not None:
                optional_data.append(f"Team {player_data.team.name}")
            if player_data.medal is not None:
                content = f"Class {player_data.medal}"
                if player_data.emblem is not None:
                    content += f", cleared all of class {player_data.emblem}"
                content += "."
                optional_data.append(content)
            optional_data_joined = "\n".join(optional_data)

            level = str(player_data.lv)
            if player_data.reborn > 0:
                level = f"{player_data.reborn}⭐ + {level}"

            description = (
                f"{optional_data_joined}\n"
                f"▸ **Level**: {level}\n"
                f"▸ **Rating**: {player_data.rating.current:.2f} (MAX {player_data.rating.max:.2f})\n"
                f"▸ **OVER POWER**: {player_data.overpower.value:.2f} ({player_data.overpower.progress * 100:.2f}%)\n"
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
                view=view if user is None else None,  # type: ignore[reportGeneralTypeIssues]
                mention_author=False,
            )

    @commands.hybrid_command(name="rename")
    async def rename(self, ctx: Context, *, new_name: str):
        """Use magical power to change your IGN.

        Please note that this will change the actual display name of your CHUNITHM account.

        Parameters
        ----------
        new_name: str
            The username you want to change to.
            Your username can include up to 8 characters, excluding specific characters. You can also use the following symbols.
            ． ・ ： ； ？ ！ ～ ／ ＋ － × ÷ ＝ ♂ ♀ ∀ ＃ ＆ ＊ ＠ ☆ ○ ◎ ◇ □ △ ▽ ♪ † ‡ Σ α β γ θ φ ψ ω Д ё
        """  # noqa: RUF002

        async with ctx.typing(), self.utils.chuninet(ctx) as client:
            try:
                await client.change_player_name(new_name)
                await ctx.reply("Your username has been changed.", mention_author=False)
            except ValueError as e:
                msg = str(e)

                if msg == "文字数が多すぎます。":  # Too many characters
                    msg = "The new username is too long (only 8 characters allowed)."

                raise commands.BadArgument(msg) from None
            except ChuniNetError as e:
                if e.code == 110106:
                    msg = "The new username contains a banned word."
                    raise commands.BadArgument(msg) from None

                raise


async def setup(bot: "ChuniBot"):
    await bot.add_cog(ProfileCog(bot))
