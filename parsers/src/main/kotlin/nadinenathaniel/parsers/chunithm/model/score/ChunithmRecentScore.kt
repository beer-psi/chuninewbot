package nadinenathaniel.parsers.chunithm.model.score

import nadinenathaniel.parsers.chunithm.model.ChunithmDifficulty

data class ChunithmRecentScore(
    override val identifier: String,
    override val title: String,
    override val difficulty: ChunithmDifficulty,
    override val score: Int,
    val jacketUrl: String,
    val rank: ChunithmRank,
    val lamps: ChunithmLamps,
    val track: Int,
    val timeAchieved: Long,
    val isNewRecord: Boolean,
    val maxCombo: Int? = null,
    val judgements: ChunithmJudgements? = null,
    val hitPercentage: ChunithmHitPercentage? = null,
    internal val memo: Any? = null,
) : ChunithmBaseScore
