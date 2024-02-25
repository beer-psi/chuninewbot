package nadinenathaniel.kord.extensions.pagination.builders

import dev.kord.rest.builder.message.MessageBuilder
import nadinenathaniel.kord.extensions.pagination.BasePaginator
import nadinenathaniel.kord.extensions.pagination.pages.Page

typealias PageMutator = suspend MessageBuilder.(page: Page) -> Unit
typealias PaginatorMutator = suspend BasePaginator.() -> Unit

/** Builder containing callbacks used to modify paginators and their page content. **/
class PageTransitionCallback {
    /** @suppress Variable storing the page mutator. **/
    var pageMutator: PageMutator? = null

    /** @suppress Variable storing the paginator mutator. **/
    var paginatorMutator: PaginatorMutator? = null

    /**
     * Set the page mutator callback.
     *
     * Called just after we apply the page's embed builder, and just before the page modifies the embed's footer.
     */
    fun page(body: PageMutator) {
        pageMutator = body
    }

    /**
     * Set the paginator mutator callback.
     *
     * Called just after we build a page embed, and just before that page is sent on Discord.
     */
    fun paginator(body: PaginatorMutator) {
        paginatorMutator = body
    }
}
