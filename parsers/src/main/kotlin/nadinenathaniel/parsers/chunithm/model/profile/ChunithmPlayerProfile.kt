package nadinenathaniel.parsers.chunithm.model.profile

import nadinenathaniel.parsers.chunithm.model.cosmetics.ChunithmNameplate

data class ChunithmPlayerProfile(
    val possession: ChunithmPossession = ChunithmPossession.NONE,
    val nameplate: ChunithmNameplate,
    val avatarUrl: String,

    val rebornLevel: Int = 0,
    val level: Int,
    val name: String,

    val rating: Float,
    val maxRating: Float,

    val overPower: Float,
    val overPowerPercentage: Float,

    val lastPlayed: Long,

    val avatar: ChunithmPlayerAvatar,

    val friendCode: String? = null,
    val ownedCurrency: Int? = null,
    val earnedCurrency: Int? = null,
    val playCount: Int? = null,
)
