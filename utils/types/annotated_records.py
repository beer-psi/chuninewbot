from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from chunithm_net.entities.record import DetailedRecentRecord, MusicRecord


@dataclass(kw_only=True)
class AnnotatedMusicRecord(MusicRecord):
    level: Optional[str] = None
    internal_level: Optional[float] = None

    play_rating: "float | Decimal" = 0.0

    overpower_base: "Decimal" = Decimal(0)
    overpower_max: "Decimal" = Decimal(0)

    @property
    def displayed_difficulty(self) -> str:
        if self.level and self.internal_level:
            return f"{self.difficulty} {self.internal_level}"
        if self.level != "0" and self.level:
            return f"{self.difficulty} {self.level}"
        return f"{self.difficulty}"


@dataclass(kw_only=True)
class AnnotatedRecentRecord(AnnotatedMusicRecord):
    track: int
    date: datetime
    new_record: bool


@dataclass(kw_only=True)
class AnnotatedDetailedRecentRecord(AnnotatedMusicRecord, DetailedRecentRecord):
    full_combo: Optional[int] = None
