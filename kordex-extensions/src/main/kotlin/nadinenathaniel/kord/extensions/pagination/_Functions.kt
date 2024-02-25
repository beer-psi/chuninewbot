package nadinenathaniel.kord.extensions.pagination

import dev.kord.core.behavior.interaction.response.EphemeralMessageInteractionResponseBehavior
import dev.kord.core.behavior.interaction.response.PublicMessageInteractionResponseBehavior
import nadinenathaniel.kord.extensions.pagination.builders.PaginatorBuilder
import java.util.Locale

/** Create a paginator that edits the original interaction. **/
inline fun PublicMessageInteractionResponseBehavior.editingPaginator(
    defaultGroup: String = "",
    locale: Locale? = null,
    builder: (PaginatorBuilder).() -> Unit
): PublicResponsePaginator {
    val pages = PaginatorBuilder(locale = locale, defaultGroup = defaultGroup)

    builder(pages)

    return PublicResponsePaginator(pages, this)
}

/**
 * Create a paginator that edits the original interaction. This is the only option for an ephemeral interaction, as
 * it's impossible to edit an ephemeral follow-up.
 */
inline fun EphemeralMessageInteractionResponseBehavior.editingPaginator(
    defaultGroup: String = "",
    locale: Locale? = null,
    builder: (PaginatorBuilder).() -> Unit
): EphemeralResponsePaginator {
    val pages = PaginatorBuilder(locale = locale, defaultGroup = defaultGroup)

    builder(pages)

    return EphemeralResponsePaginator(pages, this)
}
