package nadinenathaniel.parsers.chunithm.model

enum class ChunithmDifficulty {
    BASIC,
    ADVANCED,
    EXPERT,
    MASTER,
    ULTIMA,
    WORLDS_END,
    ;

    override fun toString(): String = when (this) {
        WORLDS_END -> "WORLD'S END"
        else -> name
    }
}
