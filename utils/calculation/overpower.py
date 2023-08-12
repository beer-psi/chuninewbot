from decimal import Decimal

from chunithm_net.entities.enums import ClearType
from utils import floor_to_ndp

from ..types.annotated_records import AnnotatedMusicRecord


def calculate_overpower_base(score: int, internal_level: float) -> Decimal:
    level_base = Decimal(str(internal_level)) * 10000

    rating100 = Decimal(0)

    if score >= 1_007_500:
        rating100 = level_base + 20_000 + (score - 1_007_500) * 3
    elif score >= 1_005_000:
        rating100 = level_base + 15_000 + (score - 1_005_000) * 2
    elif score >= 1_000_000:
        rating100 = level_base + 10_000 + (score - 1_000_000)
    elif score >= 975_000:
        rating100 = level_base + Decimal(score - 975_000) * 2 / 5
    elif score >= 900_000:
        rating100 = level_base - 50_000 + Decimal(score - 900_000) * 2 / 3
    elif score >= 800_000:
        rating100 = (level_base - 50_000) / 2 + (
            (score - 800_000) * ((level_base - 50_000) / 2)
        ) / 100_000
    elif score >= 500_000:
        rating100 = (((level_base - 50_000) / 2) * (score - 500_000)) / 300_000

    if rating100 < 0:
        rating100 = 0

    return Decimal(floor_to_ndp(rating100 / 2_000, 2))


def calculate_overpower_max(internal_level: float) -> Decimal:
    return Decimal(internal_level * 5 + 15)


def calculate_play_overpower(score: AnnotatedMusicRecord) -> Decimal:
    play_overpower = score.overpower_base
    if score.score == 1010000:
        play_overpower = score.overpower_max
    elif score.clear == ClearType.ALL_JUSTICE:
        play_overpower += Decimal(1)
    elif score.clear == ClearType.FULL_COMBO:
        play_overpower += Decimal(0.5)
    return play_overpower
