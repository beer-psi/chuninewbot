package nadinenathaniel.app.checks

import com.kotlindiscord.kord.extensions.DiscordRelayedException
import com.kotlindiscord.kord.extensions.checks.types.CheckContext
import com.kotlindiscord.kord.extensions.i18n.TranslationsProvider
import com.kotlindiscord.kord.extensions.utils.getKoin
import dev.kord.core.behavior.UserBehavior
import dev.kord.core.event.interaction.ChatInputCommandInteractionCreateEvent
import nadinenathaniel.app.services.UserService
import nadinenathaniel.parsers.chunithm.ChunithmParser

private val userService by lazy { getKoin().get<UserService>() }
private val translationProvider by lazy { getKoin().get<TranslationsProvider>() }

suspend fun CheckContext<ChatInputCommandInteractionCreateEvent>.failIfNotLoggedIn() {
    failIf(translate("errors.selfNotLoggedIn", bundle = "nadine")) {
        !userService.userExists(event.interaction.user)
    }
}

/**
 * Throws a [DiscordRelayedException] telling the user to log in
 * if the [ChunithmParser] is null.
 */
fun ChunithmParser?.throwLoginMessageIfNull(
    target: UserBehavior? = null,
    user: UserBehavior? = null,
): ChunithmParser {
    if (this != null) {
        return this
    }

    val isSelf = target == user
    val replacements = if (isSelf) {
        emptyArray()
    } else {
        arrayOf<Any?>(target!!.mention)
    }

    throw DiscordRelayedException(
        translationProvider.translate(
            key = if (isSelf) "errors.selfNotLoggedIn" else "errors.notLoggedIn",
            bundleName = "nadine",
            replacements = replacements,
        )
    )
}
