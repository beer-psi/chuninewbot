package nadinenathaniel.parsers.chunithm.model.score

/**
 * Details on how accurately the player hit a specific note type.
 * In order to avoid float processing issues, the numbers are
 * between 0 and 10100 instead of 0 to 101.
 */
data class ChunithmHitPercentage(
    val tap: Int,
    val hold: Int,
    val slide: Int,
    val air: Int,
    val flick: Int,
)
