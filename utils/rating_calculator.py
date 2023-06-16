from math import floor


def calculate_rating(score: int, internal_level: float) -> float:
    level_base = internal_level * 100

    rating100 = 0

    if score >= 1_009_000:
        rating100 = level_base + 215
    elif score >= 1_007_500:
        rating100 = level_base + 200 + (score - 1_007_500) / 100
    elif score >= 1_005_000:
        rating100 = level_base + 150 + ((score - 1_005_000) * 10) / 500
    elif score >= 1_000_000:
        rating100 = level_base + 100 + ((score - 1_000_000) * 5) / 500
    elif score >= 975_000:
        rating100 = level_base + ((score - 975_000) * 2) / 500
    elif score >= 925_000:
        rating100 = level_base - 300 + ((score - 925_000) * 3) / 500
    elif score >= 900_000:
        rating100 = level_base - 500 + ((score - 900_000) * 4) / 500
    elif score >= 800_000:
        rating100 = (level_base - 500) / 2 + (
            (score - 800_000) * ((level_base - 500) / 2)
        ) / 100_000
    elif score >= 500_000:
        rating100 = (((level_base - 500) / 2) * (score - 500_000)) / 300_000

    return max(floor(rating100) / 100, 0)
