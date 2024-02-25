package nadinenathaniel.parsers.chunithm.network

import nadinenathaniel.parsers.chunithm.error.ChunithmNetException
import okhttp3.Interceptor
import okhttp3.Response
import org.jsoup.Jsoup

internal object ChunithmNetErrorInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val response = chain.proceed(chain.request())
        val request = response.request // Use this to get the destination URL after redirects

        if (!request.url.encodedPath.startsWith("/mobile/error")) {
            return response
        }

        val document = Jsoup.parse(response.peekBody(Long.MAX_VALUE).string(), request.url.toString())
        val error = document.select(".block.text_l .font_small")
        val code = error[0].text().substringAfter(": ").toInt()
        val description = if (error.size > 1) error[1].text() else ""

        throw ChunithmNetException(code, description)
    }
}
