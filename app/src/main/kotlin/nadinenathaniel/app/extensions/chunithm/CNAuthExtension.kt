package nadinenathaniel.app.extensions.chunithm

import com.kotlindiscord.kord.extensions.commands.Arguments
import com.kotlindiscord.kord.extensions.commands.application.slash.EphemeralSlashCommandContext
import com.kotlindiscord.kord.extensions.commands.converters.impl.defaultingBoolean
import com.kotlindiscord.kord.extensions.commands.converters.impl.optionalString
import com.kotlindiscord.kord.extensions.components.components
import com.kotlindiscord.kord.extensions.components.forms.ModalForm
import com.kotlindiscord.kord.extensions.extensions.Extension
import com.kotlindiscord.kord.extensions.extensions.ephemeralSlashCommand
import com.kotlindiscord.kord.extensions.utils.waitFor
import dev.kord.common.entity.Snowflake
import dev.kord.rest.builder.message.embed
import nadinenathaniel.app.checks.failIfNotLoggedIn
import nadinenathaniel.app.checks.throwLoginMessageIfNull
import nadinenathaniel.app.events.ChunithmNetLoginEvent
import nadinenathaniel.app.models.NadineConfig
import nadinenathaniel.app.network.NetscapeCookieJar
import nadinenathaniel.app.services.UserService
import nadinenathaniel.app.util.EmbedColors
import nadinenathaniel.app.util.validateLoginCookie
import nadinenathaniel.app.util.toLong
import nadinenathaniel.kord.extensions.pagination.EphemeralResponsePaginator
import nadinenathaniel.kord.extensions.pagination.builders.PaginatorBuilder
import nadinenathaniel.parsers.chunithm.error.InvalidCookieException
import nadinenathaniel.parsers.chunithm.model.profile.ChunithmPlayerProfile
import org.koin.core.component.inject
import kotlin.time.Duration.Companion.minutes

class CNAuthExtension : Extension() {

    override val name = "CHUNITHM-NET Authentication"

    override val bundle = "nadine"

    private val botConfig by inject<NadineConfig>()
    private val userService by inject<UserService>()

    override suspend fun setup() {
        loginCommand()
        logoutCommand()
    }

    inner class LoginArguments: Arguments() {
        val cookie by optionalString {
            name = "clal"
            description = "Login cookie, if you can get it manually"
        }
    }

    private suspend fun Extension.loginCommand() {
        ephemeralSlashCommand(::LoginArguments) {
            name = "commands.login.name"
            description = "commands.login.description"

            botConfig.bot.testServerId?.let { guild(Snowflake(it)) }

            action {
                val (cookieJar, profile) = if (arguments.cookie != null) {
                    try {
                        respond {
                            embed {
                                color = EmbedColors.INFO
                                title = translate("commands.login.checkingCookie.title")
                                description = translate("commands.login.checkingCookie.description")
                            }
                        }

                        validateLoginCookie(arguments.cookie!!)
                    } catch (e: InvalidCookieException) {
                        respond {
                            embed {
                                color = EmbedColors.ERROR
                                title = translate("commands.login.failedCheck.title")
                                description = translate("commands.login.failedCheck.description")
                            }
                        }
                        return@action
                    }
                } else {
                    loginFlow() ?: return@action
                }

                userService.updateCookie(user, cookieJar.serializeToString())

                edit {
                    content = ""
                    components {}
                    embed {
                        color = EmbedColors.SUCCESS
                        title = translate("commands.login.response.title")
                        description = translate(
                            "commands.login.response.description",
                            arrayOf(profile.name),
                        )
                    }
                }
            }
        }
    }

    private suspend fun EphemeralSlashCommandContext<LoginArguments, ModalForm>.loginFlow(): Pair<NetscapeCookieJar, ChunithmPlayerProfile>? {
        val otp = buildString(6) {
            val chars = ('0'..'9')

            for (i in 0 until 6) {
                append(chars.random())
            }
        }
        val guideTranslationReplacements = arrayOf<Any?>(otp)
        val paginatorBuilder = PaginatorBuilder(getLocale()).apply {
            page(paginationInformationOnLastEmbed = true) {
                embed {
                    color = EmbedColors.CHUNITHM_YELLOW
                    title = translate("commands.login.guide.title")
                    description = translate("commands.login.guide.step1")
                }
            }
            page(paginationInformationOnLastEmbed = true) {
                embed {
                    color = EmbedColors.CHUNITHM_YELLOW
                    title = translate("commands.login.guide.title")
                    description = translate("commands.login.guide.step2", guideTranslationReplacements)
                }
            }
            page(paginationInformationOnLastEmbed = true) {
                content = "javascript:void(" +
                    "function(d){" +
                    "var s=d.createElement('script');" +
                    "s.src='https://gistcdn.githack.com/beerpiss/0eb8d3e50ae753388a6d4a4af5678a2e/raw/70f4e2f4defb26eb053b68dcee8c6250ba178503/login.js' ;" +
                    "d.body.append(s)" +
                    "}(document)" +
                    ")"
                embed {
                    color = EmbedColors.CHUNITHM_YELLOW
                    title = translate("commands.login.guide.title")
                    description = translate("commands.login.guide.step3", guideTranslationReplacements)
                }
            }
        }

        EphemeralResponsePaginator(paginatorBuilder, interactionResponse).send()

        val loginEvent = bot.waitFor<ChunithmNetLoginEvent>(5.minutes) { this.otp == otp }

        if (loginEvent == null) {
            edit {
                content = ""
                embed {
                    color = EmbedColors.ERROR
                    title = translate("commands.login.timedOut.title")
                    description = translate("commands.login.timedOut.description")
                }
            }
            return null
        }

        return loginEvent.cookieJar to loginEvent.profile
    }

    inner class LogoutArguments : Arguments() {
        val logout by defaultingBoolean {
            name = "commands.logout.args.logout.name"
            description = "commands.logout.args.logout.description"
            defaultValue = false
        }
    }

    private suspend fun Extension.logoutCommand() {
        ephemeralSlashCommand(::LogoutArguments) {
            name = "commands.logout.name"
            description = "commands.logout.description"

            botConfig.bot.testServerId?.let { guild(Snowflake(it)) }

            check { failIfNotLoggedIn() }

            action {
                val userId = user.id.toLong()

                if (arguments.logout) {
                    val parser = userService.getChunithmParser(user).throwLoginMessageIfNull()

                    parser.logout()
                }

                userService.deleteUser(user)

                respond {
                    embed {
                        color = EmbedColors.SUCCESS
                        title = translate("commands.logout.response.title")
                        description = translate("commands.logout.response.description")
                    }
                }
            }
        }
    }
}
