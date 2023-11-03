import asyncio
import contextlib
import importlib.util
import sys
from typing import Awaitable, Callable

import discord
from discord.ext import commands
import mithra_tercera

from mithra_tercera import MithraTercera
from mithra_tercera.config import bot_config
from mithra_tercera.logger import create_log_ctx


logger = create_log_ctx(__name__)


def guild_specific_prefix(
    default: str,
) -> Callable[[MithraTercera, discord.Message], Awaitable[list[str]]]:
    async def inner(bot: MithraTercera, msg: discord.Message) -> list[str]:
        when_mentioned = commands.when_mentioned(bot, msg)

        if msg.guild is None:
            return [*when_mentioned, default]

        return [*when_mentioned, bot.prefixes.get(msg.guild.id, default)]

    return inner


async def startup() -> None:
    (intents := discord.Intents.default()).message_content = True

    bot = MithraTercera(
        command_prefix=guild_specific_prefix(bot_config.discord.default_prefix),  # type: ignore[reportGeneralTypeIssues]
        intents=intents,
        # help_command=HelpCommand(),
        # config=config,
    )

    try:
        async with bot:
            await bot.start(bot_config.discord.token, reconnect=True)
    except discord.LoginFailure as e:
        logger.critical(
            f"Could not log in to Discord: {e} Double check `discord.token` in 'config.json5'."
        )
        sys.exit(1)
    except discord.PrivilegedIntentsRequired:
        logger.critical(
            "Message content intent not enabled, please enable it at https://discord.com/developers/applications",
        )
        sys.exit(1)
    except discord.DiscordException as e:
        logger.critical("A generic Discord error has occured.", exc_info=e)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        logger.critical("Failed to properly boot.", exc_info=e)
        sys.exit(1)


def sync_startup() -> None:
    logger.info(f"Booting {bot_config.display_name} {mithra_tercera.__version__}.")
    logger.info(f"Log level is set to {bot_config.logger_config.level}.")

    event_loop_impl = None
    loop_factory = None

    if sys.platform == "win32" and importlib.util.find_spec("winloop"):
        logger.info("Using `winloop` as the event loop implementation.")

        import winloop  # type: ignore[reportMissingImports]

        loop_factory = winloop.new_event_loop
        event_loop_impl = winloop
    elif sys.platform != "win32" and importlib.util.find_spec("uvloop"):
        logger.info("Using `uvloop` as the event loop implementation.")

        import uvloop  # type: ignore[reportMissingImports]

        loop_factory = uvloop.new_event_loop
        event_loop_impl = uvloop

    if sys.version_info >= (3, 11):
        with asyncio.Runner(loop_factory=loop_factory) as runner:
            runner.run(startup())
    else:
        if event_loop_impl is not None:
            event_loop_impl.install()
        asyncio.run(startup())


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        sync_startup()
