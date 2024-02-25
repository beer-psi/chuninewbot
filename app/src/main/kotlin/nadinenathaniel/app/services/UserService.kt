@file:Suppress("MemberVisibilityCanBePrivate")

package nadinenathaniel.app.services

import dev.kord.core.behavior.UserBehavior
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import nadinenathaniel.app.network.DatabaseCookieJar
import nadinenathaniel.app.util.toLong
import nadinenathaniel.data.Database
import nadinenathaniel.parsers.chunithm.ChunithmParser
import kotlin.coroutines.CoroutineContext

class UserService(
    private val db: Database,
    private val dispatcher: CoroutineContext = Dispatchers.IO,
) {

    suspend fun getChunithmParser(user: UserBehavior) =
        getChunithmParser(user.id.toLong())

    suspend fun getChunithmParser(userId: Long): ChunithmParser? {
        val cookieJar = try {
            DatabaseCookieJar(db, userId).also { it.loadCookies() }
        } catch (e: NullPointerException) {
            return null
        }

        return ChunithmParser(cookieJar = cookieJar)
    }

    suspend fun updateCookie(user: UserBehavior, cookie: String) {
        withContext(dispatcher) {
            db.usersQueries.upsert(user.id.toLong(), cookie, null)
        }
    }

    suspend fun updateKtchiToken(userId: Long, token: String) {
        withContext(dispatcher) {
            db.usersQueries.updateKtchiTokenBySnowflake(token, userId)
        }
    }

    suspend fun deleteUser(user: UserBehavior) {
        withContext(dispatcher) {
            db.usersQueries.deleteUserWithSnowflake(user.id.toLong())
        }
    }

    suspend fun userExists(user: UserBehavior): Boolean = userExists(user.id.toLong())

    suspend fun userExists(userId: Long): Boolean {
        return withContext(dispatcher) {
            db.usersQueries.getCookiesBySnowflake(userId).executeAsOneOrNull() != null
        }
    }
}
