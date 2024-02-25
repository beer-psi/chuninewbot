package nadinenathaniel.parsers.chunithm.model.score

import nadinenathaniel.parsers.chunithm.model.ChunithmDifficulty

/**
 * Common properties of a CHUNITHM score.
 */
interface ChunithmBaseScore {
    /**
     * A unique identifier that points to the song. May be empty if it cannot be retrieved.
     */
    val identifier: String

    /**
     * The song's title
     */
    val title: String

    /**
     * The difficulty of the song.
     */
    val difficulty: ChunithmDifficulty

    /**
     * The score achieved.
     */
    val score: Int
}
