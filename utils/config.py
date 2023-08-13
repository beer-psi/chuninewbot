from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from configparser import ConfigParser, SectionProxy


class BotConfig:
    def __init__(self, section: "SectionProxy") -> None:
        self.__section = section

    @property
    def token(self) -> str:
        return self.__section.get("token")

    @property
    def default_prefix(self) -> str:
        return self.__section.get("default_prefix", fallback="c>")

    @property
    def db_connection_string(self) -> str:
        return self.__section.get(
            "db_connection_string",
            fallback="sqlite+aiosqlite:///database/database.sqlite3",
        )

    @property
    def error_reporting_webhook(self) -> Optional[str]:
        return self.__section.get("error_reporting_webhook")

    @property
    def login_server_port(self) -> Optional[int]:
        return self.__section.getint("login_server_port", fallback=None)


class CredentialsConfig:
    def __init__(self, section: "SectionProxy") -> None:
        self.__section = section

    @property
    def chunirec_token(self) -> Optional[str]:
        return self.__section.get("chunirec_token")

    @property
    def kamaitachi_client_id(self) -> Optional[str]:
        return self.__section.get("kamaitachi_client_id")


class IconsConfig:
    __slots__ = (
        "__section",
        "sssp",
        "sss",
        "ssp",
        "ss",
        "sp",
        "s",
        "aaa",
        "aa",
        "a",
        "bbb",
        "bb",
        "b",
        "c",
        "d",
    )

    def __init__(self, section: "SectionProxy") -> None:
        self.__section = section

        for k in self.__slots__:
            if k.startswith("__"):
                continue
            setattr(self, k, self.__section.get(k))


class DangerousConfig:
    def __init__(self, section: "SectionProxy") -> None:
        self.__section = section

    @property
    def dev(self) -> bool:
        return self.__section.getboolean("dev", fallback=False)


class Config:
    def __init__(self, config: "ConfigParser") -> None:
        self.__config = config
        self.bot = BotConfig(self.__config["bot"])
        self.credentials = CredentialsConfig(self.__config["credentials"])
        self.icons = IconsConfig(self.__config["icons"])
        self.dangerous = DangerousConfig(self.__config["dangerous"])
