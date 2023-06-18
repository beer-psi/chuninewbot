from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from .consts import JACKET_BASE
from .enums import ClearType, Difficulty, Rank

if TYPE_CHECKING:
    from decimal import Decimal


@dataclass
class Skill:
    name: str
    grade: int


@dataclass
class Judgements:
    jcrit: int
    justice: int
    attack: int
    miss: int


@dataclass
class NoteType:
    tap: float
    hold: float
    slide: float
    air: float
    flick: float


@dataclass
class DetailedParams:
    idx: int
    token: str


@dataclass(kw_only=True)
class Record:
    detailed: Optional[DetailedParams] = None

    title: str
    difficulty: Difficulty
    score: int

    rank: Rank = Rank.D
    clear: ClearType = ClearType.FAILED


@dataclass(kw_only=True)
class MusicRecord(Record):
    jacket: str

    play_count: Optional[int] = None

    # These are not returned by the website, the bot fills it in
    level: Optional[str] = None
    internal_level: Optional[float] = None
    unknown_const: bool = True
    play_rating: "float | Decimal" = 0.0

    def full_jacket_url(self) -> str:
        return f"{JACKET_BASE}/{self.jacket}"

    @classmethod
    def from_record(cls, record: Record):
        return cls(
            detailed=record.detailed,
            title=record.title,
            difficulty=record.difficulty,
            score=record.score,
            jacket="",
            rank=Rank.D,
            clear=ClearType.FAILED,
            level="",
            internal_level=0.0,
            unknown_const=False,
            play_rating=0.0,
        )

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
class RecentRecord(MusicRecord):
    track: int
    date: datetime
    new_record: bool


@dataclass(kw_only=True)
class DetailedRecentRecord(RecentRecord):
    character: str
    skill: Skill
    skill_result: int

    max_combo: int

    judgements: Judgements
    note_type: NoteType

    # These are not returned by the website, the bot fills it in
    full_combo: Optional[int] = None

    @classmethod
    def from_basic(cls, basic: RecentRecord):
        return cls(
            detailed=None,
            track=basic.track,
            date=basic.date,
            title=basic.title,
            jacket=basic.jacket,
            difficulty=basic.difficulty,
            score=basic.score,
            rank=basic.rank,
            clear=basic.clear,
            new_record=basic.new_record,
            character="",
            skill=Skill("", 0),
            skill_result=0,
            max_combo=0,
            judgements=Judgements(0, 0, 0, 0),
            note_type=NoteType(0, 0, 0, 0, 0),
            level=basic.level,
        )
