package nadinenathaniel.parsers.chunithm

import io.kotest.assertions.throwables.shouldThrow
import io.kotest.core.spec.style.FunSpec
import io.kotest.matchers.booleans.shouldBeTrue
import io.kotest.matchers.nulls.shouldNotBeNull
import io.kotest.matchers.shouldBe
import io.kotest.matchers.types.shouldBeTypeOf
import nadinenathaniel.parsers.chunithm.error.ChunithmNetException
import nadinenathaniel.parsers.chunithm.model.score.ChunithmClearLamp
import nadinenathaniel.parsers.chunithm.model.score.ChunithmComboLamp
import nadinenathaniel.parsers.chunithm.model.ChunithmDifficulty
import nadinenathaniel.parsers.chunithm.model.score.ChunithmRank
import nadinenathaniel.parsers.chunithm.model.MusicRatingType
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.FormBody
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest

class ChunithmParserTest : FunSpec({

    coroutineTestScope = true

    lateinit var server: MockWebServer
    lateinit var cookieJar: MemoryCookieJar
    lateinit var parser: ChunithmParser

    beforeAny {
        server = MockWebServer()
        cookieJar = MemoryCookieJar()
        parser = ChunithmParser(server.url("/").toString().removeSuffix("/"), cookieJar)
    }

    afterAny {
        server.shutdown()
    }

    fun getResourceText(name: String): String {
        return this::class.java.classLoader.getResource(name)!!.readText()
    }

    test("should parse recent score and details") {
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                if (request.path == "/mobile/record/playlog" && request.method == "GET") {
                    return MockResponse()
                        .setBody(getResourceText("playlog.html"))
                }

                if (
                    request.path == "/mobile/record/playlog/sendPlaylogDetail/" &&
                    request.method == "POST" &&
                    request.body.readUtf8().contains("idx=12&token=")
                ) {
                    return MockResponse()
                        .setResponseCode(302)
                        .setHeader("Location", "/mobile/record/playlogDetail/")
                }

                if (request.path == "/mobile/record/playlogDetail/" && request.method == "GET") {
                    return MockResponse()
                        .setBody(getResourceText("detailed_playlog.html"))
                }

                return MockResponse().setResponseCode(404)
            }
        }

        val scores = parser.getRecentScores()

        scores[0].track shouldBe 4

        scores[0].title shouldBe "GEOMETRIC DANCE"
        scores[0].difficulty shouldBe ChunithmDifficulty.MASTER

        scores[0].isNewRecord.shouldBeTrue()
        scores[0].score shouldBe 996_396
        scores[0].rank shouldBe ChunithmRank.S_PLUS
        scores[0].lamps.clear shouldBe ChunithmClearLamp.CLEAR
        scores[0].lamps.combo shouldBe ChunithmComboLamp.NONE

        scores[0].jacketUrl shouldBe "https://chunithm-net-eng.com/mobile/img/87b65507b23fb234.jpg"

        scores[0].timeAchieved shouldBe 1706506500000L

        scores[0].memo.shouldBeTypeOf<FormBody>()
        (scores[0].memo as FormBody).let {
            it.size shouldBe 2
            it.name(0) shouldBe "idx"
            it.value(0) shouldBe "12"
            it.name(1) shouldBe "token"
            it.value(1) shouldBe "d5602ef5bb09ac92b9b30dec51016cc5"
        }

        val details = parser.getRecentScoreDetails(scores[0])

        details.identifier shouldBe "2480"
        details.maxCombo shouldBe 453

        details.judgements.shouldNotBeNull()
        details.judgements!!.justiceCritical shouldBe 1821
        details.judgements!!.justice shouldBe 165
        details.judgements!!.attack shouldBe 23
        details.judgements!!.miss shouldBe 14

        details.hitPercentage.shouldNotBeNull()
        details.hitPercentage!!.tap shouldBe 9866
        details.hitPercentage!!.hold shouldBe 10098
        details.hitPercentage!!.slide shouldBe 10099
        details.hitPercentage!!.air shouldBe 10099
        details.hitPercentage!!.flick shouldBe 9884
    }

    test("should parse personal best") {
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                if (
                    request.path == "/mobile/record/musicGenre/sendMusicDetail/" &&
                    request.method == "POST" &&
                    request.body.readUtf8().contains("idx=428&token=")
                ) {
                    return MockResponse()
                        .setResponseCode(302)
                        .setHeader("Location", "/mobile/record/musicDetail/")
                }

                if (request.path == "/mobile/record/musicDetail/" && request.method == "GET") {
                    return MockResponse()
                        .setBody(getResourceText("music_record.html"))
                }

                return MockResponse().setResponseCode(404)
            }
        }
        cookieJar.saveFromHeader(
            server.url("/").toString(),
            "_t=0123456789abcdef; expires=Fri, 17-Feb-2034 18:58:20 GMT; Max-Age=315360000; path=/; SameSite=Strict",
        )

        val scores = parser.getPersonalBest(428)

        scores.size shouldBe 2

        scores[0].identifier shouldBe "428"
        scores[0].title shouldBe "Aleph-0"
        scores[0].difficulty shouldBe ChunithmDifficulty.EXPERT
        scores[0].score shouldBe 1_005_037
        scores[0].coverUrl shouldBe "https://chunithm-net-eng.com/mobile/img/986a1c6047f3033e.jpg"
        scores[0].rank shouldBe ChunithmRank.SS_PLUS
        scores[0].lamps.clear shouldBe ChunithmClearLamp.CLEAR
        scores[0].lamps.combo shouldBe ChunithmComboLamp.NONE
        scores[0].playCount shouldBe 2

        scores[1].identifier shouldBe "428"
        scores[1].title shouldBe "Aleph-0"
        scores[1].difficulty shouldBe ChunithmDifficulty.MASTER
        scores[1].score shouldBe 988_818
        scores[1].coverUrl shouldBe "https://chunithm-net-eng.com/mobile/img/986a1c6047f3033e.jpg"
        scores[1].rank shouldBe ChunithmRank.S
        scores[1].lamps.clear shouldBe ChunithmClearLamp.CLEAR
        scores[1].lamps.combo shouldBe ChunithmComboLamp.NONE
        scores[1].playCount shouldBe 2
    }

    test("should parse rating entries") {
        server.enqueue(MockResponse().setBody(getResourceText("best30.html")))

        val best30 = parser.getRatingEntries(MusicRatingType.BEST)

        best30.size shouldBe 30

        best30[0].identifier shouldBe "428"
        best30[0].title shouldBe "Aleph-0"
        best30[0].score shouldBe 1_005_037
        best30[0].difficulty shouldBe ChunithmDifficulty.EXPERT
    }

    test("should throw error on error page") {
        server.enqueue(
            MockResponse()
                .setResponseCode(302)
                .setHeader("Location", "/mobile/error")
        )
        server.enqueue(MockResponse().setBody(getResourceText("error_100001.html")))

        shouldThrow<ChunithmNetException> {
            parser.getRecentScores()
        }
    }
})

