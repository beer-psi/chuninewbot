from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import escape_markdown

from api.consts import JACKET_BASE
from bot import ChuniBot
from utils import (
    did_you_mean_text,
    format_level,
    yt_search_link,
    sdvxin_link,
    release_to_chunithm_version,
)

from .botutils import UtilsCog


class SearchCog(commands.Cog, name="Search"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = bot.get_cog("Utils")  # type: ignore

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

        async with self.bot.db.execute(
            "SELECT id FROM chunirec_songs WHERE title = ?", (song_title_or_alias,)
        ) as cursor:
            song = await cursor.fetchone()
        if song is None:
            async with self.bot.db.execute(
                "SELECT song_id FROM aliases WHERE lower(alias) = ? AND (guild_id = -1 OR guild_id = ?)",
                (song_title_or_alias.lower(), ctx.guild.id),
            ) as cursor:
                alias = await cursor.fetchone()
            if alias is None:
                await ctx.reply(
                    f"**{song_title_or_alias}** does not exist.", mention_author=False
                )
                return
            song_id = alias[0]
        else:
            song_id = song[0]

        async with self.bot.db.execute(
            "SELECT alias FROM aliases WHERE lower(alias) = ? AND (guild_id = -1 OR guild_id = ?)",
            (added_alias.lower(), ctx.guild.id),
        ) as cursor:
            alias = await cursor.fetchone()
        if alias is not None:
            await ctx.reply(f"**{added_alias}** already exists.", mention_author=False)
            return

        await self.bot.db.execute(
            "INSERT INTO aliases (alias, guild_id, song_id) VALUES (?, ?, ?)",
            (added_alias, ctx.guild.id, song_id),
        )
        await self.bot.db.commit()
        await ctx.reply(
            f"Added **{added_alias}** as an alias for **{song_title_or_alias}**.",
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

        async with self.bot.db.execute(
            "SELECT alias FROM aliases WHERE lower(alias) = ? AND guild_id = ?",
            (removed_alias.lower(), ctx.guild.id),
        ) as cursor:
            alias = await cursor.fetchone()
        if alias is None:
            await ctx.reply(
                f"**{removed_alias}** does not exist.", mention_author=False
            )
            return

        await self.bot.db.execute(
            "DELETE FROM aliases WHERE lower(alias) = ? AND guild_id = ?",
            (removed_alias.lower(), ctx.guild.id),
        )
        await self.bot.db.commit()
        await ctx.reply(f"Removed **{removed_alias}**.", mention_author=False)

    @commands.hybrid_command("info")
    async def info(self, ctx: Context, *, query: str):
        """Search for a song."""

        guild_id = ctx.guild.id if ctx.guild is not None else None
        result = await self.utils.find_song(query, guild_id=guild_id)

        if result.similarity < 0.9:
            return await ctx.reply(did_you_mean_text(result), mention_author=False)

        version = release_to_chunithm_version(result.release)

        embed = discord.Embed(
            title=result.title,
            description=(
                f"**Artist**: {result.artist}\n"
                f"**Category**: {result.genre}\n"
                f"**Version**: {version} ({result.release})\n"
                f"**BPM**: {result.bpm if result.bpm != 0 else 'Unknown'}\n"
            ),
            color=discord.Color.yellow(),
        ).set_thumbnail(url=f"{JACKET_BASE}/{result.jacket}")

        chart_level_desc = []
        async with self.bot.db.execute(
            "SELECT charts.difficulty, level, const, sdvxin.id as sdvxin_id "
            "FROM chunirec_charts charts "
            "LEFT JOIN sdvxin ON charts.song_id = sdvxin.song_id AND charts.difficulty = sdvxin.difficulty "
            "WHERE charts.song_id = ? "
            "ORDER BY charts.id ASC",
            (result.id,),
        ) as cursor:
            charts = await cursor.fetchall()

        for chart in charts:
            difficulty, level, const, sdvxin_id = chart
            url = (
                sdvxin_link(sdvxin_id, difficulty)
                if sdvxin_id is not None
                else yt_search_link(result.title, difficulty)
            )
            desc = f"[{difficulty[0]}]({url}) {format_level(level)}"
            if const != 0:
                desc += f" ({const:.1f})"
            chart_level_desc.append(desc)

        if len(chart_level_desc) > 0:
            # embed.description is already set above
            embed.description += "\n" "**Level**:\n"  # type: ignore
            embed.description += " / ".join(chart_level_desc)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: ChuniBot):
    await bot.add_cog(SearchCog(bot))
