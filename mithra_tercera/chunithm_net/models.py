from typing import TypedDict, NotRequired, Literal


Difficulty = Literal["BASIC", "ADVANCED", "EXPERT", "MASTER", "ULTIMA", "WORLD'S END"]
Rank = Literal[
    "SSS+", "SSS", "SS+", "SS", "S+", "S", "AAA", "AA", "A", "BBB", "BB", "B", "C", "D"
]
ComboLamp = Literal["FULL COMBO", "ALL JUSTICE"]
ClearLamp = Literal["FAILED", "CLEAR", "HARD", "ABSOLUTE", "ABSOLUTE+", "CATASTROPHY"]


class Lamps(TypedDict):
    combo: NotRequired[ComboLamp]
    clear: ClearLamp


class Score(TypedDict):
    title: str
    difficulty: Difficulty
    score: int
    rank: NotRequired[Rank]
    lamps: Lamps
