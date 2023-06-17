from math import floor


def calculate_rating(score: int, internal_level: float) -> float:
    level_base = floor(internal_level * 10000)

    rating100 = 0

    if score >= 1_009_000:
        rating100 = level_base + 21500
    elif score >= 1_007_500:
        rating100 = level_base + 20000 + (score - 1_007_500)
    elif score >= 1_005_000:
        rating100 = level_base + 15000 + (score - 1_005_000) * 2
    elif score >= 1_000_000:
        rating100 = level_base + 10000 + (score - 1_000_000)
    elif score >= 975_000:
        rating100 = level_base + (score - 975_000) * 2 / 5
    elif score >= 925_000:
        rating100 = level_base - 30000 + (score - 925_000) * 3 / 5
    elif score >= 900_000:
        rating100 = level_base - 50000 + (score - 900_000) * 2 / 3
    elif score >= 800_000:
        rating100 = (level_base - 50000) / 2 + (
            (score - 800_000) * ((level_base - 50000) / 2)
        ) / 100_000
    elif score >= 500_000:
        rating100 = (((level_base - 50000) / 2) * (score - 500_000)) / 300_000

    return rating100 / 10000
