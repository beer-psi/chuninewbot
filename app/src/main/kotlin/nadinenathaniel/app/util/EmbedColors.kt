package nadinenathaniel.app.util

import dev.kord.common.Color
import nadinenathaniel.parsers.chunithm.model.ChunithmDifficulty
import nadinenathaniel.parsers.chunithm.model.profile.ChunithmPossession

@Suppress("MagicNumber")
object EmbedColors {
    val SUCCESS = Color(0x4caf50)
    val ERROR = Color(0xf44336)
    val INFO = Color(0x2196f3)

    val CHUNITHM_YELLOW = Color(0xFDD500)

    private val BASIC = Color(0x009F7B)
    private val ADVANCED = Color(0xF47900)
    private val EXPERT = Color(0xE92829)
    private val MASTER = Color(0x8C1BE1)
    private val ULTIMA = Color(0x131313)
    private val WORLDS_END = Color(0x0B6FF3)

    private val RARITY_NORMAL = Color(0xCECECE)
    private val RARITY_SILVER = Color(0x6BAAC7)
    private val RARITY_GOLD = Color(0xFCE620)
    private val RARITY_PLATINUM = Color(0xFFF6C5)
    private val RARITY_RAINBOW = Color(0x0B6FF3)

    fun forDifficulty(difficulty: ChunithmDifficulty): Color =
        when (difficulty) {
            ChunithmDifficulty.BASIC -> BASIC
            ChunithmDifficulty.ADVANCED -> ADVANCED
            ChunithmDifficulty.EXPERT -> EXPERT
            ChunithmDifficulty.MASTER -> MASTER
            ChunithmDifficulty.ULTIMA -> ULTIMA
            ChunithmDifficulty.WORLDS_END -> WORLDS_END
        }

    fun forPossession(possession: ChunithmPossession): Color =
        when (possession) {
            ChunithmPossession.NONE -> RARITY_NORMAL
            ChunithmPossession.SILVER -> RARITY_SILVER
            ChunithmPossession.GOLD -> RARITY_GOLD
            ChunithmPossession.PLATINUM -> RARITY_PLATINUM
            ChunithmPossession.RAINBOW -> RARITY_RAINBOW
        }
}
