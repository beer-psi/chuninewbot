import asyncio
import logging
import logging.handlers
import sys
from configparser import ConfigParser
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, ClassVar, Optional

import discord
import sqlalchemy.event
from aiohttp import web
from discord.ext import commands
from discord.ext.commands import Bot, errors
from jarowinkler import jarowinkler_similarity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database.models import Base, Prefix
from utils.help import HelpCommand
from web import init_app

if TYPE_CHECKING:
    from aiohttp.web import Application


BOT_DIR = Path(__file__).parent
cfg = ConfigParser()
cfg.read(BOT_DIR / "bot.ini")


class ChuniBot(Bot):
    cfg: ConfigParser
    dev: bool = False

    engine: AsyncEngine
    begin_db_session: async_sessionmaker[AsyncSession]

    launch_time: float
    app: Optional["Application"] = None

    prefixes: dict[int, str]

    # key: user discord ID
    # value: userId, _t cookies from CHUNITHM-NET
    sessions: ClassVar[dict[int, tuple[str | None, str | None]]] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        connection_string = cfg["bot"].get(
            "db_connection_string",
            fallback=f"sqlite+aiosqlite:///{BOT_DIR / 'database' / 'database.sqlite3'}",
        )
        self.engine = create_async_engine(connection_string)
        self.begin_db_session = async_sessionmaker(self.engine, expire_on_commit=False)
        sqlalchemy.event.listen(self.engine.sync_engine, "connect", setup_database)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.begin_db_session() as session:
            prefixes = (await session.execute(select(Prefix))).scalars()

        self.prefixes = {prefix.guild_id: prefix.prefix for prefix in prefixes}

    async def close(self) -> None:
        if self.app is not None:
            await self.app.shutdown()
            await self.app.cleanup()

        await self.engine.dispose()

        return await super().close()


def guild_specific_prefix(default: str):
    async def inner(bot: ChuniBot, msg: discord.Message) -> list[str]:
        when_mentioned = commands.when_mentioned(bot, msg)

        if msg.guild is None:
            return [*when_mentioned, default]

        return [*when_mentioned, bot.prefixes.get(msg.guild.id, default)]

    return inner


def setup_database(conn, _):
    conn.execute("PRAGMA journal_mode=WAL")
    conn.create_function("jwsim", 2, jarowinkler_similarity)


async def startup():
    if (token := cfg["bot"].get("token")) is None:
        sys.exit(
            "[ERROR] Token not found, make sure 'TOKEN' is set in the '.env' file. Exiting."
        )

    (intents := discord.Intents.default()).message_content = True
    bot = ChuniBot(
        command_prefix=guild_specific_prefix(cfg["bot"].get("default_prefix", fallback="c>")),  # type: ignore[reportGeneralTypeIssues]
        intents=intents,
        help_command=HelpCommand(),
    )
    bot.cfg = cfg
    bot.dev = cfg.getboolean("dangerous", "dev", fallback=False)

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

    discord.utils.setup_logging(
        handler=handler,
        formatter=formatter,
        level=logging.DEBUG if bot.dev else logging.INFO,
        root=False,
    )

    await bot.load_extension("cogs.botutils")
    if bot.dev:
        await bot.load_extension("cogs.hotreload")
        await bot.load_extension("jishaku")

    for file in (BOT_DIR / "cogs").glob("*.py"):
        if file.stem in ["hotreload", "botutils", "__init__"]:
            continue
        try:
            await bot.load_extension(f"cogs.{file.stem}")
            print(f"Loaded cogs.{file.stem}")
        except errors.ExtensionAlreadyLoaded:
            print(f"cogs.{file.stem} already loaded")
        except errors.NoEntryPointError:
            print(f"cogs.{file.stem} has no `setup` function.")
        except errors.ExtensionFailed as e:
            print(
                f"cogs.{file.stem} raised an error: {e.original.__class__.__name__}: {e.original}"
            )

    port = cfg["bot"].getint("login_server_port", fallback=None)
    if port is not None and int(port) > 0:
        bot.app = init_app(bot)
        _ = asyncio.ensure_future(
            web._run_app(
                bot.app,
                port=int(port),
                host="127.0.0.1",
            )
        )

    try:
        bot.launch_time = time()
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
