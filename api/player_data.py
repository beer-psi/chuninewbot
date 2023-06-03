from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .enums import Possession


@dataclass
class Nameplate:
    content: str
    rarity: str


@dataclass
class Rating:
    current: float
    max: Optional[float] = None


@dataclass
class Currency:
    owned: int
    total: int


@dataclass
class Overpower:
    value: float
    progress: float


@dataclass(kw_only=True)
class PlayerData:
    possession: Possession
    
    avatar: str

    name: str

    reborn: int = 0
    lv: int

    playcount: Optional[int] = None
    last_play_date: datetime

    overpower: Overpower
    nameplate: Nameplate
    rating: Rating
    currency: Optional[Currency] = None

    friend_code: Optional[str] = None
