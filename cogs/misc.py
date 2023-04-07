from random import random
from typing import Optional
from urllib.parse import quote

import discord
from discord.ext import commands
from discord.ext.commands import Context

from api.enums import Difficulty
from bot import ChuniBot
from cogs.botutils import UtilsCog
from utils import format_level
from utils.rating_calculator import calculate_rating
from views.songlist import SonglistView


class MiscCog(commands.Cog, name="Miscellaneous"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = self.bot.get_cog("Utils")  # type: ignore

    @commands.hybrid_command("source", aliases=["src"])
    async def source(self, ctx: Context):
        reply = (
            "https://tenor.com/view/metal-gear-rising-metal-gear-rising-revengeance-senator-armstrong-revengeance-i-made-it-the-fuck-up-gif-25029602"
            if random() < 0.1
            else "<https://github.com/beerpiss/chuninewbot>"
        )

        await ctx.reply(reply, mention_author=False)

    @commands.hybrid_command("calculate", aliases=["calc"])
    async def calc(self, ctx: Context, score: int, chart_constant: float):
        """Calculate rating from score and chart constant."""

        if not 0 <= score <= 1010000:
            await ctx.reply(
                "Score must be between 0 and 1010000.", mention_author=False
            )
            return

        rating = calculate_rating(score, chart_constant)
        await ctx.reply(f"Calculation result: {rating:.2f}", mention_author=False)

    @commands.hybrid_command("find")
    async def find(self, ctx: Context, query: float):
        """Find charts by chart constant."""

        async with self.bot.db.execute(
            "SELECT song_id, difficulty FROM chunirec_charts WHERE const = ?", (query,)
        ) as cursor:
            charts = await cursor.fetchall()
        if not charts:
            await ctx.reply("No charts found.", mention_author=False)
            return

        # title and difficulty
        results: list[tuple[str, str]] = []
        for chart in charts:
            song_id = chart[0]
            async with self.bot.db.execute(
                "SELECT title from chunirec_songs WHERE id = ?", (song_id,)
            ) as cursor:
                title = await cursor.fetchone()
            if title is None:
                continue
            results.append((title[0], chart[1]))

        view = SonglistView(ctx, results)
        view.message = await ctx.reply(
            embed=view.format_songlist(view.items[: view.per_page]),
            view=view,
            mention_author=False,
        )

    @commands.hybrid_command("random")
    async def random(self, ctx: Context, level: str, count: int = 3):
        """Get random charts based on level."""

        async with ctx.typing():
            if count > 4 or count < 1:
                raise commands.BadArgument("Number of songs must be between 1 and 4.")

            try:
                query_level = float(level.replace("+", ".5"))
            except:
                raise commands.BadArgument("Invalid level provided.")

            async with self.bot.db.execute(
                "SELECT song_id, difficulty, level, const, maxcombo, is_const_unknown FROM chunirec_charts WHERE level = ? OR const = ? ORDER BY random() LIMIT ?",
                (query_level, query_level, count),
            ) as cursor:
                charts = await cursor.fetchall()
            if not charts:
                await ctx.reply("No charts found.", mention_author=False)
                return

            embeds: list[discord.Embed] = []
            for chart in charts:
                difficulty = Difficulty.from_short_form(chart[1])
                level = format_level(chart[2])
                async with self.bot.db.execute(
                    "SELECT title, genre, artist, jacket FROM chunirec_songs WHERE id = ?",
                    (chart[0],),
                ) as cursor:
                    song = await cursor.fetchone()
                if song is None:
                    continue

                embeds.append(
                    discord.Embed(
                        title=song[0],
                        description=song[2],
                        color=difficulty.color(),
                    )
                    .set_thumbnail(
                        url=f"https://new.chunithm-net.com/chuni-mobile/html/mobile/img/{song[3]}"
                    )
                    .add_field(name="Category", value=song[1])
                    .add_field(
                        name=str(difficulty),
                        value=f"[{level}{f' ({chart[3]})' if not chart[5] else ''}](https://www.youtube.com/results?search_query={quote(f'CHUNITHM {song[0]} {difficulty}')})",
                    )
                )
            await ctx.reply(embeds=embeds, mention_author=False)

    @commands.hybrid_command("prefix")
    @commands.guild_only()
    async def prefix(self, ctx: Context, new_prefix: Optional[str] = None):
        """Get or set the prefix for this server."""

        # discord.TextChannel should have an associated guild
        assert ctx.guild is not None

        if new_prefix is None:
            answer = self.bot.cfg.get("DEFAULT_PREFIX", "c>")
            async with self.bot.db.execute(
                "SELECT prefix FROM guild_prefix WHERE guild_id = ?", (ctx.guild.id,)
            ) as cursor:
                prefix = await cursor.fetchone()
            if prefix is not None:
                answer = prefix[0]
            await ctx.reply(f"Current prefix: `{answer}`", mention_author=False)
        else:
            permissions = ctx.author.guild_permissions  # type: ignore
            missing_permission = permissions.manage_guild != True
            if missing_permission:
                raise commands.MissingPermissions(["manage_guild"])

            await self.bot.db.execute(
                "INSERT INTO guild_prefix (guild_id, prefix) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET prefix = excluded.prefix",
                (ctx.guild.id, new_prefix),
            )
            await self.bot.db.commit()
            await ctx.reply(f"Prefix set to `{new_prefix}`", mention_author=False)


async def setup(bot: ChuniBot) -> None:
    await bot.add_cog(MiscCog(bot))
