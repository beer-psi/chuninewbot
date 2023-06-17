from decimal import Decimal


def calculate_rating(score: int, internal_level: float) -> Decimal:
    level_base = Decimal(str(internal_level)) * 10000

    rating100 = Decimal(0)

    if score >= 1_009_000:
        rating100 = level_base + 21_500
    elif score >= 1_007_500:
        rating100 = level_base + 20_000 + (score - 1_007_500)
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

    return rating100 / 10000
