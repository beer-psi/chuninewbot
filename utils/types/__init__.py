from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .annotated_records import *


@dataclass(kw_only=True)
class SongSearchResult:
    similarity: float

    id: str
    chunithm_id: int

    title: str
    genre: str
    artist: str

    release: datetime

    bpm: int

    jacket: str

    alias: Optional[str] = None
