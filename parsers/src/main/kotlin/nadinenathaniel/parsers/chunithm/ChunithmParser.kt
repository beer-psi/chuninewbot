package nadinenathaniel.parsers.chunithm

import nadinenathaniel.parsers.chunithm.error.ChunithmNetException
import nadinenathaniel.parsers.chunithm.error.ERROR_USERNAME_CONTAINS_DIRTY_WORD
import nadinenathaniel.parsers.chunithm.error.UnknownDifficultyException
import nadinenathaniel.parsers.chunithm.model.score.ChunithmClearLamp
import nadinenathaniel.parsers.chunithm.model.score.ChunithmComboLamp
import nadinenathaniel.parsers.chunithm.model.ChunithmDifficulty
import nadinenathaniel.parsers.chunithm.model.score.ChunithmHitPercentage
import nadinenathaniel.parsers.chunithm.model.score.ChunithmJudgements
import nadinenathaniel.parsers.chunithm.model.score.ChunithmLamps
import nadinenathaniel.parsers.chunithm.model.score.ChunithmPersonalBest
import nadinenathaniel.parsers.chunithm.model.score.ChunithmRank
import nadinenathaniel.parsers.chunithm.model.score.ChunithmRatingEntry
import nadinenathaniel.parsers.chunithm.model.score.ChunithmRecentScore
import nadinenathaniel.parsers.chunithm.model.MusicRatingType
import nadinenathaniel.parsers.chunithm.model.cosmetics.ChunithmNameplate
import nadinenathaniel.parsers.chunithm.model.cosmetics.ChunithmNameplateRarity
import nadinenathaniel.parsers.chunithm.model.profile.ChunithmPlayerAvatar
import nadinenathaniel.parsers.chunithm.model.profile.ChunithmPossession
import nadinenathaniel.parsers.chunithm.model.profile.ChunithmPlayerProfile
import nadinenathaniel.parsers.chunithm.network.AuthenticationInterceptor
import nadinenathaniel.parsers.chunithm.network.ChunithmNetErrorInterceptor
import nadinenathaniel.parsers.chunithm.network.ScheduledMaintenanceInterceptor
import nadinenathaniel.parsers.chunithm.util.renderPlayerAvatarInternal
import nadinenathaniel.parsers.network.awaitSuccess
import nadinenathaniel.parsers.network.interceptor.UserAgentInterceptor
import nadinenathaniel.parsers.util.asJsoup
import okhttp3.Cache
import okhttp3.CookieJar
import okhttp3.FormBody
import okhttp3.Headers
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element
import java.nio.file.Files
import java.text.DecimalFormat
import java.text.DecimalFormatSymbols
import java.text.SimpleDateFormat
import java.util.TimeZone
import java.util.concurrent.TimeUnit

