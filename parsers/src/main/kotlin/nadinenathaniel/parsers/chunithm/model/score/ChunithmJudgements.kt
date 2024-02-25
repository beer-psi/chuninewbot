package nadinenathaniel.parsers.chunithm.model.score

/**
 * Details on how accurately the player hit all the notes in a score.
 */
data class ChunithmJudgements(
    val justiceCritical: Int,
    val justice: Int,
    val attack: Int,
    val miss: Int,
)
