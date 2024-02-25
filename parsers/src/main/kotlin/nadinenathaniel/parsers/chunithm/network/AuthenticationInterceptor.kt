package nadinenathaniel.parsers.chunithm.network

import nadinenathaniel.parsers.chunithm.error.ChunithmNetException
import nadinenathaniel.parsers.chunithm.error.ERROR_CONNECTION_TIME_EXPIRED
import nadinenathaniel.parsers.chunithm.error.ERROR_INVALID_SESSION
import nadinenathaniel.parsers.chunithm.error.InvalidCookieException
import okhttp3.HttpUrl
import okhttp3.Interceptor
import okhttp3.Request
import okhttp3.Response

internal object AuthenticationInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()

        try {
            val response = chain.proceed(request)

            // If we call /mobile/home with an invalid session, we get redirected
            // to /mobile/, which then redirects us to AUTHENTICATION_URL with JavaScript.
            //
            // In which case, we throw an exception here so the interceptor can authenticate.
            if (response.request.url.encodedPath == "/mobile/") {
                response.close()

                throw ChunithmNetException(ERROR_INVALID_SESSION, "")
            }

            return response
        } catch (e: ChunithmNetException) {
            if (e.code != ERROR_INVALID_SESSION && e.code != ERROR_CONNECTION_TIME_EXPIRED) {
                throw e
            }
        }

        val authRequest = Request.Builder()
            .method("GET", null)
            .url(AUTHENTICATION_URL)
            .build()

        chain.proceed(authRequest).use {
            if (it.request.url.host == AUTHENTICATION_URL.host) {
                throw InvalidCookieException()
            }
        }

        return chain.proceed(request)
    }
}

private val AUTHENTICATION_URL = HttpUrl.Builder()
    .scheme("https")
    .host("lng-tgk-aime-gw.am-all.net")
    .addPathSegments("common_auth/login")
    .addQueryParameter("site_id", "chuniex")
    .addQueryParameter("redirect_url", "https://chunithm-net-eng.com/mobile/")
    .addQueryParameter("back_url", "https://chunithm.sega.com/")
    .build()
