package nadinenathaniel.app.extensions.chunithm

import com.kotlindiscord.kord.extensions.commands.Arguments
import com.kotlindiscord.kord.extensions.commands.application.slash.PublicSlashCommandContext
import com.kotlindiscord.kord.extensions.commands.converters.impl.optionalUser
import com.kotlindiscord.kord.extensions.components.forms.ModalForm
import com.kotlindiscord.kord.extensions.extensions.Extension
import com.kotlindiscord.kord.extensions.extensions.publicSlashCommand
import dev.kord.common.entity.Snowflake
import dev.kord.rest.builder.message.embed
import kotlinx.datetime.Instant
import nadinenathaniel.app.checks.throwLoginMessageIfNull
import nadinenathaniel.app.models.NadineConfig
import nadinenathaniel.app.services.UserService
import nadinenathaniel.app.util.EmbedColors
import nadinenathaniel.app.util.groupByCredit
import nadinenathaniel.kord.extensions.pagination.PublicResponsePaginator
import nadinenathaniel.kord.extensions.pagination.builders.PaginatorBuilder
import org.koin.core.component.inject

class CNScoreExtension : Extension() {

    override val name = "CHUNITHM-NET Scores"

    override val bundle = "nadine"

    private val botConfig by inject<NadineConfig>()
    private val userService by inject<UserService>()

    override suspend fun setup() {
        recentCommand()
    }

    inner class RecentArgs : Arguments() {
        val user by optionalUser {
            name = "commands.recent.args.user.name"
            description = "commands.recent.args.user.description"
        }
    }

    private suspend fun Extension.recentCommand() {
        publicSlashCommand(::RecentArgs) {
            name = "commands.recent.name"
            description = "commands.recent.description"

            botConfig.bot.testServerId?.let { guild(Snowflake(it)) }

            action { recentAction() }
        }
    }

    private suspend fun PublicSlashCommandContext<RecentArgs, ModalForm>.recentAction() {
        val target = arguments.user ?: user
        val parser = userService.getChunithmParser(target).throwLoginMessageIfNull(target, user)
        val scores = parser.getRecentScores()

        val paginatorBuilder = PaginatorBuilder(getLocale()).apply {
            owner = user

            scores.groupByCredit().forEach { credit ->
                page {
                    content = translate("commands.recent.response", arrayOf("abc"))

                    credit.forEach {
                        val rankIcon = botConfig.rankIcons[it.rank.name.lowercase()] ?: it.rank

                        embed {
                            author {
                                name = translate("commands.recent.trackNumber", arrayOf(it.track))
                            }
                            thumbnail {
                                url = it.jacketUrl
                            }
                            timestamp = Instant.fromEpochMilliseconds(it.timeAchieved)
                            color = EmbedColors.forDifficulty(it.difficulty)
                            description = """
                            |**${it.title} [${it.difficulty}]**
                            |
                            |▸ $rankIcon ▸ ${it.lamps.clear} ▸ ${it.score}
                            """.trimMargin()
                        }
                    }
                }
            }
        }

        PublicResponsePaginator(paginatorBuilder, interactionResponse).send()
    }
}
