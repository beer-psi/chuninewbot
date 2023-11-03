import contextlib
import json
import logging
import logging.handlers

from discord.utils import stream_supports_colour, _ColourFormatter

from mithra_tercera.config import bot_config, environment
from mithra_tercera.logger.discord import DiscordHandler


ROOT_LOGGER_NAME = "mithra_tercera"


if bot_config.logger_config.seq_api_key and environment.seq_url:
    with contextlib.suppress(ImportError):
        import seqlog

        seqlog.configure_feature(
            seqlog.FeatureFlag.IGNORE_SEQ_SUBMISSION_ERRORS,
            enable=False,
        )
        seqlog.configure_feature(seqlog.FeatureFlag.EXTRA_PROPERTIES, enable=True)
        seqlog.configure_feature(seqlog.FeatureFlag.STACK_INFO, enable=True)

        logging.setLoggerClass(seqlog.StructuredLogger)

        root_logger = logging.getLogger(ROOT_LOGGER_NAME)

        handler = seqlog.SeqLogHandler(
            server_url=environment.seq_url,
            api_key=bot_config.logger_config.seq_api_key,
            auto_flush_timeout=10,
            json_encoder_class=json.encoder.JSONEncoder,
        )

        root_logger.addHandler(handler)

# Get the logger again, in cases where seqlog was not installed
# or seq was not set up.
root_logger = logging.getLogger(ROOT_LOGGER_NAME)
root_logger.setLevel(bot_config.logger_config.level)

if bot_config.logger_config.file:
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=f"logs/{ROOT_LOGGER_NAME}.log",
        when="D",
        backupCount=14,
        delay=True,
        utc=True,
    )
    root_logger.addHandler(handler)

if bot_config.logger_config.console:
    handler = logging.StreamHandler()

    if stream_supports_colour(handler.stream):
        formatter = _ColourFormatter()
    else:
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(
            "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

if bot_config.logger_config.discord and (
    webhook_url := bot_config.logger_config.discord.webhook_url
):
    handler = DiscordHandler(
        webhook_url,
        service_name=bot_config.display_name,
        who_to_mention=bot_config.logger_config.discord.who_to_mention,
    )

    # we don't want to flood discord with debug logs
    handler.setLevel(logging.WARNING)

    root_logger.addHandler(handler)

if len(root_logger.handlers) == 0:
    print(
        "You have no handlers set. Absolutely no logs will be saved. This is a terrible idea!"
    )


def create_log_ctx(name: str, lg: logging.Logger = root_logger) -> logging.Logger:
    # mithra_tercera.db
    if name.startswith(f"{ROOT_LOGGER_NAME}."):
        _, _, name = name.partition(".")

    return lg.getChild(name)
