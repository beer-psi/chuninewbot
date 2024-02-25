package nadinenathaniel.app.network

import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import nadinenathaniel.data.Database
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl

/**
 * A [CookieJar] backed by the app's database.
 */
class DatabaseCookieJar(
    private val db: Database,
    private val userId: Long,
    cookies: List<Cookie>? = null,
    private val defaultDispatcher: CoroutineDispatcher = Dispatchers.IO,
) : NetscapeCookieJar(cookies) {

    private var loaded: Boolean = false

    suspend fun loadCookies() {
        val cookies = withContext(defaultDispatcher) {
            db.usersQueries.getCookiesBySnowflake(userId).executeAsOne().cookies
        }

        if (cookies.isNullOrBlank()) {
            loaded = true
            return
        }

        saveFromString(cookies)

        loaded = true
    }

    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        require(loaded) { "CookieJar not loaded before being used" }

        val cookies = super.loadForRequest(url)

        saveCookiesToDatabase()

        return cookies
    }

    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        require(loaded) { "CookieJar not loaded before being used" }

        super.saveFromResponse(url, cookies)
        saveCookiesToDatabase()
    }

    private var updateJob: Job? = null
    private val scope = CoroutineScope(defaultDispatcher)

    private fun saveCookiesToDatabase() = scope.launch {
        updateJob?.cancel()
        updateJob = launch(defaultDispatcher) {
            delay(SAVE_DEBOUNCE_MS)
            db.usersQueries.updateCookiesBySnowflake(serializeToString(), userId)
        }
    }
}

private const val SAVE_DEBOUNCE_MS = 750L
