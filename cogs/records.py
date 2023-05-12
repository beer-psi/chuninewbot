import asyncio
from typing import Optional, cast

import discord
from discord.ext import commands
from discord.ext.commands import Context

from api import ChuniNet
from api.enums import Difficulty
from bot import ChuniBot
from cogs.botutils import UtilsCog
from utils import did_you_mean_text
from views.b30 import B30View
from views.compare import CompareView
from views.recent import RecentRecordsView


class SelectToCompareView(discord.ui.View):
    def __init__(
        self, options: list[tuple[str, int]], *, timeout: Optional[float] = 120
    ):
        super().__init__(timeout=timeout)
        self.value = None
        self.select.options = [
            discord.SelectOption(label=k, value=str(v)) for k, v in options
        ]

    async def on_timeout(self) -> None:
        self.select.disabled = True
        self.stop()

    @discord.ui.select(placeholder="Select a score...")
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.edit_message(content="Please wait...", view=None)
        self.value = select.values[0]
        self.stop()


class RecordsCog(commands.Cog, name="Records"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = self.bot.get_cog("Utils")  # type: ignore

    @commands.hybrid_command(name="recent", aliases=["rs"])
    async def recent(
        self, ctx: Context, *, user: Optional[discord.User | discord.Member] = None
    ):
        """View your recent scores.

        Parameters
        ----------
        user: Optional[discord.User | discord.Member]
            The user to view recent scores for. Defaults to the author.
        """

        async with ctx.typing():
            clal = await self.utils.login_check(ctx if user is None else user.id)

            client = ChuniNet(clal)
            userinfo = await client.authenticate()
            recent_scores = await client.recent_record()

            tasks = [self.utils.annotate_song(score) for score in recent_scores]
            recent_scores = await asyncio.gather(*tasks)

            view = RecentRecordsView(ctx, self.bot, recent_scores, client, userinfo)
            view.message = await ctx.reply(
                content=f"Most recent credits for {userinfo.name}:",
                embeds=view.format_score_page(view.items[0]),
                view=view,
                mention_author=False,
            )

    @commands.hybrid_command("compare", aliases=["c"])
    async def compare(
        self, ctx: Context, *, user: Optional[discord.User | discord.Member] = None
    ):
        """Compare your best score with the most recently posted score.
        You can reply to another user's score to compare with that instead.
        If there are multiple scores, you will be prompted to select one.

        Parameters
        ----------
        user: Optional[discord.User | discord.Member]
            The user to compare with. Defaults to the author.
        """

        async with ctx.typing():
            clal = await self.utils.login_check(ctx if user is None else user.id)

            if ctx.message.reference is not None:
                message = await ctx.channel.fetch_message(
                    cast(int, ctx.message.reference.message_id)
                )
            else:
                bot_messages: list[discord.Message] = [
                    message
                    async for message in ctx.channel.history(limit=50)
                    if message.author == self.bot.user
                    and any(
                        [
                            x.thumbnail.url is not None
                            and "https://new.chunithm-net.com/chuni-mobile/html/mobile/img/"
                            in x.thumbnail.url
                            for x in message.embeds
                        ]
                    )
                ]
                if len(bot_messages) == 0:
                    return await ctx.reply(
                        "No recent scores found.", mention_author=False
                    )
                message = bot_messages[0]

            embeds = [
                x
                for x in message.embeds
                if x.thumbnail.url is not None
                and (
                    "https://new.chunithm-net.com/chuni-mobile/html/mobile/img/"
                    in x.thumbnail.url
                    or "https://dp4p6x0xfi5o9.cloudfront.net/chunithm/img/cover/"
                    in x.thumbnail.url
                )
            ]
            if not embeds:
                raise commands.BadArgument(
                    "The message replied to does not contain any charts/scores."
                )
            if len(embeds) == 1:
                embed = embeds[0]
            else:
                placeholders = ", ".join("?" for _ in range(len(embeds)))
                query = f"SELECT title, jacket FROM chunirec_songs WHERE jacket IN ({placeholders}) OR zetaraku_jacket IN ({placeholders})"
                jackets = [x.thumbnail.url.split("/")[-1] for x in embeds] * 2  # type: ignore
                async with self.bot.db.execute(query, jackets) as cursor:
                    titles = list(await cursor.fetchall())
                jacket_map = {jacket: title for title, jacket in titles}
                view = SelectToCompareView(
                    [(jacket_map[x], i) for i, x in enumerate(jackets)]
                )
                message = await ctx.reply(
                    "Select a score to compare with:", view=view, mention_author=False
                )
                await view.wait()

                if view.value is None:
                    await message.edit(
                        content="Timed out before selecting a score.", view=None
                    )
                    return
                await message.delete()
                embed = embeds[int(view.value)]

            thumbnail_filename = cast(str, embed.thumbnail.url).split("/")[-1]

            async with self.bot.db.execute(
                "SELECT chunithm_id FROM chunirec_songs WHERE jacket = ?",
                (thumbnail_filename,),
            ) as cursor:
                song_id = await cursor.fetchone()
            if song_id is None:
                await ctx.reply("No song found.", mention_author=False)
                return

            song_id = song_id[0]

            async with ChuniNet(clal) as client:
                userinfo = await client.authenticate()
                records = await client.music_record(song_id)

            if len(records) == 0:
                await ctx.reply(
                    f"No records found for {userinfo.name}.", mention_author=False
                )
                return

            futures = [self.utils.annotate_song(record) for record in records]
            records = await asyncio.gather(*futures)

            page = 0
            try:
                # intentionally passing an invalid color so it throws and keep the page at 0
                difficulty = Difficulty.from_embed_color(
                    embed.color.value if embed.color else 0  # type: ignore[attr-defined]
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

    @commands.hybrid_command("scores")
    async def scores(
        self,
        ctx: Context,
        user: Optional[discord.User | discord.Member] = None,
        *,
        query: str,
    ):
        """Get a user's scores for a song.
        If no user is specified, your scores will be shown.

        Parameters
        ----------
        user: Optional[discord.User | discord.Member]
            The user to get scores for.
        query: str
            The song to get scores for.
        """

        async with ctx.typing():
            clal = await self.utils.login_check(ctx if user is None else user.id)

            result = await self.utils.find_song(query)
            if result.similarity < 0.9:
                return await ctx.reply(did_you_mean_text(result), mention_author=False)

            async with ChuniNet(clal) as client:
                userinfo = await client.authenticate()
                records = await client.music_record(result.chunithm_id)

            if len(records) == 0:
                await ctx.reply(
                    f"No records found for {userinfo.name}.", mention_author=False
                )
                return

            futures = [self.utils.annotate_song(record) for record in records]
            records = await asyncio.gather(*futures)

            view = CompareView(ctx, userinfo, records)
            view.message = await ctx.reply(
                embed=view.format_embed(view.items[view.page]),
                view=view,
                mention_author=False,
            )

    @commands.hybrid_command("best30", aliases=["b30"])
    async def best30(
        self, ctx: Context, *, user: Optional[discord.User | discord.Member] = None
    ):
        """View top plays

        Parameters
        ----------
        user: Optional[discord.User | discord.Member]
            The user to get scores for.
        """

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

    @commands.hybrid_command("recent10", aliases=["r10"])
    async def recent10(
        self, ctx: Context, *, user: Optional[discord.User | discord.Member] = None
    ):
        """View top recent plays

        Parameters
        ----------
        user: Optional[discord.User | discord.Member]
            The user to get scores for.
        """

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
