# We already have proper error reporting here, including Pydantic errors.
# Adding exception info only floods the logs for no good reason.
# ruff: noqa: TRY400

import importlib.util
import os
import logging
import sys
from pathlib import Path

import json5
from dotenv import load_dotenv
from pydantic import ValidationError

from mithra_tercera.config.models import MTConfig, Environment


__all__ = ("bot_config", "environment")


load_dotenv()

# Stub logger, because importing the logger here would cause a circular import.
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    ),
)
logger.addHandler(handler)

config_location = os.environ.get("TERCERA_CONF_LOCATION", "./config.json5")

try:
    config_file = Path(config_location).read_text()
except FileNotFoundError:
    logger.error("Error while trying to open 'config.json5'. Is one present?")
    sys.exit(1)

parsed_config = json5.loads(config_file)
if not isinstance(parsed_config, dict):
    logger.error("Invalid 'config.json5' file. Top level is not an object.")
    sys.exit(1)

try:
    bot_config = MTConfig(**parsed_config)
except ValidationError as e:
    logger.error(f"Invalid 'config.json5' file.\n{e}")
    sys.exit(1)


_seq_url = os.environ.get("SEQ_URL")

if not importlib.util.find_spec("seqlog") and bot_config.logger_config.seq_api_key:
    logger.warning(
        "seqlog was not installed, yet logger_config.seq_api_key was defined. No logs will be sent to seq!",
    )

if not _seq_url and bot_config.logger_config.seq_api_key:
    logger.warning(
        "No SEQ_URL specified in environment, yet logger_config.seq_api_key was defined. No logs will be sent to seq!",
    )


environment = Environment(
    seq_url=_seq_url,
)
