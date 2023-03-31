from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .enums import ClearType, Difficulty, Rank


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
class MusicRecord:
    title: str
    jacket: str
    difficulty: Difficulty

    score: int
    rank: Rank
    clear: ClearType

    play_count: Optional[int] = None

    # These are not returned by the website, the bot fills it in
    level: Optional[str] = None
    internal_level: Optional[float] = None
    unknown_const: bool = False
    play_rating: Optional[float] = None


@dataclass(kw_only=True)
class RecentRecord(MusicRecord):
    detailed: Optional[DetailedParams]

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
