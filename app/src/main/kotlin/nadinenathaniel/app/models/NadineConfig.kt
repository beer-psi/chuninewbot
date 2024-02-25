package nadinenathaniel.app.models

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
class NadineConfig(
    val bot: BotConfig,
    val database: DatabaseConfig,
    val web: WebConfig = WebConfig(),
    val ktchi: KtchiConfig = KtchiConfig(),
    @SerialName("rank_icons") val rankIcons: Map<String, String> = emptyMap(),
)

@Serializable
class BotConfig(
    val token: String,
    @SerialName("default_prefix") val defaultPrefix: String = "c>",
    @SerialName("test_server_id") val testServerId: ULong? = null,
)

@Serializable
class DatabaseConfig(
    val connection: String,
    val username: String? = null,
    val password: String? = null,
    // https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing#the-formula
    // Assuming a 2-core server.
    @SerialName("pool_size") val poolSize: Int = 5,
)

@Serializable
class WebConfig(
    val enable: Boolean = false,
    val port: Int = 5730,
    @SerialName("base_url") val baseUrl: String? = null,
    val goatcounter: String? = null,
)

@Serializable
class KtchiConfig(
    @SerialName("client_id") val clientId: String? = null,
    @SerialName("client_secret") val clientSecret: String? = null,
)
