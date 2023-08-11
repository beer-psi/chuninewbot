from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from api.entities.record import DetailedRecentRecord, MusicRecord


@dataclass(kw_only=True)
class AnnotatedMusicRecord(MusicRecord):
    level: Optional[str] = None
    internal_level: Optional[float] = None
    unknown_const: bool = True

    play_rating: "float | Decimal" = 0.0

    overpower_base: "Decimal" = Decimal(0)
    overpower_max: "Decimal" = Decimal(0)

    @property
    def displayed_difficulty(self) -> str:
        if self.level is None and self.internal_level is None:
            return f"{self.difficulty}"
        elif (
            self.internal_level is None
            or self.internal_level == 0
            or self.unknown_const
        ):
            return f"{self.difficulty} {self.level}"
        else:
            return f"{self.difficulty} {self.internal_level}"


@dataclass(kw_only=True)
class AnnotatedRecentRecord(AnnotatedMusicRecord):
    track: int
    date: datetime
    new_record: bool


@dataclass(kw_only=True)
class AnnotatedDetailedRecentRecord(AnnotatedMusicRecord, DetailedRecentRecord):
    full_combo: Optional[int] = None

