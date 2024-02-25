package nadinenathaniel.parsers.chunithm.model.profile

class ChunithmPlayerAvatar(
    val base: String,
    val back: String,
    val skinFootR: String,
    val skinFootL: String,
    val skin: String,
    val wear: String,
    val face: String,
    val faceCover: String,
    val head: String,
    val handR: String,
    val handL: String,
    val itemR: String,
    val itemL: String,
) {
    internal fun asMap() = mapOf(
        "base" to base,
        "back" to back,
        "skinFootR" to skinFootR,
        "skinFootL" to skinFootL,
        "skin" to skin,
        "wear" to wear,
        "face" to face,
        "faceCover" to faceCover,
        "head" to head,
        "handR" to handR,
        "handL" to handL,
        "itemR" to itemR,
        "itemL" to itemL,
    )
}