class MemoryCookieJar : CookieJar {
    private val cache = mutableSetOf<WrappedCookie>()

    @Synchronized
    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        val cookiesToRemove = mutableSetOf<WrappedCookie>()
        val validCookies = mutableSetOf<WrappedCookie>()

        cache.forEach { cookie ->
            if (cookie.isExpired()) {
                cookiesToRemove.add(cookie)
            } else if (cookie.matches(url)) {
                validCookies.add(cookie)
            }
        }

        cache.removeAll(cookiesToRemove)

        return validCookies.toList().map(WrappedCookie::unwrap)
    }

    @Synchronized
    fun saveFromHeader(url: String, setCookieHeader: String) {
        val cookie = Cookie.parse(url.toHttpUrl(), setCookieHeader) ?: return
        val wrappedCookie = WrappedCookie.wrap(cookie)

        cache.remove(wrappedCookie)
        cache.add(wrappedCookie)
    }

    @Synchronized
    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val cookiesToAdd = cookies.map { WrappedCookie.wrap(it) }

        cache.removeAll(cookiesToAdd.toSet())
        cache.addAll(cookiesToAdd)
    }

    @Synchronized
    fun clear() {
        cache.clear()
    }
}

class WrappedCookie private constructor(val cookie: Cookie) {
    fun unwrap() = cookie

    fun isExpired() = cookie.expiresAt < System.currentTimeMillis()

    fun matches(url: HttpUrl) = cookie.matches(url)

    override fun equals(other: Any?): Boolean {
        if (other !is WrappedCookie) return false

        return other.cookie.name == cookie.name &&
            other.cookie.domain == cookie.domain &&
            other.cookie.path == cookie.path &&
            other.cookie.secure == cookie.secure &&
            other.cookie.hostOnly == cookie.hostOnly
    }

    override fun hashCode(): Int {
        var hash = 17
        hash = 31 * hash + cookie.name.hashCode()
        hash = 31 * hash + cookie.domain.hashCode()
        hash = 31 * hash + cookie.path.hashCode()
        hash = 31 * hash + if (cookie.secure) 0 else 1
        hash = 31 * hash + if (cookie.hostOnly) 0 else 1
        return hash
    }

    companion object {
        fun wrap(cookie: Cookie) = WrappedCookie(cookie)
    }
}