class ChunithmParser(
    cookieJar: CookieJar,
    private val baseUrl: String = "https://chunithm-net-eng.com",
) {
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .callTimeout(2, TimeUnit.MINUTES)
        .cookieJar(cookieJar)
        .cache(
            Cache(
                directory = Files.createTempDirectory("nadinenathaniel").toFile(),
                maxSize = 5L * 1024 * 1024,
            )
        )
        .addInterceptor(
            UserAgentInterceptor {
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
            }
        )
        .addInterceptor(ScheduledMaintenanceInterceptor)
        .addInterceptor(AuthenticationInterceptor)
        .addInterceptor(ChunithmNetErrorInterceptor)
        .build()

    private val requestToken
        get() = client.cookieJar.loadForRequest(baseUrl.toHttpUrl())
            .first { it.name == "_t" }
            .value

    private fun parseBasicPlayerProfile(document: Document): ChunithmPlayerProfile {
        val rating = document.select(".player_rating_num_block img").joinToString("") {
            val src = it.attr("src")
            val key = src.substringAfterLast("_").substringBefore(".png")

            when {
                key == "comma" -> "."
                key.startsWith("0") -> key.removePrefix("0")
                else -> throw IllegalStateException("Could not parse rating image URL $src")
            }
        }
            .toFloat()

        val overPowerText = document.selectFirst(".player_overpower_text")!!.text().split(" ")
        val overPower = overPowerText[0].toFloat()
        val overPowerPercentage = overPowerText[1].substringAfter("(").substringBefore("%)").toFloat()

        return ChunithmPlayerProfile(
            possession = ChunithmPossession.fromId(
                document.selectFirst(".box_playerprofile")!!
                    .attr("style")
                    .substringAfter("profile_")
                    .substringBefore(".png"),
            ),
            avatarUrl = document.selectFirst(".player_chara img")!!.absUrl("src"),
            nameplate = ChunithmNameplate(
                document.selectFirst(".player_honor_text")!!.text(),
                ChunithmNameplateRarity.fromId(
                    document.selectFirst(".player_honor_short")!!
                        .attr("style")
                        .substringAfter("honor_bg_")
                        .substringBefore(".png"),
                ),
            ),
            rebornLevel = document.selectFirst(".player_reborn")?.text()?.toInt() ?: 0,
            level = document.selectFirst(".player_lv")!!.text().toInt(),
            name = document.selectFirst(".player_name_in")!!.text(),
            rating = rating,
            maxRating = document.selectFirst(".player_rating_max")!!.text().toFloat(),
            overPower = overPower,
            overPowerPercentage = overPowerPercentage,
            lastPlayed = document.selectFirst(".player_lastplaydate_text")!!.text().let {
                dateFormat.parse(it)!!.time
            },
            avatar = ChunithmPlayerAvatar(
                base = "https://new.chunithm-net.com/chuni-mobile/html/mobile/images/avatar_base.png",
                back = document.selectFirst(".avatar_back img")!!.absUrl("src"),
                skinFootR = document.selectFirst(".avatar_skinfoot_r img")!!.absUrl("src"),
                skinFootL = document.selectFirst(".avatar_skinfoot_l img")!!.absUrl("src"),
                skin = document.selectFirst(".avatar_skin img")!!.absUrl("src"),
                wear = document.selectFirst(".avatar_wear img")!!.absUrl("src"),
                face = document.selectFirst(".avatar_face img")!!.absUrl("src"),
                faceCover = document.selectFirst(".avatar_faceCover img")!!.absUrl("src"),
                head = document.selectFirst(".avatar_head img")!!.absUrl("src"),
                handR = document.selectFirst(".avatar_hand_r img")!!.absUrl("src"),
                handL = document.selectFirst(".avatar_hand_l img")!!.absUrl("src"),
                itemR = document.selectFirst(".avatar_item_r img")!!.absUrl("src"),
                itemL = document.selectFirst(".avatar_item_l img")!!.absUrl("src"),
            )
        )
    }

    /**
     * Get the player's basic profile, which does not include friend code, currency, play count
     * and last played date.
     */
    suspend fun getBasicPlayerProfile(): ChunithmPlayerProfile {
        val request = Request.Builder()
            .method("GET", null)
            .url("$baseUrl/mobile/home/")
            .build()
        val document = client.newCall(request).awaitSuccess().asJsoup()

        return parseBasicPlayerProfile(document)
    }

    /**
     * Get the player's profile.
     */
    suspend fun getPlayerProfile(): ChunithmPlayerProfile {
        val request = Request.Builder()
            .method("GET", null)
            .url("$baseUrl/mobile/home/playerData")
            .build()
        val document = client.newCall(request).awaitSuccess().asJsoup()

        return parseBasicPlayerProfile(document).copy(
            friendCode = document.selectFirst(".user_data_friend_code span:not(.font_90)")!!.text(),
            ownedCurrency = document.selectFirst(".user_data_point div")!!.text().let {
                decimalFormat.parse(it).toInt()
            },
            earnedCurrency = document.selectFirst(".user_data_total_point div")!!.text().let {
                decimalFormat.parse(it).toInt()
            },
            playCount = document.selectFirst(".user_data_play_count div")!!.text().let {
                decimalFormat.parse(it).toInt()
            },
        )
    }

    /**
     * Given a [ChunithmPlayerAvatar] object, downloads all the images that
     * make up the avatar and renders it into a complete image.
     */
    suspend fun renderPlayerAvatar(avatar: ChunithmPlayerAvatar): ByteArray {
        return renderPlayerAvatarInternal(client, avatar)
    }

    /**
     * Get the player's 50 most recent scores.
     */
    suspend fun getRecentScores(): List<ChunithmRecentScore> {
        val request = Request.Builder()
            .method("GET", null)
            .url("$baseUrl/mobile/record/playlog")
            .build()
        val document = client.newCall(request).awaitSuccess().asJsoup()

        return document.select(".frame02.w400").map { el ->
            val date = el.selectFirst(".play_datalist_date")!!.text()
            val track = el.selectFirst(".play_track_text")!!.text()
                .removePrefix("TRACK ")
                .toInt()
            val title = el.selectFirst(".play_musicdata_title")!!.text()
            val difficulty = el.selectFirst(".play_track_result img")!!.let { e ->
                val key = e.attr("src")
                    .substringAfter("musiclevel_")
                    .substringBefore(".")

                parseDifficultyFromSlug(key)
            }
            val score = el.selectFirst(".play_musicdata_score_text")!!
                .let { decimalFormat.parse(it.text()).toInt() }
            val icons = el.selectFirst(".play_musicdata_icon")!!
            val rankIndex = parseRankIndex(icons)
            val lamps = parseLamps(icons)
            val detailsFormBody = FormBody.Builder().apply {
                el.select("form:has(.btn_see_detail) input").forEach {
                    add(it.attr("name"), it.`val`())
                }
            }.build()

            ChunithmRecentScore(
                identifier = "",
                title = title,
                difficulty = difficulty,
                score = score,
                jacketUrl = el.selectFirst(".play_jacket_img img")!!.absUrl("data-original"),
                rank = if (rankIndex != null) {
                    ChunithmRank.fromIndex(rankIndex)
                } else {
                    ChunithmRank.fromScore(score)
                },
                lamps = lamps,
                track = track,
                timeAchieved = dateFormat.parse(date)!!.time,
                isNewRecord = el.selectFirst(".play_musicdata_score_img") != null,
                memo = detailsFormBody,
            )
        }
    }

    /**
     * Get details for one of the 50 most recent scores.
     *
     * @param score A [ChunithmRecentScore] instance obtained by querying [getRecentScores].
     * @return A copy of [score] with details on max combo, judgements and hit percentages.
     */
    suspend fun getRecentScoreDetails(score: ChunithmRecentScore): ChunithmRecentScore {
        val request = Request.Builder()
            .method("POST", score.memo as FormBody)
            .url("$baseUrl/mobile/record/playlog/sendPlaylogDetail/")
            .build()
        val document = client.newCall(request).awaitSuccess().asJsoup()

        val identifier = document.selectFirst("input[name=idx]")!!.`val`()

        val maxCombo = document.selectFirst(".play_data_detail_maxcombo_block")!!
            .let { decimalFormat.parse(it.text()).toInt() }

        val critical = document.selectFirst(".text_critical")!!
            .let { decimalFormat.parse(it.text()).toInt() }
        val justice = document.selectFirst(".text_justice")!!
            .let { decimalFormat.parse(it.text()).toInt() }
        val attack = document.selectFirst(".text_attack")!!
            .let { decimalFormat.parse(it.text()).toInt() }
        val miss = document.selectFirst(".text_miss")!!
            .let { decimalFormat.parse(it.text()).toInt() }

        // I am Not fucking with float issues
        val tapHit = document.selectFirst(".text_tap_red")!!.text().percentageToInt()
        val holdHit = document.selectFirst(".text_hold_yellow")!!.text().percentageToInt()
        val slideHit = document.selectFirst(".text_slide_blue")!!.text().percentageToInt()
        val airHit = document.selectFirst(".text_air_green")!!.text().percentageToInt()
        val flickHit = document.selectFirst(".text_flick_skyblue")!!.text().percentageToInt()

        return score.copy(
            identifier = identifier,
            maxCombo = maxCombo,
            judgements = ChunithmJudgements(critical, justice, attack, miss),
            hitPercentage = ChunithmHitPercentage(tapHit, holdHit, slideHit, airHit, flickHit),
        )
    }

    /**
     * Get the player's personal best for a song.
     *
     * @param songId The ID of the song to get personal bests for.
     * @param isWorldsEnd Whether the song is a WORLD'S END song. This currently can be determined
     * by checking if [songId] is larger than or equal to 8000.
     * @return A list of the player's personal bests on each difficulty of that song.
     */
    suspend fun getPersonalBest(songId: Int, isWorldsEnd: Boolean): List<ChunithmPersonalBest> {
        val body = FormBody.Builder()
            .add("idx", songId.toString())
            .add("token", requestToken)
            .build()
        val url = if (isWorldsEnd) {
            "$baseUrl/mobile/record/worldsEndList/sendWorldsEndDetail/"
        } else {
            "$baseUrl/mobile/record/musicGenre/sendMusicDetail/"
        }
        val request = Request.Builder()
            .method("POST", body)
            .url(url)
            .build()
        val document = client.newCall(request).awaitSuccess().asJsoup()
        val title = document.selectFirst(".play_musicdata_title")!!.text()
        val coverUrl = document.selectFirst(".play_jacket_img img")!!.absUrl("src")
        val identifier = document.selectFirst("input[name=idx]")!!.`val`()

        return document.select(".music_box").map { el ->
            val score = el.selectFirst(".musicdata_score_title:contains(HIGH SCORE) + .musicdata_score_num span")!!
                .let { decimalFormat.parse(it.text()).toInt() }
            val playCount = el.selectFirst(".musicdata_score_title:contains(Play Count) + .musicdata_score_num span")!!
                .let { decimalFormat.parse(it.text().substringBefore("times")).toInt() }
            val difficulty = el.classNames()
                .first { it.startsWith("bg_") }
                .let { parseDifficultyFromSlug(it.removePrefix("bg_")) }
            val icons = el.selectFirst(".play_musicdata_icon")!!
            val rankIndex = parseRankIndex(icons)
            val lamps = parseLamps(icons)

            ChunithmPersonalBest(
                identifier = identifier,
                title = title,
                difficulty = difficulty,
                score = score,
                coverUrl = coverUrl,
                rank = if (rankIndex != null) {
                    ChunithmRank.fromIndex(rankIndex)
                } else {
                    ChunithmRank.fromScore(score)
                },
                lamps = lamps,
                playCount = playCount,
            )
        }
    }

    /**
     * Get player's rating entries by the required type
     *
     * @param type The rating type to get. See the [MusicRatingType] enum for details
     * on what the types mean
     * @return A list of scores.
     */
    suspend fun getRatingEntries(type: MusicRatingType): List<ChunithmRatingEntry> {
        val url = baseUrl.toHttpUrl().newBuilder().apply {
            addPathSegments("mobile/home/playerData")

            when (type) {
                MusicRatingType.BEST -> addPathSegment("ratingDetailBest")
                MusicRatingType.RECENT -> addPathSegment("ratingDetailRecent")
                MusicRatingType.SELECTION -> addPathSegment("ratingDetailNext")
            }

            addPathSegment("")
        }.build()
        val request = Request.Builder()
            .method("GET", null)
            .url(url)
            .build()
        val document = client.newCall(request).awaitSuccess().asJsoup()

        return document.select(".musiclist_box").map { el ->
            val identifier = el.selectFirst("input[name=idx]")!!.`val`()
            val title = el.selectFirst(".music_title")!!.text()
            val difficulty = el.classNames()
                .first { it.startsWith("bg_") }
                .let { parseDifficultyFromSlug(it.removePrefix("bg_")) }
            val score = el.selectFirst(".play_musicdata_highscore span")!!.let {
                decimalFormat.parse(it.text()).toInt()
            }

            ChunithmRatingEntry(identifier, title, difficulty, score)
        }
    }

    /**
     * Get the player's current game options.
     */
    suspend fun getPlayerOptions() {

    }

    /**
     * Changes the CHUNITHM-NET player name.
     *
     * @param newName The player name to change to. It must be between 1 and 8 characters,
     * and can only contain specific special characters.
     * @return `true` if the player name has been changed, otherwise an exception will
     * be thrown.
     * @throws IllegalArgumentException if the username contains illegal characters, or does not
     * have the required length.
     * @throws ChunithmNetException with error code [ERROR_USERNAME_CONTAINS_DIRTY_WORD] if the
     * username contains forbidden words.
     */
    suspend fun changePlayerName(newName: String): Boolean {
        require(newName.length in (1..PLAYER_NAME_MAXIMUM_LENGTH)) { "Player name must be between 1 and 8 characters" }

        val body = FormBody.Builder()
            .add("userName", newName)
            .add("token", requestToken)
            .build()
        val headers = Headers.Builder()
            .add("Referer", "$baseUrl/mobile/home/userOption/updateUserName")
            .build()
        val request = Request.Builder()
            .method("POST", body)
            .url("$baseUrl/mobile/home/userOption/updateUserName/update/")
            .headers(headers)
            .build()
        val response = client.newCall(request).awaitSuccess()

        if (response.request.url.encodedPath == "/mobile/home/userOption/") {
            return true
        }

        val document = response.asJsoup()
        val errorMessage = document.selectFirst(".text_red")!!.text()

        throw IllegalArgumentException(errorMessage)
    }

    suspend fun logout() {
        val request = Request.Builder()
            .method("GET", null)
            .url("$baseUrl/mobile/home/userOption/logout/")
            .build()

        client.newCall(request).awaitSuccess()
    }
}

