package nadinenathaniel.app.network

import com.kotlindiscord.kord.extensions.utils.component6
import com.kotlindiscord.kord.extensions.utils.component7
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import java.util.Locale
import java.util.Objects

open class NetscapeCookieJar(cookies: List<Cookie>? = null) : CookieJar {

    private val cache = mutableListOf<WrappedCookie>()

    init {
        cookies?.let { cache.addAll(it.map(::WrappedCookie)) }
    }

    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        cache.removeAll { it.isExpired() }

        return cache.filter { it.matches(url) }.map { it.cookie }
    }

    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val cookiesToAdd = cookies.map { WrappedCookie(it) }.toSet()

        cache.removeAll(cookiesToAdd)
        cache.addAll(cookiesToAdd)
    }

    fun saveFromString(string: String) {
        if (!string.startsWith("# Netscape HTTP Cookie File") && !string.startsWith("# HTTP Cookie File")) {
            throw IllegalArgumentException("Input does not look like a Netscape format cookies file")
        }

        val lines = string.split("\n")

        for (line in lines) {
            var cookieLine = line.removeSuffix("\n").removeSuffix("\r")
            val isHttpOnly = cookieLine.startsWith(HTTPONLY_PREFIX)

            if (cookieLine.isBlank() || (cookieLine.startsWith("#") && !isHttpOnly)) {
                continue
            }

            val cookie = Cookie.Builder().apply {
                if (isHttpOnly) {
                    cookieLine = cookieLine.substring(HTTPONLY_PREFIX.length)
                    httpOnly()
                }

                val (domain, includeSubdomainsText, path, secureText, expiresAt, name, value) = cookieLine.split("\t")
                val includeSubdomains = includeSubdomainsText.equals("TRUE", ignoreCase = true)
                val secure = secureText.equals("TRUE", ignoreCase = true)
                val expiration = expiresAt.toLong() * 1000L

                if (includeSubdomains) {
                    domain(domain.removePrefix("."))
                } else {
                    hostOnlyDomain(domain)
                }

                path(path)

                if (secure) {
                    secure()
                }

                if (expiration != 0L) {
                    expiresAt(expiration)
                }

                name(name)
                value(value)
            }.build()

            cache.add(WrappedCookie(cookie))
        }
    }

    fun serializeToString(): String {
        val estimatedLength = COOKIES_HEADER_LENGTH +
            cache.sumOf {
                (if (it.cookie.httpOnly) HTTPONLY_PREFIX.length else 0) +
                    if (it.cookie.hostOnly) 0 else 1 +
                    it.cookie.domain.length +
                    BOOLEAN_LENGTH +
                    it.cookie.path.length +
                    BOOLEAN_LENGTH +
                    UNIX_TIMESTAMP_LENGTH +
                    it.cookie.name.length +
                    it.cookie.value.length +
                    COOKIES_COLUMN_COUNT
            }

        return buildString(estimatedLength) {
            appendLine("# Netscape HTTP Cookie File")
            appendLine("# https://curl.haxx.se/rfc/cookie_spec.html")
            appendLine("# This is a generated file! Edit at your own risk.")
            appendLine()

            cache
                .map { it.cookie }
                .forEach {
                    if (it.httpOnly) {
                        append(HTTPONLY_PREFIX)
                    }

                    if (!it.hostOnly) {
                        append(".")
                    }
                    append(it.domain)
                    append("\t")
                    append(if (it.hostOnly) "FALSE" else "TRUE")
                    append("\t")
                    append(it.path)
                    append("\t")
                    append(if (it.secure) "TRUE" else "FALSE")
                    append("\t")
                    append(if (it.persistent) it.expiresAt / 1000 else 0L)
                    append("\t")
                    append(it.name)
                    append("\t")
                    appendLine(it.value)
                }
        }
    }

    /**
     * A helper class for comparing cookies.
     */
    class WrappedCookie(val cookie: Cookie) {

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

        override fun hashCode() =
            Objects.hash(cookie.name, cookie.domain, cookie.path, cookie.secure, cookie.hostOnly)
    }
}

// The length of each line in the header, alongside the 4 newlines.
private const val COOKIES_HEADER_LENGTH = 114
private const val BOOLEAN_LENGTH = 5
// okhttp3.internal.http.MAX_DATE is 12 digits.
private const val UNIX_TIMESTAMP_LENGTH = 12
private const val COOKIES_COLUMN_COUNT = 7
private const val HTTPONLY_PREFIX = "#HttpOnly_"
