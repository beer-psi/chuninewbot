import asyncio
import io
from asyncio import TimeoutError, CancelledError
from random import randrange
from threading import Lock

import discord
from aiohttp import ClientSession
from discord.ext import commands
from discord.ext.commands import Context
from jarowinkler import jarowinkler_similarity
from PIL import Image

from api.consts import JACKET_BASE
from bot import ChuniBot
from cogs.botutils import UtilsCog


class GamingCog(commands.Cog, name="Games"):
    def __init__(self, bot: ChuniBot) -> None:
        self.bot = bot
        self.utils: UtilsCog = self.bot.get_cog("Utils")  # type: ignore

        self.session = ClientSession()

        self.current_sessions_lock = Lock()
        self.current_sessions: dict[int, asyncio.Task] = {}

    @commands.hybrid_command("guess")
    async def guess(self, ctx: Context):
        if ctx.channel.id in self.current_sessions:
            # await ctx.reply("There is already an ongoing session in this channel!")
            return
        
        with self.current_sessions_lock:
            self.current_sessions[ctx.channel.id] = asyncio.create_task(asyncio.sleep(0))

        async with ctx.typing():
            prefix = await self.utils.guild_prefix(ctx)

            async with self.bot.db.execute(
                'SELECT id, title, genre, artist, jacket FROM chunirec_songs WHERE genre != "WORLD\'S END" ORDER BY RANDOM() LIMIT 1'
            ) as cursor:
                (id, title, genre, artist, jacket) = await cursor.fetchone()  # type: ignore

            async with self.bot.db.execute(
                f"SELECT alias FROM aliases WHERE song_id = :id AND (guild_id = -1 OR guild_id = :guild_id)",
                {"id": id, "guild_id": ctx.guild.id if ctx.guild is not None else -1},
            ) as cursor:
                aliases = [alias for (alias,) in await cursor.fetchall()]
            aliases = [title] + aliases

            jacket_url = f"{JACKET_BASE}/{jacket}"
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

            await ctx.reply(
                embed=question_embed,
                file=discord.File(bytesio, "image.png"),
                mention_author=False,
            )

        answers = "\n".join(aliases)
        answer_embed = discord.Embed(
            description=(
                f"**Answer**: {answers}\n"
                "\n"
                f"**Artist**: {artist}\n"
                f"**Category**: {genre}"
            )
        )
        answer_embed.set_image(url="attachment://image.png")

        def check(m: discord.Message):
            return (
                m.channel == ctx.channel
                and max(
                    [
                        jarowinkler_similarity(m.content.lower(), alias.lower())
                        for alias in aliases
                    ]
                )
                >= 0.9
            )

        content = ""
        try:
            self.current_sessions[ctx.channel.id] = asyncio.create_task(self.bot.wait_for(
                "message", check=check, timeout=20
            ))
            msg = await self.current_sessions[ctx.channel.id]
            await msg.add_reaction("✅")

            content = f"{msg.author.mention} has the correct answer!"
        except CancelledError:
            content = "Skipped!"
        except TimeoutError:
            content = "Time's up!"
        finally:
            await ctx.send(
                content=content,
                embed=answer_embed,
                file=discord.File(io.BytesIO(jacket_bytes), "image.png"),
                mention_author=False,
            )

            with self.current_sessions_lock:
                del self.current_sessions[ctx.channel.id]
            return
    
    @commands.hybrid_command("skip")
    async def skip(self, ctx: Context):
        if ctx.channel.id not in self.current_sessions:
            await ctx.reply("There is no ongoing session in this channel!")
            return

        self.current_sessions[ctx.channel.id].cancel()
        return


async def setup(bot: ChuniBot) -> None:
    await bot.add_cog(GamingCog(bot))
