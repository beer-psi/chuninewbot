from typing import TYPE_CHECKING

from utils.config import config

if TYPE_CHECKING:
    from chunithm_net.entities.enums import Rank


def rank_icon(rank: "str | Rank") -> str:
    str_rank = str(rank)
    key = str_rank.lower().replace("+", "p")
    return getattr(config.icons, key, str_rank) or str_rank
