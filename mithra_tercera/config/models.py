from dataclasses import dataclass
from typing import Annotated, Optional

from pydantic import BaseModel, HttpUrl, StringConstraints, UrlConstraints
from pydantic_core import Url


DiscordEmoji = Annotated[
    str,
    StringConstraints(pattern=r"^<a?:[a-zA-Z0-9\_]{1,32}:[0-9]{15,20}>$"),
]
IconKey = Annotated[
    str,
    StringConstraints(pattern=r"^(sssp|sss|ssp|ss|sp|s|aaa|aa|a|bbb|bb|b|c|d)$"),
]
LogLevel = Annotated[
    str,
    StringConstraints(pattern=r"^(CRITICAL|ERROR|WARNING|INFO|DEBUG)$"),
]
KamaitachiClientId = Annotated[str, StringConstraints(pattern=r"^CI[0-9a-f]{40}$")]
KamaitachiClientSecret = Annotated[str, StringConstraints(pattern=r"^CS[0-9a-f]{40}$")]
DiscordToken = Annotated[
    str,
    StringConstraints(pattern=r"^([\w-]{26}\.[\w-]{6}\.[\w-]{38}|mfa\.[\w-]{84})$"),
]
DiscordWebhookUrl = Annotated[
    str,
    StringConstraints(
        pattern=r"^https:\/\/discord\.com\/api\/webhooks\/\d{18,19}\/[\w-]+$",
    ),
]
DiscordMentions = Annotated[
    str,
    StringConstraints(pattern=r"^<@&?\d{18,19}>$"),
]


class MTTachiConfig(BaseModel):
    base_url: HttpUrl
    client_id: KamaitachiClientId
    client_secret: KamaitachiClientSecret


class MTDiscordConfig(BaseModel):
    token: DiscordToken
    default_prefix: str
    icons: dict[IconKey, DiscordEmoji]


class MTDiscordLoggingConfig(BaseModel):
    webhook_url: DiscordWebhookUrl
    who_to_mention: list[DiscordMentions]


class MTLoggingConfig(BaseModel):
    level: LogLevel = "INFO"
    console: bool = False
    file: bool = False
    seq_api_key: Optional[str] = None
    discord: Optional[MTDiscordLoggingConfig] = None


class MTConfig(BaseModel):
    display_name: str
    db_connection_string: Annotated[
        Url,
        UrlConstraints(
            allowed_schemes=[
                "cockroachdb",
                "cockroachdb+pool",
                "crdb",
                "crdb+pool",
                "mysql",
                "mysql+pool",
                "postgres",
                "postgresql",
                "postgres+pool",
                "postgresql+pool",
                "sqlite",
                "sqliteext",
                "sqlite+pool",
                "sqliteext+pool",
            ],
        ),
    ]
    our_url: HttpUrl
    tachi: MTTachiConfig
    discord: MTDiscordConfig
    logger_config: MTLoggingConfig


@dataclass(kw_only=True)
class Environment:
    seq_url: Optional[str]
