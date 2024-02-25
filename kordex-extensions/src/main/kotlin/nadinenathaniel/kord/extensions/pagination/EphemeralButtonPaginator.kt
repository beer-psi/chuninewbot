package nadinenathaniel.kord.extensions.pagination

import com.kotlindiscord.kord.extensions.pagination.EXPAND_EMOJI
import com.kotlindiscord.kord.extensions.pagination.SWITCH_EMOJI
import dev.kord.core.behavior.UserBehavior
import dev.kord.core.behavior.interaction.response.EphemeralMessageInteractionResponseBehavior
import dev.kord.core.behavior.interaction.response.edit
import dev.kord.core.entity.ReactionEmoji
import nadinenathaniel.kord.extensions.pagination.builders.PageTransitionCallback
import nadinenathaniel.kord.extensions.pagination.builders.PaginatorBuilder
import nadinenathaniel.kord.extensions.pagination.pages.Pages
import java.util.Locale

/**
 * Class representing a button-based paginator that operates by editing the given ephemeral interaction response.
 *
 * @param interaction Interaction response behaviour to work with.
 */
class EphemeralResponsePaginator(
    pages: Pages,
    owner: UserBehavior? = null,
    timeoutSeconds: Long? = null,
    switchEmoji: ReactionEmoji = if (pages.groups.size == 2) EXPAND_EMOJI else SWITCH_EMOJI,
    mutator: PageTransitionCallback? = null,
    bundle: String? = null,
    locale: Locale? = null,

    val interaction: EphemeralMessageInteractionResponseBehavior,
) : BaseButtonPaginator(pages, owner, timeoutSeconds, true, switchEmoji, mutator, bundle, locale) {
    /** Whether this paginator has been set up for the first time. **/
    var isSetup: Boolean = false

    override suspend fun send() {
        if (!isSetup) {
            isSetup = true

            setup()
        } else {
            updateButtons()
        }

        interaction.edit {
            applyPage()

            with(this@EphemeralResponsePaginator.components) {
                this@edit.applyToMessage()
            }
        }
    }

    override suspend fun destroy() {
        if (!active) {
            return
        }

        active = false

        interaction.edit {
            applyPage()

            this.components = mutableListOf()
        }

        super.destroy()
    }
}

/** Convenience function for creating an interaction button paginator from a paginator builder. **/
@Suppress("FunctionNaming")  // Factory function
fun EphemeralResponsePaginator(
    builder: PaginatorBuilder,
    interaction: EphemeralMessageInteractionResponseBehavior
): EphemeralResponsePaginator = EphemeralResponsePaginator(
    pages = builder.pages,
    owner = builder.owner,
    timeoutSeconds = builder.timeoutSeconds,
    mutator = builder.mutator,
    bundle = builder.bundle,
    locale = builder.locale,
    interaction = interaction,

    switchEmoji = builder.switchEmoji ?: if (builder.pages.groups.size == 2) EXPAND_EMOJI else SWITCH_EMOJI,
)
