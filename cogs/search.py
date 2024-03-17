from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Sequence

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import escape_markdown as emd
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from chunithm_net.entities.enums import Difficulty
from database.models import Alias, Chart, Song
from utils import (
    TOKYO_TZ,
    did_you_mean_text,
    get_jacket_url,
    release_to_chunithm_version,
    shlex_split,
    yt_search_link,
)
from utils.config import config
from utils.views.songlist import SonglistView

if TYPE_CHECKING:
    from bot import ChuniBot
    from cogs.autocompleters import AutocompletersCog
    from cogs.botutils import UtilsCog


class SearchCog(commands.Cog, name="Search"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot
        self.utils: "UtilsCog" = bot.get_cog("Utils")  # type: ignore[reportGeneralTypeIssues]
        self.autocompleters: "AutocompletersCog" = bot.get_cog("Autocompleters")  # type: ignore[reportGeneralTypeIssues]

    @commands.hybrid_command("find")
    async def find(self, ctx: Context, level: str):
        """Find charts by level or chart constant.

        Parameters
        ----------
        query: float
            Chart constant to search for.
        """

        stmt = (
            select(Chart)
            .options(joinedload(Chart.sdvxin_chart_view), joinedload(Chart.song))
            .join(Song, Chart.song)
            .order_by(Song.title)
        )

        try:
            if "." in level:
                query_level = float(level)
                stmt = stmt.where(Chart.const == query_level)
            else:
                stmt = stmt.where(Chart.level == level)
        except ValueError:
            msg = "Please enter a valid level or chart constant."
            raise commands.BadArgument(msg) from None

        async with ctx.typing(), self.bot.begin_db_session() as session:
            charts: Sequence[Chart] = (await session.execute(stmt)).scalars().all()

            if len(charts) == 0:
                await ctx.reply("No charts found.", mention_author=False)
                return

            view = SonglistView(ctx, charts)
            view.message = await ctx.reply(
                embed=view.format_songlist(view.items[: view.per_page]),
                view=view,
                mention_author=False,
            )

    @commands.hybrid_command("addalias")
    async def addalias(
        self,
        ctx: Context,
        song_title_or_alias: str,
        added_alias: str,
        *,
        global_alias: bool = False,
    ):
        """Manually add a song alias for this server.

        Aliases are case-insensitive.

        Parameters
        ----------
        song_title_or_alias: str
            The title (or an existing alias) of the song.
        added_alias: str
            The alias to add.
        global_alias: bool
            Whether to apply the alias globally. Only a few users can do this.

        Examples
        --------
        addalias Titania tritania
        addalias "祈 -我ら神祖と共に歩む者なり-" prayer
        """

        # this command is guild-only
        if not global_alias and ctx.guild is None:
            raise commands.NoPrivateMessage

        if global_alias and ctx.author.id not in config.bot.alias_managers:
            msg = "You are not allowed to add global aliases."
            raise commands.CheckFailure(msg)

        async with ctx.typing(), self.bot.begin_db_session() as session, session.begin():
            stmt = (
                select(Song)
                .where(func.lower(Song.title) == func.lower(added_alias))
                .limit(1)
            )
            song = (await session.execute(stmt)).scalar_one_or_none()

            if song is not None:
                msg = f"**{emd(added_alias)}** is already a song title."
                raise commands.BadArgument(msg)

            if global_alias:
                stmt = (
                    select(Alias)
                    .where(func.lower(Alias.alias) == func.lower(added_alias))
                    .options(joinedload(Alias.song))
                )
                aliases = (await session.execute(stmt)).scalars().all()

                if len(aliases) > 0 and aliases[0].guild_id == -1:
                    msg = f"**{emd(added_alias)}** already exists (global alias for **{emd(aliases[0].song.title)}**)"
                    raise commands.BadArgument(msg)

                if len(aliases) > 0 and aliases[0].guild_id != -1:
                    aliases[0].guild_id = -1
                    aliases[0].owner_id = None
                    await session.merge(aliases[0])

                    for x in aliases[1:]:
                        await session.delete(x)

                    return await ctx.reply(
                        f"**{emd(added_alias)}** already exists as a guild-only alias. Promoting to global alias.",
                        mention_author=False,
                    )
            else:
                stmt = (
                    select(Alias)
                    .where(
                        (func.lower(Alias.alias) == func.lower(added_alias))
                        & ((Alias.guild_id == -1) | (Alias.guild_id == ctx.guild.id))
                    )
                    .options(joinedload(Alias.song))
                )
                alias = (await session.execute(stmt)).scalar_one_or_none()

                if alias is not None:
                    msg = (
                        f"**{emd(added_alias)}** already exists "
                        f"({'global ' if alias.guild_id == -1 else ''}alias for **{emd(alias.song.title)}**)."
                    )
                    raise commands.BadArgument(msg)

            stmt = select(Song).where(
                # Limit to non-WE entries. WE entries are redirected to
                # their non-WE respectives when song-searching anyways.
                (func.lower(Song.title) == func.lower(song_title_or_alias))
                & (Song.id < 8000)
            )
            song = (await session.execute(stmt)).scalar_one_or_none()

            if song is None:
                condition = func.lower(Alias.alias) == func.lower(song_title_or_alias)

                if not global_alias:
                    condition = condition & (
                        (Alias.guild_id == -1) | (Alias.guild_id == ctx.guild.id)
                    )

                stmt = select(Alias).where(condition).options(joinedload(Alias.song))
                alias = (await session.execute(stmt)).scalar_one_or_none()

                if alias is None:
                    msg = f"**{emd(song_title_or_alias)}** does not exist."
                    raise commands.BadArgument(msg)

                song = alias.song

            session.add(
                Alias(
                    alias=added_alias,
                    guild_id=-1 if global_alias else ctx.guild.id,
                    song_id=song.id,
                    owner_id=None if global_alias else ctx.author.id,
                )
            )

        await self.utils._reload_alias_cache()

        alias = "an alias"
        if global_alias:
            alias = "a global alias"

        await ctx.reply(
            f"Added **{emd(added_alias)}** as {alias} for **{emd(song_title_or_alias)}**.",
            mention_author=False,
        )
        return None

    @commands.hybrid_command("removealias")
    async def removealias(self, ctx: Context, *, removed_alias: str):
        """Remove an alias for this server.

        Parameters
        ----------
        alias: str
            The alias to remove.
        """

        is_alias_manager = ctx.author.id in config.bot.alias_managers

        if not is_alias_manager and ctx.guild is None:
            raise commands.NoPrivateMessage

        async with ctx.typing(), self.bot.begin_db_session() as session, session.begin():
            condition = func.lower(Alias.alias) == func.lower(removed_alias)

            if not is_alias_manager:
                condition = condition & (Alias.guild_id == ctx.guild.id)

            stmt = select(Alias).where(condition)
            alias = (await session.execute(stmt)).scalar_one_or_none()

            if alias is None:
                msg = f"**{emd(removed_alias)}** does not exist"

                if not is_alias_manager:
                    msg += " or you don't have permissions to remove it"

                msg += "."

                raise commands.BadArgument(msg)

            if (
                not is_alias_manager
                and alias.guild_id != -1
                and alias.owner_id != ctx.author.id
                and not (
                    isinstance(ctx.author, discord.Member)
                    and ctx.author.guild_permissions.administrator
                )
            ):
                msg = "You cannot delete an alias that you didn't add yourself."
                raise commands.CheckFailure(msg)

            await session.delete(alias)

        await self.utils._reload_alias_cache()
        await ctx.reply(
            f"Removed {'global ' if alias.guild_id == -1 else ''}alias **{emd(removed_alias)}**.",
            mention_author=False,
        )

    @commands.hybrid_command("listalias")
    async def listalias(self, ctx: Context, *, query: str):
        """List aliases for a given song

        Parameters
        ----------
        query: str
            The song to get aliases for. You don't have to be exact; this works
            the same way as `c>info`.
        """
        guild_id = ctx.guild.id if ctx.guild is not None else None
        song, alias, similarity = await self.utils.find_song(query, guild_id=guild_id)

        if song is None or similarity < 90:
            return await ctx.reply(did_you_mean_text(song, alias), mention_author=False)

        async with self.bot.begin_db_session() as session:
            stmt = select(Alias).where(Alias.song_id == song.id)
            aliases = (await session.execute(stmt)).scalars().all()

        embed = discord.Embed(
            title=f"Aliases for {song.title}",
            color=discord.Color.yellow(),
        )
        embed.description = ""
        global_aliases = [x.alias for x in aliases if x.guild_id == -1]

        if len(global_aliases) > 0:
            embed.description += (
                "**Global aliases:**\n"
                f"{', '.join([x.alias for x in aliases if x.guild_id == -1])}"
            )

        if ctx.guild is not None:
            local_aliases = [x.alias for x in aliases if x.guild_id == ctx.guild.id]

            if len(local_aliases) > 0:
                embed.description += (
                    "\n\n"
                    "**Local aliases:**\n"
                    f"{', '.join([x.alias for x in aliases if x.guild_id == ctx.guild.id])}"
                )

        embed.description = embed.description.strip()

        await ctx.reply(embed=embed, mention_author=False)

        return None

    async def song_title_autocomplete(
        self,
        interaction: "discord.Interaction[ChuniBot]",
        current: str,
    ):
        return await self.autocompleters.song_title_autocomplete(interaction, current)

    @app_commands.command(name="info", description="Search for a song.")
    @app_commands.describe(
        query="Song title to search for. You don't have to be exact; try things out!",
        worlds_end="Whether to search for WORLD'S END songs instead of standard songs.",
        detailed="Display detailed chart information (note counts and designer name)",
    )
    @app_commands.autocomplete(query=song_title_autocomplete)
    async def info_slash(
        self,
        interaction: "discord.Interaction[ChuniBot]",
        query: str,
        *,
        worlds_end: bool = False,
        detailed: bool = False,
    ):
        if worlds_end:
            query += " -we"
        if detailed:
            query += " -d"

        ctx = await Context.from_interaction(interaction)
        return await self.info(ctx, query=query)

    @commands.command("info")
    async def info(self, ctx: Context, *, query: str):
        """Search for a song.

        **Parameters:**
        `query`: Song title to search for. You don't have to be exact; try things out!
        `-we`: Search for WORLD'S END songs instead of normal songs.
        `-d`: Show detailed info, such as note counts and charter.
        """
        args = SimpleNamespace(worlds_end=False, detailed=False, query=[])

        argv = shlex_split(query)
        for arg in argv:
            if arg in ["-we", "--worlds-end"]:
                args.worlds_end = True
            elif arg in ["-d", "--detailed"]:
                args.detailed = True
            else:
                args.query.append(arg)

        query = " ".join(args.query)

        async with ctx.typing(), self.bot.begin_db_session() as session:
            guild_id = ctx.guild.id if ctx.guild is not None else None
            song, alias, similarity = await self.utils.find_song(
                query, guild_id=guild_id, worlds_end=args.worlds_end
            )

            if song is None or similarity < 90:
                return await ctx.reply(
                    did_you_mean_text(song, alias), mention_author=False
                )

            release = datetime.strptime(song.release, "%Y-%m-%d").astimezone(TOKYO_TZ)
            version = release_to_chunithm_version(release)

            embed = discord.Embed(
                title=song.title,
                description=(
                    f"**Artist**: {emd(song.artist)}\n"
                    f"**Category**: {song.genre}\n"
                    f"**Version**: {version} ({song.release})\n"
                    f"**BPM**: {song.bpm if song.bpm is not None else 'Unknown'}\n"
                ),
                color=discord.Color.yellow(),
            ).set_thumbnail(url=get_jacket_url(song))

            if not song.available:
                if song.removed:
                    embed.description = (
                        f"**This song is removed.**\n\n{embed.description}"
                    )
                else:
                    embed.description = f"**This song is not available in CHUNITHM International.**\n\n{embed.description}"

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
                    chart.sdvxin_chart_view.url
                    if chart.sdvxin_chart_view is not None
                    else yt_search_link(song.title, chart.difficulty)
                )
                worlds_end = "WORLD'S END"

                if args.detailed:
                    difficulty = Difficulty.from_short_form(chart.difficulty)

                    link_text = f"Lv.{chart.level}"
                    if chart.const is not None:
                        link_text += f" ({chart.const:.1f})"

                    desc = f"{difficulty.emoji()} [{link_text}]({url})"
                else:
                    desc = f"[{worlds_end if args.worlds_end else chart.difficulty[0]}]({url}) {chart.level}"
                    if chart.const is not None:
                        desc += f" ({chart.const:.1f})"

                if args.detailed and chart.charter is not None:
                    desc += f" Designer: {emd(chart.charter)}"

                if args.detailed:
                    maxcombo = chart.maxcombo or "-"
                    tap = chart.tap or "-"
                    hold = chart.hold or "-"
                    slide = chart.slide or "-"
                    air = chart.air or "-"
                    flick = chart.flick or "-"
                    desc += (
                        f"\n**{maxcombo}** / {tap} / {hold} / {slide} / {air} / {flick}"
                    )
                chart_level_desc.append(desc)

            if len(chart_level_desc) > 0:
                # embed.description is already set above
                embed.description += "\n**Level**:\n"  # type: ignore[reportGeneralTypeIssues]
                if args.detailed:
                    embed.description += (
                        "**CHAIN** / TAP / HOLD / SLIDE / AIR / FLICK\n\n"
                    )
                    embed.description += "\n".join(chart_level_desc)
                else:
                    embed.description += " / ".join(chart_level_desc)
            await ctx.reply(embed=embed, mention_author=False)
            return None


async def setup(bot: "ChuniBot"):
    await bot.add_cog(SearchCog(bot))
