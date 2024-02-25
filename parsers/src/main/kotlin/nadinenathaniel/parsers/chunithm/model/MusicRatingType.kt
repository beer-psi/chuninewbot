package nadinenathaniel.parsers.chunithm.model

enum class MusicRatingType {
    /**
     * The player's best ratings.
     */
    BEST,

    /**
     * The player's top 10 recent scores, out of 30 most recent scores.
     */
    RECENT,

    /**
     * The player's top 10 highest ratings that are not in [BEST].
     */
    SELECTION,
}
