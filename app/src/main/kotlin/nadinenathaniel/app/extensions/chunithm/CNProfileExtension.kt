package nadinenathaniel.app.extensions.chunithm

import com.kotlindiscord.kord.extensions.commands.Arguments
import com.kotlindiscord.kord.extensions.commands.converters.impl.optionalUser
import com.kotlindiscord.kord.extensions.commands.converters.impl.string
import com.kotlindiscord.kord.extensions.extensions.Extension
import com.kotlindiscord.kord.extensions.extensions.ephemeralSlashCommand
import com.kotlindiscord.kord.extensions.extensions.publicSlashCommand
import dev.kord.common.entity.Snowflake
import dev.kord.rest.builder.message.embed
import io.ktor.client.request.forms.ChannelProvider
import io.ktor.utils.io.ByteReadChannel
import nadinenathaniel.app.checks.throwLoginMessageIfNull
import nadinenathaniel.app.models.NadineConfig
import nadinenathaniel.app.services.UserService
import nadinenathaniel.app.util.EmbedColors
import nadinenathaniel.parsers.chunithm.error.ChunithmNetException
import nadinenathaniel.parsers.chunithm.error.ERROR_USERNAME_CONTAINS_DIRTY_WORD
import org.koin.core.component.inject
import java.text.DecimalFormat

class CNProfileExtension : Extension() {

    override val name = "CHUNITHM-NET Profile"

    override val bundle = "nadine"

    private val botConfig by inject<NadineConfig>()
    private val userService by inject<UserService>()

    override suspend fun setup() {
        profileCommand()
        avatarCommand()
        renameCommand()
    }

    inner class ProfileArguments : Arguments() {
        val user by optionalUser {
            name = "commands.profile.args.user.name"
            description = "commands.profile.args.user.description"
        }
    }

    private suspend fun Extension.profileCommand() {
        publicSlashCommand(::ProfileArguments) {
            name = "commands.profile.name"
            description = "commands.profile.description"

            botConfig.bot.testServerId?.let { guild(Snowflake(it)) }

            action {
                val target = arguments.user ?: user
                val parser = userService.getChunithmParser(target).throwLoginMessageIfNull(target, user)
                val profile = parser.getPlayerProfile()

                respond {
                    embed {
                        title = profile.name
                        description = translate(
                            "commands.profile.response.description",
                            mapOf(
                                "lastPlayed" to profile.lastPlayed / 1000,
                                "level" to "${profile.rebornLevel.takeIf { it > 0 }?.let { "$it⭐ + " }.orEmpty()}${profile.level}",
                                "rating" to ratingDecimalFormat.format(profile.rating),
                                "maxRating" to ratingDecimalFormat.format(profile.maxRating),
                                "overPower" to ratingDecimalFormat.format(profile.overPower),
                                "overPowerPercentage" to "${ratingDecimalFormat.format(profile.overPowerPercentage)}%",
                                "playCount" to profile.playCount,
                            ),
                        )
                        author {
                            name = profile.nameplate.content
                        }
                        thumbnail {
                            url = profile.avatarUrl
                        }
                        color = EmbedColors.forPossession(profile.possession)
                    }
                }
            }
        }
    }

    inner class AvatarArguments : Arguments() {
        val user by optionalUser {
            name = "commands.avatar.args.user.name"
            description = "commands.avatar.args.user.description"
        }
    }

    private suspend fun Extension.avatarCommand() {
        publicSlashCommand(::AvatarArguments) {
            name = "commands.avatar.name"
            description = "commands.avatar.description"

            botConfig.bot.testServerId?.let { guild(Snowflake(it)) }

            action {
                val target = arguments.user ?: user
                val parser = userService.getChunithmParser(target).throwLoginMessageIfNull(target, user)
                val profile = parser.getPlayerProfile()
                val avatar = parser.renderPlayerAvatar(profile.avatar)

                respond {
                    content = translate("commands.avatar.response", arrayOf(profile.name))

                    addFile("avatar.png", ChannelProvider { ByteReadChannel(avatar) })
                }
            }
        }
    }

    inner class RenameArguments : Arguments() {
        val playerName by string {
            name = "commands.rename.args.playerName.name"
            description = "commands.rename.args.playerName.description"
            minLength = 1
            maxLength = 8
        }
    }

    private suspend fun Extension.renameCommand() {
        ephemeralSlashCommand(::RenameArguments) {
            name = "commands.rename.name"
            description = "commands.rename.description"

            botConfig.bot.testServerId?.let { guild(Snowflake(it)) }

            action {
                val parser = userService.getChunithmParser(user).throwLoginMessageIfNull()

                try {
                    parser.changePlayerName(arguments.playerName)

                    val profile = parser.getBasicPlayerProfile()

                    respond {
                        embed {
                            color = EmbedColors.SUCCESS
                            title = translate("commands.rename.response.title")
                            description = translate(
                                "commands.rename.response.description",
                                mapOf("playerName" to profile.name),
                            )
                        }
                    }
                } catch (e: IllegalArgumentException) {
                    respond {
                        embed {
                            color = EmbedColors.ERROR
                            title = translate("commands.rename.invalidPlayerName.title")
                            description = e.message
                        }
                    }
                } catch (e: ChunithmNetException) {
                    if (e.code != ERROR_USERNAME_CONTAINS_DIRTY_WORD) {
                        throw e
                    }

                    respond {
                        embed {
                            color = EmbedColors.ERROR
                            title = translate("commands.rename.invalidPlayerName.title")
                            description = translate("commands.rename.invalidPlayerName.badWord")
                        }
                    }
                }
            }
        }
    }
}

private val ratingDecimalFormat = DecimalFormat("#.00")
