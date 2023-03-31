from enum import Enum
from typing import Self


class Difficulty(Enum):
    BASIC = 0
    ADVANCED = 1
    EXPERT = 2
    MASTER = 3
    WORLDS_END = 4

    def __str__(self):
        if self.value == 4:
            return "WORLD'S END"
        else:
            return self.name

    def color(self):
        match self.value:
            case 0:
                return 0x009F7B
            case 1:
                return 0xF47900
            case 2:
                return 0xE92829
            case 3:
                return 0x8C1BE1
            case 4:
                return 0x0B6FF3

    def short_form(self):
        if self.value == 4:
            return "WE"
        else:
            return self.name[:3]

    @classmethod
    def from_embed_color(cls, color: int) -> Self:
        if color == 0x009F7B:
            return cls.BASIC
        elif color == 0xF47900:
            return cls.ADVANCED
        elif color == 0xE92829:
            return cls.EXPERT
        elif color == 0x8C1BE1:
            return cls.MASTER
        elif color == 0x0B6FF3:
            return cls.WORLDS_END
        else:
            raise ValueError(f"Unknown difficulty color: {color}")


class ClearType(Enum):
    FAILED = 0
    CLEAR = 1
    FULL_COMBO = 2
    ALL_JUSTICE = 3

    def __str__(self):
        return self.name.replace("_", " ")


class Rank(Enum):
    D = 0
    C = 1
    B = 2
    BB = 3
    BBB = 4
    A = 5
    AA = 6
    AAA = 7
    S = 8
    Sp = 9
    SS = 10
    SSp = 11
    SSS = 12
    SSSp = 13

    def __str__(self) -> str:
        return self.name.replace("p", "+")

    @classmethod
    def from_score(cls, score: int) -> Self:
        if score >= 1009000:
            return cls.SSSp
        elif score >= 1007500:
            return cls.SSS
        elif score >= 1005000:
            return cls.SSp
        elif score >= 1000000:
            return cls.SS
        elif score >= 990000:
            return cls.Sp
        elif score >= 975000:
            return cls.S
        elif score >= 950000:
            return cls.AAA
        elif score >= 925000:
            return cls.AA
        elif score >= 900000:
            return cls.A
        elif score >= 800000:
            return cls.BBB
        elif score >= 700000:
            return cls.BB
        elif score >= 600000:
            return cls.B
        elif score >= 500000:
            return cls.C
        else:
            return cls.D
