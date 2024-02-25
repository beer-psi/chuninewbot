package nadinenathaniel.parsers.chunithm.network

import nadinenathaniel.parsers.chunithm.error.ScheduledMaintenanceException
import okhttp3.Interceptor
import okhttp3.Response

internal object ScheduledMaintenanceInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val response = chain.proceed(chain.request())

        if (response.code == HTTP_SERVICE_UNAVAILABLE) {
            throw ScheduledMaintenanceException()
        }

        return response
    }
}

/** `503 Service Unavailable` (HTTP/1.0 - RFC 7231)  */
private const val HTTP_SERVICE_UNAVAILABLE = 503
