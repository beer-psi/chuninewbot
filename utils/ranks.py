from typing import TYPE_CHECKING

from bot import cfg

if TYPE_CHECKING:
    from chunithm_net.entities.enums import Rank


def rank_icon(rank: "str | Rank") -> str:
    key = str(rank).lower().replace("+", "p")
    return getattr(cfg.icons, key, str(rank))
