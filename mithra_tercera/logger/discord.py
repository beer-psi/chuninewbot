import asyncio
import atexit
import logging
from typing import Any, ClassVar, Literal, Mapping, Optional, Self

import aiohttp
import discord


def _flush(self: logging.Logger) -> None:
    for handler in self.handlers:
        if isinstance(handler, DiscordWebhookHandler):
            handler.send()


class DiscordWebhookFormatter(logging.Formatter):
    MAX_DISCORD_MESSAGE_LEN = 2000
    DISCORD_MESSAGE_TEMPLATE = "```diff\n{}```"
    DISCORD_MESSAGE_TEMPLATE_LEN = len(DISCORD_MESSAGE_TEMPLATE.format(""))
    MAX_LOG_LEN = MAX_DISCORD_MESSAGE_LEN - DISCORD_MESSAGE_TEMPLATE_LEN

    _LEVEL_PREFIX_LENGTH = 3
    _LEVEL_PREFIX: ClassVar[dict[str, str]] = {
        "DEBUG": "===",
        "INFO": "+  ",
        "WARNING": "W  ",
        "ERROR": "-  ",
        "CRITICAL": "-!!",
    }

    def __init__(  # noqa: PLR0913
        self: Self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: Literal["%", "{", "$"] = "%",
        validate: bool = True,  # noqa: FBT001, FBT002
        *,
        defaults: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)
        for v in DiscordWebhookFormatter._LEVEL_PREFIX.values():
            assert len(v) == DiscordWebhookFormatter._LEVEL_PREFIX_LENGTH

    def format(  # noqa: A003
        self: Self,
        record: logging.LogRecord,
    ) -> tuple[list[str], int]:
        lines = record.msg.split("\n")

        try:
            level_prefix = DiscordWebhookFormatter._LEVEL_PREFIX[record.levelname]
        except KeyError:
            level_prefix = " " * DiscordWebhookFormatter._LEVEL_PREFIX_LENGTH

        formatted_lines = []
        formatted_lines_len = 0

        for i in range(len(lines)):
            # if single log message has multiple lines, show it with using different separators
            # Example:
            # Log message: logger.info('1st line\nnext line\nlast line')
            # Formatted output:
            # +  │1st line
            # +  ├next line
            # +  └last line
            if i == 0:
                separator = "│"
            elif i == len(lines) - 1:
                separator = "└"
            else:
                separator = "├"

            split_len = (
                DiscordWebhookFormatter.MAX_LOG_LEN
                - DiscordWebhookFormatter._LEVEL_PREFIX_LENGTH
                - 1
            )  # -1 = separator
            if len(lines[i]) > split_len:
                # line is too long to send in single discord message, we need to split it in multiple messages
                formatted_lines.append(level_prefix + separator + lines[i][:split_len])
                formatted_lines_len += split_len

                # use different separator to show, that line was split into multiple messages
                separator = "↳"
                for line in [
                    lines[i][x : x + split_len]
                    for x in range(split_len, len(lines[i]), split_len)
                ]:
                    formatted_lines.append(level_prefix + separator + line)
                    formatted_lines_len += len(formatted_lines[-1])
            else:
                formatted_lines.append(level_prefix + separator + lines[i])
                formatted_lines_len += len(formatted_lines[-1])

        # add \n to char count
        formatted_lines_len += len(formatted_lines) - 1

        return formatted_lines, formatted_lines_len


class DiscordWebhookHandler(logging.Handler):
    def __init__(self: Self, webhook_url: str, *, auto_flush: bool = False) -> None:
        super().__init__()
        self.webhook = discord.Webhook.from_url(
            webhook_url, session=aiohttp.ClientSession(),
        )
        self.formatter: DiscordWebhookFormatter = DiscordWebhookFormatter()

        self.auto_flush = auto_flush

        # buffer for storing shorter logs and sending them in larger batches
        self.buffer: list[tuple[logging.LogRecord, list[str]]] = []
        self.buffer_message_len = 0

        # send all remaining buffered messages before app exit
        atexit.register(self.send)

    def emit(self: Self, record: logging.LogRecord) -> None:
        try:
            formatted_lines, formatted_lines_len = self.formatter.format(record)

            if formatted_lines_len >= self.formatter.MAX_LOG_LEN:
                # new message is too large, new message can't fit info buffer, send buffered message and also send new message
                for line in formatted_lines:
                    if (
                        self.buffer_message_len + len(line)
                        >= self.formatter.MAX_LOG_LEN
                    ):
                        self.send()

                        self.buffer.append((record, [line]))
                        self.buffer_message_len += len(line) + 1
                    else:
                        self.buffer.append((record, [line]))
                        self.buffer_message_len += len(line) + 1

                self.send()
            elif (
                self.buffer_message_len + formatted_lines_len
                >= self.formatter.MAX_LOG_LEN
            ):
                # buffered message + new message is too large, but new message can fit into buffer, send buffered message and move new message into buffer
                self.send()

                self.buffer.append((record, formatted_lines))
                self.buffer_message_len += formatted_lines_len + 1
            else:
                # buffered messasge + new message fits info buffer, append it
                self.buffer.append((record, formatted_lines))
                self.buffer_message_len += formatted_lines_len + 1

            if self.auto_flush:
                self.send()
        except Exception:  # noqa: BLE001
            self.handleError(record)

    def send(self: Self) -> None:
        if self.buffer_message_len == 0:
            # if buffer is empty, skip sending
            return

        # prepare body of message
        log_message = ""
        for b in self.buffer:
            for line in b[1]:
                log_message += line + "\n"

        # prepare message for sending, exclude last \n char
        json_data = {
            "content": self.formatter.DISCORD_MESSAGE_TEMPLATE.format(log_message[:-1]),
        }

        coro = post_content(self, self.buffer[-1][0], self.webhook, json_data)
        try:
            loop = asyncio.get_event_loop()
            _ = asyncio.ensure_future(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(coro)

        self.buffer.clear()
        self.buffer_message_len = 0


async def post_content(
    handler: logging.Handler,
    record: logging.LogRecord,
    webhook: discord.Webhook,
    message_body: dict[str, Any],
) -> None:
    try:
        await webhook.send(**message_body)
    except discord.DiscordException:
        handler.handleError(record)
