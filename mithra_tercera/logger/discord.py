import asyncio
import datetime
import itertools
import logging
from dataclasses import dataclass, field
from logging import LogRecord
from typing import Any, Optional, Self

import aiohttp
import discord
from discord.ext import tasks


MAX_LOG_SNIPPET_LENGTH = 1500
DISCORD_COLORS: dict[str, int] = {
    "CRITICAL": 0xFF0000,
    "ERROR": 0xCC0000,
    "WARN": 0xFFCC00,
    "WARNING": 0xFFCC00,
}


@dataclass
class LogLevelCountState:
    warn: list[str] = field(default_factory=list)
    error: list[str] = field(default_factory=list)


class DiscordHandler(logging.Handler):
    """
    A logging.Handler implementation using Discord webhooks, inspired by
    https://github.com/TNG-dev/Tachi/blob/staging/server/src/lib/logger/discord-transport.ts
    """

    def __init__(
        self: Self,
        webhook_url: str,
        *,
        service_name: str = "",
        who_to_mention: Optional[list[str]] = None,
    ) -> None:
        super().__init__()
        self.webhook = discord.Webhook.from_url(
            webhook_url, session=aiohttp.ClientSession()
        )

        self._is_bucketing = False
        self._bucket_start: datetime.datetime | None = None
        self._bucket_data = LogLevelCountState()

        self._service_name = service_name
        self._who_to_mention = who_to_mention or []

    def _reset_bucket_data(self: Self) -> None:
        self._bucket_data.warn.clear()
        self._bucket_data.error.clear()

    def _post_data(self: Self, payload: dict[str, Any]) -> None:
        coro = self.webhook.send(**payload)
        try:
            loop = asyncio.get_event_loop()
            _ = asyncio.ensure_future(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(coro)

    def _get_who_to_mention(self: Self) -> str:
        if len(self._who_to_mention) > 0:
            return " ".join(self._who_to_mention)

        return "Nobody configured to tag, but this is bad, get someone!"

    def _send_directly_to_discord(self: Self, record: LogRecord, msg: str) -> None:
        payload = {
            "content": "",
            "embeds": [
                discord.Embed(
                    description=f"[{record.levelname}] {msg}",
                    color=DISCORD_COLORS.get(record.levelname),
                    timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
                )
            ],
        }

        if record.levelno == logging.CRITICAL:
            payload[
                "content"
            ] = f"CRITICAL ERROR: {self._get_who_to_mention()}\n{payload['content']}"

        self._post_data(payload)

    @tasks.loop(minutes=1)
    async def _send_bucket_data(self: Self) -> None:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        embed = discord.Embed(
            title=f"{self._service_name} log summary".strip(),
            description=f"Log summary for {self._bucket_start.isoformat() if self._bucket_start else ''} to {now.isoformat()}.",
            timestamp=now,
        )

        if len(warns := self._bucket_data.warn) > 0:
            embed.color = DISCORD_COLORS["WARNING"]
            embed.add_field(name="Warns", value=warns)
        if len(errs := self._bucket_data.error) > 0:
            embed.color = DISCORD_COLORS["ERROR"]
            embed.add_field(name="Errors", value=errs)

        log_snippet = "\n".join(
            itertools.chain(self._bucket_data.error, self._bucket_data.warn)
        )
        if len(log_snippet) > MAX_LOG_SNIPPET_LENGTH:
            log_snippet = f"{log_snippet[:MAX_LOG_SNIPPET_LENGTH - 3]}..."

        payload = {
            "content": f"```\n{log_snippet}\n```",
            "embed": embed,
        }
        self._post_data(payload)
        self._reset_bucket_data()
        self._is_bucketing = False
        self._bucket_start = None

    def emit(self: Self, record: LogRecord) -> None:
        if record.levelno < logging.WARNING:
            return None

        msg = self.format(record)

        if record.levelno == logging.CRITICAL:
            return self._send_directly_to_discord(record, msg)

        if record.levelno == logging.ERROR:
            self._bucket_data.error.append(msg)
        elif record.levelno == logging.WARNING:
            self._bucket_data.warn.append(msg)

        if not self._is_bucketing:
            self._is_bucketing = True
            self._bucket_start = datetime.datetime.now(tz=datetime.timezone.utc)

        if not self._send_bucket_data.is_running():
            self._send_bucket_data.start()

        return None
