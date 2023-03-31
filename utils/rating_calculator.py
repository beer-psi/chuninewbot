from math import floor


RATING_POINTS = [
    { "score": 1009000, "base": 21500, "ratio": 0 },
    { "score": 1007500, "base": 20000, "ratio": 1 },
    { "score": 1005000, "base": 15000, "ratio": 2 },
    { "score": 1000000, "base": 10000, "ratio": 1 },
    { "score": 975000, "base": 0, "ratio": 0.4 },
    { "score": 900000, "base": -50000, "ratio": 2/3 },
]


def calculate_rating(score: int, internal_level: float) -> float:
    _const = floor(internal_level * 10000)

    if score >= 900000:
        point = next(x for x in RATING_POINTS if score >= x["score"])
        return max(0, _const + point["base"] + point["ratio"] * (score - point["score"])) / 10000

    rating = 0
    if score >= 800000:
        rating = (_const - 50000) / 2 + ((_const - 50000) / 2) * (score - 800000) / 100000
    elif score >= 500000:
        rating = ((_const - 50000) / 2) * (score - 500000) / 300000
    else:
        rating = 0
    
    return max(0, rating) / 10000
