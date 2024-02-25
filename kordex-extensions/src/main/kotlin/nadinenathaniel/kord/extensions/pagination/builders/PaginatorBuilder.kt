package nadinenathaniel.kord.extensions.pagination.builders

import dev.kord.core.behavior.UserBehavior
import dev.kord.core.entity.ReactionEmoji
import dev.kord.rest.builder.message.MessageBuilder
import nadinenathaniel.kord.extensions.pagination.pages.Page
import nadinenathaniel.kord.extensions.pagination.pages.Pages
import java.util.Locale

/**
 * Wrapping builder for easily creating paginators using DSL functions defined in the context classes.
 *
 * @param locale Locale to use for the paginator
 * @param defaultGroup Default page group, if any
 */
class PaginatorBuilder(
    var locale: Locale? = null,
    val defaultGroup: String = ""
) {
    /** Pages container object. **/
    val pages: Pages = Pages(defaultGroup)

    /** Paginator owner, if only one person should be able to interact. **/
    var owner: UserBehavior? = null

    /** Paginator timeout, in seconds. When elapsed, the paginator will be destroyed. **/
    var timeoutSeconds: Long? = null

    /** Whether to keep the paginator content on Discord when the paginator is destroyed. **/
    var keepEmbed: Boolean = true

    /** Alternative switch button emoji, if needed. **/
    var switchEmoji: ReactionEmoji? = null

    /** Translations bundle to use for page groups, if any. **/
    var bundle: String? = null

    /** Object containing paginator mutation functions. **/
    var mutator: PageTransitionCallback? = null

    /** Add a page to [pages], using the default group. **/
    fun page(page: Page): Unit = pages.addPage(page)

    /** Add a page to [pages], using the given group. **/
    fun page(group: String, page: Page): Unit = pages.addPage(group, page)

    /** Add a page to [pages], using the default group. **/
    fun page(
        bundle: String? = null,
        paginationInformationOnLastEmbed: Boolean = false,
        builder: suspend MessageBuilder.() -> Unit
    ): Unit =
        page(
            Page(
                builder = builder,
                bundle = bundle,
                paginationInformationOnLastEmbed = paginationInformationOnLastEmbed
            )
        )

    /** Add a page to [pages], using the given group. **/
    fun page(
        group: String,
        bundle: String? = null,
        paginationInformationOnLastEmbed: Boolean = false,
        builder: suspend MessageBuilder.() -> Unit
    ): Unit =
        page(
            group,
            Page(
                builder = builder,
                bundle = bundle,
                paginationInformationOnLastEmbed = paginationInformationOnLastEmbed,
            )
        )

    /**
     * Mutate the paginator and pages, as pages are generated and sent.
     *
     * @see PageTransitionCallback
     */
    suspend fun mutate(
        body: suspend PageTransitionCallback.() -> Unit
    ) {
        val obj = PageTransitionCallback()

        body(obj)

        this.mutator = obj
    }
}
