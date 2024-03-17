from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import func, select

from database.models import Alias, Song

if TYPE_CHECKING:
    from bot import ChuniBot


class AutocompletersCog(commands.Cog, name="Autocompleters"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot

    async def song_title_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        if len(current) < 3:
            return []

        condition = Alias.guild_id == -1
        if interaction.guild is not None:
            condition |= Alias.guild_id == interaction.guild.id

        song_query = select(Song.title, Song.title.label("alias")).where(Song.id < 8000)
        aliases_query = (
            select(
                Song.title,
                Alias.alias,
            )
            .join(Song)
            .where(condition)
        )

        subquery = song_query.union_all(aliases_query).subquery()

        sim_col = func.fuzz_qratio(func.lower(subquery.c.alias), current.lower()).label(
            "sim"
        )
        stmt = (
            select(
                subquery.c.title,
                func.max(sim_col),
            )
            .where(sim_col > 0.7)
            .group_by(subquery.c.title)
            .order_by(sim_col.desc())
            .limit(25)
        )

        async with self.bot.begin_db_session() as session:
            rows = (await session.execute(stmt)).scalars().all()

        return [app_commands.Choice(name=row, value=row) for row in rows]


async def setup(bot: "ChuniBot"):
    await bot.add_cog(AutocompletersCog(bot))
