package nadinenathaniel.app

import app.cash.sqldelight.coroutines.asFlow
import app.cash.sqldelight.coroutines.mapToOne
import app.cash.sqldelight.driver.jdbc.JdbcDriver
import app.cash.sqldelight.driver.jdbc.asJdbcDriver
import com.kotlindiscord.kord.extensions.ExtensibleBot
import com.kotlindiscord.kord.extensions.i18n.TranslationsProvider
import com.kotlindiscord.kord.extensions.types.FailureReason
import com.kotlindiscord.kord.extensions.utils.getKoin
import com.kotlindiscord.kord.extensions.utils.loadModule
import com.typesafe.config.ConfigFactory
import com.zaxxer.hikari.HikariConfig
import com.zaxxer.hikari.HikariDataSource
import dev.kord.common.entity.Snowflake
import dev.kord.rest.builder.message.embed
import io.github.oshai.kotlinlogging.KotlinLogging
import kotlinx.coroutines.flow.first
import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.hocon.Hocon
import kotlinx.serialization.hocon.decodeFromConfig
import kotlinx.serialization.json.Json
import nadinenathaniel.app.extensions.MiscExtension
import nadinenathaniel.app.extensions.WebServerExtension
import nadinenathaniel.app.extensions.chunithm.CNAuthExtension
import nadinenathaniel.app.extensions.chunithm.CNProfileExtension
import nadinenathaniel.app.extensions.chunithm.CNScoreExtension
import nadinenathaniel.app.models.NadineConfig
import nadinenathaniel.app.services.ScoreService
import nadinenathaniel.app.services.UserService
import nadinenathaniel.app.util.EmbedColors
import nadinenathaniel.data.Database
import nadinenathaniel.parsers.chunithm.error.ChunithmNetException
import nadinenathaniel.parsers.chunithm.error.InvalidCookieException
import nadinenathaniel.parsers.chunithm.error.ScheduledMaintenanceException
import org.koin.dsl.bind
import java.io.File
import java.io.IOException
import java.sql.SQLException
import kotlin.concurrent.thread
import kotlin.coroutines.coroutineContext
import kotlin.system.exitProcess

private val logger = KotlinLogging.logger {}

@OptIn(ExperimentalSerializationApi::class)
@Suppress("LongMethod")
suspend fun main() {
    logger.info { "Starting up..." }

    val configFile = File("bot.conf")

    if (!configFile.exists()) {
        logger.error {
            "Config file \"bot.conf\" is not found. Ensure it exists in the working directory.\n" +
                "You can use the example config bundled with the bot to get started."
        }
        exitProcess(1)
    }

    val configText = try {
        configFile.readText()
    } catch (e: IOException) {
        logger.error(e) { "Could not read config file, even though it exists?!" }
        exitProcess(1)
    }
    val config = Hocon {}.decodeFromConfig<NadineConfig>(ConfigFactory.parseString(configText))

    logger.info { "Successfully parsed configuration." }

    // Ensure the database folder exists if we're using a local testing DB
    if (config.database.connection.startsWith("jdbc:h2:file:")) {
        val dbFile = File(config.database.connection.removePrefix("jdbc:h2:file:")).absoluteFile

        if (!dbFile.parentFile.exists()) {
            dbFile.parentFile.mkdirs()
        }
    }

    val dataSource = HikariDataSource(
        HikariConfig().apply {
            jdbcUrl = config.database.connection
            username = config.database.username
            password = config.database.password
            maximumPoolSize = config.database.poolSize
        }
    )
    val driver = dataSource.asJdbcDriver()
    val db = Database(driver)

    Runtime.getRuntime().addShutdownHook(thread(false) { driver.close() })

    val databaseVersion = try {
        db.databaseVersionQueries.getDatabaseVersion()
            .asFlow()
            .mapToOne(coroutineContext)
            .first()
    } catch (e: SQLException) {
        logger.debug(e) { "Could not query database version, assuming new database" }

        // Database is probably not set up yet.
        Database.Schema.create(driver).await()
        Database.Schema.version
    }

    if (databaseVersion < Database.Schema.version) {
        logger.info { "Database version ($databaseVersion) is older than the current version, migrating..." }
        Database.Schema.migrate(driver, databaseVersion, Database.Schema.version).await()
    }

    val testSnowflake = config.bot.testServerId?.let {
        logger.info { "Configured test server: $it" }
        Snowflake(it)
    }
    val bot = ExtensibleBot(config.bot.token) {
        if (testSnowflake != null) {
            applicationCommands {
                defaultGuild(testSnowflake)
            }
        }

        hooks {
            beforeKoinSetup {
                loadModule {
                    single { config } bind NadineConfig::class
                }
                loadModule {
                    single { driver } bind JdbcDriver::class
                    single { db } bind Database::class
                }
                loadModule {
                    single { UserService(db) } bind UserService::class
                    single { ScoreService(db) } bind ScoreService::class
                }
                loadModule {
                    single {
                        Json {
                            ignoreUnknownKeys = true
                            explicitNulls = false
                        }
                    } bind Json::class
                }
            }
        }

        i18n {
            interactionUserLocaleResolver()
        }

        chatCommands {
            defaultPrefix = "c>"
            enabled = true

            prefix { default ->
                if (guildId == testSnowflake) "c!" else default
            }
        }

        errorResponse { message, reason ->
            val tp = getKoin().get<TranslationsProvider>()

            embed {
                color = EmbedColors.ERROR
                title = "Error"

                description = if (reason is FailureReason.ExecutionError) {
                    when (val inner = reason.error) {
                        is ChunithmNetException -> tp.translate(
                            key = "errors.chunithmNetError",
                            bundleName = "nadine",
                            replacements = arrayOf(inner.code, inner.errorMessage),
                        )
                        is InvalidCookieException -> tp.translate(
                            key = "errors.invalidCookie",
                            bundleName = "nadine",
                        )
                        is ScheduledMaintenanceException -> tp.translate(
                            key = "errors.underMaintenance",
                            bundleName = "nadine",
                        )
                        else -> message
                    }
                } else {
                    message
                }
            }
        }

        extensions {
            add(::CNAuthExtension)
            add(::CNProfileExtension)
            add(::CNScoreExtension)
            add(::WebServerExtension)
            add(::MiscExtension)
        }
    }

    bot.start()
}
