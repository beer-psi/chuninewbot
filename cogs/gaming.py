import asyncio
import io
from asyncio import CancelledError, TimeoutError
from random import randrange
from threading import Lock
from types import SimpleNamespace
from typing import TYPE_CHECKING

import discord
from aiohttp import ClientSession
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.context import DeferTyping
from jarowinkler import jaro_similarity
from PIL import Image
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from chunithm_net.consts import JACKET_BASE
from database.models import Alias, GuessScore, Song

if TYPE_CHECKING:
    from bot import ChuniBot
    from cogs.botutils import UtilsCog


_current_sessions_lock = Lock()
_current_sessions: dict[int, asyncio.Task] = {}


class SkipButtonView(discord.ui.View):
    task: asyncio.Task
    message: discord.Message

    def __init__(self):
        super().__init__(timeout=20)

    async def on_timeout(self):
        self.clear_items()
        await self.message.edit(view=self)

    @discord.ui.button(label="⏩", style=discord.ButtonStyle.danger)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.on_timeout()
        self.task.cancel()


class NextGameButtonView(discord.ui.View):
    def __init__(self, cog: "GamingCog"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="New game", style=discord.ButtonStyle.green, custom_id="new_guess_game"
    )
    async def new_game(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if (
            interaction.channel_id in _current_sessions
            or interaction.channel is None
            or isinstance(interaction.channel, discord.ForumChannel)
            or isinstance(interaction.channel, discord.CategoryChannel)
        ):
            return await interaction.response.defer()

        cursed_context = SimpleNamespace()

        # The class only calls .defer, which interaction.response also has.
        cursed_context.typing = lambda: DeferTyping(interaction.response, ephemeral=True)  # type: ignore

        cursed_context.guild = interaction.guild
        cursed_context.channel = interaction.channel
        cursed_context.reply = interaction.channel.send
        cursed_context.send = interaction.channel.send

        # This has all the functions that guess() needs.
        await self.cog.guess(cursed_context)  # type: ignore


class GamingCog(commands.Cog, name="Games"):
    def __init__(self, bot: "ChuniBot") -> None:
        self.bot = bot
        self.utils: "UtilsCog" = self.bot.get_cog("Utils")  # type: ignore

        self.session = ClientSession()

    @commands.group("guess", invoke_without_command=True)
    async def guess(self, ctx: Context, mode: str = "lenient"):
        if ctx.channel.id in _current_sessions:
            # await ctx.reply("There is already an ongoing session in this channel!")
            return

        with _current_sessions_lock:
            _current_sessions[ctx.channel.id] = asyncio.create_task(asyncio.sleep(0))

        async with ctx.typing(), AsyncSession(self.bot.engine) as session:
            prefix = await self.utils.guild_prefix(ctx)

            stmt = (
                select(Song)
                .where(Song.genre != "WORLD'S END")
                .order_by(text("RANDOM()"))
                .limit(1)
            )
            song = (await session.execute(stmt)).scalar_one()

            stmt = select(Alias).where(
                (Alias.song_id == song.id)
                & (
                    (Alias.guild_id == -1)
                    | (
                        Alias.guild_id
                        == (ctx.guild.id if ctx.guild is not None else -1)
                    )
                )
            )
            aliases = [song.title] + [
                alias.alias for alias in (await session.execute(stmt)).scalars()
            ]

            jacket_url = f"{JACKET_BASE}/{song.jacket}"
            async with self.session.get(jacket_url) as resp:
                jacket_bytes = await resp.read()
                img = Image.open(io.BytesIO(jacket_bytes))

            x = randrange(0, img.width - 90)
            y = randrange(0, img.height - 90)

            img = img.crop((x, y, x + 90, y + 90))

            bytesio = io.BytesIO()
            img.save(bytesio, format="PNG")
            bytesio.seek(0)

            question_embed = discord.Embed(
                title="Guess the song!",
                description=f"You have 20 seconds to guess the song.\nUse `{prefix}skip` to skip.",
            )
            question_embed.set_image(url="attachment://image.png")

            view = SkipButtonView()
            view.message = await ctx.reply(
                embed=question_embed,
                file=discord.File(bytesio, "image.png"),
                mention_author=False,
                view=view,
            )

        def check(m: discord.Message):
            if mode == "strict":
                return m.channel == ctx.channel and m.content in aliases
            else:
                return (
                    m.channel == ctx.channel
                    and max(
                        [
                            jaro_similarity(m.content.lower(), alias.lower())
                            for alias in aliases
                        ]
                    )
                    >= 0.9
                )

        content = ""
        try:
            view.task = _current_sessions[ctx.channel.id] = asyncio.create_task(
                self.bot.wait_for("message", check=check, timeout=20)
            )
            msg = await _current_sessions[ctx.channel.id]
            await self._increment_score(msg.author.id)
            await msg.add_reaction("✅")

            content = f"{msg.author.mention} has the correct answer!"
        except CancelledError:
            content = "Skipped!"
        except TimeoutError:
            content = "Time's up!"
        finally:
            answers = "\n".join(aliases)
            answer_embed = discord.Embed(
                description=(
                    f"**Answer**: {answers}\n"
                    "\n"
                    f"**Artist**: {song.artist}\n"
                    f"**Category**: {song.genre}"
                )
            )
            answer_embed.set_image(url=jacket_url)

            await ctx.send(
                content=content,
                embed=answer_embed,
                mention_author=False,
                view=NextGameButtonView(self),
            )

            with _current_sessions_lock:
                del _current_sessions[ctx.channel.id]
            return

    @commands.hybrid_command("skip")
    async def skip(self, ctx: Context):
        if ctx.channel.id not in _current_sessions:
            await ctx.reply("There is no ongoing session in this channel!")
            return

        _current_sessions[ctx.channel.id].cancel()
        return

    @guess.command("leaderboard")
    async def guess_leaderboard(self, ctx: Context):
        async with AsyncSession(self.bot.engine) as session:
            stmt = select(GuessScore).order_by(GuessScore.score.desc()).limit(10)
            scores = (await session.execute(stmt)).scalars()

        embed = discord.Embed(title="Guess Leaderboard")
        description = ""
        for idx, score in enumerate(scores):
            description += f"\u200B{idx + 1}. <@{score.discord_id}>: {score.score}\n"
        embed.description = description
        await ctx.reply(embed=embed, mention_author=False)

    @guess.command("reset", hidden=True)
    @commands.is_owner()
    async def guess_reset(self, ctx: Context):
        """Resets the c>guess leaderboard"""

        async with AsyncSession(self.bot.engine) as session, session.begin():
            await session.execute(delete(GuessScore))

        await ctx.message.add_reaction("✅")

    async def _increment_score(self, discord_id: int):
        async with AsyncSession(self.bot.engine) as session, session.begin():
            stmt = select(GuessScore).where(GuessScore.discord_id == discord_id)
            score = (await session.execute(stmt)).scalar_one_or_none()

            if score is None:
                score = GuessScore(discord_id=discord_id, score=1)
                session.add(score)
            else:
                score.score += 1
                await session.merge(score)


async def setup(bot: "ChuniBot") -> None:
    cog = GamingCog(bot)
    await bot.add_cog(cog)
    bot.add_view(NextGameButtonView(cog))