private const val PLAYER_NAME_MAXIMUM_LENGTH = 8

private val decimalFormat = DecimalFormat().apply {
    decimalFormatSymbols = DecimalFormatSymbols().apply {
        groupingSeparator = ','
        decimalSeparator = '.'
    }
}
private val dateFormat = SimpleDateFormat("yyyy/MM/dd HH:mm").apply {
    timeZone = TimeZone.getTimeZone("Asia/Tokyo")
}

private fun String.percentageToInt() = replace(".", "")
    .replace("%", "")
    .toInt()

private fun parseDifficultyFromSlug(slug: String): ChunithmDifficulty {
    // ULTIMA -> ultimate???
    if (slug == "ultimate") {
        return ChunithmDifficulty.ULTIMA
    }

    // BASIC -> basic
    // ...
    // WORLDS_END -> worldsend
    return enumValues<ChunithmDifficulty>()
        .firstOrNull { d -> d.name.replace("_", "").lowercase() == slug }
        ?: throw UnknownDifficultyException(slug)
}

private fun parseRankIndex(icons: Element): Int? = icons
    .selectFirst("img[src*=icon_rank_]")
    ?.attr("src")
    ?.substringAfter("icon_rank_")
    ?.substringBefore(".")
    ?.toInt()

private fun parseLamps(icons: Element): ChunithmLamps {
    val clearLamp = when {
        icons.selectFirst("img[src*=_clear]") != null -> ChunithmClearLamp.CLEAR
        icons.selectFirst("img[src*=_hard]") != null -> ChunithmClearLamp.HARD
        icons.selectFirst("img[src*=_absolutep]") != null -> ChunithmClearLamp.ABSOLUTE_PLUS
        icons.selectFirst("img[src*=_absolute]") != null -> ChunithmClearLamp.ABSOLUTE
        icons.selectFirst("img[src*=_catastrophy]") != null -> ChunithmClearLamp.CATASTROPHY
        else -> ChunithmClearLamp.FAILED
    }
    val comboLamp = when {
        icons.selectFirst("img[src*=_fullcombo]") != null -> ChunithmComboLamp.FULL_COMBO
        icons.selectFirst("img[src*=_alljusticecritical]") != null -> ChunithmComboLamp.ALL_JUSTICE_CRITICAL
        icons.selectFirst("img[src*=_alljustice]") != null -> ChunithmComboLamp.ALL_JUSTICE
        else -> ChunithmComboLamp.NONE
    }

    return ChunithmLamps(clearLamp, comboLamp)
}
