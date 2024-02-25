package nadinenathaniel.app.extensions

import com.kotlindiscord.kord.extensions.extensions.Extension
import dev.kord.common.entity.Permission
import dev.kord.common.entity.Permissions
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.engine.embeddedServer
import io.ktor.server.netty.Netty
import io.ktor.server.netty.NettyApplicationEngine
import io.ktor.server.request.receiveParameters
import io.ktor.server.response.respondRedirect
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import nadinenathaniel.app.events.ChunithmNetLoginEvent
import nadinenathaniel.app.models.NadineConfig
import nadinenathaniel.app.services.UserService
import nadinenathaniel.app.util.validateLoginCookie
import nadinenathaniel.parsers.chunithm.error.InvalidCookieException
import nadinenathaniel.parsers.network.awaitSuccess
import okhttp3.Headers
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.koin.core.component.inject

class WebServerExtension(
    private val defaultDispatcher: CoroutineDispatcher = Dispatchers.IO,
) : Extension() {

    override val name = "Server"

    override val bundle = "nadine"

    private val config by inject<NadineConfig>()
    private val json by inject<Json>()
    private val userService by inject<UserService>()

    private val client = OkHttpClient()
    private val headers by lazy {
        Headers.Builder()
            .set("User-Agent", "NadineNathaniel (https://github.com/Kord-Extensions/kord-extensions 1.7.1-SNAPSHOT) Kotlin/1.9.20 okhttp/4.12.0")
            .build()
    }

    private lateinit var server: NettyApplicationEngine

    override suspend fun setup() {
        if (!config.web.enable) {
            return
        }

        server = embeddedServer(Netty, port = config.web.port) {
            routing {
                get("/") {
                    call.respondText { "Pri nay drac\n" }
                }
                get("/invite") {
                    val permissions = Permissions {
                        +Permission.ViewChannel
                        +Permission.SendMessages
                        +Permission.SendMessagesInThreads
                        +Permission.ReadMessageHistory
                        +Permission.ManageMessages
                    }

                    call.respondRedirect(
                        "https://discord.com/oauth2/authorize" +
                            "?client_id=${bot.kordRef.selfId}" +
                            "&scope=bot+applications.commands" +
                            "&permissions=${permissions.code.value}",
                        permanent = false,
                    )
                }
                post("/login") {
                    val data = call.receiveParameters()
                    val otp = data["otp"]
                    val clal = data["clal"]

                    if (otp?.toIntOrNull() == null) {
                        return@post call.respondText(status = HttpStatusCode.BadRequest) {
                            "Invalid parameter: OTP is missing or not a number.\n"
                        }
                    }

                    if (clal?.length != 64) {
                        return@post call.respondText(status = HttpStatusCode.BadRequest) {
                            "Invalid parameter: cookie is not of correct length.\n"
                        }
                    }

                    val (cookieJar, profile) = try {
                        validateLoginCookie(clal)
                    } catch (e: InvalidCookieException) {
                        return@post call.respondText(status = HttpStatusCode.Unauthorized) {
                            "The login cookie is invalid. Please log out, log in and try again.\n"
                        }
                    }

                    bot.send(ChunithmNetLoginEvent(otp, profile, cookieJar))

                    call.respondText {
                        "Success! Check the bot's DMs to see if the account has been successfully linked.\n"
                    }
                }

                if (
                    !config.ktchi.clientId.isNullOrBlank() &&
                    !config.ktchi.clientSecret.isNullOrBlank() &&
                    !config.web.baseUrl.isNullOrBlank()
                ) {
                    get("/kamaitachi/oauth") {
                        val params = call.request.queryParameters
                        val userId = params["context"]?.toLong()
                            ?: return@get call.respondText(status = HttpStatusCode.BadRequest) {
                                "Invalid parameter: context is not a valid Discord user ID.\n"
                            }
                        val code = params["code"]
                            ?: return@get call.respondText(status = HttpStatusCode.BadRequest) {
                                "Missing OAuth2 callback code.\n"
                            }

                        if (!userService.userExists(userId)) {
                            return@get call.respondText(status = HttpStatusCode.Unauthorized) {
                                "You have not linked your CHUNITM-NET account. Please use the /login command first.\n"
                            }
                        }

                        val requestData = OAuth2Request(
                            code = code,
                            clientId = config.ktchi.clientId!!,
                            clientSecret = config.ktchi.clientSecret!!,
                            grantType = "authorization_code",
                            redirectUri = "${config.web.baseUrl!!}/kamaitachi/oauth",
                        )
                        val request = Request.Builder()
                            .url("https://kamaitachi.xyz/api/v1/oauth/token")
                            .method(
                                "POST",
                                Json
                                    .encodeToString(requestData)
                                    .toRequestBody("application/json".toMediaType())
                            )
                            .headers(headers)
                            .build()
                        val response = client.newCall(request).awaitSuccess()
                        val data = json.decodeFromString<OAuth2Response>(response.body!!.string())

                        if (!data.success || data.body == null) {
                            return@get call.respondText(status = HttpStatusCode.Unauthorized) {
                                "Failed to authenticate with Kamaitachi: ${data.description}"
                            }
                        }

                        if (!data.body.permissions.customiseScore || data.body.permissions.submitScore) {
                            return@get call.respondText(status = HttpStatusCode.BadRequest) {
                                "Failed to authenticate with Kamaitachi: Token is missing a required permission.\n"
                            }
                        }

                        userService.updateKtchiToken(userId, data.body.token)

                        call.respondText {
                            "Your accounts are now linked! You can close this page now.\n"
                        }
                    }
                }
            }
        }

        server.start(wait = false)
    }

    override suspend fun unload() {
        if (!config.web.enable) {
            return
        }

        server.stop()
    }
}

@Serializable
private class OAuth2Request(
    val code: String,
    @SerialName("client_id") val clientId: String,
    @SerialName("client_secret") val clientSecret: String,
    @SerialName("grant_type") val grantType: String,
    @SerialName("redirect_uri") val redirectUri: String,
)

@Serializable
private class OAuth2Response(
    val success: Boolean,
    val description: String,
    val body: OAuth2ResponseBody? = null,
)

@Serializable
private class OAuth2ResponseBody(
    val token: String,
    val permissions: KtchiPermissions,
)

@Serializable
private class KtchiPermissions(
    @SerialName("submit_score") val submitScore: Boolean = false,
    @SerialName("customise_score") val customiseScore: Boolean = false,
)
