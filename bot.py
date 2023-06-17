from pathlib import Path

from dotenv import dotenv_values

BOT_DIR = Path(__file__).absolute().parent
cfg = dotenv_values(BOT_DIR / ".env")


import asyncio
import logging
import logging.handlers
import sys
from typing import TYPE_CHECKING, Optional

import aiosqlite
import discord
from aiohttp import web
from discord.ext import commands
from discord.ext.commands import Bot

from utils.help import HelpCommand
from web import init_app

if TYPE_CHECKING:
    from aiohttp.web import Application


class ChuniBot(Bot):
    cfg: dict[str, str | None]
    db: aiosqlite.Connection
    app: Optional["Application"] = None
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def guild_specific_prefix(default: str):
    async def inner(bot: ChuniBot, msg: discord.Message) -> list[str]:
        when_mentioned = commands.when_mentioned(bot, msg)

        if msg.guild is None:
            return when_mentioned + [default]
        else:
            async with bot.db.execute(
                "SELECT prefix from guild_prefix WHERE guild_id = ?", (msg.guild.id,)
            ) as cursor:
                prefix = await cursor.fetchone()
            return when_mentioned + [(prefix[0] if prefix is not None else default)]

    return inner


async def startup():
    if (token := cfg.get("TOKEN")) is None:
        sys.exit(
            "[ERROR] Token not found, make sure 'TOKEN' is set in the '.env' file. Exiting."
        )

    logger = logging.getLogger("discord")
    logger.setLevel(logging.DEBUG)

    handler = logging.handlers.RotatingFileHandler(
        filename="discord.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    (intents := discord.Intents.default()).message_content = True
    bot = ChuniBot(
        command_prefix=guild_specific_prefix(cfg.get("DEFAULT_PREFIX", "c>")),  # type: ignore
        intents=intents,
        help_command=HelpCommand(),
    )

    await bot.load_extension("cogs.botutils")
    if cfg["DEV"] == "1":
        await bot.load_extension("cogs.hotreload")
        await bot.load_extension("jishaku")

    for file in (BOT_DIR / "cogs").glob("*.py"):
        if file.stem in ["hotreload", "botutils", "__init__"]:
            continue
        try:
            await bot.load_extension(f"cogs.{file.stem}")
            print(f"Loaded cogs.{file.stem}")
        except Exception as e:
            print(f"Failed to load extension cogs.{file.stem}")
            print(f"{type(e).__name__}: {e}")

    async with aiosqlite.connect(BOT_DIR / "database" / "database.sqlite3") as db:
        await db.enable_load_extension(True)
        await db.load_extension(str(BOT_DIR / "database" / "distlib"))
        await db.enable_load_extension(False)

        with (BOT_DIR / "database" / "schema.sql").open() as f:
            await db.executescript(f.read())
        await db.commit()

        bot.db = db
        bot.cfg = cfg

        port = cfg.get("LOGIN_ENDPOINT_PORT", "5730")
        if port is not None and port.isdigit() and int(port) > 0:
            bot.app = init_app(bot)
            asyncio.ensure_future(
                web._run_app(
                    bot.app,
                    port=int(port),
                    host="127.0.0.1",
                )
            )

        try:
            await bot.start(token)
        except discord.LoginFailure:
            sys.exit(
                "[ERROR] Token not found, make sure 'TOKEN' is set in the '.env' file. Exiting."
            )
        except discord.PrivilegedIntentsRequired:
            sys.exit(
                "[ERROR] Message Content Intent not enabled, go to 'https://discord.com/developers/applications' and enable the Message Content Intent. Exiting."
            )


if __name__ == "__main__":
    asyncio.run(startup())
