import sys
from time import time
from typing import NamedTuple, Literal, Self

from discord.ext import commands

from mithra_tercera.cogs import ENABLED_COGS
from mithra_tercera.db import close_db, init_db
from mithra_tercera.db.models import Prefix
from mithra_tercera.logger import create_log_ctx


logger = create_log_ctx(__name__)


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: Literal["alpha", "beta", "candidate", "final"]
    serial: int


__title__ = "mithratercera"
__author__ = "beerpsi"
__license__ = "0BSD"
__copyright__ = "Copyright 2023-present beerpsi"
__version__ = "0.3.0a"


version_info: VersionInfo = VersionInfo(
    major=0,
    minor=3,
    micro=0,
    releaselevel="alpha",
    serial=0,
)


class MithraTercera(commands.Bot):
    prefixes: dict[int, str]
    launch_time: float

    # Not typing all that
    def __init__(self: Self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.prefixes = {}

        super().__init__(*args, **kwargs)

    async def start(self: Self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.launch_time = time()
        return await super().start(*args, **kwargs)

    async def setup_hook(self: Self) -> None:
        await init_db()

        prefixes = await Prefix.all()
        for prefix in prefixes:
            self.prefixes[prefix.guild_id] = prefix.prefix

        for cog in ENABLED_COGS:
            try:
                await self.load_extension(cog)
                logger.debug(f"Loaded extension {cog}")
            except commands.errors.ExtensionAlreadyLoaded:  # noqa: PERF203
                logger.warning(f"Extension {cog} was already loaded")
            except commands.errors.ExtensionNotFound:
                logger.critical(
                    f"Extension {cog} was not found. Perhaps there was a typo?"
                )
                await self.close()
                sys.exit(1)
            except commands.errors.NoEntryPointError:
                logger.critical(f"Extension {cog} has no setup function.")
                await self.close()
                sys.exit(1)
            except commands.errors.ExtensionFailed as e:
                logger.critical(f"Extension {cog} raised an error.", exc_info=e)
                await self.close()
                sys.exit(1)

    async def close(self: Self) -> None:
        await close_db()
        return await super().close()
