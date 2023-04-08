from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import escape_markdown

from bot import ChuniBot
from utils import format_level, yt_search_link, sdvxin_link, release_to_chunithm_version

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
                "SELECT song_id FROM aliases WHERE lower(alias) = ? AND (guild_id IS NULL OR guild_id = ?)",
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
            "SELECT alias FROM aliases WHERE lower(alias) = ? AND (guild_id IS NULL OR guild_id = ?)",
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

        guild_id = ctx.guild.id if ctx.guild is not None else 0

        async with self.bot.db.execute(
            "SELECT jwsim(lower(title), ?) AS similarity, id, title, genre, artist, release, bpm, jacket "
            "FROM chunirec_songs "
            "ORDER BY similarity DESC "
            "LIMIT 1",
            (query.lower(),),
        ) as cursor:
            song = await cursor.fetchone()
        assert song is not None

        similarity, id, title, genre, artist, release, bpm, jacket = song
        if similarity < 0.9:
            async with self.bot.db.execute(
                "SELECT jwsim(lower(aliases.alias), ?) AS similarity, id, title, genre, artist, release, bpm, jacket, aliases.alias "
                "FROM chunirec_songs "
                "LEFT JOIN aliases ON aliases.song_id = chunirec_songs.id "
                "WHERE aliases.guild_id IS NULL OR aliases.guild_id = ? "
                "ORDER BY similarity DESC "
                "LIMIT 1",
                (query.lower(), guild_id),
            ) as cursor:
                song = await cursor.fetchone()
            assert song is not None
            similarity, id, title, genre, artist, release, bpm, jacket, alias = song
            if similarity < 0.9:
                await ctx.reply(
                    f"No songs found. Did you mean **{escape_markdown(alias)}** (for **{escape_markdown(title)}**)?",
                    mention_author=False,
                )
                return

        version = release_to_chunithm_version(datetime.strptime(release, "%Y-%m-%d"))

        embed = discord.Embed(
            title=title,
            description=(
                f"**Artist**: {artist}\n"
                f"**Category**: {genre}\n"
                f"**Version**: {version} ({release})\n"
                f"**BPM**: {bpm if bpm != 0 else 'Unknown'}\n"
            ),
            color=discord.Color.yellow(),
        ).set_thumbnail(
            url=f"https://new.chunithm-net.com/chuni-mobile/html/mobile/img/{jacket}"
        )

        chart_level_desc = []
        async with self.bot.db.execute(
            "SELECT charts.difficulty, level, const, sdvxin.id as sdvxin_id "
            "FROM chunirec_charts charts "
            "LEFT JOIN sdvxin ON charts.song_id = sdvxin.song_id AND charts.difficulty = sdvxin.difficulty "
            "WHERE charts.song_id = ? "
            "ORDER BY charts.id ASC",
            (id,),
        ) as cursor:
            charts = await cursor.fetchall()

        for chart in charts:
            difficulty, level, const, sdvxin_id = chart
            url = (
                sdvxin_link(sdvxin_id, difficulty)
                if sdvxin_id is not None
                else yt_search_link(title, difficulty)
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
