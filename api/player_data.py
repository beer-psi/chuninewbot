from dataclasses import dataclass
from datetime import datetime
from typing import Optional


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
    avatar: str

    name: str
    lv: int
    playcount: Optional[int] = 0
    last_play_date: datetime

    overpower: Overpower
    nameplate: Nameplate
    rating: Rating
    currency: Optional[Currency] = None
