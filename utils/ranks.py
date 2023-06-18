from typing import TYPE_CHECKING

from bot import cfg

if TYPE_CHECKING:
    from api.enums import Rank


def rank_icon(rank: "str | Rank") -> str:
    return cfg.get(f"RANK_ICON_{str(rank).replace('+', 'P')}", str(rank))  # type: ignore
