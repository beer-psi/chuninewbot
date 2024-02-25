package nadinenathaniel.app.util

import nadinenathaniel.app.network.NetscapeCookieJar
import nadinenathaniel.parsers.chunithm.ChunithmParser
import nadinenathaniel.parsers.chunithm.model.profile.ChunithmPlayerProfile
import okhttp3.Cookie

suspend fun validateLoginCookie(clal: String): Pair<NetscapeCookieJar, ChunithmPlayerProfile> {
    val cookie = Cookie.Builder()
        .hostOnlyDomain("lng-tgk-aime-gw.am-all.net")
        .path("/common_auth")
        .name("clal")
        .value(clal)
        .build()
    val cookieJar = NetscapeCookieJar(listOf(cookie))
    val parser = ChunithmParser(cookieJar = cookieJar)

    return cookieJar to parser.getBasicPlayerProfile()
}
