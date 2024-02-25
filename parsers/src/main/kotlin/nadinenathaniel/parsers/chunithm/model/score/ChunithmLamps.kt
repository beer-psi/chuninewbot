package nadinenathaniel.parsers.chunithm.model.score

/**
 * The lamps for a CHUNITHM score.
 */
data class ChunithmLamps(
    val clear: ChunithmClearLamp = ChunithmClearLamp.FAILED,
    val combo: ChunithmComboLamp = ChunithmComboLamp.NONE,
)

enum class ChunithmClearLamp {
    FAILED,
    CLEAR,
    HARD,
    ABSOLUTE,
    ABSOLUTE_PLUS,
    CATASTROPHY,
    ;

    override fun toString() = this.name.replace("_PLUS", "+")
}

enum class ChunithmComboLamp {
    NONE,
    FULL_COMBO,
    ALL_JUSTICE,
    ALL_JUSTICE_CRITICAL,
    ;

    override fun toString() = when (this) {
        ALL_JUSTICE_CRITICAL -> "AJC"
        else -> this.name.replace("_", " ")
    }
}
