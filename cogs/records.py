import asyncio
from typing import cast, Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context

from api import ChuniNet
from bot import ChuniBot
from api.enums import Difficulty
from views.b30 import B30View
from views.compare import CompareView
from views.recent import RecentRecordsView

from cogs.botutils import UtilsCog


class RecordsCog(commands.Cog, name="Records"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = self.bot.get_cog("Utils")  # type: ignore

    @commands.command(name="recent", aliases=["rs"])
    async def recent(self, ctx: Context, user: Optional[discord.User] = None):
        """View your recent scores."""

        async with ctx.typing():
            clal = await self.utils.login_check(ctx if user is None else user.id)

            client = ChuniNet(clal)
            userinfo = await client.authenticate()
            recent_scores = await client.recent_record()

            tasks = [self.utils.annotate_song(score) for score in recent_scores]
            recent_scores = await asyncio.gather(*tasks)

            view = RecentRecordsView(ctx, self.bot, recent_scores, client)
            view.message = await ctx.reply(
                content=f"Most recent credits for {userinfo.name}:",
                embeds=view.format_score_page(view.items[0]),
                view=view,
                mention_author=False,
            )

    @commands.command("compare", aliases=["c"])
    async def compare(self, ctx: Context, user: Optional[discord.User] = None):
        """Compare your best score with the most recently posted score."""

        async with ctx.typing():
            clal = await self.utils.login_check(ctx if user is None else user.id)

            if ctx.message.reference is not None:
                message = await ctx.channel.fetch_message(
                    cast(int, ctx.message.reference.message_id)
                )
                if (
                    len(message.embeds) > 1
                    or len(message.embeds) == 0
                    or message.embeds[0].thumbnail.url is None
                    or "https://new.chunithm-net.com/chuni-mobile/html/mobile/img/"
                    not in message.embeds[0].thumbnail.url
                ):
                    raise commands.BadArgument(
                        "The message replied to does not contain a detailed score embed."
                    )
                embed = message.embeds[0]
            else:
                bot_messages: list[discord.Message] = [
                    message
                    async for message in ctx.channel.history(limit=50)
                    if len(message.embeds) == 1
                    and message.embeds[0].thumbnail.url is not None
                    and "https://new.chunithm-net.com/chuni-mobile/html/mobile/img/"
                    in message.embeds[0].thumbnail.url
                ]
                if len(bot_messages) == 0:
                    await ctx.reply("No recent scores found.", mention_author=False)
                    return
                embed = bot_messages[0].embeds[0]

            thumbnail_filename = cast(str, embed.thumbnail.url).split("/")[-1]

            cursor = await self.bot.db.execute(
                "SELECT chunithm_id FROM chunirec_songs WHERE jacket = ?",
                (thumbnail_filename,),
            )
            song_id = await cursor.fetchone()
            if song_id is None:
                await ctx.reply("No song found.", mention_author=False)
                return

            song_id = song_id[0]

            async with ChuniNet(clal) as client:
                userinfo = await client.authenticate()
                records = await client.music_record(song_id)

            futures = [self.utils.annotate_song(record) for record in records]
            records = await asyncio.gather(*futures)

            if len(records) == 0:
                await ctx.reply(
                    f"No records found for {userinfo.name}.", mention_author=False
                )
                return

            page = 0
            try:
                difficulty = Difficulty.from_embed_color(
                    embed.color.value if embed.color else 0x8C1BE1
                )
                page = next(
                    (
                        i
                        for i, record in enumerate(records)
                        if record.difficulty == difficulty
                    ),
                    0,
                )
            except ValueError:
                pass

            view = CompareView(ctx, userinfo, records)
            view.page = page
            view.message = await ctx.reply(
                embed=view.format_embed(view.items[view.page]),
                view=view,
                mention_author=False,
            )

    @commands.command("best30", aliases=["b30"])
    async def best30(self, ctx: Context, user: Optional[discord.User] = None):
        """View top plays"""

        async with ctx.typing():
            clal = await self.utils.login_check(ctx if user is None else user.id)

            async with ChuniNet(clal) as client:
                best30 = await client.best30()

            tasks = [self.utils.annotate_song(score) for score in best30]
            best30 = await asyncio.gather(*tasks)

            view = B30View(ctx, best30)
            view.message = await ctx.reply(
                content=view.format_content(),
                embeds=view.format_page(view.items[: view.per_page]),
                view=view,
                mention_author=False,
            )

    @commands.command("recent10", aliases=["r10"])
    async def recent10(self, ctx: Context, user: Optional[discord.User] = None):
        """View top recent plays"""

        async with ctx.typing():
            clal = await self.utils.login_check(ctx if user is None else user.id)

            async with ChuniNet(clal) as client:
                recent10 = await client.recent10()

            tasks = [self.utils.annotate_song(score) for score in recent10]
            recent10 = await asyncio.gather(*tasks)

            view = B30View(ctx, recent10)
            view.message = await ctx.reply(
                content=view.format_content(),
                embeds=view.format_page(view.items[: view.per_page]),
                view=view,
                mention_author=False,
            )


async def setup(bot: ChuniBot):
    await bot.add_cog(RecordsCog(bot))
