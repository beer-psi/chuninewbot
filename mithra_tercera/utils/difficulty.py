from typing import Literal


ShortDifficulty = Literal["BAS", "ADV", "EXP", "MAS", "ULT", "WE"]

DIFFICULTIES: tuple[ShortDifficulty, ShortDifficulty, ShortDifficulty, ShortDifficulty, ShortDifficulty, ShortDifficulty] = ("BAS", "ADV", "EXP", "MAS", "ULT", "WE")

DIFFICULTY_TO_EMOJI: dict[ShortDifficulty, str] = {
    "BAS": ":green_square:",
    "ADV": ":yellow_square:",
    "EXP": ":red_square:",
    "MAS": ":purple_square:",
    "ULT": ":black_large_square:",
    "WE": ":blue_square:",
}
