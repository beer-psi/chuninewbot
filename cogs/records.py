import asyncio
import logging
from types import SimpleNamespace
from typing import TYPE_CHECKING, Optional, cast

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from sqlalchemy import select

from chunithm_net.consts import JACKET_BASE
from chunithm_net.entities.enums import Difficulty
from database.models import Song
from utils import did_you_mean_text, shlex_split
from utils.components import ScoreCardEmbed
from utils.views import B30View, CompareView, RecentRecordsView, SelectToCompareView

if TYPE_CHECKING:
    from bot import ChuniBot
    from cogs.autocompleters import AutocompletersCog
    from cogs.botutils import UtilsCog


logger = logging.getLogger("chuninewbot")


class RecordsCog(commands.Cog, name="Records"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot
        self.utils: "UtilsCog" = self.bot.get_cog("Utils")  # type: ignore[reportGeneralTypeIssues]
        self.autocompleters: "AutocompletersCog" = self.bot.get_cog("Autocompleters")  # type: ignore[reportGeneralTypeIssues]

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
            ctxmgr = self.utils.chuninet(ctx if user is None else user.id)
            client = await ctxmgr.__aenter__()
            userinfo = await client.authenticate()
            recent_scores = await client.recent_record()

            tasks = [self.utils.annotate_song(score) for score in recent_scores]
            recent_scores = await asyncio.gather(*tasks)

            view = RecentRecordsView(
                ctx, self.bot, recent_scores, client, ctxmgr, userinfo
            )
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
        """Compare your best score with another score.

        By default, it's the most recently posted score. You can reply to another
        user's score to compare with that instead. If there are multiple scores in
        said message, you will be prompted to select one.

        Parameters
        ----------
        user: Optional[discord.User | discord.Member]
            The user to compare with. Defaults to the author.
        """

        async with ctx.typing(), self.bot.begin_db_session() as session, self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
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
                        x.thumbnail.url is not None and JACKET_BASE in x.thumbnail.url
                        for x in message.embeds
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
                    JACKET_BASE in x.thumbnail.url
                    or "https://dp4p6x0xfi5o9.cloudfront.net/chunithm/img/cover/"
                    in x.thumbnail.url
                )
            ]
            if not embeds:
                msg = "The message replied to does not contain any charts/scores."
                raise commands.BadArgument(msg)
            if len(embeds) == 1:
                embed = embeds[0]
                compare_message = None
            else:
                jackets = [x.thumbnail.url.split("/")[-1] for x in embeds]  # type: ignore[reportGeneralTypeIssues]
                stmt = select(Song).where(
                    (Song.jacket.in_(jackets)) | (Song.zetaraku_jacket.in_(jackets))
                )
                songs = (await session.execute(stmt)).scalars().all()

                jacket_map = {song.jacket: song.title for song in songs}
                view = SelectToCompareView(
                    [(jacket_map[x], i) for i, x in enumerate(jackets)]
                )
                compare_message = await ctx.reply(
                    "Select a score to compare with:", view=view, mention_author=False
                )
                await view.wait()

                if view.value is None:
                    await compare_message.edit(
                        content="Timed out before selecting a score.", view=None
                    )
                    return None
                embed = embeds[int(view.value)]

            thumbnail_filename = cast(str, embed.thumbnail.url).split("/")[-1]

            stmt = select(Song).where(
                (Song.jacket == thumbnail_filename)
                | (Song.zetaraku_jacket == thumbnail_filename)
            )
            song = (await session.execute(stmt)).scalar_one_or_none()
            if song is None:
                await ctx.reply("No song found.", mention_author=False)
                return None

            userinfo = await client.authenticate()
            records = await client.music_record(song.chunithm_id)

            if len(records) == 0:
                await ctx.reply(
                    f"No records found for {userinfo.name}.", mention_author=False
                )
                return None

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

            if compare_message is not None:
                view.message = compare_message
                await compare_message.edit(
                    content=f"Top play for {userinfo.name}",
                    embed=ScoreCardEmbed(view.items[view.page]),
                    view=view,
                )
                return None
            view.message = await ctx.reply(
                content=f"Top play for {userinfo.name}",
                embed=ScoreCardEmbed(view.items[view.page]),
                view=view,
                mention_author=False,
            )
            return None

    async def song_title_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.autocompleters.song_title_autocomplete(interaction, current)

    @app_commands.command(name="scores", description="Get scores for a specific song.")
    @app_commands.describe(
        query="Song title to search for. You don't have to be exact; try things out!",
        user="Check scores of this Discord user. Yourself, if not provided.",
        worlds_end="Search for WORLD'S END songs instead of standard songs.",
    )
    @app_commands.autocomplete(query=song_title_autocomplete)
    async def scores_slash(
        self,
        interaction: "discord.Interaction[ChuniBot]",
        query: str,
        *,
        user: Optional[discord.User | discord.Member] = None,
        worlds_end: bool = False,
    ):
        if user is not None:
            query = f"{user.mention} {query}"
        if worlds_end:
            query += " -we"

        ctx = await Context.from_interaction(interaction)
        return await self.scores(ctx, query=query)

    @commands.command("scores")
    async def scores(
        self,
        ctx: Context,
        *,
        query: str,
    ):
        """**Get a user's scores for a song.
        If no user is specified, your scores will be shown.**

        **Parameters:**
        `username`: Discord username of the player. Yourself, if not provided.
        `query`: Song title to search for.
        `-we`: Search for WORLD'S END songs instead of standard songs (no param).
        """
        args = SimpleNamespace(worlds_end=False, query=[])

        argv = shlex_split(query)
        for arg in argv:
            if arg in ["-we", "--worlds-end"]:
                args.worlds_end = True
            else:
                args.query.append(arg)

        user = None
        query = " ".join(args.query)
        for converter in [commands.MemberConverter, commands.UserConverter]:
            try:
                user = await converter().convert(ctx, args.query[0])
                query = " ".join(args.query[1:])
            # We need to iterate over all converters, so PERF203 does not
            # apply here.
            except commands.BadArgument:  # noqa: PERF203
                pass

        async with ctx.typing(), self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            guild_id = ctx.guild.id if ctx.guild else None
            song, alias, similarity = await self.utils.find_song(
                query, guild_id=guild_id, worlds_end=args.worlds_end
            )
            if song is None or similarity < 0.9:
                return await ctx.reply(
                    did_you_mean_text(song, alias), mention_author=False
                )

            userinfo = await client.authenticate()

            records = await client.music_record(song.chunithm_id)

            if len(records) == 0:
                await ctx.reply(
                    f"No records found for {userinfo.name}.", mention_author=False
                )
                return None

            futures = [self.utils.annotate_song(record) for record in records]
            records = await asyncio.gather(*futures)

            view = CompareView(ctx, userinfo, records)
            view.message = await ctx.reply(
                content=f"Top play for {userinfo.name}",
                embed=ScoreCardEmbed(view.items[view.page]),
                view=view,
                mention_author=False,
            )
            return None

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

        async with ctx.typing(), self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            await client.authenticate()
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

        async with ctx.typing(), self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            await client.authenticate()
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

    @commands.hybrid_command("top")
    async def top(
        self,
        ctx: Context,
        level: str,
        user: Optional[discord.User | discord.Member] = None,
    ):
        """View your best scores for a level."""

        if level[-1] == "+":
            numeric_level = int(level.zfill(3)[:-1])
        else:
            numeric_level = int(level[0:2])

        msg = "Invalid level."
        if level[-1] == "+" and numeric_level not in range(7, 15):
            raise commands.BadArgument(msg)
        if numeric_level not in range(1, 16):
            raise commands.BadArgument(msg)

        async with ctx.typing(), self.utils.chuninet(
            ctx if user is None else user.id
        ) as client:
            await client.authenticate()
            records = await client.music_record_by_folder(level=level)
            assert records is not None

            if len(records) == 0:
                return await ctx.reply(
                    f"No scores found for level {level}.", mention_author=False
                )

            tasks = [self.utils.annotate_song(score) for score in records]
            records = await asyncio.gather(*tasks)
            records.sort(key=lambda x: (x.play_rating, x.score), reverse=True)

            view = B30View(ctx, records, show_average=False)
            view.message = await ctx.reply(
                content=view.format_content(),
                embeds=view.format_page(view.items[: view.per_page]),
                view=view,
                mention_author=False,
            )
            return None


async def setup(bot: "ChuniBot"):
    await bot.add_cog(RecordsCog(bot))
