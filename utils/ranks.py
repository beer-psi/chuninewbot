from pathlib import Path

from dotenv import dotenv_values

from api.enums import Rank

BOT_DIR = Path(__file__).absolute().parent.parent
cfg = dotenv_values(BOT_DIR / ".env")


def rank_icon(rank: str | Rank) -> str:
    return cfg.get(f"RANK_ICON_{str(rank).replace('+', 'P')}", str(rank))  # type: ignore
