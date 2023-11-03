import sys
from time import perf_counter

import asyncio
from tortoise import Tortoise
from tortoise.exceptions import ConfigurationError

from mithra_tercera.config import bot_config
from mithra_tercera.logger import create_log_ctx
import contextlib


logger = create_log_ctx(__name__)


async def init_db() -> None:
    logger.info(f"Connecting to database {bot_config.db_connection_string}...")

    try:
        start = perf_counter()

        await Tortoise.init(
            db_url=str(bot_config.db_connection_string),
            modules={"models": ["mithra_tercera.db.models"]},
        )
        await Tortoise.generate_schemas(safe=True)

        stop = perf_counter()

        logger.info(f"Database initialization successful: took {(stop - start) * 1000}ms")
    except Exception as e:  # noqa: BLE001
        logger.critical("Failed to initialize database", exc_info=e)
        await asyncio.sleep(1)
        sys.exit(1)


async def close_db() -> None:
    with contextlib.suppress(ConfigurationError):
        await Tortoise.close_connections()
        logger.info("Closed database connection.")


def close_db_sync() -> None:
    coro = close_db()
    try:
        loop = asyncio.get_event_loop()
        _ = asyncio.ensure_future(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)
