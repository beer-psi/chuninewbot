from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import escape_markdown as emd
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.consts import JACKET_BASE
from database.models import Alias, Chart, Song
from utils import (
    did_you_mean_text,
    format_level,
    release_to_chunithm_version,
    sdvxin_link,
    yt_search_link,
)

if TYPE_CHECKING:
    from bot import ChuniBot
    from cogs.botutils import UtilsCog


class SearchCog(commands.Cog, name="Search"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot
        self.utils: "UtilsCog" = bot.get_cog("Utils")  # type: ignore

    @commands.hybrid_command("addalias")
    @commands.guild_only()
    async def addalias(self, ctx: Context, song_title_or_alias: str, added_alias: str):
        """Manually add a song alias for this server.

        Aliases are case-insensitive.

        Parameters
        ----------
        song_title_or_alias: str
            The title (or an existing alias) of the song.
        added_alias: str
            The alias to add.

        Examples
        --------
        addalias Titania tritania
        addalias "祈 -我ら神祖と共に歩む者なり-" prayer
        """

        # this command is guild-only
        assert ctx.guild is not None

        added_alias_lower = added_alias.strip().lower()
        song_title_or_alias_lower = song_title_or_alias.strip().lower()

        async with AsyncSession(self.bot.engine) as session, session.begin():
            stmt = select(Song).where(func.lower(Song.title) == added_alias_lower)
            song = (await session.execute(stmt)).scalar_one_or_none()
            if song is not None:
                return await ctx.reply(
                    f"**{added_alias}** is already a song title.", mention_author=False
                )

            stmt = select(Alias).where(
                (func.lower(Alias.alias) == added_alias_lower)
                & ((Alias.guild_id == -1) | (Alias.guild_id == ctx.guild.id))
            )
            alias = (await session.execute(stmt)).scalar_one_or_none()
            if alias is not None:
                return await ctx.reply(
                    f"**{added_alias}** already exists.", mention_author=False
                )

            stmt = select(Song).where(
                func.lower(Song.title) == song_title_or_alias_lower
            )
            song = (await session.execute(stmt)).scalar_one_or_none()

            if song is None:
                stmt = select(Alias).where(
                    (func.lower(Alias.alias) == song_title_or_alias_lower)
                    & ((Alias.guild_id == -1) | (Alias.guild_id == ctx.guild.id))
                )
                alias = (await session.execute(stmt)).scalar_one_or_none()
                if alias is None:
                    return await ctx.reply(
                        f"**{song_title_or_alias}** does not exist.",
                        mention_author=False,
                    )
                song = alias.song

            session.add(
                Alias(alias=added_alias, guild_id=ctx.guild.id, song_id=song.id)
            )

        await ctx.reply(
            f"Added **{emd(added_alias)}** as an alias for **{emd(song_title_or_alias)}**.",
            mention_author=False,
        )

    @commands.hybrid_command("removealias")
    @commands.guild_only()
    async def removealias(self, ctx: Context, removed_alias: str):
        """Remove an alias for this server.

        Parameters
        ----------
        alias: str
            The alias to remove.
        """

        # this command is guild-only
        assert ctx.guild is not None

        async with AsyncSession(self.bot.engine) as session, session.begin():
            stmt = select(Alias).where(
                (func.lower(Alias.alias) == removed_alias.lower())
                & (Alias.guild_id == ctx.guild.id)
            )
            alias = (await session.execute(stmt)).scalar_one_or_none()

            if alias is None:
                return await ctx.reply(
                    f"**{removed_alias}** does not exist.", mention_author=False
                )

            await session.delete(alias)

        await ctx.reply(f"Removed **{emd(removed_alias)}**.", mention_author=False)

    @commands.hybrid_command("info")
    async def info(self, ctx: Context, *, query: str):
        """Search for a song.

        Parameters
        ----------
        query: str
            The song title or alias to search for.
        """

        guild_id = ctx.guild.id if ctx.guild is not None else None
        song, alias, similarity = await self.utils.find_song(query, guild_id=guild_id)

        if similarity < 0.9:
            return await ctx.reply(did_you_mean_text(song, alias), mention_author=False)

        release = datetime.strptime(song.release, "%Y-%m-%d")
        version = release_to_chunithm_version(release)

        embed = discord.Embed(
            title=song.title,
            description=(
                f"**Artist**: {emd(song.artist)}\n"
                f"**Category**: {song.genre}\n"
                f"**Version**: {version} ({song.release})\n"
                f"**BPM**: {song.bpm if song.bpm != 0 else 'Unknown'}\n"
            ),
            color=discord.Color.yellow(),
        ).set_thumbnail(url=f"{JACKET_BASE}/{song.jacket}")

        async with AsyncSession(self.bot.engine) as session:
            stmt = (
                select(Chart)
                .where(Chart.song_id == song.id)
                .order_by(Chart.id)
                .options(joinedload(Chart.sdvxin_chart_view))
            )
            charts = (await session.execute(stmt)).scalars().all()

            chart_level_desc = []

            for chart in charts:
                url = (
                    sdvxin_link(chart.sdvxin_chart_view.id, chart.difficulty)
                    if chart.sdvxin_chart_view is not None
                    else yt_search_link(song.title, chart.difficulty)
                )
                desc = f"[{chart.difficulty[0]}]({url}) {format_level(chart.level)}"
                if chart.const != 0:
                    desc += f" ({chart.const:.1f})"
                chart_level_desc.append(desc)

        if len(chart_level_desc) > 0:
            # embed.description is already set above
            embed.description += "\n" "**Level**:\n"  # type: ignore
            embed.description += " / ".join(chart_level_desc)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: "ChuniBot"):
    await bot.add_cog(SearchCog(bot))
