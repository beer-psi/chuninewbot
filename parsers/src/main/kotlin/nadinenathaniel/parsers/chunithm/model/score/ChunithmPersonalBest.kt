package nadinenathaniel.parsers.chunithm.model.score

import nadinenathaniel.parsers.chunithm.model.ChunithmDifficulty

data class ChunithmPersonalBest(
    override val identifier: String,
    override val title: String,
    override val difficulty: ChunithmDifficulty,
    override val score: Int,
    val coverUrl: String,
    val rank: ChunithmRank,
    val lamps: ChunithmLamps,
    val playCount: Int,
) : ChunithmBaseScore
