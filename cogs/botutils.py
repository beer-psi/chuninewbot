from datetime import time, timezone
from math import floor

from async_lru import alru_cache
from discord.ext import commands, tasks
from discord.ext.commands import Context

from api.record import MusicRecord, DetailedRecentRecord
from bot import ChuniBot
from update_db import update_db
from utils.rating_calculator import calculate_rating


class UtilsCog(commands.Cog, name="Utils"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot

    async def login_check(self, ctx: Context) -> str | None:
        clal = await self.fetch_cookie(ctx.author.id)
        if clal is None:
            await ctx.send(
                "You are not logged in. Please use `!login <cookie>` in DMs to log in."
            )
            return
        return clal

    @alru_cache()
    async def fetch_cookie(self, id: int) -> str | None:
        cursor = await self.bot.db.execute(
            "SELECT cookie FROM cookies WHERE discord_id = ?", (id,)
        )
        clal = await cursor.fetchone()
        if clal is None:
            return None

        return clal[0]

    async def annotate_song(self, song: MusicRecord):
        cursor = await self.bot.db.execute(
            "SELECT id FROM chunirec_songs WHERE title = ? AND jacket = ?",
            (song.title, song.jacket.split("/")[-1]),
        )
        song_data = await cursor.fetchone()
        if song_data is None:
            return
        id = song_data[0]

        cursor = await self.bot.db.execute(
            "SELECT level, const, maxcombo, is_const_unknown FROM chunirec_charts WHERE song_id = ? AND difficulty = ?",
            (id, song.difficulty.short_form()),
        )
        chart_data = await cursor.fetchone()
        if chart_data is None:
            return
        song.internal_level = chart_data[1]

        level = chart_data[0]
        song.level = str(floor(level)) + ("+" if level * 10 % 10 >= 5 else "")
        song.unknown_const = bool(chart_data[3])

        if not song.unknown_const:
            song.play_rating = calculate_rating(song.score, song.internal_level)

        if isinstance(song, DetailedRecentRecord) and chart_data[2] != 0:
            song.full_combo = chart_data[2]

    # maimai and CHUNITHM NET goes under maintenance every day at 2:00 AM JST, so we update the DB then
    @tasks.loop(time=time(hour=17, tzinfo=timezone.utc))
    async def update_chunirec_db(self):
        # Disable all commands while updating the DB
        for cmd in self.bot.walk_commands():
            cmd.enabled = False
        await update_db(self.bot.db)
        # Re-enable all commands
        for cmd in self.bot.walk_commands():
            cmd.enabled = True


async def setup(bot: ChuniBot):
    await bot.add_cog(UtilsCog(bot))
