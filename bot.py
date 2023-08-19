import asyncio
import logging
import logging.handlers
import sys
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Optional

import discord
import sqlalchemy.event
from aiohttp import web
from discord.ext import commands
from jarowinkler import jarowinkler_similarity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from database.models import Prefix
from utils.config import Config
from utils.help import HelpCommand
from web import init_app

if TYPE_CHECKING:
    from aiohttp.web import Application
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


BOT_DIR = Path(__file__).parent
cfg = Config.from_file(BOT_DIR / "bot.ini")


class ChuniBot(commands.Bot):
    cfg: Config
    dev: bool = False

    engine: "AsyncEngine"
    begin_db_session: async_sessionmaker["AsyncSession"]

    launch_time: float
    app: Optional["Application"] = None

    # Prefix cache
    prefixes: dict[int, str]

    # key: user discord ID
    # value: userId, _t cookies from CHUNITHM-NET
    sessions: dict[int, tuple[str | None, str | None]]

    def __init__(self, *args, config: Config, **kwargs):
        self.cfg = config
        self.dev = self.cfg.dangerous.dev
        self.prefixes = {}
        self.sessions = {}

        super().__init__(*args, **kwargs)

    async def start(self, *args, **kwargs):
        self.launch_time = time()
        return await super().start(*args, **kwargs)

    async def setup_hook(self) -> None:
        await self.load_extension("cogs.autocompleters")
        print("Loaded cogs.autocompleters")

        await self.load_extension("cogs.botutils")
        print("Loaded cogs.botutils")
        if self.dev:
            await self.load_extension("cogs.hotreload")
            print("Loaded cogs.hotreload")

            await self.load_extension("jishaku")
            print("Loaded jishaku")

        for file in (BOT_DIR / "cogs").glob("*.py"):
            if file.stem in ("hotreload", "botutils", "__init__", "autocompleters"):
                continue
            try:
                await self.load_extension(f"cogs.{file.stem}")
                print(f"Loaded cogs.{file.stem}")
            except commands.errors.ExtensionAlreadyLoaded:
                print(f"cogs.{file.stem} already loaded")
            except commands.errors.NoEntryPointError:
                print(f"cogs.{file.stem} has no `setup` function.")
            except commands.errors.ExtensionFailed as e:
                print(
                    f"cogs.{file.stem} raised an error: {e.original.__class__.__name__}: {e.original}"
                )

        connection_string = cfg.bot.db_connection_string
        self.engine = create_async_engine(connection_string)
        self.begin_db_session = async_sessionmaker(self.engine, expire_on_commit=False)

        def setup_database(conn, _):
            conn.execute("PRAGMA journal_mode=WAL")
            conn.create_function("jwsim", 2, jarowinkler_similarity)

        sqlalchemy.event.listen(self.engine.sync_engine, "connect", setup_database)

        async with self.begin_db_session() as session:
            prefixes = (await session.execute(select(Prefix))).scalars()

        self.prefixes = {prefix.guild_id: prefix.prefix for prefix in prefixes}
        print(f"Loaded {len(self.prefixes)} guild prefixes")

        port = cfg.web.login_server_port
        if port is not None and int(port) > 0:
            self.app = init_app(self, cfg.web.goatcounter)
            _ = asyncio.ensure_future(
                web._run_app(
                    self.app,
                    port=int(port),
                    host="127.0.0.1",
                )
            )

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


if __name__ == "__main__":
    if (token := cfg.bot.token) is None:
        sys.exit(
            "[ERROR] Token not found, make sure 'bot.token' is set in 'bot.ini'. Exiting."
        )

    (intents := discord.Intents.default()).message_content = True
    bot = ChuniBot(
        command_prefix=guild_specific_prefix(cfg.bot.default_prefix),  # type: ignore[reportGeneralTypeIssues]
        intents=intents,
        help_command=HelpCommand(),
        config=cfg,
    )

    try:
        bot.run(
            token,
            reconnect=True,
            log_handler=logging.handlers.RotatingFileHandler(
                filename="discord.log",
                encoding="utf-8",
                maxBytes=32 * 1024 * 1024,  # 32 MiB
                backupCount=5,  # Rotate through 5 files
            ),
            log_formatter=logging.Formatter(
                "[{asctime}] [{levelname:<8}] {name}: {message}",
                datefmt="%Y-%m-%d %H:%M:%S",
                style="{",
            ),
            log_level=logging.DEBUG if bot.dev else logging.INFO,
        )
    except discord.LoginFailure:
        sys.exit(
            "[ERROR] Invalid token, make sure 'bot.token' is properly set in 'bot.ini'. Exiting."
        )
    except discord.PrivilegedIntentsRequired:
        sys.exit(
            "[ERROR] Message Content Intent not enabled, go to 'https://discord.com/developers/applications' and enable the Message Content Intent. Exiting."
        )
