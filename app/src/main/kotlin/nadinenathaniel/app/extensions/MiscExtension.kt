package nadinenathaniel.app.extensions

import com.kotlindiscord.kord.extensions.extensions.Extension
import com.kotlindiscord.kord.extensions.extensions.ephemeralSlashCommand
import dev.kord.common.entity.Snowflake
import nadinenathaniel.app.models.NadineConfig
import org.koin.core.component.inject
import kotlin.time.DurationUnit

class MiscExtension : Extension() {

    override val name = "Miscellaneous"

    override val bundle = "nadine"

    private val botConfig by inject<NadineConfig>()

    override suspend fun setup() {
        pingCommand()
    }

    private suspend fun Extension.pingCommand() {
        ephemeralSlashCommand {
            name = "commands.ping.name"
            description = "commands.ping.description"

            botConfig.bot.testServerId?.let { guild(Snowflake(it)) }

            action {
                val begin = System.nanoTime()

                respond { content = translate("commands.ping.response.begin") }

                val end = System.nanoTime()
                val duration = ((end - begin) / 10_000).toString()

                edit {
                    content = translate(
                        "commands.ping.response.end",
                        arrayOf(
                            "${duration.substring(0, 3)}.${duration.substring(3, 5)}ms",
                            this@ephemeralSlashCommand.kord.gateway.averagePing!!.toString(DurationUnit.MILLISECONDS, 2),
                        ),
                    )
                }
            }
        }
    }
}
