package nadinenathaniel.parsers.chunithm.model.cosmetics

class ChunithmNameplate(
    val content: String,
    val rarity: ChunithmNameplateRarity,
)

enum class ChunithmNameplateRarity(val id: String) {
    NORMAL("normal"),
    BRONZE("bronze"),
    SILVER("silver"),
    GOLD("gold"),
    PLATINUM("platina"),
    RAINBOW("rainbow"),
    STAFF("staff"),
    ONGEKI("ongeki"),
    ;
    companion object {
        fun fromId(id: String): ChunithmNameplateRarity {
            return enumValues<ChunithmNameplateRarity>().first{ it.id == id }
        }
    }
}
