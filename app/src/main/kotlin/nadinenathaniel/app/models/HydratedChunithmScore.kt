package nadinenathaniel.app.models

import nadinenathaniel.parsers.chunithm.model.score.ChunithmBaseScore

class HydratedChunithmScore<T : ChunithmBaseScore>(
    val score: T,
    val chartConstant: Float,
    val playRating: Float,
    val overPowerBase: Float,
    val overPowerMax: Float,
)
