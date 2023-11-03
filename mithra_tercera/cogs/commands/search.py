from typing import TYPE_CHECKING, Self

from discord.ext import commands
from discord.ext.commands import Context

from mithra_tercera.db.services import SongService
from mithra_tercera.embeds.song_card import SongCardEmbed

if TYPE_CHECKING:
    from mithra_tercera import MithraTercera


class SearchCog(commands.Cog, name="Search"):
    def __init__(self: Self, bot: "MithraTercera") -> None:
        self.bot = bot

    @commands.command("info")
    async def info(self: Self, ctx: Context, *, query: str) -> None:
        guild_id = ctx.guild.id if ctx.guild else None

        # Searching in database is absolutely abysmal.
        # We're also trying to be database-agnostic.
        # Searching in-memory is fine. I think.
        song = await SongService.search_song_by_title(query, guild_id=guild_id)
        if song is None:
            await ctx.reply("No results found.", mention_author=False)
            return

        await ctx.reply(embed=SongCardEmbed(song), mention_author=False)


async def setup(bot: "MithraTercera") -> None:
    await bot.add_cog(SearchCog(bot))
