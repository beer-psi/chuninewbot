package nadinenathaniel.parsers.chunithm.model.score

import nadinenathaniel.parsers.chunithm.model.ChunithmDifficulty

data class ChunithmRatingEntry(
    override val identifier: String,
    override val title: String,
    override val difficulty: ChunithmDifficulty,
    override val score: Int,
) : ChunithmBaseScore
