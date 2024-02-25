package nadinenathaniel.parsers.chunithm.model.profile

enum class ChunithmPossession(val id: String) {
    NONE("normal"),
    SILVER("silver"),
    GOLD("gold"),
    PLATINUM("platina"),
    RAINBOW("rainbow"),
    ;
    companion object {
        fun fromId(id: String): ChunithmPossession {
            return enumValues<ChunithmPossession>().first{ it.id == id }
        }
    }
}
